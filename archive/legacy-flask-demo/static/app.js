"use strict";

const $ = (id) => document.getElementById(id);
let currentTicker = "";
let chart = null;

function fmt(v, digits = 2) {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return Number(v).toLocaleString("zh-CN", {
    minimumFractionDigits: digits, maximumFractionDigits: digits,
  });
}

function fmtInt(v) {
  if (v === null || v === undefined) return "—";
  return Math.round(Number(v)).toLocaleString("zh-CN");
}

// 大额金额：万亿 / 亿 / 万
function fmtBig(v) {
  if (v === null || v === undefined) return "—";
  const a = Math.abs(v);
  if (a >= 1e12) return fmt(v / 1e12) + " 万亿";
  if (a >= 1e8) return fmt(v / 1e8) + " 亿";
  if (a >= 1e4) return fmt(v / 1e4) + " 万";
  return fmt(v);
}

function fmtYi(v) { // 财务报表：统一换算成亿元
  if (v === null || v === undefined) return "—";
  return fmt(v / 1e8);
}

function setStatus(msg, isError = false) {
  const el = $("status");
  el.textContent = msg;
  el.className = "status" + (isError ? " error" : "");
}

async function fetchJSON(url) {
  const resp = await fetch(url);
  const data = await resp.json();
  if (!resp.ok) throw new Error(data.error || `请求失败（${resp.status}）`);
  return data;
}

// ---------------- 行情与概览 ----------------

function renderQuote(q) {
  $("q-name").textContent = q.name || q.ticker;
  $("q-ticker").textContent = q.ticker + (q.demo ? " · 演示数据" : "");
  $("q-price").textContent = fmt(q.price);
  $("q-currency").textContent = q.currency || "";
  const ch = $("q-change");
  if (q.change !== null && q.change !== undefined) {
    const sign = q.change >= 0 ? "+" : "";
    ch.textContent = `${sign}${fmt(q.change)} (${sign}${fmt(q.change_pct)}%)`;
    ch.className = "change " + (q.change >= 0 ? "up" : "down");
  } else {
    ch.textContent = "";
  }
  const stats = [
    ["市 值", fmtBig(q.market_cap)],
    ["市盈率 P/E (TTM)", fmt(q.pe_ttm)],
    ["预期市盈率 Forward P/E", fmt(q.forward_pe)],
    ["每股收益 EPS (TTM)", fmt(q.eps_ttm)],
    ["股息率", q.dividend_yield == null ? "—" : fmt(q.dividend_yield) + "%"],
    ["Beta", fmt(q.beta, 3)],
    ["52 周最高", fmt(q.week52_high)],
    ["52 周最低", fmt(q.week52_low)],
    ["成交量", fmtInt(q.volume)],
    ["昨 收", fmt(q.previous_close)],
    ["日内区间", (q.day_low == null ? "—" : fmt(q.day_low)) + " – " + (q.day_high == null ? "—" : fmt(q.day_high))],
    ["总股本", fmtBig(q.shares_outstanding)],
  ];
  $("stats-grid").innerHTML = stats.map(
    ([k, v]) => `<div class="stat"><span class="k">${k}</span><span class="v">${v}</span></div>`
  ).join("");
}

async function renderChart(ticker) {
  const data = await fetchJSON(`/api/history?ticker=${encodeURIComponent(ticker)}`);
  const pts = data.points || [];
  const labels = pts.map((p) => p.date);
  const closes = pts.map((p) => p.close);
  if (chart) chart.destroy();
  chart = new Chart($("price-chart"), {
    type: "line",
    data: {
      labels,
      datasets: [{
        label: "收盘价", data: closes, borderColor: "#f5b942",
        backgroundColor: "rgba(245,185,66,0.12)", fill: true,
        borderWidth: 1.6, pointRadius: 0, tension: 0.15,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      scales: {
        x: { ticks: { color: "#93a0bb", maxTicksLimit: 8 }, grid: { color: "#232c47" } },
        y: { ticks: { color: "#93a0bb" }, grid: { color: "#232c47" } },
      },
      plugins: { legend: { labels: { color: "#e8ecf5" } } },
    },
  });
}

// ---------------- 财务报表 ----------------

async function renderFinancials(ticker) {
  const thead = $("fin-table").querySelector("thead");
  const tbody = $("fin-table").querySelector("tbody");
  let data;
  try {
    data = await fetchJSON(`/api/financials?ticker=${encodeURIComponent(ticker)}`);
  } catch (e) {
    thead.innerHTML = "";
    tbody.innerHTML = `<tr><td>${e.message}</td></tr>`;
    return;
  }
  const years = data.years || [];
  const rows = [
    ["营业收入", "revenue"],
    ["毛利润", "gross_profit"],
    ["营业利润", "operating_income"],
    ["净利润", "net_income"],
    ["自由现金流 FCF", "free_cash_flow"],
  ];
  thead.innerHTML = "<tr><th>科目（亿元）</th>" + years.map((y) => `<th>${y.year}</th>`).join("") + "</tr>";
  tbody.innerHTML = rows.map(([label, key]) =>
    `<tr><td>${label}</td>` + years.map((y) => `<td>${fmtYi(y[key])}</td>`).join("") + "</tr>"
  ).join("");
}

// ---------------- 估值 ----------------

function valuationQuery(ticker) {
  const p = new URLSearchParams({ ticker });
  const g = $("in-growth").value, t = $("in-terminal").value,
        d = $("in-discount").value, dg = $("in-ddm-growth").value;
  if (g !== "") p.set("growth", g);
  if (t !== "") p.set("terminal", t);
  if (d !== "") p.set("discount", d);
  if (dg !== "") p.set("ddm_growth", dg);
  return p.toString();
}

async function renderValuation(ticker) {
  const data = await fetchJSON(`/api/valuation?${valuationQuery(ticker)}`);
  const inp = data.inputs || {};

  $("dcf-meta").innerHTML =
    `基准 FCF（最近财年）：<b>${fmtBig(inp.base_fcf)}</b> · ` +
    `总债务：<b>${fmtBig(inp.total_debt)}</b> · 现金：<b>${fmtBig(inp.total_cash)}</b> · ` +
    `总股本：<b>${fmtBig(inp.shares_outstanding)}</b><br>` +
    `CAPM 折现率 = 4% + Beta(${fmt(inp.beta, 2)}) × 5% = <b>${fmt(inp.discount_default_capm)}%</b>` +
    (inp.balance_note ? `<br>⚠️ ${inp.balance_note}` : "");
  if (document.activeElement !== $("in-discount") && $("in-discount").value === "") {
    $("in-discount").placeholder = fmt(inp.discount);
  }

  // DCF 结果
  const dcfEl = $("dcf-result");
  if (data.dcf) {
    const up = data.dcf.upside_pct;
    const upCls = up >= 0 ? "up" : "down";
    dcfEl.innerHTML =
      `<div class="kv">
         <div>DCF 每股内在价值<b class="big-value">${fmt(data.dcf.per_share)}</b></div>
         <div>相对现价<b class="${upCls}" style="font-size:17px">${up >= 0 ? "+" : ""}${fmt(up)}%</b></div>
         <div>企业价值 EV<b>${fmtBig(data.dcf.enterprise_value)}</b></div>
         <div>终值占 EV<b>${fmt((data.dcf.pv_terminal_ratio || 0) * 100, 1)}%</b></div>
       </div>`;
  } else {
    dcfEl.innerHTML = `<p class="note">自由现金流或股本数据缺失，无法计算 DCF。</p>`;
  }

  // 敏感性
  const sHead = $("sens-table").querySelector("thead");
  const sBody = $("sens-table").querySelector("tbody");
  if (data.sensitivity) {
    sHead.innerHTML = "<tr><th>折现率 \\ 永续增速</th>" +
      data.sensitivity.terminal_growths.map((g) => `<th>${fmt(g, 1)}%</th>`).join("") + "</tr>";
    sBody.innerHTML = data.sensitivity.rows.map((r) =>
      `<tr><td>${fmt(r.discount)}%</td>` +
      r.values.map((v) => `<td>${fmt(v)}</td>`).join("") + "</tr>"
    ).join("");
  } else {
    sHead.innerHTML = ""; sBody.innerHTML = "<tr><td>数据不足</td></tr>";
  }

  // 倍数
  $("multiples").innerHTML = (data.multiples || []).map((m) =>
    `<div class="mult-row"><div>${m.name}<div class="f">${m.formula}</div></div>` +
    `<div class="mv">${fmt(m.value)}</div></div>`
  ).join("") || `<p class="note">暂无倍数数据</p>`;

  // 股利折现
  if (data.ddm) {
    $("ddm-card").classList.remove("hidden");
    $("ddm-result").innerHTML =
      `<div class="kv">
         <div>股利折现每股价值<b>${fmt(data.ddm.per_share)}</b></div>
         <div>当前股息率<b>${fmt(data.ddm.dividend_yield)}%</b></div>
         <div>假设股利增速<b>${fmt(data.ddm.growth)}%</b></div>
         <div>折现率<b>${fmt(data.ddm.discount)}%</b></div>
       </div>
       <p class="note">公式：价值 = 每股股利 ×(1+g) ÷ (r − g)，每股股利 = 股价 × 股息率。</p>`;
  } else {
    $("ddm-card").classList.add("hidden");
  }

  // 综合
  const s = data.summary;
  const bandEl = $("q-band");
  if (s) {
    const cls = s.band === "低估" ? "low" : (s.band === "高估" ? "high" : "fair");
    $("summary-result").innerHTML =
      `<div class="kv">
         <div>各方法平均每股价值<b>${fmt(s.average_value)}</b></div>
         <div>参与方法数<b>${s.methods_used}</b></div>
         <div>相对现价<b>${s.vs_price_pct >= 0 ? "+" : ""}${fmt(s.vs_price_pct)}%</b></div>
         <div>模型判定<b class="band ${cls}" style="padding:2px 12px">${s.band}</b></div>
       </div>
       <p class="note">判定规则：平均值高于现价 15% 以上为「低估」，低于现价 15% 以上为「高估」，其间为「合理」。这是模型输出，不是投资建议。</p>`;
    bandEl.textContent = `模型判定：${s.band}`;
    bandEl.className = "band " + cls;
  } else {
    $("summary-result").innerHTML = `<p class="note">可用估值方法不足，暂无法给出综合结论。</p>`;
    bandEl.className = "band hidden";
  }
  return data;
}

// ---------------- 主流程 ----------------

async function loadAll(ticker) {
  currentTicker = ticker.toUpperCase();
  setStatus(`正在加载 ${currentTicker} …`);
  $("quote-section").classList.add("hidden");
  try {
    const quote = await fetchJSON(`/api/quote?ticker=${encodeURIComponent(currentTicker)}`);
    renderQuote(quote);
    $("quote-section").classList.remove("hidden");
    setStatus(quote.demo ? "演示模式数据已加载。" : "数据已更新。");
    renderChart(currentTicker).catch((e) => setStatus("图表加载失败：" + e.message, true));
    renderFinancials(currentTicker);
    renderValuation(currentTicker).catch((e) => setStatus("估值加载失败：" + e.message, true));
  } catch (e) {
    setStatus(e.message, true);
  }
}

$("search-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const t = $("ticker-input").value.trim();
  if (t) loadAll(t);
});

$("dcf-form").addEventListener("submit", (e) => {
  e.preventDefault();
  if (currentTicker) {
    renderValuation(currentTicker).catch((err) => setStatus("估值加载失败：" + err.message, true));
  }
});

document.querySelectorAll(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    document.querySelectorAll(".tab-page").forEach((p) => p.classList.add("hidden"));
    $("tab-" + btn.dataset.tab).classList.remove("hidden");
  });
});
