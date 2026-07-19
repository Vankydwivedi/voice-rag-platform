from __future__ import annotations

import json
import os
import platform
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class SttResult:
    transcript: str
    provider: str
    confidence: float | None = None
    language: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "transcript": self.transcript,
            "provider": self.provider,
            "confidence": self.confidence,
            "language": self.language,
            "metadata": self.metadata or {},
        }


class SttProvider(Protocol):
    def transcribe(self, audio_path: Path | None = None, transcript_path: Path | None = None) -> SttResult:
        ...


_NUMBER_WORDS_FOR_LAKH = {
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
    "eleven",
    "twelve",
    "fifteen",
    "twenty",
    "thirty",
    "forty",
    "fifty",
}


def _finance_title_replacement(canonical: str):
    def replace(match: re.Match[str]) -> str:
        return canonical

    return replace


def normalize_finance_transcript(text: str) -> tuple[str, list[dict[str, str]]]:
    """Repair common ASR mistakes for Indian lending calls.

    The assessment cares about live signal quality, and short financial terms
    are often heard as ordinary English words. Keep the raw transcript in
    metadata while giving the downstream signal detector canonical loan terms.
    """

    corrections: list[tuple[re.Pattern[str], Any]] = [
        (re.compile(r"\bLending\s+(?:Cart|Kart)\b", re.IGNORECASE), _finance_title_replacement("Lendingkart")),
        (re.compile(r"\bC\s*I\s*B\s*I\s*L\b", re.IGNORECASE), _finance_title_replacement("CIBIL")),
        (re.compile(r"\b(?:civil|cible|sibyl)\b", re.IGNORECASE), _finance_title_replacement("CIBIL")),
        (re.compile(r"\bE\s*M\s*I\b", re.IGNORECASE), _finance_title_replacement("EMI")),
        (re.compile(r"\b(?:Emmy|Amy)\b", re.IGNORECASE), _finance_title_replacement("EMI")),
        (re.compile(r"\bturn\s+over\b", re.IGNORECASE), _finance_title_replacement("turnover")),
        (re.compile(r"\b(\d+(?:\.\d+)?)\s+(?:lock|lac|lack)\b", re.IGNORECASE), r"\1 lakh"),
        (
            re.compile(
                r"\b("
                + "|".join(sorted(_NUMBER_WORDS_FOR_LAKH, key=len, reverse=True))
                + r")\s+(?:lock|lac|lack)\b",
                re.IGNORECASE,
            ),
            lambda match: f"{match.group(1)} lakh",
        ),
    ]

    normalized = text
    changes: list[dict[str, str]] = []
    for pattern, replacement in corrections:
        matches = [match.group(0) for match in pattern.finditer(normalized)]
        if not matches:
            continue
        normalized = pattern.sub(replacement, normalized)
        for original in matches:
            changes.append({"from": original, "rule": pattern.pattern})
    return normalized, changes


class TranscriptFileSttProvider:
    """Offline STT adapter for assessment demos.

    This treats a `.txt` or `.json` transcript as the STT output. It lets the
    rest of the voice pipeline run deterministically without paid APIs.
    """

    provider_name = "transcript_file"

    def transcribe(self, audio_path: Path | None = None, transcript_path: Path | None = None) -> SttResult:
        path = transcript_path
        if path is None and audio_path is not None:
            path = audio_path.with_suffix(".txt")
        if path is None:
            raise ValueError("TranscriptFileSttProvider needs --transcript or an audio path with a matching .txt file.")
        if not path.exists():
            raise FileNotFoundError(f"Transcript file not found: {path}")

        if path.suffix.lower() == ".json":
            payload = json.loads(path.read_text(encoding="utf-8"))
            transcript = payload.get("transcript") or payload.get("text") or payload.get("caller_utterance")
            if not transcript:
                raise ValueError(f"Transcript JSON must contain transcript/text/caller_utterance: {path}")
            confidence = payload.get("confidence")
            language = payload.get("language")
            metadata = {"transcript_path": str(path), "audio_path": str(audio_path) if audio_path else None}
        else:
            transcript = path.read_text(encoding="utf-8").strip()
            confidence = 1.0
            language = None
            metadata = {"transcript_path": str(path), "audio_path": str(audio_path) if audio_path else None}

        return SttResult(
            transcript=str(transcript).strip(),
            provider=self.provider_name,
            confidence=float(confidence) if confidence is not None else None,
            language=language,
            metadata=metadata,
        )


class OpenAISttProvider:
    """Optional real audio STT provider.

    Requires:
    - `pip install openai`
    - `OPENAI_API_KEY`

    It is intentionally optional so local tests do not depend on network access.
    """

    provider_name = "openai"

    def __init__(self, model: str | None = None) -> None:
        self.model = model or os.getenv("OPENAI_STT_MODEL", "whisper-1")

    def transcribe(self, audio_path: Path | None = None, transcript_path: Path | None = None) -> SttResult:
        if audio_path is None:
            raise ValueError("OpenAISttProvider needs --audio.")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("OpenAI STT requires the `openai` Python package.") from exc

        client = OpenAI()
        with audio_path.open("rb") as handle:
            result = client.audio.transcriptions.create(model=self.model, file=handle)
        transcript = getattr(result, "text", None) or str(result)

        return SttResult(
            transcript=transcript.strip(),
            provider=self.provider_name,
            confidence=None,
            language=None,
            metadata={"audio_path": str(audio_path), "model": self.model},
        )


class WindowsSapiSttProvider:
    """Local audio-file STT using Windows System.Speech.

    This provider is useful for offline assessment demos because it accepts a
    WAV file and returns a real recognition result without an API key. It works
    best for clear English audio and installed Windows recognizers; production
    calls should use a call-grade ASR provider with diarization.
    """

    provider_name = "windows_sapi"

    def transcribe(self, audio_path: Path | None = None, transcript_path: Path | None = None) -> SttResult:
        if audio_path is None:
            raise ValueError("WindowsSapiSttProvider needs --audio.")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if platform.system().lower() != "windows":
            raise RuntimeError("Windows SAPI STT is only available on Windows.")

        ps_script = """
param(
  [string]$AudioPath
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Speech
$engine = New-Object System.Speech.Recognition.SpeechRecognitionEngine
$grammar = New-Object System.Speech.Recognition.DictationGrammar
$engine.LoadGrammar($grammar)
$engine.SetInputToWaveFile($AudioPath)
$result = $engine.Recognize()
$recognizer = $engine.RecognizerInfo
$payload = @{
  status = "no_result"
  text = ""
  confidence = $null
  culture = $recognizer.Culture.Name
  recognizer_name = $recognizer.Name
  recognizer_description = $recognizer.Description
  alternates = @()
}
if ($null -ne $result) {
  $payload.status = "ok"
  $payload.text = $result.Text
  $payload.confidence = $result.Confidence
  $payload.alternates = @(
    $result.Alternates |
      Select-Object -First 5 |
      ForEach-Object { @{ text = $_.Text; confidence = $_.Confidence } }
  )
}
$engine.Dispose()
$payload | ConvertTo-Json -Depth 6 -Compress
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "recognize.ps1"
            script_path.write_text(ps_script, encoding="utf-8")
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                    str(audio_path),
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )

        if completed.returncode != 0:
            raise RuntimeError(
                "Windows SAPI STT failed: "
                + json.dumps(
                    {
                        "returncode": completed.returncode,
                        "stdout": completed.stdout[-1000:],
                        "stderr": completed.stderr[-1000:],
                    },
                    ensure_ascii=False,
                )
            )

        payload = json.loads(completed.stdout.strip())
        transcript = str(payload.get("text") or "").strip()
        if not transcript:
            raise RuntimeError(f"Windows SAPI STT returned no transcript for audio file: {audio_path}")

        return SttResult(
            transcript=transcript,
            provider=self.provider_name,
            confidence=float(payload["confidence"]) if payload.get("confidence") is not None else None,
            language=payload.get("culture"),
            metadata={
                "audio_path": str(audio_path),
                "status": payload.get("status"),
                "recognizer_name": payload.get("recognizer_name"),
                "recognizer_description": payload.get("recognizer_description"),
                "alternates": payload.get("alternates", []),
            },
        )


class FasterWhisperSttProvider:
    """Local Whisper STT using faster-whisper.

    This is the practical free/offline option for the browser voice demo. The
    first run downloads the selected model, then later runs use the local cache.
    """

    provider_name = "faster_whisper"

    def __init__(
        self,
        model: str | None = None,
        device: str | None = None,
        compute_type: str | None = None,
        language: str | None = None,
        download_root: str | None = None,
        beam_size: int | None = None,
        best_of: int | None = None,
        vad_filter: bool | None = None,
        condition_on_previous_text: bool | None = None,
    ) -> None:
        self.model = model or os.getenv("FASTER_WHISPER_MODEL", "base")
        self.device = device or os.getenv("FASTER_WHISPER_DEVICE", "cpu")
        self.compute_type = compute_type or os.getenv("FASTER_WHISPER_COMPUTE_TYPE", "int8")
        self.language = language if language is not None else os.getenv("FASTER_WHISPER_LANGUAGE")
        self.download_root = download_root or os.getenv("FASTER_WHISPER_DOWNLOAD_ROOT")
        self.beam_size = beam_size if beam_size is not None else int(os.getenv("FASTER_WHISPER_BEAM_SIZE", "5"))
        self.best_of = best_of if best_of is not None else int(os.getenv("FASTER_WHISPER_BEST_OF", str(self.beam_size)))
        if vad_filter is None:
            vad_filter = os.getenv("FASTER_WHISPER_VAD_FILTER", "true").strip().lower() in {"1", "true", "yes", "on"}
        self.vad_filter = vad_filter
        if condition_on_previous_text is None:
            condition_on_previous_text = (
                os.getenv("FASTER_WHISPER_CONDITION_ON_PREVIOUS_TEXT", "true").strip().lower()
                in {"1", "true", "yes", "on"}
            )
        self.condition_on_previous_text = condition_on_previous_text
        self._whisper_model: Any | None = None

    def _get_model(self) -> Any:
        if self._whisper_model is None:
            if platform.system().lower() == "windows":
                # Avoid Anaconda/Intel OpenMP duplicate-runtime crashes in local demos.
                os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
            try:
                from faster_whisper import WhisperModel
            except ImportError as exc:
                raise RuntimeError(
                    "faster-whisper STT requires `pip install faster-whisper`."
                ) from exc
            self._whisper_model = WhisperModel(
                self.model,
                device=self.device,
                compute_type=self.compute_type,
                download_root=self.download_root,
            )
        return self._whisper_model

    def transcribe(self, audio_path: Path | None = None, transcript_path: Path | None = None) -> SttResult:
        if audio_path is None:
            raise ValueError("FasterWhisperSttProvider needs --audio.")
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._get_model()
        transcribe_kwargs: dict[str, Any] = {
            "beam_size": self.beam_size,
            "best_of": self.best_of,
            "vad_filter": self.vad_filter,
            "condition_on_previous_text": self.condition_on_previous_text,
            "temperature": 0.0,
            "word_timestamps": False,
        }
        if self.language:
            transcribe_kwargs["language"] = self.language
        segments, info = model.transcribe(str(audio_path), **transcribe_kwargs)
        segment_rows: list[dict[str, Any]] = []
        text_parts: list[str] = []
        weighted_logprob = 0.0
        total_duration = 0.0
        no_speech_probs: list[float] = []

        for segment in segments:
            text = segment.text.strip()
            if text:
                text_parts.append(text)
            duration = max(0.0, float(segment.end) - float(segment.start))
            avg_logprob = getattr(segment, "avg_logprob", None)
            if avg_logprob is not None and duration > 0:
                weighted_logprob += float(avg_logprob) * duration
                total_duration += duration
            no_speech_prob = getattr(segment, "no_speech_prob", None)
            if no_speech_prob is not None:
                no_speech_probs.append(float(no_speech_prob))
            segment_rows.append(
                {
                    "start": float(segment.start),
                    "end": float(segment.end),
                    "text": text,
                    "avg_logprob": avg_logprob,
                    "no_speech_prob": no_speech_prob,
                }
            )

        raw_transcript = " ".join(text_parts).strip()
        transcript, finance_normalizations = normalize_finance_transcript(raw_transcript)
        if not transcript:
            raise RuntimeError(f"faster-whisper returned no transcript for audio file: {audio_path}")

        confidence = None
        acoustic_confidence = None
        if total_duration > 0:
            # Convert mean log probability into a rough 0..1 quality signal.
            acoustic_confidence = max(0.0, min(1.0, pow(2.718281828, weighted_logprob / total_duration)))

        language_probability = getattr(info, "language_probability", None)
        max_no_speech_prob = max(no_speech_probs) if no_speech_probs else None
        speech_confidence = None
        if transcript and max_no_speech_prob is not None:
            speech_confidence = max(0.0, min(1.0, (1.0 - max_no_speech_prob) * 0.90))
            if language_probability is not None:
                speech_confidence = max(
                    speech_confidence,
                    max(0.0, min(1.0, float(language_probability) * (1.0 - max_no_speech_prob) * 0.96)),
                )
        confidence_candidates = [value for value in (acoustic_confidence, speech_confidence) if value is not None]
        if confidence_candidates:
            confidence = max(confidence_candidates)

        metadata = {
            "audio_path": str(audio_path),
            "model": self.model,
            "device": self.device,
            "compute_type": self.compute_type,
            "beam_size": self.beam_size,
            "best_of": self.best_of,
            "vad_filter": self.vad_filter,
            "condition_on_previous_text": self.condition_on_previous_text,
            "raw_transcript": raw_transcript,
            "finance_normalizations": finance_normalizations,
            "language": getattr(info, "language", None),
            "language_probability": language_probability,
            "duration": getattr(info, "duration", None),
            "acoustic_confidence": acoustic_confidence,
            "speech_confidence": speech_confidence,
            "max_no_speech_prob": max_no_speech_prob,
            "segments": segment_rows[:12],
        }
        return SttResult(
            transcript=transcript,
            provider=self.provider_name,
            confidence=confidence,
            language=getattr(info, "language", self.language),
            metadata=metadata,
        )


def get_stt_provider(name: str) -> SttProvider:
    normalized = name.strip().lower()
    if normalized in {"transcript", "transcript_file", "file", "mock"}:
        return TranscriptFileSttProvider()
    if normalized in {"windows", "windows_sapi", "sapi", "local"}:
        return WindowsSapiSttProvider()
    if normalized in {"faster_whisper", "faster-whisper", "whisper", "local_whisper"}:
        return FasterWhisperSttProvider()
    if normalized in {"faster_whisper_fast", "faster-whisper-fast", "whisper_fast", "local_whisper_fast"}:
        return FasterWhisperSttProvider(
            model=os.getenv("FASTER_WHISPER_FAST_MODEL", "tiny.en"),
            language=os.getenv("FASTER_WHISPER_FAST_LANGUAGE", "en"),
            beam_size=int(os.getenv("FASTER_WHISPER_FAST_BEAM_SIZE", "1")),
            best_of=int(os.getenv("FASTER_WHISPER_FAST_BEST_OF", "1")),
            vad_filter=os.getenv("FASTER_WHISPER_FAST_VAD_FILTER", "false").strip().lower()
            in {"1", "true", "yes", "on"},
            condition_on_previous_text=False,
        )
    if normalized == "openai":
        return OpenAISttProvider()
    raise ValueError(f"Unknown STT provider: {name}")
