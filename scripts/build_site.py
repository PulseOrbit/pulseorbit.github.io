import json, html, re
from pathlib import Path
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
BASE='https://pulseorbit.github.io'
INDEX=ROOT/'posts'/'index.json'
def esc(v): return html.escape(str(v or ''), quote=True)
def build_post(p):
    slug=p['slug']; title=esc(p.get('title')); desc=esc(p.get('description')); date=esc(p.get('date')); image=esc(p.get('image') or '/assets/images/placeholder.svg')
    body=p.get('content_html','')
    canonical=f'{BASE}/posts/{slug}/'
    doc=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{desc}"><meta name="theme-color" content="#08111f"><title>{title} | PulseOrbit</title><link rel="canonical" href="{canonical}"><meta property="og:type" content="article"><meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:image" content="{image}"><link rel="icon" href="/assets/images/favicon.svg"><link rel="stylesheet" href="/assets/css/style.css"></head><body><header class="topbar"><div class="wrap nav"><a class="brand" href="/"><span class="brand-mark">P</span><span>Pulse<span class="brand-accent">Orbit</span><small>IDEAS IN MOTION</small></span></a><nav><a href="/">Home</a><a href="/#latest">Latest stories</a></nav></div></header><main class="wrap section" style="max-width:850px"><a href="/#latest" class="eyebrow">← BACK TO STORIES</a><p class="story-category" style="margin-top:30px">{esc(p.get('category'))}</p><h1 style="font-size:clamp(34px,6vw,58px);letter-spacing:-2px">{title}</h1><p style="color:var(--muted)">{date} · {esc(p.get('read_time','4 min read'))}</p><img src="{image}" alt="{esc(p.get('image_alt',p.get('title')))}" style="width:100%;max-height:430px;object-fit:cover;border-radius:16px;margin:20px 0"><article class="article-content" style="font-size:17px;line-height:1.9">{body}</article><div style="border-top:1px solid var(--line);margin-top:40px;padding-top:25px"><a class="outline-btn" href="https://www.facebook.com/sharer/sharer.php?u={canonical}">Share story ↗</a> <button class="outline-btn" onclick="navigator.clipboard.writeText(location.href)">Copy link</button></div></main><footer><div class="wrap footer-bottom"><span>© {datetime.now(timezone.utc).year} PulseOrbit</span><span>Website crafted and maintained by Ahyan</span></div></footer></body></html>'''
    target=ROOT/'posts'/slug/'index.html'; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(doc,encoding='utf-8')
def main():
    data=json.loads(INDEX.read_text(encoding='utf-8')); posts=data.get('posts',[])
    seen=set(); urls=[BASE+'/']
    for p in posts:
        slug=p.get('slug','')
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',slug): raise ValueError(f'Invalid slug: {slug}')
        if slug in seen: raise ValueError(f'Duplicate slug: {slug}')
        seen.add(slug); build_post(p); urls.append(f'{BASE}/posts/{slug}/')
    xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+''.join(f'  <url><loc>{html.escape(u)}</loc></url>\n' for u in urls)+'</urlset>\n'
    (ROOT/'sitemap.xml').write_text(xml,encoding='utf-8')
    print(f'Built {len(posts)} article pages and sitemap.')
if __name__=='__main__': main()
