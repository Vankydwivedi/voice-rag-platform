# Voice Agent Design

This is the first call-facing wrapper for the Lendingkart business-loan bot.

For the full STT -> agent -> TTS demo pipeline, see `docs/voice_pipeline_stt_tts_design.md`.

## Goal

The voice agent should:

- accept a caller utterance,
- mask obvious customer PII before logging,
- retrieve grounded evidence from `data/kb/master_kb.jsonl`,
- produce a short spoken answer,
- keep citations and top KB records in structured metadata,
- escalate when the retriever says the evidence is weak or risky.

## Runtime Path

1. Caller text enters `src/voice_agent/lendingkart_agent.py`.
2. The agent masks email, phone, PAN, Aadhaar, and GSTIN-like values.
3. The masked text is sent to `src/kb/retriever.py`.
4. The retriever returns an answer, citations, top records, and status.
5. The voice layer rewrites the retrieved answer into a concise spoken response.
6. The response includes:
   - `spoken_text`
   - `action`
   - `retrieval_status`
   - `human_escalation_required`
   - citations and top records for audit.

## Voice Style

The bot is concise and practical:

- no long legal explanations unless asked,
- no unsupported promises,
- no invented rates or approval guarantees,
- brief follow-up question at the end,
- human escalation if evidence is weak.

## Actions

The wrapper maps retrieval output into call actions:

- `answer_fee_or_charge`
- `guide_application`
- `answer_eligibility`
- `answer_repayment`
- `warn_customer_safety`
- `answer_question`
- `escalate_to_human`
- `clarify`

These actions make it easier to integrate with a real call system later.

## Human Escalation

If the retriever returns `human_escalation_required`, the voice agent does not answer from partial evidence. It says it should transfer or arrange a callback.

## Demo Commands

Single utterance:

```powershell
python src\voice_agent\lendingkart_agent.py --project-root . --utterance "What processing fee will I need to pay?"
```

Scenario run:

```powershell
python src\voice_agent\lendingkart_agent.py --project-root . --scenarios data\evaluation\voice_agent_scenarios.jsonl --output demos\call_results\voice_agent_scenario_results.json
```

## Current Validation

Scenario file:

- `data/evaluation/voice_agent_scenarios.jsonl`

Expected output:

- `demos/call_results/voice_agent_scenario_results.json`

The scenario test checks action classification, citation presence, and human-escalation behavior.

Latest run:

- scenarios: 6
- passed: 6
- pass rate: 1.0
- PII masking verified for phone and PAN values
- citations present for every scenario

Result file:

- `demos/call_results/voice_agent_scenario_results.json`
