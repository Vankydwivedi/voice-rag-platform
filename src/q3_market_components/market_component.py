from __future__ import annotations

import json
import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from localized_bots.localized_bot import LocalizedBot, LocalizedResponse


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


STOPWORDS = {
    "ako",
    "ang",
    "apa",
    "are",
    "ba",
    "bisa",
    "can",
    "for",
    "how",
    "ibu",
    "may",
    "ng",
    "po",
    "sa",
    "saya",
    "the",
    "to",
    "what",
    "yang",
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def tokens_for(text: str) -> set[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {token for token in tokens if len(token) >= 3 and token not in STOPWORDS}


def has_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def detect_terms_from_action_record(record: dict[str, Any], base_terms: list[str]) -> list[str]:
    terms = {str(term) for term in base_terms}
    terms.update(str(term).lower().replace(" ", "_") for term in record.get("expected_terms", []))
    return sorted(term for term in terms if term)


@dataclass
class ActionMatch:
    record: dict[str, Any]
    score: float
    reasons: list[str]


@dataclass
class Q3MarketResult:
    localized_response: LocalizedResponse
    citations: list[dict[str, Any]]
    retrieval_status: str
    component: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "localized_response": self.localized_response.to_dict(),
            "citations": self.citations,
            "retrieval_status": self.retrieval_status,
            "component": self.component,
        }


class Q3MarketComponent:
    def __init__(
        self,
        *,
        component_dir: Path,
        component_config: dict[str, Any],
        bot: LocalizedBot,
        kb_records: list[dict[str, Any]],
        action_records: list[dict[str, Any]],
    ) -> None:
        self.component_dir = component_dir
        self.component_config = component_config
        self.bot = bot
        self.kb_records = kb_records
        self.action_records = action_records

    @classmethod
    def from_component_dir(cls, component_dir: Path) -> "Q3MarketComponent":
        config_path = component_dir / "component.json"
        component_config = json.loads(config_path.read_text(encoding="utf-8"))
        bot_config_path = (component_dir / str(component_config["config_path"])).resolve()
        kb_path = (component_dir / str(component_config["kb_path"])).resolve()
        action_kb_path = None
        if component_config.get("action_kb_path"):
            action_kb_path = (component_dir / str(component_config["action_kb_path"])).resolve()
        return cls(
            component_dir=component_dir,
            component_config=component_config,
            bot=LocalizedBot.from_config_path(bot_config_path),
            kb_records=read_jsonl(kb_path),
            action_records=read_jsonl(action_kb_path) if action_kb_path and action_kb_path.exists() else [],
        )

    @property
    def response_register_values(self) -> set[str]:
        values = {str(option["value"]) for option in self.component_config.get("response_register_options", [])}
        return values | {"auto"}

    def respond(self, utterance: str, response_register: str | None = None) -> Q3MarketResult:
        requested_register = (response_register or "auto").strip() or "auto"
        if requested_register not in self.response_register_values:
            raise ValueError(
                f"Unsupported response register '{requested_register}' for {self.component_config['component_id']}"
            )
        preferred = None if requested_register == "auto" else requested_register
        localized_response = self.bot.respond(utterance, preferred_response_register=preferred)
        retrieval_status = "q3_market_kb_script_pack"
        selected_action_record: dict[str, Any] | None = None
        action_match: ActionMatch | None = None
        template_response = self.apply_safety_template(localized_response, utterance)
        if template_response:
            localized_response = template_response
            retrieval_status = "q3_safety_template"
        else:
            action_match = self.match_action_record(
                utterance=utterance,
                requested_register=requested_register,
                detected_register=localized_response.response_register,
            )
            if action_match:
                selected_action_record = action_match.record
                localized_response = self.apply_action_record(localized_response, action_match)
                retrieval_status = "q3_action_kb_v2"

        citations = self.retrieve_citations(
            localized_response.intent,
            localized_response.terms_detected,
            selected_action_record=selected_action_record,
            action_match_score=action_match.score if action_match else None,
        )
        return Q3MarketResult(
            localized_response=localized_response,
            citations=citations,
            retrieval_status=retrieval_status,
            component={
                "component_id": self.component_config.get("component_id"),
                "market_id": self.component_config.get("market_id"),
                "kb_record_count": len(self.kb_records),
                "action_kb_record_count": len(self.action_records),
                "requested_response_register": requested_register,
                "selected_action_record_id": selected_action_record.get("record_id") if selected_action_record else None,
            },
        )

    def match_action_record(
        self,
        *,
        utterance: str,
        requested_register: str,
        detected_register: str,
    ) -> ActionMatch | None:
        if not self.action_records:
            return None

        lowered = normalize(utterance)
        utterance_tokens = tokens_for(utterance)
        scored: list[ActionMatch] = []
        for record in self.action_records:
            score = 0.0
            reasons: list[str] = []

            run_register = str(record.get("run_register") or "auto")
            if requested_register != "auto" and run_register == requested_register:
                score += 1.0
                reasons.append("requested_register_match")
            elif requested_register == "auto" and run_register == detected_register:
                score += 0.5
                reasons.append("detected_register_match")

            for phrase in record.get("trigger_phrases", []):
                phrase_text = normalize(str(phrase))
                if not phrase_text:
                    continue
                phrase_tokens = tokens_for(phrase_text)
                if phrase_text in lowered and len(phrase_text) >= 10:
                    score += 12.0
                    reasons.append("exact_trigger_phrase")
                    continue
                if not phrase_tokens:
                    continue
                overlap = len(utterance_tokens & phrase_tokens) / max(1, len(phrase_tokens))
                if overlap >= 0.55 and len(phrase_tokens) >= 2:
                    score += 6.0 * overlap
                    reasons.append("trigger_token_overlap")

            keyword_hits = utterance_tokens & tokens_for(" ".join(str(keyword) for keyword in record.get("keywords", [])))
            if keyword_hits:
                score += min(5.0, len(keyword_hits) * 0.8)
                reasons.append("keyword_hits")

            if score >= 5.5:
                scored.append(ActionMatch(record=record, score=round(score, 3), reasons=reasons))

        if not scored:
            return None
        return sorted(scored, key=lambda item: item.score, reverse=True)[0]

    def apply_action_record(self, base_response: LocalizedResponse, action_match: ActionMatch) -> LocalizedResponse:
        record = action_match.record
        response_text = str(record.get("localized_response") or base_response.response_text)
        metadata = dict(base_response.metadata)
        metadata["action_kb_match"] = {
            "record_id": record.get("record_id"),
            "score": action_match.score,
            "reasons": action_match.reasons,
            "category": record.get("category"),
            "expected_action_detail": record.get("expected_action_detail"),
            "source_refs": record.get("source_refs", []),
        }
        return replace(
            base_response,
            intent=str(record.get("intent") or base_response.intent),
            action=str(record.get("action") or base_response.action),
            response_text=response_text,
            terms_detected=detect_terms_from_action_record(record, base_response.terms_detected),
            fallback_used=False,
            metadata=metadata,
        )

    def apply_safety_template(self, base_response: LocalizedResponse, utterance: str) -> LocalizedResponse | None:
        lowered = normalize(utterance)
        market_id = str(self.component_config.get("market_id") or "")
        register = base_response.response_register

        if market_id.startswith("philippines"):
            template = self.philippines_safety_template(lowered, register)
        else:
            template = self.indonesia_safety_template(lowered, register)
        if not template:
            return None

        action, intent, response_text, terms = template
        metadata = dict(base_response.metadata)
        metadata["q3_template_match"] = {
            "intent": intent,
            "market_id": market_id,
            "register": register,
            "reason": "high_precision_paraphrase_or_safety_boundary",
        }
        return replace(
            base_response,
            intent=intent,
            action=action,
            response_text=response_text,
            terms_detected=sorted(set(base_response.terms_detected) | set(terms)),
            fallback_used=False,
            metadata=metadata,
        )

    def philippines_safety_template(
        self,
        lowered: str,
        register: str,
    ) -> tuple[str, str, str, list[str]] | None:
        filipino = register == "filipino"
        english = register == "english"

        wants_handoff = has_any(lowered, ["connect", "talk", "speak", "kausap", "kumausap", "route", "transfer"])
        handoff_target = has_any(lowered, ["advisor", "human", "tao", "representative", "supervisor"])
        if wants_handoff and handoff_target:
            if english:
                text = "Yes, I can connect you with a licensed advisor for policy, premium, and coverage questions."
            elif filipino:
                text = "Opo, ikokonekta ko po kayo sa licensed advisor para maayos na masagot ang policy, premium, at coverage questions ninyo."
            else:
                text = "Opo, i-connect ko po kayo sa licensed advisor para maayos na masagot ang policy, premium, and coverage questions ninyo."
            return ("escalate_to_human", "q3_template_ph_human_escalation", text, ["policy", "coverage"])

        if has_any(lowered, ["may sakit", "health condition", "sick", "medical"]) and has_any(
            lowered,
            ["hindi", "not", "hide", "sabihin", "disclose", "application", "approve"],
        ):
            if english:
                text = "I cannot help hide health information. Health answers must be accurate, and a licensed advisor should guide the proper application process."
            elif filipino:
                text = "Hindi po ako makakatulong sa pagtatago ng health information. Kailangan pong tama ang health answers, at mas ligtas na kausapin ang licensed advisor."
            else:
                text = "Hindi po ako makakatulong magtago ng health information. Health answers must be accurate, and best po na licensed advisor ang mag-guide sa tamang process."
            return ("localized_fallback", "q3_template_ph_health_disclosure_boundary", text, ["policy", "coverage"])

        if "beneficiary" in lowered and has_any(
            lowered,
            ["without telling", "without the policy owner", "hindi sabihin", "di sabihin", "policy owner"],
        ):
            if english:
                text = "I cannot advise changing a beneficiary without proper authorization. Beneficiary changes must follow policy owner and insurer servicing rules."
            elif filipino:
                text = "Hindi po ako makakapag-advise ng beneficiary change kung walang tamang authorization. Dapat sundin ang policy owner at insurer servicing rules."
            else:
                text = "Hindi po ako makakapag-advise ng beneficiary change without proper authorization. Kailangan sundin ang policy owner and insurer servicing rules."
            return ("localized_fallback", "q3_template_ph_beneficiary_authorization_boundary", text, ["beneficiary", "policy"])

        premium_hardship = has_any(
            lowered,
            [
                "makakabayad",
                "can't pay",
                "cannot pay",
                "kulang",
                "short ako",
                "hindi mababayaran",
                "hindi ko mababayaran",
                "lapse",
                "ma-lapse",
                "maputol",
            ],
        )
        if premium_hardship and has_any(lowered, ["premium", "policy", "coverage", "hulog", "payment"]):
            if english:
                text = "I understand. I should not guess the grace-period rule. Let me route you to servicing or a licensed advisor to confirm payment options and lapse risk."
            elif filipino:
                text = "Naiintindihan ko po. Hindi po ako dapat manghula sa grace-period rule. Ipapakausap ko po kayo sa servicing o licensed advisor para ma-confirm ang payment options at lapse risk."
            else:
                text = "Naiintindihan ko po. Ayokong manghula sa grace-period rule. I can route you to servicing or a licensed advisor para ma-confirm ang payment options and lapse risk."
            return ("handle_renewal_or_premium", "q3_template_ph_premium_hardship", text, ["premium", "policy", "lapse", "coverage"])

        return None

    def indonesia_safety_template(
        self,
        lowered: str,
        register: str,
    ) -> tuple[str, str, str, list[str]] | None:
        colloquial = register == "colloquial_id"
        regional = register == "regional_javanese_id"

        if has_any(lowered, ["cs manusia", "bicara sama petugas", "ngomong sama petugas", "petugas collection", "petugas aja", "petugas mawon"]):
            if regional:
                text = "Nggih, saya bantu arahkan ke petugas supaya bisa ditangani langsung."
            elif colloquial:
                text = "Baik, saya bantu arahkan ke petugas ya supaya bisa ditangani langsung."
            else:
                text = "Baik, saya akan arahkan ke petugas agar pertanyaan Bapak/Ibu ditangani langsung."
            return ("escalate_to_human", "q3_template_id_human_escalation", text, ["pembiayaan"])

        if has_any(lowered, ["hapus denda", "denda dihapus", "waive denda"]) and has_any(
            lowered,
            ["tanpa proses resmi", "di luar proses", "langsung saja", "bypass"],
        ):
            if regional:
                text = "Nggih, saya tidak bisa membantu penghapusan denda di luar proses resmi. Saya bisa arahkan ke petugas untuk pengecekan sesuai ketentuan."
            elif colloquial:
                text = "Maaf ya, saya tidak bisa bantu hapus denda di luar proses resmi. Saya bisa bantu arahkan ke petugas untuk dicek sesuai ketentuan."
            else:
                text = "Maaf, saya tidak bisa membantu penghapusan denda di luar proses resmi. Saya bisa arahkan ke petugas untuk pengecekan sesuai ketentuan."
            return ("localized_fallback", "q3_template_id_official_process_boundary", text, ["denda", "pembiayaan"])

        if has_any(lowered, ["otp", "password", "pin"]) and has_any(lowered, ["hapus denda", "denda", "telepon", "ngaku"]):
            if regional:
                text = "Nggih, jangan berikan OTP, PIN, password, atau kode apa pun. Saya bisa arahkan ke kanal resmi atau tim keamanan untuk pelaporan."
            elif colloquial:
                text = "Jangan kasih OTP, PIN, password, atau kode apa pun ya. Saya bisa bantu arahkan ke kanal resmi atau tim keamanan untuk laporan."
            else:
                text = "Jangan berikan OTP, PIN, password, atau kode apa pun. Saya bisa arahkan ke kanal resmi atau tim keamanan untuk pelaporan."
            return ("escalate_to_human", "q3_template_id_fraud_security_escalation", text, ["denda", "pembiayaan"])

        if has_any(lowered, ["denda", "late fee", "dendanya"]) and has_any(lowered, ["berapa", "nominal"]):
            if regional:
                text = "Nggih, kalau lewat jatuh tempo bisa ada denda sesuai ketentuan pembiayaan. Saya tidak bisa memastikan nominal tanpa data kontrak."
            elif colloquial:
                text = "Kalau sudah lewat jatuh tempo, bisa kena denda sesuai aturan pembiayaan. Nominal pastinya harus dicek di kontrak atau kanal resmi."
            else:
                text = "Jika pembayaran melewati jatuh tempo, denda dapat berlaku sesuai ketentuan pembiayaan. Nominal pastinya perlu dicek melalui kontrak atau kanal resmi."
            return ("explain_penalty_or_due_date", "q3_template_id_penalty_question", text, ["denda", "jatuh_tempo", "pembiayaan"])

        if has_any(lowered, ["bayar sebagian", "bayar full", "belum bisa bayar full", "bayar setengah"]):
            if regional:
                text = "Nggih, pembayaran sebagian bisa membantu mengurangi outstanding, tetapi belum tentu menghentikan status terlambat atau denda. Opsi resmi perlu dicek oleh tim terkait."
            elif colloquial:
                text = "Bayar sebagian bisa membantu mengurangi outstanding, tapi belum tentu menghentikan status telat atau denda. Sebaiknya cek opsi resmi seperti restrukturisasi atau arahan CS."
            else:
                text = "Pembayaran sebagian bisa membantu mengurangi outstanding, tetapi belum tentu menghentikan status keterlambatan atau denda. Sebaiknya cek opsi resmi seperti restrukturisasi atau instruksi layanan pelanggan."
            return ("offer_payment_support", "q3_template_id_partial_payment_boundary", text, ["cicilan", "denda", "pembiayaan"])

        payment_difficulty = has_any(
            lowered,
            [
                "gak bisa bayar",
                "nggak bisa bayar",
                "belum bisa bayar",
                "mboten bisa bayar",
                "mboten saged bayar",
                "sulit bayar",
                "keringanan",
                "reschedule pembayaran",
            ],
        )
        if payment_difficulty:
            if regional:
                text = "Nggih, saya paham. Saya bantu catat kendala pembayaran panjenengan dan arahkan ke tim terkait untuk opsi bantuan resmi."
            elif colloquial:
                text = "Saya paham. Kalau lagi belum bisa bayar, saya bisa bantu catat kendalanya dan ajukan callback resmi untuk opsi bantuan."
            else:
                text = "Saya mengerti. Saya bisa catat kendala pembayaran dan bantu arahkan ke opsi bantuan atau jadwal callback dari tim terkait."
            return ("offer_payment_support", "q3_template_id_payment_difficulty", text, ["cicilan", "angsuran", "pembiayaan"])

        if "pengajuan" in lowered and has_any(lowered, ["tidak pernah", "atas nama saya", "mau lapor", "tidak sah", "tanpa izin"]):
            if regional:
                text = "Nggih, ini perlu ditangani sebagai dugaan pengajuan tidak sah. Saya bisa eskalasikan ke tim keamanan atau pengaduan. Jangan bagikan OTP, PIN, password, atau foto identitas di chat ini."
            elif colloquial:
                text = "Baik, ini perlu dianggap dugaan pengajuan tidak sah. Saya bisa eskalasikan ke tim keamanan atau pengaduan. Jangan bagikan OTP, PIN, password, atau foto identitas di chat ini."
            else:
                text = "Baik, ini perlu ditangani serius sebagai dugaan pengajuan tidak sah. Saya bisa eskalasikan ke tim keamanan atau pengaduan. Jangan bagikan OTP, PIN, password, atau foto identitas di chat ini."
            return ("escalate_to_human", "q3_template_id_unauthorized_application", text, ["pembiayaan"])

        fraud_indicators = ["tidak sah", "tidak pernah", "atas nama saya", "bukan saya", "tanpa izin", "dicuri", "fraud", "penipuan", "otp", "pin", "password"]
        qualification_markers = ["dp", "tenor", "motor", "mobil", "pembiayaan", "pengajuan", "ajukan", "apply", "dokumen"]
        if has_any(lowered, qualification_markers) and not has_any(lowered, fraud_indicators) and not has_any(lowered, ["dokumen kurang", "pasti ditolak"]):
            if regional:
                text = "Nggih, untuk pengajuan pembiayaan biasanya dicek DP, tenor, barang atau kendaraan yang dibiayai, dokumen identitas, dan kemampuan bayar."
            elif colloquial:
                text = "Untuk pengajuan, biasanya dicek DP, tenor, barang atau kendaraan yang mau dibiayai, dokumen identitas, dan kemampuan bayar."
            else:
                text = "Untuk pengajuan pembiayaan, biasanya perlu informasi DP, tenor, data barang atau kendaraan, dokumen identitas, dan kemampuan membayar."
            return ("handle_finance_qualification", "q3_template_id_finance_qualification", text, ["dp", "tenor", "pembiayaan"])

        return None

    def retrieve_citations(
        self,
        intent: str,
        terms: list[str],
        *,
        selected_action_record: dict[str, Any] | None = None,
        action_match_score: float | None = None,
    ) -> list[dict[str, Any]]:
        citations: list[dict[str, Any]] = []
        if selected_action_record:
            citations.append(
                {
                    "record_id": selected_action_record.get("record_id"),
                    "label": f"Q3 action KB: {selected_action_record.get('category')}",
                    "url": "",
                    "source_id": selected_action_record.get("source_id"),
                    "source_refs": selected_action_record.get("source_refs", []),
                    "evidence": selected_action_record.get("response_goal")
                    or selected_action_record.get("customer_situation"),
                    "market_id": selected_action_record.get("market_id"),
                    "score": action_match_score,
                }
            )

        term_set = {term.lower() for term in terms}
        scored: list[tuple[int, dict[str, Any]]] = []
        for record in self.kb_records:
            score = 0
            if intent in record.get("intents", []):
                score += 4
            score += len(term_set & {str(term).lower() for term in record.get("terms", [])})
            if score > 0:
                scored.append((score, record))

        if not scored:
            scored = [(1, record) for record in self.kb_records if "fallback" in record.get("intents", [])]

        for score, record in sorted(scored, key=lambda item: item[0], reverse=True)[:3]:
            citations.append(
                {
                    "record_id": record.get("record_id"),
                    "label": record.get("label"),
                    "url": record.get("url"),
                    "source_id": record.get("source_id"),
                    "evidence": record.get("evidence"),
                    "market_id": record.get("market_id"),
                    "score": score,
                }
            )
        return citations
