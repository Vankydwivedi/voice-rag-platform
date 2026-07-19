from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+-]*")

STOPWORDS = {
    "about",
    "after",
    "also",
    "amount",
    "and",
    "are",
    "based",
    "been",
    "being",
    "between",
    "business",
    "can",
    "for",
    "from",
    "has",
    "have",
    "into",
    "loan",
    "loans",
    "may",
    "more",
    "not",
    "only",
    "other",
    "over",
    "per",
    "such",
    "that",
    "the",
    "their",
    "this",
    "through",
    "with",
    "will",
    "your",
}

SOURCE_LABELS = {
    "lendingkart_business_loan_overview": "Lendingkart Business Loan Overview",
    "lendingkart_check_eligibility_form": "Lendingkart Check Eligibility",
    "lendingkart_eligibility_requirements": "Lendingkart Eligibility Requirements",
    "lendingkart_interest_rate_charges": "Lendingkart Interest Rate and Charges",
    "lendingkart_schedule_of_charges": "Lendingkart Schedule of Charges",
    "lendingkart_faq_hub": "Lendingkart FAQ Hub",
    "lendingkart_faq_businesses_qualify": "Lendingkart Business Qualification FAQ",
    "lendingkart_faq_documents_unsecured": "Lendingkart Documents FAQ",
    "lendingkart_faq_application_online": "Lendingkart Online Application FAQ",
    "lendingkart_faq_application_fees": "Lendingkart Application Fees FAQ",
    "lendingkart_faq_hidden_charges": "Lendingkart Hidden Charges FAQ",
    "lendingkart_faq_interest_rate_min_max": "Lendingkart Interest Rate FAQ",
    "lendingkart_faq_benefits": "Lendingkart Benefits FAQ",
    "lendingkart_faq_self_employed_professionals": "Lendingkart Self-Employed Professionals FAQ",
    "lendingkart_emi_calculator": "Lendingkart EMI Calculator",
    "lendingkart_term_loan": "Lendingkart Term Loan",
    "lendingkart_types_of_business_loans": "Lendingkart Types of Business Loans",
    "lendingkart_repayment_guide": "Lendingkart Repayment Guide",
    "lendingkart_cibil_business_loan": "Lendingkart CIBIL Business Loan Guide",
    "lendingkart_general_terms_conditions": "Lendingkart General Terms and Conditions",
    "lendingkart_privacy_policy": "Lendingkart Privacy Policy",
    "lendingkart_regulatory_disclosures": "Lendingkart Regulatory Disclosures",
    "lendingkart_loan_fraud_advisory": "Lendingkart Loan Fraud Advisory",
    "lendingkart_interest_penalty_policy": "Lendingkart Interest Rate, Penalty, and Charges Policy",
    "lendingkart_operational_risk_policy": "Lendingkart Operational Risk Policy",
    "lendingkart_restructuring_policy_addendum": "Lendingkart Restructuring Policy Addendum",
    "lendingkart_trade_relief_moratorium_policy": "Lendingkart Trade Relief Moratorium Policy",
    "lendingkart_colending_partners": "Lendingkart Co-Lending Partners",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def top_keywords(text: str, category: str, heading: str, limit: int = 18) -> list[str]:
    words = [word.lower() for word in WORD_RE.findall(" ".join([category, heading, text]))]
    counts = Counter(word for word in words if len(word) > 2 and word not in STOPWORDS)
    keywords = [word for word, _count in counts.most_common(limit)]

    required = []
    if category == "fees_and_charges":
        required.extend(["fees", "charges", "interest"])
    elif category == "eligibility":
        required.extend(["eligibility", "turnover", "income"])
    elif category == "repayment":
        required.extend(["emi", "repayment"])
    elif category == "customer_protection":
        required.extend(["fraud", "suspicious", "safety"])
    elif category == "credit_score":
        required.extend(["cibil", "credit"])
    elif category == "documents":
        required.extend(["documents", "kyc"])

    for item in reversed(required):
        if item not in keywords:
            keywords.insert(0, item)
    return keywords[:limit]


def infer_product(category: str, source_id: str, heading: str, text: str) -> str:
    blob = " ".join([source_id, heading, text]).lower()
    if "term" in blob and "loan" in blob:
        return "term_loan"
    if "unsecured" in blob or "collateral-free" in blob or "collateral free" in blob:
        return "unsecured_business_loan"
    if category in {"privacy_pii", "terms", "compliance_policy"}:
        return "policy_or_compliance"
    if category == "credit_score":
        return "credit_assessment"
    if category == "customer_protection":
        return "fraud_and_customer_safety"
    return "business_loan"


def infer_subcategory(category: str, heading: str, text: str) -> str:
    blob = " ".join([heading, text]).lower()
    patterns: list[tuple[str, str]] = [
        ("processing_fee", r"processing fee|processing charges"),
        ("loan_fraud_advisory", r"fraud|suspicious|fake website|cyber crime|upfront"),
        ("co_lending_partners", r"co-lending|co lending|co-lenders|partner"),
        ("privacy", r"privacy|personal data|consent"),
        ("late_payment_charge", r"late payment|penal charge|overdue|miss.*emi"),
        ("foreclosure_charge", r"foreclosure|pre-closure|pre closure"),
        ("nach_charge", r"\bnach\b"),
        ("dishonour_charge", r"dishonou?r|cheque"),
        ("interest_rate", r"interest rate|rate of interest"),
        ("loan_amount", r"loan amount|amount size|amount of loan|loan limit|up to inr|50 lakh|35 lakh|35,00,000"),
        ("loan_tenure", r"tenure"),
        ("turnover", r"turnover|monthly sales"),
        ("age", r"\bage\b|18 to 65|22 and 65"),
        ("entity_type", r"company|proprietorship|llp|self-employed|professionals|traders"),
        ("documents_required", r"documents|required|kyc|bank statement|gst"),
        ("emi_calculation", r"\bemi\b|calculator|formula|principal"),
        ("missed_payment", r"miss.*emi|default|repayment"),
        ("cibil_score", r"cibil|credit score|credit history"),
        ("moratorium_policy", r"moratorium"),
        ("restructuring_policy", r"restructuring"),
    ]
    for label, pattern in patterns:
        if re.search(pattern, blob):
            return label

    heading_slug = re.sub(r"[^a-z0-9]+", "_", heading.lower()).strip("_")
    if heading_slug:
        return heading_slug[:64]
    return category


def infer_intent(category: str, subcategory: str) -> str:
    return f"ask_{subcategory}" if subcategory else f"ask_{category}"


def source_priority_score(source_type: str, priority: str, source_id: str) -> float:
    score = {
        "highest": 1.5,
        "high": 1.3,
        "medium": 1.0,
        "low": 0.8,
    }.get(priority, 1.0)

    if source_type == "table":
        score += 0.2
    elif source_type == "pdf":
        score += 0.1
    if source_id == "lendingkart_schedule_of_charges":
        score += 0.3
    return round(score, 2)


def quality_status(warnings: list[str]) -> tuple[str, str]:
    if any(warning in warnings for warning in {"source_value_inconsistency_needs_review"}):
        return "needs_review", "medium"
    if any(warning in warnings for warning in {"source_value_conflict_preserve_context", "thin_cleaned_text_after_noise_removal"}):
        return "approved_with_warning", "medium"
    return "approved", "high"


def citation_label(source_id: str) -> str:
    return SOURCE_LABELS.get(source_id, source_id.replace("_", " ").title())


def build_record(clean_row: dict[str, Any], kb_version: str, created_at: str) -> dict[str, Any]:
    category = clean_row["taxonomy"]["category"]
    heading = clean_row["taxonomy"].get("heading") or clean_row["content"].get("title") or ""
    text = clean_row["content"]["text"]
    source = clean_row["source"]
    warnings = list(clean_row.get("quality", {}).get("warnings", []))
    priority = clean_row.get("quality", {}).get("priority", "medium")
    source_type = source.get("source_type", clean_row.get("chunk_type"))
    source_id = source.get("source_id")
    subcategory = infer_subcategory(category, heading, text)
    intent = infer_intent(category, subcategory)
    keywords = top_keywords(text, category, heading)
    status, confidence = quality_status(warnings)
    boost = source_priority_score(source_type, priority, source_id)
    record_seed = "|".join([clean_row["id"], kb_version, clean_row["hashes"]["chunk_content_hash"]])
    record_id = "kb_" + clean_row["id"].replace("clean_", "")

    source_url = source.get("source_url", "")
    record = {
        "id": record_id,
        "kb_version": kb_version,
        "record_type": "knowledge_chunk",
        "provider": clean_row.get("provider", "lendingkart"),
        "business_domain": clean_row.get("business_domain", "business_loans"),
        "country": clean_row.get("country", "india"),
        "language": clean_row.get("language", "en"),
        "product": infer_product(category, source_id, heading, text),
        "taxonomy": {
            "domain": clean_row.get("business_domain", "business_loans"),
            "category": category,
            "sub_category": subcategory,
            "intent": intent,
            "heading": heading,
        },
        "content": {
            "title": clean_row["content"].get("title", heading),
            "answer_text": text,
            "raw_evidence": text,
        },
        "source": {
            "source_id": source_id,
            "source_type": source_type,
            "source_url": source_url,
            "source_file": source.get("source_file", ""),
            "clean_chunk_id": clean_row["id"],
        },
        "quality": {
            "status": status,
            "confidence": confidence,
            "source_priority": priority,
            "needs_human_review": status == "needs_review",
            "warnings": warnings,
            "pii_masks": clean_row.get("quality", {}).get("pii_masks", {}),
        },
        "retrieval": {
            "keywords": keywords,
            "embedding_text": " ".join([category, subcategory, heading, text]),
            "metadata_filters": {
                "provider": clean_row.get("provider", "lendingkart"),
                "country": clean_row.get("country", "india"),
                "product": infer_product(category, source_id, heading, text),
                "category": category,
                "source_type": source_type,
                "confidence": confidence,
            },
            "boost": boost,
        },
        "versioning": {
            "created_at_utc": created_at,
            "source_content_hash": clean_row.get("hashes", {}).get("normalized_text_hash"),
            "record_hash": None,
            "supersedes_record_id": None,
            "is_current": True,
        },
        "citations": [
            {
                "label": citation_label(source_id),
                "url": source_url,
                "source_id": source_id,
                "evidence": text[:280],
            }
        ],
    }
    record["versioning"]["record_hash"] = "rec_" + hash_record(record_seed + json.dumps(record, ensure_ascii=False, sort_keys=True))
    return record


def hash_record(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:12]


def schema() -> dict[str, Any]:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Lendingkart Master KB Record",
        "type": "object",
        "required": [
            "id",
            "kb_version",
            "record_type",
            "provider",
            "business_domain",
            "country",
            "language",
            "product",
            "taxonomy",
            "content",
            "source",
            "quality",
            "retrieval",
            "versioning",
            "citations",
        ],
        "properties": {
            "id": {"type": "string"},
            "kb_version": {"type": "string"},
            "record_type": {"const": "knowledge_chunk"},
            "provider": {"type": "string"},
            "business_domain": {"type": "string"},
            "country": {"type": "string"},
            "language": {"type": "string"},
            "product": {"type": "string"},
            "taxonomy": {
                "type": "object",
                "required": ["domain", "category", "sub_category", "intent", "heading"],
                "properties": {
                    "domain": {"type": "string"},
                    "category": {"type": "string"},
                    "sub_category": {"type": "string"},
                    "intent": {"type": "string"},
                    "heading": {"type": "string"},
                },
            },
            "content": {
                "type": "object",
                "required": ["title", "answer_text", "raw_evidence"],
                "properties": {
                    "title": {"type": "string"},
                    "answer_text": {"type": "string"},
                    "raw_evidence": {"type": "string"},
                },
            },
            "source": {
                "type": "object",
                "required": ["source_id", "source_type", "source_url", "source_file", "clean_chunk_id"],
                "properties": {
                    "source_id": {"type": "string"},
                    "source_type": {"type": "string"},
                    "source_url": {"type": "string"},
                    "source_file": {"type": "string"},
                    "clean_chunk_id": {"type": "string"},
                },
            },
            "quality": {"type": "object"},
            "retrieval": {"type": "object"},
            "versioning": {"type": "object"},
            "citations": {"type": "array"},
        },
    }


def write_report(path: Path, records: list[dict[str, Any]], source_path: Path, output_paths: dict[str, str]) -> None:
    category_counts = Counter(record["taxonomy"]["category"] for record in records)
    source_type_counts = Counter(record["source"]["source_type"] for record in records)
    status_counts = Counter(record["quality"]["status"] for record in records)
    confidence_counts = Counter(record["quality"]["confidence"] for record in records)
    warning_counts: Counter[str] = Counter()
    for record in records:
        warning_counts.update(record["quality"].get("warnings", []))

    lines = [
        "# Master KB Build Report",
        "",
        f"Generated at UTC: {utc_now()}",
        "",
        "## Summary",
        "",
        f"- Source chunks file: `{source_path}`",
        f"- Master KB records: {len(records)}",
        f"- Output: `{output_paths['master_kb_jsonl']}`",
        f"- Schema: `{output_paths['schema_json']}`",
        f"- Sample records: `{output_paths['sample_jsonl']}`",
        "",
        "## Records By Source Type",
        "",
    ]
    for key, value in sorted(source_type_counts.items()):
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Records By Category", ""])
    for key, value in category_counts.most_common():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Quality Status", ""])
    for key, value in sorted(status_counts.items()):
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Confidence", ""])
    for key, value in sorted(confidence_counts.items()):
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Warning Counts", ""])
    if warning_counts:
        for key, value in warning_counts.most_common():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "## Retrieval Design Encoded In Records",
            "",
            "- `retrieval.keywords` supports exact keyword/BM25 matching.",
            "- `retrieval.embedding_text` is the text that can be embedded later for vector search.",
            "- `retrieval.metadata_filters` allows filtering by provider, country, product, category, source type, and confidence.",
            "- `retrieval.boost` gives higher rank to stronger sources such as tables and official policy PDFs.",
            "",
            "## Citation Design Encoded In Records",
            "",
            "Each record has a `citations` array with source label, URL, source id, and short evidence excerpt.",
            "The answer layer should cite the highest-ranked record used for the response.",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def choose_sample(records: list[dict[str, Any]], limit: int = 12) -> list[dict[str, Any]]:
    desired = [
        ("fees_and_charges", "processing_fee"),
        ("fees_and_charges", "late_payment_charge"),
        ("eligibility", "turnover"),
        ("documents", "documents_required"),
        ("repayment", "emi_calculation"),
        ("credit_score", "cibil_score"),
        ("customer_protection", "loan_fraud_advisory"),
        ("compliance_policy", "co_lending_partners"),
        ("privacy_pii", "privacy"),
    ]
    samples: list[dict[str, Any]] = []
    used_ids = set()
    for category, subcategory in desired:
        for record in records:
            if record["id"] in used_ids:
                continue
            if record["taxonomy"]["category"] == category and record["taxonomy"]["sub_category"] == subcategory:
                samples.append(record)
                used_ids.add(record["id"])
                break

    for record in records:
        if len(samples) >= limit:
            break
        if record["id"] not in used_ids:
            samples.append(record)
            used_ids.add(record["id"])
    return samples[:limit]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build final master KB JSONL from approved clean chunks.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--kb-version", default="lendingkart_business_loans_v0.1")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    kb_dir = project_root / "data" / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    input_path = args.input or (kb_dir / "approved_clean_chunks.jsonl")
    clean_rows = read_jsonl(input_path)
    created_at = utc_now()
    records = [build_record(row, args.kb_version, created_at) for row in clean_rows]

    master_path = kb_dir / "master_kb.jsonl"
    schema_path = kb_dir / "master_kb_schema.json"
    sample_path = kb_dir / "master_kb_sample_records.jsonl"
    report_json_path = kb_dir / "master_kb_report.json"
    report_md_path = kb_dir / "master_kb_report.md"

    write_jsonl(master_path, records)
    schema_path.write_text(json.dumps(schema(), indent=2, ensure_ascii=False), encoding="utf-8")
    samples = choose_sample(records)
    write_jsonl(sample_path, samples)

    report = {
        "generated_at_utc": created_at,
        "kb_version": args.kb_version,
        "source_chunks": str(input_path),
        "record_count": len(records),
        "source_type_counts": dict(Counter(record["source"]["source_type"] for record in records)),
        "category_counts": dict(Counter(record["taxonomy"]["category"] for record in records)),
        "quality_status_counts": dict(Counter(record["quality"]["status"] for record in records)),
        "confidence_counts": dict(Counter(record["quality"]["confidence"] for record in records)),
        "outputs": {
            "master_kb_jsonl": str(master_path),
            "schema_json": str(schema_path),
            "sample_jsonl": str(sample_path),
            "report_json": str(report_json_path),
            "report_md": str(report_md_path),
        },
    }
    report_json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_report(report_md_path, records, input_path, report["outputs"])

    print(
        "master_records={0} samples={1} categories={2}".format(
            len(records),
            len(samples),
            len(report["category_counts"]),
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
