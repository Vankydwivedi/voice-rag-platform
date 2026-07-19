# Source Allowlist Decisions

This document records the source-selection rules for the Lendingkart KB cleaning stage.

## Decision

The KB cleaner must read from `data/kb/source_allowlist.json` and must ignore any source that is not explicitly listed there.

This prevents accidental mixing of:

- old HDFC extraction leftovers,
- external linked documents,
- Lendingkart corporate archive PDFs,
- zero-text scanned PDFs,
- repeated website navigation and blog-sidebar noise.

## Allowed Inputs

The allowlist approves three input groups:

1. Lendingkart webpage extractions from the active `data/sources.json`.
2. Seven extracted Lendingkart CSV tables from `data/raw/tables/`.
3. Six high/medium relevance downloaded PDF text files from `data/cleaned/documents/`.

The highest-priority source for exact fees and charges is:

- `data/raw/tables/lendingkart_schedule_of_charges_table_01.csv`

The highest-priority source for fraud/suspicious-call guidance is:

- `data/cleaned/documents/Loan_Fraud_Advisory__a1560d24c151.txt`

## Excluded Inputs

The cleaner must exclude:

- `hdfc_*.txt` and `hdfc_*.html` files because the current KB is Lendingkart-only.
- `lendingkart_homepage` because the extraction is too thin and mostly navigation/positioning.
- Annual report, AGM, EGM, MGT-7, CSR, and shareholder PDFs because they are corporate archive material.
- The external CSB Bank CKYC PDF because it is outside Lendingkart-owned domains.
- Downloaded PDFs that produced zero extractable text.
- Repeated page sections such as related posts, recent posts, trending posts, newsletter blocks, category blocks, and generic CTAs.

## Conflict Handling

Some Lendingkart sources disagree on values such as processing fee, loan amount, interest-rate starting point, and tenure.

The cleaner must not deduplicate or merge those into one flattened answer. It should keep them as separate evidence chunks and add a warning so the retrieval layer can prefer higher-priority sources.

For charge-specific questions, the ranking layer should prefer:

1. official schedule-of-charges table,
2. official charge/interest policy PDF,
3. product page,
4. FAQ/blog text.

## PII Handling

Customer PII must be masked before KB creation. This includes phone numbers, emails, PAN, Aadhaar, bank account numbers, IFSC, GSTIN, and personal addresses.

Public official company URLs and public compliance disclosures may remain when they are useful as citations.
