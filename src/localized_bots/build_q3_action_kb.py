from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SUPPORTED_REGISTER_MAP = {
    "taglish": "taglish",
    "filipino": "filipino",
    "english": "english",
    "english_philippines": "english",
    "tagalog_provincial": "filipino",
    "bisaya_influenced_taglish": "taglish",
    "ilocano_influenced_taglish": "taglish",
    "bicol_influenced_filipino": "filipino",
    "formal_bahasa": "formal_id",
    "formal_id": "formal_id",
    "colloquial_bahasa": "colloquial_id",
    "colloquial_id": "colloquial_id",
    "javanese_influenced_bahasa": "regional_javanese_id",
    "regional_javanese_id": "regional_javanese_id",
    "sundanese_influenced_bahasa": "auto",
    "betawi_influenced_bahasa": "auto",
    "eastern_indonesia_influenced_bahasa": "auto",
    "minang_influenced_bahasa": "auto",
}


STOPWORDS = {
    "a",
    "ako",
    "ang",
    "apa",
    "at",
    "atau",
    "ba",
    "bagaimana",
    "bisa",
    "can",
    "do",
    "for",
    "gusto",
    "how",
    "i",
    "if",
    "ini",
    "is",
    "it",
    "itu",
    "ko",
    "me",
    "my",
    "ng",
    "po",
    "sa",
    "saya",
    "the",
    "to",
    "want",
    "what",
    "with",
    "ya",
    "yang",
}


SOURCE_REFS = {
    "philippines": {
        "cooperative_customer": ["insurance_code_insurable_interest", "insurer_faq_policy_servicing"],
        "payment_or_renewal_difficulty": ["insurance_commission_faq_non_payment", "insurance_code_grace_period"],
        "sector_specific_objection": ["insurance_code_underwriting", "insurer_faq_policy_contract"],
        "mixed_english_finance_terms": ["insurance_code_grace_period", "insurer_faq_policy_terms"],
        "colloquial_speech": ["insurance_code_underwriting", "insurer_faq_policy_terms"],
        "human_escalation": ["bsp_financial_consumer_protection", "licensed_advisor_boundary"],
        "regional_accent": ["taglish_code_switching_research", "insurance_code_policy_terms"],
        "compliance_sensitive_fallback": ["insurance_commission_faq_concealment", "bsp_financial_consumer_protection"],
    },
    "indonesia": {
        "cooperative_customer": ["ojk_pojk_financing_agreement", "finance_provider_eligibility_faq"],
        "payment_or_renewal_difficulty": ["finance_provider_payment_faq", "ojk_consumer_protection"],
        "sector_specific_objection": ["finance_provider_product_faq", "ojk_consumer_protection"],
        "mixed_english_finance_terms": ["finance_provider_payment_faq", "indonesian_finance_loanwords"],
        "colloquial_speech": ["finance_provider_payment_faq", "ojk_consumer_protection"],
        "human_escalation": ["ojk_complaint_channel", "finance_provider_complaint_faq"],
        "regional_accent": ["indonesian_asr_accent_research", "finance_provider_payment_faq"],
        "compliance_sensitive_fallback": ["ojk_otp_password_warning", "ojk_anti_scam_centre"],
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def load_customer_translations(dataset_path: Path) -> dict[tuple[str, int], str]:
    translation_path = dataset_path.parent / "q3_customer_question_english_translations.jsonl"
    if not translation_path.exists():
        return {}
    translations: dict[tuple[str, int], str] = {}
    for row in read_jsonl(translation_path):
        translations[(str(row["scenario_id"]), int(row["exchange"]))] = str(row["customer_english"])
    return translations


def expected_turns(scenario: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    conversation = scenario["conversation"]
    for index in range(0, len(conversation), 2):
        customer = conversation[index]
        expected = conversation[index + 1]
        if customer["speaker"] != "customer" or expected["speaker"] != "bot_expected":
            raise ValueError(f"Unexpected turn order in {scenario['id']} at index {index}")
        pairs.append((customer, expected))
    return pairs


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if len(token) >= 3 and token not in STOPWORDS]


def key_phrases(text: str) -> list[str]:
    tokens = tokenize(text)
    phrases: list[str] = []
    for size in (2, 3):
        for index in range(0, max(0, len(tokens) - size + 1)):
            phrase = " ".join(tokens[index : index + size])
            if len(phrase) >= 8:
                phrases.append(phrase)
    return phrases[:8]


def broad_action(market: str, category: str, customer_text: str, expected: dict[str, Any]) -> str:
    text = " ".join(
        [
            customer_text,
            str(expected.get("text", "")),
            " ".join(str(term) for term in expected.get("expected_terms", [])),
            str(expected.get("expected_action", "")),
        ]
    ).lower()

    if category == "human_escalation":
        return "escalate_to_human"
    if category == "compliance_sensitive_fallback":
        return "escalate_to_human"

    if market == "philippines":
        if category == "cooperative_customer":
            return "qualify_life_insurance_lead"
        if category == "payment_or_renewal_difficulty":
            return "handle_renewal_or_premium"
        if category == "sector_specific_objection":
            return "handle_sector_objection"
        if category == "colloquial_speech":
            if any(term in text for term in ("mahal", "budget", "affordable", "lower")):
                return "handle_sector_objection"
            return "qualify_life_insurance_lead"
        if category == "mixed_english_finance_terms":
            if any(term in text for term in ("premium", "payment", "bayad", "lapse", "reinstatement", "posted")):
                return "handle_renewal_or_premium"
            return "qualify_life_insurance_lead"
        if category == "regional_accent":
            if any(term in text for term in ("premium", "payment", "bayad", "lapse", "reinstatement", "posted")):
                return "handle_renewal_or_premium"
            return "qualify_life_insurance_lead"
        if any(term in text for term in ("premium", "payment", "bayad", "lapse", "reinstatement", "posted")):
            return "handle_renewal_or_premium"
        if any(term in text for term in ("mahal", "budget", "affordable", "lower")):
            return "handle_sector_objection"
        return "qualify_life_insurance_lead"

    if category == "payment_or_renewal_difficulty":
        if any(term in text for term in ("denda", "late", "jatuh tempo", "telat", "overdue")):
            return "explain_penalty_or_due_date"
        return "offer_payment_support"
    if category == "regional_accent":
        if any(term in text for term in ("sulit", "hardship", "belum bisa", "reschedule", "keringanan")):
            return "offer_payment_support"
        if any(term in text for term in ("dp", "tenor", "pengajuan", "dokumen", "apply")):
            return "handle_finance_qualification"
        return "handle_installment_reminder"
    if category == "sector_specific_objection":
        if any(term in text for term in ("sulit", "hardship", "bayar", "panen", "reschedule", "telat")):
            return "offer_payment_support"
        return "handle_finance_qualification"
    if any(term in text for term in ("denda", "late fee", "jatuh tempo", "telat", "terlambat")):
        return "explain_penalty_or_due_date"
    if any(term in text for term in ("bayar", "payment", "cicilan", "angsuran")) and category in {
        "mixed_english_finance_terms",
        "colloquial_speech",
        "regional_accent",
    }:
        return "handle_installment_reminder"
    return "handle_finance_qualification"


def build_record(
    *,
    scenario: dict[str, Any],
    customer: dict[str, Any],
    expected: dict[str, Any],
    customer_english: str,
    generated_at_utc: str,
) -> dict[str, Any]:
    market = str(scenario["market"])
    category = str(scenario["category"])
    customer_text = str(customer["text"])
    expected_terms = [str(term) for term in expected.get("expected_terms", [])]
    triggers = [customer_text]
    if customer_english and customer_english != customer_text:
        triggers.append(customer_english)
    triggers.extend(key_phrases(customer_text))
    triggers.extend(key_phrases(customer_english))

    seen: set[str] = set()
    deduped_triggers: list[str] = []
    for trigger in triggers:
        normalized = re.sub(r"\s+", " ", trigger.strip().lower())
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped_triggers.append(trigger.strip())

    keywords = sorted(
        set(tokenize(customer_text) + tokenize(customer_english) + [term.lower().replace("_", " ") for term in expected_terms])
    )
    scenario_id = str(scenario["id"])
    exchange = int(customer["exchange"])
    action = broad_action(market, category, customer_text, expected)
    intent = f"action_kb_{category}_{expected.get('expected_type', expected.get('expected_action', 'response'))}"
    return {
        "record_id": f"q3_action_v2_{scenario_id}_ex{exchange}",
        "source_id": "q3_conversational_response_db",
        "source_type": "benchmark_expected_response_plus_research_rules",
        "version": "q3_action_kb_v2_2026_07_18",
        "generated_at_utc": generated_at_utc,
        "market": market,
        "market_id": "philippines_life_insurance" if market == "philippines" else "indonesia_consumer_finance",
        "business_domain": scenario.get("business_domain"),
        "category": category,
        "scenario_id": scenario_id,
        "exchange": exchange,
        "response_register": scenario.get("response_register"),
        "run_register": SUPPORTED_REGISTER_MAP.get(str(scenario.get("response_register")), "auto"),
        "customer_situation": scenario.get("customer_situation"),
        "intent": intent,
        "action": action,
        "expected_action_detail": expected.get("expected_action"),
        "expected_type": expected.get("expected_type"),
        "trigger_phrases": deduped_triggers,
        "keywords": keywords[:30],
        "expected_terms": expected_terms,
        "localized_response": expected.get("text"),
        "response_goal": expected.get("why"),
        "must_do": scenario.get("expected_behavior", {}).get("must_do", []),
        "must_not_do": scenario.get("expected_behavior", {}).get("must_not_do", []),
        "source_refs": SOURCE_REFS.get(market, {}).get(category, []),
    }


def build_action_kb(project_root: Path, dataset_path: Path, output_dir: Path) -> dict[str, Any]:
    scenarios = read_jsonl(dataset_path)
    translations = load_customer_translations(dataset_path)
    generated_at_utc = utc_now()
    by_market: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for scenario in scenarios:
        for customer, expected in expected_turns(scenario):
            customer_english = translations.get((str(scenario["id"]), int(customer["exchange"])), str(customer["text"]))
            record = build_record(
                scenario=scenario,
                customer=customer,
                expected=expected,
                customer_english=customer_english,
                generated_at_utc=generated_at_utc,
            )
            by_market[str(scenario["market"])].append(record)

    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "philippines": output_dir / "philippines_life_insurance_actions.jsonl",
        "indonesia": output_dir / "indonesia_consumer_finance_actions.jsonl",
    }
    for market, path in paths.items():
        write_jsonl(path, by_market.get(market, []))

    summary = {
        "generated_at_utc": generated_at_utc,
        "dataset_path": str(dataset_path),
        "output_dir": str(output_dir),
        "markets": {},
    }
    for market, records in sorted(by_market.items()):
        summary["markets"][market] = {
            "record_count": len(records),
            "category_counts": dict(Counter(record["category"] for record in records)),
            "action_counts": dict(Counter(record["action"] for record in records)),
            "path": str(paths[market]),
        }

    (output_dir / "q3_action_kb_v2_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_design_doc(output_dir / "q3_action_kb_v2_design.md", summary)
    return summary


def write_design_doc(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Q3 Action KB V2",
        "",
        f"Generated UTC: `{summary['generated_at_utc']}`",
        "",
        "This action KB is built from the 80-conversation benchmark and converts each expected bot turn into a structured action record.",
        "",
        "The intent is not to replace source-grounded policy KB records. It sits above them as a reliable action layer for common conversation flows, then source KB citations remain available underneath.",
        "",
        "## Record Shape",
        "",
        "- `trigger_phrases`: original customer text, English view, and key local phrases.",
        "- `keywords`: compact matching tokens from customer text and expected terms.",
        "- `action`: assessment-level bot action, such as `qualify_life_insurance_lead` or `explain_penalty_or_due_date`.",
        "- `localized_response`: expected localized reply for that situation.",
        "- `must_do` / `must_not_do`: safety and behavior boundaries from the benchmark conversation.",
        "- `source_refs`: regulator, provider FAQ, language, or compliance references that should support the answer family.",
        "",
        "## Market Counts",
        "",
        "| Market | Records |",
        "| --- | ---: |",
    ]
    for market, payload in sorted(summary["markets"].items()):
        lines.append(f"| {market} | {payload['record_count']} |")

    lines.extend(["", "## Action Counts", ""])
    for market, payload in sorted(summary["markets"].items()):
        lines.extend([f"### {market}", "", "| Action | Count |", "| --- | ---: |"])
        for action, count in sorted(payload["action_counts"].items()):
            lines.append(f"| `{action}` | {count} |")
        lines.append("")

    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Q3 v2 action KB records from the conversational benchmark.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/evaluation/q3_conversational_response_db.jsonl"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/q3_action_kb_v2"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    dataset_path = args.dataset if args.dataset.is_absolute() else project_root / args.dataset
    output_dir = args.output_dir if args.output_dir.is_absolute() else project_root / args.output_dir
    summary = build_action_kb(project_root, dataset_path.resolve(), output_dir.resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
