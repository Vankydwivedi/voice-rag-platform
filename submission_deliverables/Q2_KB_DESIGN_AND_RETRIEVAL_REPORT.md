# Q2 Knowledge Base Design And Retrieval Report

## Objective

Question 2 asks for a production-ready knowledge base from mixed business content. The final KB must be structured, searchable, traceable, and usable by the Q1 voice agent.

This implementation builds a Lendingkart business-loan KB with 257 JSONL records.

Canonical file:

```text
data/kb/master_kb.jsonl
```

## Source Strategy

The KB uses an explicit allowlist:

```text
data/kb/source_allowlist.json
```

Why:

- It prevents unrelated HDFC experiments, external bank documents, archive-only filings, or extraction failures from silently entering the bot.
- It keeps the bot grounded in one business domain.
- It makes source inclusion explainable.

Allowed source types include:

- Lendingkart product and marketing pages.
- Eligibility and application pages.
- FAQ and explainer pages.
- Extracted HTML tables.
- Downloaded official documents and policy PDFs where relevant.

Document acquisition evidence:

- 24 official downloadable document candidates found.
- 24 official documents downloaded.
- 21 of 24 document files produced extractable text.
- 3 archive-only PDFs produced zero text and were flagged instead of used.

## Extraction And Parsing

Website extraction:

- HTML pages were fetched and parsed with BeautifulSoup.
- Main content was extracted from readable page sections.
- Table data was separately preserved as CSV-like records.
- Blocked, thin, or failed pages were recorded instead of accepted.

Document parsing:

- Downloaded PDFs were parsed into text files.
- Text extraction failures were flagged.
- Archive-only/corporate filings were downloaded for evidence but not promoted into customer-facing answers unless relevant.

Why this approach:

- Website text gives user-facing explanations.
- Tables preserve exact charges, amounts, and structured eligibility fields.
- PDFs/policies provide compliance and customer-protection evidence.

## Cleaning Rules

Cleaning removes:

- Navigation text.
- Headers and footers.
- Repeated related-post sections.
- Newsletter and marketing boilerplate.
- Page-number footers.
- Extraction markers.
- Duplicate and near-duplicate chunks.

Standardization includes:

- Rupee and INR formatting.
- Lendingkart spelling normalization.
- `installment` to `instalment` where consistent with source wording.
- Common typos such as `Customsed` to `Customised`.
- Dates into metadata where possible.

PII protection masks:

- Email addresses.
- Phone numbers.
- PAN.
- Aadhaar.
- GSTIN.
- IFSC.
- Bank account numbers when written in account-number context.

Why this matters:

- Voice agents repeat answers. If the KB contains footer noise, duplicate fragments, or PII, the bot can leak or cite bad content.
- Cleaning before indexing is safer than asking the model to ignore bad text later.

## Master Record Schema

Each KB record includes:

```json
{
  "id": "kb_lendingkart_business_loan_overview_001",
  "record_type": "knowledge_chunk",
  "content": {
    "title": "Business loan amount",
    "answer_text": "Loan Amount: Up to INR 50 Lakh business loan"
  },
  "taxonomy": {
    "category": "product_overview",
    "sub_category": "loan_amount",
    "intent": "answer_product_question"
  },
  "source": {
    "source_id": "lendingkart_business_loan_overview",
    "source_url": "https://www.lendingkart.com/business-loans/",
    "source_type": "webpage"
  },
  "retrieval": {
    "embedding_text": "Business loan amount ...",
    "keywords": ["loan amount", "business loan", "INR 50 lakh"]
  },
  "quality": {
    "status": "approved",
    "warnings": []
  },
  "citations": [
    {
      "label": "Lendingkart business loan overview",
      "url": "https://www.lendingkart.com/business-loans/"
    }
  ],
  "versioning": {
    "kb_version": "v1",
    "record_hash": "rec_..."
  }
}
```

## KB Size And Taxonomy

Current record count:

- Total records: 257
- Approved: 238
- Approved with warning: 14
- Needs review: 5

Category counts:

| Category | Records |
| --- | ---: |
| fees_and_charges | 50 |
| repayment | 45 |
| compliance_policy | 30 |
| product_variant | 24 |
| product_overview | 22 |
| credit_score | 22 |
| privacy_pii | 22 |
| eligibility | 17 |
| product_taxonomy | 11 |
| terms | 7 |
| application_process | 3 |
| documents | 1 |
| faq | 1 |
| objection_handling | 1 |
| customer_protection | 1 |

## Chunking Strategy

Chunking rules:

- Keep exact fee rows and table values as small standalone chunks.
- Keep policy/explainer content in topic-sized chunks.
- Split long pages by semantic headings, not arbitrary token count alone.
- Preserve source context in every chunk.
- Do not merge conflicting values from different sources.

Why:

- A voice bot needs short, answerable facts.
- Charges and eligibility values must be cited precisely.
- Conflicting records should be visible to ranking and escalation logic.

Future improvement:

- Add automatic chunk-size validation by token count.
- Add richer conflict groups for amount, tenure, interest rate, and fees.
- Add human review workflow for `needs_review` records.

## Retrieval And Ranking

Current retrieval method:

- Local in-memory BM25-style keyword index.
- Keyword overlap.
- Category and sub-category boosts.
- Exact phrase boosts for high-value finance terms.
- Source-type and quality-status boosts.
- Warnings can reduce confidence.

Why this instead of vector-only retrieval:

- Exact terms matter in lending.
- BM25 makes retrieval mistakes easier to inspect.
- It keeps evaluation deterministic.
- It does not require a running vector database.

Vector plan:

- Add embeddings over `retrieval.embedding_text`.
- Keep JSONL as source of truth.
- Use vector search as an index, not a separate knowledge source.
- Merge vector top-k and BM25 top-k.
- Rerank with source quality, category, and warnings.
- Escalate when confidence or source consistency is weak.

## Citation Method

Every answer returns citations with:

- Record ID.
- Source label.
- Source URL.
- Source ID.
- Short evidence excerpt.

For voice, citations are kept in metadata and can be summarized verbally when useful. The important point is that the answer can be audited back to a KB record.

## Retrieval Test Results

Result file:

```text
data/evaluation/retrieval_smoke_results.json
```

Latest run:

- Questions: 12
- Passed: 12
- Citation count: 12
- Human escalation count: 0
- Pass rate: 1.0

Coverage:

- Product question: loan amount.
- Policy/compliance question: privacy and co-lending partners.
- Qualification question: self-employed professionals.
- FAQ/application question: online application.
- Objection/safety question: upfront payment/fraud advisory.
- Charges question: processing fee and interest rate.
- Repayment question: missed EMI and foreclosure.

Known issue:

- Some retrieved answers are technically grounded but verbose because the underlying source chunk is policy-like. The voice layer shortens them for callers.

