const simulatorData = window.SIMULATOR_TOPICS || { metadata: {}, topics: [] };
const topics = Array.isArray(simulatorData.topics) ? simulatorData.topics : [];
const metadata = simulatorData.metadata || {};

const scenarioInput = document.querySelector("#scenario");
const simulateBtn = document.querySelector("#simulateBtn");
const matchCount = document.querySelector("#matchCount");
const matchHint = document.querySelector("#matchHint");
const matches = document.querySelector("#matches");
const template = document.querySelector("#topicTemplate");
const metaLine = document.querySelector("#metaLine");

function setMetaLine() {
  const topicCount = metadata.topic_count || topics.length;
  const sourceCount = metadata.source_count || 0;
  metaLine.textContent = `${topicCount} 個主題，${sourceCount} 筆代表來源，目前為草稿審核版`;
}

function scoreTopic(topic, query) {
  const compact = query.replace(/\s+/g, "");
  let score = 0;
  for (const keyword of topic.keywords || []) {
    if (keyword && compact.includes(keyword)) score += 8 + Math.min(keyword.length, 6);
  }
  for (const text of topic.scenario_triggers || []) {
    for (const piece of splitTerms(text)) {
      if (compact.includes(piece)) score += 3;
    }
  }
  if (compact.includes(topic.name || "")) score += 20;
  if (compact.includes(topic.group || "")) score += 8;
  return score;
}

function splitTerms(text) {
  return String(text)
    .replace(/[，、。；;：:]/g, " ")
    .split(/\s+/)
    .map((piece) => piece.trim())
    .filter((piece) => piece.length >= 3);
}

function formatSource(source) {
  const date = source.citation_date || source.date || "日期待補";
  const docNo = source.citation_document_no || source.document_no || "字號待補";
  const title = source.title || "標題待補";
  const parts = [];
  if (source.printed_page) parts.push(`書上頁碼 ${source.printed_page}`);
  if (source.physical_page) parts.push(`PDF頁碼 ${source.physical_page}`);
  if (source.source_url) parts.push(`<a href="${escapeHtml(source.source_url)}" target="_blank" rel="noreferrer">原文網址</a>`);
  return `${escapeHtml(date)}，${escapeHtml(docNo)}，${escapeHtml(title)}${parts.length ? `（${parts.join("；")}）` : ""}`;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function render() {
  const query = scenarioInput.value.trim();
  matches.replaceChildren();
  if (!query) {
    matchCount.textContent = "0 個主題";
    matchHint.textContent = "請輸入情境後按「模擬立場」。";
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "可以先按上方常用情境試試看。";
    matches.append(empty);
    return;
  }

  const ranked = topics
    .map((topic) => ({ topic, score: scoreTopic(topic, query) }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);

  matchCount.textContent = `${ranked.length} 個主題`;
  matchHint.textContent = ranked.length ? "依關鍵字與情境相似度排序。" : "找不到明顯相符主題，請換更具體的字詞。";

  if (!ranked.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = "建議改用：校護、幼兒園、執業登記、醫療輔助、照顧服務員、護病比、加班費。";
    matches.append(empty);
    return;
  }

  for (const { topic, score } of ranked) {
    const node = template.content.cloneNode(true);
    node.querySelector(".topic-group").textContent = topic.group || "";
    node.querySelector("h2").textContent = `${topic.id} ${topic.name}`;
    node.querySelector(".score").textContent = `相關 ${score}`;
    node.querySelector(".position").textContent = topic.position || "";

    const questions = node.querySelector(".questions");
    for (const question of topic.decision_questions || []) {
      const li = document.createElement("li");
      li.textContent = question;
      questions.append(li);
    }

    const outputs = node.querySelector(".outputs");
    for (const output of topic.likely_outputs || []) {
      const li = document.createElement("li");
      li.textContent = output;
      outputs.append(li);
    }

    const sources = node.querySelector(".sources");
    for (const source of (topic.sources || []).slice(0, 4)) {
      const li = document.createElement("li");
      li.innerHTML = formatSource(source);
      sources.append(li);
    }
    if (!sources.children.length) {
      const li = document.createElement("li");
      li.textContent = "待補代表來源";
      sources.append(li);
    }

    matches.append(node);
  }
}

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    scenarioInput.value = button.dataset.example || "";
    render();
    scenarioInput.focus();
  });
});

simulateBtn.addEventListener("click", render);
scenarioInput.addEventListener("input", () => {
  if (!scenarioInput.value.trim()) render();
});

setMetaLine();
render();
