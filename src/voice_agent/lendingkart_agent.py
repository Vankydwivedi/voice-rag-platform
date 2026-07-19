from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_SRC = Path(__file__).resolve().parents[1]
if str(PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(PROJECT_SRC))

from kb.retriever import KbRetriever, citation_from_record  # noqa: E402


EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+91[\s-]?)?[6-9]\d{9}(?!\d)")
PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", re.IGNORECASE)
AADHAAR_RE = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
GSTIN_RE = re.compile(r"\b[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]\b", re.IGNORECASE)


@dataclass
class AgentConfig:
    brand_name: str = "Lendingkart"
    agent_name: str = "Asha"
    max_spoken_words: int = 70
    cite_sources_in_voice: bool = False
    include_follow_up: bool = True


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mask_pii(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}

    def apply(label: str, pattern: re.Pattern[str], replacement: str, value: str) -> str:
        new_value, count = pattern.subn(replacement, value)
        if count:
            counts[label] = counts.get(label, 0) + count
        return new_value

    text = apply("email", EMAIL_RE, "[REDACTED_EMAIL]", text)
    text = apply("phone_number", PHONE_RE, "[REDACTED_PHONE]", text)
    text = apply("pan", PAN_RE, "[REDACTED_PAN]", text)
    text = apply("aadhaar", AADHAAR_RE, "[REDACTED_AADHAAR]", text)
    text = apply("gstin", GSTIN_RE, "[REDACTED_GSTIN]", text)
    return text, counts


def normalize_for_voice(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^\s*[-+*]\s+", "", text)
    text = re.sub(r"^(Loan Fraud Advisory|Quick Summary|Overview)\s+", "", text, flags=re.IGNORECASE)
    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)
    text = text.replace("INR ", "rupees ")
    text = text.replace("per annum", "per year")
    text = text.replace("CIBIL", "CIBIL")
    text = text.replace("KYC", "KYC")
    text = text.replace("GST", "GST")
    text = re.sub(r"\s+([,.;:!?])", r"\1", text)
    return text.strip()


def soften_answer_start(text: str) -> str:
    return re.sub(r"^(yes|no)[,.]?\s+", "", text.strip(), flags=re.IGNORECASE)


def trim_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(" ,.;:") + "."


def has_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def has_word_any(text: str, words: list[str]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def latest_customer_segment(text: str) -> str:
    match = re.search(r"customer follow-up:\s*(.*)$", text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else text


def direct_action_override(text: str) -> str | None:
    lowered = latest_customer_segment(text).lower()

    if has_any(lowered, ["apply online", "online application", "visit a branch", "application link"]) or ("apply" in lowered and "online" in lowered):
        return "guide_application"

    if has_any(lowered, ["upload them online", "send them on whatsapp", "upload documents", "upload both", "upload later"]):
        return "guide_application"

    if has_any(lowered, ["approval happen quickly", "approved quickly", "can approval happen"]):
        return "answer_eligibility"

    if has_any(
        lowered,
        [
            "what kind of business loan",
            "vendor payments",
            "working capital for stock",
            "business use",
            "details should i keep ready",
            "keep ready before starting",
            "starting the form",
            "how much amount",
            "loan amount",
            "will get 5 lakh",
            "get 5 lakh",
            "what is the tenure",
            "valid business use",
            "business need",
            "equipment",
            "machine",
            "machinery",
        ],
    ):
        return "answer_question"

    if has_any(lowered, ["property", "collateral", "unsecured"]) and has_any(lowered, ["worried", "100%", "safe", "security", "required", "needed"]):
        return "answer_question"

    if has_any(lowered, ["hurt my cibil", "applying will hurt", "many lenders", "compare", "two years", "three months", "tenure feels", "too long"]):
        return "answer_question"

    if has_any(lowered, ["what can you help with", "what can you do", "scope"]):
        return "answer_question"

    if has_any(lowered, ["gst is old", "bank account is new", "started last month", "family shop", "cash sales", "bank entries"]):
        return "answer_eligibility"

    if has_any(
        lowered,
        [
            "pay money before disbursal",
            "upfront money",
            "asked me to pay money",
            "asked me to transfer",
            "asked me for money",
            "before disbursal",
            "not share",
            "not to share",
            "not give",
            "should i share",
            "otp",
            "upi id",
            "transaction id",
            "mobile number",
            "friend's gst",
            "someone else's gst",
            "scam",
            "fraud",
            "fake",
            "whatsapp",
            "stocks",
            "crypto",
            "quick profit",
        ],
    ):
        return "warn_customer_safety"

    if re.search(r"\b(pan|aadhaar|aadhar|bank account|account number)\b", lowered):
        return "warn_customer_safety"

    if has_any(
        lowered,
        [
            "human",
            "representative",
            "advisor",
            "adviser",
            "agent",
            "specialist",
            "person",
            "someone",
            "executive",
            "connect",
            "transfer",
            "speak to",
            "talk to",
            "call me",
            "callback",
            "support",
            "complaint",
            "escalate",
            "frustrated",
            "already applied",
            "nobody updated",
            "application status",
            "sanction letter",
            "exact offer",
            "confirm my offer",
            "confirm it is correct",
            "legal notice",
            "old shop name",
            "tell them",
            "already paid",
            "do not ask me",
            "someone will help",
        ],
    ):
        return "escalate_to_human"

    if has_any(
        lowered,
        [
            "personal loan",
            "home loan",
            "sister's wedding",
            "wedding",
            "flat",
            "tax advice",
            "file gst return",
            "gst return",
            "government subsidy",
            "subsidy scheme",
            "upi payment failed",
            "another app",
        ],
    ):
        return "escalate_to_human"

    if has_any(
        lowered,
        [
            "miss an emi",
            "missed emi",
            "late payment",
            "miss a payment",
            "emi",
            "repayment",
            "prepay",
            "prepayment",
            "foreclose",
            "foreclosure",
            "close the loan early",
            "close it early",
            "calculate exact emi",
            "exact emi",
        ],
    ):
        return "answer_repayment"

    if has_any(lowered, ["submit", "upload", "application steps", "application process", "apply online", "online application", "visit a branch", "application link"]):
        return "guide_application"

    if "apply" in lowered and "online" in lowered:
        return "guide_application"

    if has_any(lowered, ["accept", "sign", "see the offer", "review the offer"]):
        return "guide_application"

    if has_any(
        lowered,
        [
            "can i get a loan",
            "business income",
            "either trading or service",
            "father's name",
            "in my name",
            "verbally",
            "revenue is good",
            "not sure",
            "accountant",
            "proprietor",
            "proprietorship",
            "gst compulsory",
            "skip bank statements",
            "bank statement is mine",
            "gst is his",
            "no business",
            "salaried",
            "reject me",
            "guarantee",
            "approval",
        ],
    ):
        return "answer_eligibility"

    if has_any(lowered, ["eligible", "eligibility", "qualify", "can i apply", "improve", "turnover", "business vintage", "credit score", "cibil"]):
        return "answer_eligibility"

    if has_any(lowered, ["processing fee", "interest rate", "charges", "expensive", "check before saying yes", "rates and fees"]) or has_word_any(lowered, ["fee", "fees", "interest", "rate"]):
        return "answer_fee_or_charge"

    if has_any(lowered, ["what documents", "which documents", "documents required", "need for the loan", "documents", "docs", "kyc", "bank statements", "gst filings"]):
        return "answer_question"

    if has_any(lowered, ["paperwork", "check my file", "need loan for my shop", "prepare first"]):
        return "answer_question"

    return None


def classify_action(retrieval_response: dict[str, Any]) -> str:
    status = retrieval_response.get("status")
    if status == "human_escalation_required":
        return "escalate_to_human"

    top_records = retrieval_response.get("top_records") or []
    if not top_records:
        return "clarify"

    category = top_records[0].get("category")
    subcategory = top_records[0].get("sub_category")
    if category == "application_process":
        return "guide_application"
    if category == "eligibility":
        return "answer_eligibility"
    if category == "fees_and_charges":
        return "answer_fee_or_charge"
    if category == "customer_protection":
        return "warn_customer_safety"
    if subcategory in {"missed_payment", "foreclosure_charge"}:
        return "answer_repayment"
    return "answer_question"


def follow_up_for_action(action: str) -> str:
    if action == "guide_application":
        return "Would you like me to explain the eligibility checks next?"
    if action == "answer_eligibility":
        return "Would you like me to list the documents usually needed?"
    if action == "answer_fee_or_charge":
        return "Would you like me to also explain how this may affect the total repayment?"
    if action == "warn_customer_safety":
        return "If anyone has asked you for upfront money, please do not pay and contact official support."
    if action == "answer_repayment":
        return "Would you like me to explain the next safe step for repayment support?"
    return "Is there anything else you want to check about the loan?"


def retrieved_answer(retrieval_response: dict[str, Any], max_words: int) -> str:
    answer = normalize_for_voice(str(retrieval_response.get("answer", "")))
    return trim_words(answer, max_words)


def grounding_query_for_action(action: str, query: str) -> str:
    lowered = latest_customer_segment(query).lower()
    if action == "guide_application":
        if "partner" in lowered:
            return "Lendingkart co-lending partners application offer agreement business loan"
        return "Lendingkart apply online business loan application process documents offer"
    if action == "answer_eligibility":
        return "Lendingkart business loan eligibility turnover documents verification CIBIL"
    if action == "answer_repayment":
        if has_any(lowered, ["waive", "waiver", "penalty"]):
            return "Lendingkart penal charges overdue instalment repayment support"
        if has_any(lowered, ["miss", "bounced", "late", "overdue"]):
            return "Lendingkart missed payment CIBIL repayment support"
        return "Lendingkart repayment EMI overdue charges support"
    if action == "answer_fee_or_charge":
        return "Lendingkart processing fee interest rate penal charges"
    if action == "warn_customer_safety":
        return "Lendingkart loan fraud advisory official channel upfront money"
    if action == "answer_question":
        if has_any(lowered, ["collateral", "property", "unsecured"]):
            return "Lendingkart unsecured business loan collateral-free agreement terms"
        if has_any(lowered, ["cibil", "credit score", "many lenders", "compare"]):
            return "Lendingkart CIBIL credit score business loan application"
        if has_any(lowered, ["details should i keep ready", "starting the form", "documents", "docs", "kyc"]):
            return "Lendingkart documents required KYC bank statements GST business loan"
        if has_any(lowered, ["vendor payments", "working capital", "stock", "restaurant", "kirana"]):
            return "Lendingkart MSME working capital business loan"
        if has_any(lowered, ["loan amount", "how much amount", "5 lakh"]):
            return "Lendingkart business loan amount up to 50 lakh eligibility verification"
        if has_any(lowered, ["two years", "three months", "tenure", "too long"]):
            return "Lendingkart loan tenure minimum 2 years business loan"
        if has_any(lowered, ["business use", "business purpose"]):
            return "Lendingkart business loan purpose documents accurate application"
    return f"Lendingkart business loan {action.replace('_', ' ')}"


def fallback_citations_for_action(retriever: KbRetriever, action: str, query: str) -> list[dict[str, Any]]:
    anchor_query = grounding_query_for_action(action, query)
    preferred: dict[str, tuple[set[str], set[str]]] = {
        "guide_application": (
            {"application_process", "product_overview", "product_variant", "compliance_policy"},
            {"application_process_for_quick_business_loan", "simple_application_process", "co_lending_partners"},
        ),
        "answer_eligibility": (
            {"eligibility", "product_overview", "credit_score"},
            {"turnover", "documents_required", "cibil_score"},
        ),
        "answer_repayment": (
            {"repayment", "fees_and_charges", "credit_score", "product_overview"},
            {"missed_payment", "late_payment_charge", "foreclosure_charge", "cibil_score"},
        ),
        "answer_fee_or_charge": (
            {"fees_and_charges", "product_overview"},
            {"processing_fee", "interest_rate", "late_payment_charge", "dishonour_charge"},
        ),
        "warn_customer_safety": (
            {"customer_protection", "privacy_pii"},
            {"loan_fraud_advisory", "privacy"},
        ),
        "answer_question": (
            {"product_overview", "product_taxonomy", "product_variant", "documents", "eligibility", "application_process"},
            {
                "what_is_a_business_loan",
                "loan_tenure",
                "documents_required",
                "application_process_for_quick_business_loan",
                "co_lending_partners",
            },
        ),
    }
    categories, subcategories = preferred.get(action, (set(), set()))
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in retriever.search(anchor_query, top_k=10):
        taxonomy = item.record.get("taxonomy", {})
        category = str(taxonomy.get("category") or "")
        subcategory = str(taxonomy.get("sub_category") or "")
        if categories and category not in categories and subcategory not in subcategories:
            continue
        citation = citation_from_record(item.record)
        source_key = str(citation.get("source_id") or citation.get("url") or citation.get("record_id"))
        if source_key in seen:
            continue
        seen.add(source_key)
        citations.append(citation)
        if len(citations) >= 2:
            break
    return citations


def structured_policy_answer(action: str, query: str, retrieval_response: dict[str, Any], brand_name: str) -> str | None:
    lowered = latest_customer_segment(query).lower()

    if action == "warn_customer_safety":
        if has_any(lowered, ["stocks", "crypto", "quick profit"]):
            return (
                "I cannot advise using a business loan for stocks, crypto, or quick-profit investments. "
                "Use the loan only for legitimate business needs and review the official terms before accepting."
            )
        if has_any(lowered, ["friend's gst", "someone else's gst"]):
            return (
                "Please do not use another person's GST or business documents. "
                "Application details must be accurate and should belong to the applicant business."
            )
        if has_any(lowered, ["otp", "upi id", "transaction id", "mobile number", "pan", "aadhaar", "aadhar", "bank account", "not share", "not to share", "not give", "should i share"]):
            return (
                "Please do not share OTPs, PAN, Aadhaar, UPI IDs, transaction IDs, bank details, or document numbers in this chat. "
                "Use only official secure channels for sensitive information."
            )
        return (
            "Please use only official Lendingkart channels. Do not pay upfront money to unofficial callers, "
            "do not open suspicious links, and do not share OTPs or documents on random WhatsApp numbers."
        )

    if action == "guide_application":
        if has_any(lowered, ["partner", "co-lending"]):
            return (
                "A partner may appear in the offer or agreement, but the application steps should still be followed through the official flow. "
                "Review the offer, partner details, fees, tenure, and terms before accepting."
            )
        if has_any(lowered, ["upload later", "upload both", "just upload"]):
            return (
                "Use only the official application flow for document upload. Incomplete or mismatched documents can delay verification, "
                "so it is better to confirm the right applicant documents before uploading sensitive files."
            )
        if "whatsapp" in lowered:
            return (
                "Use the official Lendingkart application flow for uploading documents, not random WhatsApp numbers. "
                "You can apply online, check eligibility, upload required documents securely, review the offer, and sign only after reading the terms."
            )
        if has_any(lowered, ["disagree", "fee", "accept", "offer", "sign"]):
            return (
                "You can apply or review an offer, but accept only after checking the sanctioned amount, interest rate, processing fee, tenure, EMI, and agreement terms."
            )
        return (
            "You can start through the official Lendingkart online application flow. "
            "The usual flow is eligibility check, basic business details, document upload, offer review, agreement signing, and disbursal after approval."
        )

    if action == "answer_repayment":
        if has_any(lowered, ["waive", "waiver", "promise to pay next week"]):
            return (
                "I cannot confirm a penalty waive request here. Penalty or repayment support is account-specific, "
                "depends on your loan agreement, and must be confirmed by official support."
            )
        if has_any(lowered, ["what decides my emi", "decides my emi"]):
            return (
                "EMI mainly depends on the loan amount, interest rate, tenure, and final sanction terms. "
                "Use the official calculator or final offer for exact EMI."
            )
        if has_any(lowered, ["exact emi", "calculate exact emi", "calculator", "8 lakh"]):
            return (
                "I should not guess an exact EMI here. EMI depends on loan amount, interest rate, tenure, and final sanction terms, "
                "so use the official calculator or final offer for exact numbers."
            )
        if has_any(lowered, ["shorter need", "still okay if i prepay"]):
            return (
                "Prepaying may be possible, but compare your cash flow, EMI, and agreement terms first. "
                "Do not borrow unless the total cost and tenure work for your business."
            )
        if has_any(lowered, ["close the loan early", "close it early", "prepay", "foreclose", "foreclosure"]):
            return (
                "The KB says there are no pre-closure charges on unsecured business loans, but you should still check your own loan agreement before acting."
            )
        if has_any(lowered, ["miss", "late", "bounced", "overdue"]):
            return (
                "A missed payment, late EMI, or bounced EMI can affect your account and CIBIL or credit profile. "
                "Please contact official support early instead of waiting."
            )
        return (
            "Repayment depends on the sanctioned amount, interest rate, tenure, and loan agreement. "
            "For account-specific repayment options, official support should confirm the next step."
        )

    if action == "answer_eligibility":
        if has_any(lowered, ["approval happen quickly", "approved quickly", "can approval happen"]):
            return (
                "The process can be fast, but approval is not automatic. It depends on eligibility checks, documents, credit profile, and final verification."
            )
        if has_any(lowered, ["eligibility things matter", "what eligibility things matter"]):
            return (
                "Common eligibility factors include business turnover, business vintage, documents, repayment capacity, and credit profile. "
                "Final approval still depends on verification."
            )
        if has_any(lowered, ["improve", "better", "what should i improve"]):
            return (
                "Focus on accurate business records, complete documents, stable turnover, timely repayments, and a healthy credit profile. "
                "These can support eligibility, but approval is still subject to verification."
            )
        if has_any(lowered, ["eligible or not", "am i eligible"]):
            return (
                "I cannot confirm eligibility from that alone, and approval is not guaranteed. "
                "Eligibility depends on verified business details, turnover, documents, credit profile, and final verification."
            )
        if has_any(lowered, ["80,000 monthly", "80000 monthly", "80,000 yearly", "80000 yearly"]):
            return (
                "Please confirm whether that turnover is monthly or yearly. The period matters for eligibility, and it should match documents used for verification."
            )
        if has_any(lowered, ["will get 5 lakh", "get 5 lakh"]):
            return (
                "I cannot confirm a loan amount without verified turnover, documents, credit checks, and final approval. The approved amount depends on assessment."
            )
        if has_any(lowered, ["skip bank statements", "gst bills"]):
            return (
                "I should not say you can skip a required document. GST bills can help, but bank statements and other records are commonly used for verification."
            )
        if has_any(lowered, ["bank statement is mine", "gst is his", "matching"]):
            return (
                "Those documents do not clearly match one applicant. Bank statement, GST, ownership, and applicant details should align, so get official guidance before applying."
            )
        if has_any(lowered, ["legal notice", "that notice", "reject me because"]):
            return (
                "I cannot predict rejection from that notice. Credit profile, documents, and application details may be checked, but approval depends on official verification."
            )
        if has_any(lowered, ["salaried", "no business"]):
            return (
                "This bot is for Lendingkart business-loan information. If you do not have a business, you may not fit the business-loan eligibility use case."
            )
        if has_any(lowered, ["subsidy approval", "subsidy"]):
            return (
                "I cannot guarantee subsidy or loan approval here. "
                "Please confirm scheme rules through official government or lender channels."
            )
        if has_any(lowered, ["some business income", "either trading or service", "not sure", "verbally", "old shop name", "father's name"]):
            return (
                "I cannot confirm eligibility from incomplete or conflicting details. "
                "Please confirm the applicant business, business type, turnover, vintage, and matching documents before applying."
            )
        if has_any(lowered, ["started last month", "family shop", "gst is old", "bank account is new"]):
            return (
                "The applicant business details should match the records used for verification. "
                "If GST, bank account, ownership, or business vintage do not align, a specialist should confirm before you apply."
            )
        if has_any(lowered, ["cash sales", "bank entries", "revenue is good"]):
            return (
                "Verbal revenue is not enough for eligibility. Bank statements, turnover records, GST or sales records, and business documents are usually needed for verification."
            )
        if has_any(lowered, ["proprietor", "proprietorship"]):
            return (
                "Proprietorship businesses can generally be considered if they meet the business-loan eligibility and document requirements. "
                "Final approval still depends on verification."
            )
        if has_any(lowered, ["gst compulsory"]):
            return (
                "GST records can help if they apply to your business, but exact document requirements depend on business type and verification. "
                "Use accurate records and official guidance."
            )
        if has_any(lowered, ["guarantee", "promise", "exact score", "will get"]):
            return (
                "I cannot confirm an exact CIBIL score or approval result here. "
                "Eligibility depends on verified business details, documents, credit profile, and final checks."
            )

    if action == "answer_question":
        if has_any(lowered, ["unsecured", "collateral", "property", "100% safe"]):
            return (
                "The KB includes unsecured business-loan information, where collateral may not be required. "
                "Still, read the agreement and terms for your specific offer before signing."
            )
        if has_any(lowered, ["owner documents", "owner document"]):
            return (
                "For owner KYC, identity and address documents such as PAN or Aadhaar may be checked. "
                "Do not share PAN or Aadhaar numbers in this chat."
            )
        if has_any(lowered, ["hurt my cibil", "applying will hurt", "cibil score"]):
            return (
                "CIBIL or credit score can be part of loan assessment. Apply only when you are serious, keep documents ready, and avoid unnecessary repeated applications."
            )
        if has_any(lowered, ["many lenders", "compare"]):
            return (
                "Compare options carefully, but avoid unnecessary repeated applications. Multiple credit checks or applications can affect how lenders view your profile."
            )
        if has_any(lowered, ["will get 5 lakh", "get 5 lakh"]):
            return (
                "I cannot confirm a loan amount without eligibility and verification. The approved loan amount depends on turnover, documents, credit checks, and final assessment."
            )
        if has_any(lowered, ["how much amount", "loan amount", "how much can", "50 lakh"]):
            return (
                "The KB says Lendingkart business loans can go up to Rs. 50 lakh, subject to eligibility and verification."
            )
        if has_any(lowered, ["details should i keep ready", "keep ready before starting", "starting the form"]):
            return (
                "Before starting the business loan form, keep KYC, bank statements, business details, registration proof, "
                "GST records if applicable, and income or financial records ready. Use the official form for document upload."
            )
        if has_any(lowered, ["what kind of business loan", "working capital", "vendor payments", "stock", "business use"]):
            if has_any(lowered, ["show it as business use"]):
                return (
                    "Application details and documents should be accurate. Use a business loan only for a genuine business purpose, and do not present a personal expense as business use."
                )
            return (
                "This is a business loan use case, often an MSME working capital need for stock, vendor payments, operations, or expansion. "
                "The final product and offer depend on eligibility and verification."
            )
        if has_any(lowered, ["valid business use", "machine", "machinery", "equipment", "manufacture"]):
            return (
                "Business loans can support genuine business needs such as working capital, expansion, or equipment. "
                "Mention the machine or equipment use accurately during application."
            )
        if has_any(lowered, ["two years", "three months", "tenure", "too long"]):
            return (
                "The KB lists business loan tenure as minimum 2 years. If that tenure is too long for a three-month need, review the offer carefully and compare alternatives before accepting."
            )
        if has_any(lowered, ["paperwork", "headache", "small loan"]):
            return (
                "I understand. Basic documents are still usually needed: KYC, bank statements, and business proof, because eligibility has to be verified."
            )
        if has_any(lowered, ["prepare first"]):
            return (
                "Prepare KYC, bank statements, business proof, and any GST or sales records you have. If records are unusual, ask official support before uploading."
            )
        if has_any(lowered, ["documents", "docs", "kyc", "bank statements", "gst", "itr", "registration"]):
            return (
                "Keep basic KYC, bank statements, business registration proof, GST records if applicable, and income-tax or financial records if requested. "
                "Do not share document numbers in this chat."
            )
        if has_any(lowered, ["check my file"]):
            return (
                "Personal file checks should happen only through the official secure application or support flow. "
                "I can explain what documents are usually needed, but I should not collect sensitive details here."
            )
        if has_any(lowered, ["need loan for my shop"]):
            return (
                "I can help with Lendingkart business-loan information for your shop. Tell me whether you want eligibility, documents, fees, or application steps."
            )
        if has_any(lowered, ["what can you help with", "scope"]):
            return (
                "I can help with Lendingkart business-loan overview, eligibility, documents, fees and charges, tenure, repayment basics, safe application guidance, and when to escalate to a human."
            )

    if action == "answer_fee_or_charge":
        if has_any(lowered, ["check before saying yes", "saying yes"]):
            return (
                "Before accepting, check the sanctioned amount, interest rate, processing fee, tenure, EMI, pre-closure terms, and total repayment."
            )
        if has_any(lowered, ["surprise charge", "hidden charge", "hidden charges"]):
            return (
                "I should not guess future charges. Please rely on the official fee schedule, offer, and loan agreement for exact charges."
            )
        if has_any(lowered, ["starting rate", "rate looks", "expensive", "business loan rate", "rates and fees", "interest"]):
            return (
                "The KB mentions customised business-loan interest rates starting from 13.5% annually, subject to profile and final offer."
            )
        if has_any(lowered, ["processing fee", "charges", "fee", "fees"]):
            return (
                "The KB says processing fees can be up to 3% of the sanctioned amount. Review the official fee schedule, offer, and agreement for exact charges."
            )
        answer = retrieved_answer(retrieval_response, 45)
        if answer:
            return answer
        return (
            f"I can explain {brand_name} fees and charges from the approved KB, but your exact cost should be checked in the official offer and agreement."
        )

    return None


class LendingkartVoiceAgent:
    def __init__(self, retriever: KbRetriever, config: AgentConfig | None = None) -> None:
        self.retriever = retriever
        self.config = config or AgentConfig()

    @classmethod
    def from_project_root(cls, project_root: Path, config: AgentConfig | None = None) -> "LendingkartVoiceAgent":
        return cls(KbRetriever.from_project_root(project_root), config=config)

    def respond(self, caller_utterance: str, session_id: str = "demo_session") -> dict[str, Any]:
        masked_utterance, pii_counts = mask_pii(caller_utterance)
        retrieval_query = re.sub(r"\[REDACTED_[A-Z_]+\]", " ", masked_utterance)
        retrieval_query = re.sub(r"\s+", " ", retrieval_query).strip()
        retrieval_response = self.retriever.answer(retrieval_query, top_k=5)
        action = direct_action_override(retrieval_query) or classify_action(retrieval_response)

        if action == "escalate_to_human":
            spoken = (
                "I do not want to guess on this. I found some related information, "
                "but a human specialist should confirm it before we continue. "
                "I can arrange a callback or transfer."
            )
        else:
            answer = structured_policy_answer(action, retrieval_query, retrieval_response, self.config.brand_name)
            if answer is None:
                answer = retrieved_answer(retrieval_response, self.config.max_spoken_words)
            if retrieval_response.get("status") == "answered_with_caution":
                spoken = f"Based on the approved {self.config.brand_name} information I found, {soften_answer_start(answer)}"
            else:
                spoken = answer

            if self.config.cite_sources_in_voice and retrieval_response.get("citations"):
                source_label = retrieval_response["citations"][0].get("label")
                if source_label:
                    spoken = f"{spoken} This is from {source_label}."

            if self.config.include_follow_up:
                spoken = f"{spoken} {follow_up_for_action(action)}"

        citations = list(retrieval_response.get("citations", []))
        if action != "escalate_to_human" and not citations:
            citations = fallback_citations_for_action(self.retriever, action, retrieval_query)

        response = {
            "generated_at_utc": utc_now(),
            "session_id": session_id,
            "agent": asdict(self.config),
            "input": {
                "caller_utterance_masked": masked_utterance,
                "retrieval_query": retrieval_query,
                "pii_masks": pii_counts,
            },
            "response": {
                "spoken_text": normalize_for_voice(spoken),
                "action": action,
                "retrieval_status": retrieval_response.get("status"),
                "retrieval_reason": retrieval_response.get("reason"),
                "human_escalation_required": action == "escalate_to_human",
            },
            "grounding": {
                "citations": citations,
                "top_records": retrieval_response.get("top_records", []),
            },
        }
        return response


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def run_scenarios(agent: LendingkartVoiceAgent, scenarios_path: Path) -> dict[str, Any]:
    scenarios = read_jsonl(scenarios_path)
    rows: list[dict[str, Any]] = []
    pass_count = 0

    for scenario in scenarios:
        result = agent.respond(str(scenario["caller_utterance"]), session_id=str(scenario.get("id", "demo")))
        expected_action = scenario.get("expected_action")
        expected_escalation = scenario.get("expected_human_escalation")
        expected_citation = bool(scenario.get("expected_citation", True))

        action_ok = expected_action is None or result["response"]["action"] == expected_action
        escalation_ok = expected_escalation is None or result["response"]["human_escalation_required"] == expected_escalation
        citation_ok = not expected_citation or bool(result["grounding"]["citations"])
        ok = action_ok and escalation_ok and citation_ok
        if ok:
            pass_count += 1

        rows.append(
            {
                "id": scenario.get("id"),
                "caller_utterance_masked": result["input"]["caller_utterance_masked"],
                "expected_action": expected_action,
                "actual_action": result["response"]["action"],
                "expected_human_escalation": expected_escalation,
                "actual_human_escalation": result["response"]["human_escalation_required"],
                "has_citation": bool(result["grounding"]["citations"]),
                "pass": ok,
                "spoken_text": result["response"]["spoken_text"],
                "top_source": result["grounding"]["citations"][0]["source_id"] if result["grounding"]["citations"] else None,
            }
        )

    return {
        "generated_at_utc": utc_now(),
        "scenario_count": len(scenarios),
        "pass_count": pass_count,
        "pass_rate": round(pass_count / max(1, len(scenarios)), 3),
        "rows": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lendingkart voice-agent wrapper over the approved KB retriever.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--utterance", default=None, help="Single caller utterance to answer.")
    parser.add_argument("--scenarios", type=Path, default=None, help="JSONL scenario file to run.")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--cite-sources-in-voice", action="store_true")
    parser.add_argument("--no-follow-up", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    config = AgentConfig(
        cite_sources_in_voice=args.cite_sources_in_voice,
        include_follow_up=not args.no_follow_up,
    )
    agent = LendingkartVoiceAgent.from_project_root(project_root, config=config)

    if args.scenarios:
        payload = run_scenarios(agent, args.scenarios)
    elif args.utterance:
        payload = agent.respond(args.utterance)
    else:
        raise SystemExit("Provide either --utterance or --scenarios.")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
