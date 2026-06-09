/* Invoice Copilot — top bar, queue, composer, drawers. Exports to window. */
const { money: fmt } = window.IC;

/* ============================== TOP BAR ============================== */
function TopBar({ t, setTweak, role, onRole, onPlay, playing, beatLabel, onResetDemo }) {
  const min = 2000, max = 25000;
  const fill = ((t.tAmount - min) / (max - min)) * 100;
  return (
    <header className="topbar">
      <div className="brand">
        <div className="brand-mark"><window.Icon.spark2 style={{ width: 17, height: 17 }} /></div>
        <div className="brand-name">Invoice <b>Copilot</b></div>
      </div>

      <div className="env-pill" title="Model adapter — runs key-free in mock mode">
        <span className="dot" /> <span className="mono">{t.provider}</span> &middot; mock-safe
      </div>

      <div className="topbar-spacer" />

      <div className="autonomy" title="Auto-clear cap (T_amount). Invoices above this always escalate.">
        <window.Icon.dollar style={{ width: 14, height: 14, color: "var(--ink-3)" }} />
        <label>auto-clear &le;</label>
        <input type="range" min={min} max={max} step={500} value={t.tAmount}
          style={{ "--fill": fill + "%" }}
          onChange={(e) => setTweak("tAmount", Number(e.target.value))} />
        <span className="val">{fmt(t.tAmount)}</span>
      </div>

      <div className="roleswitch" role="tablist">
        <button className={"role-btn " + (role === "maya" ? "active" : "")} onClick={() => onRole("maya")}>
          <span className="ava" style={{ background: "#0E7490" }}>M</span> Maya
        </button>
        <button className={"role-btn " + (role === "priya" ? "active" : "")} onClick={() => onRole("priya")}>
          <span className="ava" style={{ background: "#7E22CE" }}>P</span> Priya
        </button>
      </div>

      <button className="icon-btn" title="Toggle theme" onClick={() => setTweak("dark", !t.dark)}>
        {t.dark ? <window.Icon.sun style={{ width: 17, height: 17 }} /> : <window.Icon.moon style={{ width: 17, height: 17 }} />}
      </button>

      <button className={"play-btn " + (playing ? "ghost" : "")} onClick={onPlay}>
        {playing ? <window.Icon.pause style={{ width: 13, height: 13 }} /> : <window.Icon.play style={{ width: 13, height: 13 }} />}
        {playing ? "Demo running" : "Play demo"}
      </button>
    </header>
  );
}

/* ============================== QUEUE ============================== */
const GROUP_ORDER = ["needs", "routed", "reading", "ruled", "queued", "held", "blocked", "received"];
const GROUP_LABEL = {
  needs: "Needs you", routed: "With Priya for sign-off", reading: "Reading", ruled: "Auto-handled by your rules",
  queued: "Queued for payment run", held: "Held", blocked: "Blocked", received: "Today\u2019s batch",
};

function Queue({ invoices, selected, onSelect, savedMin }) {
  const counts = invoices.reduce((a, i) => { a[i.status] = (a[i.status] || 0) + 1; return a; }, {});
  const groups = GROUP_ORDER.filter((g) => invoices.some((i) => i.status === g));
  const processed = invoices.some((i) => ["queued", "needs", "blocked", "ruled", "reading"].includes(i.status));

  return (
    <aside className="queue">
      <div className="queue-head">
        <div className="queue-title">
          <h2>Invoice queue</h2>
          <span className="count">{invoices.length} today</span>
        </div>
        <div className="stat-row">
          {processed ? (
            <React.Fragment>
              <span className="stat"><span className="sdot" style={{ background: "var(--ok)" }} /><b>{(counts.queued || 0) + (counts.ruled || 0)}</b> queued</span>
              <span className="stat"><span className="sdot" style={{ background: "var(--warn)" }} /><b>{counts.needs || 0}</b> need you</span>
              <span className="stat"><span className="sdot" style={{ background: "var(--bad)" }} /><b>{counts.blocked || 0}</b> blocked</span>
              {savedMin > 0 && <span className="stat saved"><window.Icon.clock style={{ width: 12, height: 12 }} /> ~<b>{savedMin}</b> min saved</span>}
            </React.Fragment>
          ) : (
            <span className="stat"><span className="sdot" style={{ background: "var(--ink-faint)" }} /><b>{invoices.length}</b> waiting to process</span>
          )}
        </div>
      </div>

      <div className="queue-list scroll">
        {groups.map((g) => (
          <div key={g}>
            <div className="queue-group-label">{GROUP_LABEL[g]} &middot; {counts[g]}</div>
            {invoices.filter((i) => i.status === g).map((inv) => (
              <QueueRow key={inv.id} inv={inv} selected={selected === inv.id} onSelect={onSelect} />
            ))}
          </div>
        ))}
      </div>
    </aside>
  );
}

function QueueRow({ inv, selected, onSelect }) {
  return (
    <div className={"qrow " + (inv.status === "reading" ? "reading " : "") + (selected ? "sel" : "")} onClick={() => onSelect(inv.id)}>
      <VLogo vendor={inv.vendor} />
      <div className="vmeta">
        <div className="vname">{inv.vendor}</div>
        <div className="vsub">{inv.id} &middot; {inv.po}</div>
      </div>
      <div className="vright">
        <span className="vamt">{fmt(inv.amount)}</span>
        {inv.status === "ruled"
          ? <span className="ruled-badge"><window.Icon.route /> rule R-7</span>
          : <Chip status={inv.status} />}
      </div>
    </div>
  );
}

/* ============================== COMPOSER ============================== */
function Composer({ onSend, suggestions, busy }) {
  const [val, setVal] = React.useState("");
  const ref = React.useRef(null);
  const send = () => { const v = val.trim(); if (!v) return; onSend(v); setVal(""); if (ref.current) ref.current.style.height = "auto"; };
  return (
    <div className="composer">
      <div className="composer-inner">
        {suggestions && suggestions.length > 0 && (
          <div className="suggest-row">
            {suggestions.map((s) => <button key={s} className="suggest" onClick={() => onSend(s)}>{s}</button>)}
          </div>
        )}
        <div className="input-wrap">
          <textarea ref={ref} rows={1} placeholder="Ask Copilot, or type an instruction…" value={val}
            onChange={(e) => { setVal(e.target.value); e.target.style.height = "auto"; e.target.style.height = e.target.scrollHeight + "px"; }}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
          <button className="send-btn" disabled={!val.trim() || busy} onClick={send}><window.Icon.send style={{ width: 16, height: 16 }} /></button>
        </div>
      </div>
    </div>
  );
}

/* ============================== AUDIT DRAWER ============================== */
const TL_ICON = { read: "eye", resolve: "link", flag: "alert", shield: "shield", ask: "user", execute: "check", learn: "spark", verdict: "gavel" };
const TL_GROUP = { extraction: "agent", enrichment: "agent", policy: "system", guard: "guard", execution: "execute", learning: "agent", human: "human" };

function AuditDrawer({ inv, events, onClose }) {
  const [open, setOpen] = React.useState({});
  return (
    <React.Fragment>
      <div className="scrim" onClick={onClose} />
      <div className="drawer">
        <div className="drawer-head">
          <div style={{ flex: 1 }}>
            <h3>Audit trail</h3>
            <div className="sub">{inv ? <span>{inv.vendor} &middot; <span className="mono">{inv.id}</span> &middot; {fmt(inv.amount)}</span> : "Full event stream"}</div>
          </div>
          <span className="chain-badge"><window.Icon.link /> chain verified</span>
          <button className="icon-btn" onClick={onClose}><window.Icon.x style={{ width: 17, height: 17 }} /></button>
        </div>
        <div className="drawer-body scroll">
          <div className="tl">
            {events.map((e, i) => {
              const grp = e.actorGroup || TL_GROUP[e.module] || "system";
              const Ico = window.Icon[TL_ICON[e.icon] || "file"];
              const isOpen = open[i];
              return (
                <div key={i} className={"tl-item " + grp} style={{ animationDelay: i * 55 + "ms" }}>
                  <span className="tl-node"><Ico /></span>
                  <div className="tl-row">
                    <span className={"tl-actor " + (grp === "execute" ? "agent" : grp)}>
                      {e.actor === "agent" ? "COPILOT" : e.actor === "system" ? "GUARD / POLICY" : e.actor.replace("user:", "").toUpperCase()}
                    </span>
                    <span className="tl-time mono">{e.time}</span>
                  </div>
                  <div className="tl-action">{e.action}</div>
                  <div className="tl-rationale">{e.rationale}</div>
                  {e.detail && (
                    <React.Fragment>
                      <button className="link-btn" style={{ marginTop: 7, fontSize: 11 }} onClick={() => setOpen((o) => ({ ...o, [i]: !o[i] }))}>
                        {isOpen ? <window.Icon.chevU /> : <window.Icon.chevD />} {isOpen ? "Hide" : "Inputs / outputs"}
                      </button>
                      {isOpen && (
                        <div className="tl-expand">
                          {Object.entries(e.detail).map(([k, v]) => (
                            <div key={k}><span className="k">{k}:</span> {Array.isArray(v) ? v.join(", ") : String(v)}</div>
                          ))}
                        </div>
                      )}
                    </React.Fragment>
                  )}
                  {e.meta && <div className="tl-hash"><span className="dot" />{e.meta.provider}/{e.meta.model} &middot; conf {e.meta.confidence}</div>}
                  {e.hash && <div className="tl-hash"><span className="dot" />{e.hash.slice(0, 18)}…</div>}
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </React.Fragment>
  );
}

/* ============================== RULES DRAWER ============================== */
function RulesDrawer({ rules, onToggle, onClose }) {
  return (
    <React.Fragment>
      <div className="scrim" onClick={onClose} />
      <div className="drawer">
        <div className="drawer-head">
          <div style={{ flex: 1 }}>
            <h3>Learned rules</h3>
            <div className="sub">Behaviour you taught Copilot &middot; editable &amp; reversible</div>
          </div>
          <button className="icon-btn" onClick={onClose}><window.Icon.x style={{ width: 17, height: 17 }} /></button>
        </div>
        <div className="drawer-body scroll">
          {rules.length === 0 && (
            <div style={{ textAlign: "center", padding: "48px 20px", color: "var(--ink-3)" }}>
              <div className="empty-mark" style={{ margin: "0 auto 14px" }}><window.Icon.book /></div>
              <div style={{ fontSize: 13 }}>No rules yet. Correct Copilot a few times and it&rsquo;ll propose one.</div>
            </div>
          )}
          {rules.map((r) => (
            <div key={r.id} className="rule-item">
              <div className="rule-item-head">
                <span className={"rule-status " + r.status}>{r.status}</span>
                <span className="rule-rid">{r.id}</span>
                <span className="rule-toggle">
                  <button className={"switch " + (r.status === "active" ? "on" : "")} onClick={() => onToggle(r.id)} />
                </span>
              </div>
              <div className="rule-text">
                <span className="rk">WHEN</span> vendor is <b>{r.vendor}</b> and amount over PO &lt; <b>{r.threshold}%</b><br />
                <span className="rk">THEN</span> route to <b>{r.route}</b> <span style={{ color: "var(--ink-faint)" }}>(instead of auto-hold)</span>
              </div>
              <div className="rule-meta">
                <window.Icon.spark style={{ width: 13, height: 13, color: "var(--accent-ink)" }} />
                Learned from <span className="mono">{r.sources.join(", ")}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </React.Fragment>
  );
}

Object.assign(window, { TopBar, Queue, Composer, AuditDrawer, RulesDrawer });
