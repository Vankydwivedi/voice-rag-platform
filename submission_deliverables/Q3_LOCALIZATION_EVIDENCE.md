# Q3 Native-Language Voice Bots Evidence

## Objective

Q3 is separate from the Q1/Q2 Lendingkart KB agent. It tests localization for real financial conversations in two markets:

- Philippines: life insurance / bancassurance.
- Indonesia: multifinance / consumer finance.

The goal is not literal translation. The bots must handle local terminology, politeness, code-switching, fallback, and market tone.

## Implemented Components

Main files:

```text
src/q3_market_components/market_component.py
src/q3_market_components/philippines/component.json
src/q3_market_components/indonesia/component.json
data/q3_kb/philippines_life_insurance.jsonl
data/q3_kb/indonesia_consumer_finance.jsonl
data/q3_action_kb_v2/
```

## Philippines Bot

Sector:

- Life insurance / bancassurance.

Supported styles:

- English.
- Filipino/Tagalog.
- Natural Taglish.

Terms used naturally:

- `premium`
- `policy`
- `beneficiary`
- `rider`
- `lapse`
- `coverage`
- `bank referral`

Use cases:

- Lead qualification.
- Renewal/premium reminder.
- Bancassurance cross-sell.
- Beneficiary/rider explanation.
- Human escalation to licensed advisor.

## Indonesia Bot

Sector:

- Multifinance / consumer finance.

Supported styles:

- Formal Bahasa Indonesia.
- Colloquial Bahasa Indonesia.
- Finance-related English loanwords.
- Javanese-influenced Indonesian markers.

Terms used naturally:

- `cicilan`
- `tenor`
- `denda`
- `DP`
- `jatuh tempo`
- `angsuran`
- `pembiayaan`

Use cases:

- Installment reminder.
- Loan follow-up.
- Payment difficulty support.
- Qualification explanation.
- Human escalation.

## ASR Configuration And Report

Deterministic benchmark provider:

- Provider: `transcript_file`.
- Purpose: repeatable text-level localization testing.

Browser/audio provider:

- Provider: `faster_whisper` where microphone turns are recorded through the web UI.
- Local CPU model: configurable through `FASTER_WHISPER_MODEL`.

Why transcript-file tests were used:

- They isolate localization logic from acoustic recognition noise.
- They make the 80-conversation benchmark deterministic.
- They are useful for checking response language, terminology, fallback, and code-switching behavior.

Known ASR gap:

- Real Filipino, Taglish, Indonesian, and Indonesian regional accents still need native-speaker audio tests.
- Production should report word error rate, per-chunk latency, and accent-specific errors.

## TTS Configuration And Report

Current provider:

- Windows SAPI.

Why:

- It produces local WAV evidence without paid services.
- It works offline for a reproducible assessment demo.

Compromise:

- If Filipino or Indonesian voices are not installed, pronunciation may not be native.
- The docs and transcripts prove language behavior, but final production should use native Filipino and Indonesian neural voices.

## Localization Examples

### Philippines

Direct translation:

```text
Your policy will lapse if you do not pay.
```

Localized:

```text
Para hindi ma-lapse ang coverage, kailangan po mabayaran ang premium before the due date.
```

Why this is better:

- Uses `po`.
- Keeps `lapse`, `coverage`, and `premium` in natural Taglish.
- Sounds like a local bancassurance reminder rather than a translated warning.

Direct translation:

```text
Do you want to add a rider?
```

Localized:

```text
Gusto niyo po bang magdagdag ng rider, like extra coverage for accident or critical illness?
```

Why this is better:

- Keeps `rider` as the market term.
- Explains the concept in a practical way.

Direct translation:

```text
You were referred by the bank.
```

Localized:

```text
Nakita ko po na galing ito sa bank referral, so I can explain the coverage options connected to that offer.
```

Why this is better:

- Uses a familiar bancassurance phrase.
- Keeps the tone polite and service-oriented.

### Indonesia

Direct translation:

```text
Your installment is due tomorrow.
```

Localized:

```text
Cicilan Bapak jatuh tempo besok, mohon dibayar sebelum tanggal jatuh tempo agar tidak kena denda.
```

Why this is better:

- Uses `cicilan`, `jatuh tempo`, and `denda`.
- Fits a formal Indonesian payment reminder.

Direct translation:

```text
Your down payment affects the loan tenure.
```

Localized:

```text
DP dan tenor akan mempengaruhi simulasi pembiayaan, jadi kita cek dulu nominal dan jangka waktunya.
```

Why this is better:

- Keeps `DP` and `tenor`, which are common finance terms in Indonesia.

Direct translation:

```text
I understand you cannot pay now.
```

Localized:

```text
Nggih, saya paham kalau saat ini belum bisa bayar. Saya bantu catat kendalanya dulu.
```

Why this is better:

- Uses a Javanese-influenced politeness marker.
- Avoids shaming the customer.

## Benchmark Results

Result file:

```text
demos/q3_last_push_after_v2/q3_conversation_bot_run_summary.json
```

Latest summary:

- Conversations: 80
- Turns: 240
- Good turns: 240
- Average score: 0.952
- Philippines: 120 good turns
- Indonesia: 120 good turns

Coverage:

| Required case | Philippines | Indonesia |
| --- | --- | --- |
| Cooperative customer | Covered | Covered |
| Sector-specific objection | Covered | Covered |
| Mixed English/finance terms | Covered | Covered |
| Colloquial speech | Covered | Covered |
| Human escalation | Covered | Covered |
| Regional accent | Simulated/localized only | Javanese-influenced Indonesian covered |

## Known Native-Speaker And Compliance Gaps

- No licensed insurance compliance review yet.
- No Indonesian finance compliance review yet.
- No native-speaker review yet.
- Filipino and Indonesian TTS voices depend on installed system voices.
- Regional accent handling is text-marker based in the benchmark; real acoustic accent testing is still needed.
- The localized KBs are compact script/action KBs, not full production policy bases.

