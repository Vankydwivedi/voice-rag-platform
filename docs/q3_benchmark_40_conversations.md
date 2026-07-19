# Q3 Benchmark - 40 Multi-Turn Conversations

## Purpose

This benchmark tests whether the localized Q3 bots behave like local voice agents rather than literal translation systems. Each record contains a customer turn, expected bot reply, second customer turn, and expected follow-up reply.

Dataset:

`data/evaluation/q3_benchmark_40_conversations.jsonl`

## Category Counts

| Category | Count | Markets |
|---|---:|---|
| cooperative_customer | 5 | Philippines, Indonesia |
| sector_specific_objection | 5 | Philippines, Indonesia |
| mixed_english_finance_terms | 5 | Philippines, Indonesia |
| colloquial_speech | 5 | Philippines, Indonesia |
| human_escalation | 5 | Philippines, Indonesia |
| regional_accent | 5 | Indonesia |
| payment_or_renewal_difficulty | 5 | Philippines, Indonesia |
| compliance_sensitive_fallback | 5 | Philippines, Indonesia |

Total: 40 conversations.

## Configurations Expected

Philippines:

- Mode: `q3_philippines`
- Domain: life insurance / bancassurance
- Supported response registers: English, Filipino/Tagalog, natural Taglish
- Default response style: Taglish
- Preferred TTS: Filipino/Tagalog or Philippine English voice where available
- STT/ASR target: English, Filipino/Tagalog, Taglish, and code-switching

Indonesia:

- Mode: `q3_indonesia`
- Domain: consumer finance / multifinance
- Supported response registers: formal Bahasa Indonesia, colloquial Bahasa Indonesia, Javanese-influenced Indonesian
- Preferred TTS: Indonesian voice where available
- STT/ASR target: id-ID, colloquial Indonesian, finance loanwords, Javanese-influenced Indonesian

## Terminology Expected

Philippines life insurance:

- `premium`
- `policy`
- `coverage`
- `beneficiary`
- `rider`
- `ma-lapse`
- `bank referral`
- polite marker `po`

Indonesia consumer finance:

- `cicilan`
- `angsuran`
- `jatuh tempo`
- `denda`
- `DP`
- `tenor`
- `pembiayaan`
- `reschedule`

## Localization Examples

Philippines:

- Literal idea: "Your policy will lapse if you do not pay."
- Localized expected style: "Para hindi po ma-lapse ang coverage, kailangan mabayaran ang premium before the due date."
- Why: keeps common insurance terms and uses polite Taglish.

Indonesia:

- Literal idea: "Your installment is due tomorrow."
- Localized expected style: "Cicilan Bapak/Ibu perlu dibayar sebelum jatuh tempo agar tidak kena denda."
- Why: uses natural Indonesian finance terms.

Regional Indonesia:

- Literal idea: "I cannot pay this week."
- Localized expected style: "Nggih, saya paham. Saya bantu catat kendala pembayaran panjenengan."
- Why: recognizes Javanese-influenced markers while keeping the response understandable.

## Code-Switching Behavior Expected

Philippines:

- Understand mixed English and Filipino/Tagalog in one turn.
- Preserve terms such as `bank referral`, `coverage`, `premium`, `policy`, `rider`.
- Reply in natural Taglish unless the user or UI selects Filipino/Tagalog or English.

Indonesia:

- Understand Bahasa Indonesia mixed with English finance loanwords.
- Preserve `DP`, `tenor`, `reschedule`, `late fee`, and similar finance terms.
- Reply in Indonesian register, not sudden English.

## Accent Observations Expected

Indonesia regional-accent records use Javanese-influenced Indonesian markers:

- `nggih`
- `mboten`
- `kulo`
- `nopo`
- `matur nuwun`
- `panjenengan`

Expected behavior:

- Detect regional register where possible.
- Keep the answer respectful.
- Do not overuse regional words to the point that the answer becomes unnatural.

## Comparison Expectations

Strong localized behavior:

- Uses local terminology naturally.
- Uses market-appropriate politeness.
- Keeps language/register stable.
- Escalates safely in the same language/register.
- Avoids making guarantees or compliance-sensitive claims.

Weak literal-translation behavior:

- Translates English sentence structure word-for-word.
- Drops local terms.
- Falls back to English unexpectedly.
- Gives exact policy or penalty promises without authority.
- Ignores local politeness markers.

## Known Native-Speaker And Compliance Gaps

- A native Filipino/Tagalog reviewer has not yet validated every expected response.
- A native Indonesian reviewer has not yet validated every expected response.
- Javanese-influenced examples are lightweight test phrases, not full regional-language coverage.
- Life-insurance responses are not reviewed by a licensed insurance advisor.
- Consumer-finance responses are not reviewed by a compliance officer.
- Native TTS depends on installed voices; if Filipino or Indonesian voices are unavailable, the system must document fallback to the default Windows voice.
- ASR quality should be measured with real spoken audio, not only text scenarios.
