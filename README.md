# PulseOrbit

Responsive editorial website hosted on GitHub Pages.

## Daily publishing
The scheduled workflow runs daily at 07:30 Bangladesh time. It drafts two explainers with Gemini, validates article structure, searches Pixabay first for a relevant horizontal photo (with safe search enabled), downloads the selected image into the article assets folder, and falls back to Wikimedia Commons when Pixabay is unavailable. Pixabay API responses are cached for 24 hours. Pixabay images are not copied into the public Hugging Face dataset; they are stored with their article on this site, with source and license attribution.

https://huggingface.co/datasets/AhyanCreationsLTD/pulseorbit-images

Each image has a metadata JSON file recording creator, source page, licence, licence URL, and retrieval date. Only CC0, CC BY, CC BY-SA, and public-domain results are considered. If no suitable image is found, the site uses its local placeholder.

## GitHub Actions configuration
Required repository Actions secrets:
- GEMINI_API_KEY — Gemini API key
- HF_TOKEN — Hugging Face token with write access to the dataset

Optional Actions variable:
- GEMINI_MODEL — preferred Gemini model name; automatic model discovery is used if empty

The dataset repository ID is configured in the workflow. Never put API keys or tokens in frontend JavaScript, cache files, or committed files. Pixabay images are downloaded to the website rather than redistributed as standalone dataset files.

Run publishing manually from Actions → PulseOrbit daily publishing → Run workflow.

## Local build
```bash
python -m pip install -r requirements.txt
python scripts/build_site.py
```
