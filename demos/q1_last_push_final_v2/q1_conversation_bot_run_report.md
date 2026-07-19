# Q1 Conversational Holdout Evaluation

Generated UTC: `2026-07-19T00:54:07.042059+00:00`

## Scope

- Conversations: `40`
- Turns tested: `120`
- Bot tested: current Q1 Lendingkart voice agent
- This is a holdout-style dataset generated after the original Q1 KB and agent were already built.
- These conversations were not loaded into an action KB before evaluation.

## Overall Result

- Average score: `0.948`
- Good turns: `120`
- Partial turns: `0`
- Weak turns: `0`
- Conversations with all 3 turns good: `40`
- Conversations with zero good turns: `0`
- Conversations with any weak turn: `0`
- Unique actual response texts: `63`

## By Category

| Category | Good | Partial | Weak | Total |
| --- | ---: | ---: | ---: | ---: |
| cooperative_customer | 24 | 0 | 0 | 24 |
| human_assistance_request | 24 | 0 | 0 | 24 |
| incomplete_or_conflicting_details | 24 | 0 | 0 | 24 |
| objection | 24 | 0 | 0 | 24 |
| out_of_scope_question | 24 | 0 | 0 | 24 |

## By Expected Action

| Expected action | Good | Partial | Weak | Total |
| --- | ---: | ---: | ---: | ---: |
| `answer_eligibility` | 23 | 0 | 0 | 23 |
| `answer_fee_or_charge` | 10 | 0 | 0 | 10 |
| `answer_question` | 25 | 0 | 0 | 25 |
| `answer_repayment` | 11 | 0 | 0 | 11 |
| `escalate_to_human` | 30 | 0 | 0 | 30 |
| `guide_application` | 8 | 0 | 0 | 8 |
| `warn_customer_safety` | 13 | 0 | 0 | 13 |

## Main Findings

- The Q1 bot passed this holdout-style dataset under the current heuristic, but this still needs human review.
- Action mismatches: `3` out of `120` turns.
- Missing citations on non-escalation turns: `0`.
- PII masking triggered on `1` turns.
- Human escalation detected correctly on `30/30` expected escalation turns.
- Repeated response count: `57`. Lower repetition means the KB is giving more varied grounded answers.

## Weak Turns

No weak turns under the current heuristic.

## Partial Turns Sample

No partial turns under the current heuristic.

## Most Repeated Actual Responses

- `30` times: I do not want to guess on this. I found some related information, but a human specialist should confirm it before we continue. I can arrange a callback or transfer.
- `7` times: Please do not share OTPs, PAN, Aadhaar, UPI IDs, transaction IDs, bank details, or document numbers in this chat. Use only official secure channels for sensitive information. If anyone has asked you for upfront money,...
- `4` times: I cannot confirm eligibility from incomplete or conflicting details. Please confirm the applicant business, business type, turnover, vintage, and matching documents before applying. Would you like me to list the docum...
- `3` times: You can apply or review an offer, but accept only after checking the sanctioned amount, interest rate, processing fee, tenure, EMI, and agreement terms. Would you like me to explain the eligibility checks next?
- `3` times: The KB mentions customised business-loan interest rates starting from 13.5% annually, subject to profile and final offer. Would you like me to also explain how this may affect the total repayment?
- `3` times: Please use only official Lendingkart channels. Do not pay upfront money to unofficial callers, do not open suspicious links, and do not share OTPs or documents on random WhatsApp numbers. If anyone has asked you for u...
- `3` times: Repayment depends on the sanctioned amount, interest rate, tenure, and loan agreement. For account-specific repayment options, official support should confirm the next step. Would you like me to explain the next safe ...
- `2` times: This is a business loan use case, often an MSME working capital need for stock, vendor payments, operations, or expansion. The final product and offer depend on eligibility and verification. Is there anything else you...
- `2` times: The KB lists business loan tenure as minimum 2 years. If that tenure is too long for a three-month need, review the offer carefully and compare alternatives before accepting. Is there anything else you want to check a...
- `2` times: Focus on accurate business records, complete documents, stable turnover, timely repayments, and a healthy credit profile. These can support eligibility, but approval is still subject to verification. Would you like me...
