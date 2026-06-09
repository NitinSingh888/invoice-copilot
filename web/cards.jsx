/* Invoice Copilot — inline thread cards + shared primitives. Exports to window. */
const { money } = window.IC;

/* ---------- primitives ---------- */
function VLogo({ vendor, size = 34, r = 9 }) {
  const v = window.IC.VENDORS[vendor] || { color: "#64748b", init: vendor[0] };
  return (
    <div className="vlogo" style={{ width: size, height: size, borderRadius: r, background: v.color, fontSize: size * 0.42 }}>
      {v.init}
    </div>
  );
}

const CHIP_META = {
  queued:  { cls: "queued",  label: "Queued",   icon: "check" },
  needs:   { cls: "needs",   label: "Needs you", icon: "alert" },
  held:    { cls: "held",    label: "Held",     icon: "hold" },
  blocked: { cls: "blocked", label: "Blocked",  icon: "shieldX" },
  reading: { cls: "reading", label: "Reading\u2026", icon: null },
  ruled:   { cls: "ruled",   label: "Auto-routed", icon: "route" },
  routed:  { cls: "ruled",   label: "With Priya",  icon: "route" },
  received:{ cls: "held",    label: "Ready",       icon: "file" },
};
function Chip({ status }) {
  const m = CHIP_META[status] || CHIP_META.held;
  const Ico = m.icon ? window.Icon[m.icon] : null;
  return (
    <span className={"chip " + m.cls}>
      {status === "reading" ? <span className="cdot" /> : Ico ? <Ico /> : null}
      {m.label}
    </span>
  );
}

const SEV_ICON = { ok: "check", info: "file", warn: "alert", stop: "shieldX" };
function Finding({ f }) {
  const Ico = window.Icon[SEV_ICON[f.sev] || "file"];
  return (
    <span className={"finding " + f.sev}>
      <Ico /> {f.text}
    </span>
  );
}

/* ---------- batch narration ---------- */
function BatchNarration({ steps }) {
  return (
    <div className="narr-steps">
      {steps.map((s, i) => (
        <div key={i} className={"narr-step " + (s.running ? "run" : "")}>
          <span className="tick">{s.running ? <window.Icon.search style={{ width: 11, height: 11 }} /> : <window.Icon.check style={{ width: 11, height: 11 }} />}</span>
          <span>{s.text}</span>
          {s.meta && <span className="mono">{s.meta}</span>}
        </div>
      ))}
    </div>
  );
}

/* ---------- approval / correction card ---------- */
function ApprovalCard({ inv, onResolve, onTrail }) {
  const [editing, setEditing] = React.useState(false);
  const [amt, setAmt] = React.useState(inv.amount);
  const [route, setRoute] = React.useState("Priya (manager)");
  const isAcme = inv.kind === "acme_over";
  const isInjection = inv.kind === "injection";

  const headTint = isInjection ? "stop" : "flag";
  const kicker = isInjection ? "Escalated \u00b7 instruction ignored" : isAcme ? "Needs your call" : "Approval needed";

  return (
    <div className={"card " + (isInjection ? "flag" : "flag")} style={isInjection ? { borderColor: "var(--bad-line)" } : null}>
      <div className="card-head">
        <VLogo vendor={inv.vendor} size={30} r={8} />
        <div>
          <div className="ch-vendor">{inv.vendor}</div>
          <div className="kicker" style={isInjection ? { color: "var(--bad-ink)" } : null}>{kicker}</div>
        </div>
        <div style={{ marginLeft: "auto", textAlign: "right" }}>
          <div className="ch-amt">{money(inv.amount)}</div>
          <div className="id">{inv.id}</div>
        </div>
      </div>

      <div className="card-body">
        <div className="field-label">What I found</div>
        <div className="findings">
          {inv.findings.map((f, i) => <Finding key={i} f={f} />)}
        </div>

        <div className={"didblock " + (isInjection ? "warn" : "warn")}>
          <span className="lead" style={isInjection ? { background: "var(--bad)" } : { background: "var(--warn)" }} />
          <div>
            <div className="did-action">{inv.action}</div>
            <div className="did-why">{inv.why}</div>
          </div>
        </div>

        {editing && (
          <div className="editform">
            <div className="ef-row">
              <label>Invoice amount</label>
              <input className="mono" value={amt} onChange={(e) => setAmt(Number(e.target.value) || 0)} />
            </div>
            <div className="ef-row">
              <label>Then</label>
              <select value={route} onChange={(e) => setRoute(e.target.value)}>
                <option>Queue for payment run</option>
                <option>Priya (manager)</option>
                <option>CFO sign-off</option>
              </select>
            </div>
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button className="btn ghost" onClick={() => setEditing(false)}>Cancel</button>
              <button className="btn primary" onClick={() => onResolve(inv.id, "edit", { amount: amt, route })}>
                <window.Icon.check /> Apply &amp; execute
              </button>
            </div>
          </div>
        )}
      </div>

      {!editing && (
        <div className="card-actions">
          {isInjection ? (
            <React.Fragment>
              <button className="btn primary" onClick={() => onTrail(inv.id)}><window.Icon.branch /> Show the trail</button>
              <button className="btn" onClick={() => onResolve(inv.id, "hold")}><window.Icon.hold /> Keep on hold</button>
              <div className="spacer" />
              <button className="btn ghost" onClick={() => onResolve(inv.id, "approve")}>Override &amp; approve</button>
            </React.Fragment>
          ) : isAcme ? (
            <React.Fragment>
              <button className="btn primary" onClick={() => onResolve(inv.id, "route")}><window.Icon.route /> Route to Priya</button>
              <button className="btn" onClick={() => onResolve(inv.id, "approve")}><window.Icon.check /> Approve</button>
              <button className="btn ghost" onClick={() => onResolve(inv.id, "hold")}>Hold</button>
              <div className="spacer" />
              <button className="link-btn" onClick={() => onTrail(inv.id)}><window.Icon.branch /> Trail</button>
            </React.Fragment>
          ) : (
            <React.Fragment>
              <button className="btn good" onClick={() => onResolve(inv.id, "approve")}><window.Icon.check /> Approve</button>
              <button className="btn" onClick={() => onResolve(inv.id, "hold")}><window.Icon.hold /> Hold</button>
              <button className="btn" onClick={() => setEditing(true)}><window.Icon.pencil /> Edit</button>
              <div className="spacer" />
              <button className="link-btn" onClick={() => onTrail(inv.id)}><window.Icon.branch /> Trail</button>
            </React.Fragment>
          )}
        </div>
      )}
    </div>
  );
}

/* ---------- resolved compact summary ---------- */
const RESOLVED_META = {
  approve: { cls: "approve", icon: "check", verb: "Approved" },
  edit:    { cls: "approve", icon: "pencil", verb: "Edited & approved" },
  route:   { cls: "route",   icon: "route", verb: "Routed to Priya" },
  hold:    { cls: "hold",    icon: "hold",  verb: "Held" },
};
function ResolvedSummary({ inv, action, actor, onTrail }) {
  const m = RESOLVED_META[action] || RESOLVED_META.hold;
  const Ico = window.Icon[m.icon];
  const tail = action === "approve" || action === "edit"
    ? <span>queued <span className="mono">{money(inv.amount)}</span></span>
    : action === "route"
    ? <span>for <b>Priya</b>&rsquo;s sign-off</span>
    : <span>parked, no execution</span>;
  return (
    <div className={"resolved " + m.cls}>
      <span className="rdot"><Ico style={{ width: 14, height: 14 }} /></span>
      <span className="rtext">
        <b>{actor === "rule" ? "Auto-handled" : m.verb}</b> &middot; {inv.vendor} <span className="mono">{inv.id}</span> &middot; {tail}
      </span>
      <button className="link-btn trail-tiny" onClick={() => onTrail(inv.id)}><window.Icon.branch /></button>
    </div>
  );
}

/* ---------- learned-rule card (the headline) ---------- */
function LearnedRuleCard({ proposal, onApprove, onDismiss }) {
  const [thr, setThr] = React.useState(proposal.threshold);
  const [editing, setEditing] = React.useState(false);
  const step = (d) => setThr((v) => Math.max(1, Math.min(20, v + d)));
  return (
    <div className="card learn">
      <div className="card-head">
        <span className="spark-badge" style={{ width: 30, height: 30, borderRadius: 8, display: "grid", placeItems: "center", background: "var(--accent-soft)", color: "var(--accent-ink)", border: "1px solid var(--accent-line)" }}>
          <window.Icon.spark2 style={{ width: 16, height: 16 }} />
        </span>
        <div>
          <div className="ch-vendor">A pattern in how you decide</div>
          <div className="kicker">Learned rule &mdash; your confirmation needed</div>
        </div>
        <span className="id">proposed R-7</span>
      </div>

      <div className="card-body">
        <div className="msg-text" style={{ fontSize: 13 }}>
          The last <b>3 times</b> an <b>Acme Corp</b> invoice came in over its PO by a small margin, you routed it to <b>Priya</b> instead of holding it. Want me to do that for you automatically?
        </div>

        <div className="rule-block">
          <div className="rule-clause">
            <span className="rule-kw">WHEN</span>
            <span className="pred">vendor is <span className="mono">Acme Corp</span></span>
          </div>
          <div className="rule-clause">
            <span className="rule-kw">AND</span>
            <span className="pred">amount over PO by less than</span>
            <span className="thresh-input">
              <input value={thr} onChange={(e) => setThr(Math.max(1, Math.min(20, Number(e.target.value) || 0)))} />
              <span className="unit">%</span>
              <span className="thresh-step">
                <button onClick={() => step(1)}><window.Icon.chevU style={{ width: 11, height: 11 }} /></button>
                <button onClick={() => step(-1)}><window.Icon.chevD style={{ width: 11, height: 11 }} /></button>
              </span>
            </span>
          </div>
          <div className="rule-clause">
            <span className="rule-kw">THEN</span>
            <span className="pred">route to <span className="mono">Priya</span> &nbsp;<span style={{ color: "var(--ink-faint)" }}>(instead of auto-hold)</span></span>
          </div>
        </div>

        <div className="rule-reason">
          <window.Icon.scale />
          <span>Inferred from corrections at <b>+4%</b>, <b>+6%</b>, <b>+7%</b> over PO &mdash; so the threshold generalizes to <b>~{proposal.threshold}%</b>, not just the exact values. Edit it if that&rsquo;s too loose.</span>
        </div>

        <div className="evidence-row">
          {proposal.examples.map((e) => (
            <span key={e.id} className="evidence">{e.id} <b>+{e.pct}%</b></span>
          ))}
        </div>
      </div>

      <div className="card-actions">
        <button className="btn primary" onClick={() => onApprove(thr)}><window.Icon.check /> Approve rule</button>
        <button className="btn" onClick={() => setEditing(true)}><window.Icon.pencil /> Keep editing</button>
        <div className="spacer" />
        <button className="btn ghost" onClick={onDismiss}>Dismiss</button>
      </div>
    </div>
  );
}

Object.assign(window, { VLogo, Chip, Finding, BatchNarration, ApprovalCard, ResolvedSummary, LearnedRuleCard });
