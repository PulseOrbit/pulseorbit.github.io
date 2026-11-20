import os, json, re, html, hashlib, datetime, requests, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "posts" / "index.json"
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL_OVERRIDE = os.environ.get("GEMINI_MODEL", "").strip()
BASE = "https://generativelanguage.googleapis.com/v1beta"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "PulseOrbitPublisher/1.1 (https://pulseorbit.github.io)"})

def checked(response, label):
    if not response.ok:
        try:
            detail = response.json().get("error", {}).get("message", response.text[:1200])
        except Exception:
            detail = response.text[:1200]
        raise RuntimeError(f"{label} failed (HTTP {response.status_code}): {detail}")
    return response

def get_trends():
    url = "https://trends.google.com/trending/rss?geo=US"
    response = checked(SESSION.get(url, timeout=30), "Google Trends RSS")
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        if title and link:
            items.append({"title": title, "url": link})
    if not items:
        raise RuntimeError("Google Trends RSS returned no topics. No posts were published.")
    return items

def available_models():
    response = checked(SESSION.get(f"{BASE}/models", params={"key": API_KEY, "pageSize": 1000}, timeout=30), "Gemini model discovery")
    models = response.json().get("models", [])
    usable = {
        item.get("name", "").removeprefix("models/")
        for item in models
        if "generateContent" in item.get("supportedGenerationMethods", [])
    }
    preferred = [
        "gemini-3.8-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
        "gemini-3.5-flash",
        "gemini-2.5-flash"
    ]
    ordered = [name for name in preferred if name in usable]
    ordered.extend(sorted(usable - set(ordered)))
    if MODEL_OVERRIDE:
        override = MODEL_OVERRIDE.removeprefix("models/")
        ordered = [override] + [name for name in ordered if name != override]
    if not ordered:
        raise RuntimeError("This Gemini API key has no models supporting generateContent. Check the key's project and Gemini API access.")
    return ordered

def gemini_json(prompt):
    if not API_KEY:
        raise RuntimeError("Missing GEMINI_API_KEY. Add it under Repository Settings → Secrets and variables → Actions.")
    transient_statuses = {429, 500, 502, 503, 504}
    failures = []
    for model in available_models():
        endpoint = f"{BASE}/models/{model}:generateContent"
        for attempt, delay in enumerate((0, 3, 8), start=1):
            if delay:
                import time
                print(f"Gemini {model}: waiting {delay}s before retry {attempt}/3")
                time.sleep(delay)
            try:
                response = SESSION.post(endpoint, params={"key": API_KEY}, json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 7000}
                }, timeout=120)
                if response.status_code in transient_statuses:
                    detail = response.text[:800]
                    failures.append(f"{model} attempt {attempt}: HTTP {response.status_code} {detail}")
                    print(f"Gemini {model} temporarily unavailable (HTTP {response.status_code}); retrying if possible.")
                    continue
                checked(response, f"Gemini generateContent ({model})")
                payload = response.json()
                candidates = payload.get("candidates") or []
                if not candidates:
                    raise RuntimeError("Gemini returned no candidates. Check API quota, safety filtering, and model availability.")
                parts = candidates[0].get("content", {}).get("parts", [])
                raw = "".join(part.get("text", "") for part in parts)
                match = re.search(r"\\{.*\\}", raw, re.S)
                if not match:
                    raise ValueError(f"Gemini did not return valid JSON. Response preview: {raw[:500]}")
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Gemini returned malformed JSON: {exc}") from exc
            except requests.RequestException as exc:
                failures.append(f"{model} attempt {attempt}: {exc}")
                print(f"Gemini {model} network error: {exc}")
                continue
            except Exception:
                raise
        print(f"Gemini model {model} exhausted retries; trying another available model.")
    summary = " | ".join(failures[-8:])
    raise RuntimeError(f"All available Gemini models failed after retries. Last errors: {summary}")

def commons_image(topic):
    params = {"action":"query","format":"json","generator":"search","gsrsearch":"filetype:bitmap " + topic,
              "gsrnamespace":6,"gsrlimit":10,"prop":"imageinfo","iiprop":"url|extmetadata","iiurlwidth":1400}
    try:
        response = checked(SESSION.get("https://commons.wikimedia.org/w/api.php", params=params, timeout=30), "Wikimedia Commons image search")
        pages = (response.json().get("query") or {}).get("pages") or {}
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            license_name = html.unescape(re.sub("<[^>]+>", "", (meta.get("LicenseShortName") or {}).get("value", ""))).strip()
            artist = html.unescape(re.sub("<[^>]+>", "", (meta.get("Artist") or {}).get("value", ""))).strip()
            if info.get("thumburl") and license_name:
                return {"url":info["thumburl"],"page":info.get("descriptionurl",""),
                        "credit":artist or "Wikimedia Commons contributor","license":license_name,
                        "license_url":(meta.get("LicenseUrl") or {}).get("value","")}
    except Exception as exc:
        print(f"Image search warning: {exc}")
    return None

def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:75] or hashlib.sha1(value.encode()).hexdigest()[:12]

def make_article(trend, existing_titles):
    prompt = f"""You are the careful editor of PulseOrbit, an English-language global explainer publication.
Create one original, useful, balanced article about this currently trending topic: {trend['title']!r}.
Discovery link: {trend['url']}
Do not treat a trend as proof. Do not invent facts, quotes, numbers, dates, causes or events. Do not invent sources or claim research you did not perform. Avoid advice in high-stakes areas. Write natural, clear English for a general audience. Do not copy source wording.
Return JSON only with keys:
title (accurate, <=90 chars), description (one sentence), category (Technology, Science, Business, or Culture), content (5-7 objects with heading and text; each text 80-150 words), image_query (concrete visual search phrase), image_alt (accurate short alt text), sources (array containing only the supplied discovery URL; do not invent URLs).
Existing titles to avoid: {json.dumps(existing_titles[:100])}
"""
    return gemini_json(prompt)

def main():
    if not INDEX.exists():
        raise RuntimeError(f"Posts index not found: {INDEX}")
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    posts = data.get("posts", [])
    titles = [p.get("title", "") for p in posts]
    trends = get_trends()
    selected, seen = [], set()
    for trend in trends:
        key = trend["title"].casefold()
        duplicate = any(key == old.casefold() or key in old.casefold() or old.casefold() in key for old in titles if old)
        if key not in seen and not duplicate:
            selected.append(trend); seen.add(key)
        if len(selected) == 2:
            break
    if len(selected) != 2:
        raise RuntimeError(f"Only {len(selected)} distinct eligible trends found; refusing to publish fewer than two posts.")
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    new_posts, existing_slugs = [], {p.get("slug") for p in posts}
    for trend in selected:
        article = make_article(trend, titles)
        title = str(article.get("title", "")).strip()
        if not title or len(title) > 100:
            raise ValueError("Generated title is missing or too long.")
        blocks = article.get("content") or []
        if len(blocks) < 5:
            raise ValueError(f"Article '{title}' is too short; refusing to publish.")
        body = []
        word_count = 0
        for block in blocks:
            heading = html.escape(str(block.get("heading", "")).strip())
            paragraph_text = str(block.get("text", "")).strip()
            word_count += len(paragraph_text.split())
            paragraph = html.escape(paragraph_text).replace("\n", "<br>")
            if heading and paragraph:
                body.append(f"<h2>{heading}</h2><p>{paragraph}</p>")
        if word_count < 350:
            raise ValueError(f"Article '{title}' is under 350 words; refusing to publish.")
        slug = slugify(title)
        if slug in existing_slugs:
            slug += "-" + hashlib.sha1(trend["title"].encode()).hexdigest()[:6]
        image = commons_image(str(article.get("image_query") or trend["title"]))
        sources = [{"title":"Google Trends topic discovery","url":trend["url"]}]
        if image and image.get("page"):
            sources.append({"title":"Image source and license","url":image["page"]})
        post = {
            "slug":slug,"title":title,"description":str(article.get("description","")).strip(),
            "category":article.get("category") if article.get("category") in {"Technology","Science","Business","Culture"} else "Culture",
            "date":today,"read_time":f"{max(3, word_count//220)} min read","content_html":"\n".join(body),
            "image":image["url"] if image else "assets/images/placeholder.svg",
            "image_alt":str(article.get("image_alt") or title),
            "image_credit":(f"{image['credit']} — {image['license']}" if image else "PulseOrbit abstract placeholder"),
            "image_source":image["page"] if image else "",
            "image_license_url":image["license_url"] if image else "",
            "sources":sources
        }
        new_posts.append(post); existing_slugs.add(slug); titles.append(title)
    INDEX.write_text(json.dumps({"posts":new_posts+posts},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Prepared exactly two articles:", " | ".join(p["title"] for p in new_posts))

if __name__ == "__main__":
    main()
