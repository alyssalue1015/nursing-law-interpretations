#!/usr/bin/env python3
import csv
import json
import re
import sqlite3
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = ROOT / "source" / "護理人員法解釋彙編108年5月.pdf"
DATA_DIR = ROOT / "data"
WEB_DATA_DIR = ROOT / "web" / "data"
DRIVE_URL = "https://drive.google.com/file/d/1IEo7JO0CoxnfXCeiRm87BLzYfexqwZH7/view?usp=drivesdk"


DOC_RE = re.compile(
    r"(?P<date>\d{2,3}\s*[.．/年]\s*\d{1,2}\s*(?:[.．/月]\s*\d{1,2}\s*日?)?)"
    r"\s*(?P<docno>[\u4e00-\u9fffA-Za-z（）()○0-9第字_\-\.．\s]{0,35}?字第\s*[A-Za-z0-9]{5,}\s*號)"
    r"\s*(?:函|令|書函)?"
)
ARTICLE_RE = re.compile(r"第\s*(\d+(?:-\d+)?)\s*條")
PRINTED_PAGE_RE = re.compile(r"^\s*(\d{1,3})\s*$")
MAIN_INTERPRETATION_RE = re.compile(r"(護理人員法|護理機構分類設置標準)解釋[彙彚]編")


def normalize_text(text: str) -> str:
    text = text.replace("\u3000", " ")
    text = text.replace("．", ".")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_docno(text: str) -> str:
    text = compact(text)
    text = re.sub(r"^[.。．、，,\s]+", "", text)
    text = re.sub(r"\s+", "", text)
    text = text.replace("（", "(").replace("）", ")")
    return text


def roc_date_to_sortable(raw: str) -> str:
    nums = re.findall(r"\d+", raw)
    if len(nums) < 2:
        return raw.strip()
    year = int(nums[0]) + 1911
    month = int(nums[1])
    day = int(nums[2]) if len(nums) >= 3 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def extract_printed_page(text: str, physical_page: int) -> int | None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    candidates = []
    for line in lines[:8] + lines[-8:]:
        match = PRINTED_PAGE_RE.match(line)
        if match:
            candidates.append(int(match.group(1)))
    if candidates:
        return candidates[-1]
    if physical_page >= 50:
        return physical_page - 13
    return None


def page_header(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines[:2])


def infer_law_name(header: str, current: str) -> str:
    if "護理機構分類設置標準解釋" in header:
        return "護理機構分類設置標準解釋彙編"
    if "護理人員法解釋" in header:
        return "護理人員法解釋彙編"
    return current


def infer_article(header: str, body: str, current: str) -> str:
    for source in (header, body[:160]):
        match = ARTICLE_RE.search(source)
        if match:
            return f"第 {match.group(1)} 條"
    return current


def infer_category(text: str, current: str) -> str:
    match = re.search(r"〔釋例類別〕\s*(第\s*\d+\s*類)?\s*([^\n]+)", text)
    if match:
        label = compact(match.group(0))
        label = re.sub(r"\s*\d{1,3}$", "", label)
        return label
    return current


def make_title(body: str) -> str:
    match = re.search(r"主旨[:：]\s*(.+?)(?:\n|說明[:：])", body, re.S)
    if match:
        title = compact(match.group(1))
    else:
        lines = [compact(line) for line in body.splitlines() if compact(line)]
        title = lines[0] if lines else ""
    return title[:180]


def make_keywords(entry: dict) -> list[str]:
    text = " ".join(
        [
            entry.get("law_name", ""),
            entry.get("article", ""),
            entry.get("category", ""),
            entry.get("title", ""),
            entry.get("body", "")[:900],
        ]
    )
    keywords = []
    for pattern in [
        r"護理人員",
        r"護理師",
        r"護士",
        r"專科護理師",
        r"護理機構",
        r"居家護理",
        r"產後護理",
        r"護理之家",
        r"照顧服務員",
        r"醫療輔助",
        r"執業登記",
        r"執業執照",
        r"負責人",
        r"開業",
        r"收費",
        r"評鑑",
        r"督導考核",
        r"繼續教育",
        r"停業",
        r"歇業",
        r"廣告",
        r"病歷",
        r"管路",
        r"傷口",
        r"給藥",
        r"採血",
        r"口腔",
        r"麻醉",
        r"公共衛生",
    ]:
        if re.search(pattern, text) and pattern not in keywords:
            keywords.append(pattern)
    return keywords


def read_pages() -> list[dict]:
    reader = PdfReader(str(PDF_PATH))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = normalize_text(page.extract_text() or "")
        pages.append(
            {
                "physical_page": index,
                "printed_page": extract_printed_page(text, index),
                "header": page_header(text),
                "text": text,
            }
        )
    return pages


def build_interpretations(pages: list[dict]) -> list[dict]:
    entries = []
    current = None
    law_name = ""
    article = ""
    category = ""

    for page in pages:
        if page["printed_page"] is None or page["printed_page"] < 37 or page["printed_page"] > 460:
            continue

        text = page["text"]
        header = page["header"]
        if MAIN_INTERPRETATION_RE.search(header):
            law_name = infer_law_name(header, law_name)
            article = infer_article(header, text, article)

        category = infer_category(text, category)
        page_article = infer_article(header, text, article)
        if page_article:
            article = page_article

        matches = list(DOC_RE.finditer(text))
        if not matches:
            if current:
                current["body_parts"].append({"page": page, "text": text})
                current["end_printed_page"] = page["printed_page"]
                current["end_physical_page"] = page["physical_page"]
            continue

        first_prefix = text[: matches[0].start()].strip()
        if first_prefix and current:
            current["body_parts"].append({"page": page, "text": first_prefix})
            current["end_printed_page"] = page["printed_page"]
            current["end_physical_page"] = page["physical_page"]

        for idx, match in enumerate(matches):
            if current:
                body = text[current["_start_pos_on_page"] : match.start()].strip() if current.get("_same_page") else ""
                if body:
                    current["body_parts"].append({"page": page, "text": body})
                entries.append(finalize_entry(current))

            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            body = text[match.start() : end].strip()
            current = {
                "source_title": "護理人員法解釋彙編108年5月.pdf",
                "drive_url": DRIVE_URL,
                "law_name": law_name or "護理人員法解釋彙編",
                "article": article,
                "category": category,
                "issued_date_raw": compact(match.group("date")),
                "issued_date": roc_date_to_sortable(match.group("date")),
                "document_no": clean_docno(match.group("docno")),
                "start_printed_page": page["printed_page"],
                "end_printed_page": page["printed_page"],
                "start_physical_page": page["physical_page"],
                "end_physical_page": page["physical_page"],
                "body_parts": [{"page": page, "text": body}],
                "_same_page": False,
                "_start_pos_on_page": end,
            }

        if current:
            current["end_printed_page"] = page["printed_page"]
            current["end_physical_page"] = page["physical_page"]

    if current:
        entries.append(finalize_entry(current))

    return entries


def finalize_entry(entry: dict) -> dict:
    body = "\n".join(part["text"] for part in entry["body_parts"] if part["text"].strip())
    body = normalize_text(body)
    result = {k: v for k, v in entry.items() if not k.startswith("_") and k != "body_parts"}
    result["title"] = make_title(body)
    result["body"] = body
    result["snippet"] = compact(body)[:320]
    return result


def write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_js(path: Path, variable_name: str, payload) -> None:
    data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    path.write_text(f"window.{variable_name} = {data};\n", encoding="utf-8")


def write_csv(path: Path, entries: list[dict]) -> None:
    fields = [
        "id",
        "law_name",
        "article",
        "category",
        "issued_date_raw",
        "issued_date",
        "document_no",
        "title",
        "start_printed_page",
        "end_printed_page",
        "start_physical_page",
        "end_physical_page",
        "keywords",
        "body",
        "drive_url",
        "source_url",
        "list_url",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for entry in entries:
            row = {field: entry.get(field, "") for field in fields}
            row["keywords"] = "、".join(entry.get("keywords", []))
            writer.writerow(row)


def write_sqlite(path: Path, entries: list[dict], pages: list[dict]) -> None:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.execute(
        """
        CREATE TABLE interpretations (
          id TEXT PRIMARY KEY,
          law_name TEXT,
          article TEXT,
          category TEXT,
          issued_date_raw TEXT,
          issued_date TEXT,
          document_no TEXT,
          title TEXT,
          start_printed_page INTEGER,
          end_printed_page INTEGER,
          start_physical_page INTEGER,
          end_physical_page INTEGER,
          keywords TEXT,
          body TEXT,
          snippet TEXT,
          drive_url TEXT,
          source_url TEXT,
          list_url TEXT,
          source_title TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE VIRTUAL TABLE interpretations_fts USING fts5(
          id UNINDEXED,
          law_name,
          article,
          category,
          document_no,
          title,
          keywords,
          body,
          tokenize='unicode61'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE pages (
          physical_page INTEGER PRIMARY KEY,
          printed_page INTEGER,
          header TEXT,
          text TEXT
        )
        """
    )
    for page in pages:
        conn.execute(
            "INSERT INTO pages VALUES (?, ?, ?, ?)",
            (page["physical_page"], page["printed_page"], page["header"], page["text"]),
        )
    for entry in entries:
        values = (
            entry["id"],
            entry["law_name"],
            entry["article"],
            entry["category"],
            entry["issued_date_raw"],
            entry["issued_date"],
            entry["document_no"],
            entry["title"],
            entry["start_printed_page"],
            entry["end_printed_page"],
            entry["start_physical_page"],
            entry["end_physical_page"],
            "、".join(entry["keywords"]),
            entry["body"],
            entry["snippet"],
            entry.get("drive_url", ""),
            entry.get("source_url", ""),
            entry.get("list_url", ""),
            entry.get("source_title", ""),
        )
        conn.execute(
            "INSERT INTO interpretations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        conn.execute(
            "INSERT INTO interpretations_fts VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                entry["id"],
                entry["law_name"],
                entry["article"],
                entry["category"],
                entry["document_no"],
                entry["title"],
                "、".join(entry["keywords"]),
                entry["body"],
            ),
        )
    conn.commit()
    conn.close()


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    pages = read_pages()
    entries = build_interpretations(pages)
    web_source_path = DATA_DIR / "mohw_web_sources.json"
    web_entries = []
    if web_source_path.exists():
        web_payload = json.loads(web_source_path.read_text(encoding="utf-8"))
        web_entries = web_payload.get("entries", [])
        entries.extend(web_entries)

    for index, entry in enumerate(entries, start=1):
        entry["id"] = f"interp-{index:04d}"
        entry["keywords"] = make_keywords(entry)

    metadata = {
        "source_title": "護理人員法解釋彙編108年5月.pdf",
        "drive_url": DRIVE_URL,
        "drive_file_id": "1IEo7JO0CoxnfXCeiRm87BLzYfexqwZH7",
        "pdf_pages": len(pages),
        "interpretation_entries": len(entries),
        "pdf_interpretation_entries": len(entries) - len(web_entries),
        "mohw_web_entries": len(web_entries),
        "notes": [
            "printed_page is the page number printed in the compilation.",
            "physical_page is the page number in the PDF file.",
            "Entries are split by ROC date plus official document number patterns.",
            "MOHW web entries come from https://nurse.mohw.gov.tw/lp-125-2.html and https://nurse.mohw.gov.tw/lp-126-2.html.",
        ],
    }

    write_json(DATA_DIR / "pages.json", pages)
    write_json(DATA_DIR / "interpretations.json", entries)
    write_json(DATA_DIR / "metadata.json", metadata)
    write_json(WEB_DATA_DIR / "interpretations.json", entries)
    write_json(WEB_DATA_DIR / "metadata.json", metadata)
    write_js(WEB_DATA_DIR / "interpretations.js", "INTERPRETATIONS", entries)
    write_js(WEB_DATA_DIR / "metadata.js", "DATABASE_METADATA", metadata)
    write_csv(DATA_DIR / "interpretations.csv", entries)
    write_sqlite(DATA_DIR / "nursing_law_interpretations.sqlite", entries, pages)

    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
