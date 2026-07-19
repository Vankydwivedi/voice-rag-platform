# Document Acquisition Summary

Generated from the Lendingkart scrape on 2026-07-17.

## What was added

- Scanned 24 saved raw HTML pages from the active Lendingkart source list.
- Parsed 5,048 links from those pages.
- Found 24 official/allowed downloadable document candidates.
- Downloaded all 24 official documents into `data/raw/documents/`.
- Parsed PDF text for 21 of the 24 downloaded documents into `data/cleaned/documents/`.
- Recorded 1 external document candidate from `www.csb.bank.in` but skipped it by default because it is outside the Lendingkart-owned domains.

## Current volume

- Raw downloaded documents: 24 files, 161,247,374 bytes.
- Extracted document text: 21 files, 506,303 text characters reported by the parser.
- Extracted cleaned-document files on disk: 535,826 bytes including metadata headers.

## Relevance split

- High relevance: 2 files.
- Medium relevance: 4 files.
- Archive-only/corporate filings: 18 files.

High and medium relevance files should be reviewed for the master KB. Archive-only documents were still downloaded to prove broad extraction/document parsing, but they should not be promoted into the customer-facing bot KB unless a specific assessment section needs corporate evidence.

## High-value files

- `Loan_Fraud_Advisory.pdf`: customer protection and fraud-awareness material.
- `Policy-on-Interest-Rate-Penalties-and-Other-Charges_website_version_v20260616.docx.pdf`: interest-rate, penalty, and charge policy material.

## Medium-value files

- `Addendum-to-Policy-for-Restructuring-of-Advances-3.pdf`
- `Operational-Risk-and-Operational-Resilience-Document-with-Updated-Date.pdf`
- `Trade-relief-Moratorium-Policy-Website.pdf`
- `List-of-Active-Colending-Partners-1.pdf`

## Extraction issues

Three downloaded archive-only PDFs produced zero extractable text:

- `LTPL_Notice-of-11th-AGM.pdf`
- `Notice-of-Annual-General-Meeting-LTPL-1.pdf`
- `Annual-Report-2019.pdf`

These are likely scanned/image-heavy PDFs or otherwise not text-extractable through normal PDF parsing. They should be treated as extraction-failure examples and not used in the master KB.

## Generated reports

- `data/kb/download_candidates.json`
- `data/kb/download_candidates.md`
- `data/kb/download_candidates_external_skipped.json`
- `data/kb/download_report.json`
- `data/kb/download_report.md`
