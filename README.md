# PulseOrbit

Responsive bilingual (English/Bangla) editorial blog hosted on GitHub Pages.

## Image pipeline

Each article gets a topic-specific visual search phrase. When PIXABAY_API_KEY is configured, Pixabay is queried with safe search enabled; its tags refine the visual topic. Pixabay image files are not copied into the public dataset because its license restricts redistribution of standalone content.

The publisher then searches Wikimedia Commons for a matching CC0, CC BY, CC BY-SA, or public-domain image. The selected file and attribution JSON are uploaded to the Hugging Face dataset at https://huggingface.co/datasets/AhyanCreationsLTD/pulseorbit-images. Files are stored under images/ and metadata/ respectively. Posts store the Hugging Face resolve/main URL, used by thumbnails, article hero images and social previews. Creator, source page, license, license URL and retrieval time are retained in dataset metadata and displayed on article pages. If no eligible image is found or HF_TOKEN is missing, a placeholder is used. No downloaded image is saved in the GitHub repository.

## Daily publishing

GitHub Actions runs daily at 07:30 Bangladesh time and generates two explainers using Gemini, validates them, retrieves eligible imagery, updates posts/index.json, builds article pages and the sitemap, then commits generated content.

## Required Actions secrets

- GEMINI_API_KEY — Gemini API key
- HF_TOKEN — Hugging Face token with write permission to the dataset
- PIXABAY_API_KEY — Pixabay API key (optional; Commons search uses the topic directly if absent)

Optional Actions variable: GEMINI_MODEL. The workflow uses dataset ID AhyanCreationsLTD/pulseorbit-images. Keep keys out of frontend code and commits; revoke and replace any exposed key.

Run manually from Actions → PulseOrbit daily publishing → Run workflow.
