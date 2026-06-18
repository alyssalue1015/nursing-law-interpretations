const entries = Array.isArray(window.INTERPRETATIONS) ? window.INTERPRETATIONS : [];
const metadata = window.DATABASE_METADATA || {};

const queryInput = document.querySelector("#query");
const clearBtn = document.querySelector("#clearBtn");
const articleFilter = document.querySelector("#articleFilter");
const categoryFilter = document.querySelector("#categoryFilter");
const sortMode = document.querySelector("#sortMode");
const resultCount = document.querySelector("#resultCount");
const queryHint = document.querySelector("#queryHint");
const results = document.querySelector("#results");
const template = document.querySelector("#resultTemplate");
const metaLine = document.querySelector("#metaLine");

const searchableFields = ["title", "body", "law_name", "article", "category", "document_no"];
const knownTerms = [
  "護理人員",
  "專科護理師",
  "護理師",
  "護士",
  "護理機構",
  "居家護理",
  "產後護理",
  "坐月子",
  "護理之家",
  "照顧服務員",
  "醫療輔助",
  "執業登記",
  "執業執照",
  "負責人",
  "開業",
  "收費",
  "評鑑",
  "督導考核",
  "繼續教育",
  "停業",
  "歇業",
  "廣告",
  "病歷",
  "管路",
  "傷口",
  "給藥",
  "餵藥",
  "採血",
  "口腔",
  "麻醉",
  "公共衛生",
  "預防保健",
  "學校",
  "診所",
  "醫院",
  "申請",
  "許可",
  "罰鍰",
];

function uniqueSorted(values) {
  return [...new Set(values.filter(Boolean))].sort((a, b) => a.localeCompare(b, "zh-Hant"));
}

function initFilters() {
  for (const article of uniqueSorted(entries.map((entry) => entry.article))) {
    const option = document.createElement("option");
    option.value = article;
    option.textContent = article;
    articleFilter.append(option);
  }
  for (const category of uniqueSorted(entries.map((entry) => entry.category))) {
    const option = document.createElement("option");
    option.value = category;
    option.textContent = category;
    categoryFilter.append(option);
  }
}

function termsFromQuery(query) {
  const rawTerms = query
    .trim()
    .split(/[\s,，、。；;]+/)
    .map((term) => term.trim())
    .filter(Boolean);
  const expanded = [...rawTerms];
  const compactQuery = query.replace(/[\s,，、。；;]+/g, "");
  for (const term of knownTerms) {
    if (compactQuery.includes(term) && !expanded.includes(term)) expanded.push(term);
  }
  if (rawTerms.length === 1 && expanded.length > 1) {
    return expanded.filter((term) => term !== compactQuery || term.length <= 2);
  }
  return expanded;
}

function scoreEntry(entry, terms) {
  if (!terms.length) return 0;
  let score = 0;
  const combined = searchableFields.map((field) => entry[field] || "").join("\n");
  for (const term of terms) {
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const occurrences = combined.match(new RegExp(escaped, "gi")) || [];
    if (!occurrences.length) return 0;
    score += occurrences.length;
    if ((entry.title || "").includes(term)) score += 8;
    if ((entry.document_no || "").includes(term)) score += 10;
    if ((entry.article || "").includes(term)) score += 6;
    if ((entry.category || "").includes(term)) score += 5;
  }
  return score;
}

function scoreEntryAny(entry, terms) {
  if (!terms.length) return 0;
  let score = 0;
  const combined = searchableFields.map((field) => entry[field] || "").join("\n");
  for (const term of terms) {
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const occurrences = combined.match(new RegExp(escaped, "gi")) || [];
    if (!occurrences.length) continue;
    score += occurrences.length;
    if ((entry.title || "").includes(term)) score += 8;
    if ((entry.document_no || "").includes(term)) score += 10;
    if ((entry.article || "").includes(term)) score += 6;
    if ((entry.category || "").includes(term)) score += 5;
  }
  return score;
}

function highlight(text, terms) {
  let output = escapeHtml(text || "");
  for (const term of [...terms].sort((a, b) => b.length - a.length)) {
    const escapedTerm = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    output = output.replace(new RegExp(escapedTerm, "gi"), (match) => `<mark>${match}</mark>`);
  }
  return output;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function pageLabel(entry) {
  if (entry.source_url) return "官方網頁";
  const start = entry.start_printed_page;
  const end = entry.end_printed_page;
  if (!start) return "頁碼待校";
  return start === end ? `第 ${start} 頁` : `第 ${start}-${end} 頁`;
}

function makeSnippet(entry, terms) {
  const fallback = entry.snippet || "";
  if (!terms.length) return fallback;

  const body = entry.body || "";
  const positions = terms
    .map((term) => ({ term, index: body.indexOf(term) }))
    .filter(({ index }) => index >= 0)
    .sort((a, b) => a.index - b.index);

  if (!positions.length) return fallback;

  const start = Math.max(0, positions[0].index - 90);
  const end = Math.min(body.length, positions[0].index + 260);
  const prefix = start > 0 ? "..." : "";
  const suffix = end < body.length ? "..." : "";
  return prefix + body.slice(start, end).replace(/\s+/g, " ").trim() + suffix;
}

function sourceLinks(entry) {
  const links = [];
  if (entry.source_url) {
    links.push(`<a href="${escapeHtml(entry.source_url)}" target="_blank" rel="noreferrer">開啟來源網頁</a>`);
  }
  if (entry.drive_url) {
    links.push(`<a href="${escapeHtml(entry.drive_url)}" target="_blank" rel="noreferrer">開啟來源 PDF</a>`);
  }
  return links.join("　");
}

function render() {
  const query = queryInput.value;
  const terms = termsFromQuery(query);
  const article = articleFilter.value;
  const category = categoryFilter.value;

  let partialMode = false;
  let matches = entries
    .map((entry) => ({ entry, score: scoreEntry(entry, terms) }))
    .filter(({ entry, score }) => {
      if (terms.length && score <= 0) return false;
      if (article && entry.article !== article) return false;
      if (category && entry.category !== category) return false;
      return terms.length || article || category;
    });

  if (!matches.length && terms.length > 1) {
    partialMode = true;
    matches = entries
      .map((entry) => ({ entry, score: scoreEntryAny(entry, terms) }))
      .filter(({ entry, score }) => {
        if (score <= 0) return false;
        if (article && entry.article !== article) return false;
        if (category && entry.category !== category) return false;
        return true;
      });
  }

  if (sortMode.value === "page") {
    matches.sort((a, b) => (a.entry.start_printed_page || 9999) - (b.entry.start_printed_page || 9999));
  } else if (sortMode.value === "date") {
    matches.sort((a, b) => String(b.entry.issued_date).localeCompare(String(a.entry.issued_date)));
  } else {
    matches.sort((a, b) => b.score - a.score || (a.entry.start_printed_page || 9999) - (b.entry.start_printed_page || 9999));
  }

  resultCount.textContent = `${matches.length} 筆`;
  queryHint.textContent = terms.length
    ? `${partialMode ? "部分符合：" : "搜尋："}${terms.join("、")}`
    : "可用條文或分類篩選，也可以直接輸入疑問。";
  results.replaceChildren();

  if (!matches.length) {
    const empty = document.createElement("p");
    empty.className = "empty";
    empty.textContent = terms.length || article || category ? "沒有找到符合條件的資料。" : "請輸入關鍵字開始查詢。";
    results.append(empty);
    return;
  }

  for (const { entry, score } of matches.slice(0, 80)) {
    const node = template.content.cloneNode(true);
    node.querySelector("h2").innerHTML = highlight(entry.title || entry.document_no, terms);
    node.querySelector(".score").textContent = score ? `相關 ${score}` : pageLabel(entry);

    const chips = node.querySelector(".chips");
    const chipTexts = [
      entry.article,
      entry.category,
      entry.document_no,
      entry.issued_date_raw,
      entry.source_quality,
      entry.source_title,
      pageLabel(entry),
    ].filter(Boolean);
    for (const text of chipTexts) {
      const chip = document.createElement("span");
      chip.className = "chip";
      chip.textContent = text;
      chips.append(chip);
    }

    node.querySelector(".snippet").innerHTML = highlight(makeSnippet(entry, terms), terms);
    if (entry.completeness_note) {
      node.querySelector(".snippet").title = entry.completeness_note;
    }
    const sourceUrl = node.querySelector(".source-url");
    const links = sourceLinks(entry);
    if (links) {
      sourceUrl.innerHTML = links;
    } else {
      sourceUrl.remove();
    }
    node.querySelector("pre").textContent = entry.body;
    results.append(node);
  }
}

function setMetaLine() {
  const count = metadata.interpretation_entries || entries.length;
  const pages = metadata.pdf_pages || "";
  metaLine.textContent = `${count.toLocaleString()} 筆解釋資料${pages ? `，來源 PDF ${pages} 頁` : ""}`;
}

initFilters();
setMetaLine();
render();

queryInput.addEventListener("input", render);
articleFilter.addEventListener("change", render);
categoryFilter.addEventListener("change", render);
sortMode.addEventListener("change", render);
clearBtn.addEventListener("click", () => {
  queryInput.value = "";
  queryInput.focus();
  render();
});
