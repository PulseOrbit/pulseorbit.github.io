# PulseOrbit

A responsive editorial website hosted on GitHub Pages.

## Daily publishing
- GitHub Actions generates two draft stories each day at 07:30 Bangladesh time.
- Add `GEMINI_API_KEY` under **Settings → Secrets and variables → Actions → New repository secret**.
- The publishing workflow creates crawlable static article pages and refreshes `sitemap.xml`.
- Review factual claims and sources before relying on or sharing an article. Trending-topic discovery alone is not independent reporting.

## Language
The site interface supports English and Bangla. Article text is currently published in English.

## Images
The publisher searches Wikimedia Commons for images and stores attribution and licence information. If no suitable openly licensed image is found, it uses the local placeholder. Check every image licence before reuse.

## Reader counts (optional)
PulseOrbit uses GoatCounter for privacy-friendly per-page view counts.
1. Create a GoatCounter site for `pulseorbit.github.io`.
2. In `assets/js/config.js`, set `window.PULSEORBIT_GOATCOUNTER_URL` to your site's public count endpoint, for example `https://YOUR-CODE.goatcounter.com/count`.
3. Enable **Allow adding visitor counts on your website** in GoatCounter site settings.
4. Commit the config change. View counts will then appear on article pages.
Do not put an API key or private token in this public repository.

## SEO
- Each article has a static URL, canonical URL, Open Graph/Twitter metadata, Article structured data, and is listed in the sitemap.
- `PulseOrbit SEO health check` runs weekly and can also be started manually from Actions.
- Submit `https://pulseorbit.github.io/sitemap.xml` in Google Search Console and Bing Webmaster Tools.
- Search rankings are not guaranteed. Publish accurate, original, useful articles and earn relevant links naturally. Do not use automated link farms, bulk directory submissions, or paid ranking links.

## Contact
support@ahyancreations.top
