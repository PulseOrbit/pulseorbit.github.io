# PulseOrbit

A responsive editorial blog published with GitHub Pages.

## Features
- Responsive homepage, article view, search, category filters and light/dark theme.
- Daily publishing workflow (two articles per run).
- Google Trends RSS discovery and AI-assisted article drafting with Gemini.
- Relevant Wikimedia Commons image discovery with source/author/license attribution.
- Duplicate-topic checks and source links.

## Setup
1. In the repository, open **Settings → Pages** and set **Deploy from a branch**, branch **main**, folder **/(root)**.
2. Open **Settings → Secrets and variables → Actions → New repository secret**.
3. Add a secret named `GEMINI_API_KEY` containing your Gemini API key.
4. Open **Actions**, enable workflows if prompted, then run **PulseOrbit daily publishing** manually once.
5. The scheduled workflow runs daily at 01:30 UTC (07:30 Bangladesh time) and attempts to publish two stories.

The workflow uses the free-to-access Google Trends RSS feed and Wikimedia Commons API. Gemini API usage may have quotas or costs depending on the account and model availability. If the API key is absent or generation fails, the workflow stops without publishing fabricated content.

## Image attribution
Images are selected from Wikimedia Commons and the post stores the file page, author and license metadata. Always retain the attribution shown in each article.

## Customize
Edit the site identity and navigation in `index.html`, visual styling in `assets/css/style.css`, and generation settings in `scripts/generate.py`.
