from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ACTUAL_RESPONSE_TRANSLATIONS = {
    "Pasensya na po, ayokong manghula. Pwede ko kayong i-connect sa advisor, o magtanong po kayo tungkol sa premium, policy, beneficiary, rider, lapse, o coverage. Gusto niyo po bang i-continue natin?": "Sorry, I do not want to guess. I can connect you to an advisor, or you can ask about premium, policy, beneficiary, rider, lapse, or coverage. Would you like us to continue?",
    "Maaf, saya tidak ingin memberi informasi yang tidak pasti. Saya bisa bantu soal cicilan, tenor, denda, DP, jatuh tempo, angsuran, atau pembiayaan. Apakah Bapak/Ibu ingin saya lanjutkan?": "Sorry, I do not want to give uncertain information. I can help with installments, tenor, penalties, down payment, due date, monthly payments, or financing. Would you like me to continue?",
    "Maaf ya, saya tidak mau asal jawab. Saya bisa bantu soal cicilan, tenor, denda, DP, jatuh tempo, angsuran, atau pembiayaan. Mau saya bantu lanjutkan?": "Sorry, I do not want to answer carelessly. I can help with installments, tenor, penalties, down payment, due date, monthly payments, or financing. Do you want me to continue?",
    "Pasensya na po, ayokong manghula. Pwede ko kayong i-connect sa advisor, o magtanong po kayo tungkol sa premium, policy, benepisyaryo, rider, lapse, o coverage. Gusto niyo po bang magpatuloy?": "Sorry, I do not want to guess. I can connect you to an advisor, or you can ask about premium, policy, beneficiary, rider, lapse, or coverage. Would you like to continue?",
    "Baik Bapak/Ibu. Cicilan atau angsuran perlu dibayarkan sebelum tanggal jatuh tempo agar tidak muncul denda keterlambatan. Apakah Bapak/Ibu ingin saya lanjutkan?": "Okay, Sir/Ma'am. The installment or monthly payment should be paid before the due date so a late-payment penalty does not appear. Would you like me to continue?",
    "Sorry, I do not want to guess. I can connect you to an advisor, or you can ask about premium, policy, beneficiary, rider, lapse, or coverage. Would you like me to continue?": "Sorry, I do not want to guess. I can connect you to an advisor, or you can ask about premium, policy, beneficiary, rider, lapse, or coverage. Would you like me to continue?",
    "Baik, cicilannya perlu dibayar sebelum jatuh tempo ya, supaya tidak kena denda. Mau saya bantu lanjutkan?": "Okay, the installment needs to be paid before the due date so you do not get a penalty. Do you want me to continue helping?",
    "Sige po. Para ma-check ang tamang coverage, ito po ba ay for yourself, family protection, o pagdagdag ng beneficiary or rider? Gusto niyo po bang i-continue natin?": "Okay. To check the right coverage, is this for yourself, family protection, or adding a beneficiary or rider? Would you like us to continue?",
    "Untuk pengajuan pembiayaan, biasanya perlu informasi DP, tenor yang diinginkan, data kendaraan atau barang, dan dokumen identitas. Apakah Bapak/Ibu ingin saya lanjutkan?": "For a financing application, information is usually needed about the down payment, desired tenor, vehicle or item details, and identity documents. Would you like me to continue?",
    "Opo, i-connect ko po kayo sa licensed advisor para maayos na masagot ang policy at coverage questions ninyo.": "Yes, I will connect you to a licensed advisor so your policy and coverage questions can be answered properly.",
    "Kalau lewat jatuh tempo, biasanya bisa kena denda sesuai aturan pembiayaan. Saya bisa bantu arahkan cara bayarnya. Mau saya bantu lanjutkan?": "If payment goes past the due date, there can usually be a penalty according to the financing rules. I can help guide you on how to pay. Do you want me to continue helping?",
    "Opo. Para manatiling active ang policy, kailangan mabayaran ang premium bago ang due date. Matutulungan ko po kayong i-check ang amount at payment option. Gusto niyo po bang magpatuloy?": "Yes. To keep the policy active, the premium needs to be paid before the due date. I can help you check the amount and payment option. Would you like to continue?",
    "Jika pembayaran melewati jatuh tempo, denda dapat berlaku sesuai ketentuan pembiayaan. Saya bisa bantu cek kanal pembayaran agar tidak terlambat. Apakah Bapak/Ibu ingin saya lanjutkan?": "If payment goes past the due date, a penalty may apply according to the financing terms. I can help check the payment channel so it is not late. Would you like me to continue?",
    "Opo, noted po. Para active pa rin ang policy, kailangan mabayaran ang premium bago ang due date. Para hindi ma-lapse ang coverage, tutulungan ko po kayong i-check ang amount at payment option. Gusto niyo po bang i-continue natin?": "Yes, noted. For the policy to remain active, the premium needs to be paid before the due date. To avoid the coverage lapsing, I will help you check the amount and payment option. Would you like us to continue?",
    "Baik, saya akan arahkan ke petugas agar pertanyaan Bapak/Ibu ditangani langsung.": "Okay, I will direct you to an officer so your question can be handled directly.",
    "Sige po. Para malaman ang tamang coverage, ito po ba ay para sa sarili, family protection, o pagdagdag ng benepisyaryo o rider? Gusto niyo po bang magpatuloy?": "Okay. To know the right coverage, is this for yourself, family protection, or adding a beneficiary or rider? Would you like to continue?",
    "Sure. To check the right coverage, is this for yourself, family protection, or adding a beneficiary or rider? Would you like me to continue?": "Sure. To check the right coverage, is this for yourself, family protection, or adding a beneficiary or rider? Would you like me to continue?",
    "Nggih Bapak/Ibu, angsuran perlu dibayar sebelum jatuh tempo supaya mboten kena denda keterlambatan. Nggih, mau saya bantu lanjutkan?": "Yes, Sir/Ma'am, the installment needs to be paid before the due date so you do not get a late-payment penalty. Yes, would you like me to continue helping?",
    "Untuk pengajuan, biasanya dicek DP, tenor, barang atau kendaraan yang mau dibiayai, dan dokumen identitas. Mau saya bantu lanjutkan?": "For an application, the down payment, tenor, item or vehicle to be financed, and identity documents are usually checked. Do you want me to continue helping?",
    "Saya paham. Kalau lagi belum bisa bayar, saya bisa bantu catat kendalanya dan ajukan callback untuk opsi bantuan. Mau saya bantu lanjutkan?": "I understand. If you currently cannot pay, I can record the difficulty and request a callback for support options. Do you want me to continue helping?",
    "Yes. To keep the policy active, the premium should be paid before the due date. I can help confirm the amount and payment option. Would you like me to continue?": "Yes. To keep the policy active, the premium should be paid before the due date. I can help confirm the amount and payment option. Would you like me to continue?",
    "Baik, saya bantu arahkan ke petugas ya supaya bisa ditangani langsung.": "Okay, I will help direct you to an officer so it can be handled directly.",
    "Nggih, kalau lewat jatuh tempo bisa ada denda sesuai ketentuan pembiayaan. Saya bantu arahkan cara bayarnya. Nggih, mau saya bantu lanjutkan?": "Yes, if payment goes past the due date, there can be a penalty according to the financing terms. I will help guide you on how to pay. Yes, would you like me to continue helping?",
    "No problem. I can schedule a callback. What time is convenient? Would you like me to continue?": "No problem. I can schedule a callback. What time is convenient? Would you like me to continue?",
    "Yes, I can connect you with a licensed advisor for policy and coverage questions.": "Yes, I can connect you with a licensed advisor for policy and coverage questions.",
    "Opo, ikokonekta ko kayo sa licensed advisor para maayos na masagot ang policy at coverage questions ninyo.": "Yes, I will connect you to a licensed advisor so your policy and coverage questions can be answered properly.",
    "Gets ko po na importante ang budget. Pwede nating tingnan ang lower premium option o i-adjust ang riders para sakto pa rin ang coverage. Gusto niyo po bang i-continue natin?": "I understand that budget is important. We can look at a lower-premium option or adjust the riders so the coverage still fits. Would you like us to continue?",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def actual_answer_english(row: dict[str, Any]) -> str:
    actual = str(row["actual_response_text"])
    if actual in ACTUAL_RESPONSE_TRANSLATIONS:
        return ACTUAL_RESPONSE_TRANSLATIONS[actual]
    return str(row.get("actual_response_english_summary") or "")


def output_rows(run_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in run_rows:
        rows.append(
            {
                "scenario_id": row["scenario_id"],
                "market": row["market"],
                "category": row["category"],
                "exchange": row["exchange"],
                "quality": row["quality"],
                "overall_score": row["overall_score"],
                "english_customer_question": row["customer_text_english_view"],
                "expected_bot_answer_english": row["expected_response_english_summary"],
                "actual_bot_answer_localized": row["actual_response_text"],
                "actual_bot_answer_english": actual_answer_english(row),
                "original_customer_text": row["customer_text"],
                "expected_localized_reply": row["expected_response_text"],
                "actual_action": row["actual_action"],
                "actual_register": row["actual_response_register"],
            }
        )
    return rows


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Q3 English Questions With Expected And Actual Bot Answers",
        "",
        "This is the simple comparison file.",
        "",
        "Each exchange shows the English customer question, the expected answer in English, the localized answer the bot actually gave, and that actual bot answer in English.",
        "",
    ]
    previous_scenario = None
    for row in rows:
        scenario_id = row["scenario_id"]
        if scenario_id != previous_scenario:
            previous_scenario = scenario_id
            lines.extend(
                [
                    f"## {scenario_id} - {row['market']} - {row['category']}",
                    "",
                ]
            )
        lines.extend(
            [
                f"### Exchange {row['exchange']}",
                "",
                f"ENGLISH CUSTOMER QUESTION: {row['english_customer_question']}",
                "",
                f"EXPECTED BOT ANSWER IN ENGLISH: {row['expected_bot_answer_english']}",
                "",
                f"ACTUAL BOT ANSWER LOCALIZED: {row['actual_bot_answer_localized']}",
                "",
                f"ACTUAL BOT ANSWER IN ENGLISH: {row['actual_bot_answer_english']}",
                "",
                f"QUALITY: {row['quality']} ({row['overall_score']})",
                "",
                f"Original customer text: {row['original_customer_text']}",
                "",
                f"Expected localized reply: {row['expected_localized_reply']}",
                "",
            ]
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "scenario_id",
        "market",
        "category",
        "exchange",
        "quality",
        "overall_score",
        "english_customer_question",
        "expected_bot_answer_english",
        "actual_bot_answer_localized",
        "actual_bot_answer_english",
        "original_customer_text",
        "expected_localized_reply",
        "actual_action",
        "actual_register",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def resolve(project_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else project_root / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Q3 expected-vs-actual answer view.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--run-results",
        type=Path,
        default=Path("demos/q3_conversation_eval/q3_conversation_bot_run_results.jsonl"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("docs/q3_questions_expected_and_actual_bot_answers_english.md"),
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("data/evaluation/q3_questions_expected_and_actual_bot_answers_english.csv"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    run_rows = read_jsonl(resolve(project_root, args.run_results))
    rows = output_rows(run_rows)
    write_markdown(resolve(project_root, args.markdown_output), rows)
    write_csv(resolve(project_root, args.csv_output), rows)
    missing_translations = sorted(
        {
            row["actual_response_text"]
            for row in run_rows
            if row["actual_response_text"] not in ACTUAL_RESPONSE_TRANSLATIONS
        }
    )
    print(
        json.dumps(
            {
                "exchanges": len(rows),
                "unique_actual_responses": len({row["actual_response_text"] for row in run_rows}),
                "missing_actual_response_translations": len(missing_translations),
            },
            indent=2,
        )
    )
    if missing_translations:
        raise SystemExit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
