from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_SRC = Path(__file__).resolve().parents[1]
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from voice_agent.lendingkart_agent import LendingkartVoiceAgent  # noqa: E402
from voice_agent.stt import get_stt_provider  # noqa: E402
from voice_agent.tts import get_tts_provider  # noqa: E402


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_slug(value: str, fallback: str = "call") -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return (slug or fallback)[:60]


def run_pipeline(
    *,
    project_root: Path,
    session_id: str,
    audio_path: Path | None,
    transcript_path: Path | None,
    utterance: str | None,
    stt_provider_name: str,
    tts_provider_name: str,
    output_dir: Path,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    if utterance:
        transcript_payload = {
            "transcript": utterance,
            "provider": "direct_text",
            "confidence": 1.0,
            "language": None,
            "metadata": {},
        }
    else:
        stt_provider = get_stt_provider(stt_provider_name)
        stt_result = stt_provider.transcribe(audio_path=audio_path, transcript_path=transcript_path)
        transcript_payload = stt_result.to_dict()

    agent = LendingkartVoiceAgent.from_project_root(project_root)
    agent_response = agent.respond(transcript_payload["transcript"], session_id=session_id)
    spoken_text = agent_response["response"]["spoken_text"]

    audio_output_path = output_dir / f"{safe_slug(session_id)}_response.wav"
    tts_provider = get_tts_provider(tts_provider_name)
    tts_result = tts_provider.synthesize(spoken_text, audio_output_path)

    return {
        "generated_at_utc": utc_now(),
        "session_id": session_id,
        "input_audio_path": str(audio_path) if audio_path else None,
        "input_transcript_path": str(transcript_path) if transcript_path else None,
        "stt": transcript_payload,
        "agent_response": agent_response,
        "tts": tts_result.to_dict(),
        "pipeline": {
            "stt_provider": stt_provider_name if not utterance else "direct_text",
            "tts_provider": tts_provider_name,
            "output_dir": str(output_dir),
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run STT -> grounded voice agent -> TTS pipeline.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--session-id", default="demo_call")
    parser.add_argument("--audio", type=Path, default=None, help="Optional caller audio file.")
    parser.add_argument("--transcript", type=Path, default=None, help="Optional transcript file for offline STT.")
    parser.add_argument("--utterance", default=None, help="Direct text input, bypassing STT.")
    parser.add_argument("--stt-provider", default="transcript_file", choices=["transcript_file", "windows_sapi", "openai"])
    parser.add_argument("--tts-provider", default="windows_sapi", choices=["windows_sapi", "text_only"])
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--output-json", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    output_dir = args.output_dir or (project_root / "demos" / "call_results")
    payload = run_pipeline(
        project_root=project_root,
        session_id=args.session_id,
        audio_path=args.audio.resolve() if args.audio else None,
        transcript_path=args.transcript.resolve() if args.transcript else None,
        utterance=args.utterance,
        stt_provider_name=args.stt_provider,
        tts_provider_name=args.tts_provider,
        output_dir=output_dir.resolve(),
    )

    output_json = args.output_json or (output_dir / f"{safe_slug(args.session_id)}_pipeline_result.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
