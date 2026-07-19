# Question 1 - Multi-Turn Voice Call Flow

## What Was Added

The single-turn voice pipeline has been extended into a real multi-turn call-session runner.

Pipeline:

```text
customer turn WAV
  -> Windows SAPI STT
  -> transcript
  -> KB-grounded Lendingkart agent
  -> agent response text
  -> Windows SAPI TTS
  -> agent response WAV
  -> next customer turn
```

The session keeps one call-level transcript, all per-turn STT results, agent responses, citations, response audio files, and session state.

## Files

- `src/voice_agent/call_session.py`
- `data/evaluation/q1_multiturn_call_scenarios.jsonl`
- `demos/call_results/q1_multiturn/q1_multiturn_call_results.json`

## Demo Calls

The test set contains three multi-turn calls:

- `q1_call_001_cooperative`: cooperative application, documents, and processing-fee questions.
- `q1_call_002_objection_and_safety`: fee objection, fraud-safety concern, and human callback.
- `q1_call_003_repayment_support`: missed EMI, incomplete eligibility details, and human representative request.

## Result

Latest local run:

- Calls: 3
- Passed: 3
- Pass rate: 1.0
- STT provider: `windows_sapi`
- Agent TTS provider: `windows_sapi`
- Customer audio mode: scripted caller text synthesized to WAV, then transcribed through STT.

## Run Command

```powershell
python src\voice_agent\call_session.py --project-root . --scenarios data\evaluation\q1_multiturn_call_scenarios.jsonl --output-dir demos\call_results\q1_multiturn --output-json demos\call_results\q1_multiturn\q1_multiturn_call_results.json --stt-provider windows_sapi --tts-provider windows_sapi
```

## Honest Limitation

This is now a real multi-turn audio-file call simulation, but it is still not a deployed phone number or browser microphone UI. The same loop can be connected to a web calling interface or Twilio-style phone stream later.
