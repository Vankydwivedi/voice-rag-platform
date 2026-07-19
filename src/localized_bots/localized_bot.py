from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_SRC = Path(__file__).resolve().parents[1]
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from voice_agent.tts import get_tts_provider  # noqa: E402


CONFIG_MAP = {
    "philippines": "philippines_life_insurance.json",
    "ph": "philippines_life_insurance.json",
    "philippines_life_insurance": "philippines_life_insurance.json",
    "indonesia": "indonesia_consumer_finance.json",
    "id": "indonesia_consumer_finance.json",
    "indonesia_consumer_finance": "indonesia_consumer_finance.json",
}


@dataclass
class LocalizedResponse:
    market_id: str
    utterance: str
    detected_language: str
    response_register: str
    code_switching_detected: bool
    regional_accent_detected: bool
    intent: str
    action: str
    response_text: str
    terms_detected: list[str]
    fallback_used: bool
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "market_id": self.market_id,
            "utterance": self.utterance,
            "detected_language": self.detected_language,
            "response_register": self.response_register,
            "code_switching_detected": self.code_switching_detected,
            "regional_accent_detected": self.regional_accent_detected,
            "intent": self.intent,
            "action": self.action,
            "response_text": self.response_text,
            "terms_detected": self.terms_detected,
            "fallback_used": self.fallback_used,
            "metadata": self.metadata,
        }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def contains_phrase(text: str, phrase: str) -> bool:
    normalized_phrase = normalize(phrase)
    if " " in normalized_phrase or "-" in normalized_phrase:
        return normalized_phrase in text
    return bool(re.search(rf"\b{re.escape(normalized_phrase)}\b", text))


def count_marker_groups(text: str, marker_groups: dict[str, list[str]]) -> dict[str, int]:
    lowered = normalize(text)
    counts: dict[str, int] = {}
    for group, markers in marker_groups.items():
        counts[group] = sum(1 for marker in markers if contains_phrase(lowered, marker))
    return counts


def detect_terms(text: str, terminology: dict[str, list[str]]) -> list[str]:
    lowered = normalize(text)
    found: list[str] = []
    for term, variants in terminology.items():
        if any(contains_phrase(lowered, variant) for variant in variants):
            found.append(term)
    return sorted(found)


def detect_intent(text: str, intent_keywords: dict[str, list[str]]) -> str:
    lowered = normalize(text)
    priority = [
        "human_escalation",
        "price_objection",
        "penalty_question",
        "payment_difficulty",
        "busy_later",
        "qualification_followup",
        "lead_qualification",
        "renewal_reminder",
        "installment_reminder",
    ]
    scores: Counter[str] = Counter()
    for intent, keywords in intent_keywords.items():
        scores[intent] = sum(1 for keyword in keywords if contains_phrase(lowered, keyword))
    for intent in priority:
        if scores.get(intent, 0) > 0:
            return intent
    if scores:
        best, score = scores.most_common(1)[0]
        if score > 0:
            return best
    return "fallback"


def infer_language_and_register(config: dict[str, Any], utterance: str) -> tuple[str, str, bool, bool, dict[str, int]]:
    marker_counts = count_marker_groups(utterance, config.get("language_markers", {}))
    market_id = config["market_id"]
    active_groups = {group for group, count in marker_counts.items() if count > 0}

    if market_id.startswith("philippines"):
        english = marker_counts.get("english", 0)
        filipino = marker_counts.get("filipino", 0)
        taglish = marker_counts.get("taglish", 0)
        code_switching = (english > 0 and filipino > 0) or taglish > 0
        if code_switching:
            return "taglish", "taglish", True, False, marker_counts
        if filipino > english:
            return "filipino", "filipino", False, False, marker_counts
        return "english", "english", False, False, marker_counts

    regional = marker_counts.get("regional_javanese_id", 0) > 0
    colloquial = marker_counts.get("colloquial_id", 0) > 0
    loanwords = marker_counts.get("loanwords", 0) > 0
    formal = marker_counts.get("formal_id", 0) > 0
    code_switching = loanwords and (formal or colloquial or regional)

    if regional:
        return "javanese_influenced_indonesian", "regional_javanese_id", code_switching, True, marker_counts
    if colloquial:
        return "colloquial_bahasa_indonesia", "colloquial_id", code_switching, False, marker_counts
    if loanwords and not formal:
        return "bahasa_with_finance_loanwords", "formal_id", True, False, marker_counts
    return "formal_bahasa_indonesia", "formal_id", code_switching, False, marker_counts


def action_for_intent(intent: str) -> str:
    return {
        "renewal_reminder": "handle_renewal_or_premium",
        "lead_qualification": "qualify_life_insurance_lead",
        "price_objection": "handle_sector_objection",
        "busy_later": "schedule_callback",
        "installment_reminder": "handle_installment_reminder",
        "payment_difficulty": "offer_payment_support",
        "penalty_question": "explain_penalty_or_due_date",
        "qualification_followup": "handle_finance_qualification",
        "human_escalation": "escalate_to_human",
        "fallback": "localized_fallback",
    }.get(intent, "localized_fallback")


def followup_for_market(config: dict[str, Any], intent: str, register: str) -> str:
    if config["market_id"].startswith("philippines"):
        if intent == "human_escalation":
            return ""
        if register == "english":
            return "Would you like me to continue?"
        if register == "filipino":
            return "Gusto niyo po bang magpatuloy?"
        return "Gusto niyo po bang i-continue natin?"

    if intent == "human_escalation":
        return ""
    if register == "colloquial_id":
        return "Mau saya bantu lanjutkan?"
    if register == "regional_javanese_id":
        return "Nggih, mau saya bantu lanjutkan?"
    return "Apakah Bapak/Ibu ingin saya lanjutkan?"


def response_register_for_market(
    config: dict[str, Any],
    detected_register: str,
    preferred_response_register: str | None = None,
) -> str:
    if preferred_response_register and preferred_response_register != "auto":
        return preferred_response_register
    overrides = config.get("response_register_overrides", {})
    if detected_register in overrides:
        return str(overrides[detected_register])
    return str(config.get("default_response_register") or detected_register)


class LocalizedBot:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    @classmethod
    def from_config_path(cls, path: Path) -> "LocalizedBot":
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def respond(self, utterance: str, preferred_response_register: str | None = None) -> LocalizedResponse:
        detected_language, detected_register, code_switching, regional, marker_counts = infer_language_and_register(
            self.config, utterance
        )
        response_register = response_register_for_market(self.config, detected_register, preferred_response_register)
        intent = detect_intent(utterance, self.config.get("intent_keywords", {}))
        responses = self.config.get("responses", {})
        response_group = responses.get(intent) or responses.get("fallback", {})
        fallback_used = intent == "fallback"
        response_text = (
            response_group.get(response_register)
            or response_group.get(detected_register)
            or response_group.get("formal_id")
            or response_group.get("taglish")
        )
        if not response_text:
            response_text = next(iter(response_group.values()), "Sorry, I cannot answer that safely.")

        followup = followup_for_market(self.config, intent, response_register)
        if followup:
            response_text = f"{response_text} {followup}"

        terms = detect_terms(utterance + " " + response_text, self.config.get("terminology", {}))
        action = action_for_intent(intent)
        return LocalizedResponse(
            market_id=self.config["market_id"],
            utterance=utterance,
            detected_language=detected_language,
            response_register=response_register,
            code_switching_detected=code_switching,
            regional_accent_detected=regional,
            intent=intent,
            action=action,
            response_text=response_text,
            terms_detected=terms,
            fallback_used=fallback_used,
            metadata={
                "marker_counts": marker_counts,
                "asr_config": self.config.get("asr_config", {}),
                "tts_config": self.config.get("tts_config", {}),
                "sector": self.config.get("sector"),
                "use_case": self.config.get("use_case"),
                "detected_register": detected_register,
                "requested_response_register": preferred_response_register,
                "default_response_register": self.config.get("default_response_register"),
                "response_register_overrides": self.config.get("response_register_overrides", {}),
            },
        )


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


def write_call_transcript(path: Path, scenario: dict[str, Any], response: LocalizedResponse) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"Scenario: {scenario.get('id', 'single')}",
        f"Market: {response.market_id}",
        "",
        f"Customer: {response.utterance}",
        f"Bot: {response.response_text}",
        "",
        f"Detected language/register: {response.detected_language} / {response.response_register}",
        f"Intent/action: {response.intent} / {response.action}",
        f"Terms detected: {', '.join(response.terms_detected) if response.terms_detected else 'none'}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def evaluate_scenarios(
    *,
    bot: LocalizedBot,
    scenarios_path: Path,
    output_audio_dir: Path | None,
    transcript_output_dir: Path | None,
    tts_provider_name: str,
) -> dict[str, Any]:
    scenarios = read_jsonl(scenarios_path)
    tts_provider = get_tts_provider(tts_provider_name) if output_audio_dir else None
    rows: list[dict[str, Any]] = []
    pass_count = 0

    for scenario in scenarios:
        response = bot.respond(str(scenario["utterance"]))
        scenario_id = str(scenario.get("id", "scenario"))
        expected_action = scenario.get("expected_action")
        expected_register = scenario.get("expected_register")
        expected_code_switching = scenario.get("expected_code_switching")
        expected_regional = scenario.get("expected_regional_accent")

        action_ok = expected_action is None or response.action == expected_action
        register_ok = expected_register is None or response.response_register == expected_register
        code_switch_ok = expected_code_switching is None or response.code_switching_detected == expected_code_switching
        regional_ok = expected_regional is None or response.regional_accent_detected == expected_regional

        audio_result: dict[str, Any] | None = None
        if output_audio_dir and tts_provider:
            audio_path = output_audio_dir / f"{scenario_id}_response.wav"
            audio_result = tts_provider.synthesize(response.response_text, audio_path).to_dict()

        transcript_path = None
        if transcript_output_dir:
            transcript_path = transcript_output_dir / f"{scenario_id}_transcript.txt"
            write_call_transcript(transcript_path, scenario, response)

        ok = action_ok and register_ok and code_switch_ok and regional_ok
        if ok:
            pass_count += 1

        row = response.to_dict()
        row.update(
            {
                "id": scenario_id,
                "expected_action": expected_action,
                "expected_register": expected_register,
                "expected_code_switching": expected_code_switching,
                "expected_regional_accent": expected_regional,
                "checks": {
                    "action_ok": action_ok,
                    "register_ok": register_ok,
                    "code_switching_ok": code_switch_ok,
                    "regional_accent_ok": regional_ok,
                },
                "pass": ok,
                "audio": audio_result,
                "transcript_path": str(transcript_path) if transcript_path else None,
            }
        )
        rows.append(row)

    return {
        "generated_at_utc": utc_now(),
        "market_id": bot.config["market_id"],
        "scenario_count": len(scenarios),
        "pass_count": pass_count,
        "pass_rate": round(pass_count / max(1, len(scenarios)), 3),
        "asr_config": bot.config.get("asr_config", {}),
        "tts_config": bot.config.get("tts_config", {}),
        "rows": rows,
    }


def resolve_config(project_root: Path, market_or_path: str) -> Path:
    candidate = Path(market_or_path)
    if candidate.exists():
        return candidate
    config_name = CONFIG_MAP.get(market_or_path.lower())
    if not config_name:
        raise ValueError(f"Unknown market/config: {market_or_path}")
    return project_root / "src" / "localized_bots" / "configs" / config_name


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run localized Q3 voice-bot prototypes.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--market", required=True, help="philippines, indonesia, or config path")
    parser.add_argument("--utterance", default=None)
    parser.add_argument("--scenarios", type=Path, default=None)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--audio-output-dir", type=Path, default=None)
    parser.add_argument("--transcript-output-dir", type=Path, default=None)
    parser.add_argument("--tts-provider", default="text_only", choices=["text_only", "windows_sapi"])
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    config_path = resolve_config(project_root, args.market)
    bot = LocalizedBot.from_config_path(config_path)

    if args.scenarios:
        payload = evaluate_scenarios(
            bot=bot,
            scenarios_path=args.scenarios.resolve(),
            output_audio_dir=args.audio_output_dir.resolve() if args.audio_output_dir else None,
            transcript_output_dir=args.transcript_output_dir.resolve() if args.transcript_output_dir else None,
            tts_provider_name=args.tts_provider,
        )
    elif args.utterance:
        payload = bot.respond(args.utterance).to_dict()
    else:
        raise SystemExit("Provide either --utterance or --scenarios.")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
