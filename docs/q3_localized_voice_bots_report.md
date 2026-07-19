# Question 3 - Native-Language Voice Bots

## What This Tests

Question 3 is separate from the Question 1/2 knowledge-grounded Lendingkart bot. The goal here is localized voice behavior:

- natural language and code-switching,
- local financial terminology,
- market-appropriate tone and politeness,
- language-specific fallback,
- native or closest-available TTS,
- ASR behavior notes for each market,
- Indonesian regional-accent handling.

This implementation uses separate Q3 market components with compact market-specific script KBs. It is not a production regulatory/product KB, but it gives each market its own localized knowledge records, response register controls, terminology, scripts, and source tracking.

## Implemented Bots

### Philippines Bot

- Market: Philippines
- Sector: life insurance / bancassurance
- Use case: renewal reminder and lead qualification
- Supported styles: English, Filipino/Tagalog, Taglish
- Terms handled: premium, policy, beneficiary, rider, lapse, coverage, bank referral
- Config: `src/localized_bots/configs/philippines_life_insurance.json`
- Component: `src/q3_market_components/philippines/component.json`
- Market KB: `data/q3_kb/philippines_life_insurance.jsonl`
- UI response languages: Auto, Taglish, Filipino/Tagalog, English

### Indonesia Bot

- Market: Indonesia
- Sector: multifinance / consumer finance
- Use case: installment reminder and payment support
- Supported styles: formal Bahasa Indonesia, colloquial Bahasa Indonesia, finance English loanwords, Javanese-influenced Indonesian
- Terms handled: cicilan, tenor, denda, DP, jatuh tempo, angsuran, pembiayaan
- Config: `src/localized_bots/configs/indonesia_consumer_finance.json`
- Component: `src/q3_market_components/indonesia/component.json`
- Market KB: `data/q3_kb/indonesia_consumer_finance.jsonl`
- UI response registers: Auto, formal Bahasa Indonesia, colloquial Bahasa Indonesia, Javanese-influenced Indonesian

## Q3 Component And KB Layout

```text
src/q3_market_components/
  philippines/component.json
  indonesia/component.json
  market_component.py

data/q3_kb/
  philippines_life_insurance.jsonl
  indonesia_consumer_finance.jsonl
```

Each component points to:

- the localized bot config,
- the market-specific KB file,
- supported UI response registers,
- the default response register.

The market KB records are cited in web responses as `q3_market_kb_script_pack`. They track the local intent, terminology, market ID, source ID, version, and evidence text used to support the scripted response.

## Runtime

Main runner:

```powershell
python src\localized_bots\localized_bot.py --project-root . --market philippines --scenarios data\evaluation\q3_philippines_scenarios.jsonl --output demos\call_results\q3\q3_philippines_results.json --audio-output-dir demos\call_results\q3 --transcript-output-dir demos\transcripts\q3 --tts-provider windows_sapi
```

```powershell
python src\localized_bots\localized_bot.py --project-root . --market indonesia --scenarios data\evaluation\q3_indonesia_scenarios.jsonl --output demos\call_results\q3\q3_indonesia_results.json --audio-output-dir demos\call_results\q3 --transcript-output-dir demos\transcripts\q3 --tts-provider windows_sapi
```

The runner detects:

- market,
- language/register,
- code-switching,
- regional-accent markers for Indonesia,
- intent,
- localized response action,
- financial terms used.

It writes:

- scenario result JSON,
- call transcript text files,
- TTS response text files,
- TTS response WAV files.

## ASR Configuration And Observations

Current provider:

- Provider: `transcript_file`
- Model: `transcript_file_v0`
- Purpose: deterministic offline assessment run

Philippines tests:

- `en-PH`
- `fil-PH`
- Taglish

Indonesia tests:

- formal `id-ID`
- colloquial `id-ID`
- Indonesian with English finance loanwords
- Javanese-influenced Indonesian transcript markers

Observed behavior:

- Transcript-file ASR has perfect transcript quality by design, so it does not measure acoustic recognition errors.
- Code-switching detection worked for 4 of 6 Philippines scenarios and 3 of 6 Indonesia scenarios where mixed language/loanwords were expected.
- Indonesian regional handling detected the Javanese-influenced scenario using markers such as `nggih`, `mboten`, `kulo`, and `nopo`.

Known ASR gap:

- Real microphone/call audio ASR was not acoustically tested for Filipino, Taglish, Indonesian, or regional Indonesian accents.
- Production should replace `transcript_file_v0` with a multilingual ASR provider and report word-level errors, latency, and regional accent accuracy.

## TTS Configuration And Observations

Current provider:

- Provider: `windows_sapi`
- Engine: Windows `System.Speech.Synthesis.SpeechSynthesizer`

Results:

- Philippines WAV files generated: 6/6
- Indonesia WAV files generated: 6/6

Compromise:

- Windows SAPI uses the installed system voice. If Filipino or Indonesian voices are not installed locally, pronunciation may not be native.
- The system still produces WAV evidence and text sidecars for review.

## Test Results

Philippines:

- Scenarios: 6
- Passed: 6
- Pass rate: 1.0
- WAV responses: 6
- Code-switching scenarios detected: 4

Indonesia:

- Scenarios: 6
- Passed: 6
- Pass rate: 1.0
- WAV responses: 6
- Code-switching scenarios detected: 3
- Regional-accent scenario detected: 1

Result files:

- `demos/call_results/q3/q3_philippines_results.json`
- `demos/call_results/q3/q3_indonesia_results.json`

Transcript folder:

- `demos/transcripts/q3/`

Audio folder:

- `demos/call_results/q3/`

## Localization Examples

### Philippines

Literal: "Your policy will lapse if you do not pay."

Localized: "Para hindi ma-lapse ang coverage, kailangan po mabayaran ang premium before the due date."

Why: Uses common Taglish insurance phrasing and softens the warning with polite `po`.

Literal: "Do you want to add a rider?"

Localized: "Gusto niyo po bang magdagdag ng rider, like extra coverage for accident or critical illness?"

Why: Keeps `rider` in English and explains it naturally.

Literal: "You were referred by the bank."

Localized: "Nakita ko po na galing ito sa bank referral, so I can explain the coverage options connected to that offer."

Why: Uses `bank referral` as a familiar bancassurance phrase.

### Indonesia

Literal: "Your installment is due tomorrow."

Localized: "Cicilan Bapak jatuh tempo besok, mohon dibayar sebelum tanggal jatuh tempo agar tidak kena denda."

Why: Uses natural Indonesian finance terms: `cicilan`, `jatuh tempo`, and `denda`.

Literal: "Your down payment affects the loan tenure."

Localized: "DP dan tenor akan mempengaruhi simulasi pembiayaan, jadi kita cek dulu nominal dan jangka waktunya."

Why: Keeps common finance loanwords `DP` and `tenor` instead of forcing formal equivalents.

Literal: "I understand you cannot pay now."

Localized: "Nggih, saya paham kalau saat ini belum bisa bayar. Saya bantu catat kendalanya dulu."

Why: Uses a respectful Javanese-influenced marker while keeping the answer understandable in Indonesian.

## Required Coverage Mapping

- Cooperative customer: `ph_001`, `id_001`
- Sector-specific objection: `ph_002`, `id_002`
- Mixed English / finance terms: `ph_004`, `id_003`, `id_004`
- Colloquial speech: `ph_005`, `id_002`, `id_003`
- Human escalation: `ph_006`, `id_005`
- Indonesian regional accent: `id_006`

## Known Gaps

- No native-speaker review yet.
- No compliance review by licensed insurance or finance experts.
- TTS voice may not be native if Filipino/Indonesian voices are not installed on the machine.
- Real acoustic ASR quality is not measured; transcript-file ASR is used for deterministic local tests.
- No live telephony/WebRTC connection for these Q3 localized bots yet.
