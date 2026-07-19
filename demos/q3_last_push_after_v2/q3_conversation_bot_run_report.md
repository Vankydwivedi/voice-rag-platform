# Q3 Conversational Bot Run Report

Generated UTC: `2026-07-19T01:03:32.686416+00:00`

## Scope

- Scenarios: 80
- Customer turns tested: 240
- Bots tested: Q3 Philippines life insurance and Q3 Indonesia consumer finance
- Input type: text customer turns from the conversational database
- Output evaluated: actual Q3 bot response text, action, register, terms, and fallback behavior

## Overall Result

- Average heuristic score: `0.952`
- Good turns: `240`
- Partial turns: `0`
- Weak turns: `0`
- Unique actual response templates used: `232`

## Market Results

| Market | Good | Partial | Weak | Total |
| --- | ---: | ---: | ---: | ---: |
| indonesia | 120 | 0 | 0 | 120 |
| philippines | 120 | 0 | 0 | 120 |

## Category Results

| Category | Good | Partial | Weak | Total |
| --- | ---: | ---: | ---: | ---: |
| colloquial_speech | 30 | 0 | 0 | 30 |
| compliance_sensitive_fallback | 30 | 0 | 0 | 30 |
| cooperative_customer | 30 | 0 | 0 | 30 |
| human_escalation | 30 | 0 | 0 | 30 |
| mixed_english_finance_terms | 30 | 0 | 0 | 30 |
| payment_or_renewal_difficulty | 30 | 0 | 0 | 30 |
| regional_accent | 30 | 0 | 0 | 30 |
| sector_specific_objection | 30 | 0 | 0 | 30 |

## Main Findings

1. The bots can respond in the selected market language/register, especially when the UI register is explicitly set.
2. The current Q3 bots are still script-template bots, so many answers are safe but too generic compared with the new conversational DB.
3. Philippines handles basic premium, coverage, beneficiary, rider, and advisor-routing questions better than detailed claim, legal, payment hardship, or fraud cases.
4. Indonesia handles due-date, installment, denda, DP, tenor, and petugas escalation better than nuanced regional accents or document/fraud edge cases.
5. The very low unique-response count shows repetition. This is the biggest gap if the assessment expects natural 2-3 turn conversations.

## Recommended Fixes

1. Add conversation-state handling so exchange 2 and exchange 3 use earlier customer details.
2. Add category-specific response templates for payment promises, partial payment, fraud/OTP, claim guarantees, fake documents, and legal/servicing boundaries.
3. Expand the Q3 intent keywords using the actual dataset terms.
4. Add unsupported Indonesia regional variants beyond Javanese, or document them as known gaps.
5. Use the expected-response DB as a regression suite after improving the bot.

## Most Repeated Actual Responses

- `5` times: Untuk pengajuan pembiayaan, biasanya perlu informasi DP, tenor, data barang atau kendaraan, dokumen identitas, dan kemampuan membayar.
- `5` times: Untuk pengajuan, biasanya dicek DP, tenor, barang atau kendaraan yang mau dibiayai, dokumen identitas, dan kemampuan bayar.
- `1` times: Sige po, thank you for sharing. For family protection, usually tinitingnan muna kung sino ang gusto ninyong protektahan, magkano ang target coverage, at kung monthly or annual premium ang comfortable. Para ma-guide ko kayo, coverage ba i...
- `1` times: Gets ko po. For income protection, importante malaman ang approximate monthly income, existing insurance if any, at budget range. Hindi ko po kailangan ng exact private details dito. Range lang muna, like below 2k, 2k to 5k, or above 5k ...
- `1` times: Noted po, 3k monthly and no existing insurance. Good starting point po yan for basic family protection, pero final options depend on age, health declaration, and insurer underwriting. I can summarize the likely plan types and then connec...
- `1` times: Pwede po kayong mag-request ng beneficiary update sa policy servicing channel. Kailangan po munang ma-verify ang policy owner bago tanggapin ang pagbabago. Dito, maaari ko lang ipaliwanag ang general steps at hindi ko po kukunin ang buon...
- `1` times: Mas mabuti pong huwag ibigay dito ang full personal details. Para safe, gamitin natin ang official servicing form or advisor-assisted process. Usually hihingin doon ang relationship, complete name, birth date, and supporting details, per...
- `1` times: Sa maraming policy servicing requests, maaaring walang fee, pero policy-specific po ito at depende sa insurer rules. I-check po natin sa official servicing team para hindi tayo magbigay ng maling commitment. Gusto ninyo po bang i-route k...
- `1` times: Depende po sa goal. Term insurance is usually focused on protection for a fixed period. Insurance with investment component can combine protection and fund value, pero hindi guaranteed ang market-linked performance. Ang unang tanong po: ...
- `1` times: Gets po. Kung gusto ninyo ng future value, kailangan nating pag-usapan ang budget, risk tolerance, at kung gaano katagal ninyo kayang ituloy ang premium. Important din po malaman na early withdrawal or missed payments may affect benefits...

## Example Weak Turns
