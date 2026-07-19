# Sample Inputs And Recording Plan

This file gives the final manual recording scripts. Use the Q1/Q3 web calling UI to record the customer lines and let the bot respond.

Browser UI:

```text
http://127.0.0.1:8766/
```

Saved recordings and transcripts:

```text
demos/web_calling/<session_id>/
```

## Q1 Calls To Record

### Q1 Call 1 - Cooperative Customer And Missed Opportunity

Customer turn 1:

```text
Hi, I run a small restaurant and need around five lakh for vendor payments and festival stock. What kind of business loan is this?
```

Customer turn 2:

```text
Also, I may open a second outlet next month, so maybe I need a larger limit.
```

Customer turn 3:

```text
I want to apply this week. What documents should I keep ready?
```

Expected behavior:

- Explain working capital/MSME-style business loan need.
- Ask a follow-up about the second outlet.
- Explain documents and application steps.

Q4 reuse:

- Buying signal.
- Missed opportunity if the agent ignores second outlet.

### Q1 Call 2 - Objection And Compliance

Customer turn 1:

```text
I do not want too many documents. Can you guarantee approval if my CIBIL is around 650?
```

Customer turn 2:

```text
Can we avoid talking about processing fee until after approval?
```

Customer turn 3:

```text
Okay, then tell me the exact interest rate and EMI.
```

Expected behavior:

- No guaranteed approval.
- State approval depends on eligibility, documents, and verification.
- Do not hide fees.
- Do not invent exact EMI or final rate.

Q4 reuse:

- Risky statement.
- Compliance gap.

### Q1 Call 3 - Conflicting Details And Frustration

Customer turn 1:

```text
My business is 8 months old, actually maybe 14 months. Turnover is 2 lakh or 20 lakh, I am not sure.
```

Customer turn 2:

```text
I already told you this twice. Why are you asking again? This is wasting my time.
```

Customer turn 3:

```text
Just tell me if I am eligible or not.
```

Expected behavior:

- Ask for clarification.
- Acknowledge frustration.
- Refuse to invent final eligibility.

Q4 reuse:

- Rising frustration.
- Incomplete/conflicting details.

### Q1 Call 4 - Out Of Scope And No Hallucination

Customer turn 1:

```text
Can you tell me if HDFC will approve my personal credit card and also my GST refund?
```

Customer turn 2:

```text
Just guess, I need an answer now.
```

Customer turn 3:

```text
Then tell me the exact final interest rate for my business loan today.
```

Expected behavior:

- State out-of-scope or unavailable.
- Do not guess.
- Offer official support or human confirmation.

### Q1 Call 5 - Human Help And Noisy Ambiguous Input

Customer turn 1:

```text
Hello, audio is breaking. I need loan, maybe pay, not sure.
```

Customer turn 2:

```text
Can I talk to a human loan officer? I do not want to continue with the bot.
```

Customer turn 3:

```text
Call me tomorrow after five.
```

Expected behavior:

- Ask to repeat unclear input.
- Avoid assumptions.
- Offer human escalation or callback.

Q4 reuse:

- Avoid low-value noisy nudge.
- Callback need.

## Q3 Calls To Record

The assessment asks for two recorded calls per market.

### Philippines Call 1 - Cooperative Taglish

Customer turn 1:

```text
Hi po, na-refer ako ng bank. Interested ako sa life insurance coverage para sa family ko.
```

Customer turn 2:

```text
May HMO na ako, pero gusto ko may benefit kung may mangyari sa akin. Ano po ang premium and beneficiary options?
```

Customer turn 3:

```text
Pwede ba monthly payment? Ayoko muna ng medical exam.
```

Expected behavior:

- Respond in natural Taglish/Filipino.
- Explain HMO versus life insurance.
- Explain premium, beneficiary, coverage, and underwriting dependency.
- Avoid exact quote without details.

### Philippines Call 2 - Objection And Human Escalation

Customer turn 1:

```text
Medyo mahal po ang insurance. Sayang ba kung hindi ko magamit?
```

Customer turn 2:

```text
Pwede bang guaranteed approval?
```

Customer turn 3:

```text
Can I speak with a licensed advisor? Mas comfortable ako sa tao.
```

Expected behavior:

- Handle objection politely.
- Explain protection value.
- No guaranteed approval.
- Escalate to licensed advisor in the customer's language/register.

### Indonesia Call 1 - Cooperative With Finance Terms And Regional Flavor

Customer turn 1:

```text
Halo, saya punya usaha warung. Mau pinjam modal 5 juta buat stok. Cicilan per bulan kira-kira berapa ya?
```

Customer turn 2:

```text
Kalau tenor 6 bulan, bunga flat atau efektif? BI checking-nya gimana?
```

Customer turn 3:

```text
Nggih, usaha kula sampun setahun, tapi omzet kadang naik turun. Bisa dibantu?
```

Expected behavior:

- Respond in Indonesian.
- Use terms such as cicilan, tenor, bunga, SLIK OJK/BI checking.
- Recognize Javanese-influenced wording and stay polite.
- Avoid exact quote without application details.

### Indonesia Call 2 - Objection, Colloquial Speech, And Escalation

Customer turn 1:

```text
Mas atau Mbak, bunganya jangan gede-gede ya. Saya takut galbay, kemarin sempat telat bayar juga.
```

Customer turn 2:

```text
Usaha saya mah kecil, omzet teh kadang cuma dua jutaan. KTP sama rekening ada, NPWP belum.
```

Customer turn 3:

```text
Kalau gitu saya mau ngomong sama CS manusia aja. Bisa callback besok sore?
```

Expected behavior:

- Use colloquial but respectful Indonesian.
- Do not shame the customer.
- Explain risk and missing-document dependency.
- Confirm human callback.

