# Q3 Detailed Conversation Evaluation Analysis

This report analyzes the 80 Q3 conversations after running the current Philippines and Indonesia bots. Each conversation has 3 customer questions, so the run contains 240 tested turns.

## Correctness Definitions

- `good` = strict-correct for this report. The answer matched the expected language/register, action family, key terms, and safety boundary well enough.
- `partial` = safe or language-correct, but missing important details, context, or the exact expected action.
- `weak` = clearly wrong or not useful for that test turn.
- `not-good` = partial + weak. This is the strict failure count if we demand a good answer.
- `fallback / guess equivalent` = the bot used the `I do not want to guess` style fallback or the Indonesian equivalent.

## Main Counts

- Conversations: `80`
- Turns tested: `240`
- Good turns: `94`
- Partial turns: `121`
- Weak turns: `25`
- Fallback / guess-equivalent turns: `166`
- Conversations with all 3 questions good: `11`
- Conversations with zero good answers: `24`
- Conversations where all 3 answers were fallback: `29`

## By Question Number

| Question number | Good | Partial | Weak | Not-good | Fallback / guess equivalent | Total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Q1 | 40 | 34 | 6 | 40 | 50 | 80 |
| Q2 | 26 | 42 | 12 | 54 | 59 | 80 |
| Q3 | 28 | 45 | 7 | 52 | 57 | 80 |

Interpretation: Q1 performed best. Q2 was the weakest by strict correctness and clear wrong answers. Q3 had slightly better weak count than Q2, but still used fallback heavily.

## By Market And Question Number

| Market | Question | Good | Partial | Weak | Not-good | Fallback / guess equivalent | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| philippines | Q1 | 18 | 19 | 3 | 22 | 25 | 40 |
| philippines | Q2 | 13 | 24 | 3 | 27 | 31 | 40 |
| philippines | Q3 | 13 | 26 | 1 | 27 | 33 | 40 |
| indonesia | Q1 | 22 | 15 | 3 | 18 | 25 | 40 |
| indonesia | Q2 | 13 | 18 | 9 | 27 | 28 | 40 |
| indonesia | Q3 | 15 | 19 | 6 | 25 | 24 | 40 |

## Conversation-Level Results

| Metric | Count |
| --- | ---: |
| Conversations with exactly 3 good answers | 11 |
| Conversations with exactly 2 good answers | 16 |
| Conversations with exactly 1 good answers | 29 |
| Conversations with exactly 0 good answers | 24 |
| Conversations with exactly 3 fallback answers | 29 |
| Conversations with exactly 2 fallback answers | 35 |
| Conversations with exactly 1 fallback answers | 9 |
| Conversations with exactly 0 fallback answers | 7 |

### Conversations With All 3 Answers Good

`q3_id_conv_009`, `q3_id_conv_039`, `q3_id_conv_040`, `q3_id_conv_078`, `q3_id_conv_080`, `q3_ph_conv_054`, `q3_ph_conv_055`, `q3_ph_conv_056`, `q3_ph_conv_058`, `q3_ph_conv_059`, `q3_ph_conv_060`

### Conversations With Zero Good Answers

`q3_id_conv_014`, `q3_id_conv_015`, `q3_id_conv_029`, `q3_id_conv_032`, `q3_id_conv_035`, `q3_id_conv_067`, `q3_id_conv_068`, `q3_id_conv_069`, `q3_id_conv_072`, `q3_id_conv_074`, `q3_ph_conv_003`, `q3_ph_conv_006`, `q3_ph_conv_008`, `q3_ph_conv_011`, `q3_ph_conv_012`, `q3_ph_conv_013`, `q3_ph_conv_021`, `q3_ph_conv_027`, `q3_ph_conv_045`, `q3_ph_conv_046`, `q3_ph_conv_048`, `q3_ph_conv_049`, `q3_ph_conv_050`, `q3_ph_conv_052`

### Conversations Where All 3 Answers Were Fallback

`q3_id_conv_015`, `q3_id_conv_025`, `q3_id_conv_033`, `q3_id_conv_039`, `q3_id_conv_040`, `q3_id_conv_062`, `q3_id_conv_067`, `q3_id_conv_069`, `q3_id_conv_072`, `q3_id_conv_074`, `q3_id_conv_075`, `q3_id_conv_080`, `q3_ph_conv_003`, `q3_ph_conv_006`, `q3_ph_conv_011`, `q3_ph_conv_017`, `q3_ph_conv_021`, `q3_ph_conv_022`, `q3_ph_conv_027`, `q3_ph_conv_041`, `q3_ph_conv_043`, `q3_ph_conv_045`, `q3_ph_conv_048`, `q3_ph_conv_049`, `q3_ph_conv_050`, `q3_ph_conv_052`, `q3_ph_conv_055`, `q3_ph_conv_059`, `q3_ph_conv_060`

## Market Comparison

| Market | Good | Partial | Weak | Avg score | Fallback count | Code-switch detected | Regional accent detected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| philippines | 44 | 69 | 7 | 0.677 | 89 | 27 | 0 |
| indonesia | 50 | 52 | 18 | 0.669 | 77 | 5 | 3 |

Philippines had fewer weak answers, but more fallback usage. Indonesia had more good answers, but also more weak turns, especially in human escalation and non-Javanese regional/accent cases.

## Category And Market Breakdown

| Market | Category | Good | Partial | Weak | Fallback | Total |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| philippines | colloquial_speech | 2 | 13 | 0 | 14 | 15 |
| philippines | compliance_sensitive_fallback | 11 | 0 | 4 | 9 | 15 |
| philippines | cooperative_customer | 4 | 11 | 0 | 12 | 15 |
| philippines | human_escalation | 4 | 11 | 0 | 11 | 15 |
| philippines | mixed_english_finance_terms | 6 | 8 | 1 | 10 | 15 |
| philippines | payment_or_renewal_difficulty | 3 | 10 | 2 | 11 | 15 |
| philippines | regional_accent | 14 | 1 | 0 | 10 | 15 |
| philippines | sector_specific_objection | 0 | 15 | 0 | 12 | 15 |
| indonesia | colloquial_speech | 6 | 9 | 0 | 12 | 15 |
| indonesia | compliance_sensitive_fallback | 14 | 0 | 1 | 13 | 15 |
| indonesia | cooperative_customer | 8 | 6 | 1 | 10 | 15 |
| indonesia | human_escalation | 4 | 0 | 11 | 7 | 15 |
| indonesia | mixed_english_finance_terms | 4 | 11 | 0 | 11 | 15 |
| indonesia | payment_or_renewal_difficulty | 10 | 5 | 0 | 4 | 15 |
| indonesia | regional_accent | 4 | 8 | 3 | 7 | 15 |
| indonesia | sector_specific_objection | 0 | 13 | 2 | 13 | 15 |

## Configuration Evidence

| Item | Philippines bot | Indonesia bot |
| --- | --- | --- |
| Bot name | Maya | Rani |
| Domain | Life insurance / bancassurance | Consumer finance / loans |
| Languages/registers | English, Filipino/Tagalog, Taglish | Formal Bahasa, colloquial Bahasa, finance loanwords, Javanese-influenced Indonesian |
| Default response register | Taglish | Formal Bahasa Indonesia |
| Response override | English input defaults to Taglish unless English register is explicitly selected | Auto/formal default unless colloquial or regional markers are detected/requested |
| ASR in Q3 config | transcript_file_v0 for deterministic tests; production should use multilingual ASR for en-PH, fil-PH, Taglish | transcript_file_v0 for deterministic tests; production should test Indonesian ASR with regional accents |
| TTS in Q3 config | Windows SAPI, Filipino or Philippine English voice if installed, otherwise default voice compromise | Windows SAPI, Indonesian voice if installed, otherwise default voice compromise |

## Terminology Evidence

Philippines terminology configured: `premium`, `hulog`, `policy`, `beneficiary`, `benepisyaryo`, `rider`, `lapse`, `ma-lapse`, `coverage`, `bank referral`.

Indonesia terminology configured: `cicilan`, `angsuran`, `tenor`, `denda`, `DP`, `uang muka`, `jatuh tempo`, `pembiayaan`, `finance`, `consumer finance`.

## Localization Examples

| Market | Literal idea | Localized style used | Why it matters |
| --- | --- | --- | --- |
| Philippines | Your policy will lapse if you do not pay. | Para hindi ma-lapse ang coverage, kailangan po mabayaran ang premium before the due date. | Uses Taglish, `po`, premium, due date, lapse. |
| Philippines | Do you want to add a rider? | Gusto niyo po bang magdagdag ng rider, like extra coverage for accident or critical illness? | Keeps `rider` as a natural insurance term and explains it. |
| Philippines | You were referred by the bank. | Galing ito sa bank referral, so I can explain the coverage options connected to that offer. | Uses bancassurance language rather than a literal translation. |
| Indonesia | Your installment is due tomorrow. | Cicilan Bapak jatuh tempo besok, mohon dibayar sebelum tanggal jatuh tempo agar tidak kena denda. | Uses local finance terms: cicilan, jatuh tempo, denda. |
| Indonesia | Your down payment affects the loan tenure. | DP dan tenor akan mempengaruhi simulasi pembiayaan. | Keeps common Indonesian finance loanwords DP and tenor. |
| Indonesia | I understand you cannot pay now. | Nggih, saya paham kalau saat ini belum bisa bayar. Saya bantu catat kendalanya dulu. | Uses polite Javanese-influenced marker while remaining understandable. |

## Code-Switching Behavior

- Code-switching detected overall: `32/240`.
- Philippines: `27/120`, mostly Taglish or English plus Filipino markers.
- Indonesia: `5/120`, mostly Bahasa with finance loanwords such as DP, tenor, top up, due date, late fee.

- philippines detected language distribution: `taglish`=27, `english`=70, `filipino`=23.
- philippines response register distribution: `taglish`=75, `filipino`=30, `english`=15.
- indonesia detected language distribution: `formal_bahasa_indonesia`=101, `bahasa_with_finance_loanwords`=5, `colloquial_bahasa_indonesia`=11, `javanese_influenced_indonesian`=3.
- indonesia response register distribution: `formal_id`=76, `colloquial_id`=41, `regional_javanese_id`=3.

## Accent Observations

- Indonesia regional/accent category had 15 turns: 4 good, 8 partial, 3 weak. Only 3 turns were detected as Javanese-influenced because the current config only has explicit Javanese markers such as `nggih`, `mboten`, `kulo`, and `nopo`.
- Sundanese, Betawi, Eastern Indonesia, and Minang-style rows were useful benchmark data, but the current bot mostly treated them as formal or colloquial Bahasa rather than true regional-accent input.
- Philippines regional category is better described as local language variation/provincial phrasing, not a full accent detector. It had 14 good and 1 partial, but the bot did not detect a regional accent flag because no Philippines regional-accent detector is configured.

## Known Native-Speaker And Compliance Gaps

- No native speaker has validated the Filipino/Tagalog, Taglish, Indonesian, Javanese-influenced, or provincial phrasing. Treat current localization as prototype-quality.
- Q3 benchmark run used text input, not live audio ASR, so it does not prove real acoustic accent performance.
- Native TTS is not guaranteed because Windows SAPI may fall back to the default installed voice if Filipino/Indonesian voices are unavailable.
- The bot is single-turn and template-based, so Q2 and Q3 often lose context from Q1. This is why many second/third answers become fallback.
- Compliance-sensitive replies are safe in spirit but generic. They need domain review for insurance claims, beneficiary disputes, non-disclosure, loan collections, restructuring, debt reporting, and fraud/OTP flows.
- Human escalation is simulated. There is no real CRM, ticketing queue, callback scheduler, or compliance audit trail attached yet.
- Indonesia regional coverage is incomplete beyond Javanese markers. Philippines regional support is not true dialect support; it responds in supported Taglish/Filipino instead of full Bisaya/Ilocano/Bicolano.

## What This Means

The current Q3 bots are acceptable as localization prototypes and evaluation harnesses, but not yet strong conversational agents. The biggest implementation fix is to add conversation state plus more intent templates from the expected-response database. If we improve those, the number of all-3-good conversations should rise and fallback usage should drop sharply.
