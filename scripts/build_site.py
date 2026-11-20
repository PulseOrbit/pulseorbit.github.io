import json, html, re
from pathlib import Path
from datetime import datetime, timezone
from html.parser import HTMLParser
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://pulseorbit.github.io"
INDEX = ROOT / "posts" / "index.json"
ALLOWED = {"h2", "h3", "p", "br", "strong", "em", "ul", "ol", "li", "blockquote", "a"}

class SafeHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True); self.out = []
    def handle_starttag(self, tag, attrs):
        if tag not in ALLOWED: return
        if tag == "a":
            href = dict(attrs).get("href", "")
            if urlparse(href).scheme in ("https", "http"):
                self.out.append(f'<a href="{html.escape(href, quote=True)}" rel="nofollow noopener" target="_blank">')
            else: self.out.append("<a>")
        else: self.out.append(f"<{tag}>")
    def handle_endtag(self, tag):
        if tag in ALLOWED and tag != "br": self.out.append(f"</{tag}>")
    def handle_data(self, data): self.out.append(html.escape(data))

def safe_body(post):
    if isinstance(post.get("sections"), list):
        chunks = []
        for section in post["sections"]:
            heading = html.escape(str(section.get("heading", "")))
            paragraph = html.escape(str(section.get("text", ""))).replace("\n", "<br>")
            if heading and paragraph: chunks.append(f"<h2>{heading}</h2><p>{paragraph}</p>")
        return "\n".join(chunks)
    parser = SafeHTML(); parser.feed(str(post.get("content_html", "")))
    return "".join(parser.out)

def absolute_image(raw):
    raw = str(raw or "/assets/images/placeholder.svg")
    return raw if raw.startswith(("https://", "http://")) else BASE + "/" + raw.lstrip("/")

def build_post(post):
    slug = post["slug"]
    title, desc = html.escape(str(post.get("title", ""))), html.escape(str(post.get("description", "")))
    date = html.escape(str(post.get("date", "")))
    image_raw = str(post.get("image") or "/assets/images/placeholder.svg")
    image, image_abs = html.escape(image_raw, quote=True), html.escape(absolute_image(image_raw), quote=True)
    canonical = f"{BASE}/posts/{slug}/"
    body = safe_body(post)
    credit = html.escape(str(post.get("image_credit", "")))
    source, license_url = str(post.get("image_source", "")), str(post.get("image_license_url", ""))
    attribution = ""
    if credit:
        attribution = f'<p class="image-credit">Image: {credit}'
        if source.startswith("https://"): attribution += f' · <a href="{html.escape(source, quote=True)}" rel="nofollow noopener" target="_blank">Source</a>'
        if license_url.startswith("https://"): attribution += f' · <a href="{html.escape(license_url, quote=True)}" rel="nofollow noopener" target="_blank">License</a>'
        attribution += "</p>"
    structured = json.dumps({
        "@context":"https://schema.org", "@type":"BlogPosting", "headline":str(post.get("title","")),
        "description":str(post.get("description","")), "datePublished":str(post.get("date","")),
        "image":absolute_image(image_raw), "mainEntityOfPage":canonical,
        "author":{"@type":"Organization","name":"PulseOrbit"},
        "publisher":{"@type":"Organization","name":"PulseOrbit"}
    }, ensure_ascii=False).replace("</", "<\\/")
    doc = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#08111f"><meta name="description" content="{desc}"><title>{title} | PulseOrbit</title><link rel="canonical" href="{canonical}"><meta property="og:type" content="article"><meta property="og:site_name" content="PulseOrbit"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:url" content="{canonical}"><meta property="og:image" content="{image_abs}"><meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{structured}</script><link rel="icon" href="/assets/images/favicon.svg"><link rel="stylesheet" href="/assets/css/style.css"><script async src="https://gc.zgo.at/count.js" data-goatcounter="https://pulseorbit.goatcounter.com/count"></script></head><body><header class="topbar"><div class="wrap nav"><a class="brand" href="/"><span class="brand-mark">P</span><span>Pulse<span class="brand-accent">Orbit</span><small>IDEAS IN MOTION</small></span></a><nav><a href="/">Home</a><a href="/#latest">Latest stories</a></nav></div></header><main class="wrap section article-page"><a href="/#latest" class="eyebrow">← BACK TO STORIES</a><p class="story-category article-category">{html.escape(str(post.get("category", "")))}</p><h1>{title}</h1><p class="article-meta">{date} · {html.escape(str(post.get("read_time", "4 min read")))}</p><img class="article-hero-image" src="{image}" alt="{html.escape(str(post.get("image_alt", post.get("title", ""))), quote=True)}" loading="eager"><div>{attribution}</div><article class="article-content">{body}</article><div class="article-actions"><a class="outline-btn" href="https://www.facebook.com/sharer/sharer.php?u={html.escape(canonical, quote=True)}" target="_blank" rel="noopener">Share story ↗</a> <button class="outline-btn" id="copyLink" type="button">Copy link</button></div><p id="copyStatus" aria-live="polite"></p></main><footer><div class="wrap footer-bottom"><span>© {datetime.now(timezone.utc).year} PulseOrbit</span><span>Website crafted and maintained by Ahyan · Rajshahi, Bangladesh · <a href="mailto:support@ahyancreations.top">Contact</a></span></div></footer><script>document.getElementById("copyLink").addEventListener("click",async()=>{{const status=document.getElementById("copyStatus");try{{await navigator.clipboard.writeText(location.href);status.textContent="Link copied."}}catch(e){{status.textContent="Copy is unavailable in this browser."}}}});</script></body></html>'''
    target = ROOT / "posts" / slug / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(doc, encoding="utf-8")

def main():
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    posts = data.get("posts", [])
    if not isinstance(posts, list): raise ValueError("Post index must contain a posts array.")
    seen, urls = set(), [BASE + "/"]
    for post in posts:
        slug = post.get("slug", "")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug): raise ValueError(f"Invalid slug: {slug}")
        if slug in seen: raise ValueError(f"Duplicate slug: {slug}")
        seen.add(slug)
        if not post.get("title") or not post.get("description"): raise ValueError(f"Post {slug} is missing title or description.")
        build_post(post); urls.append(f"{BASE}/posts/{slug}/")
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + "".join(f"  <url><loc>{html.escape(url)}</loc></url>\n" for url in urls) + "</urlset>\n"
    (ROOT / "sitemap.xml").write_text(xml, encoding="utf-8")
    print(f"Built {len(posts)} article pages and sitemap.")

if __name__ == "__main__":
    main()
