/* ==========================================================================
   Déjà Vu — front end
   The screen has one job: make memory legible in under 30 seconds.
   ========================================================================== */
"use strict";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let selectSeq = 0;

const state = {
  overview: null,
  health: null,
  alerts: [],
  alert: null,
  off: null,
  on: null,
  memories: [],
  memStats: null,
  memFilter: "all",
  memQuery: "",
  incidents: [],
  incService: "all",
  incQuery: "",
  learning: null,
  bus: [],
  tab: "live",
  busy: false,
  story: false,
  storyAbort: false,
};

/* ------------------------------------------------------------------ utils */

const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

const pct = (v) => `${Math.round((Number(v) || 0) * 100)}%`;
const num = (v, d = 1) => {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return Number.isInteger(n) ? String(n) : n.toFixed(d);
};
const day = (ts) => String(ts || "").slice(0, 10);
const clock = (ts) => {
  try {
    return new Date(ts).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch { return "—"; }
};

function toast(msg, kind = "") {
  const wrap = $("#toasts");
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.innerHTML = `<span class="tdot"></span><span>${esc(msg)}</span>`;
  wrap.appendChild(el);
  setTimeout(() => {
    el.classList.add("out");
    setTimeout(() => el.remove(), 240);
  }, 4200);
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return res.json();
}

/* ------------------------------------------------------------------- boot */

async function boot() {
  bindChrome();
  bindModal();
  bindTabs();
  loadHealth();
  await Promise.all([loadOverview(), loadAlerts()]);
  if (state.alerts.length && !state.alert) {
    const open = state.alerts.find((a) => a.status === "open") || state.alerts[0];
    await selectAlert(open.id, { quiet: true });
  } else if (!state.alert) {
    renderStage();
  }
  loadBus();
  setInterval(loadBus, 4000);
  setInterval(loadHealth, 25000);
}

/* ----------------------------------------------------------------- badges */

async function loadHealth(retry = true) {
  try {
    const h = await api("/api/health");
    state.health = h;
    renderBadges();
  } catch {
    if (retry) setTimeout(() => loadHealth(false), 1200);
  }
}

function renderBadges() {
  const h = state.health;
  if (!h) return;
  const mem = $("#memBadge");
  const backend = h.memory?.backend || "local";
  const isHs = backend === "hindsight";
  mem.className = `badge ${isHs ? "ok" : "warn"}`;
  mem.innerHTML = `<i class="dot"></i><span>${isHs ? "HINDSIGHT" : "BM25 FALLBACK"}</span>`;
  mem.title = isHs
    ? `Hindsight at ${h.memory.url} · bank ${h.memory.bank}`
    : "Hindsight server unreachable — serving from the local SQLite mirror";

  const llm = $("#llmBadge");
  if (h.groq) {
    llm.className = "badge ok";
    llm.innerHTML = `<i class="dot"></i><span>${esc(h.model.replace("openai/", ""))}</span>`;
    llm.title = "Groq narrative synthesis is live";
  } else {
    llm.className = "badge neutral";
    llm.innerHTML = `<i class="dot"></i><span>template narrative</span>`;
    llm.title = "No GROQ_API_KEY set — using deterministic template narrative";
  }
}

/* --------------------------------------------------------------- overview */

async function loadOverview() {
  try {
    const o = await api("/api/overview");
    state.overview = o;
    const c = o.counts || {};
    $("#memCount").textContent = c.memories ?? "—";
  } catch { /* ignore */ }
}

/* ----------------------------------------------------------------- alerts */

async function loadAlerts() {
  try {
    const d = await api("/api/alerts");
    state.alerts = d.alerts || [];
    renderAlertList();
  } catch { /* ignore */ }
}

function renderAlertList() {
  const list = $("#alertList");
  if (!state.alerts.length) {
    list.innerHTML = `<div class="rail-empty">No alerts yet.<br />Fire one to begin.</div>`;
    return;
  }
  list.innerHTML = state.alerts
    .map((a) => {
      const active = state.alert && state.alert.id === a.id ? "active" : "";
      return `<button class="alert-item ${active}" data-alert="${esc(a.id)}">
        <span class="ai-top">
          <span class="sev ${esc(a.severity)}">${esc(a.severity)}</span>
          <span>${esc(clock(a.ts))}</span>
          <span class="status-dot ${a.status === "resolved" ? "resolved" : ""}"></span>
        </span>
        <span class="ai-title">${esc(a.title)}</span>
      </button>`;
    })
    .join("");

  $$("[data-alert]", list).forEach((el) =>
    el.addEventListener("click", () => selectAlert(el.dataset.alert))
  );
}

async function selectAlert(id, opts = {}) {
  const seq = ++selectSeq;
  try {
    const a = await api(`/api/alerts/${encodeURIComponent(id)}`);
    if (seq !== selectSeq) return; // a newer selection won the race
    state.alert = a;
    state.off = null;
    state.on = null;
    renderAlertList();
    renderStage();
    if (!opts.quiet) switchTab("live");
  } catch (e) {
    if (seq !== selectSeq) return;
    toast(`Could not load alert: ${e.message}`, "bad");
  }
}

async function fireAlert(scenario = "demo") {
  try {
    const a = await api("/api/alerts", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    });
    await loadAlerts();
    await selectAlert(a.id, { quiet: true });
    return a;
  } catch (e) {
    toast(`Could not fire alert: ${e.message}`, "bad");
    return null;
  }
}

/* ------------------------------------------------------------------ stage */

function renderStage() {
  const stage = $("#stage");
  if (!state.alert) {
    stage.innerHTML = `<div class="empty">
      <div class="empty-ring"></div>
      <h2>No incident selected</h2>
      <p>Fire a demo alert to watch the agent recall what happened last time — and what it got wrong.</p>
      <div class="empty-actions">
        <button class="btn primary lg" id="btnDemo2">▶ Run the full story</button>
        <button class="btn ghost lg" id="btnFire2">Fire an alert</button>
      </div>
    </div>`;
    const b = $("#btnDemo2");
    if (b) b.addEventListener("click", () => runStory());
    const f = $("#btnFire2");
    if (f) f.addEventListener("click", () => runStoryless("demo"));
    return;
  }

  stage.innerHTML = `
    ${alertSummary(state.alert)}
    <div id="verdictStrip"></div>
    <div class="split">
      <section class="mode-col" id="colOff">
        <div class="mode-head">
          <span class="mode-tag">off</span>
          <span class="mode-title">A generic on-call model</span>
          <span class="mode-sub">no memory</span>
        </div>
        <div class="mode-body" id="offBody"></div>
      </section>
      <section class="mode-col on" id="colOn">
        <div class="mode-head">
          <span class="mode-tag">on</span>
          <span class="mode-title">Déjà Vu</span>
          <span class="mode-sub" id="onMeta">${esc(backendLabel())}</span>
        </div>
        <div class="mode-body" id="onBody"></div>
      </section>
    </div>
    <div id="bandRoom"></div>`;

  renderOff(state.off);
  try {
    renderOn(state.on);
  } catch (err) {
    console.error("renderOn failed", err);
  }
  renderVerdict();
  renderBandRoom(state.on?.band || null);
}

function backendLabel() {
  const b = state.health?.memory?.backend;
  return b === "hindsight" ? "hindsight · dejavu-oncall" : "local bm25 mirror";
}

function alertSummary(a) {
  const sig = Object.entries(a.signals || {});
  return `<div class="alert-summary fade-in">
    <div class="as-top">
      <span class="sev ${esc(a.severity)}">${esc(a.severity)}</span>
      <span class="as-id">${esc(a.id)}</span>
      <span class="as-id">· ${esc(a.service)}</span>
      <span class="as-id">· ${esc(day(a.ts))} ${esc(clock(a.ts))}</span>
      ${a.status === "resolved" ? `<span class="pill-out resolved">resolved</span>` : `<span class="live-pill"><i></i>firing</span>`}
    </div>
    <h2 class="as-title">${esc(a.title)}</h2>
    <p class="as-body">${esc(a.body)}</p>
    <div class="sig-row">${sig
      .map(([k, v]) => `<span class="sig">${esc(k)} <b>${esc(v)}</b></span>`)
      .join("")}</div>
  </div>`;
}

/* -------------------------------------------------------------- off column */

function renderOff(payload) {
  const body = $("#offBody");
  if (!body) return;

  if (!payload) {
    body.innerHTML = `<div class="run-wrap">
      <p>A capable model with no memory of this service. It has read the same runbooks everyone else has.</p>
      <button class="btn" id="runOff">Run without memory</button>
    </div>`;
    $("#runOff").addEventListener("click", () => runAnalysis("off"));
    return;
  }

  const h = payload.hypothesis || {};
  body.innerHTML = `
    <div class="fade-in">
      <div class="hyp-label">Hypothesis</div>
      <h3 class="hyp-title">${esc(h.title || payload.title)}</h3>
      <div class="conf-row">
        <div class="conf-bar"><div class="conf-fill" style="width:${Math.round((h.confidence || 0.31) * 100)}%;background:linear-gradient(90deg,#5a6070,#3a3f4a);box-shadow:none"></div></div>
        <span class="conf-num" style="color:var(--muted)">${pct(h.confidence || 0.31)}</span>
      </div>
      <div class="meta-chips">
        <span class="chip">0 receipts</span>
        <span class="chip">no receipt</span>
        <span class="chip">no owner</span>
      </div>
    </div>

    <p class="narrative" style="border-left-color:var(--line)">${esc(payload.narrative)}</p>

    <div class="off-card">
      <div class="hyp-label" style="margin:0">Generic playbook</div>
      <ul class="off-list">
        ${(payload.actions || []).map((s) => `<li>${esc(s.step)}</li>`).join("")}
      </ul>
    </div>

    <div class="verdict">
      <span>✕</span>
      <span>No incident, no engineer, no fix time, no outcome. Nothing here can be audited after the fact.</span>
    </div>`;
}

/* --------------------------------------------------------------- on column */

function renderOn(payload) {
  const body = $("#onBody");
  if (!body) return;

  if (!payload) {
    const meta = $("#onMeta");
    if (meta) meta.textContent = backendLabel();
    body.innerHTML = `<div class="run-wrap">
      <p>Ask the same question with incident memory switched on. Every claim will link back to a real incident.</p>
      <button class="btn primary" id="runOn">Recall with memory</button>
    </div>`;
    $("#runOn").addEventListener("click", () => runAnalysis("on"));
    return;
  }

  const meta = $("#onMeta");
  if (meta) {
    const ms = Math.round(payload.memory_latency_ms || 0);
    meta.textContent = ms ? `${backendLabel()} · ${ms}ms recall` : backendLabel();
  }

  const h = payload.hypothesis || {};
  const evidence = payload.evidence || [];
  const conf = Number(h.confidence || 0);
  const ring = confidenceRing(conf);

  body.innerHTML = `
    <div class="fade-in">
      <div class="hyp-head">
        <div style="flex:1 1 auto;min-width:0">
          <div class="hyp-label">Recalled root cause</div>
          <h3 class="hyp-title">${esc(h.title)}</h3>
        </div>
        ${ring}
      </div>

      <div class="meta-chips">
        <span class="chip good">${h.support} receipt${h.support === 1 ? "" : "s"}</span>
        <span class="chip good">${pct(h.success_rate)} success</span>
        <span class="chip">${num(h.fix_minutes, 0)} min fix</span>
        <span class="chip">${esc(h.engineer)}</span>
        ${evidence.some((e) => e.stale) ? `<span class="chip warn">stale — revalidate</span>` : ""}
      </div>
    </div>

    <p class="narrative">${esc(payload.narrative)}</p>

    <div class="first-action">
      <div class="fa-label"><span>◆</span> Do this first</div>
      <div class="fa-text">${esc(payload.first_action || h.fix)}</div>
    </div>

    ${receiptsBlock(evidence, payload.hypothesis?.support || evidence.length)}

    ${payload.contradiction ? contradictionBlock(payload.contradiction) : ""}

    ${signalFingerprint(payload)}

    ${stepsBlock(payload.actions || [])}

    ${payload.avoid && payload.avoid.length ? avoidBlock(payload.avoid) : ""}

    ${traceBlock(payload)}

    <div class="resolve-cta">
      <div>
        <strong>Did it work?</strong>
        <span>Resolve, and the lesson is retained — with your name and the minutes it took.</span>
      </div>
      <button class="btn primary" id="openResolve">Resolve &amp; retain</button>
    </div>
  `;

  const rb = $("#openResolve");
  if (rb) rb.addEventListener("click", () => openModal(true));
}

function confidenceRing(conf) {
  const r = 27;
  const c = 2 * Math.PI * r;
  const dash = c * Math.max(0, Math.min(1, conf));
  return `<div class="ring" title="Confidence ${pct(conf)}">
    <svg viewBox="0 0 64 64" width="64" height="64">
      <circle cx="32" cy="32" r="${r}" fill="none" stroke="#23262e" stroke-width="4"/>
      <circle cx="32" cy="32" r="${r}" fill="none" stroke="url(#rg)" stroke-width="4"
        stroke-linecap="round" stroke-dasharray="${dash} ${c}" transform="rotate(-90 32 32)"/>
      <defs><linearGradient id="rg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0%" stop-color="#ff8a3d"/><stop offset="100%" stop-color="#ff5c1a"/>
      </linearGradient></defs>
    </svg>
    <div class="ring-num">${Math.round(conf * 100)}<span>%</span></div>
  </div>`;
}

function receiptsBlock(evidence, support) {
  if (!evidence.length) return "";
  const bank = state.overview?.counts?.memories;
  return `<div>
    <div class="section-title">Memory receipts${bank ? ` · ${support || evidence.length} of ${bank} in bank` : ""}</div>
    ${timelineBlock(evidence)}
    <div class="receipts">
      ${evidence
        .map((e) => {
          const outClass = e.outcome === "resolved" ? "ok" : e.outcome === "recurred" ? "stale" : "no";
          return `<div class="receipt" title="${esc(e.title)}">
            <span class="rid">${esc(e.incident_id)}</span>
            <span class="rcause">${esc(e.root_cause)}</span>
            <span class="rscore">${Math.round((e.similarity || 0) * 100)}% match</span>
            <span class="rmeta">
              <span>${esc(e.service)}</span>
              <span>${esc(day(e.ts))}</span>
              <span class="${outClass}">${esc(e.outcome)}</span>
              <span>${num(e.fix_minutes, 0)} min</span>
              <span>${esc(e.engineer)}</span>
              ${e.stale ? `<span class="stale">stale</span>` : ""}
            </span>
          </div>`;
        })
        .join("")}
    </div>
  </div>`;
}

/* When did this failure pattern actually happen? A strip makes history visible. */
function timelineBlock(evidence) {
  const times = evidence
    .map((e) => ({ t: new Date(e.ts).getTime(), e }))
    .filter((x) => Number.isFinite(x.t));
  if (times.length < 2) return "";
  const min = Math.min(...times.map((x) => x.t));
  const max = Date.now();
  const span = Math.max(1, max - min);
  const pos = (t) => Math.min(100, Math.max(0, ((t - min) / span) * 100));
  const fmt = (t) => new Date(t).toLocaleDateString([], { day: "numeric", month: "short" });

  const dots = times
    .map(
      ({ t, e }) => `<span class="tl-dot ${e.outcome === "resolved" ? "ok" : "warn"}"
        style="left:${pos(t).toFixed(1)}%"
        title="${esc(e.incident_id)} · ${esc(day(e.ts))} · ${esc(e.outcome)}"></span>`
    )
    .join("");

  return `<div class="timeline">
    <span class="tl-line"></span>
    ${dots}
    <span class="tl-now" style="left:100%"></span>
    <span class="tl-label start">${esc(fmt(min))}</span>
    <span class="tl-label end">now</span>
    <span class="tl-mid">this failure pattern, seen ${times.length}×</span>
  </div>`;
}

function contradictionBlock(cd) {
  return `<div class="contradiction">
    <div class="cd-head"><span>⚠</span> Contradiction guard</div>
    <div class="cd-title">
      <b>${esc(cd.incident_id)}</b> looks almost identical but ended with
      <b>${esc(cd.root_cause)}</b> — ${pct(cd.similarity)} similarity.
    </div>
    <div class="cd-note"><strong>Why not:</strong> ${esc(cd.why_not)}<br />
      <strong>Different fix:</strong> ${esc(cd.different_fix)}</div>
  </div>`;
}

/* Compare the alert fingerprint against the closest recalled incident. */
function signalFingerprint(payload) {
  const alertSig = payload.alert?.signals || {};
  const top = (payload.receipts || [])[0];
  if (!top || !top.signals) return "";
  const memSig = top.signals;

  const rows = Object.entries(alertSig).map(([k, a]) => {
    const has = Object.prototype.hasOwnProperty.call(memSig, k);
    const b = memSig[k];
    let closeness = 0;
    let kind = "absent";
    if (has) {
      if (typeof a === "number" && typeof b === "number") {
        const d = Math.max(Math.abs(a), Math.abs(b), 1e-9);
        closeness = 1 - Math.min(1, Math.abs(a - b) / d);
        kind = closeness > 0.85 ? "match" : closeness > 0.5 ? "close" : "diff";
      } else {
        closeness = String(a).toLowerCase() === String(b).toLowerCase() ? 1 : 0;
        kind = closeness ? "match" : "diff";
      }
    }
    return { k, a, b, has, closeness, kind };
  });

  const matched = rows.filter((r) => r.kind === "match").length;
  const scored = rows.filter((r) => r.kind !== "absent").length || 1;

  return `<div>
    <div class="section-title">Signal fingerprint · vs ${esc(top.incident_id)}</div>
    <div class="fingerprint">
      <div class="fp-head">
        <span>signal</span><span>this alert</span><span>recalled</span><span class="fp-bar-h">fit</span>
      </div>
      ${rows
        .map(
          (r) => `<div class="fp-row ${r.kind}">
            <span class="fp-k">${esc(r.k)}</span>
            <span class="fp-v">${esc(r.a)}</span>
            <span class="fp-v dim">${r.has ? esc(r.b) : "not reported"}</span>
            <span class="fp-bar"><i style="width:${Math.round(r.closeness * 100)}%"></i></span>
          </div>`
        )
        .join("")}
      <div class="fp-foot">${matched}/${scored} comparable signals agree · the rest are what keep this from being a text match</div>
    </div>
  </div>`;
}

function stepsBlock(actions) {
  if (!actions.length) return "";
  return `<div>
    <div class="section-title">Plan · grounded in the receipts</div>
    <div class="steps">
      ${actions
        .map(
          (a, i) => `<div class="step">
            <div class="num">${i + 1}</div>
            <div>
              <div class="st-text">${esc(a.step)}</div>
              <div class="st-why">${esc(a.why)}</div>
              <span class="st-src">${esc(a.source)}</span>
            </div>
          </div>`
        )
        .join("")}
    </div>
  </div>`;
}

function avoidBlock(avoid) {
  return `<div class="avoid-card">
    <div class="cd-head"><span>✕</span> Do not repeat this</div>
    ${avoid.map((a) => `<p>${esc(a)}</p>`).join("")}
  </div>`;
}

function traceBlock(p) {
  const tr = p.trace || [];
  return `<div class="trace">
    ${tr
      .map(
        (t, i) =>
          `${i ? `<span class="arr">→</span>` : ""}<span class="tr"><b>${esc(t.step)}</b> ${esc(t.label)}${
            t.ms ? ` · ${t.ms}ms` : ""
          }</span>`
      )
      .join("")}
    <span class="arr">·</span>
    <span class="tr"><b>${esc(p.backend || "local")}</b> ${p.llm ? "llm" : "no-llm"}</span>
  </div>`;
}

/* ---------------------------------------------------------------- verdict */

function renderVerdict() {
  const el = $("#verdictStrip");
  if (!el) return;
  if (!state.off || !state.on) { el.innerHTML = ""; return; }
  const on = state.on;
  const h = on.hypothesis || {};
  const offConf = (state.off?.hypothesis?.confidence) || 0.31;
  const saved = Math.max(0, Math.round((h.fix_minutes ? 45 - h.fix_minutes : 39)));
  el.innerHTML = `<div class="verdict-hero fade-in">
    <div class="vh-left">
      <div class="vh-eyebrow">Same alert · two answers</div>
      <div class="vh-grid">
        <div class="vh-col off">
          <span class="vh-tag">memory off</span>
          <span class="vh-head">${esc(state.off?.hypothesis?.title || "Generic triage")}</span>
          <span class="vh-sub">${esc(state.off?.first_action || "Restart the affected pods")}</span>
          <div class="vh-stats">
            <span>${pct(offConf)} confidence</span>
            <span>0 receipts</span>
            <span>no owner</span>
          </div>
        </div>
        <div class="vh-mid">
          <div class="vh-arrow">→</div>
          <div class="vh-saved">≈ ${saved} min saved</div>
        </div>
        <div class="vh-col on">
          <span class="vh-tag on">memory on</span>
          <span class="vh-head">${esc(h.title)}</span>
          <span class="vh-sub">${esc(on.first_action || h.fix)}</span>
          <div class="vh-stats">
            <span>${pct(h.confidence)} confidence</span>
            <span>${h.support} receipt${h.support === 1 ? "" : "s"}</span>
            <span>${num(h.fix_minutes, 0)} min · ${esc(h.engineer)}</span>
          </div>
        </div>
      </div>
    </div>
    <div class="vh-ring">${confidenceRing(h.confidence || 0)}</div>
  </div>`;
}

/* ------------------------------------------------------------- band room */

function mdLite(s) {
  return esc(s)
    .replace(/\*\*(.+?)\*\*/g, "<b>$1</b>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br />");
}

function renderBandRoom(band) {
  const el = $("#bandRoom");
  if (!el) return;
  if (!band || !band.messages || !band.messages.length) {
    el.innerHTML = "";
    return;
  }
  const live = band.transport === "band";
  const review = band.review || {};
  const v = review.verdict || "allow";
  const label = { allow: "ALLOWED", review: "NEEDS REVIEW", block: "BLOCKED" }[v] || v.toUpperCase();

  const msgs = band.messages
    .map((m) => {
      const who = m.role === "critic" ? "critic" : "recall";
      return `<div class="br-msg ${who}">
        <div class="br-who">
          <span class="br-avatar">${who === "critic" ? "◇" : "◆"}</span>
          <span class="br-author">${esc(m.author)}</span>
          <span class="br-tag">${esc(m.kind)}</span>
        </div>
        <div class="br-body">${mdLite(m.body)}</div>
      </div>`;
    })
    .join("");

  el.innerHTML = `<section class="band-room">
    <div class="br-head">
      <span class="br-title"><span class="br-glyph">◈</span> Band room <span class="br-chan">#on-call</span></span>
      <span class="br-right">
        <span class="br-transport ${live ? "live" : ""}">${live ? "delivered to Band" : "local preview"}</span>
        <span class="br-verdict ${v}">${label}</span>
      </span>
    </div>
    <div class="br-sub">Two agents, one decision. The critic reviews the recall before anything reaches a human.</div>
    <div class="br-feed">${msgs}</div>
    <div class="br-foot">
      <span class="br-rule">${esc(review.reason || "")}</span>
      <span class="br-hint">${live ? "X-API-Key · Agent API" : "set BAND_API_KEY + BAND_CHAT_ID to post for real"}</span>
    </div>
  </section>`;
}

/* --------------------------------------------------------------- analysis */

const RECALL_STEPS = [
  "encoding the alert signature",
  "hindsight.recall(bank=dejavu-oncall, budget=mid)",
  "reranking by signal fingerprint + outcome",
  "synthesising the narrative from receipts",
];

async function runAnalysis(mode, opts = {}) {
  if (!state.alert || state.busy) return null;
  state.busy = true;
  const body = mode === "off" ? $("#offBody") : $("#onBody");
  if (!body) { state.busy = false; return null; }

  const t0 = performance.now();
  let ticker = null;

  if (mode === "off") {
    body.innerHTML = `<div class="run-wrap">
      <div class="spinner"></div>
      <p>Reading the runbook. No memory of this service.</p>
    </div>`;
  } else {
    body.innerHTML = `<div class="recall">
      <div class="recall-head"><span class="spinner"></span> recalling from <b>dejavu-oncall</b></div>
      <div class="recall-lines" id="recallLines"></div>
    </div>`;
    ticker = animateRecall($("#recallLines"), RECALL_STEPS, 320);
  }

  try {
    const payload = await api("/api/analyze", {
      method: "POST",
      body: JSON.stringify({ alert_id: state.alert.id, mode }),
    });

    if (mode === "off") state.off = payload;
    else state.on = payload;

    // let the animation breathe for a beat even when the API is instant
    if (mode === "on") {
      await ticker;
      const elapsed = performance.now() - t0;
      if (elapsed < 900) await sleep(900 - elapsed);
    }

    if (mode === "off") renderOff(payload);
    else renderOn(payload);
    renderVerdict();
    if (mode === "on") renderBandRoom(payload.band || null);
    loadBus();
    return payload;
  } catch (e) {
    if (mode === "off") renderOff(null);
    else renderOn(null);
    toast(`Analysis failed: ${e.message}`, "bad");
    return null;
  } finally {
    state.busy = false;
  }
}

async function animateRecall(container, steps, gap) {
  if (!container) return;
  for (const s of steps) {
    const line = document.createElement("div");
    line.className = "recall-line";
    line.innerHTML = `<span class="rl-dot"></span><span>${esc(s)}</span><span class="rl-ms">…</span>`;
    container.appendChild(line);
    await sleep(gap);
    const ms = line.querySelector(".rl-ms");
    if (ms) ms.textContent = "ok";
  }
}

/* ------------------------------------------------------------------ story */

async function runStory() {
  if (state.story || state.busy) return;
  state.story = true;
  state.storyAbort = false;
  const btn = $("#btnStory");
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Running the story…`;
  }

  try {
    toast("02:14 — SEV-1 on checkout-api. The page fires.");
    const a = await fireAlert("demo");
    if (!a || state.storyAbort) return;
    await sleep(1200);
    if (state.storyAbort) return;

    toast("Memory OFF: a generic model answers.");
    await runAnalysis("off");
    await sleep(2200);
    if (state.storyAbort) return;

    toast("Memory ON: same alert, now with 34 retained incidents.");
    await runAnalysis("on");
    await sleep(2600);
    if (state.storyAbort) return;

    const h = state.on?.hypothesis;
    if (h) {
      toast("Resolving and retaining the lesson…");
      await api("/api/resolve", {
        method: "POST",
        body: JSON.stringify({
          alert_id: state.alert.id,
          root_cause: h.title,
          cause_class: h.cause_class || "",
          fix: h.fix,
          engineer: h.engineer || "Abinivesh M",
          minutes: h.fix_minutes || 6,
          outcome: "resolved",
        }),
      });
      await loadAlerts();
      await sleep(1600);
      if (state.storyAbort) return;
    }

    toast("09:41 — the same fingerprint fires again.");
    const b = await fireAlert("repeat");
    if (!b || state.storyAbort) return;
    await sleep(900);
    if (state.storyAbort) return;

    const second = await runAnalysis("on");
    if (second) {
      toast(
        `Answered from memory in ${Math.round(second.memory_latency_ms || 0)}ms — it now cites the incident it just learned.`,
        "good"
      );
    }
  } catch (e) {
    toast(`Story stopped: ${e.message}`, "bad");
  } finally {
    state.story = false;
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `<span class="play">▶</span> Run the story`;
    }
  }
}

async function runStoryless(scenario) {
  const a = await fireAlert(scenario);
  if (a) toast("Alert fired. Run it with memory off, then on.");
}

/* ------------------------------------------------------------------ modal */

function bindModal() {
  const wrap = $("#modalWrap");
  $("#modalClose").addEventListener("click", closeModal);
  $("#modalCancel").addEventListener("click", closeModal);
  wrap.addEventListener("click", (e) => { if (e.target === wrap) closeModal(); });

  $("#resolveForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const btn = $("#resolveSubmit");
    btn.disabled = true;
    btn.innerHTML = `<span class="spinner"></span> Retaining…`;
    try {
      const r = await api("/api/resolve", {
        method: "POST",
        body: JSON.stringify({
          alert_id: fd.get("alert_id"),
          root_cause: fd.get("root_cause"),
          cause_class: fd.get("cause_class") || "",
          fix: fd.get("fix"),
          engineer: fd.get("engineer"),
          minutes: Number(fd.get("minutes")),
          outcome: fd.get("outcome"),
        }),
      });
      closeModal();
      toast(`Retained ${r.incident_id} — the next matching alert will find it.`, "good");
      await Promise.all([loadAlerts(), loadHealth()]);
      await selectAlert(state.alert.id, { quiet: true });
      loadBus();
    } catch (err) {
      toast(`Could not retain: ${err.message}`, "bad");
    } finally {
      btn.disabled = false;
      btn.textContent = "Retain this lesson";
    }
  });
}

function openModal(prefill = true) {
  const form = $("#resolveForm");
  form.reset();
  form.alert_id.value = state.alert?.id || "";
  if (prefill && state.on?.hypothesis) {
    const h = state.on.hypothesis;
    form.root_cause.value = h.title || "";
    form.fix.value = h.fix || "";
    form.cause_class.value = h.cause_class || "";
    form.minutes.value = Math.max(1, Math.round(h.fix_minutes || 6));
    form.engineer.value = h.engineer && h.engineer !== "none" ? h.engineer : "Abinivesh M";
  }
  $("#modalWrap").classList.remove("hidden");
  setTimeout(() => form.root_cause.focus(), 60);
}

function closeModal() {
  $("#modalWrap").classList.add("hidden");
}

/* ------------------------------------------------------------------ chrome */

function bindChrome() {
  $("#btnDemo").addEventListener("click", async () => {
    const btn = $("#btnDemo");
    if (state.busy || state.story) return;
    btn.disabled = true;
    const prev = btn.innerHTML;
    btn.innerHTML = `<span class="spinner"></span> Firing…`;
    try { await runStoryless("demo"); }
    finally { btn.disabled = false; btn.innerHTML = prev; }
  });

  const story = $("#btnStory");
  if (story) story.addEventListener("click", runStory);

  const reset = $("#btnReset");
  let armed = false;
  let timer = null;
  reset.addEventListener("click", async () => {
    if (!armed) {
      armed = true;
      reset.textContent = "Sure?";
      reset.style.color = "var(--bad)";
      timer = setTimeout(() => {
        armed = false;
        reset.textContent = "Reset";
        reset.style.color = "";
      }, 3200);
      return;
    }
    clearTimeout(timer);
    armed = false;
    reset.textContent = "Reset";
    reset.style.color = "";
    await api("/api/reset", { method: "POST", body: JSON.stringify({ fresh: false }) });
    state.alert = null; state.off = null; state.on = null;
    await Promise.all([loadAlerts(), loadOverview()]);
    renderStage();
    loadBus();
    toast("Cleared alerts and analyses.", "good");
  });

  $("#busToggle").addEventListener("click", () => {
    const bus = $(".bus");
    bus.classList.toggle("open");
    if (bus.classList.contains("open")) loadBus();
  });

  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, textarea, select")) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    const k = e.key.toLowerCase();
    if (k === "1") switchTab("live");
    if (k === "2") switchTab("memory");
    if (k === "3") switchTab("learning");
    if (k === "4") switchTab("incidents");
    if (k === "d") runStoryless("demo");
    if (k === "s") runStory();
    if (k === "m" && state.alert) runAnalysis("on");
    if (k === "b") $("#busToggle").click();
    if (k === "r" && state.alert) openModal(true);
  });
}

/* -------------------------------------------------------------------- tabs */

function bindTabs() {
  $$(".tab").forEach((t) => t.addEventListener("click", () => switchTab(t.dataset.tab)));
}

function switchTab(name) {
  state.tab = name;
  $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
  $$(".panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${name}`));
  if (name === "memory" && !state.memories.length) loadMemory();
  if (name === "learning" && !state.learning) loadLearning();
  if (name === "incidents" && !state.incidents.length) loadIncidents();
}

/* ------------------------------------------------------------------ memory */

async function loadMemory(q = state.memQuery) {
  const grid = $("#memoryGrid");
  if (grid) grid.innerHTML = Array.from({ length: 6 }).map(() => `<div class="mem-card skeleton" style="height:118px"></div>`).join("");
  try {
    const d = await api(`/api/memory?q=${encodeURIComponent(q)}`);
    state.memories = d.memories || [];
    state.memStats = d.stats || null;
    state.memQuery = q;
    renderMemory();
  } catch (e) {
    if (grid) grid.innerHTML = `<div class="empty-mini">Memory unavailable: ${esc(e.message)}</div>`;
  }
}

function renderMemory() {
  const stats = state.memStats || {};
  $("#memStats").innerHTML = `
    ${statCard("Retained incidents", stats.memories ?? state.memories.length, "memories")}
    ${statCard("Learned live", stats.learned_live ?? 0, "closed-loop", "accent")}
    ${statCard("Stale", stats.stale ?? 0, "flagged for revalidation", "warn")}
    ${statCard("Bank", "dejavu-oncall", "hindsight")}`;

  let rows = state.memories.slice();
  if (state.memFilter === "resolved") rows = rows.filter((m) => m.outcome === "resolved");
  if (state.memFilter === "recurred") rows = rows.filter((m) => m.outcome !== "resolved");
  if (state.memFilter === "stale") rows = rows.filter((m) => m.stale);
  if (state.memFilter === "live") rows = rows.filter((m) => String(m.memory_id || "").includes("LIVE"));

  const filters = `
    <div class="filters">
      ${["all", "resolved", "recurred", "stale", "live"]
        .map(
          (f) =>
            `<button class="filter ${state.memFilter === f ? "active" : ""}" data-memfilter="${f}">${
              f === "live" ? "learned live" : f
            }</button>`
        )
        .join("")}
    </div>`;

  const grid = $("#memoryGrid");
  grid.innerHTML =
    filters +
    (rows.length
      ? rows
          .map((m) => {
            const live = String(m.memory_id || "").includes("LIVE");
            return `<article class="mem-card ${m.stale ? "is-stale" : ""}">
              <div class="mc-top">
                <span class="rid">${esc(m.incident_id)}</span>
                <span class="sev ${m.service === "checkout-api" ? "SEV-2" : "SEV-3"}" style="border:0;background:transparent;padding:0;color:var(--muted)">${esc(m.service)}</span>
                ${live ? `<span class="chip good" style="margin-left:auto">learned live</span>` : ""}
                ${m.stale ? `<span class="chip warn" style="margin-left:auto">stale</span>` : ""}
              </div>
              <div class="mc-cause">${esc(m.root_cause)}</div>
              <div class="mc-fix">${esc(m.fix)}</div>
              <div class="mc-foot">
                <span class="pill-out ${esc(m.outcome)}">${esc(m.outcome)}</span>
                <span>${num(m.fix_minutes, 0)} min</span>
                <span class="who">${esc(m.engineer)}</span>
                <span style="margin-left:auto">${esc(day(m.created_at))}</span>
              </div>
            </article>`;
          })
          .join("")
      : `<div class="empty-mini">No memories match “${esc(state.memQuery)}” with this filter.</div>`);

  $$("[data-memfilter]", grid).forEach((b) =>
    b.addEventListener("click", () => {
      state.memFilter = b.dataset.memfilter;
      renderMemory();
    })
  );
}

function statCard(label, value, note, tone = "") {
  return `<div class="stat">
    <div class="s-label">${esc(label)}</div>
    <div class="s-value ${tone}">${esc(value)}${typeof value === "number" ? "" : ""}</div>
    <div class="s-note">${esc(note)}</div>
  </div>`;
}

/* ---------------------------------------------------------------- learning */

async function loadLearning() {
  try {
    const d = await api("/api/learning");
    state.learning = d;
    renderLearning();
  } catch (e) {
    $("#learnStats").innerHTML = `<div class="empty-mini">Replay unavailable: ${esc(e.message)}</div>`;
  }
}

function renderLearning() {
  const d = state.learning;
  if (!d) return;

  $("#replayBadge").textContent = `${d.graded} graded · no future memories`;
  $("#learnStats").innerHTML = `
    <div class="stat">
      <div class="s-label">Top-1 accuracy</div>
      <div class="s-value accent">${pct(d.top1)}</div>
      <div class="s-note">cause class correct on first guess</div>
    </div>
    <div class="stat">
      <div class="s-label">Top-3</div>
      <div class="s-value">${pct(d.top3)}</div>
      <div class="s-note">cause class in the shortlist</div>
    </div>
    <div class="stat">
      <div class="s-label">Early incidents</div>
      <div class="s-value" style="color:var(--bad)">${pct(d.early)}</div>
      <div class="s-note">first six graded alerts</div>
    </div>
    <div class="stat">
      <div class="s-label">Recent incidents</div>
      <div class="s-value good">${pct(d.late)}</div>
      <div class="s-note">last six graded alerts</div>
    </div>`;

  $("#chart").innerHTML = chartSVG(d.points || []);

  const sample = (p) => `<div class="sample">
    <div class="sm-top">
      <span class="rid">${esc(p.incident_id)}</span>
      <span>${esc(p.ts)}</span>
      <span style="margin-left:auto">${esc(p.service)}</span>
    </div>
    <div class="sm-text">Predicted <b>${esc(p.predicted)}</b><br />Actual <b>${esc(p.actual)}</b></div>
  </div>`;

  $("#sampleRight").innerHTML = (d.sample_right || []).map(sample).join("") || `<div class="empty-mini">—</div>`;
  $("#sampleWrong").innerHTML = (d.sample_wrong || []).map(sample).join("") || `<div class="empty-mini">—</div>`;
}

function chartSVG(points) {
  if (!points.length) return `<div class="empty-mini">No graded points yet.</div>`;
  const W = 1000, H = 250, L = 42, R = 16, T = 16, B = 34;
  const iw = W - L - R, ih = H - T - B;
  const n = points.length;
  const x = (i) => L + (n === 1 ? iw / 2 : (i / (n - 1)) * iw);
  const y = (v) => T + ih - v * ih;

  const path = points.map((p, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(p.accuracy).toFixed(1)}`).join(" ");
  const area = `${path} L${x(n - 1).toFixed(1)},${T + ih} L${x(0).toFixed(1)},${T + ih} Z`;

  const grid = [0, 0.25, 0.5, 0.75, 1]
    .map(
      (v) => `<line x1="${L}" y1="${y(v)}" x2="${W - R}" y2="${y(v)}" stroke="#1e222a" stroke-width="1"/>
              <text x="${L - 9}" y="${y(v) + 3.5}" text-anchor="end" fill="#5c626e" font-size="10" font-family="var(--mono)">${v * 100}%</text>`
    )
    .join("");

  const dots = points
    .map((p, i) => {
      const c = p.correct ? "#34d399" : "#ff5468";
      return `<g class="pt">
        <circle cx="${x(i).toFixed(1)}" cy="${y(p.accuracy).toFixed(1)}" r="4" fill="${c}" stroke="#0e1013" stroke-width="1.5">
          <title>${esc(p.incident_id)} · ${esc(p.ts)} · ${p.correct ? "correct" : "missed"} · cumulative ${pct(p.accuracy)}
Predicted: ${esc(p.predicted)}
Actual: ${esc(p.actual)}</title>
        </circle>
      </g>`;
    })
    .join("");

  const labels = points
    .map((p, i) =>
      i % Math.max(1, Math.ceil(n / 8)) === 0 || i === n - 1
        ? `<text x="${x(i).toFixed(1)}" y="${H - 12}" text-anchor="middle" fill="#5c626e" font-size="9.5" font-family="var(--mono)">${esc(p.ts.slice(5))}</text>`
        : ""
    )
    .join("");

  return `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet" role="img" aria-label="Cumulative top-1 accuracy across replayed incidents">
    <defs>
      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="#ff5c1a" stop-opacity="0.28"/>
        <stop offset="100%" stop-color="#ff5c1a" stop-opacity="0"/>
      </linearGradient>
      <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="#ff8a3d"/><stop offset="100%" stop-color="#ff5c1a"/>
      </linearGradient>
    </defs>
    ${grid}
    <path d="${area}" fill="url(#areaGrad)"/>
    <path d="${path}" fill="none" stroke="url(#lineGrad)" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round"/>
    ${dots}
    ${labels}
  </svg>`;
}

/* --------------------------------------------------------------- incidents */

async function loadIncidents() {
  try {
    const d = await api("/api/incidents");
    state.incidents = d.incidents || [];
    renderIncidents();
  } catch (e) {
    toast(`Could not load incidents: ${e.message}`, "bad");
  }
}

function renderIncidents() {
  const card = $("#tab-incidents .table-card");
  if (!card) return;
  const services = ["all", ...Array.from(new Set(state.incidents.map((i) => i.service)))];
  const q = state.incQuery.toLowerCase();
  const rows = state.incidents.filter(
    (i) =>
      (state.incService === "all" || i.service === state.incService) &&
      (!q || `${i.id} ${i.title} ${i.root_cause} ${i.cause_class} ${i.service}`.toLowerCase().includes(q))
  );

  card.innerHTML = `
    <div class="table-tools">
      <div class="filters">
        ${services
          .map(
            (s) =>
              `<button class="filter ${state.incService === s ? "active" : ""}" data-incservice="${esc(s)}">${esc(s)}</button>`
          )
          .join("")}
      </div>
      <div class="searchbox small">
        <svg viewBox="0 0 20 20" width="15" height="15"><circle cx="9" cy="9" r="6" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M13.5 13.5L18 18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>
        <input id="incSearch" placeholder="Filter incidents…" value="${esc(state.incQuery)}" />
      </div>
    </div>
    <div class="table-scroll">
      <table class="table" id="incTable">
        <thead><tr><th>Incident</th><th>Date</th><th>Service</th><th>What happened</th><th>Cause class</th><th>Outcome</th><th class="r">Time</th></tr></thead>
        <tbody>
          ${rows
            .map(
              (i) => `<tr>
                <td class="tid">${esc(i.id)}</td>
                <td class="tsvc">${esc(day(i.ts))}</td>
                <td class="tsvc">${esc(i.service)}</td>
                <td class="ttitle">${esc(i.title)}</td>
                <td class="tclass">${esc(i.cause_class || i.root_cause)}</td>
                <td><span class="pill-out ${esc(i.outcome)}">${esc(i.outcome)}</span></td>
                <td class="r">${num(i.fix_minutes, 0)} min</td>
              </tr>`
            )
            .join("") || `<tr><td colspan="7"><div class="empty-mini">No incidents match.</div></td></tr>`}
        </tbody>
      </table>
    </div>`;

  $$("[data-incservice]", card).forEach((b) =>
    b.addEventListener("click", () => {
      state.incService = b.dataset.incservice;
      renderIncidents();
    })
  );
  const search = $("#incSearch", card);
  search.addEventListener("input", () => {
    state.incQuery = search.value;
    const pos = search.selectionStart;
    renderIncidents();
    const again = $("#incSearch");
    if (again) { again.focus(); again.setSelectionRange(pos, pos); }
  });
}

/* -------------------------------------------------------------------- bus */

async function loadBus() {
  try {
    const d = await api("/api/bus");
    state.bus = d.ops || [];
    renderBus(d.backend);
  } catch { /* ignore */ }
}

function renderBus(backend) {
  const log = $("#busLog");
  if (!log) return;
  const ops = state.bus.slice(0, 24);
  $("#busMeta").textContent = ops.length
    ? `${ops.length} ops · ${backend === "hindsight" ? "hindsight" : "local"} · retain / recall`
    : "retain · recall · reflect";

  log.innerHTML = ops
    .map((o) => {
      const hs = o.backend === "hindsight";
      return `<div class="bus-line">
        <span>${esc(clock(o.ts))}</span>
        <span class="b-op ${esc(o.op)}">${esc(o.op)}</span>
        <span class="b-q" title="${esc(o.detail || o.query)}">${esc(o.query)}</span>
        <span class="b-meta"><span class="${hs ? "hs" : ""}">${esc(o.backend)}</span> · ${o.n_results} · ${Math.round(o.latency_ms)}ms</span>
      </div>`;
    })
    .join("") || `<div class="bus-line"><span></span><span class="b-op">idle</span><span class="b-q">no memory operations yet</span><span></span></div>`;
}

/* ------------------------------------------------------------------- init */

document.addEventListener("DOMContentLoaded", boot);
