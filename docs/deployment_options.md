# 護理人員法解釋彙編資料庫上線方式

## 目前完成的第一版

- `data/nursing_law_interpretations.sqlite`: 給後續 AI 問答工具使用的資料庫。
- `data/interpretations.csv`: 給人工校對或 Excel/Google Sheet 使用。
- `web/index.html`: 可直接查詢的靜態網頁。
- `web/data/interpretations.js`: 網頁用的搜尋資料。

## 建議上線方式

### 方式一：私有 GitHub repository + GitHub Pages

適合：資料不涉及個資，且你希望辦公室、家裡都能用網址開。

優點是維護最簡單，靜態網頁不用伺服器。缺點是 GitHub Pages 在私人倉庫的可見性要依帳號方案與設定確認，若資料不能外流，要先確認權限。

### 方式二：Google Drive 放網頁檔 + 自己開 HTML

適合：先快速共享給自己使用。

把整個 `web/` 資料夾放到 Drive，辦公室電腦下載或同步後開 `index.html`。優點是最少設定，缺點是它不是一個真正網址，每台電腦要能拿到資料夾。

### 方式三：家中 Mac 當主機，用 Cloudflare Tunnel

適合：你希望資料留在家中本機，但辦公室可以用網址查。

優點是資料庫不必放到公開雲端，之後也適合接 AI 問答工具。缺點是家中電腦要保持開機，並且要設定 Tunnel 與登入保護。

### 方式四：小型雲端主機

適合：之後要做 AI 問答、帳密登入、多份法規彙編、使用紀錄。

可用 Render、Fly.io、Railway、Cloud Run 或 VPS。優點是最完整，缺點是需要部署與金鑰管理。

## 我建議的路線

第一階段先用靜態網頁：`web/index.html`。

第二階段若只要自己跨地點查詢，用「私有 GitHub Pages」或「Cloudflare Tunnel」。如果要接 AI 問答，我建議用 Cloudflare Tunnel 或小型雲端主機，因為 AI 金鑰不能放在純靜態網頁裡。
