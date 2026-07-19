from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


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


def humanize(value: str | None) -> str:
    return str(value or "").replace("_", " ").strip()


def load_translations(path: Path) -> dict[tuple[str, int], str]:
    return {
        (str(row["scenario_id"]), int(row["exchange"])): str(row["customer_english"])
        for row in read_jsonl(path)
    }


def expected_answer_english(expected: dict[str, Any]) -> str:
    action = humanize(expected.get("expected_action"))
    why = str(expected.get("why") or "").strip()
    terms = ", ".join(str(term) for term in expected.get("expected_terms", []))
    pieces = [f"The bot should {action}."]
    if why:
        pieces.append(why)
    if terms:
        pieces.append(f"It should cover these terms or ideas: {terms}.")
    return " ".join(pieces)


def iter_exchange_rows(dataset_rows: list[dict[str, Any]], translations: dict[tuple[str, int], str]):
    for scenario in dataset_rows:
        conversation = scenario["conversation"]
        for index in range(0, len(conversation), 2):
            customer = conversation[index]
            expected = conversation[index + 1]
            exchange = int(customer["exchange"])
            scenario_id = str(scenario["id"])
            yield {
                "scenario_id": scenario_id,
                "market": scenario["market"],
                "category": scenario["category"],
                "exchange": exchange,
                "business_situation": scenario["customer_situation"],
                "english_customer_question": translations[(scenario_id, exchange)],
                "expected_bot_answer_english": expected_answer_english(expected),
                "expected_response_type": expected.get("expected_type"),
                "original_customer_text": customer["text"],
                "original_expected_bot_reply": expected["text"],
            }


def write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        "# Q3 English Questions And Expected Answers Only",
        "",
        "This file is intentionally simple. It shows the English customer question first, then the expected bot answer in English.",
        "",
        "Use this file when you only want to read the test questions and ideal answer behavior without the full run report.",
        "",
    ]
    previous_scenario = None
    for row in rows:
        if row["scenario_id"] != previous_scenario:
            previous_scenario = row["scenario_id"]
            lines.extend(
                [
                    f"## {row['scenario_id']} - {row['market']} - {row['category']}",
                    "",
                    f"Business situation: {row['business_situation']}",
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
                f"Original customer text: {row['original_customer_text']}",
                "",
                f"Original expected localized reply: {row['original_expected_bot_reply']}",
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
        "business_situation",
        "english_customer_question",
        "expected_bot_answer_english",
        "expected_response_type",
        "original_customer_text",
        "original_expected_bot_reply",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a simple English-only Q3 question/answer view.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--dataset", type=Path, default=Path("data/evaluation/q3_conversational_response_db.jsonl"))
    parser.add_argument(
        "--translations",
        type=Path,
        default=Path("data/evaluation/q3_customer_question_english_translations.jsonl"),
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        default=Path("docs/q3_english_questions_and_expected_answers_only.md"),
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("data/evaluation/q3_english_questions_and_expected_answers_only.csv"),
    )
    return parser.parse_args()


def resolve(project_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else project_root / path


def main() -> int:
    args = parse_args()
    project_root = args.project_root.resolve()
    dataset = read_jsonl(resolve(project_root, args.dataset))
    translations = load_translations(resolve(project_root, args.translations))
    rows = list(iter_exchange_rows(dataset, translations))
    write_markdown(resolve(project_root, args.markdown_output), rows)
    write_csv(resolve(project_root, args.csv_output), rows)
    print(json.dumps({"scenarios": len(dataset), "exchanges": len(rows)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
