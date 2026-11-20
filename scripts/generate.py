import os, json, re, html, hashlib, datetime, urllib.parse, requests, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "posts" / "index.json"
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "PulseOrbitPublisher/1.0 (https://pulseorbit.github.io; editorial contact: site owner)"})

def get_trends():
    url = "https://trends.google.com/trending/rss?geo=US"
    response = SESSION.get(url, timeout=25)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title and link:
            items.append({"title": title, "url": link})
    return items

def commons_image(topic):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": "filetype:bitmap " + topic, "gsrnamespace": 6,
        "gsrlimit": 8, "prop": "imageinfo", "iiprop": "url|extmetadata",
        "iiurlwidth": 1400
    }
    try:
        data = SESSION.get("https://commons.wikimedia.org/w/api.php", params=params, timeout=25).json()
        pages = (data.get("query") or {}).get("pages") or {}
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            license_name = html.unescape(re.sub("<[^>]+>", "", (meta.get("LicenseShortName") or {}).get("value", ""))).strip()
            license_url = (meta.get("LicenseUrl") or {}).get("value", "")
            artist = html.unescape(re.sub("<[^>]+>", "", (meta.get("Artist") or {}).get("value", ""))).strip()
            if not info.get("thumburl") or not license_name:
                continue
            return {
                "url": info["thumburl"],
                "page": info.get("descriptionurl", ""),
                "credit": artist or "Wikimedia Commons contributor",
                "license": license_name,
                "license_url": license_url
            }
    except Exception as exc:
        print("Image lookup failed:", exc)
    return None

def gemini_json(prompt):
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY secret is missing. Add it in Settings → Secrets and variables → Actions.")
    model = "gemini-2.5-flash"
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    response = SESSION.post(endpoint, params={"key": API_KEY}, json={
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.55, "responseMimeType": "application/json"}
    }, timeout=90)
    response.raise_for_status()
    payload = response.json()
    text = payload["candidates"][0]["content"]["parts"][0]["text"]
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("Gemini returned no JSON object")
    return json.loads(match.group(0))

def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:75] or hashlib.sha1(value.encode()).hexdigest()[:12]

def make_article(trend, existing_titles):
    prompt = f"""You are the careful editor of PulseOrbit, an English-language global explainer publication.
Create one original, useful, balanced article about this currently trending topic: {trend['title']!r}.
Discovery/source link: {trend['url']}
Important: the trend feed alone does not prove factual claims. Do not invent facts, quotes, numbers, dates, causes or events. Use cautious language where the supplied source is insufficient. Do not claim to have interviewed anyone. Avoid medical, legal or financial advice. Write in clear natural English for a general audience. Make the article genuinely informative, not generic filler. Do not copy source wording.
Return only valid JSON with keys:
title (specific, accurate, <= 90 chars), description (one-sentence 140-180 chars), category (one of Technology, Science, Business, Culture), content (array of 5-7 objects each with heading and 1-2 paragraph text), image_query (short concrete visual search phrase), image_alt (accurate short alt text), sources (array of objects title,url; include the supplied discovery URL and only sources you can confidently identify).
Existing article titles to avoid duplicating: {json.dumps(existing_titles[:80])}
"""
    return gemini_json(prompt)

def main():
    posts = json.loads(INDEX.read_text(encoding="utf-8")).get("posts", [])
    existing = {p.get("slug") for p in posts}
    titles = [p.get("title", "") for p in posts]
    trends = get_trends()
    selected, seen = [], set()
    for t in trends:
        key = t["title"].casefold()
        if key not in seen and not any(key in x.casefold() or x.casefold() in key for x in titles if x):
            selected.append(t); seen.add(key)
        if len(selected) == 2:
            break
    if len(selected) < 2:
        raise RuntimeError(f"Only {len(selected)} eligible distinct trending topics found; refusing to publish filler.")
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    new_posts = []
    for trend in selected:
        article = make_article(trend, titles)
        title = str(article["title"]).strip()
        slug = slugify(title)
        if slug in existing:
            slug += "-" + hashlib.sha1(trend["title"].encode()).hexdigest()[:6]
        blocks = article.get("content") or []
        if len(blocks) < 4:
            raise ValueError("Generated article was too short; refusing to publish.")
        body = []
        for block in blocks:
            heading = html.escape(str(block.get("heading", "")).strip())
            paragraph = html.escape(str(block.get("text", "")).strip()).replace("\n", "<br>")
            if heading and paragraph:
                body.append(f"<h2>{heading}</h2><p>{paragraph}</p>")
        image = commons_image(str(article.get("image_query") or trend["title"]))
        sources = article.get("sources") or []
        if not any(s.get("url") == trend["url"] for s in sources):
            sources.insert(0, {"title": "Trending topic discovery", "url": trend["url"]})
        post = {
            "slug": slug, "title": title,
            "description": str(article["description"]).strip(),
            "category": article.get("category") if article.get("category") in {"Technology","Science","Business","Culture"} else "Culture",
            "date": today, "read_time": f"{max(4, sum(len(str(x.get('text','')).split()) for x in blocks)//220)} min read",
            "content_html": "\n".join(body),
            "image": image["url"] if image else "assets/images/placeholder.svg",
            "image_alt": str(article.get("image_alt") or title),
            "image_credit": (f"{image['credit']} — {image['license']}" if image else "PulseOrbit abstract placeholder"),
            "image_source": image["page"] if image else "",
            "image_license_url": image["license_url"] if image else "",
            "sources": [s for s in sources if isinstance(s, dict) and str(s.get("url","")).startswith(("https://","http://"))][:8]
        }
        new_posts.append(post)
        existing.add(slug); titles.append(title)
    INDEX.write_text(json.dumps({"posts": new_posts + posts}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Prepared two articles:", ", ".join(p["title"] for p in new_posts))

if __name__ == "__main__":
    main()
