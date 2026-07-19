from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+-]*")

STOPWORDS = {
    "a",
    "about",
    "after",
    "all",
    "am",
    "an",
    "and",
    "any",
    "are",
    "as",
    "at",
    "be",
    "by",
    "can",
    "do",
    "does",
    "for",
    "from",
    "get",
    "give",
    "have",
    "how",
    "i",
    "if",
    "in",
    "is",
    "it",
    "loan",
    "loans",
    "me",
    "my",
    "of",
    "on",
    "or",
    "should",
    "that",
    "the",
    "to",
    "what",
    "when",
    "which",
    "with",
    "you",
}

CATEGORY_HINTS = {
    "application_process": {
        "apply",
        "application",
        "online",
        "process",
        "form",
        "submit",
    },
    "compliance_policy": {
        "policy",
        "rbi",
        "moratorium",
        "restructuring",
        "complaint",
        "grievance",
        "regulated",
    },
    "credit_score": {
        "cibil",
        "credit",
        "score",
        "bureau",
    },
    "customer_protection": {
        "fraud",
        "scam",
        "fake",
        "upfront",
        "safe",
        "representative",
        "disbursal",
        "safety",
    },
    "documents": {
        "document",
        "documents",
        "paperwork",
        "kyc",
        "pan",
        "gst",
        "bank",
        "statement",
    },
    "eligibility": {
        "eligible",
        "eligibility",
        "criteria",
        "qualify",
        "turnover",
        "age",
        "vintage",
        "self-employed",
        "professional",
    },
    "fees_and_charges": {
        "fee",
        "fees",
        "charge",
        "charges",
        "processing",
        "interest",
        "rate",
        "foreclosure",
        "prepayment",
        "nach",
        "bounce",
        "penalty",
        "penal",
    },
    "privacy_pii": {
        "privacy",
        "personal",
        "data",
        "information",
        "consent",
        "pii",
    },
    "product_overview": {
        "amount",
        "limit",
        "tenure",
        "collateral",
        "unsecured",
        "business",
        "msme",
    },
    "product_taxonomy": {
        "types",
        "type",
        "variant",
        "working",
        "capital",
        "term",
    },
    "product_variant": {
        "term",
        "working",
        "capital",
        "trader",
        "professional",
        "women",
    },
    "repayment": {
        "repay",
        "repayment",
        "emi",
        "instalment",
        "installment",
        "miss",
        "missed",
        "overdue",
        "due",
        "foreclose",
        "foreclosure",
        "prepay",
    },
}

SUBCATEGORY_HINTS = {
    "processing_fee": {"processing", "fee", "fees"},
    "interest_rate": {"interest", "rate", "apr"},
    "loan_amount": {"amount", "limit", "maximum", "minimum", "lakh", "crore"},
    "loan_tenure": {"tenure", "duration", "months", "years"},
    "documents_required": {"document", "documents", "paperwork", "kyc", "pan", "gst"},
    "cibil_score": {"cibil", "credit", "score"},
    "missed_payment": {"miss", "missed", "late", "overdue", "bounce"},
    "foreclosure_charge": {"foreclosure", "foreclose", "prepayment", "prepay"},
    "loan_fraud_advisory": {"fraud", "scam", "fake", "upfront", "safe", "representative", "disbursal"},
    "privacy": {"privacy", "personal", "data", "consent"},
    "co_lending_partners": {"co-lending", "colending", "co-lenders", "partner", "partners"},
}

SOURCE_TYPE_BOOST = {
    "table": 0.35,
    "pdf": 0.2,
    "webpage": 0.0,
}

QUALITY_BOOST = {
    "approved": 0.3,
    "approved_with_warning": 0.0,
    "needs_review": -0.8,
}


@dataclass(frozen=True)
class ScoredRecord:
    record: dict[str, Any]
    score: float
    score_parts: dict[str, float]


def tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in TOKEN_RE.findall(text)
        if len(token) > 1 and token.lower() not in STOPWORDS
    ]


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def compact_text(text: str, max_words: int = 95) -> str:
    text = re.sub(r"^\s*[-+*]\s+", "", text.strip())
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).rstrip(" ,.;:") + "..."


def infer_query_hints(query_tokens: set[str]) -> tuple[dict[str, float], dict[str, float]]:
    category_scores: dict[str, float] = {}
    for category, hints in CATEGORY_HINTS.items():
        overlap = query_tokens & hints
        if overlap:
            category_scores[category] = min(1.5, 0.45 * len(overlap))

    subcategory_scores: dict[str, float] = {}
    for subcategory, hints in SUBCATEGORY_HINTS.items():
        overlap = query_tokens & hints
        if overlap:
            subcategory_scores[subcategory] = min(1.2, 0.5 * len(overlap))

    return category_scores, subcategory_scores


def citation_from_record(record: dict[str, Any]) -> dict[str, Any]:
    citation = (record.get("citations") or [{}])[0]
    evidence = citation.get("evidence") or record.get("content", {}).get("answer_text", "")
    return {
        "record_id": record.get("id"),
        "label": citation.get("label") or record.get("source", {}).get("source_id"),
        "url": citation.get("url") or record.get("source", {}).get("source_url"),
        "source_id": citation.get("source_id") or record.get("source", {}).get("source_id"),
        "evidence": compact_text(str(evidence), 45),
    }


def citation_relevant_to_subcategory(subcategory: str | None, evidence: str) -> bool:
    if not subcategory:
        return True
    lowered = evidence.lower()
    checks = {
        "processing_fee": ("processing fee", "processing charges"),
        "interest_rate": ("interest rate", "rate of interest"),
        "documents_required": ("document", "kyc", "bank statement"),
        "loan_fraud_advisory": ("fraud", "fake", "suspicious"),
        "missed_payment": ("default", "miss", "late", "overdue", "non-payment"),
        "foreclosure_charge": ("foreclose", "foreclosure", "prepay", "prepayment"),
    }
    terms = checks.get(subcategory)
    if not terms:
        return True
    return any(term in lowered for term in terms)


class KbRetriever:
    def __init__(self, records: list[dict[str, Any]]) -> None:
        if not records:
            raise ValueError("KB retriever received zero records.")
        self.records = records
        self.doc_tokens: list[list[str]] = []
        self.doc_term_counts: list[Counter[str]] = []
        self.doc_lengths: list[int] = []
        self.document_frequency: Counter[str] = Counter()
        self.avg_doc_length = 0.0
        self._build_index()

    @classmethod
    def from_project_root(cls, project_root: Path, kb_path: Path | None = None) -> "KbRetriever":
        path = kb_path or (project_root / "data" / "kb" / "master_kb.jsonl")
        return cls(read_jsonl(path))

    def _record_index_text(self, record: dict[str, Any]) -> str:
        retrieval = record.get("retrieval", {})
        taxonomy = record.get("taxonomy", {})
        content = record.get("content", {})
        source = record.get("source", {})
        pieces = [
            retrieval.get("embedding_text", ""),
            " ".join(retrieval.get("keywords") or []),
            content.get("title", ""),
            taxonomy.get("category", ""),
            taxonomy.get("sub_category", ""),
            taxonomy.get("intent", ""),
            source.get("source_id", ""),
        ]
        return " ".join(str(piece) for piece in pieces if piece)

    def _build_index(self) -> None:
        total_length = 0
        for record in self.records:
            tokens = tokenize(self._record_index_text(record))
            counts = Counter(tokens)
            self.doc_tokens.append(tokens)
            self.doc_term_counts.append(counts)
            self.doc_lengths.append(len(tokens))
            total_length += len(tokens)
            self.document_frequency.update(counts.keys())
        self.avg_doc_length = total_length / max(1, len(self.records))

    def _idf(self, term: str) -> float:
        docs = len(self.records)
        df = self.document_frequency.get(term, 0)
        return math.log(1 + (docs - df + 0.5) / (df + 0.5))

    def _bm25(self, query_tokens: list[str], doc_index: int) -> float:
        k1 = 1.35
        b = 0.75
        doc_len = max(1, self.doc_lengths[doc_index])
        avg_len = max(1.0, self.avg_doc_length)
        counts = self.doc_term_counts[doc_index]
        score = 0.0
        for term in query_tokens:
            tf = counts.get(term, 0)
            if tf == 0:
                continue
            denom = tf + k1 * (1 - b + b * doc_len / avg_len)
            score += self._idf(term) * (tf * (k1 + 1) / denom)
        return score

    def _score_record(
        self,
        query: str,
        query_tokens: list[str],
        query_token_set: set[str],
        record: dict[str, Any],
        doc_index: int,
    ) -> ScoredRecord:
        retrieval = record.get("retrieval", {})
        taxonomy = record.get("taxonomy", {})
        source = record.get("source", {})
        quality = record.get("quality", {})
        content = record.get("content", {})

        bm25 = self._bm25(query_tokens, doc_index)
        record_keywords = set(str(item).lower() for item in retrieval.get("keywords") or [])
        keyword_overlap = 0.25 * len(query_token_set & record_keywords)

        category_hints, subcategory_hints = infer_query_hints(query_token_set)
        category_boost = category_hints.get(taxonomy.get("category"), 0.0)
        subcategory_boost = subcategory_hints.get(taxonomy.get("sub_category"), 0.0)

        lower_query = query.lower()
        answer_text = str(content.get("answer_text", "")).lower()
        title = str(content.get("title", "")).lower()
        exact_phrase = 0.0
        for phrase in (
            "processing fee",
            "interest rate",
            "cibil score",
            "business loan",
            "required documents",
            "documents required",
            "documents are required",
            "loan amount",
            "miss emi",
            "missed emi",
            "co-lending partners",
        ):
            if phrase in lower_query and (phrase in answer_text or phrase in title):
                exact_phrase += 0.75

        special_intent = 0.0
        subcategory = taxonomy.get("sub_category")
        category = taxonomy.get("category")
        source_id = str(source.get("source_id", ""))

        amount_query = bool(query_token_set & {"amount", "limit", "maximum", "minimum", "lakh", "crore"})
        if amount_query and not (query_token_set & {"interest", "rate", "fee", "charge", "charges"}):
            if subcategory == "loan_amount":
                special_intent += 3.0
            if category in {"product_overview", "product_taxonomy"}:
                special_intent += 0.8
            if subcategory == "interest_rate":
                special_intent -= 1.5
            if "interest rate" in answer_text:
                special_intent -= 0.75

        missed_payment_query = bool(query_token_set & {"miss", "missed", "late", "overdue", "bounce", "bounced"})
        if missed_payment_query:
            if subcategory == "missed_payment":
                special_intent += 4.0
            elif subcategory in {"late_payment_charge", "dishonour_charge"}:
                special_intent += 2.0
            if source_id in {"lendingkart_repayment_guide", "lendingkart_schedule_of_charges"}:
                special_intent += 0.8
            if source_id == "lendingkart_emi_calculator":
                special_intent -= 8.0
            if "calculator" in answer_text and not any(term in answer_text for term in ("miss", "late", "overdue", "bounce")):
                special_intent -= 2.5

        direct_fraud_terms = {"fraud", "scam", "fake", "upfront", "disbursal", "safe", "representative"}
        suspicious_payment_terms = {"pay", "money"} <= query_token_set and bool(
            query_token_set & {"before", "upfront", "disbursal", "safe", "representative"}
        )
        fraud_query = bool(query_token_set & direct_fraud_terms) or suspicious_payment_terms
        if fraud_query:
            if subcategory == "loan_fraud_advisory":
                special_intent += 5.0
            if category == "customer_protection":
                special_intent += 2.0
            if source_id == "lendingkart_loan_fraud_advisory":
                special_intent += 2.0
            if category == "credit_score":
                special_intent -= 3.0

        processing_fee_query = {"processing", "fee"} <= query_token_set
        if processing_fee_query:
            if subcategory == "processing_fee":
                special_intent += 3.0
            if source_id in {"lendingkart_faq_application_fees", "lendingkart_schedule_of_charges"}:
                special_intent += 1.2
            if "settlement" in answer_text and source_id == "lendingkart_interest_penalty_policy":
                special_intent -= 4.0

        colending_query = bool(query_token_set & {"co-lending", "colending", "co-lenders", "partners", "partner"})
        if colending_query:
            if subcategory == "co_lending_partners":
                special_intent += 2.5
            if category == "compliance_policy":
                special_intent += 0.8

        documents_query = bool(query_token_set & {"document", "documents", "paperwork", "kyc"})
        privacy_query = bool(query_token_set & {"privacy", "personal", "data", "consent"})
        if documents_query:
            if subcategory == "documents_required":
                special_intent += 4.0
            if category in {"documents", "application_process", "eligibility"}:
                special_intent += 1.0
            if category == "privacy_pii" and not privacy_query:
                special_intent -= 5.0

        metadata_boost = float(retrieval.get("boost") or 1.0) * 0.15
        source_type_boost = SOURCE_TYPE_BOOST.get(str(source.get("source_type", "")), 0.0)
        quality_boost = QUALITY_BOOST.get(str(quality.get("status", "approved")), 0.0)

        parts = {
            "bm25": bm25,
            "keyword_overlap": keyword_overlap,
            "category_boost": category_boost,
            "subcategory_boost": subcategory_boost,
            "exact_phrase": exact_phrase,
            "special_intent": special_intent,
            "metadata_boost": metadata_boost,
            "source_type_boost": source_type_boost,
            "quality_boost": quality_boost,
        }
        total = sum(parts.values())
        return ScoredRecord(record=record, score=round(total, 4), score_parts={k: round(v, 4) for k, v in parts.items()})

    def search(self, query: str, top_k: int = 5) -> list[ScoredRecord]:
        query_tokens = tokenize(query)
        query_token_set = set(query_tokens)
        if not query_tokens:
            return []

        scored = [
            self._score_record(query, query_tokens, query_token_set, record, doc_index)
            for doc_index, record in enumerate(self.records)
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def answer(self, query: str, top_k: int = 5) -> dict[str, Any]:
        results = self.search(query, top_k=top_k)
        if not results:
            return {
                "status": "human_escalation_required",
                "answer": "I could not find enough information in the approved knowledge base. Please connect this caller to a human agent.",
                "reason": "empty_query_or_no_results",
                "citations": [],
                "top_records": [],
            }

        best = results[0]
        top_status = best.record.get("quality", {}).get("status", "approved")
        top_warnings = set(best.record.get("quality", {}).get("warnings") or [])
        score_gap = best.score - results[1].score if len(results) > 1 else best.score
        escalation_reasons: list[str] = []

        if best.score < 2.25:
            escalation_reasons.append("low_retrieval_score")
        if top_status == "needs_review" and score_gap < 1.0:
            escalation_reasons.append("best_source_needs_human_review")
        if "source_value_inconsistency_needs_review" in top_warnings:
            escalation_reasons.append("source_value_inconsistency")

        conflict_count = sum(
            1
            for item in results[:3]
            if "source_value_conflict_preserve_context" in set(item.record.get("quality", {}).get("warnings") or [])
        )
        if conflict_count >= 2:
            escalation_reasons.append("multiple_conflicting_sources")

        best_category = best.record.get("taxonomy", {}).get("category")
        best_subcategory = best.record.get("taxonomy", {}).get("sub_category")
        citations = []
        seen_sources: set[str] = set()
        for item in results[:5]:
            item_taxonomy = item.record.get("taxonomy", {})
            if item is not best:
                if item_taxonomy.get("category") != best_category:
                    continue
                if best_subcategory and item_taxonomy.get("sub_category") != best_subcategory:
                    continue
            citation = citation_from_record(item.record)
            if not citation_relevant_to_subcategory(best_subcategory, str(citation.get("evidence", ""))):
                continue
            source_key = str(citation.get("source_id") or citation.get("url") or citation.get("record_id"))
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)
            citations.append(citation)
            if len(citations) >= 3:
                break

        if escalation_reasons:
            answer_text = (
                "I found related information, but it needs human confirmation before a customer-facing answer. "
                "Please connect this caller to a human agent."
            )
            status = "human_escalation_required"
        else:
            answer_text = compact_text(best.record.get("content", {}).get("answer_text", ""))
            status = "answered"
            if top_status == "approved_with_warning":
                status = "answered_with_caution"

        return {
            "status": status,
            "answer": answer_text,
            "reason": ";".join(escalation_reasons) if escalation_reasons else "sufficient_retrieval_confidence",
            "citations": citations,
            "top_records": [
                {
                    "record_id": item.record.get("id"),
                    "score": item.score,
                    "score_parts": item.score_parts,
                    "category": item.record.get("taxonomy", {}).get("category"),
                    "sub_category": item.record.get("taxonomy", {}).get("sub_category"),
                    "source_id": item.record.get("source", {}).get("source_id"),
                    "source_type": item.record.get("source", {}).get("source_type"),
                    "quality_status": item.record.get("quality", {}).get("status"),
                    "warnings": item.record.get("quality", {}).get("warnings") or [],
                }
                for item in results
            ],
        }


def evaluate(retriever: KbRetriever, questions_path: Path) -> dict[str, Any]:
    questions = read_jsonl(questions_path)
    rows: list[dict[str, Any]] = []
    pass_count = 0
    citation_count = 0
    escalation_count = 0

    for question in questions:
        response = retriever.answer(str(question["question"]), top_k=5)
        top_records = response["top_records"]
        top_categories = [item["category"] for item in top_records[:3]]
        top_subcategories = [item["sub_category"] for item in top_records[:3]]
        expected_category = question.get("expected_category")
        expected_subcategory = question.get("expected_sub_category")

        category_ok = expected_category is None or expected_category in top_categories
        subcategory_ok = expected_subcategory is None or expected_subcategory in top_subcategories
        has_citation = bool(response["citations"])
        ok = category_ok and subcategory_ok and has_citation

        if ok:
            pass_count += 1
        if has_citation:
            citation_count += 1
        if response["status"] == "human_escalation_required":
            escalation_count += 1

        rows.append(
            {
                "id": question.get("id"),
                "question": question.get("question"),
                "expected_category": expected_category,
                "expected_sub_category": expected_subcategory,
                "status": response["status"],
                "top_category": top_records[0]["category"] if top_records else None,
                "top_sub_category": top_records[0]["sub_category"] if top_records else None,
                "top_score": top_records[0]["score"] if top_records else 0,
                "category_in_top3": category_ok,
                "subcategory_in_top3": subcategory_ok,
                "has_citation": has_citation,
                "pass": ok,
                "reason": response["reason"],
                "answer_preview": compact_text(response["answer"], 35),
            }
        )

    return {
        "question_count": len(questions),
        "pass_count": pass_count,
        "citation_count": citation_count,
        "human_escalation_count": escalation_count,
        "pass_rate": round(pass_count / max(1, len(questions)), 3),
        "rows": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retrieve cited answers from the Lendingkart master KB.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--kb", type=Path, default=None, help="Optional path to master_kb.jsonl.")
    parser.add_argument("--query", default=None, help="Customer question to answer.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--eval", type=Path, default=None, help="Optional JSONL smoke-test question file.")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    retriever = KbRetriever.from_project_root(project_root, args.kb)

    payload: dict[str, Any]
    if args.eval:
        payload = evaluate(retriever, args.eval)
    elif args.query:
        payload = retriever.answer(args.query, top_k=args.top_k)
    else:
        raise SystemExit("Provide either --query or --eval.")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
