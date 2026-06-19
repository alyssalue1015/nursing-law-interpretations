# 護理立場模擬器資料庫

這個資料夾是獨立於「護理人員法解釋彙編查詢庫」的第二套資料庫。

## 用途

- 查詢庫：找原文、日期、發文字號、頁碼、網址。
- 模擬器資料庫：把既有函釋歸納成主題、判準與可比附立場，用於遇到新增或類似議題時產生回應草稿。

## 已產出檔案

- `data/simulator_topics.json`：主資料，含 27 個主題、判準、立場與代表函釋摘要。
- `data/simulator_sources.json`：代表來源原始資料，保留原文、頁碼、網址等引用欄位。
- `data/simulator_topics.csv`：給人工檢查用的主題表。
- `data/nursing_position_simulator.sqlite`：後續 AI 模擬器可直接查詢的 SQLite 資料庫。

## 引用原則

PDF 彙編來源需保留：

- 日期
- 發文字號
- 書上頁碼
- PDF 實際頁碼
- 原文內容或可引用摘錄

官方網頁來源需保留：

- 原文網址
- 清單來源網址
- 頁面發布或清單日期
- 附件公文日期與發文字號，如附件可抽取
- 原文內容或可引用摘錄

## 重建方式

```bash
/Users/lvlaiyan/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 src/build_simulator_database.py
```

重建會讀取既有查詢庫：

```text
data/nursing_law_interpretations.sqlite
```

並只輸出到：

```text
simulator/data/
```

不會覆蓋 `web/`、`docs/` 或昨天完成的查詢網站。

## 下一步

先人工確認 27 個主題與代表函釋是否可行。確認後，再做共同來源擷取器，讓衛福部「人員執業」與「機構管理」兩頁更新時，可同時重建查詢庫與模擬器資料庫。
