# PulseOrbit

A responsive, static editorial website hosted on GitHub Pages.

## Structure

- `index.html` — home page
- `assets/` — styles, scripts, brand artwork
- `posts/index.json` — article data source
- `posts/<slug>/index.html` — generated, crawlable article pages
- `scripts/` — article builder and AI publisher
- `.github/workflows/` — publishing and build automation

## Daily AI publishing

The daily workflow runs at 07:30 Bangladesh time. Add a repository Actions secret named `GEMINI_API_KEY`. The publisher discovers available Gemini models, drafts two original explainers from Google Trends, searches Wikimedia Commons for images with reusable licenses, and records attribution in article metadata.

Run it manually from **Actions → PulseOrbit daily publishing → Run workflow**.

## Build locally

```bash
python -m pip install -r requirements.txt
python scripts/build_site.py
```

The site uses no frontend build system. GitHub Pages can publish the repository root from the `main` branch.
