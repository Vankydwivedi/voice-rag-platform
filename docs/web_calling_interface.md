# Web Calling Interface

## Purpose

This adds a browser-based voice interface for Question 1. It is not a phone number. It is a local web calling experience where the user records a voice turn, taps send, receives a KB-grounded audio answer, then records the next turn.

The same interface can also demo the Question 3 localized bots by changing the mode selector.

## Flow

```text
browser microphone recording
  -> browser WAV audio recording
  -> Python runs faster-whisper STT on the WAV when no typed transcript is sent
  -> transcript sent to the selected agent
  -> Lendingkart KB-grounded agent or Q3 market component
  -> Windows SAPI TTS
  -> response WAV returned to browser
  -> next user turn
```

Typed text is also supported as a fallback if browser speech recognition is unavailable.

## Modes

- `Q1 Lendingkart KB`: KB-grounded business-loan voice agent with citations.
- `Q3 Philippines`: localized life-insurance / bancassurance bot connected to `data/q3_kb/philippines_life_insurance.jsonl`.
- `Q3 Indonesia`: localized consumer-finance bot connected to `data/q3_kb/indonesia_consumer_finance.jsonl`.

When a Q3 mode is selected, a response language/register selector appears:

- Philippines: Auto, Taglish, Filipino/Tagalog, English.
- Indonesia: Auto, formal Bahasa Indonesia, colloquial Bahasa Indonesia, Javanese-influenced Indonesian.

## Conversation Controls

- `Record`: starts recording and transcribing the customer turn. While recording, the button stays disabled as `Recording...` so the UI does not flicker when browser speech recognition restarts internally.
- `Send Recording`: sends the transcript and WAV audio. If the browser transcript is empty, the server tries to transcribe the WAV before answering.
- STT confidence guard: if Windows SAPI confidence is below `0.30`, the bot does not answer; the page shows what it heard and asks the user to repeat or edit.
- `Auto-record after reply`: after the agent audio finishes, the browser tries to start recording the next user turn.
- `Talk Now`: practical barge-in. If the agent is speaking, playback stops immediately and the microphone starts.
- `Record`: also stops current agent playback before listening.
- `Mic` meter: shows whether the browser is receiving microphone signal while recording.
- Listener keep-alive: if the browser ends recognition early with no speech, the page restarts listening several times instead of dropping immediately.

This is a demo-safe interruption model. It avoids keeping the microphone open while the agent is speaking, because browser speech recognition can accidentally hear the agent's own audio.

## Files

- `src/web_calling/web_call_server.py`
- `demos/web_calling/<session_id>/session.json`
- `demos/web_calling/<session_id>/transcript.txt`
- `demos/web_calling/<session_id>/turn_XX_customer.wav`
- `demos/web_calling/<session_id>/turn_XX_agent_response.wav`

## Run Command

```powershell
python src\web_calling\web_call_server.py --project-root . --host 127.0.0.1 --port 8765 --tts-provider windows_sapi
```

Then open:

```text
http://127.0.0.1:8765
```

## Demo Questions

- What processing fee will I need to pay?
- Can I apply online?
- What documents are required?
- What happens if I miss an EMI payment?
- Can I speak to a human advisor?

## Evidence Saved

Each session saves:

- user transcripts,
- customer audio recordings when available,
- grounded agent replies,
- citations,
- action labels,
- latency,
- playable response WAV files.

## Limitations

- Browser speech recognition availability depends on the browser. If it returns no text, the local server falls back to Windows SAPI STT on the saved WAV.
- This is a browser web-calling interface, not a deployed phone number.
- Browser speech recognition may use the browser vendor's online speech service.
- The backend TTS uses Windows SAPI and may sound like the installed system voice.
- Barge-in is button-driven, not fully automatic acoustic interruption.
- Windows SAPI STT is offline and demo-friendly, but it may mishear accents, noisy audio, or unsupported languages.
- Low-confidence Windows SAPI transcripts are blocked so misheard audio does not produce a confident wrong loan answer.
