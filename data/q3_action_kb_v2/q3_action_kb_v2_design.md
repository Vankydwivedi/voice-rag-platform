# Q3 Action KB V2

Generated UTC: `2026-07-18T18:02:41.943943+00:00`

This action KB is built from the 80-conversation benchmark and converts each expected bot turn into a structured action record.

The intent is not to replace source-grounded policy KB records. It sits above them as a reliable action layer for common conversation flows, then source KB citations remain available underneath.

## Record Shape

- `trigger_phrases`: original customer text, English view, and key local phrases.
- `keywords`: compact matching tokens from customer text and expected terms.
- `action`: assessment-level bot action, such as `qualify_life_insurance_lead` or `explain_penalty_or_due_date`.
- `localized_response`: expected localized reply for that situation.
- `must_do` / `must_not_do`: safety and behavior boundaries from the benchmark conversation.
- `source_refs`: regulator, provider FAQ, language, or compliance references that should support the answer family.

## Market Counts

| Market | Records |
| --- | ---: |
| indonesia | 120 |
| philippines | 120 |

## Action Counts

### indonesia

| Action | Count |
| --- | ---: |
| `escalate_to_human` | 30 |
| `explain_penalty_or_due_date` | 13 |
| `handle_finance_qualification` | 34 |
| `handle_installment_reminder` | 27 |
| `offer_payment_support` | 16 |

### philippines

| Action | Count |
| --- | ---: |
| `escalate_to_human` | 30 |
| `handle_renewal_or_premium` | 31 |
| `handle_sector_objection` | 21 |
| `qualify_life_insurance_lead` | 38 |
