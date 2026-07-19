from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_SRC = Path(__file__).resolve().parents[1]
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from q3_market_components.market_component import Q3MarketComponent  # noqa: E402


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
    # These are intentionally unsupported by the current prototype. We run auto
    # so the report can surface the real gap instead of hiding it.
    "sundanese_influenced_bahasa": "auto",
    "betawi_influenced_bahasa": "auto",
    "eastern_indonesia_influenced_bahasa": "auto",
    "minang_influenced_bahasa": "auto",
}


CATEGORY_ACTIONS = {
    "philippines": {
        "cooperative_customer": {"qualify_life_insurance_lead", "localized_fallback"},
        "payment_or_renewal_difficulty": {"handle_renewal_or_premium", "localized_fallback"},
        "sector_specific_objection": {
            "handle_sector_objection",
            "qualify_life_insurance_lead",
            "localized_fallback",
        },
        "mixed_english_finance_terms": {
            "qualify_life_insurance_lead",
            "handle_renewal_or_premium",
            "localized_fallback",
        },
        "colloquial_speech": {
            "handle_sector_objection",
            "qualify_life_insurance_lead",
            "localized_fallback",
        },
        "human_escalation": {"escalate_to_human"},
        "regional_accent": {
            "qualify_life_insurance_lead",
            "handle_renewal_or_premium",
            "localized_fallback",
        },
        "compliance_sensitive_fallback": {"localized_fallback", "escalate_to_human"},
    },
    "indonesia": {
        "cooperative_customer": {"handle_finance_qualification", "localized_fallback"},
        "payment_or_renewal_difficulty": {
            "handle_installment_reminder",
            "offer_payment_support",
            "explain_penalty_or_due_date",
        },
        "sector_specific_objection": {
            "handle_finance_qualification",
            "offer_payment_support",
            "localized_fallback",
        },
        "mixed_english_finance_terms": {
            "handle_finance_qualification",
            "handle_installment_reminder",
            "explain_penalty_or_due_date",
            "localized_fallback",
        },
        "colloquial_speech": {
            "handle_installment_reminder",
            "handle_finance_qualification",
            "explain_penalty_or_due_date",
            "localized_fallback",
        },
        "human_escalation": {"escalate_to_human"},
        "regional_accent": {
            "handle_installment_reminder",
            "handle_finance_qualification",
            "offer_payment_support",
            "localized_fallback",
        },
        "compliance_sensitive_fallback": {"localized_fallback", "escalate_to_human"},
    },
}


ACTION_ENGLISH = {
    "handle_renewal_or_premium": "The bot says the insurance premium must be paid before the due date to keep the policy active and offers payment help.",
    "qualify_life_insurance_lead": "The bot asks what coverage is needed, such as self, family protection, beneficiary, or rider.",
    "handle_sector_objection": "The bot acknowledges the customer's concern and suggests a lower premium or adjusted riders.",
    "schedule_callback": "The bot offers to schedule a callback at a convenient time.",
    "escalate_to_human": "The bot offers to connect the customer to a licensed advisor, servicing representative, or human agent.",
    "localized_fallback": "The bot says it does not want to guess and asks the customer to use supported topics or talk to a human.",
    "handle_installment_reminder": "The bot says the installment should be paid before the due date to avoid late fees.",
    "offer_payment_support": "The bot acknowledges payment difficulty and offers to record the issue or arrange support.",
    "explain_penalty_or_due_date": "The bot explains that late payment can trigger penalties according to the finance terms.",
    "handle_finance_qualification": "The bot explains loan/application inputs such as DP, tenor, item or vehicle details, and documents.",
}


REGISTER_ENGLISH = {
    "taglish": "Taglish",
    "filipino": "Filipino/Tagalog",
    "english": "Philippine English",
    "formal_id": "Formal Bahasa Indonesia",
    "colloquial_id": "Colloquial Bahasa Indonesia",
    "regional_javanese_id": "Javanese-influenced Bahasa Indonesia",
    "auto": "Auto-detect",
}


GUARDRAIL_PATTERNS = {
    "payment_or_renewal_difficulty": [
        "due date",
        "jatuh tempo",
        "premium",
        "cicilan",
        "denda",
        "lapse",
        "ma-lapse",
        "terlambat",
    ],
    "human_escalation": [
        "advisor",
        "petugas",
        "representative",
        "connect",
        "arahkan",
        "licensed",
        "human",
    ],
    "compliance_sensitive_fallback": [
        "guess",
        "manghula",
        "tidak pasti",
        "asal jawab",
        "advisor",
        "petugas",
        "official",
        "resmi",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
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
    for idx in range(0, len(conversation), 2):
        customer = conversation[idx]
        expected = conversation[idx + 1]
        if customer["speaker"] != "customer" or expected["speaker"] != "bot_expected":
            raise ValueError(f"Unexpected turn order in {scenario['id']} at index {idx}")
        pairs.append((customer, expected))
    return pairs


def requested_register_for(row: dict[str, Any]) -> str:
    return SUPPORTED_REGISTER_MAP.get(str(row.get("response_register")), "auto")


def register_score(row: dict[str, Any], actual_register: str, requested_register: str) -> float:
    if requested_register == "auto":
        if row["market"] == "indonesia" and str(row.get("response_register", "")).endswith("_influenced_bahasa"):
            return 1.0 if actual_register == "regional_javanese_id" else 0.4
        return 1.0
    return 1.0 if actual_register == requested_register else 0.0


def action_score(row: dict[str, Any], action: str) -> float:
    acceptable = CATEGORY_ACTIONS[row["market"]].get(row["category"], set())
    if action in acceptable:
        if action == "localized_fallback" and row["category"] not in {"compliance_sensitive_fallback", "regional_accent"}:
            return 0.55
        return 1.0
    if action == "localized_fallback":
        return 0.35
    return 0.0


def term_score(expected: dict[str, Any], actual_text: str) -> float:
    terms = [str(term).lower() for term in expected.get("expected_terms", [])]
    if not terms:
        return 1.0
    actual = normalize(actual_text)
    hits = 0
    for term in terms:
        simplified = term.replace("_", " ").lower()
        if simplified in actual:
            hits += 1
            continue
        pieces = [piece for piece in re.split(r"[^a-z0-9]+", simplified) if len(piece) >= 4]
        if pieces and any(piece in actual for piece in pieces):
            hits += 1
    return hits / len(terms)


def guardrail_score(row: dict[str, Any], actual_text: str, action: str) -> float:
    category = row["category"]
    if category not in GUARDRAIL_PATTERNS:
        return 1.0
    actual = normalize(actual_text)
    hits = sum(1 for pattern in GUARDRAIL_PATTERNS[category] if pattern in actual)
    if hits:
        return 1.0
    if category == "compliance_sensitive_fallback" and action == "localized_fallback":
        return 0.75
    return 0.0


def quality_label(score: float) -> str:
    if score >= 0.75:
        return "good"
    if score >= 0.5:
        return "partial"
    return "weak"


def english_expected_summary(expected: dict[str, Any]) -> str:
    action = str(expected.get("expected_action", "")).replace("_", " ")
    why = str(expected.get("why", "")).strip()
    terms = ", ".join(str(term) for term in expected.get("expected_terms", []))
    parts = [f"Expected answer should {action}."]
    if why:
        parts.append(f"Reason: {why}")
    if terms:
        parts.append(f"Key terms: {terms}.")
    return " ".join(parts)


@dataclass
class EvalOutputs:
    run_rows: list[dict[str, Any]]
    summary: dict[str, Any]
    english_markdown: str
    report_markdown: str


def run_eval(project_root: Path, dataset_path: Path) -> EvalOutputs:
    components = {
        "philippines": Q3MarketComponent.from_component_dir(project_root / "src" / "q3_market_components" / "philippines"),
        "indonesia": Q3MarketComponent.from_component_dir(project_root / "src" / "q3_market_components" / "indonesia"),
    }
    scenarios = read_jsonl(dataset_path)
    customer_translations = load_customer_translations(dataset_path)
    run_rows: list[dict[str, Any]] = []
    by_market: dict[str, Counter[str]] = defaultdict(Counter)
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    by_market_category: dict[str, Counter[str]] = defaultdict(Counter)
    fallback_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    response_repetition: Counter[str] = Counter()

    english_lines = [
        "# Q3 Conversational Dataset English View",
        "",
        "This file shows every customer turn, the customer question in English, the expected answer meaning in English, and the actual bot response meaning after running the current Q3 bots.",
        "",
        "The original customer text and original expected reply are kept so you can test voice input exactly as written.",
        "",
    ]

    for scenario in scenarios:
        market = scenario["market"]
        component = components[market]
        requested_register = requested_register_for(scenario)
        english_lines.extend(
            [
                f"## {scenario['id']} - {market} - {scenario['category']}",
                "",
                f"Situation: {scenario['customer_situation']}",
                "",
                f"Expected register: {scenario['response_register']} -> run as `{requested_register}`",
                "",
            ]
        )
        for customer, expected in expected_turns(scenario):
            customer_english = customer_translations.get(
                (str(scenario["id"]), int(customer["exchange"])),
                customer["text"],
            )
            result = component.respond(customer["text"], response_register=requested_register)
            localized = result.localized_response
            scores = {
                "register": register_score(scenario, localized.response_register, requested_register),
                "action": action_score(scenario, localized.action),
                "terms": term_score(expected, localized.response_text),
                "guardrail": guardrail_score(scenario, localized.response_text, localized.action),
            }
            overall = round(
                0.25 * scores["register"]
                + 0.3 * scores["action"]
                + 0.25 * scores["terms"]
                + 0.2 * scores["guardrail"],
                3,
            )
            label = quality_label(overall)
            run_row = {
                "scenario_id": scenario["id"],
                "market": market,
                "category": scenario["category"],
                "exchange": customer["exchange"],
                "customer_text": customer["text"],
                "customer_text_english_view": customer_english,
                "expected_response_text": expected["text"],
                "expected_response_english_summary": english_expected_summary(expected),
                "expected_type": expected.get("expected_type"),
                "expected_action": expected.get("expected_action"),
                "expected_terms": expected.get("expected_terms", []),
                "requested_register": requested_register,
                "actual_detected_language": localized.detected_language,
                "actual_response_register": localized.response_register,
                "actual_action": localized.action,
                "actual_intent": localized.intent,
                "actual_response_text": localized.response_text,
                "actual_response_english_summary": ACTION_ENGLISH.get(localized.action, localized.action),
                "citations": result.citations,
                "scores": scores,
                "overall_score": overall,
                "quality": label,
                "fallback_used": localized.fallback_used,
                "terms_detected": localized.terms_detected,
                "code_switching_detected": localized.code_switching_detected,
                "regional_accent_detected": localized.regional_accent_detected,
            }
            run_rows.append(run_row)
            by_market[market][label] += 1
            by_category[scenario["category"]][label] += 1
            by_market_category[f"{market}/{scenario['category']}"][label] += 1
            action_counts[localized.action] += 1
            response_repetition[localized.response_text] += 1
            if localized.fallback_used:
                fallback_counts[market] += 1

            english_lines.extend(
                [
                    f"### Exchange {customer['exchange']}",
                    "",
                    f"Customer question, original: {customer['text']}",
                    "",
                    f"Customer question, English view: {customer_english}",
                    "",
                    f"Expected answer, original: {expected['text']}",
                    "",
                    f"Expected answer, English view: {run_row['expected_response_english_summary']}",
                    "",
                    f"Actual bot answer, original: {localized.response_text}",
                    "",
                    f"Actual bot answer, English view: {run_row['actual_response_english_summary']}",
                    "",
                    f"Actual action/register: `{localized.action}` / `{localized.response_register}`",
                    "",
                    f"Quality: **{label}** (`{overall}`)",
                    "",
                ]
            )

    total = len(run_rows)
    summary = {
        "generated_at_utc": utc_now(),
        "dataset_path": str(dataset_path),
        "scenario_count": len(scenarios),
        "turn_count": total,
        "market_quality_counts": {market: dict(counts) for market, counts in sorted(by_market.items())},
        "category_quality_counts": {category: dict(counts) for category, counts in sorted(by_category.items())},
        "market_category_quality_counts": {
            key: dict(counts) for key, counts in sorted(by_market_category.items())
        },
        "action_counts": dict(action_counts),
        "fallback_counts": dict(fallback_counts),
        "unique_actual_response_count": len(response_repetition),
        "most_repeated_actual_responses": response_repetition.most_common(10),
        "average_score": round(sum(row["overall_score"] for row in run_rows) / max(1, total), 3),
        "quality_counts": dict(Counter(row["quality"] for row in run_rows)),
    }

    report_markdown = make_report_markdown(summary, run_rows)
    return EvalOutputs(
        run_rows=run_rows,
        summary=summary,
        english_markdown="\n".join(english_lines).rstrip() + "\n",
        report_markdown=report_markdown,
    )


def make_report_markdown(summary: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    quality = Counter(row["quality"] for row in rows)
    lines = [
        "# Q3 Conversational Bot Run Report",
        "",
        f"Generated UTC: `{summary['generated_at_utc']}`",
        "",
        "## Scope",
        "",
        f"- Scenarios: {summary['scenario_count']}",
        f"- Customer turns tested: {summary['turn_count']}",
        "- Bots tested: Q3 Philippines life insurance and Q3 Indonesia consumer finance",
        "- Input type: text customer turns from the conversational database",
        "- Output evaluated: actual Q3 bot response text, action, register, terms, and fallback behavior",
        "",
        "## Overall Result",
        "",
        f"- Average heuristic score: `{summary['average_score']}`",
        f"- Good turns: `{quality.get('good', 0)}`",
        f"- Partial turns: `{quality.get('partial', 0)}`",
        f"- Weak turns: `{quality.get('weak', 0)}`",
        f"- Unique actual response templates used: `{summary['unique_actual_response_count']}`",
        "",
        "## Market Results",
        "",
        "| Market | Good | Partial | Weak | Total |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for market, counts in summary["market_quality_counts"].items():
        total = sum(counts.values())
        lines.append(
            f"| {market} | {counts.get('good', 0)} | {counts.get('partial', 0)} | {counts.get('weak', 0)} | {total} |"
        )

    lines.extend(["", "## Category Results", "", "| Category | Good | Partial | Weak | Total |", "| --- | ---: | ---: | ---: | ---: |"])
    for category, counts in summary["category_quality_counts"].items():
        total = sum(counts.values())
        lines.append(
            f"| {category} | {counts.get('good', 0)} | {counts.get('partial', 0)} | {counts.get('weak', 0)} | {total} |"
        )

    lines.extend(
        [
            "",
            "## Main Findings",
            "",
            "1. The bots can respond in the selected market language/register, especially when the UI register is explicitly set.",
            "2. The current Q3 bots are still script-template bots, so many answers are safe but too generic compared with the new conversational DB.",
            "3. Philippines handles basic premium, coverage, beneficiary, rider, and advisor-routing questions better than detailed claim, legal, payment hardship, or fraud cases.",
            "4. Indonesia handles due-date, installment, denda, DP, tenor, and petugas escalation better than nuanced regional accents or document/fraud edge cases.",
            "5. The very low unique-response count shows repetition. This is the biggest gap if the assessment expects natural 2-3 turn conversations.",
            "",
            "## Recommended Fixes",
            "",
            "1. Add conversation-state handling so exchange 2 and exchange 3 use earlier customer details.",
            "2. Add category-specific response templates for payment promises, partial payment, fraud/OTP, claim guarantees, fake documents, and legal/servicing boundaries.",
            "3. Expand the Q3 intent keywords using the actual dataset terms.",
            "4. Add unsupported Indonesia regional variants beyond Javanese, or document them as known gaps.",
            "5. Use the expected-response DB as a regression suite after improving the bot.",
            "",
            "## Most Repeated Actual Responses",
            "",
        ]
    )
    for response, count in summary["most_repeated_actual_responses"]:
        short = response.replace("\n", " ")
        if len(short) > 240:
            short = short[:237] + "..."
        lines.append(f"- `{count}` times: {short}")

    weak_examples = [row for row in rows if row["quality"] == "weak"][:12]
    lines.extend(["", "## Example Weak Turns", ""])
    for row in weak_examples:
        lines.extend(
            [
                f"### {row['scenario_id']} exchange {row['exchange']} ({row['market']} / {row['category']})",
                "",
                f"Customer: {row['customer_text']}",
                "",
                f"Customer English view: {row['customer_text_english_view']}",
                "",
                f"Expected English view: {row['expected_response_english_summary']}",
                "",
                f"Actual: {row['actual_response_text']}",
                "",
                f"Score: `{row['overall_score']}`",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate Q3 conversational response DB against current bots.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("data/evaluation/q3_conversational_response_db.jsonl"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("demos/q3_conversation_eval"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    dataset_path = (project_root / args.dataset).resolve() if not args.dataset.is_absolute() else args.dataset
    output_dir = (project_root / args.output_dir).resolve() if not args.output_dir.is_absolute() else args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = run_eval(project_root, dataset_path)
    write_jsonl(output_dir / "q3_conversation_bot_run_results.jsonl", outputs.run_rows)
    (output_dir / "q3_conversation_bot_run_summary.json").write_text(
        json.dumps(outputs.summary, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "q3_conversational_dataset_english_view.md").write_text(
        outputs.english_markdown,
        encoding="utf-8",
    )
    (output_dir / "q3_conversation_bot_run_report.md").write_text(
        outputs.report_markdown,
        encoding="utf-8",
    )
    print(json.dumps(outputs.summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
