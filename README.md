# PulseOrbit

Responsive editorial website hosted on GitHub Pages.

## Daily publishing
The scheduled workflow runs daily at 07:30 Bangladesh time. It drafts two explainers with Gemini, validates article structure, searches Wikimedia Commons for reusable images, downloads selected images, and uploads them to the public Hugging Face dataset:

https://huggingface.co/datasets/AhyanCreationsLTD/pulseorbit-images

Each image has a metadata JSON file recording creator, source page, licence, licence URL, and retrieval date. Only CC0, CC BY, CC BY-SA, and public-domain results are considered. If no suitable image is found, the site uses its local placeholder.

## GitHub Actions configuration
Required repository Actions secrets:
- GEMINI_API_KEY — Gemini API key
- HF_TOKEN — Hugging Face token with write access to the dataset

Optional Actions variable:
- GEMINI_MODEL — preferred Gemini model name; automatic model discovery is used if empty

The dataset repository ID is configured in the workflow. Never put API keys or tokens in frontend JavaScript or committed files.

Run publishing manually from Actions → PulseOrbit daily publishing → Run workflow.

## Local build
```bash
python -m pip install -r requirements.txt
python scripts/build_site.py
```
