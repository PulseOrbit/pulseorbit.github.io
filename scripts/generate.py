import os, json, re, html, hashlib, datetime, mimetypes, time
from pathlib import Path
from urllib.parse import quote
import requests
from huggingface_hub import HfApi

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "posts" / "index.json"
IMAGE_DIR = ROOT / "assets" / "images" / "posts"
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
MODEL_OVERRIDE = os.environ.get("GEMINI_MODEL", "").strip()
HF_TOKEN = os.environ.get("HF_TOKEN", "").strip()
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()
PIXABAY_CACHE_DIR = ROOT / "scripts" / "cache" / "pixabay"
PIXABAY_LICENSE_URL = "https://pixabay.com/service/license-summary/"
HF_DATASET_REPO = os.environ.get("HF_DATASET_REPO", "AhyanCreationsLTD/pulseorbit-images").strip()
BASE = "https://generativelanguage.googleapis.com/v1beta"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "PulseOrbitPublisher/2.0 (https://pulseorbit.github.io)"})
MAX_IMAGE_BYTES = 8 * 1024 * 1024

def checked(response, label):
    if not response.ok:
        try: detail = response.json().get("error", {}).get("message", response.text[:1000])
        except Exception: detail = response.text[:1000]
        raise RuntimeError(f"{label} failed (HTTP {response.status_code}): {detail}")
    return response

def get_trends():
    response = checked(SESSION.get("https://trends.google.com/trending/rss?geo=US", timeout=30), "Google Trends RSS")
    import xml.etree.ElementTree as ET
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item"):
        title, link = (item.findtext("title") or "").strip(), (item.findtext("link") or "").strip()
        if title and link: items.append({"title": title, "url": link})
    if not items: raise RuntimeError("Google Trends RSS returned no topics; no posts were published.")
    return items

def available_models():
    response = checked(SESSION.get(f"{BASE}/models", params={"key": API_KEY, "pageSize": 1000}, timeout=30), "Gemini model discovery")
    usable = {m.get("name", "").removeprefix("models/") for m in response.json().get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])}
    preferred = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
    ordered = [m for m in preferred if m in usable] + sorted(usable - set(preferred))
    if MODEL_OVERRIDE:
        override = MODEL_OVERRIDE.removeprefix("models/")
        ordered = [override] + [m for m in ordered if m != override]
    if not ordered: raise RuntimeError("No Gemini model supporting generateContent is available for this API key.")
    return ordered

def gemini_json(prompt):
    if not API_KEY: raise RuntimeError("Missing GEMINI_API_KEY GitHub Actions secret.")
    failures = []
    for model in available_models():
        endpoint = f"{BASE}/models/{model}:generateContent"
        for delay in (0, 4, 10):
            if delay: time.sleep(delay)
            try:
                response = SESSION.post(endpoint, params={"key": API_KEY}, json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json", "maxOutputTokens": 8192}
                }, timeout=120)
                if response.status_code in (429, 500, 502, 503, 504):
                    failures.append(f"{model}: HTTP {response.status_code}")
                    continue
                checked(response, f"Gemini ({model})")
                candidates = response.json().get("candidates") or []
                raw = "".join(p.get("text", "") for p in candidates[0].get("content", {}).get("parts", [])) if candidates else ""
                match = re.search(r"\{.*\}", raw, re.S)
                if match:
                    try: return json.loads(match.group(0))
                    except json.JSONDecodeError: failures.append(f"{model}: malformed JSON")
            except requests.RequestException as exc: failures.append(f"{model}: {exc}")
        print(f"Gemini model {model} failed; trying another model.")
    raise RuntimeError("All Gemini models failed: " + " | ".join(failures[-8:]))

def plain(value):
    return html.unescape(re.sub(r"<[^>]*>", "", str(value or ""))).strip()

def upload_image(image_bytes, slug, content_type, attribution):
    ext = mimetypes.guess_extension(content_type) or ".jpg"
    if ext == ".jpe": ext = ".jpg"
    digest = hashlib.sha256(image_bytes).hexdigest()[:12]
    filename = f"{slug[:55]}-{digest}{ext}"
    if HF_TOKEN:
        api = HfApi(token=HF_TOKEN)
        api.upload_file(path_or_fileobj=image_bytes, path_in_repo=f"images/{filename}",
                        repo_id=HF_DATASET_REPO, repo_type="dataset",
                        commit_message=f"Add licensed article image {slug[:55]}")
        metadata = json.dumps(attribution, ensure_ascii=False, indent=2).encode("utf-8")
        api.upload_file(path_or_fileobj=metadata, path_in_repo=f"metadata/{filename}.json",
                        repo_id=HF_DATASET_REPO, repo_type="dataset",
                        commit_message=f"Add image attribution metadata {slug[:55]}")
        return f"https://huggingface.co/datasets/{HF_DATASET_REPO}/resolve/main/images/{quote(filename)}", "huggingface"
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    (IMAGE_DIR / filename).write_bytes(image_bytes)
    return f"/assets/images/posts/{quote(filename)}", "repository"

def pixabay_image(topic, slug):
    """Search one focused query, cache its API response for 24 hours, then download locally.
    Pixabay image files are used in the context of their article, never mirrored to the public HF dataset.
    """
    if not PIXABAY_API_KEY:
        print("PIXABAY_API_KEY is not configured; using Wikimedia Commons fallback.")
        return None
    query = re.sub(r"[^a-zA-Z0-9 ,'-]", " ", str(topic or ""))[:100].strip()
    if not query:
        return None
    cache_key = hashlib.sha256(query.casefold().encode("utf-8")).hexdigest()
    cache_file = PIXABAY_CACHE_DIR / f"{cache_key}.json"
    payload = None
    try:
        if cache_file.exists():
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            fetched = datetime.datetime.fromisoformat(cached.get("fetched_at", ""))
            if (datetime.datetime.now(datetime.timezone.utc) - fetched).total_seconds() < 86400:
                payload = cached.get("response")
        if payload is None:
            response = checked(SESSION.get("https://pixabay.com/api/", params={
                "key": PIXABAY_API_KEY, "q": query, "lang": "en",
                "image_type": "photo", "orientation": "horizontal",
                "safesearch": "true", "per_page": 12, "order": "popular"
            }, timeout=35), "Pixabay image search")
            payload = response.json()
            PIXABAY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file.write_text(json.dumps({
                "query": query,
                "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "response": payload
            }, ensure_ascii=False), encoding="utf-8")
        hits = payload.get("hits") or []
        if not hits:
            print(f"Pixabay returned no image results for: {query}")
            return None
        for hit in hits[:12]:
            page_url = hit.get("pageURL", "")
            image_url = hit.get("largeImageURL") or hit.get("webformatURL")
            if not page_url.startswith("https://pixabay.com/") or not image_url.startswith("https://"):
                continue
            try:
                downloaded = checked(SESSION.get(image_url, timeout=45), "Pixabay image download")
                content_type = downloaded.headers.get("Content-Type", "").split(";")[0].lower()
                if not content_type.startswith("image/") or len(downloaded.content) > MAX_IMAGE_BYTES:
                    continue
                ext = mimetypes.guess_extension(content_type) or ".jpg"
                if ext == ".jpe": ext = ".jpg"
                digest = hashlib.sha256(downloaded.content).hexdigest()[:12]
                filename = f"{slug[:55]}-{digest}{ext}"
                IMAGE_DIR.mkdir(parents=True, exist_ok=True)
                (IMAGE_DIR / filename).write_bytes(downloaded.content)
                creator = str(hit.get("user") or "Pixabay contributor")
                return {
                    "url": f"/assets/images/posts/{quote(filename)}",
                    "page": page_url,
                    "credit": creator,
                    "license": "Pixabay Content License",
                    "license_url": PIXABAY_LICENSE_URL,
                    "storage": "repository"
                }
            except Exception as exc:
                print(f"Skipping a Pixabay result for '{query}': {exc}")
        print(f"Pixabay results were not downloadable for: {query}")
    except Exception as exc:
        print(f"Pixabay search warning for '{query}': {exc}")
    return None

def commons_image(topic, slug):
    api = "https://commons.wikimedia.org/w/api.php"
    try:
        response = checked(SESSION.get(api, params={
            "action": "query", "format": "json", "generator": "search",
            "gsrsearch": str(topic)[:180], "gsrnamespace": 6, "gsrlimit": 12,
            "prop": "imageinfo", "iiprop": "url|extmetadata|mime", "iiurlwidth": 1400
        }, timeout=35), "Wikimedia Commons search")
        pages = sorted(response.json().get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 999))
        for page in pages:
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            license_name = plain((meta.get("LicenseShortName") or {}).get("value"))
            lic = license_name.lower().strip()
            allowed = lic.startswith("cc0") or "public domain" in lic or bool(re.match(r"^cc by(?:-sa)?(?:\s|$)", lic))
            image_url, page_url = info.get("thumburl") or info.get("url"), info.get("descriptionurl", "")
            mime = (info.get("mime") or "").lower()
            if not allowed or not image_url or not page_url or not mime.startswith("image/"): continue
            image_response = checked(SESSION.get(image_url, timeout=45), "Commons image download")
            content_type = image_response.headers.get("Content-Type", "").split(";")[0].lower()
            if not content_type.startswith("image/") or len(image_response.content) > MAX_IMAGE_BYTES: continue
            attribution = {
                "title": plain(page.get("title")),
                "creator": plain((meta.get("Artist") or {}).get("value")) or "Wikimedia Commons contributor",
                "license": license_name, "license_url": (meta.get("LicenseUrl") or {}).get("value", ""),
                "source_page": page_url, "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
            url, storage = upload_image(image_response.content, slug, content_type, attribution)
            return {"url": url, "page": page_url, "credit": attribution["creator"],
                    "license": license_name, "license_url": attribution["license_url"], "storage": storage}
        print(f"No suitable freely reusable Commons image found for: {topic}")
    except Exception as exc: print(f"Image retrieval warning for '{topic}': {exc}")
    return None

def slugify(value):
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:75] or hashlib.sha1(value.encode()).hexdigest()[:12]

def make_article(trend, existing_titles):
    prompt = f"""You are PulseOrbit's careful English-language explainer editor.
Write one original, balanced and useful explainer about: {trend['title']!r}
Discovery page: {trend['url']}
A trending query is not evidence. Never invent facts, statistics, quotations, dates, sources or events. Qualify uncertainty. Do not provide personalized financial, medical or legal advice. Do not copy source text.
Return JSON only with keys: title (<=90 chars), description (one sentence), category (Technology, Science, Business, or Culture), content (exactly 5 objects with heading and text; each text 70-100 words), image_query (visual search phrase), image_alt (accurate concise alt text).
Avoid these existing titles: {json.dumps(existing_titles[:100])}
"""
    return gemini_json(prompt)

def main():
    if not INDEX.exists(): raise RuntimeError(f"Missing posts index: {INDEX}")
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    posts = data.get("posts", [])
    if not isinstance(posts, list): raise ValueError("posts/index.json must contain a posts array.")
    titles = [str(p.get("title", "")) for p in posts]
    backfilled = 0
    for old in posts:
        if backfilled >= 4: break
        if str(old.get("image", "")).endswith("placeholder.svg"):
            candidate = commons_image(old.get("title", ""), old.get("slug", "story"))
            if candidate:
                old.update({"image": candidate["url"], "image_credit": f"{candidate['credit']} — {candidate['license']}",
                            "image_source": candidate["page"], "image_license_url": candidate["license_url"],
                            "image_storage": candidate["storage"]})
                backfilled += 1
    trends = get_trends()
    selected, seen = [], set()
    for trend in trends:
        key = trend["title"].casefold()
        duplicate = any(key == old.casefold() or key in old.casefold() or old.casefold() in key for old in titles if old)
        if key not in seen and not duplicate:
            selected.append(trend); seen.add(key)
        if len(selected) == 2: break
    if len(selected) != 2: raise RuntimeError(f"Only {len(selected)} distinct eligible trends found; refusing partial publication.")
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    new_posts, slugs = [], {p.get("slug") for p in posts}
    for trend in selected:
        article = make_article(trend, titles)
        title = str(article.get("title", "")).strip()
        if not title or len(title) > 100: raise ValueError("Generated title missing or too long.")
        blocks = article.get("content") or []
        if len(blocks) != 5: raise ValueError(f"Article '{title}' must have exactly five sections.")
        body, words = [], 0
        for block in blocks:
            heading, paragraph = str(block.get("heading", "")).strip(), str(block.get("text", "")).strip()
            words += len(paragraph.split())
            if not heading or not paragraph: raise ValueError(f"Article '{title}' contains an empty section.")
            body.append(f"<h2>{html.escape(heading)}</h2><p>{html.escape(paragraph).replace(chr(10), '<br>')}</p>")
        if words < 350: raise ValueError(f"Article '{title}' is too short ({words} words).")
        slug = slugify(title)
        if slug in slugs: slug += "-" + hashlib.sha1(trend["title"].encode()).hexdigest()[:6]
        slugs.add(slug)
        image_topic = str(article.get("image_query") or trend["title"])
        image = pixabay_image(image_topic, slug) or commons_image(image_topic, slug)
        category = article.get("category")
        if category not in {"Technology", "Science", "Business", "Culture"}: category = "Culture"
        new_posts.append({
            "slug": slug, "title": title, "description": str(article.get("description", "")).strip(),
            "category": category, "date": today, "read_time": f"{max(3, words // 220)} min read",
            "content_html": "\n".join(body),
            "image": image["url"] if image else "/assets/images/placeholder.svg",
            "image_alt": str(article.get("image_alt") or title),
            "image_credit": f"{image['credit']} — {image['license']}" if image else "PulseOrbit",
            "image_source": image["page"] if image else "",
            "image_license_url": image["license_url"] if image else "",
            "image_storage": image["storage"] if image else "placeholder",
            "sources": [{"title": "Google Trends topic discovery", "url": trend["url"]}]
        })
    INDEX.write_text(json.dumps({"posts": new_posts + posts}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Prepared:", " | ".join(p["title"] for p in new_posts))

if __name__ == "__main__":
    main()
