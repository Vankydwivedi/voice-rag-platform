# Q1 Knowledge-Grounded Voice Agent Evidence

## Use Case

Q1 implements a business-loan qualification and support voice agent for Lendingkart-style SME lending.

The agent can answer:

- Product questions.
- Loan amount and tenure questions.
- Eligibility questions.
- Document questions.
- Fees and charges.
- CIBIL/credit-profile questions.
- Repayment and missed-payment questions.
- Fraud/customer-safety questions.
- Human escalation requests.

## Runtime Flow

```text
Customer audio or typed text
  -> STT when audio is used
  -> PII masking
  -> retrieval from data/kb/master_kb.jsonl
  -> grounded response generation
  -> fallback or escalation when evidence is weak
  -> TTS audio response
  -> saved transcript and session JSON
```

Main files:

```text
src/voice_agent/lendingkart_agent.py
src/voice_agent/call_session.py
src/web_calling/web_call_server.py
src/kb/retriever.py
data/kb/master_kb.jsonl
```

## Why The Agent Uses Retrieval Instead Of Hardcoded FAQ Prompting

The assessment explicitly says Q1 must connect to the Q2 KB and should not hardcode all FAQs, objections, or policies in the system prompt.

Design choice:

- Product and policy facts live in `master_kb.jsonl`.
- The retriever selects source-backed records.
- The voice layer converts the retrieved answer into a short spoken response.
- The agent escalates when retrieval is weak or source warnings are risky.

Why:

- The source can be audited.
- Updating a policy does not require rewriting the prompt.
- The bot can cite where answers came from.
- It reduces invented answers.

## Conversation Actions

The voice layer maps answers into action labels:

- `answer_fee_or_charge`
- `guide_application`
- `answer_eligibility`
- `answer_repayment`
- `warn_customer_safety`
- `answer_question`
- `escalate_to_human`
- `clarify`

Why:

- Action labels make test coverage measurable.
- A real CRM or call system can later route by action.
- They separate "what the agent is doing" from the final text.

## Fallback And Escalation

The bot escalates when:

- The top retrieval score is low.
- The best record is marked `needs_review`.
- Sources conflict on values.
- The customer asks for account-specific or final approval decisions.
- The user asks for a human.

Safe fallback behavior:

- The bot says information is unavailable or requires confirmation.
- It does not guess final eligibility, exact EMI, final interest rate, or approval.
- It offers callback or human specialist transfer.

## PII Handling

The agent masks obvious:

- Phone numbers.
- Email addresses.
- PAN.
- Aadhaar.
- GSTIN-like values.

Why:

- Call transcripts are stored for evidence.
- Even test data should avoid leaking personal identifiers.

## Test Coverage

Required assessment coverage:

| Required case | Covered by |
| --- | --- |
| Cooperative customer | Q1 conversation DB and multi-turn call 001 |
| Objection | Q1 conversation DB and multi-turn call 002 |
| Incomplete/conflicting details | Q1 conversation DB and multi-turn call 003 |
| Out-of-scope question | Q1 conversation DB |
| Human-assistance request | Q1 conversation DB and multi-turn calls 002/003 |
| Information unavailable instead of invented answer | Fallback/escalation cases in Q1 conversation DB |

## Automated Conversation Analysis

Result file:

```text
demos/q1_last_push_final_v2/q1_conversation_bot_run_summary.json
```

Latest summary:

- Conversations: 40
- Turns: 120
- Good turns: 120
- Weak turns: 0
- Conversations with all 3 turns good: 40
- Average score: 0.948

Category result:

- Cooperative customer: 24 good.
- Human assistance request: 24 good.
- Incomplete or conflicting details: 24 good.
- Objection: 24 good.
- Out-of-scope question: 24 good.

Interpretation:

- This is a scripted benchmark, not a proof of all real-world behavior.
- It is useful evidence that the response routing, fallback, and action design cover the assessment cases.

## Multi-Turn Audio Simulation

Result file:

```text
demos/call_results/q1_multiturn/q1_multiturn_call_results.json
```

Scenario calls:

- `q1_call_001_cooperative`
- `q1_call_002_objection_and_safety`
- `q1_call_003_repayment_support`

Pipeline:

```text
scripted customer text -> generated customer WAV -> STT -> KB agent -> TTS response WAV
```

Latest result:

- Calls: 3
- Passed: 3
- STT provider: `windows_sapi`
- TTS provider: `windows_sapi`

Honest limitation:

- The current multi-turn audio evidence is a call simulation. Final submission should include human-recorded browser calls through the Q1 web calling UI.

## Browser Calling Evidence

The web calling UI supports:

- Microphone recording.
- Server-side STT.
- Grounded answer generation.
- TTS response audio.
- Transcript and session logging.

Stored session folder:

```text
demos/web_calling/<session_id>/
```

Files:

- `turn_XX_customer.wav`
- `turn_XX_agent_response.wav`
- `transcript.txt`
- `session.json`

## Optional Business Action

Implemented as a mock action layer through action labels and escalation/callback outputs.

Future production action:

- Create lead in CRM.
- Schedule callback.
- Push escalation webhook.
- Save preliminary eligibility summary.

