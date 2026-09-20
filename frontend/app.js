let currentData = null;
let currentFilter = "all";

const qs = (s) => document.querySelector(s);
const qsa = (s) => [...document.querySelectorAll(s)];

function riskText(score) {
  if (score >= 70) return "Critical repository risk";
  if (score >= 40) return "High repository risk";
  if (score >= 18) return "Moderate repository risk";
  if (score > 0) return "Low repository risk";
  return "Repository looks clean";
}

function renderStats(stats) {
  const values = [
    ["Files", stats.files_scanned || 0],
    ["Findings", stats.findings || 0],
    ["Critical", stats.critical || 0],
    ["High", stats.high || 0],
    ["Medium", stats.medium || 0],
    ["Low", stats.low || 0],
  ];
  qs("#stats").innerHTML = values.map(([label,val]) =>
    `<div class="stat"><b>${val}</b><span>${label}</span></div>`
  ).join("");
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&","&amp;").replaceAll("<","&lt;")
    .replaceAll(">","&gt;").replaceAll('"',"&quot;");
}

function renderFindings() {
  if (!currentData) return;
  const list = currentData.findings.filter(f => currentFilter === "all" || f.severity === currentFilter);
  if (!list.length) {
    qs("#findings").innerHTML = `<div class="empty">No ${currentFilter === "all" ? "" : currentFilter + " "}findings.</div>`;
    return;
  }
  qs("#findings").innerHTML = list.map(f => `
    <div class="finding">
      <div class="sev ${f.severity}"></div>
      <div>
        <div class="finding-title">
          ${escapeHtml(f.title)}
          <span class="badge">${escapeHtml(f.type)}</span>
          <span class="badge">${escapeHtml(f.severity)}</span>
        </div>
        <p>${escapeHtml(f.message)}</p>
        <div class="meta">${escapeHtml(f.file)}:${f.line}</div>
      </div>
      <button class="explain-btn" data-id="${f.id}">Explain</button>
    </div>
  `).join("");

  qsa(".explain-btn").forEach(btn => btn.addEventListener("click", () => explain(btn.dataset.id)));
}

function renderEvents(events=[]) {
  qs("#events").innerHTML = events.slice(0,30).map(e => `
    <div class="event"><time>${escapeHtml(e.time)}</time><span>${escapeHtml(e.message)}</span></div>
  `).join("") || `<div class="empty">No events yet.</div>`;
}

function render(payload) {
  currentData = payload.data || payload;
  if (!currentData) return;
  qs("#watchPath").textContent = currentData.root;
  qs("#riskScore").textContent = currentData.risk_score;
  qs("#riskLabel").textContent = riskText(currentData.risk_score);
  if (payload.last_scan) qs("#lastScan").textContent = `Last scan: ${payload.last_scan}`;
  renderStats(currentData.stats);
  renderFindings();
  if (payload.events) renderEvents(payload.events);
}

async function loadStatus() {
  const r = await fetch("/api/status");
  const status = await r.json();
  render({data: status.data, last_scan: status.last_scan, events: status.events});
}

async function runScan() {
  const btn = qs("#scanBtn");
  btn.disabled = true;
  btn.textContent = "Scanning...";
  try {
    const r = await fetch("/api/scan", {method:"POST"});
    const data = await r.json();
    render(data);
  } finally {
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = "Run scan";
    }, 250);
  }
}

async function explain(id) {
  const f = currentData.findings.find(x => x.id === id);
  qs("#modal").classList.remove("hidden");
  qs("#modalTitle").textContent = f.title;
  qs("#modalMeta").textContent = `${f.severity.toUpperCase()} · ${f.file}:${f.line}`;
  qs("#modalText").textContent = "Analyzing finding...";
  try {
    const r = await fetch("/api/explain", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({finding_id:id})
    });
    const data = await r.json();
    qs("#modalText").textContent = data.text || "No explanation available.";
  } catch {
    qs("#modalText").textContent = "Could not generate explanation.";
  }
}

function connectWS() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onopen = () => {
    qs("#socketDot").classList.add("live");
    qs("#socketText").textContent = "Live";
    ws.send("hello");
  };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    render(msg);
  };
  ws.onclose = () => {
    qs("#socketDot").classList.remove("live");
    qs("#socketText").textContent = "Reconnecting...";
    setTimeout(connectWS, 1200);
  };
}

qsa(".filter").forEach(btn => btn.addEventListener("click", () => {
  qsa(".filter").forEach(x => x.classList.remove("active"));
  btn.classList.add("active");
  currentFilter = btn.dataset.filter;
  renderFindings();
}));

qs("#scanBtn").addEventListener("click", runScan);
qs("#closeModal").addEventListener("click", () => qs("#modal").classList.add("hidden"));
qs("#modal").addEventListener("click", e => {
  if (e.target.id === "modal") qs("#modal").classList.add("hidden");
});

loadStatus();
connectWS();
// TODO: Test DriftGuard real-time monitoring