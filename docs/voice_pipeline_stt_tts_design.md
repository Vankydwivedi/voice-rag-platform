# STT And TTS Voice Pipeline

This adds the missing audio-facing pipeline around the grounded Lendingkart agent.

## Pipeline

```text
caller audio or transcript
  -> STT adapter
  -> Lendingkart grounded voice agent
  -> TTS adapter
  -> response WAV + audit JSON
```

## Files

- `src/voice_agent/stt.py`
- `src/voice_agent/tts.py`
- `src/voice_agent/voice_pipeline.py`
- `demos/transcripts/sample_processing_fee_call.txt`
- `demos/call_results/*_pipeline_result.json`
- `demos/call_results/*_response.wav`

## STT Providers

`windows_sapi`

- Local real audio-file transcription provider on Windows.
- Uses `System.Speech.Recognition.SpeechRecognitionEngine`.
- Takes a `.wav` caller audio file and returns transcript text, confidence, language/culture, recognizer metadata, and alternates.
- Best for clear English demo audio; not a replacement for production call-grade ASR on noisy calls.

`transcript_file`

- Offline deterministic provider.
- Reads a `.txt` or `.json` transcript.
- Used for repeatable local assessment demos when no real call/audio service is connected.

`openai`

- Optional real audio transcription provider.
- Requires `openai` Python package and `OPENAI_API_KEY`.
- Takes an audio file and sends it for transcription.

## TTS Providers

`windows_sapi`

- Uses the Windows built-in `System.Speech.Synthesis.SpeechSynthesizer`.
- Produces an actual `.wav` response file on Windows.
- Also writes a `.txt` sidecar with the spoken text.

`text_only`

- Writes only the spoken response text.
- Useful if audio synthesis is disabled.

## Demo Command

```powershell
python src\voice_agent\voice_pipeline.py --project-root . --session-id demo_processing_fee --transcript demos\transcripts\sample_processing_fee_call.txt --stt-provider transcript_file --tts-provider windows_sapi --output-dir demos\call_results
```

Real audio-file STT demo:

```powershell
python src\voice_agent\voice_pipeline.py --project-root . --session-id q1_audio_stt_processing_fee --audio demos\call_inputs\q1_processing_fee_question.wav --stt-provider windows_sapi --tts-provider windows_sapi --output-dir demos\call_results\q1_audio_stt
```

## Current Status

- `text -> grounded response` is implemented by `lendingkart_agent.py`.
- `audio WAV -> text` is implemented through the Windows SAPI STT adapter.
- `transcript -> text` remains available through the deterministic transcript-file STT adapter.
- `response text -> audio` is implemented through the Windows SAPI TTS adapter.
- Real call streaming/WebRTC/telephony is still an integration layer to add later.

Latest transcript-file demo:

- STT provider: `transcript_file`
- transcript: `demos/transcripts/sample_processing_fee_call.txt`
- TTS provider: `windows_sapi`
- TTS status: `ok`
- response audio: `demos/call_results/demo_processing_fee_response.wav`
- pipeline result: `demos/call_results/demo_processing_fee_pipeline_result.json`

Latest real audio-file STT demo:

- caller audio: `demos/call_inputs/q1_processing_fee_question.wav`
- STT provider: `windows_sapi`
- recognizer: Microsoft Speech Recognizer 8.0 for Windows (`en-US`)
- transcript: `What is the processing fee for a business loan`
- confidence: `0.843311369`
- grounded agent action: `answer_fee_or_charge`
- TTS provider: `windows_sapi`
- response audio: `demos/call_results/q1_audio_stt/q1_audio_stt_processing_fee_response.wav`
- pipeline result: `demos/call_results/q1_audio_stt/q1_audio_stt_processing_fee_result.json`
