# Cleaning Rules

These rules run after extraction and before `master_kb.jsonl` generation.

## Input Control

The cleaner reads only `data/kb/source_allowlist.json`.

It excludes unlisted files by default. This prevents old HDFC files, corporate archive PDFs, external PDFs, and zero-text documents from entering the Lendingkart KB.

## Navigation And Repeated Content

The cleaner removes known repeated sections:

- Home
- Blogs
- Related Posts
- Recent Posts
- Trending Posts
- Categories
- Subscribe To Our Newsletter
- Apply for Business Loan
- Apply for Business Loan Now
- Lodge a Complaint

For blog/FAQ pages, once a related/recent/trending-post section begins, the cleaner stops reading the remaining page because later text is usually sidebar or footer noise.

For parsed PDFs and DOCX-derived PDFs, the cleaner also removes extraction boilerplate:

- `--- page N ---` markers,
- page-number footers such as `1 | Page Classification: Internal`,
- standalone classification lines,
- `Page N of M` footer text.

## Extraction Failure Flags

The cleaner flags:

- thin cleaned text after noise removal,
- blocked/forbidden text,
- 404-style titles,
- empty tables,
- source value conflicts,
- source value inconsistencies,
- PII masking events.

Thin source pages can still be allowed when a better linked table or PDF exists. Example: the fraud advisory landing page is thin, but the downloaded fraud advisory PDF is approved.

## Duplicate Handling

The cleaner removes:

- exact duplicate chunks by normalized text hash,
- near duplicates by token Jaccard similarity within the same category.

It does not merge conflicting values. Conflicting evidence remains as separate chunks with warning metadata so retrieval can prefer stronger sources.

## Standardization

The cleaner normalizes:

- garbled rupee symbols and `Rs.` variants to `INR`,
- Lending Kart and LendingKart to `Lendingkart`,
- `installment` to `instalment`,
- smart dashes/quotes to ASCII punctuation,
- obvious extracted typo `Customsed` to `Customised`,
- `Upto` to `Up to`,
- clear posted dates to ISO format metadata.

## PII Protection

The cleaner masks:

- email addresses,
- phone numbers,
- PAN numbers,
- Aadhaar numbers,
- GSTIN,
- IFSC,
- bank account numbers when written in account-number context.

Official company URLs and public policy URLs may remain because they are citation sources, not customer PII.

## Outputs

The cleaner writes:

- `data/kb/approved_clean_chunks.jsonl`
- `data/kb/cleaning_report.json`
- `data/kb/cleaning_report.md`

The final `master_kb.jsonl` should be built only from `approved_clean_chunks.jsonl`.
