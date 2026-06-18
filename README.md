# 護理人員法解釋彙編資料庫

這個資料夾保存「護理人員法解釋彙編108年5月.pdf」的第一版可查詢資料庫與靜態搜尋頁。

## 已完成

- 來源 PDF：`source/護理人員法解釋彙編108年5月.pdf`
- 結構化資料：`data/interpretations.json`
- 人工校對表：`data/interpretations.csv`
- SQLite 資料庫：`data/nursing_law_interpretations.sqlite`
- 靜態查詢頁：`web/index.html`

資料庫目前收錄彙編本體第 37 到 460 頁，不含附錄法規全文。每筆資料保存條文、分類、發文字號、日期、書上頁碼、PDF 實際頁碼與原文。

## 使用

本機預覽：

```bash
cd web
python3 -m http.server 8765
```

打開：

```text
http://127.0.0.1:8765
```

## 重建資料庫

```bash
/Users/lvlaiyan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 src/build_database.py
```

## 下一階段

第二階段可以把 `web/` 放到私有雲端或靜態網站。第三階段再接 AI 問答工具，讓系統先查 SQLite，再用查到的原文回答，並強制列出資料來源、條文、發文字號和頁碼。

跨地點查詢建議詳見 `docs/deployment_options.md`。
