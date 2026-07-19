from __future__ import annotations

import math
import platform
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass
class TtsResult:
    audio_path: str | None
    provider: str
    status: str
    text_path: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio_path": self.audio_path,
            "provider": self.provider,
            "status": self.status,
            "text_path": self.text_path,
            "metadata": self.metadata or {},
        }


class TtsProvider(Protocol):
    def synthesize(self, text: str, output_path: Path) -> TtsResult:
        ...


def write_tone_wav(path: Path, duration_seconds: float = 0.35, sample_rate: int = 16000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = int(duration_seconds * sample_rate)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frames):
            sample = int(1200 * math.sin(2 * math.pi * 440 * index / sample_rate))
            wav.writeframesraw(sample.to_bytes(2, byteorder="little", signed=True))


class WindowsSapiTtsProvider:
    provider_name = "windows_sapi"

    def synthesize(self, text: str, output_path: Path) -> TtsResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        text_path = output_path.with_suffix(".txt")
        text_path.write_text(text, encoding="utf-8")

        if platform.system().lower() != "windows":
            write_tone_wav(output_path)
            return TtsResult(
                audio_path=str(output_path),
                provider=self.provider_name,
                status="fallback_tone_non_windows",
                text_path=str(text_path),
                metadata={"reason": "System.Speech is Windows-only."},
            )

        ps_script = """
param(
  [string]$TextPath,
  [string]$OutputPath
)
Add-Type -AssemblyName System.Speech
$text = Get-Content -LiteralPath $TextPath -Raw -Encoding UTF8
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 0
$synth.Volume = 95
$synth.SetOutputToWaveFile($OutputPath)
$synth.Speak($text)
$synth.Dispose()
"""
        with tempfile.TemporaryDirectory() as temp_dir:
            script_path = Path(temp_dir) / "speak.ps1"
            script_path.write_text(ps_script, encoding="utf-8")
            completed = subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(script_path),
                    str(text_path),
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=45,
            )

        if completed.returncode == 0 and output_path.exists() and output_path.stat().st_size > 44:
            return TtsResult(
                audio_path=str(output_path),
                provider=self.provider_name,
                status="ok",
                text_path=str(text_path),
                metadata={"engine": "System.Speech.Synthesis.SpeechSynthesizer"},
            )

        write_tone_wav(output_path)
        return TtsResult(
            audio_path=str(output_path),
            provider=self.provider_name,
            status="fallback_tone_after_tts_failure",
            text_path=str(text_path),
            metadata={
                "stderr": completed.stderr[-500:],
                "stdout": completed.stdout[-500:],
                "returncode": completed.returncode,
            },
        )


class TextOnlyTtsProvider:
    provider_name = "text_only"

    def synthesize(self, text: str, output_path: Path) -> TtsResult:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        text_path = output_path.with_suffix(".txt")
        text_path.write_text(text, encoding="utf-8")
        return TtsResult(
            audio_path=None,
            provider=self.provider_name,
            status="text_only",
            text_path=str(text_path),
            metadata={"reason": "TTS audio generation disabled."},
        )


def get_tts_provider(name: str) -> TtsProvider:
    normalized = name.strip().lower()
    if normalized in {"windows", "windows_sapi", "sapi", "local"}:
        return WindowsSapiTtsProvider()
    if normalized in {"none", "text", "text_only", "mock"}:
        return TextOnlyTtsProvider()
    raise ValueError(f"Unknown TTS provider: {name}")
