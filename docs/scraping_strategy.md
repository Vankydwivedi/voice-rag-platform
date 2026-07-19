# Scraping Strategy

The knowledge base uses an allowlisted source list rather than a broad crawler.
Each URL in `data/sources.json` is an official HDFC Bank page selected for a
specific KB category such as product overview, eligibility, documentation,
fees, compliance, privacy, or human escalation.

Extraction runs in two stages:

1. Static extraction with `requests` and `BeautifulSoup`.
2. Quality checks that flag pages needing rendered extraction.

The scraper saves:

- raw HTML snapshots in `data/raw/`
- extracted tables in `data/raw/tables/`
- cleaned text in `data/cleaned/`
- extraction status in `data/kb/extraction_report.json`
- source traceability in `data/kb/source_manifest.json`
- review notes in `data/kb/source_quality_report.md`

Navigation, headers, footers, scripts, forms, cookie banners, menus, and other
irrelevant blocks are removed before extracting headings, paragraphs, list
items, and tables. Pages with low extracted text, missing expected category
keywords, or missing expected tables are marked as `partial` so they can be
reviewed or rerun with a Playwright fallback.
