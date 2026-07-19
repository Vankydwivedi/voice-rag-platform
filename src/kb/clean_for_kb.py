from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SPACE_RE = re.compile(r"[ \t\r\f\v]+")
WORD_RE = re.compile(r"[a-z0-9]+")

SECTION_BREAK_HEADINGS = {
    "related posts",
    "recent posts",
    "trending posts",
    "categories",
    "subscribe to our newsletter",
}

DROP_LINE_TEXT = {
    "",
    "...",
    "home",
    "blogs",
    "apply for business loan",
    "apply for business loan now",
    "lodge a complaint",
    "by lendingkart",
}

MONTHS = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}

TAXONOMY_MAP = {
    "application_process": "application_process",
    "compliance": "compliance_policy",
    "compliance_policy": "compliance_policy",
    "credit_score": "credit_score",
    "customer_protection": "customer_protection",
    "documents": "documents",
    "eligibility": "eligibility",
    "faq": "faq",
    "fees": "fees_and_charges",
    "fees_and_charges": "fees_and_charges",
    "fraud_advisory": "customer_protection",
    "objection_handling": "objection_handling",
    "privacy_pii": "privacy_pii",
    "product_overview": "product_overview",
    "product_taxonomy": "product_taxonomy",
    "product_variant": "product_variant",
    "repayment": "repayment",
    "terms": "terms",
}

PRIORITY_SCORE = {
    "highest": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
}

SOURCE_TYPE_SCORE = {
    "table": 4,
    "pdf": 3,
    "webpage": 2,
}


@dataclass
class Chunk:
    id: str
    source_id: str
    source_type: str
    source_url: str
    source_file: str
    category: str
    priority: str
    title: str
    heading: str
    text: str
    raw_text: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    pii_masks: dict[str, int] = field(default_factory=dict)
    normalized_hash: str = ""
    token_fingerprint: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_short(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:length]


def normalize_space(value: str) -> str:
    value = value.replace("\u00a0", " ")
    return SPACE_RE.sub(" ", value).strip()


def normalize_heading(value: str) -> str:
    value = value.strip().lstrip("#").strip()
    value = normalize_text(value)
    if not value:
        return ""
    keep_upper = {"EMI", "KYC", "PAN", "GST", "GSTIN", "CIBIL", "MSME", "FAQ", "NACH", "BPI", "RBI"}
    words = []
    for word in value.split():
        clean = re.sub(r"[^A-Za-z0-9]", "", word)
        if clean.upper() in keep_upper:
            words.append(word.upper())
        elif word.isupper() and len(word) <= 4:
            words.append(word)
        else:
            words.append(word[:1].upper() + word[1:].lower())
    return " ".join(words)


def fix_mojibake(value: str) -> tuple[str, bool]:
    original = value
    replacements = {
        "â‚¹": "INR ",
        "Ã¢â€šÂ¹": "INR ",
        "₹": "INR ",
        "â€“": "-",
        "â€”": "-",
        "–": "-",
        "—": "-",
        "â€˜": "'",
        "â€™": "'",
        "‘": "'",
        "’": "'",
        "â€œ": '"',
        "â€": '"',
        "“": '"',
        "”": '"',
        "â€": '"',
        "Â": "",
        "\ufeff": "",
    }
    for bad, good in replacements.items():
        value = value.replace(bad, good)
    return value, value != original


def normalize_text(value: str) -> str:
    value, _ = fix_mojibake(value)
    value = value.replace("Lending Kart", "Lendingkart")
    value = value.replace("LendingKart", "Lendingkart")
    value = value.replace("Customsed", "Customised")
    value = value.replace("customsed", "customised")
    value = value.replace("Upto", "Up to")
    value = value.replace("upto", "up to")
    value = value.replace("installment", "instalment")
    value = value.replace("Installment", "Instalment")
    value = re.sub(r"\bRs\.?\s*", "INR ", value, flags=re.IGNORECASE)
    value = re.sub(r"\bINR\s+", "INR ", value, flags=re.IGNORECASE)
    value = re.sub(r"\s+([,.;:!?])", r"\1", value)
    value = normalize_space(value)
    return value


def parse_iso_date(line: str) -> str | None:
    match = re.search(r"Posted on:\s*([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})", line, flags=re.IGNORECASE)
    if not match:
        return None
    month = MONTHS.get(match.group(1).lower())
    if not month:
        return None
    return f"{match.group(3)}-{month}-{int(match.group(2)):02d}"


def mask_pii(text: str) -> tuple[str, dict[str, int]]:
    counts: Counter[str] = Counter()

    patterns: list[tuple[str, str, str]] = [
        ("email", r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[REDACTED_EMAIL]"),
        ("pan", r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "[REDACTED_PAN]"),
        ("gstin", r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b", "[REDACTED_GSTIN]"),
        ("ifsc", r"\b[A-Z]{4}0[A-Z0-9]{6}\b", "[REDACTED_IFSC]"),
        ("aadhaar", r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[REDACTED_AADHAAR]"),
        ("phone_number", r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)", "[REDACTED_PHONE]"),
    ]

    for label, pattern, replacement in patterns:
        text, count = re.subn(pattern, replacement, text, flags=re.IGNORECASE)
        if count:
            counts[label] += count

    account_pattern = re.compile(
        r"\b((?:account|a/c|acct|bank account)(?:\s*(?:no|number|#))?\s*[:.-]?\s*)(\d{9,18})\b",
        flags=re.IGNORECASE,
    )

    def replace_account(match: re.Match[str]) -> str:
        counts["bank_account_number"] += 1
        return match.group(1) + "[REDACTED_BANK_ACCOUNT]"

    text = account_pattern.sub(replace_account, text)
    return text, dict(counts)


def token_fingerprint(text: str) -> str:
    words = WORD_RE.findall(text.lower())
    words = [word for word in words if len(word) > 2]
    return " ".join(words)


def exact_hash(text: str) -> str:
    return sha256_short(token_fingerprint(text), length=16)


def jaccard(a: str, b: str) -> float:
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def priority_rank(chunk: Chunk) -> tuple[int, int, int]:
    return (
        PRIORITY_SCORE.get(chunk.priority, 1),
        SOURCE_TYPE_SCORE.get(chunk.source_type, 1),
        len(chunk.text),
    )


def normalize_warning(value: str) -> str:
    if value == "Normalize garbled rupee symbols before KB generation.":
        return "source_had_currency_encoding_artifacts_normalized"
    if value == "Values appear to total 105 percent. Mark as needs_review before customer-facing use.":
        return "source_value_inconsistency_needs_review"
    if value == "Processing fee and loan amount values conflict with some other sources; preserve source context.":
        return "source_value_conflict_preserve_context"
    if value == "Thin single-row table; lower priority than schedule of charges and core overview.":
        return "thin_single_row_table_lower_priority"
    return value


def normalize_warnings(values: list[str]) -> list[str]:
    return [normalize_warning(value) for value in values]


def is_pdf_extraction_boilerplate(line: str) -> bool:
    if re.match(r"^---\s*page\s+\d+\s*---$", line, flags=re.IGNORECASE):
        return True
    if re.match(r"^\d+\s*\|\s*Page(?:\s+Classification\s*:\s*\w+)?$", line, flags=re.IGNORECASE):
        return True
    if re.match(r"^Classification\s*:\s*(Internal|Public|Confidential)$", line, flags=re.IGNORECASE):
        return True
    if re.match(r"^Page\s+\d+\s+of\s+\d+$", line, flags=re.IGNORECASE):
        return True
    return False


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_source_text(path: Path) -> tuple[dict[str, str], str, str]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    marker = "--- CLEANED TEXT ---"
    doc_marker = "--- CLEANED DOCUMENT TEXT ---"
    if marker in text:
        header, body = text.split(marker, 1)
    elif doc_marker in text:
        header, body = text.split(doc_marker, 1)
    else:
        header, body = "", text

    metadata: dict[str, str] = {}
    for line in header.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip()] = value.strip()
    return metadata, header, body


def strip_noise_lines(
    body: str,
    source_id: str,
    report_counter: Counter[str],
) -> tuple[list[str], dict[str, Any]]:
    cleaned: list[str] = []
    removed_lines = 0
    removed_pdf_boilerplate = 0
    published_date: str | None = None
    hard_stop = False

    for raw_line in body.splitlines():
        line = normalize_space(raw_line)
        if not line:
            continue

        fixed, changed = fix_mojibake(line)
        if changed:
            report_counter["mojibake_lines_seen"] += 1
        line = normalize_text(fixed)
        lowered = line.lower().lstrip("#").strip()

        parsed_date = parse_iso_date(line)
        if parsed_date:
            published_date = parsed_date
            removed_lines += 1
            continue

        if is_pdf_extraction_boilerplate(line):
            removed_lines += 1
            removed_pdf_boilerplate += 1
            report_counter["pdf_extraction_boilerplate_removed"] += 1
            continue

        if lowered in SECTION_BREAK_HEADINGS:
            hard_stop = True
            removed_lines += 1
            break

        if lowered in DROP_LINE_TEXT:
            removed_lines += 1
            continue

        if lowered.startswith("## "):
            heading_text = lowered[3:].strip()
            if heading_text in SECTION_BREAK_HEADINGS:
                hard_stop = True
                removed_lines += 1
                break
            if heading_text in DROP_LINE_TEXT:
                removed_lines += 1
                continue

        if re.match(r"^##\s+(mobile number|how to link aadhaar|government|budget|nsdc|itr-v|igst|aadhaar card)", line, flags=re.IGNORECASE):
            hard_stop = True
            removed_lines += 1
            break

        cleaned.append(line)

    return cleaned, {
        "removed_noise_lines": removed_lines,
        "removed_pdf_boilerplate_lines": removed_pdf_boilerplate,
        "published_date": published_date,
        "stopped_at_noise_section": hard_stop,
        "source_id": source_id,
    }


def split_by_headings(lines: list[str]) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = []
    current_heading = "Overview"
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = normalize_heading(line)
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, current_lines))

    return [(heading, "\n".join(section_lines).strip()) for heading, section_lines in sections if "\n".join(section_lines).strip()]


def split_long_text(text: str, max_words: int = 240, overlap: int = 30) -> list[str]:
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(len(words), start + max_words)
        chunks.append(" ".join(words[start:end]).strip())
        if end == len(words):
            break
        start = max(0, end - overlap)
    return chunks


def build_chunk(
    *,
    source: dict[str, Any],
    source_type: str,
    source_file: str,
    title: str,
    heading: str,
    text: str,
    raw_text: str,
    chunk_index: int,
    metadata: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> Chunk | None:
    text = normalize_text(text)
    text, pii_counts = mask_pii(text)
    text = normalize_space(text)
    if len(text) < 80 and source_type != "table":
        return None

    category = TAXONOMY_MAP.get(str(source.get("category", "")), str(source.get("category", "uncategorized")))
    chunk_id_seed = "|".join([str(source.get("source_id", "")), source_type, heading, text[:160], str(chunk_index)])
    chunk = Chunk(
        id=f"clean_{sha256_short(chunk_id_seed)}",
        source_id=str(source.get("source_id", "")),
        source_type=source_type,
        source_url=str(source.get("source_url") or source.get("url") or ""),
        source_file=source_file,
        category=category,
        priority=str(source.get("priority", "medium")),
        title=title,
        heading=heading or title or "Untitled",
        text=text,
        raw_text=raw_text,
        chunk_index=chunk_index,
        metadata=metadata or {},
        warnings=warnings or [],
        pii_masks=pii_counts,
    )
    chunk.normalized_hash = exact_hash(text)
    chunk.token_fingerprint = token_fingerprint(text)
    if pii_counts:
        chunk.warnings.append("pii_masked")
    if "access denied" in text.lower() or "forbidden" in text.lower():
        chunk.warnings.append("source_may_be_blocked")
    if "404" in (title or "").lower():
        chunk.warnings.append("title_indicates_404")
    return chunk


def process_web_source(project_root: Path, source: dict[str, Any], counters: Counter[str]) -> tuple[list[Chunk], dict[str, Any]]:
    source_path = project_root / source["cleaned_file"]
    metadata, _header, body = read_source_text(source_path)
    title = normalize_heading(metadata.get("title") or source.get("source_id", ""))
    lines, noise_meta = strip_noise_lines(body, source["source_id"], counters)
    sections = split_by_headings(lines)
    chunks: list[Chunk] = []
    warnings: list[str] = []

    clean_chars = sum(len(line) for line in lines)
    if clean_chars < 400:
        warnings.append("thin_cleaned_text_after_noise_removal")
    if not sections:
        warnings.append("no_clean_sections_found")

    chunk_index = 0
    for heading, section_text in sections:
        if len(section_text) < 80:
            continue
        for part in split_long_text(section_text):
            chunk_index += 1
            chunk = build_chunk(
                source=source,
                source_type="webpage",
                source_file=source["cleaned_file"],
                title=title,
                heading=heading,
                text=part,
                raw_text=section_text,
                chunk_index=chunk_index,
                metadata={
                    "published_date": noise_meta.get("published_date"),
                    "extraction_title": metadata.get("title"),
                    "source_priority_note": source.get("use"),
                },
                warnings=warnings.copy(),
            )
            if chunk:
                chunks.append(chunk)

    return chunks, {
        "source_id": source["source_id"],
        "source_type": "webpage",
        "input_file": source["cleaned_file"],
        "clean_chars": clean_chars,
        "chunks_created": len(chunks),
        "warnings": sorted(set(warnings)),
        **noise_meta,
    }


def process_table(project_root: Path, table: dict[str, Any], source_lookup: dict[str, dict[str, Any]]) -> tuple[list[Chunk], dict[str, Any]]:
    path = project_root / table["file_path"]
    source = source_lookup.get(table["source_id"], {})
    rows: list[list[str]] = []
    with path.open("r", encoding="utf-8", errors="ignore", newline="") as handle:
        reader = csv.reader(handle)
        rows = [[normalize_text(cell) for cell in row] for row in reader if any(cell.strip() for cell in row)]

    chunks: list[Chunk] = []
    if not rows:
        return [], {
            "table_id": table["table_id"],
            "source_type": "table",
            "input_file": table["file_path"],
            "rows": 0,
            "chunks_created": 0,
            "warnings": ["empty_table"],
        }

    header_like = rows[0] if len(rows[0]) > 2 else None
    data_rows = rows[1:] if header_like else rows
    warnings = normalize_warnings(list(table.get("warnings", [])))

    for idx, row in enumerate(data_rows, start=1):
        row = [cell for cell in row if cell]
        if not row:
            continue

        if header_like and len(row) == len(header_like):
            pairs = [f"{header_like[col_idx]}: {cell}" for col_idx, cell in enumerate(row)]
            text = "; ".join(pairs)
            heading = row[0]
        elif len(row) == 2:
            text = f"{row[0]}: {row[1]}"
            heading = row[0]
        else:
            text = " | ".join(row)
            heading = row[0]

        table_source = {
            **source,
            "source_id": table["source_id"],
            "source_url": source.get("source_url") or source.get("url") or "",
            "category": table.get("category", source.get("category", "")),
            "priority": table.get("priority", source.get("priority", "medium")),
        }
        chunk = build_chunk(
            source=table_source,
            source_type="table",
            source_file=table["file_path"],
            title=normalize_heading(table["table_id"]),
            heading=normalize_heading(heading),
            text=text,
            raw_text=" | ".join(row),
            chunk_index=idx,
            metadata={
                "table_id": table["table_id"],
                "row_index": idx,
                "source_priority_note": table.get("use"),
            },
            warnings=warnings.copy(),
        )
        if chunk:
            chunks.append(chunk)

    return chunks, {
        "table_id": table["table_id"],
        "source_id": table["source_id"],
        "source_type": "table",
        "input_file": table["file_path"],
        "rows": len(data_rows),
        "chunks_created": len(chunks),
        "warnings": sorted(set(warnings)),
    }


def process_document(project_root: Path, document: dict[str, Any], counters: Counter[str]) -> tuple[list[Chunk], dict[str, Any]]:
    path = project_root / document["cleaned_file"]
    metadata, _header, body = read_source_text(path)
    lines, noise_meta = strip_noise_lines(body, document["source_id"], counters)
    text = "\n".join(lines).strip()
    warnings: list[str] = []
    if len(text) < 400:
        warnings.append("thin_document_text")

    chunks: list[Chunk] = []
    parts = split_long_text(text, max_words=260, overlap=35)
    for idx, part in enumerate(parts, start=1):
        chunk = build_chunk(
            source=document,
            source_type="pdf",
            source_file=document["cleaned_file"],
            title=normalize_heading(document["source_id"]),
            heading=normalize_heading(document.get("category", "Document")),
            text=part,
            raw_text=part,
            chunk_index=idx,
            metadata={
                "document_id": document.get("document_id"),
                "raw_file": document.get("raw_file"),
                "parser_status": metadata.get("parser_status"),
                "source_priority_note": document.get("use"),
            },
            warnings=warnings.copy(),
        )
        if chunk:
            chunks.append(chunk)

    return chunks, {
        "document_id": document.get("document_id"),
        "source_id": document["source_id"],
        "source_type": "pdf",
        "input_file": document["cleaned_file"],
        "clean_chars": len(text),
        "chunks_created": len(chunks),
        "warnings": sorted(set(warnings)),
        **noise_meta,
    }


def dedupe_chunks(chunks: list[Chunk]) -> tuple[list[Chunk], dict[str, Any]]:
    exact_seen: dict[str, Chunk] = {}
    exact_removed = 0
    for chunk in sorted(chunks, key=priority_rank, reverse=True):
        existing = exact_seen.get(chunk.normalized_hash)
        if existing is None:
            exact_seen[chunk.normalized_hash] = chunk
        else:
            exact_removed += 1

    exact_kept = list(exact_seen.values())
    final_chunks: list[Chunk] = []
    near_removed = 0
    near_examples: list[dict[str, str]] = []

    for chunk in sorted(exact_kept, key=priority_rank, reverse=True):
        duplicate_of: Chunk | None = None
        for kept in final_chunks:
            if chunk.category != kept.category:
                continue
            if abs(len(chunk.text) - len(kept.text)) > max(120, int(0.5 * max(len(chunk.text), len(kept.text)))):
                continue
            score = jaccard(chunk.token_fingerprint, kept.token_fingerprint)
            if score >= 0.92:
                duplicate_of = kept
                break
        if duplicate_of:
            near_removed += 1
            if len(near_examples) < 20:
                near_examples.append(
                    {
                        "removed_chunk_id": chunk.id,
                        "kept_chunk_id": duplicate_of.id,
                        "removed_source_id": chunk.source_id,
                        "kept_source_id": duplicate_of.source_id,
                    }
                )
            continue
        final_chunks.append(chunk)

    final_chunks.sort(key=lambda item: (item.source_id, item.source_type, item.chunk_index, item.id))
    return final_chunks, {
        "input_chunks": len(chunks),
        "exact_duplicates_removed": exact_removed,
        "near_duplicates_removed": near_removed,
        "output_chunks": len(final_chunks),
        "near_duplicate_examples": near_examples,
    }


def discover_unlisted_inputs(project_root: Path, allowlist: dict[str, Any]) -> dict[str, Any]:
    allowed_files = set()
    for source in allowlist.get("allowed_web_sources", []):
        allowed_files.add(str(project_root / source["cleaned_file"]))
    for document in allowlist.get("allowed_documents", []):
        allowed_files.add(str(project_root / document["cleaned_file"]))

    cleaned_files = sorted(project_root.glob("data/cleaned/*.txt"))
    cleaned_doc_files = sorted(project_root.glob("data/cleaned/documents/*.txt"))

    unlisted = [str(path.relative_to(project_root)) for path in cleaned_files + cleaned_doc_files if str(path) not in allowed_files]
    return {
        "unlisted_cleaned_text_files": unlisted,
        "unlisted_cleaned_text_file_count": len(unlisted),
    }


def chunk_to_dict(chunk: Chunk, kb_version: str) -> dict[str, Any]:
    return {
        "id": chunk.id,
        "kb_version": kb_version,
        "provider": "lendingkart",
        "business_domain": "business_loans",
        "country": "india",
        "language": "en",
        "chunk_type": chunk.source_type,
        "taxonomy": {
            "category": chunk.category,
            "heading": chunk.heading,
        },
        "content": {
            "title": chunk.title,
            "text": chunk.text,
        },
        "source": {
            "source_id": chunk.source_id,
            "source_type": chunk.source_type,
            "source_url": chunk.source_url,
            "source_file": chunk.source_file,
        },
        "quality": {
            "status": "approved" if "needs_review" not in chunk.warnings else "needs_review",
            "priority": chunk.priority,
            "warnings": sorted(set(chunk.warnings)),
            "pii_masks": chunk.pii_masks,
        },
        "metadata": chunk.metadata,
        "hashes": {
            "normalized_text_hash": chunk.normalized_hash,
            "chunk_content_hash": sha256_short(chunk.text, length=16),
        },
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_markdown_report(path: Path, report: dict[str, Any]) -> None:
    lines = [
        "# KB Cleaning Report",
        "",
        f"Generated at UTC: {report['generated_at_utc']}",
        "",
        "## Summary",
        "",
        f"- Approved chunks written: {report['summary']['approved_chunks']}",
        f"- Web sources processed: {report['summary']['web_sources_processed']}",
        f"- Tables processed: {report['summary']['tables_processed']}",
        f"- Documents processed: {report['summary']['documents_processed']}",
        f"- Exact duplicates removed: {report['dedupe']['exact_duplicates_removed']}",
        f"- Near duplicates removed: {report['dedupe']['near_duplicates_removed']}",
        f"- Unlisted cleaned files ignored: {report['unlisted_inputs']['unlisted_cleaned_text_file_count']}",
        "",
        "## Warnings",
        "",
    ]
    for warning, count in sorted(report["warning_counts"].items()):
        lines.append(f"- {warning}: {count}")
    if not report["warning_counts"]:
        lines.append("- None")

    lines.extend(["", "## Cleaning Counters", ""])
    for label, count in sorted(report["cleaning_counters"].items()):
        lines.append(f"- {label}: {count}")
    if not report["cleaning_counters"]:
        lines.append("- None")

    lines.extend(["", "## PII Masks", ""])
    for label, count in sorted(report["pii_mask_counts"].items()):
        lines.append(f"- {label}: {count}")
    if not report["pii_mask_counts"]:
        lines.append("- None detected")

    lines.extend(["", "## Processed Inputs", ""])
    for item in report["processed_inputs"]:
        name = item.get("source_id") or item.get("table_id") or item.get("document_id")
        lines.append(f"- {item.get('source_type')}: {name} -> {item.get('chunks_created')} chunks")

    lines.extend(["", "## Ignored Unlisted Files", ""])
    for item in report["unlisted_inputs"]["unlisted_cleaned_text_files"][:80]:
        lines.append(f"- {item}")
    if report["unlisted_inputs"]["unlisted_cleaned_text_file_count"] > 80:
        lines.append("- ...")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Clean allowlisted extracted sources into approved KB chunks.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--allowlist", type=Path, default=None)
    parser.add_argument("--kb-version", default="lendingkart_business_loans_clean_v0.1")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    kb_dir = project_root / "data" / "kb"
    kb_dir.mkdir(parents=True, exist_ok=True)
    allowlist_path = args.allowlist or (kb_dir / "source_allowlist.json")
    allowlist = load_json(allowlist_path)

    counters: Counter[str] = Counter()
    all_chunks: list[Chunk] = []
    processed_inputs: list[dict[str, Any]] = []
    source_lookup = {source["source_id"]: source for source in allowlist.get("allowed_web_sources", [])}

    for source in allowlist.get("allowed_web_sources", []):
        chunks, detail = process_web_source(project_root, source, counters)
        all_chunks.extend(chunks)
        processed_inputs.append(detail)

    for table in allowlist.get("allowed_tables", []):
        chunks, detail = process_table(project_root, table, source_lookup)
        all_chunks.extend(chunks)
        processed_inputs.append(detail)

    for document in allowlist.get("allowed_documents", []):
        chunks, detail = process_document(project_root, document, counters)
        all_chunks.extend(chunks)
        processed_inputs.append(detail)

    deduped_chunks, dedupe_report = dedupe_chunks(all_chunks)
    rows = [chunk_to_dict(chunk, args.kb_version) for chunk in deduped_chunks]

    warning_counts: Counter[str] = Counter()
    pii_mask_counts: Counter[str] = Counter()
    for chunk in deduped_chunks:
        warning_counts.update(set(chunk.warnings))
        pii_mask_counts.update(chunk.pii_masks)

    output_jsonl = kb_dir / "approved_clean_chunks.jsonl"
    report_json = kb_dir / "cleaning_report.json"
    report_md = kb_dir / "cleaning_report.md"

    write_jsonl(output_jsonl, rows)
    unlisted_inputs = discover_unlisted_inputs(project_root, allowlist)
    report = {
        "generated_at_utc": utc_now(),
        "project_root": str(project_root),
        "allowlist_path": str(allowlist_path),
        "kb_version": args.kb_version,
        "summary": {
            "approved_chunks": len(rows),
            "web_sources_processed": len(allowlist.get("allowed_web_sources", [])),
            "tables_processed": len(allowlist.get("allowed_tables", [])),
            "documents_processed": len(allowlist.get("allowed_documents", [])),
            "raw_candidate_chunks_before_dedupe": len(all_chunks),
        },
        "dedupe": dedupe_report,
        "warning_counts": dict(warning_counts),
        "pii_mask_counts": dict(pii_mask_counts),
        "cleaning_counters": dict(counters),
        "processed_inputs": processed_inputs,
        "unlisted_inputs": unlisted_inputs,
        "outputs": {
            "approved_clean_chunks_jsonl": str(output_jsonl),
            "cleaning_report_json": str(report_json),
            "cleaning_report_md": str(report_md),
        },
    }
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    write_markdown_report(report_md, report)

    print(
        "approved_chunks={0} exact_dupes={1} near_dupes={2} unlisted_ignored={3}".format(
            len(rows),
            dedupe_report["exact_duplicates_removed"],
            dedupe_report["near_duplicates_removed"],
            unlisted_inputs["unlisted_cleaned_text_file_count"],
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
