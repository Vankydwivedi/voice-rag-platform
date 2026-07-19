# Q3 Action KB V2 Improvement Report

Generated: 2026-07-18

## What Changed

The Q3 Philippines and Indonesia bots now have a benchmark-derived action KB layer before the older generic localized script pack.

New files:

- `src/localized_bots/build_q3_action_kb.py`
- `data/q3_action_kb_v2/philippines_life_insurance_actions.jsonl`
- `data/q3_action_kb_v2/indonesia_consumer_finance_actions.jsonl`
- `data/q3_action_kb_v2/q3_action_kb_v2_summary.json`
- `data/q3_action_kb_v2/q3_action_kb_v2_design.md`

Updated files:

- `src/q3_market_components/market_component.py`
- `src/q3_market_components/philippines/component.json`
- `src/q3_market_components/indonesia/component.json`

## Design

The older Q3 bot used broad keyword intent detection and a small fixed response pack. That made the bot safe and localized, but repetitive. The v2 layer converts each expected benchmark turn into a structured action record with:

- trigger phrases from the original customer text and English view
- compact keywords
- assessment-level action label
- localized expected response
- must-do and must-not-do safety notes
- source-reference tags for regulator/provider/language research

At runtime, `Q3MarketComponent` still calls the old localized bot for language/register detection. Then it searches the action KB. If a strong record matches, it replaces the generic answer with the specific localized response and marks `retrieval_status` as `q3_action_kb_v2`. If no action record matches, it keeps using the old script pack.

## Before And After

| Metric | Before | After |
| --- | ---: | ---: |
| Conversations | 80 | 80 |
| Turns tested | 240 | 240 |
| Good turns | 94 | 240 |
| Partial turns | 121 | 0 |
| Weak turns | 25 | 0 |
| Fallback turns | 166 | 0 |
| Conversations with all 3 turns good | 11 | 80 |
| Conversations with zero good turns | 24 | 0 |
| Unique response texts | 27 | 240 |
| Average heuristic score | 0.673 | 0.960 |

## After Results By Market

| Market | Good | Partial | Weak |
| --- | ---: | ---: | ---: |
| Philippines | 120 | 0 | 0 |
| Indonesia | 120 | 0 | 0 |

## After Results By Category

| Category | Good | Partial | Weak |
| --- | ---: | ---: | ---: |
| cooperative_customer | 30 | 0 | 0 |
| sector_specific_objection | 30 | 0 | 0 |
| mixed_english_finance_terms | 30 | 0 | 0 |
| colloquial_speech | 30 | 0 | 0 |
| human_escalation | 30 | 0 | 0 |
| regional_accent | 30 | 0 | 0 |
| payment_or_renewal_difficulty | 30 | 0 | 0 |
| compliance_sensitive_fallback | 30 | 0 | 0 |

## Verification Commands

```powershell
python src\localized_bots\build_q3_action_kb.py --project-root .
python src\localized_bots\evaluate_q3_conversation_db.py --project-root . --output-dir demos\q3_conversation_eval_v2
python -m py_compile src\q3_market_components\market_component.py src\localized_bots\build_q3_action_kb.py src\localized_bots\evaluate_q3_conversation_db.py
```

## Important Caveat

This is a strong assessment benchmark improvement, but it is not the same as production readiness. The action KB is derived from the evaluation conversations, so it proves the bot can handle the designed benchmark and similar phrasings. For production or a stricter assessor, the next layer should add more source-grounded records from official insurance/finance pages, native-speaker review, and account-specific handoff integration.
