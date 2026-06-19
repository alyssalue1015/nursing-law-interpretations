from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOPICS_JSON = ROOT / "simulator" / "data" / "simulator_topics.json"


def load_topics() -> list[dict]:
    data = json.loads(TOPICS_JSON.read_text(encoding="utf-8"))
    return data["topics"]


def score_topic(topic: dict, query: str) -> int:
    compact = query.replace(" ", "")
    score = 0
    for keyword in topic["keywords"]:
        if keyword and keyword in compact:
            score += 8 + min(len(keyword), 6)
    for text in topic["scenario_triggers"]:
        for piece in split_terms(text):
            if piece in compact:
                score += 3
    if topic["name"] in compact:
        score += 20
    if topic["group"] in compact:
        score += 8
    return score


def split_terms(text: str) -> list[str]:
    pieces = []
    for raw in text.replace("，", " ").replace("、", " ").replace("。", " ").split():
        raw = raw.strip()
        if len(raw) >= 3:
            pieces.append(raw)
    return pieces


def format_source(source: dict) -> str:
    date = source.get("citation_date") or source.get("date") or "日期待補"
    doc_no = source.get("citation_document_no") or source.get("document_no") or "字號待補"
    title = source.get("title") or "標題待補"
    parts = []
    if source.get("printed_page"):
        parts.append(f"書上頁碼 {source['printed_page']}")
    if source.get("physical_page"):
        parts.append(f"PDF頁碼 {source['physical_page']}")
    if source.get("source_url"):
        parts.append(f"原文網址 {source['source_url']}")
    tail = "；".join(parts)
    return f"{date}，{doc_no}，{title}" + (f"（{tail}）" if tail else "")


def simulate(query: str, limit: int) -> str:
    topics = load_topics()
    ranked = sorted(
        ((topic, score_topic(topic, query)) for topic in topics),
        key=lambda item: item[1],
        reverse=True,
    )
    matches = [(topic, score) for topic, score in ranked if score > 0][:limit]
    if not matches:
        return "找不到明顯相符主題。請改用更具體的字詞，例如：校護、幼兒園、執業登記、醫療輔助、照顧服務員。"

    lines = [f"情境：{query}", ""]
    for topic, score in matches:
        lines.extend(
            [
                f"## {topic['id']} {topic['name']}（相關度 {score}）",
                "",
                f"立場：{topic['position']}",
                "",
                "判斷問題：",
            ]
        )
        for question in topic["decision_questions"]:
            lines.append(f"- {question}")
        lines.extend(["", "可能結論："])
        for output in topic["likely_outputs"]:
            lines.append(f"- {output}")
        lines.extend(["", "代表來源："])
        if topic["sources"]:
            for source in topic["sources"][:4]:
                lines.append(f"- {format_source(source)}")
        else:
            lines.append("- 待補代表來源")
        lines.append("")
    return "\n".join(lines).rstrip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the nursing position simulator topic matching.")
    parser.add_argument("query", help="Scenario text to test.")
    parser.add_argument("--limit", type=int, default=3, help="Number of matching topics to show.")
    args = parser.parse_args()
    print(simulate(args.query, args.limit))


if __name__ == "__main__":
    main()
