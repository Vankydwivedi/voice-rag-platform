# Retrieval, Ranking, And Citation Design

This layer answers from `data/kb/master_kb.jsonl`. It does not invent answers outside approved KB records.

## Indexing Approach

Current implementation: local in-memory BM25-style keyword index.

Input fields:

- `retrieval.embedding_text`
- `retrieval.keywords`
- `content.title`
- `taxonomy.category`
- `taxonomy.sub_category`
- `taxonomy.intent`
- `source.source_id`

The master KB already stores `retrieval.embedding_text`, so a vector index can be added later without changing the KB schema. For the first submission, keyword/BM25 is safer and easier to audit than a broad vector database.

## Ranking Logic

Each result receives a combined score:

- BM25 score over the record index text,
- exact keyword overlap with `retrieval.keywords`,
- category hint boost from the user query,
- sub-category hint boost from the user query,
- exact phrase boost for common questions such as processing fee, interest rate, CIBIL score, and required documents,
- source metadata boost from the master KB,
- source-type boost for tables and official PDFs,
- quality boost or penalty from `quality.status`.

The ranker prefers:

- official tables for exact values,
- official policy PDFs for compliance and policy questions,
- clean high-confidence webpages for user-facing explanations,
- approved records over records marked `needs_review`.

## Human Escalation

The answer layer returns `human_escalation_required` when:

- the best retrieval score is too low,
- the best record is marked `needs_review` and other results are close,
- the best evidence has a source inconsistency warning,
- multiple top records carry value-conflict warnings.

This keeps unclear or conflicting answers out of the voice bot.

## Citation Method

Each answer includes citations from the top records:

- `record_id`
- source label,
- source URL,
- source id,
- short evidence excerpt.

The voice agent should use the citation internally for grounding. For customer-facing voice, it can say a short source phrase such as "based on Lendingkart's schedule of charges" when needed.

## Vector Search Plan

Vector search is optional for this phase. If added later:

- embed only `retrieval.embedding_text`,
- keep metadata filters from `retrieval.metadata_filters`,
- retrieve vector top-k,
- merge with BM25 top-k,
- rerank using the same quality, source, warning, and citation rules,
- still escalate when confidence is weak or sources conflict.

Vector search should not be a separate broad database. It should be an index over the same approved master KB records.

## Smoke Test

Smoke questions live in `data/evaluation/retrieval_smoke_questions.jsonl`.

Run:

```powershell
python src\kb\retriever.py --project-root . --eval data\evaluation\retrieval_smoke_questions.jsonl --output data\evaluation\retrieval_smoke_results.json
```

The test checks whether the expected category and sub-category appear in the top three retrieved records and whether a citation is present.

Latest run:

- questions: 12
- passed: 12
- pass rate: 1.0
- cited answers: 12
- human escalations during smoke test: 0

Result file:

- `data/evaluation/retrieval_smoke_results.json`
