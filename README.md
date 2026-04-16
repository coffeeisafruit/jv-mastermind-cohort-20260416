# JV Partner Enrichment — Mastermind Cohort

**Internal ops site.** Static, client-side AES-encrypted, served via GitHub Pages.

- **Live site:** https://coffeeisafruit.github.io/jv-mastermind-cohort-20260416/
- **Password:** shared out-of-band with the ops team (ask Joe)
- **Generated from:** `/Users/josephtepe/exa-research/reports/jv-partners-20260416/*-report.md`
- **Source of truth:** Exa research-pro (batch 20260416)

## What's here

- `build.py` — regenerates `site/index.html` from the 15 Exa reports with full non-truncated content
- `site/index.html` — unencrypted HTML (dev preview, **not published**)
- `encrypted/index.html` — staticrypt-encrypted version
- `publish/` — exactly what GitHub Pages serves: `index.html` (encrypted), `.nojekyll`, `robots.txt`

## Regenerate

1. Update source reports in `/Users/josephtepe/exa-research/reports/jv-partners-20260416/`
2. `python3 build.py`
3. `npx staticrypt@latest site/index.html -p "$(awk '{print $2}' .password.txt)" --short -d encrypted`
4. `cp encrypted/index.html publish/index.html`
5. `git add publish && git commit -m "update" && git push`

## Notes

- Encryption is AES-256-GCM (PBKDF2-HMAC-SHA256). Real crypto, not obfuscation.
- `robots.txt` + `<meta name="robots" content="noindex">` keep it out of search indexes.
- `.password.txt` is gitignored. Share the password via 1Password / Slack DM / secure channel.
