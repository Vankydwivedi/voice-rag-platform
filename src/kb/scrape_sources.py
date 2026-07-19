from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Tag


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/126.0 Safari/537.36 "
    "AIEngineerAssessmentBot/0.1"
)

EXPECTED_CATEGORY_KEYWORDS = {
    "product_overview": ["business loan", "loan", "tenure", "eligibility"],
    "eligibility": ["eligibility", "age", "turnover", "income", "business"],
    "documents": ["document", "identity", "address", "bank statement", "itr"],
    "fees": ["charge", "fee", "interest", "processing", "repayment"],
    "use_cases": ["business", "expansion", "loan", "faq"],
    "product_variant": ["business loan", "eligibility", "documents", "faq"],
    "msme_overview": ["msme", "loan", "working capital", "faq"],
    "working_capital": ["working capital", "turnover", "eligible", "documents"],
    "forms": ["form", "application", "download"],
    "privacy_pii": ["privacy", "data", "personal", "processing"],
    "human_escalation": ["grievance", "complaint", "nodal", "ombudsman"],
    "support": ["customer care", "loan services", "complaint", "contact"],
    "compliance": ["fair practice", "lending", "borrower", "grievance"],
}

REMOVE_SELECTORS = [
    "script",
    "style",
    "noscript",
    "svg",
    "canvas",
    "picture",
    "source",
    "iframe",
    "header",
    "footer",
    "nav",
    "aside",
    "form",
    "[role='navigation']",
    "[aria-label='breadcrumb']",
    "[aria-label='breadcrumbs']",
]

NOISE_RE = re.compile(
    r"(cookie|breadcrumb|footer|header|nav|navbar|menu|mega-menu|social|"
    r"login|locator|apply-now|sticky|modal|popup|carousel|language|translate|"
    r"copyright|dicgc|qr code|select|input|button)",
    re.IGNORECASE,
)

SPACE_RE = re.compile(r"[ \t\r\f\v]+")


@dataclass
class ScrapeResult:
    source_id: str
    url: str
    status: str
    status_code: int | None
    method: str
    raw_path: str | None
    cleaned_path: str | None
    tables: list[str]
    raw_bytes: int
    cleaned_chars: int
    title: str
    headings_count: int
    warnings: list[str]
    error: str | None = None


def slug_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:12]


def ensure_dirs(project_root: Path) -> dict[str, Path]:
    dirs = {
        "raw": project_root / "data" / "raw",
        "cleaned": project_root / "data" / "cleaned",
        "tables": project_root / "data" / "raw" / "tables",
        "kb": project_root / "data" / "kb",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def load_sources(project_root: Path) -> list[dict[str, Any]]:
    source_path = project_root / "data" / "sources.json"
    if not source_path.exists():
        raise FileNotFoundError(f"Missing source list: {source_path}")
    sources = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(sources, list):
        raise ValueError("sources.json must contain a list of source objects")
    return sources


def fetch_url(url: str, timeout: int) -> requests.Response:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-IN,en;q=0.9"})
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response


def remove_noise(soup: BeautifulSoup) -> None:
    for selector in REMOVE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()


def normalize_line(line: str) -> str:
    line = SPACE_RE.sub(" ", line).strip()
    line = line.replace("\u00a0", " ")
    return SPACE_RE.sub(" ", line).strip()


def node_text(node: Tag) -> str:
    return normalize_line(node.get_text(" ", strip=True))


def extract_table(table: Tag) -> list[list[str]]:
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        cells = [normalize_line(cell.get_text(" ", strip=True)) for cell in tr.find_all(["th", "td"])]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append(cells)
    return rows


def save_tables(source_id: str, soup: BeautifulSoup, tables_dir: Path) -> list[str]:
    table_paths: list[str] = []
    for idx, table in enumerate(soup.find_all("table"), start=1):
        rows = extract_table(table)
        if len(rows) < 2:
            continue
        path = tables_dir / f"{source_id}_table_{idx:02d}.csv"
        width = max(len(row) for row in rows)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            for row in rows:
                writer.writerow(row + [""] * (width - len(row)))
        table_paths.append(str(path))
    return table_paths


def extract_clean_text(source: dict[str, Any], html: str, tables_dir: Path) -> tuple[str, str, int, list[str], list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    title = normalize_line(soup.title.get_text(" ", strip=True)) if soup.title else ""
    remove_noise(soup)
    table_paths = save_tables(source["source_id"], soup, tables_dir)

    root = soup.find("main") or soup.find("article") or soup.body or soup
    blocks: list[str] = []
    seen: set[str] = set()
    heading_count = 0

    for node in root.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "th", "td"], recursive=True):
        text = node_text(node)
        if not text:
            continue
        if len(text) < 3:
            continue
        if text.lower() in {"apply", "apply now", "know more", "read more", "view more", "locate us"}:
            continue
        if node.name and node.name.startswith("h"):
            heading_count += 1
            text = f"\n## {text}"
        fingerprint = re.sub(r"\W+", "", text.lower())
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        blocks.append(text)

    text = "\n".join(blocks)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    warnings = quality_warnings(source, title, text, heading_count, len(table_paths))
    return title, text, heading_count, table_paths, warnings


def quality_warnings(source: dict[str, Any], title: str, text: str, heading_count: int, table_count: int) -> list[str]:
    warnings: list[str] = []
    lowered = text.lower()
    if len(text) < 1200:
        warnings.append("thin_extraction_static_html_may_need_playwright")
    if heading_count < 2:
        warnings.append("few_headings_found")
    if source.get("category") in {"fees", "forms"} and table_count == 0:
        warnings.append("expected_tables_or_links_not_found")
    expected = EXPECTED_CATEGORY_KEYWORDS.get(source.get("category", ""), [])
    missing = [keyword for keyword in expected if keyword not in lowered]
    if len(missing) >= max(2, len(expected) // 2):
        warnings.append("category_keywords_missing:" + ",".join(missing[:5]))
    if title and "404" in title.lower():
        warnings.append("title_indicates_404")
    if "access denied" in lowered or "forbidden" in lowered:
        warnings.append("page_may_block_scraping")
    return warnings


def write_cleaned_file(path: Path, source: dict[str, Any], title: str, text: str, tables: list[str]) -> None:
    generated_at = datetime.now(timezone.utc).isoformat()
    header = [
        f"source_id: {source['source_id']}",
        f"url: {source['url']}",
        f"title: {title}",
        f"category: {source.get('category', '')}",
        f"priority: {source.get('priority', '')}",
        f"extracted_at_utc: {generated_at}",
        f"tables_extracted: {len(tables)}",
        "",
        "--- CLEANED TEXT ---",
        "",
    ]
    path.write_text("\n".join(header) + text + "\n", encoding="utf-8")


def scrape_source(source: dict[str, Any], dirs: dict[str, Path], timeout: int) -> ScrapeResult:
    source_id = source["source_id"]
    url = source["url"]
    raw_path = dirs["raw"] / f"{source_id}.html"
    cleaned_path = dirs["cleaned"] / f"{source_id}.txt"

    try:
        response = fetch_url(url, timeout=timeout)
        html = response.text
        raw_path.write_text(html, encoding=response.encoding or "utf-8", errors="ignore")
        title, clean_text, heading_count, table_paths, warnings = extract_clean_text(source, html, dirs["tables"])
        write_cleaned_file(cleaned_path, source, title, clean_text, table_paths)

        status = "success"
        if warnings:
            status = "partial"
        return ScrapeResult(
            source_id=source_id,
            url=url,
            status=status,
            status_code=response.status_code,
            method="requests+beautifulsoup",
            raw_path=str(raw_path),
            cleaned_path=str(cleaned_path),
            tables=table_paths,
            raw_bytes=len(response.content),
            cleaned_chars=len(clean_text),
            title=title,
            headings_count=heading_count,
            warnings=warnings,
        )
    except Exception as exc:  # noqa: BLE001 - report extraction failure in assessment artifact
        return ScrapeResult(
            source_id=source_id,
            url=url,
            status="failed",
            status_code=None,
            method="requests+beautifulsoup",
            raw_path=None,
            cleaned_path=None,
            tables=[],
            raw_bytes=0,
            cleaned_chars=0,
            title="",
            headings_count=0,
            warnings=["extraction_failed"],
            error=repr(exc),
        )


def write_reports(project_root: Path, sources: list[dict[str, Any]], results: list[ScrapeResult]) -> None:
    kb_dir = project_root / "data" / "kb"
    report_path = kb_dir / "extraction_report.json"
    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_count": len(sources),
        "success_count": sum(1 for item in results if item.status == "success"),
        "partial_count": sum(1 for item in results if item.status == "partial"),
        "failed_count": sum(1 for item in results if item.status == "failed"),
        "results": [item.__dict__ for item in results],
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest_path = kb_dir / "source_manifest.json"
    manifest_records = []
    result_by_id = {item.source_id: item for item in results}
    for source in sources:
        result = result_by_id.get(source["source_id"])
        manifest_records.append(
            {
                **source,
                "domain": urlparse(source["url"]).netloc,
                "raw_file": result.raw_path if result else None,
                "cleaned_file": result.cleaned_path if result else None,
                "extraction_status": result.status if result else "not_run",
                "content_hash": slug_hash(Path(result.cleaned_path).read_text(encoding="utf-8"))
                if result and result.cleaned_path
                else None,
            }
        )
    manifest_path.write_text(json.dumps(manifest_records, indent=2, ensure_ascii=False), encoding="utf-8")

    quality_lines = [
        "# Source Quality Report",
        "",
        f"Generated at UTC: {report['generated_at_utc']}",
        "",
        "| Source | Status | Clean chars | Tables | Warnings |",
        "|---|---:|---:|---:|---|",
    ]
    for item in results:
        warnings = ", ".join(item.warnings) if item.warnings else "-"
        quality_lines.append(
            f"| {item.source_id} | {item.status} | {item.cleaned_chars} | {len(item.tables)} | {warnings} |"
        )
    quality_lines.extend(
        [
            "",
            "## Notes",
            "",
            "- `success` means static HTML extraction produced enough category-relevant text.",
            "- `partial` means the page was saved but should be reviewed; it may need Playwright rendered extraction.",
            "- `failed` means the source could not be fetched or parsed and should be retried or replaced.",
        ]
    )
    (kb_dir / "source_quality_report.md").write_text("\n".join(quality_lines) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scrape approved HDFC sources for the business-loan KB.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd(), help="Project root containing data/sources.json")
    parser.add_argument("--timeout", type=int, default=25, help="Per-request timeout in seconds")
    parser.add_argument("--delay", type=float, default=0.8, help="Delay between requests in seconds")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    project_root = args.project_root.resolve()
    dirs = ensure_dirs(project_root)
    sources = load_sources(project_root)
    results: list[ScrapeResult] = []

    for index, source in enumerate(sources, start=1):
        print(f"[{index}/{len(sources)}] scraping {source['source_id']} -> {source['url']}")
        result = scrape_source(source, dirs, timeout=args.timeout)
        results.append(result)
        print(f"  {result.status}: chars={result.cleaned_chars} warnings={len(result.warnings)}")
        time.sleep(args.delay)

    write_reports(project_root, sources, results)
    print("Done.")
    print(f"Extraction report: {project_root / 'data' / 'kb' / 'extraction_report.json'}")
    print(f"Quality report: {project_root / 'data' / 'kb' / 'source_quality_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
