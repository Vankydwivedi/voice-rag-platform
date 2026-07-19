# Extracted Table KB Coverage Checklist

Scope: this check covers only the extracted CSV tables in `data/raw/tables/`.
It does not count information available in cleaned webpages or PDF text unless noted as a follow-up source.

## Minimum Table Quality Checklist

| Check | Requirement | Status | Notes |
| --- | --- | --- | --- |
| Source traceability | Every table must map back to a source page/source id. | Pass | File names preserve source ids. Use `source_manifest.json` to attach URLs in the master KB. |
| Header/row structure | Tables must keep clear row labels and values. | Pass | All 7 tables have readable row/value structure. |
| Numeric values preserved | Amounts, percentages, tenure, and fee values must survive extraction. | Pass | Interest rates, fees, turnover, tenure, and charges are present. |
| Currency readability | INR/rupee symbols must be readable after extraction. | Warn | Several tables contain garbled rupee symbols; normalize to `INR` or `Rs.` before master KB. |
| Duplicate/noisy rows | Navigation/footer/button text should not appear as table rows. | Pass | No obvious navigation/footer rows in the extracted CSVs. |
| Conflict detection | Conflicting values must be flagged, not silently merged. | Warn | Processing fee, tenure, interest start, and loan amount vary across tables. Preserve source context. |
| Table completeness | Each important loan topic should have at least one table source or a documented non-table fallback. | Warn | Fees/charges are strong. Documents and escalation are not covered by tables and need webpage/PDF text. |

## Business Coverage Checklist

| Topic needed for loan bot | Minimum needed | Evidence from extracted tables | Status | Can answer? |
| --- | --- | --- | --- | --- |
| Loan type/product scope | Product name and secured/unsecured/collateral status. | `interest_rate_charges`: collateral `NA`; `types_of_business_loans`: collateral-free business loan. | Pass | General yes. Specific product variants need webpage text. |
| Loan amount | Min/max amount or max amount. | `interest_rate_charges`: INR 1,00,000 to INR 50,00,000; `business_loan_overview`: up to INR 50 lakh; `types`: INR 1,00,000 to INR 35,00,000. | Warn | Yes, but answer must mention source/context because one table says 35 lakh and others say 50 lakh. |
| Interest rate | Starting/range interest rate. | `schedule_of_charges`: 13.5% to 35%; `interest_rate_charges`: starting from 13.5%; `types`: starting from 17.25%. | Warn | General yes. Specific answer must cite the table used. |
| Processing fee | Fee percentage and GST note if available. | `schedule_of_charges`: max 3% excluding GST; `business_loan_overview`: up to 3%; `interest_rate_charges` and `types`: up to 4%. | Warn | Yes, but conflict must be surfaced. Use schedule of charges as strongest source for charges. |
| Tenure | Loan tenure range. | `interest_rate_charges`: 1-3 years; `types`: up to 3 years; `business_loan_overview`: minimum 2 years. | Warn | Average yes. Exact tenure answer needs source-specific wording. |
| Foreclosure/pre-closure | Whether charges apply. | `schedule_of_charges`: no foreclosure charges for unsecured business loan; `overview` and `interest_rate_charges` also say no foreclosure/pre-closure charges. | Pass | Yes, including specific fee question. |
| Late/penal charges | Penal charge formula or amount. | `schedule_of_charges`: 0.1% per day or 36% p.a. plus Rs. 300 per overdue instalment; `overview` repeats Rs. 300 and 0.1% per day. | Pass | Yes, specific answer possible. |
| Other operational charges | NACH, swap, dishonour, legal, duplicate certificates, signature verification, BPI, cooling-off period. | `schedule_of_charges` has NACH Rs. 30, swap Rs. 500, account mapping Rs. 500, dishonour charges, legal at actuals, signature verification Rs. 10, BPI cases, cooling-off retention. | Pass | Yes, strong specific answers possible. |
| Turnover/sales eligibility | Minimum turnover or sales criteria. | `overview`: INR 75,000 turnover; `interest_rate_charges`: more than INR 75,000 turnover in three months before application. | Pass | Yes. |
| Applicant age | Age range. | `eligibility_requirements`: applicants aged 18 to 65. | Pass | Yes. |
| Business vintage/profitability | Cash profit or years in business. | `eligibility_requirements`: business must have shown cash profits over past 2 years. | Pass | Yes for general criteria. |
| Business/entity type eligibility | Company type criteria. | `eligibility_requirements`: private/limited companies, self-employed professionals, proprietorship/LLP, general criteria. | Pass | Yes for average questions. |
| Income threshold | Income/profit threshold by entity type. | `eligibility_requirements`: net annual income over INR 1.5 lakh for loans up to INR 15 lakh, over INR 3 lakh beyond that for private/limited companies. | Pass | Yes, but verify with cleaned webpage text before final KB because table wording is dense. |
| Required documents | KYC, bank statement, ITR, GST, proof requirements. | Only partial mention: self-employed professionals need proof; proprietorship/LLP need P&L statements. | Gap | No, not from tables alone. Use FAQ/page text. |
| CIBIL score guidance | Score bands or minimum score guidance. | `cibil_business_loan_table_01`: 850-900 excellent, 750-850 80% chance, 700-750 secured loans, 500-700 difficult, 300-500 close to impossible. | Pass | Yes for educational/general CIBIL questions. |
| CIBIL factor weightage | Credit history/utilization/duration/misc factors. | `cibil_business_loan_table_02`: 30%, 25%, 25%, 25%. | Warn | Use cautiously. The listed weights sum to 105%, so flag as source inconsistency. |
| EMI/repayment calculation | Formula or exact EMI examples. | No calculation table. Only `overview`: monthly instalments. | Gap | Cannot answer exact EMI from tables alone. Need EMI calculator logic or formula. |
| Sanction/application timing | Timeline for sanction. | `interest_rate_charges`: within 3 working days. | Pass | Yes. |
| Fraud/customer protection | Fraud warning or safety instructions. | Not in extracted tables. | Gap | Use downloaded `Loan_Fraud_Advisory.pdf` text, not tables. |
| Human escalation/grievance | Contact/escalation path. | Not in extracted tables. | Gap | Use webpage/footer/compliance text, not tables. |

## Per-Table Assessment

| Table | Main value | Quality | Use in master KB? |
| --- | --- | --- | --- |
| `lendingkart_business_loan_overview_table_01.csv` | Quick product snapshot: interest start, processing fee, tenure, no pre-closure, turnover, amount, monthly instalments, penal charges. | Useful but has encoding artifacts and a typo in `Customsed`. | Yes, after cleanup and conflict flagging. |
| `lendingkart_eligibility_requirements_table_01.csv` | Entity-wise eligibility and general age/profit criteria. | Good structure, dense text. | Yes. |
| `lendingkart_interest_rate_charges_table_01.csv` | Interest start, tenure, collateral, amount, processing, sanction timing, turnover. | Good but conflicts with other tables for processing fee and tenure. | Yes, with source-specific wording. |
| `lendingkart_schedule_of_charges_table_01.csv` | Strongest specific fee/charge table. | Best table for precise charges. | Yes, high priority. |
| `lendingkart_types_of_business_loans_table_01.csv` | Collateral-free business loan summary. | Thin single-row table; conflicts with amount and interest start. | Maybe, lower priority. |
| `lendingkart_cibil_business_loan_table_01.csv` | CIBIL score bands and meaning. | Useful educational table. | Yes. |
| `lendingkart_cibil_business_loan_table_02.csv` | CIBIL factor weightage. | Suspicious because values total 105%. | Maybe, only with warning or exclude. |

## Question Answerability

### Average/common questions we can answer from tables

- What is the approximate business loan amount range?
- What interest rate range is shown in the schedule of charges?
- What is the processing fee according to the official schedule of charges?
- Are there foreclosure charges for unsecured business loans?
- What are late payment or penal charges?
- What turnover criterion is shown?
- What is the applicant age range?
- What types of businesses/professionals are mentioned?
- What CIBIL score ranges mean good or weak credit?
- How long can sanction take?

### Specific questions we can answer from tables

- What is the NACH registration charge?
- What is the instrument swap charge?
- What is the account mapping change charge?
- What are dishonour charges?
- What are late payment charges?
- What is the documentation charge?
- What is the cooling-off period retention rule?
- What are the listed CIBIL score bands?

### Specific questions we should not answer from tables alone

- What exact documents must every borrower upload?
- What exact EMI will I pay for a given loan amount?
- Am I eligible based on my full profile?
- What is the final interest rate for me?
- What is the latest grievance escalation path?
- Which value is final when tables conflict on processing fee, interest start, loan amount, or tenure?

For those, use cleaned webpage text, downloaded PDF text, or respond with a caveat and human escalation.

## Verdict

The extracted tables meet the minimum requirement for a business-loan voice bot that can answer average/common product, eligibility, CIBIL, and charges questions.

They are strong enough for very specific fee questions because the schedule of charges table was extracted well.

They are not sufficient alone for a production KB. Before final `master_kb.jsonl`, clean encoding, attach source URLs, preserve conflicting source-specific values, and fill non-table gaps from webpage/PDF text.
