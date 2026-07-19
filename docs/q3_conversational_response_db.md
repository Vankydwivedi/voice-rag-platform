# Q3 Conversational Response Database

This file documents the expected-response conversation database for the localized Q3 voice bots.

Dataset path:

`data/evaluation/q3_conversational_response_db.jsonl`

## Purpose

The older benchmark file checks whether the bot can handle different categories of input.

This database is different. It is written like real call training data:

- customer says something realistic
- bot gives the expected localized answer
- customer pushes back or clarifies
- bot responds again
- customer asks one more thing
- bot responds with the correct next action

Each conversation has 3 customer-bot exchanges, so it can be used for:

- manual voice-bot testing
- expected-answer evaluation
- prompt tuning
- localized script design
- human escalation examples
- compliance and safety review

## Record Schema

Each JSONL row is one conversation scenario.

Required fields:

| Field | Meaning |
| --- | --- |
| `id` | Stable scenario id |
| `market` | `philippines` or `indonesia` |
| `bot_mode` | UI/backend mode such as `q3_philippines` or `q3_indonesia` |
| `business_domain` | Market-specific domain |
| `category` | Scenario bucket |
| `response_register` | Expected language/register |
| `customer_situation` | Short business context |
| `expected_behavior` | Tone and guardrails for the whole scenario |
| `conversation` | Ordered customer and expected bot turns |

Bot turns contain:

| Field | Meaning |
| --- | --- |
| `expected_type` | The expected response behavior, such as `empathetic_payment_boundary` |
| `text` | The ideal bot reply |
| `expected_action` | What the bot should do next |
| `expected_terms` | Local or domain terms expected in the answer |
| `why` | Why this reply is the right one |

## Category Coverage

The dataset contains 80 conversations, balanced per market:

- 40 Philippines life-insurance conversations
- 40 Indonesia consumer-finance conversations
- 5 conversations per category per market
- 3 customer-bot exchanges per conversation
- 240 expected bot replies total

| Category | Count | What It Tests |
| --- | ---: | --- |
| `cooperative_customer` | 10 | Normal qualification and helpful customers |
| `payment_or_renewal_difficulty` | 10 | Empathy plus firm payment boundaries |
| `sector_specific_objection` | 10 | Domain-specific objections, not generic replies |
| `mixed_english_finance_terms` | 10 | Code-switching and finance terminology |
| `colloquial_speech` | 10 | Natural casual language |
| `human_escalation` | 10 | When to route to a person |
| `regional_accent` | 10 | Indonesia regional accent plus Philippines local language/provincial phrasing |
| `compliance_sensitive_fallback` | 10 | Refusals, disclosure rules, fraud, legal/claim boundaries |

Market split:

| Market | Count |
| --- | ---: |
| Philippines life insurance | 40 |
| Indonesia consumer finance | 40 |

Per-market matrix:

| Category | Philippines | Indonesia |
| --- | ---: | ---: |
| `cooperative_customer` | 5 | 5 |
| `payment_or_renewal_difficulty` | 5 | 5 |
| `sector_specific_objection` | 5 | 5 |
| `mixed_english_finance_terms` | 5 | 5 |
| `colloquial_speech` | 5 | 5 |
| `human_escalation` | 5 | 5 |
| `regional_accent` | 5 | 5 |
| `compliance_sensitive_fallback` | 5 | 5 |

## Example Expected Behavior

Customer:

`I will pay this week po, huwag muna i-cancel. Medyo short lang talaga ngayon.`

Expected bot:

`I understand po, and thank you for telling us early. Hindi ko po ma-o-override ang policy rules, so kailangan pa rin ma-settle ang premium before the due date or within any allowed grace period. If unpaid beyond that, may risk po ng lapse or reduced benefits depending on the policy.`

Why this is good:

- It is empathetic.
- It does not attack the customer.
- It does not falsely mark the payment as complete.
- It explains the consequence clearly.
- It stays in Taglish, which matches the Philippines bot.

## How To Use For Testing

For each scenario:

1. Read only the customer turns into the voice bot.
2. Compare the bot's reply against `bot_expected.text`.
3. Check whether the bot performs the same `expected_action`.
4. Check that it uses the market language/register in `response_register`.
5. Check that it avoids every item in `expected_behavior.must_not_do`.

The bot does not need to match the expected text word-for-word. It should match the same intent, tone, local terminology, and compliance boundary.

## Important Design Notes

The Philippines rows are not literal translations of the Indonesia rows. They use life-insurance concepts such as:

- premium
- beneficiary
- rider
- underwriting
- grace period
- lapse
- claim requirements
- licensed advisor

For Philippines, the `regional_accent` category is treated as local language variation and provincial phrasing, because the bot requirement is English, Filipino/Tagalog, and natural Taglish. The examples include Tagalog provincial phrasing, Bisaya-influenced Taglish, Ilocano-influenced phrasing, and Bicol-influenced phrasing, while the bot responds clearly without mocking or over-imitating the speaker.

The Indonesia rows use consumer-finance concepts such as:

- cicilan
- jatuh tempo
- denda
- tenor
- outstanding
- restrukturisasi
- virtual account
- analisis kredit

The dataset intentionally includes difficult cases where the bot should not answer directly:

- exact quote requests
- claim guarantees
- legal questions
- fake document requests
- fee waiver promises
- fraud or OTP requests
- human escalation demands

Those cases prove that the bot has a language-specific fallback and does not simply translate or hallucinate.
