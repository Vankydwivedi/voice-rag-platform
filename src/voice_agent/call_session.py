from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_SRC = Path(__file__).resolve().parents[1]
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from voice_agent.lendingkart_agent import LendingkartVoiceAgent  # noqa: E402
from voice_agent.stt import get_stt_provider  # noqa: E402
from voice_agent.tts import get_tts_provider  # noqa: E402


@dataclass
class SessionState:
    session_id: str
    turn_count: int = 0
    actions: list[str] | None = None
    topics: list[str] | None = None
    human_escalation_required: bool = False
    callback_requested: bool = False

    def __post_init__(self) -> None:
        if self.actions is None:
            self.actions = []
        if self.topics is None:
            self.topics = []

    def update(self, agent_response: dict[str, Any], transcript: str) -> None:
        self.turn_count += 1
        action = str(agent_response["response"]["action"])
        self.actions.append(action)
        self.human_escalation_required = (
            self.human_escalation_required or bool(agent_response["response"]["human_escalation_required"])
        )
        lowered = transcript.lower()
        if any(token in lowered for token in ["callback", "call me", "later", "tomorrow"]):
            self.callback_requested = True
        if agent_response["grounding"]["top_records"]:
            category = agent_response["grounding"]["top_records"][0].get("category")
            subcategory = agent_response["grounding"]["top_records"][0].get("sub_category")
            topic = "/".join(str(item) for item in [category, subcategory] if item)
            if topic and topic not in self.topics:
                self.topics.append(topic)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_slug(value: str, fallback: str = "call") -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return (slug or fallback)[:70]


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


def write_transcript_text(path: Path, scenario: dict[str, Any], turns: list[dict[str, Any]]) -> None:
    lines = [
        f"Session: {scenario['id']}",
        f"Name: {scenario.get('name', '')}",
        f"Generated: {utc_now()}",
        "",
    ]
    for turn in turns:
        lines.append(f"Customer turn {turn['turn_index']}: {turn['stt']['transcript']}")
        lines.append(f"Agent turn {turn['turn_index']}: {turn['agent_response']['response']['spoken_text']}")
        if turn["agent_response"]["grounding"]["citations"]:
            citation = turn["agent_response"]["grounding"]["citations"][0]
            lines.append(f"Top source: {citation.get('label')} ({citation.get('url')})")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def synthesize_customer_audio(text: str, output_path: Path, tts_provider_name: str) -> dict[str, Any]:
    provider = get_tts_provider(tts_provider_name)
    result = provider.synthesize(text, output_path)
    return result.to_dict()


def contextualize_short_turn(transcript: str, previous_agent_text: str | None) -> str:
    lowered = transcript.lower().strip()
    if not previous_agent_text:
        return transcript
    short_followups = {
        "yes",
        "yes please",
        "sure",
        "ok",
        "okay",
        "tell me",
        "tell me more",
        "continue",
        "go ahead",
    }
    if lowered in short_followups or len(lowered.split()) <= 3:
        return f"Previous agent message: {previous_agent_text}. Customer follow-up: {transcript}"
    return transcript


def run_call(
    *,
    scenario: dict[str, Any],
    project_root: Path,
    output_dir: Path,
    stt_provider_name: str,
    tts_provider_name: str,
    synthesize_caller_audio: bool,
) -> dict[str, Any]:
    session_id = str(scenario["id"])
    session_dir = output_dir / safe_slug(session_id)
    caller_dir = session_dir / "caller_audio"
    agent_dir = session_dir / "agent_audio"
    transcript_dir = session_dir / "transcripts"
    session_dir.mkdir(parents=True, exist_ok=True)
    caller_dir.mkdir(parents=True, exist_ok=True)
    agent_dir.mkdir(parents=True, exist_ok=True)
    transcript_dir.mkdir(parents=True, exist_ok=True)

    agent = LendingkartVoiceAgent.from_project_root(project_root)
    stt_provider = get_stt_provider(stt_provider_name)
    tts_provider = get_tts_provider(tts_provider_name)
    state = SessionState(session_id=session_id)
    turns: list[dict[str, Any]] = []
    previous_agent_text: str | None = None

    for index, customer_turn in enumerate(scenario["turns"], start=1):
        expected_action = customer_turn.get("expected_action")
        caller_audio_path = caller_dir / f"turn_{index:02d}_customer.wav"
        caller_audio_result: dict[str, Any] | None = None

        if synthesize_caller_audio:
            caller_audio_result = synthesize_customer_audio(
                str(customer_turn["caller_utterance"]),
                caller_audio_path,
                tts_provider_name,
            )
        else:
            caller_audio_path = Path(customer_turn["audio_path"])

        stt_result = stt_provider.transcribe(audio_path=caller_audio_path)
        agent_query = contextualize_short_turn(stt_result.transcript, previous_agent_text)
        agent_response = agent.respond(agent_query, session_id=session_id)
        state.update(agent_response, stt_result.transcript)
        previous_agent_text = agent_response["response"]["spoken_text"]

        response_audio_path = agent_dir / f"turn_{index:02d}_agent_response.wav"
        tts_result = tts_provider.synthesize(previous_agent_text, response_audio_path)

        action_ok = expected_action is None or agent_response["response"]["action"] == expected_action
        turn_payload = {
            "turn_index": index,
            "caller_script_text": customer_turn.get("caller_utterance"),
            "caller_audio": caller_audio_result
            or {
                "audio_path": str(caller_audio_path),
                "provider": "provided_audio",
                "status": "provided",
            },
            "stt": stt_result.to_dict(),
            "agent_query": agent_query,
            "agent_response": agent_response,
            "tts": tts_result.to_dict(),
            "expected_action": expected_action,
            "actual_action": agent_response["response"]["action"],
            "turn_pass": action_ok and bool(agent_response["grounding"]["citations"]),
        }
        turns.append(turn_payload)

    transcript_text_path = transcript_dir / f"{safe_slug(session_id)}_transcript.txt"
    write_transcript_text(transcript_text_path, scenario, turns)
    pass_count = sum(1 for turn in turns if turn["turn_pass"])
    return {
        "generated_at_utc": utc_now(),
        "session_id": session_id,
        "name": scenario.get("name"),
        "coverage": scenario.get("coverage", []),
        "project_root": str(project_root),
        "providers": {
            "stt": stt_provider_name,
            "caller_audio_synthesis": tts_provider_name if synthesize_caller_audio else "provided_audio",
            "agent_tts": tts_provider_name,
        },
        "turn_count": len(turns),
        "pass_count": pass_count,
        "pass_rate": round(pass_count / max(1, len(turns)), 3),
        "session_state": state.to_dict(),
        "transcript_text_path": str(transcript_text_path),
        "turns": turns,
    }


def run_scenarios(
    *,
    scenarios_path: Path,
    project_root: Path,
    output_dir: Path,
    stt_provider_name: str,
    tts_provider_name: str,
    synthesize_caller_audio: bool,
) -> dict[str, Any]:
    scenarios = read_jsonl(scenarios_path)
    call_results = [
        run_call(
            scenario=scenario,
            project_root=project_root,
            output_dir=output_dir,
            stt_provider_name=stt_provider_name,
            tts_provider_name=tts_provider_name,
            synthesize_caller_audio=synthesize_caller_audio,
        )
        for scenario in scenarios
    ]
    pass_count = sum(1 for call in call_results if call["pass_count"] == call["turn_count"])
    return {
        "generated_at_utc": utc_now(),
        "system": "q1_multiturn_voice_call_session",
        "scenario_count": len(call_results),
        "pass_count": pass_count,
        "pass_rate": round(pass_count / max(1, len(call_results)), 3),
        "providers": {
            "stt": stt_provider_name,
            "caller_audio_synthesis": tts_provider_name if synthesize_caller_audio else "provided_audio",
            "agent_tts": tts_provider_name,
        },
        "call_results": call_results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-turn voice call sessions.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--scenarios", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    parser.add_argument("--stt-provider", default="windows_sapi", choices=["windows_sapi", "transcript_file", "openai"])
    parser.add_argument("--tts-provider", default="windows_sapi", choices=["windows_sapi", "text_only"])
    parser.add_argument("--use-provided-caller-audio", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    output_dir = args.output_dir or (project_root / "demos" / "call_results" / "q1_multiturn")
    output = run_scenarios(
        scenarios_path=args.scenarios.resolve(),
        project_root=project_root,
        output_dir=output_dir.resolve(),
        stt_provider_name=args.stt_provider,
        tts_provider_name=args.tts_provider,
        synthesize_caller_audio=not args.use_provided_caller_audio,
    )
    output_json = args.output_json or (output_dir / "q1_multiturn_call_results.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"pass_count": output["pass_count"], "scenario_count": output["scenario_count"], "pass_rate": output["pass_rate"]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
