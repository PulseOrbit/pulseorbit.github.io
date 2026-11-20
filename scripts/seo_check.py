import requests, xml.etree.ElementTree as ET
from pathlib import Path
BASE = "https://pulseorbit.github.io"
ROOT = Path(__file__).resolve().parents[1]
tree = ET.parse(ROOT / "sitemap.xml")
ns = {"s":"http://www.sitemaps.org/schemas/sitemap/0.9"}
urls = [node.text for node in tree.findall(".//s:loc", ns)]
if not urls:
    raise SystemExit("Sitemap contains no URLs")
bad = []
for url in urls:
    try:
        response = requests.get(url, timeout=25, allow_redirects=True)
        print(f"{response.status_code} {url}")
        if response.status_code != 200:
            bad.append((url, response.status_code))
        if "noindex" in response.text.lower():
            print(f"Warning: noindex text found on {url}")
    except requests.RequestException as exc:
        bad.append((url, str(exc)))
if bad:
    raise SystemExit(f"SEO health check failed for {len(bad)} URL(s): {bad}")
print(f"SEO health check passed for {len(urls)} URLs.")
