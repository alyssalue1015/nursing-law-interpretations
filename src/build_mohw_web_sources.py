#!/usr/bin/env python3
import html
import json
import re
import ssl
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SOURCE_DIR = ROOT / "source" / "mohw_web"
BASE = "https://nurse.mohw.gov.tw/"
PAGES = [
    {
        "url": "https://nurse.mohw.gov.tw/lp-125-2.html",
        "section": "人員執業",
        "category": "衛福部護助e起來 / 法規解釋函 / 人員執業",
    },
    {
        "url": "https://nurse.mohw.gov.tw/lp-126-2.html",
        "section": "機構管理",
        "category": "衛福部護助e起來 / 法規解釋函 / 機構管理",
    },
]


SSL_CONTEXT = ssl._create_unverified_context()


def fetch_bytes(url: str) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, context=SSL_CONTEXT, timeout=30) as response:
        content_type = response.headers.get("content-type", "")
        return response.read(), content_type


def decode_html(data: bytes) -> str:
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("big5", errors="replace")


def strip_tags(text: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>", " ", text)
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p|</div|</li|</h\d", "\n<", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def clean_title(raw: str) -> str:
    text = strip_tags(raw)
    text = re.sub(r"^\d+\s*", "", text)
    text = re.sub(r"\s*\d{2,3}-\d{2}-\d{2}\s*$", "", text)
    return compact(text)


def page_title(markup: str) -> str:
    match = re.search(r"(?is)<title>(.*?)</title>", markup)
    return compact(match.group(1)) if match else ""


def parse_list(markup: str, page: dict) -> list[dict]:
    block_match = re.search(r'(?is)<section class="lp">(.*?)</section>', markup)
    block = block_match.group(1) if block_match else markup
    item_re = re.compile(
        r'(?is)<li>\s*<a\s+href="(?P<href>[^"]+)"\s+title="(?P<title>[^"]*)".*?'
        r'<span class="num">(?P<num>\d+)</span>(?P<body>.*?)<time>(?P<date>[^<]+)</time>'
    )
    items = []
    for match in item_re.finditer(block):
        url = urljoin(page["url"], html.unescape(match.group("href")))
        title = clean_title(match.group("body")) or compact(match.group("title"))
        items.append(
            {
                "list_url": page["url"],
                "section": page["section"],
                "category": page["category"],
                "order": int(match.group("num")),
                "title": title,
                "source_url": url,
                "published_date_raw": compact(match.group("date")),
            }
        )
    return items


def extract_file_links(markup: str, base_url: str) -> list[dict]:
    links = []
    block_match = re.search(r'(?is)<div class="web_link">(.*?)</div>\s*<div class="bottom_info"', markup)
    block = block_match.group(1) if block_match else markup
    for href, title, label in re.findall(r'(?is)<a[^>]+href="([^"]+)"[^>]*title="([^"]*)"[^>]*>(.*?)</a>', block):
        url = urljoin(base_url, html.unescape(href))
        if "/dl-" not in url and ".pdf" not in compact(title).lower() and ".pdf" not in compact(label).lower():
            continue
        links.append({"url": url, "title": compact(label) or compact(title)})
    return links


def extract_detail(item: dict) -> dict:
    data, content_type = fetch_bytes(item["source_url"])
    if "pdf" in content_type.lower() or item["source_url"].lower().endswith(".pdf"):
        text, saved = extract_pdf_text(data, item)
        return {"body": text, "attachments": [], "saved_files": [saved] if saved else []}

    markup = decode_html(data)
    text = strip_tags(extract_main_content(markup))
    attachments = []
    saved_files = []
    for link in extract_file_links(markup, item["source_url"]):
        try:
            pdf_data, pdf_content_type = fetch_bytes(link["url"])
            pdf_text, saved = extract_pdf_text(pdf_data, item, link["title"])
            attachments.append({**link, "text": pdf_text})
            if saved:
                saved_files.append(saved)
            time.sleep(0.1)
        except Exception as exc:
            attachments.append({**link, "error": str(exc)})

    body_parts = [text]
    for attachment in attachments:
        if attachment.get("text"):
            body_parts.append(f"附件：{attachment['title']}\n{attachment['text']}")
    return {"body": "\n\n".join(part for part in body_parts if part), "attachments": attachments, "saved_files": saved_files}


def extract_main_content(markup: str) -> str:
    match = re.search(r'(?is)<div id="center".*?</h2>(.*?)(?:<section class="fatfooter"|<footer>)', markup)
    if match:
        return match.group(1)
    return markup


def safe_name(text: str) -> str:
    text = re.sub(r"[\\/:*?\"<>|]+", "_", text)
    text = re.sub(r"\s+", "_", text).strip("_")
    return text[:120] or "download"


def extract_pdf_text(data: bytes, item: dict, title: str | None = None) -> tuple[str, str | None]:
    SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    name = safe_name(title or item["title"])
    path = SOURCE_DIR / f"{item['section']}_{item['order']:02d}_{name}.pdf"
    path.write_bytes(data)
    reader = PdfReader(str(path))
    parts = []
    for index, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        page_text = page_text.strip()
        if page_text:
            parts.append(f"[附件PDF第 {index} 頁]\n{page_text}")
    return "\n\n".join(parts).strip(), str(path.relative_to(ROOT))


def normalize_entry(item: dict, detail: dict) -> dict:
    body = detail.get("body") or item["title"]
    return {
        "source_title": "衛福部護助e起來法規解釋函",
        "source_type": "官方網頁",
        "source_url": item["source_url"],
        "list_url": item["list_url"],
        "law_name": "衛福部護助e起來法規解釋函",
        "article": "",
        "category": item["category"],
        "issued_date_raw": item["published_date_raw"],
        "issued_date": roc_to_iso(item["published_date_raw"]),
        "document_no": "",
        "title": item["title"],
        "start_printed_page": None,
        "end_printed_page": None,
        "start_physical_page": None,
        "end_physical_page": None,
        "body": body,
        "snippet": compact(body)[:320],
        "keywords": [],
        "attachments": detail.get("attachments", []),
        "saved_files": detail.get("saved_files", []),
    }


def roc_to_iso(raw: str) -> str:
    nums = re.findall(r"\d+", raw)
    if len(nums) >= 3:
        return f"{int(nums[0]) + 1911:04d}-{int(nums[1]):02d}-{int(nums[2]):02d}"
    return raw


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    all_entries = []
    source_lists = []
    for page in PAGES:
        data, _ = fetch_bytes(page["url"])
        markup = decode_html(data)
        items = parse_list(markup, page)
        source_lists.append({"url": page["url"], "title": page_title(markup), "count": len(items)})
        for item in items:
            try:
                detail = extract_detail(item)
            except Exception as exc:
                detail = {"body": item["title"], "attachments": [], "saved_files": [], "error": str(exc)}
            entry = normalize_entry(item, detail)
            all_entries.append(entry)
            time.sleep(0.15)

    payload = {
        "source_lists": source_lists,
        "entries": all_entries,
    }
    (DATA_DIR / "mohw_web_sources.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"source_lists": source_lists, "entries": len(all_entries)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
