const state = {
  role: localStorage.getItem("lend_role") || null,
  theme: localStorage.getItem("lend_theme") || "bright",
  page: "home",
  apps: [],
  selectedId: null,
  summary: null,
  filters: {
    week: "All",
    risk: "All",
    sort: "pd_probability",
    q: "",
    assigned: "All",
    decision: "All",
  },
};

const $app = document.getElementById("app");

function fmtPct(x) {
  return `${(Number(x) * 100).toFixed(1)}%`;
}
function fmtMoney(x) {
  return Number(x).toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  });
}
function badge(band) {
  const cls =
    band === "Risky" ? "badge-high" : band === "Moderately risky" ? "badge-mid" : "badge-low";
  return `<span class="badge ${cls}">${band}</span>`;
}
function decisionBadge(status) {
  const map = {
    Approve: "badge-low",
    Refer: "badge-mid",
    Decline: "badge-high",
    Pending: "badge-pending",
  };
  return `<span class="badge ${map[status] || "badge-pending"}">${status || "Pending"}</span>`;
}
function calloutClass(band) {
  return band === "Risky" ? "high" : band === "Moderately risky" ? "mid" : "low";
}

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) return res.json();
  return res.text();
}

function setTheme(theme) {
  state.theme = theme;
  localStorage.setItem("lend_theme", theme);
  document.body.dataset.theme = theme;
  syncThemeToggle();
}

function themeIconSvg(theme) {
  if (theme === "night") {
    // sun = switch to light
    return `<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
      <circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>
    </svg>`;
  }
  // moon = switch to dark
  return `<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 14.5A8.5 8.5 0 0 1 9.5 3 7 7 0 1 0 21 14.5z"/>
  </svg>`;
}

function themeToggleHtml() {
  const isNight = state.theme === "night";
  return `<button type="button" class="theme-fab" id="theme-toggle" aria-label="${
    isNight ? "Switch to light mode" : "Switch to dark mode"
  }" title="${isNight ? "Light mode" : "Dark mode"}">${themeIconSvg(state.theme)}</button>`;
}

function syncThemeToggle() {
  const btn = document.getElementById("theme-toggle");
  if (!btn) return;
  const isNight = state.theme === "night";
  btn.setAttribute("aria-label", isNight ? "Switch to light mode" : "Switch to dark mode");
  btn.title = isNight ? "Light mode" : "Dark mode";
  btn.innerHTML = themeIconSvg(state.theme);
}

function toggleTheme() {
  setTheme(state.theme === "night" ? "bright" : "night");
}

function bindThemeToggle() {
  document.getElementById("theme-toggle")?.addEventListener("click", (e) => {
    e.preventDefault();
    toggleTheme();
  });
}

function setRole(role) {
  state.role = role;
  localStorage.setItem("lend_role", role);
  state.page = role === "Underwriter" ? "home" : "admin-home";
  render();
}

function logout() {
  state.role = null;
  localStorage.removeItem("lend_role");
  render();
}

function disclaimer() {
  return `<div class="disclaimer">Synthetic demo data · Charged-Off proxy for default · not production risk scoring</div>`;
}

function shell(navItems, content, { showRoleSwitch = true } = {}) {
  const nav = navItems
    .map(
      ([id, label]) =>
        `<button class="nav-btn ${state.page === id ? "active" : ""}" data-nav="${id}">${label}</button>`
    )
    .join("");
  const otherRole = state.role === "Underwriter" ? "Admin" : "Underwriter";
  return `
  <div class="shell">
    <aside class="sidebar">
      <p class="brand-mark">Lendistry</p>
      <p class="brand-sub">Underwriting intelligence</p>
      ${nav}
      <div class="sidebar-foot">
        <p class="muted" style="font-size:0.82rem;margin:0 0 0.6rem">Signed in as <b>${state.role}</b></p>
        ${
          showRoleSwitch
            ? `<button class="primary-btn" id="switch-role" style="width:100%;margin-bottom:0.45rem">Switch to ${otherRole}</button>`
            : ""
        }
        <button class="ghost-btn" id="logout" style="width:100%">Sign out</button>
      </div>
    </aside>
    <main class="main">
      ${themeToggleHtml()}
      ${disclaimer()}${content}
    </main>
  </div>`;
}

function loginView() {
  return `
  ${themeToggleHtml()}
  <div class="login-wrap">
    <div class="login-card">
      ${disclaimer()}
      <div class="hero" style="margin:0">
        <h1>Lendistry</h1>
        <p>Default-risk underwriting workspace for business users, with an admin model lab underneath.</p>
        <div class="pills">
          <span class="pill">Synthetic demo data</span>
          <span class="pill">Charged-Off proxy</span>
          <span class="pill">Leakage-safe features</span>
        </div>
      </div>
      <div class="login-grid">
        <div>
          <h3 style="font-family:var(--display);margin:0.2rem 0 0.4rem">Choose a role</h3>
          <p class="muted">No password — presentation login for client demos.</p>
        </div>
        <div class="role-card" data-role="Underwriter">
          <h3>Underwriter</h3>
          <p>Application queue, risk bands, weekly business insights.</p>
          <button class="primary-btn">Enter workspace</button>
        </div>
        <div class="role-card" data-role="Admin">
          <h3>Admin</h3>
          <p>Model metrics, drivers, and sandbox scoring lab.</p>
          <button class="ghost-btn">Enter lab</button>
        </div>
      </div>
    </div>
  </div>`;
}

function pulseChart(pulse) {
  if (!pulse) return "";
  const weeks = ["This week", "Last week"];
  const bands = [
    ["Risky", "high"],
    ["Moderately risky", "mid"],
    ["Lower risk", "low"],
  ];
  const maxBand = Math.max(
    ...weeks.flatMap((w) => bands.map(([b]) => pulse[w]?.[b] || 0)),
    1
  );

  const compareRows = bands
    .map(([band, cls]) => {
      const a = pulse["This week"]?.[band] || 0;
      const b = pulse["Last week"]?.[band] || 0;
      const delta = a - b;
      const deltaText =
        delta === 0 ? "flat" : delta > 0 ? `+${delta} vs last week` : `${delta} vs last week`;
      return `
      <div class="pulse-compare-row">
        <div class="pulse-compare-label">
          <span class="dot ${cls}"></span>
          <span>${band}</span>
          <em>${deltaText}</em>
        </div>
        <div class="pulse-compare-bars">
          <div class="pulse-hbar">
            <span class="pulse-hbar-tag">This week</span>
            <div class="pulse-hbar-track">
              <div class="pulse-hbar-fill ${cls}" style="width:${(a / maxBand) * 100}%"></div>
            </div>
            <strong>${a}</strong>
          </div>
          <div class="pulse-hbar">
            <span class="pulse-hbar-tag">Last week</span>
            <div class="pulse-hbar-track">
              <div class="pulse-hbar-fill ${cls} dim" style="width:${(b / maxBand) * 100}%"></div>
            </div>
            <strong>${b}</strong>
          </div>
        </div>
      </div>`;
    })
    .join("");

  const mixCards = weeks
    .map((w) => {
      const total = Math.max(pulse[w]?.total || 0, 1);
      const counts = bands.map(([band, cls]) => ({
        band,
        cls,
        n: pulse[w]?.[band] || 0,
      }));
      const segs = counts
        .filter((c) => c.n > 0)
        .map(
          (c) =>
            `<div class="mix-seg ${c.cls}" style="width:${(c.n / total) * 100}%" title="${c.band}: ${c.n}"><span>${c.n}</span></div>`
        )
        .join("");
      return `
      <div class="mix-card pulse-mix">
        <div class="mix-head">
          <h3>${w}</h3>
          <strong>${pulse[w]?.total || 0} applications</strong>
        </div>
        <div class="mix-bar">${segs || `<div class="mix-seg empty">0</div>`}</div>
      </div>`;
    })
    .join("");

  return `
  <div class="panel">
    <h2>Portfolio pulse</h2>
    <p class="muted">This week vs last week — risk mix and band-by-band comparison.</p>
    <div class="pulse-mix-grid">${mixCards}</div>
    <div class="pulse-compare">${compareRows}</div>
    <div class="pulse-legend">
      <span><i class="swatch high"></i> Risky</span>
      <span><i class="swatch mid"></i> Moderately risky</span>
      <span><i class="swatch low"></i> Lower risk</span>
    </div>
  </div>`;
}

async function underwriterHome() {
  const s = await api("/api/summary");
  state.summary = s;
  return `
  <div class="hero">
    <h1>Underwriting workspace</h1>
    <p>Review loan applications by default risk — built for underwriters, not data scientists.</p>
    <div class="pills">
      <span class="pill">Application queue</span>
      <span class="pill">Business insights</span>
      <span class="pill">Model runs underneath</span>
    </div>
  </div>
  <div class="grid-kpis">
    <div class="kpi"><div class="label">Applications (2 weeks)</div><div class="value">${s.total}</div></div>
    <div class="kpi"><div class="label">Risky</div><div class="value">${s.risky}</div></div>
    <div class="kpi"><div class="label">Moderately risky</div><div class="value">${s.moderate}</div></div>
    <div class="kpi"><div class="label">Pending decisions</div><div class="value">${s.pending}</div></div>
  </div>
  ${pulseChart(s.pulse)}
  <div class="panel">
    <h2>Your next step</h2>
    <p class="muted">Open the <b>Application dashboard</b> to work the queue, or <b>Business insights</b> for weekly risk mix and outcomes.</p>
  </div>`;
}

function appSummaryText(app) {
  return [
    `Lendistry underwriting summary (DEMO)`,
    `Application: ${app.application_id}`,
    `Business: ${app.business_name}`,
    `Date: ${app.application_date}`,
    `Requested: ${fmtMoney(app.requested_amount)}`,
    `Assigned to: ${app.assigned_to || "—"}`,
    `Default risk score: ${fmtPct(app.pd_probability)}`,
    `Risk band: ${app.risk_band}`,
    `Recommendation: ${app.recommendation}`,
    `Decision: ${app.decision_status || "Pending"}`,
    `Plain English: ${app.plain_english || ""}`,
    `Why flagged: ${app.why_flagged}`,
    `Credit ${app.credit_score} · Rating ${app.risk_rating} · Rate ${Number(app.interest_rate).toFixed(1)}%`,
    `Entity/State: ${app.entity} / ${app.jurisdiction}`,
    ``,
    `Synthetic demo data. Charged-Off proxy for default. Not production risk.`,
  ].join("\n");
}

function closeAppModal() {
  document.getElementById("app-modal")?.remove();
  state.selectedId = null;
}

function toast(msg) {
  document.getElementById("toast")?.remove();
  const t = document.createElement("div");
  t.id = "toast";
  t.className = "toast";
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2200);
}

async function saveDecision(applicationId, decision) {
  await api(`/api/applications/${applicationId}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, note: "Demo decision" }),
  });
  const app = state.apps.find((a) => a.application_id === applicationId);
  if (app) app.decision_status = decision;
  toast(`Marked ${applicationId} as ${decision}`);
  openAppModal(state.apps.find((a) => a.application_id === applicationId) || app, {
    skipAgents: true,
  });
  document.querySelectorAll(`tr[data-id="${applicationId}"] .dec-cell`).forEach((el) => {
    el.innerHTML = decisionBadge(decision);
  });
}

function agentStepsFor(app) {
  const creditOk = Number(app.credit_score) >= 620;
  const ratingOk = Number(app.risk_rating) <= 5;
  const rateOk = Number(app.interest_rate) < 12;
  return [
    {
      id: "agent1",
      name: "Agent 1 · Intake",
      checking: "Checking application completeness and borrower profile…",
      done: `Profile verified · ${app.entity} · ${app.jurisdiction} · ${fmtMoney(app.requested_amount)}`,
      tone: "ok",
    },
    {
      id: "agent2",
      name: "Agent 2 · Credit",
      checking: "Checking credit score, internal risk rating, and pricing…",
      done: creditOk && ratingOk
        ? `Credit review clear · score ${app.credit_score}, rating ${app.risk_rating}`
        : `Credit flags · score ${app.credit_score}, rating ${app.risk_rating}${rateOk ? "" : `, rate ${Number(app.interest_rate).toFixed(1)}%`}`,
      tone: creditOk && ratingOk ? "ok" : "warn",
    },
    {
      id: "agent3",
      name: "Agent 3 · Default risk",
      checking: "Running default-risk model on leakage-safe features…",
      done: `Model complete · ${app.risk_band} · ${fmtPct(app.pd_probability)} default risk`,
      tone: app.risk_band === "Risky" ? "bad" : app.risk_band === "Moderately risky" ? "warn" : "ok",
    },
  ];
}

function bindModalChrome(el) {
  el.addEventListener("click", (e) => {
    if (e.target === el) closeAppModal();
  });
  document.getElementById("modal-close")?.addEventListener("click", closeAppModal);
}

function bindOutcomeActions(app) {
  const root = document.getElementById("outcome-slot") || document.getElementById("app-modal");
  if (!root) return;
  root.querySelectorAll("[data-decision]").forEach((btn) =>
    btn.addEventListener("click", () =>
      saveDecision(app.application_id, btn.dataset.decision).catch((err) => alert(err.message))
    )
  );
  document.getElementById("copy-summary")?.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(appSummaryText(app));
      toast("Summary copied");
    } catch {
      toast("Copy failed - use Download instead");
    }
  });
  document.getElementById("replay-agents")?.addEventListener("click", () =>
    openAppModal(app, { skipAgents: false })
  );
}

function outcomeHtml(app) {
  const cls = calloutClass(app.risk_band);
  return `
      <div class="outcome-reveal" id="outcome-block">
        <div class="modal-pd callout ${cls}">
          <p class="outcome-label">Final outcome</p>
          <div class="modal-pd-row">
            <span>Default risk score</span>
            <strong>${fmtPct(app.pd_probability)}</strong>
          </div>
          <p class="plain-risk">${app.plain_english || ""}</p>
          <div class="modal-pd-row">
            <span>Risk band</span>
            ${badge(app.risk_band)}
          </div>
          <div class="modal-pd-row">
            <span>Recommended path</span>
            <strong class="rec-text">${app.recommendation}</strong>
          </div>
          <div class="modal-pd-row">
            <span>Decision status</span>
            ${decisionBadge(app.decision_status || "Pending")}
          </div>
        </div>
        <div class="modal-why">
          <h3>Why this was flagged</h3>
          <p>${app.why_flagged}</p>
        </div>
        <div class="modal-meta">
          <div><span>Requested</span><b>${fmtMoney(app.requested_amount)}</b></div>
          <div><span>Application date</span><b>${app.application_date}</b></div>
          <div><span>Credit score</span><b>${app.credit_score}</b></div>
          <div><span>Risk rating</span><b>${app.risk_rating}</b></div>
          <div><span>Interest rate</span><b>${Number(app.interest_rate).toFixed(1)}%</b></div>
          <div><span>Entity / state</span><b>${app.entity} · ${app.jurisdiction}</b></div>
        </div>
        <div class="modal-actions">
          <button type="button" class="decision-btn approve" data-decision="Approve">Approve</button>
          <button type="button" class="decision-btn refer" data-decision="Refer">Refer</button>
          <button type="button" class="decision-btn decline" data-decision="Decline">Decline</button>
        </div>
        <div class="modal-share">
          <button type="button" class="ghost-btn" id="copy-summary">Copy summary</button>
          <a class="ghost-btn" id="download-summary" href="/api/applications/${app.application_id}/summary.txt" download="${app.application_id}-summary.txt">Download .txt</a>
          <button type="button" class="ghost-btn" id="replay-agents">Replay agents</button>
        </div>
      </div>`;
}

function openAppModal(app, { skipAgents = false } = {}) {
  if (!app) return;
  document.getElementById("app-modal")?.remove();
  state.selectedId = app.application_id;
  const steps = agentStepsFor(app);
  const agentRows = steps
    .map(
      (s, i) => `
      <div class="agent-row" id="${s.id}" data-tone="${s.tone}">
        <div class="agent-status" aria-hidden="true"><span class="agent-dot"></span></div>
        <div class="agent-body">
          <div class="agent-name">${s.name}</div>
          <div class="agent-msg" data-checking="${s.checking}" data-done="${s.done}">Waiting…</div>
        </div>
      </div>`
    )
    .join("");

  const el = document.createElement("div");
  el.id = "app-modal";
  el.className = "modal-backdrop";
  el.innerHTML = `
    <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div class="modal-head">
        <div>
          <p class="modal-eyebrow">${app.application_id} · ${app.assigned_to || "Unassigned"}</p>
          <h2 id="modal-title">${app.business_name}</h2>
        </div>
        <button type="button" class="ghost-btn modal-close" id="modal-close" aria-label="Close">Close</button>
      </div>
      <div class="agent-pipeline" id="agent-pipeline">
        <p class="agent-pipeline-title">Multi-agent review</p>
        ${agentRows}
      </div>
      <div id="outcome-slot">${skipAgents ? outcomeHtml(app) : ""}</div>
    </div>`;
  document.body.appendChild(el);
  bindModalChrome(el);

  if (skipAgents) {
    steps.forEach((s) => {
      const row = document.getElementById(s.id);
      if (!row) return;
      row.classList.add("done", s.tone);
      row.querySelector(".agent-msg").textContent = s.done;
    });
    bindOutcomeActions(app);
    return;
  }

  runAgentPipeline(steps, app);
}

function runAgentPipeline(steps, app) {
  let i = 0;
  const tick = () => {
    if (!document.getElementById("app-modal")) return;
    if (i > 0) {
      const prev = steps[i - 1];
      const prevRow = document.getElementById(prev.id);
      if (prevRow) {
        prevRow.classList.remove("checking");
        prevRow.classList.add("done", prev.tone);
        prevRow.querySelector(".agent-msg").textContent = prev.done;
      }
    }
    if (i >= steps.length) {
      const slot = document.getElementById("outcome-slot");
      if (slot) {
        slot.innerHTML = outcomeHtml(app);
        slot.querySelector(".outcome-reveal")?.classList.add("show");
        bindOutcomeActions(app);
      }
      return;
    }
    const step = steps[i];
    const row = document.getElementById(step.id);
    if (row) {
      row.classList.add("checking");
      row.querySelector(".agent-msg").textContent = step.checking;
      row.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
    i += 1;
    setTimeout(tick, i === steps.length ? 900 : 1100);
  };
  setTimeout(tick, 350);
}

async function applicationsView() {
  const f = state.filters;
  const week = document.getElementById("f-week")?.value || f.week;
  const risk = document.getElementById("f-risk")?.value || f.risk;
  const sort = document.getElementById("f-sort")?.value || f.sort;
  const q = document.getElementById("f-q")?.value ?? f.q;
  const assigned = document.getElementById("f-assigned")?.value || f.assigned;
  const decision = document.getElementById("f-decision")?.value || f.decision;
  state.filters = { week, risk, sort, q, assigned, decision };

  const qs = new URLSearchParams({
    week,
    risk_band: risk,
    sort_by: sort,
    q,
    assigned,
    decision,
  });
  state.apps = await api(`/api/applications?${qs}`);
  const summary = state.summary || (await api("/api/summary"));
  state.summary = summary;
  const uwOptions = ["All", ...(summary.underwriters || [])];

  const rows = state.apps
    .map(
      (a) => `
    <tr data-id="${a.application_id}" class="clickable-row" title="Open application details">
      <td><button type="button" class="app-link" data-id="${a.application_id}">${a.application_id}</button></td>
      <td>${a.business_name}</td>
      <td>${a.assigned_to || "—"}</td>
      <td>${fmtMoney(a.requested_amount)}</td>
      <td>${fmtPct(a.pd_probability)}</td>
      <td>${badge(a.risk_band)}</td>
      <td class="dec-cell">${decisionBadge(a.decision_status)}</td>
    </tr>`
    )
    .join("");

  return `
  <div class="panel">
    <h2>Application dashboard</h2>
    <p class="muted">Click an application to see default risk score, why it was flagged, and record Approve / Refer / Decline.</p>
    <div class="filters filters-wide">
      <label class="field">Search
        <input id="f-q" type="search" placeholder="Business or APP-…" value="${q.replace(/"/g, "&quot;")}" />
      </label>
      <label class="field">Period
        <select id="f-week">
          ${["All", "This week", "Last week"].map((x) => `<option ${x === week ? "selected" : ""}>${x}</option>`).join("")}
        </select>
      </label>
      <label class="field">Risk band
        <select id="f-risk">
          ${["All", "Risky", "Moderately risky", "Lower risk"].map((x) => `<option ${x === risk ? "selected" : ""}>${x}</option>`).join("")}
        </select>
      </label>
      <label class="field">Queue
        <select id="f-assigned">
          ${uwOptions.map((x) => `<option ${x === assigned ? "selected" : ""}>${x}</option>`).join("")}
        </select>
      </label>
      <label class="field">Decision
        <select id="f-decision">
          ${["All", "Pending", "Approve", "Refer", "Decline"].map((x) => `<option ${x === decision ? "selected" : ""}>${x}</option>`).join("")}
        </select>
      </label>
      <label class="field">Sort by
        <select id="f-sort">
          <option value="pd_probability" ${sort === "pd_probability" ? "selected" : ""}>Default risk</option>
          <option value="application_date" ${sort === "application_date" ? "selected" : ""}>Date</option>
          <option value="requested_amount" ${sort === "requested_amount" ? "selected" : ""}>Amount</option>
        </select>
      </label>
    </div>
    <div class="table-wrap"><table>
      <thead><tr>
        <th>Application</th><th>Business</th><th>Assigned</th><th>Requested</th><th>Risk score</th><th>Band</th><th>Decision</th>
      </tr></thead>
      <tbody>${rows || `<tr><td colspan="7">No applications match</td></tr>`}</tbody>
    </table></div>
  </div>`;
}

function weekBucket(weekly, week) {
  const rows = weekly.filter((w) => w.week === week);
  const get = (band) => rows.find((r) => r.risk_band === band)?.applications || 0;
  const total = rows.reduce((s, r) => s + (r.applications || 0), 0) || 1;
  return {
    week,
    total: rows.reduce((s, r) => s + (r.applications || 0), 0),
    Risky: get("Risky"),
    "Moderately risky": get("Moderately risky"),
    "Lower risk": get("Lower risk"),
    riskyPct: get("Risky") / total,
  };
}

function compositionBar(bucket) {
  const total = Math.max(bucket.total, 1);
  const parts = [
    ["Risky", "high", bucket.Risky],
    ["Moderately risky", "mid", bucket["Moderately risky"]],
    ["Lower risk", "low", bucket["Lower risk"]],
  ];
  const segs = parts
    .filter(([, , n]) => n > 0)
    .map(
      ([label, cls, n]) =>
        `<div class="mix-seg ${cls}" style="width:${(n / total) * 100}%" title="${label}: ${n}">
          <span>${n}</span>
        </div>`
    )
    .join("");
  return `
    <div class="mix-card">
      <div class="mix-head">
        <h3>${bucket.week}</h3>
        <strong>${bucket.total} applications</strong>
      </div>
      <div class="mix-bar">${segs || `<div class="mix-seg empty">0</div>`}</div>
      <div class="mix-stats">
        <div><span class="dot high"></span>Risky <b>${bucket.Risky}</b> <em>${fmtPct(bucket.Risky / total)}</em></div>
        <div><span class="dot mid"></span>Moderate <b>${bucket["Moderately risky"]}</b> <em>${fmtPct(bucket["Moderately risky"] / total)}</em></div>
        <div><span class="dot low"></span>Lower <b>${bucket["Lower risk"]}</b> <em>${fmtPct(bucket["Lower risk"] / total)}</em></div>
      </div>
    </div>`;
}

async function insightsView() {
  const [weekly, outcomes, drivers, summary] = await Promise.all([
    api("/api/insights/weekly"),
    api("/api/insights/outcomes"),
    api("/api/insights/drivers"),
    api("/api/summary"),
  ]);
  state.summary = summary;

  const thisWeek = weekBucket(weekly, "This week");
  const lastWeek = weekBucket(weekly, "Last week");
  const riskyDelta = thisWeek.Risky - lastWeek.Risky;
  const deltaLabel =
    riskyDelta === 0
      ? "Risky volume flat vs last week"
      : riskyDelta > 0
        ? `${riskyDelta} more risky applications than last week`
        : `${Math.abs(riskyDelta)} fewer risky applications than last week`;

  const orderedOutcomes = ["Risky", "Moderately risky", "Lower risk"]
    .map((band) => outcomes.find((o) => o.risk_band === band))
    .filter(Boolean);

  const riskyOutcome = orderedOutcomes.find((o) => o.risk_band === "Risky");
  const takeaway = riskyOutcome
    ? `In this demo, ${fmtPct(riskyOutcome.default_rate)} of applications flagged Risky later defaulted — vs ${fmtPct(orderedOutcomes.find((o) => o.risk_band === "Lower risk")?.default_rate || 0)} for Lower risk.`
    : "Outcome alignment is shown below for the demo portfolio.";

  const outcomeCards = orderedOutcomes
    .map((o) => {
      const cls = calloutClass(o.risk_band);
      const rate = Number(o.default_rate) || 0;
      return `
      <div class="outcome-card ${cls}">
        <div class="outcome-card-top">
          ${badge(o.risk_band)}
          <strong class="outcome-rate">${fmtPct(rate)}</strong>
        </div>
        <p class="outcome-rate-label">later defaulted (demo)</p>
        <div class="outcome-meter" aria-hidden="true">
          <div class="outcome-meter-fill" style="width:${Math.min(rate * 100, 100)}%"></div>
        </div>
        <div class="outcome-card-meta">
          <span><b>${o.applications}</b> apps</span>
          <span><b>${o.defaulted}</b> defaults</span>
        </div>
      </div>`;
    })
    .join("");

  const driverCards = drivers
    .map(
      (d, i) => `
    <div class="driver-card ranked" style="animation-delay:${i * 40}ms">
      <div class="driver-rank">${String(i + 1).padStart(2, "0")}</div>
      <div>
        <h4>${d.label || d.driver}</h4>
        <p>${d.tip}</p>
      </div>
    </div>`
    )
    .join("");

  return `
  <div class="hero insights-hero">
    <h1>Business insights</h1>
    <p>Portfolio risk mix and whether flags lined up with defaults — built for underwriting managers.</p>
  </div>

  <div class="insight-takeaway">
    <div>
      <p class="eyebrow">Key takeaway</p>
      <p>${takeaway}</p>
    </div>
    <div class="insight-takeaway-side">
      <span class="muted">Queue signal</span>
      <strong>${deltaLabel}</strong>
    </div>
  </div>

  <div class="insight-grid-2">
    <div class="panel insight-panel">
      <div class="panel-head">
        <h2>Risk mix by week</h2>
        <p class="muted">Share of Risky / Moderate / Lower in the underwriting queue.</p>
      </div>
      <div class="mix-grid">
        ${compositionBar(thisWeek)}
        ${compositionBar(lastWeek)}
      </div>
    </div>

    <div class="panel insight-panel">
      <div class="panel-head">
        <h2>Portfolio snapshot</h2>
        <p class="muted">Last 14 days of scored applications.</p>
      </div>
      <div class="snapshot-grid">
        <div class="snapshot-kpi"><span>Total apps</span><b>${summary.total}</b></div>
        <div class="snapshot-kpi bad"><span>Risky</span><b>${summary.risky}</b></div>
        <div class="snapshot-kpi mid"><span>Moderate</span><b>${summary.moderate}</b></div>
        <div class="snapshot-kpi good"><span>Lower risk</span><b>${summary.lower}</b></div>
        <div class="snapshot-kpi"><span>Pending decisions</span><b>${summary.pending}</b></div>
        <div class="snapshot-kpi"><span>Avg default risk</span><b>${fmtPct(summary.avg_pd)}</b></div>
      </div>
    </div>
  </div>

  <div class="panel insight-panel">
    <div class="panel-head">
      <h2>Did risk flags become defaults?</h2>
      <p class="muted">Manager view only — individual application popups never show later outcomes.</p>
    </div>
    <div class="outcome-grid">${outcomeCards}</div>
  </div>

  <div class="panel insight-panel">
    <div class="panel-head">
      <h2>What usually drives risk flags</h2>
      <p class="muted">Business language for underwriters. Model importance % stays in Admin.</p>
    </div>
    <div class="driver-grid">${driverCards}</div>
  </div>`;
}

async function adminHome() {
  const m = await api("/api/admin/metrics");
  return `
  <div class="hero">
    <h1>Admin · model lab</h1>
    <p>Technical view for calibration and model health. Underwriters use the business workspace instead.</p>
  </div>
  <div class="grid-kpis">
    <div class="kpi"><div class="label">Best model</div><div class="value" style="font-size:1.3rem">${m.best_model}</div></div>
    <div class="kpi"><div class="label">Accuracy</div><div class="value">${fmtPct(m.accuracy)}</div></div>
    <div class="kpi"><div class="label">ROC AUC</div><div class="value">${Number(m.roc_auc).toFixed(3)}</div></div>
    <div class="kpi"><div class="label">Recall</div><div class="value">${fmtPct(m.recall)}</div></div>
  </div>`;
}

async function adminPerformance() {
  const m = await api("/api/admin/metrics");
  const cmp = (m.model_comparison || [])
    .sort((a, b) => b.roc_auc - a.roc_auc)
    .map(
      (r) => `<tr>
        <td>${r.model}${r.model === m.best_model ? " · BEST" : ""}</td>
        <td>${fmtPct(r.accuracy)}</td>
        <td>${fmtPct(r.precision)}</td>
        <td>${fmtPct(r.recall)}</td>
        <td>${Number(r.roc_auc).toFixed(3)}</td>
      </tr>`
    )
    .join("");
  return `
  <div class="panel">
    <h2>Model performance</h2>
    <div class="table-wrap"><table>
      <thead><tr><th>Model</th><th>Accuracy</th><th>Precision</th><th>Recall</th><th>ROC AUC</th></tr></thead>
      <tbody>${cmp}</tbody>
    </table></div>
    <p class="muted" style="margin-top:0.8rem">Train/test 75/25 · selected by ROC AUC · leakage checks passed</p>
  </div>`;
}

async function adminDrivers() {
  const feats = await api("/api/admin/features");
  const drivers = feats.model_drivers || [];
  const maxImp = Math.max(...drivers.map((d) => d.importance), 1e-9);
  const bars = drivers
    .map(
      (d) => `
    <div class="bar-row">
      <span>${d.label || d.driver}</span>
      <div class="bar-track"><div class="bar-fill" style="width:${(d.importance / maxImp) * 100}%"></div></div>
      <span>${(d.importance * 100).toFixed(1)}%</span>
    </div>`
    )
    .join("");
  return `<div class="panel"><h2>Feature importance (model)</h2><div class="bars">${bars}</div></div>`;
}

function adminScoreForm() {
  return `
  <div class="panel">
    <h2>Sandbox score</h2>
    <p class="muted">Quick what-if scoring. Threshold stays in Admin only.</p>
    <div class="toolbar">
      <button class="ghost-btn" id="preset-low">Load low-risk</button>
      <button class="ghost-btn" id="preset-high">Load high-risk</button>
      <button class="primary-btn" id="score-btn">Predict PD</button>
    </div>
    <form id="score-form" onsubmit="return false;">
      <div class="form-grid">
        <label class="field">Credit score<input type="number" name="creditscore" value="650" min="300" max="850" /></label>
        <label class="field">Annual revenue<input type="number" name="annualgrossrevenue" value="1500000" /></label>
        <label class="field">Note amount<input type="number" name="original_note_amount" value="250000" /></label>
        <label class="field">Interest rate %<input type="number" step="0.1" name="current_interest_rate" value="9.5" /></label>
        <label class="field">Risk rating<input type="number" name="risk_rating_no" value="4" min="1" max="9" /></label>
        <label class="field">Principal balance<input type="number" name="current_principal_balance" value="180000" /></label>
        <label class="field">Threshold (Admin)<input type="number" step="0.05" name="threshold" value="0.5" min="0.1" max="0.9" /></label>
      </div>
      <details class="advanced-box">
        <summary>Advanced fields</summary>
        <div class="form-grid" style="margin-top:0.75rem">
          <label class="field">Loan age months<input type="number" name="loan_age_months" value="24" /></label>
          <label class="field">Business age years<input type="number" name="business_age_years" value="10" step="0.1" /></label>
          <label class="field">Times renewed<input type="number" name="times_renewed" value="1" /></label>
          <label class="field">Times extended<input type="number" name="times_extended" value="1" /></label>
          <label class="field">Jobs<input type="number" name="jobstimeofinvestment" value="12" /></label>
          <label class="field">Banked at intake
            <select name="bankedatintake"><option value="1">1</option><option value="0">0</option></select>
          </label>
          <label class="field">Entity
            <select name="entity"><option>LLC</option><option>Corp</option><option>Partnership</option><option>Sole Proprietor</option></select>
          </label>
          <label class="field">Jurisdiction
            <select name="contractualjurisdiction"><option>CA</option><option>TX</option><option>NY</option><option>FL</option><option>IL</option></select>
          </label>
        </div>
      </details>
    </form>
    <div id="score-result"></div>
  </div>`;
}

function fillPreset(kind) {
  const form = document.getElementById("score-form");
  if (!form) return;
  const low = {
    creditscore: 740,
    annualgrossrevenue: 2800000,
    original_note_amount: 180000,
    current_interest_rate: 6.5,
    risk_rating_no: 2,
    current_principal_balance: 120000,
    loan_age_months: 18,
    business_age_years: 14,
    times_renewed: 0,
    times_extended: 0,
    jobstimeofinvestment: 22,
    bankedatintake: "1",
    entity: "LLC",
    contractualjurisdiction: "CA",
  };
  const high = {
    creditscore: 545,
    annualgrossrevenue: 420000,
    original_note_amount: 320000,
    current_interest_rate: 16.5,
    risk_rating_no: 8,
    current_principal_balance: 290000,
    loan_age_months: 36,
    business_age_years: 4,
    times_renewed: 3,
    times_extended: 4,
    jobstimeofinvestment: 4,
    bankedatintake: "0",
    entity: "Sole Proprietor",
    contractualjurisdiction: "FL",
  };
  const data = kind === "low" ? low : high;
  Object.entries(data).forEach(([k, v]) => {
    const el = form.elements.namedItem(k);
    if (el) el.value = v;
  });
}

async function scoreSubmit() {
  const form = document.getElementById("score-form");
  const fd = new FormData(form);
  const body = Object.fromEntries(fd.entries());
  [
    "creditscore",
    "annualgrossrevenue",
    "original_note_amount",
    "current_interest_rate",
    "risk_rating_no",
    "current_principal_balance",
    "loan_age_months",
    "business_age_years",
    "times_renewed",
    "times_extended",
    "jobstimeofinvestment",
    "bankedatintake",
    "threshold",
  ].forEach((k) => (body[k] = Number(body[k])));
  body.loan_type = 3;
  body.portfolio_code_id = 2;
  body.loan_group_no = 4;
  body.entitystructure = 3;
  body.investeetype = 2;
  body.naicscode = 541511;

  const result = document.getElementById("score-result");
  result.innerHTML = `
    <div class="agent-pipeline sandbox-agents" id="sandbox-agents">
      <p class="agent-pipeline-title">Multi-agent review</p>
      <div class="agent-row" id="sb-a1"><div class="agent-status"><span class="agent-dot"></span></div><div class="agent-body"><div class="agent-name">Agent 1 · Intake</div><div class="agent-msg">Waiting…</div></div></div>
      <div class="agent-row" id="sb-a2"><div class="agent-status"><span class="agent-dot"></span></div><div class="agent-body"><div class="agent-name">Agent 2 · Credit</div><div class="agent-msg">Waiting…</div></div></div>
      <div class="agent-row" id="sb-a3"><div class="agent-status"><span class="agent-dot"></span></div><div class="agent-body"><div class="agent-name">Agent 3 · Default risk</div><div class="agent-msg">Waiting…</div></div></div>
    </div>
    <div id="sandbox-outcome"></div>`;

  const setRow = (id, phase, msg, tone) => {
    const row = document.getElementById(id);
    if (!row) return;
    row.className = `agent-row ${phase}${tone ? ` ${tone}` : ""}`;
    row.querySelector(".agent-msg").textContent = msg;
  };

  setRow("sb-a1", "checking", "Checking application completeness…");
  await new Promise((r) => setTimeout(r, 700));
  setRow("sb-a1", "done ok", `Profile inputs received · revenue ${fmtMoney(body.annualgrossrevenue)}`);
  setRow("sb-a2", "checking", "Checking credit score and risk rating…");
  await new Promise((r) => setTimeout(r, 800));
  const creditOk = body.creditscore >= 620 && body.risk_rating_no <= 5;
  setRow(
    "sb-a2",
    creditOk ? "done ok" : "done warn",
    creditOk
      ? `Credit review clear · score ${body.creditscore}`
      : `Credit flags · score ${body.creditscore}, rating ${body.risk_rating_no}`
  );
  setRow("sb-a3", "checking", "Running default-risk model…");

  const out = await api("/api/score", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await new Promise((r) => setTimeout(r, 600));
  const tone =
    out.risk_band === "Risky" ? "bad" : out.risk_band === "Moderately risky" ? "warn" : "ok";
  setRow("sb-a3", `done ${tone}`, `Model complete · ${out.risk_band} · ${fmtPct(out.pd_probability)}`);
  const cls = calloutClass(out.risk_band);
  document.getElementById("sandbox-outcome").innerHTML = `
    <div class="outcome-reveal show">
      <div class="callout ${cls}">
        <p class="outcome-label">Final outcome</p>
        <b>PD = ${fmtPct(out.pd_probability)}</b> · ${badge(out.risk_band)}<br/>
        ${out.plain_english_risk || out.plain_english}<br/>
        ${out.recommendation}<br/>
        <i>Why: ${out.why_flagged}</i>
      </div>
    </div>`;
}

async function pageContent() {
  if (!state.role) return loginView();
  if (state.role === "Underwriter") {
    const nav = [
      ["home", "Home"],
      ["applications", "Application dashboard"],
      ["insights", "Business insights"],
    ];
    let content = "";
    if (state.page === "home") content = await underwriterHome();
    else if (state.page === "applications") content = await applicationsView();
    else content = await insightsView();
    return shell(nav, content);
  }
  const nav = [
    ["admin-home", "Admin overview"],
    ["admin-perf", "Model performance"],
    ["admin-drivers", "Feature importance"],
    ["admin-score", "Sandbox score"],
  ];
  let content = "";
  if (state.page === "admin-home") content = await adminHome();
  else if (state.page === "admin-perf") content = await adminPerformance();
  else if (state.page === "admin-drivers") content = await adminDrivers();
  else content = adminScoreForm();
  return shell(nav, content);
}

function bind() {
  bindThemeToggle();
  document.querySelectorAll("[data-role]").forEach((card) =>
    card.addEventListener("click", () => setRole(card.dataset.role))
  );
  document.querySelectorAll("[data-nav]").forEach((btn) =>
    btn.addEventListener("click", () => {
      state.page = btn.dataset.nav;
      render();
    })
  );
  document.getElementById("logout")?.addEventListener("click", logout);
  document.getElementById("switch-role")?.addEventListener("click", () => {
    setRole(state.role === "Underwriter" ? "Admin" : "Underwriter");
  });

  ["f-week", "f-risk", "f-sort", "f-assigned", "f-decision"].forEach((id) => {
    document.getElementById(id)?.addEventListener("change", () => render());
  });
  let searchTimer;
  document.getElementById("f-q")?.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => render(), 280);
  });

  const openById = (id) => {
    const app = state.apps.find((a) => a.application_id === id);
    openAppModal(app);
  };
  document.querySelectorAll("tbody tr[data-id]").forEach((tr) =>
    tr.addEventListener("click", () => openById(tr.dataset.id))
  );
  document.querySelectorAll(".app-link").forEach((btn) =>
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      openById(btn.dataset.id);
    })
  );

  document.getElementById("preset-low")?.addEventListener("click", () => fillPreset("low"));
  document.getElementById("preset-high")?.addEventListener("click", () => fillPreset("high"));
  document.getElementById("score-btn")?.addEventListener("click", () => scoreSubmit().catch(alert));
}

async function render() {
  closeAppModal();
  document.body.dataset.theme = state.theme;
  try {
    $app.innerHTML = await pageContent();
    bind();
  } catch (err) {
    $app.innerHTML = `<div class="login-wrap"><div class="panel"><h2>Error</h2><p>${err.message}</p></div></div>`;
  }
}

setTheme(state.theme);
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeAppModal();
});
render();
