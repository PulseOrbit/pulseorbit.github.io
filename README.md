# PulseOrbit

A responsive editorial blog published with GitHub Pages and automated daily publishing.

## Website
- URL: https://pulseorbit.github.io
- Responsive layout, category filters, search, article reader, and light/dark theme.
- Article data is stored in `posts/index.json`.

## Enable GitHub Pages
1. Open **Settings → Pages**.
2. Select **Deploy from a branch**.
3. Choose branch **main** and folder **/(root)**, then save.

## Configure AI publishing
1. Open **Settings → Secrets and variables → Actions**.
2. Add a repository secret named `GEMINI_API_KEY` containing a Gemini API key.
3. Optional: add an Actions variable named `GEMINI_MODEL` to pin a model that your API key supports and that supports `generateContent`. If omitted, the publisher discovers available models and chooses a preferred current Flash model automatically.
4. Open **Actions → PulseOrbit daily publishing** and run it manually to test.

The schedule is 01:30 UTC (07:30 Bangladesh time). Each successful run attempts to publish exactly two distinct articles. If it cannot create two sufficiently complete articles, it stops rather than publishing filler.

## AI model selection and troubleshooting
The publisher first calls the Gemini models list endpoint and selects a model available to the configured key that supports `generateContent`. It prefers current Flash models and reports the HTTP status and API error message if model discovery or generation fails.

- HTTP 400: inspect the request or model response details in the Actions log.
- HTTP 401/403: verify the API key, project access and API availability.
- HTTP 404: verify that the selected model is available to this key and supports `generateContent`; remove an optional `GEMINI_MODEL` variable to use automatic discovery.
- HTTP 429: the API quota or rate limit was reached; check the provider's quota page and retry later.

Never place API keys in source files or commit them to Git.

## Images and attribution
The publisher searches Wikimedia Commons for a topic-related image and stores the image page, creator and license metadata. If no suitable openly licensed image is found, the article uses a local abstract placeholder. Retain image attribution and license links.

## Editorial note
Trend discovery is not independent fact verification. Review source links and generated articles before relying on or sharing factual claims. AI output can contain errors.
