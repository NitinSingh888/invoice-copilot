/* ============================================================
   Invoice Copilot — app + scripted 7-beat demo machine
   ============================================================ */
const usd = window.IC.money;
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let _uid = 0; const uid = () => "m" + (++_uid);

/* ---------- audit trail generation ---------- */
function genTrail(inv) {
  if (inv.kind === "injection") {
    const base = window.IC.INJECTION_TRAIL.map((e) => ({ ...e, actorGroup: e.actor === "agent" ? "agent" : e.module === "guard" ? "guard" : e.module === "policy" ? "system" : "agent" }));
    if (inv.resolution) base.push(...humanEvents(inv));
    return base;
  }
  const verdict = inv.status === "queued" ? "AUTO_CLEAR" : inv.status === "blocked" ? "BLOCK" : inv.status === "ruled" ? "ESCALATE (rule)" : "ESCALATE";
  const codes = (inv.findings || [{ code: "PO_MATCH_OK" }]).map((f) => f.code);
  const ev = [
    { module: "extraction", actor: "agent", actorGroup: "agent", icon: "read", time: "10:14:" + pad(inv),
      action: "Read invoice (vision)", rationale: `Parsed ${inv.vendor} \u00b7 ${usd(inv.amount)}. Decision-fields confidence ${inv.conf || "HIGH"}.`,
      meta: { provider: "anthropic", model: "claude", confidence: inv.conf || "HIGH" },
      detail: { vendor: inv.vendor, total: usd(inv.amount), invoice_no: inv.id, po_ref: inv.po } },
    { module: "enrichment", actor: "agent", actorGroup: "agent", icon: "resolve", time: "10:14:" + pad(inv, 1),
      action: "Resolved vendor \u00b7 matched PO", rationale: inv.po === "\u2014" ? "No PO references this vendor." : `${inv.vendor} is an approved vendor. Matched ${inv.po}.`,
      detail: { vendor_status: "approved", po_match: inv.po } },
    { module: "policy", actor: "system", actorGroup: "system", icon: "flag", time: "10:14:" + pad(inv, 1),
      action: "Findings computed", rationale: (inv.findings || []).map((f) => f.code).join(" \u00b7 ") || "All checks clean.",
      detail: { findings: codes } },
    { module: "guard", actor: "system", actorGroup: "guard", icon: "verdict", time: "10:14:" + pad(inv, 2),
      action: `Verdict \u2192 ${verdict}`, guard: verdict !== "AUTO_CLEAR",
      rationale:
        verdict === "AUTO_CLEAR" ? "HIGH confidence, within $10k cap, all findings info, approved vendor \u2192 auto-clear."
        : verdict === "BLOCK" ? "Exact-duplicate hard stop. Never auto-paid; cannot be overridden without an explicit reason."
        : inv.status === "ruled" ? "Your active rule R-7 matched \u2192 route to Priya (rules may only tighten)."
        : "Over PO tolerance / above auto-cap \u2192 hand to a human.",
      detail: { auto_clear_predicate: verdict === "AUTO_CLEAR" ? "PASSED" : "FAILED" } },
  ];
  if (inv.status === "queued")
    ev.push({ module: "execution", actor: "agent", actorGroup: "execute", icon: "execute", time: "10:14:" + pad(inv, 3),
      action: "Queued for payment run", rationale: "Idempotent \u2014 keyed by (invoice_id, action). Re-runs are a no-op.", detail: { side_effect: "scheduled into batch, not wired" } });
  if (inv.status === "ruled")
    ev.push({ module: "learning", actor: "agent", actorGroup: "agent", icon: "learn", time: "10:14:" + pad(inv, 3),
      action: "Applied rule R-7", rationale: "Matched your approved rule; routed to Priya with a badge.", detail: { rule: "R-7", route: "Priya" } });
  if (inv.resolution) ev.push(...humanEvents(inv));
  return window.IC.chain(ev);
}
function pad(inv, add = 0) { const n = (parseInt(inv.id.replace(/\D/g, ""), 10) % 50) + 1 + add; return String(n).padStart(2, "0"); }
function humanEvents(inv) {
  const r = inv.resolution; const who = r.actor === "priya" ? "user:priya" : "user:maya";
  const labels = { approve: "Approved for payment", edit: "Edited then approved", route: "Routed to Priya for sign-off", hold: "Held with reason" };
  const out = [{ module: "human", actor: who, actorGroup: "human", icon: "ask", time: "10:16:02",
    action: labels[r.action] || "Acted", rationale: `${r.actor === "priya" ? "Priya" : "Maya"} took this decision; recorded as the acting authority.` }];
  if (r.action === "approve" || r.action === "edit")
    out.push({ module: "execution", actor: "agent", actorGroup: "execute", icon: "execute", time: "10:16:03", action: "Queued for payment run", rationale: "Executed past the gate with the human as actor." });
  return window.IC.chain(out);
}

/* ============================================================ App */
const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "dark": false,
  "tAmount": 10000,
  "tone": "friendly",
  "provider": "anthropic",
  "accent": "#4f46e5"
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [mode, setMode] = React.useState("demo");
  const [invoices, setInvoices] = React.useState(() => window.IC.INVOICES.map((i) => ({ ...i, status: "received" })));
  const [messages, setMessages] = React.useState([]);
  const [role, setRole] = React.useState("maya");
  const [drawer, setDrawer] = React.useState(null);
  const [rules, setRules] = React.useState([]);
  const [selected, setSelected] = React.useState(null);
  const [playing, setPlaying] = React.useState(false);
  const [suggestions, setSuggestions] = React.useState(["Process today\u2019s invoices"]);
  const [savedMin, setSavedMin] = React.useState(0);
  const [liveTrailEvents, setLiveTrailEvents] = React.useState([]);
  const [liveChainVerified, setLiveChainVerified] = React.useState(true);

  const invRef = React.useRef(invoices); invRef.current = invoices;
  const acmeRef = React.useRef(0);
  const ruleRef = React.useRef(false);
  const procRef = React.useRef(false);
  const lateRef = React.useRef(false);
  const threadRef = React.useRef(null);

  /* theme + accent */
  React.useEffect(() => {
    document.documentElement.setAttribute("data-theme", t.dark ? "dark" : "light");
  }, [t.dark]);
  React.useEffect(() => {
    if (t.accent) document.documentElement.style.setProperty("--accent", t.accent);
  }, [t.accent]);

  /* autoscroll */
  React.useEffect(() => {
    const el = threadRef.current; if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  const tn = (terse, friendly) => (t.tone === "terse" ? terse : friendly);

  /* ---------- message helpers ---------- */
  const add = (m) => setMessages((x) => [...x, { id: uid(), ...m }]);
  const typing = async (ms = 850) => { const id = uid(); setMessages((x) => [...x, { id, kind: "typing" }]); await sleep(ms); setMessages((x) => x.filter((m) => m.id !== id)); };
  const say = async (text, ms) => { await typing(ms); add({ kind: "agent", text }); };
  const userSay = (text, who = "maya") => add({ kind: "user", actor: who, text });

  /* ---------- recompute saved minutes ---------- */
  const recalcSaved = (list) => {
    const auto = list.filter((i) => i.status === "queued").length;
    const ruled = list.filter((i) => i.status === "ruled").length;
    setSavedMin(auto * 3 + ruled * 4);
  };

  /* ---------- BEAT: process the batch ---------- */
  async function processBatch() {
    if (procRef.current) return; procRef.current = true;
    setSuggestions([]);
    await say(tn("On it. Reading the batch.", "On it \u2014 reading the batch now. I\u2019ll pull vendor, totals, PO numbers and line items off each document."), 700);

    setInvoices((prev) => prev.map((i) => ({ ...i, status: "reading" })));
    await sleep(700);

    // clear the routine ones in waves
    const queuedIds = window.IC.INVOICES.filter((i) => i.target === "queued").map((i) => i.id);
    for (let k = 0; k < queuedIds.length; k += 3) {
      const slice = queuedIds.slice(k, k + 3);
      setInvoices((prev) => prev.map((i) => (slice.includes(i.id) ? { ...i, status: "queued" } : i)));
      await sleep(260);
    }
    await sleep(200);
    setInvoices((prev) => { const next = prev.map((i) => (i.status === "reading" ? { ...i, status: i.target === "ruled" ? "needs" : i.target } : i)); recalcSaved(next); return next; });
    await sleep(300);

    add({ kind: "narration", steps: [
      { text: "Read 16 invoices", meta: "16 / 16" },
      { text: "Matched purchase orders", meta: "15 matched" },
      { text: "Ran policy: tolerance, duplicates, budget, vendor", meta: "" },
      { text: "Cleared the low-risk majority", meta: "10 queued" },
    ] });
    await sleep(350);
    await say(tn(
      "10 queued. 5 need you. 1 blocked (exact duplicate). First one:",
      "Done. I queued 10 routine invoices for the payment run, blocked 1 exact duplicate, and 5 need your judgement. Let\u2019s start with the one furthest over policy:"
    ), 650);
    add({ kind: "card", invId: "INV-4471" });
    setSuggestions(["Approve all Acme under $5k", "Why did you escalate Cyberdyne?"]);
  }

  /* ---------- resolve an escalation ---------- */
  function resolveInvoice(invId, action, payload) {
    if (mode === "live") {
      // Live mode: call backend action endpoint, then refresh queue (no scripted choreography)
      const actor = role;
      (async () => {
        try {
          await IC_API.action(invId, {
            action,
            amount: payload && payload.amount ? payload.amount : undefined,
            route: payload && payload.route ? payload.route : undefined,
            reason: payload && payload.reason ? payload.reason : undefined,
          }, role);
          // Collapse card to resolved summary immediately
          setMessages((x) => x.map((m) => (m.kind === "card" && m.invId === invId ? { id: m.id, kind: "resolved", invId, action, actor } : m)));
          // Refresh queue from backend
          const rows = await IC_API.listInvoices();
          // exclude historical cold-start rows (status "cleared") from the live queue
          const mapped = rows.filter((r) => r.status !== "cleared").map(mapLiveInvoice);
          setInvoices(mapped);
          recalcSaved(mapped);
        } catch (err) {
          add({ kind: "system", text: "Action failed: " + err.message });
        }
      })();
      return;
    }

    // Demo mode — existing scripted choreography (unchanged)
    const inv = invRef.current.find((i) => i.id === invId); if (!inv) return;
    const actor = role;
    const newStatus = action === "route" ? "routed" : action === "hold" ? "held" : "queued";
    setInvoices((prev) => { const next = prev.map((i) => (i.id === invId ? { ...i, status: newStatus, resolution: { action, actor }, amount: payload && payload.amount ? payload.amount : i.amount } : i)); recalcSaved(next); return next; });
    // collapse the open card → resolved summary
    setMessages((x) => x.map((m) => (m.kind === "card" && m.invId === invId ? { id: m.id, kind: "resolved", invId, action, actor } : m)));

    const isAcmeRoute = action === "route" && inv.vendor === "Acme Corp";
    if (isAcmeRoute) acmeRef.current += 1;

    // what comes next
    setTimeout(async () => {
      if (isAcmeRoute && acmeRef.current >= 3 && !ruleRef.current) {
        ruleRef.current = true;
        await say(tn("I see a pattern in those Acme calls.", "That\u2019s the third time you\u2019ve sent an Acme over-PO invoice to Priya. I think I can take that off your plate \u2014 let me show you what I mean."), 900);
        add({ kind: "learn", proposal: { vendor: "Acme Corp", threshold: 8, route: "Priya", examples: [
          { id: "INV-4483", pct: 6 }, { id: "INV-4488", pct: 4 }, { id: "INV-4490", pct: 7 },
        ] } });
        setSuggestions([]);
        return;
      }
      presentNext();
    }, 520);
  }

  const PENDING = ["INV-4471", "INV-4483", "INV-4488", "INV-4490"];
  function presentNext() {
    const done = invRef.current;
    const next = PENDING.find((id) => { const v = done.find((i) => i.id === id); return v && v.status === "needs"; });
    if (next) { add({ kind: "card", invId: next }); }
    else {
      // all routine escalations cleared — nudge toward the trust beat
      setSuggestions(["Why did you escalate Cyberdyne?", "Show me the Cyberdyne trail"]);
    }
  }

  /* ---------- approve learned rule ---------- */
  async function approveRule(threshold) {
    setMessages((x) => x.filter((m) => m.kind !== "learn"));
    const rule = { id: "R-7", vendor: "Acme Corp", threshold, route: "Priya", status: "active", sources: ["INV-4483", "INV-4488", "INV-4490"] };
    setRules((r) => [...r, rule]);
    add({ kind: "rule-saved", threshold });
    await say(tn(
      `Saved as R-7. Acme over-PO under ${threshold}% now routes to Priya automatically.`,
      `Done \u2014 saved as rule R-7. From now on, Acme invoices over PO by less than ${threshold}% route straight to Priya, and I\u2019ll log it each time. You can edit or switch it off in the Rules panel anytime.`
    ), 800);
    if (!lateRef.current) {
      lateRef.current = true;
      await sleep(600);
      await say(tn("One just came in \u2014 watch:", "Speaking of which, another Acme invoice just landed. Watch what happens:"), 700);
      const late = { ...window.IC.LATE_INVOICE, status: "reading" };
      setInvoices((prev) => [late, ...prev]);
      await sleep(1100);
      setInvoices((prev) => { const next = prev.map((i) => (i.id === late.id ? { ...i, status: "ruled", resolution: { action: "route", actor: "rule" } } : i)); recalcSaved(next); return next; });
      add({ kind: "resolved", invId: late.id, action: "route", actor: "rule" });
      await sleep(200);
      setSuggestions(["Why did you escalate Cyberdyne?"]);
    }
  }

  /* ---------- trust beat ---------- */
  async function explainInjection() {
    const inv = invRef.current.find((i) => i.id === "INV-4495");
    if (messages.some((m) => m.kind === "card" && m.invId === "INV-4495")) { openTrail("INV-4495"); return; }
    await say(tn(
      "INV-4495 told me to pay it immediately. I ignored that and escalated. Here\u2019s why:",
      "Good one to check. Cyberdyne\u2019s invoice (INV-4495) had a line in the notes telling me to ignore policy and pay it right away. That text has no authority \u2014 the gate only acts on amount, findings and confidence, never on what a document tells it to do. So I escalated instead of paying."
    ), 1000);
    add({ kind: "card", invId: "INV-4495" });
    setSuggestions([]);
  }

  function openTrail(invId) {
    setSelected(invId);
    if (mode === "live") {
      // Live mode: fetch real audit trail from backend
      (async () => {
        try {
          const data = await IC_API.trail(invId);
          // Map backend event shape to what AuditDrawer expects
          const mapped = (data.events || []).map((e) => ({
            module: e.module,
            actor: e.actor,
            actorGroup: e.actor === "agent" ? "agent" : e.module === "guard" ? "guard" : e.module === "policy" ? "system" : e.actor.startsWith("user:") ? "human" : "system",
            icon: e.action ? "verdict" : "flag",
            time: String(e.seq),
            action: e.action,
            rationale: e.rationale,
            detail: e.inputs || e.outputs ? { ...e.inputs, ...e.outputs } : undefined,
            meta: e.model_meta || null,
            hash: e.hash,
            prev_hash: e.prev_hash,
          }));
          setLiveTrailEvents(mapped);
          setLiveChainVerified(data.chain_verified !== false);
        } catch (err) {
          setLiveTrailEvents([]);
          setLiveChainVerified(false);
        }
        setDrawer({ type: "audit", invId });
      })();
    } else {
      // Demo mode: use genTrail (existing)
      setDrawer({ type: "audit", invId });
    }
  }

  /* ---------- free-text intent ---------- */
  function handleSend(text) {
    if (mode === "live") {
      // Live mode: send to backend chat API, no scripted regex
      userSay(text, role);
      setSuggestions([]);
      (async () => {
        try {
          // Build a simple history array from current messages for context
          const history = messages
            .filter((m) => m.kind === "user" || m.kind === "agent")
            .map((m) => ({ role: m.kind === "user" ? "user" : "assistant", content: m.text }));
          const r = await IC_API.chat(text, history, role);
          await say(r.reply);
          // If result has batch counts, refresh the queue
          if (r.result && (r.result.queued != null || r.result.needs != null || r.result.blocked != null)) {
            const rows = await IC_API.listInvoices();
            // exclude historical cold-start rows (status "cleared") from the live queue
          const mapped = rows.filter((r) => r.status !== "cleared").map(mapLiveInvoice);
            setInvoices(mapped);
            recalcSaved(mapped);
            const q = r.result.queued || 0;
            const n = r.result.needs || 0;
            const b = r.result.blocked || 0;
            add({ kind: "narration", steps: [
              { text: "Processed batch via API", meta: "" },
              { text: "Queued for payment run", meta: q + " invoices" },
              { text: "Need your review", meta: n + " invoices" },
              { text: "Blocked", meta: b + " invoices" },
            ] });
          }
          // If explain intent with invoice_id, open the trail
          if (r.intent === "explain" && r.result && r.result.invoice_id) {
            openTrail(r.result.invoice_id);
          }
          // Refresh rules if a rule-related intent
          if (r.intent === "rules") {
            openRulesDrawerLive();
          }
        } catch (err) {
          add({ kind: "system", text: "API error: " + err.message });
        }
      })();
      return;
    }

    // Demo mode \u2014 existing scripted intent matching (unchanged)
    userSay(text, role);
    setSuggestions([]);
    const low = text.toLowerCase();
    setTimeout(() => {
      if (/process|run today|today'?s|start|go ahead/.test(low)) return void processBatch();
      if (/cyberdyne|injection|escalat|4495|pay now|trail/.test(low)) return void explainInjection();
      if (/acme.*(under|below).*5|approve all acme/.test(low)) {
        say(tn("Two Acme invoices are under $5k and clean \u2014 nothing to approve there; the flagged ones are over PO.", "There are two Acme invoices under $5k, but both are already queued \u2014 clean within tolerance. The Acme ones that need you are the three over PO, below."));
        return;
      }
      if (/rule|learn/.test(low)) { setDrawer({ type: "rules" }); return; }
      say(tn("I can process the batch, explain any decision, or show a trail.", "I can process today\u2019s batch, explain why I made any call, route or approve what needs you, or pull up the full audit trail for any invoice. What would you like?"));
    }, 250);
  }

  /* ---------- guided autoplay ---------- */
  async function playDemo() {
    if (playing) { setPlaying(false); return; }
    setPlaying(true);
    if (!procRef.current) { userSay("Process today\u2019s invoices"); await processBatch(); }
    await sleep(1300);
    // resolve Northwind
    if (invRef.current.find((i) => i.id === "INV-4471").status === "needs") { resolveInvoice("INV-4471", "approve"); await sleep(1700); }
    // route the three Acme
    for (const id of ["INV-4483", "INV-4488", "INV-4490"]) {
      if (invRef.current.find((i) => i.id === id).status === "needs") { resolveInvoice(id, "route"); await sleep(1700); }
    }
    await sleep(900); // learn card shows
    if (ruleRef.current && rules.length === 0) { await approveRule(8); await sleep(1400); }
    await explainInjection(); await sleep(1400);
    openTrail("INV-4495");
    setPlaying(false);
  }

  function resetDemo() {
    procRef.current = false; acmeRef.current = 0; ruleRef.current = false; lateRef.current = false;
    setMessages([]); setRules([]); setDrawer(null); setSelected(null); setSavedMin(0); setPlaying(false);
    setInvoices(window.IC.INVOICES.map((i) => ({ ...i, status: "received" })));
    setSuggestions(["Process today\u2019s invoices"]);
  }

  /* ---------- map backend invoice \u2192 Queue shape ---------- */
  function mapLiveInvoice(row) {
    // backend statuses: received|queued|needs|blocked|routed|held|cleared
    // frontend statuses: queued|needs|blocked|reading|routed|ruled|held|received
    const statusMap = {
      received: "received",
      queued: "queued",
      needs: "needs",
      blocked: "blocked",
      routed: "routed",
      held: "held",
      cleared: "queued",
    };
    return {
      id: row.id,
      vendor: row.vendor,
      amount: Number(row.amount),
      po: row.po_number || "\u2014",
      status: statusMap[row.status] || "received",
      // carry raw fields so ApprovalCard can use findings etc. if present
      findings: row.findings || [],
      kind: row.verdict || null,
      _raw: row,
    };
  }

  /* ---------- enter live mode ---------- */
  async function enterLive() {
    try {
      await IC_API.reset();
      const rows = await IC_API.listInvoices();
      // exclude historical cold-start rows (status "cleared") from the live queue
      const mapped = rows.filter((r) => r.status !== "cleared").map(mapLiveInvoice);
      setInvoices(mapped);
      recalcSaved(mapped);
      setMessages([]);
      add({ kind: "system", text: "Live mode \u2014 connected to the API. Try: \u2018process today\u2019s invoices\u2019." });
      setSuggestions(["Process today\u2019s invoices", "Show me the rules"]);
    } catch (err) {
      add({ kind: "system", text: "Could not connect to the API: " + err.message });
    }
  }

  /* ---------- handle mode switching ---------- */
  function handleModeSwitch(newMode) {
    if (newMode === mode) return;
    setMode(newMode);
    if (newMode === "live") {
      enterLive();
    } else {
      resetDemo();
    }
  }

  /* ---------- open rules drawer (live: fetch from API) ---------- */
  async function openRulesDrawerLive() {
    try {
      const apiRules = await IC_API.listRules();
      const mapped = (apiRules || []).map((r) => ({
        id: r.id,
        vendor: r.vendor,
        threshold: r.max_over_pct != null ? r.max_over_pct * 100 : r.threshold || 0,
        route: r.route,
        status: r.status,
        sources: r.source_correction_ids || [],
      }));
      setRules(mapped);
    } catch (err) {
      // leave existing rules state if fetch fails
    }
    setDrawer({ type: "rules" });
  }

  /* ---------- role switch ---------- */
  function switchRole(r) {
    if (r === role) return; setRole(r);
    const routed = invRef.current.filter((i) => i.status === "routed").length;
    if (r === "priya") add({ kind: "system", text: `You\u2019re now acting as Priya. ${routed > 0 ? routed + " invoice" + (routed > 1 ? "s" : "") + " await your sign-off." : "No escalations waiting."}` });
    else add({ kind: "system", text: "Back to Maya\u2019s queue." });
  }

  const trailInv = drawer && drawer.type === "audit" ? invoices.find((i) => i.id === drawer.invId) : null;
  // In live mode use events fetched from the API; in demo mode generate them from scripted data
  const trailEvents = mode === "live" ? liveTrailEvents : (trailInv ? genTrail(trailInv) : []);
  const intro = messages.length === 0;

  return (
    <div className="app">
      <TopBar t={t} setTweak={setTweak} role={role} onRole={switchRole} onPlay={playDemo} playing={playing} onResetDemo={resetDemo} mode={mode} onMode={handleModeSwitch} />

      <div className="workspace">
        <Queue invoices={invoices} selected={selected} onSelect={openTrail} savedMin={savedMin} />

        <section className="convo">
          <div className="convo-head">
            <div className="agent-ava"><window.Icon.spark2 style={{ width: 16, height: 16 }} /></div>
            <div>
              <h3>Copilot</h3>
              <div className="sub">AP agent &middot; acting for {role === "maya" ? "Maya" : "Priya"}</div>
            </div>
            <div className="liveband">
              <button className="link-btn" onClick={() => mode === "live" ? openRulesDrawerLive() : setDrawer({ type: "rules" })}><window.Icon.book /> Rules{rules.length ? " \u00b7 " + rules.length : ""}</button>
              {mode === "demo" && messages.length > 0 && <React.Fragment><span style={{ color: "var(--line)" }}>|</span><button className="link-btn" onClick={resetDemo}>Reset</button></React.Fragment>}
            </div>
          </div>

          <div className="thread scroll" ref={threadRef}>
            {intro ? (
              <Intro onStart={() => { userSay("Process today\u2019s invoices"); processBatch(); }} onPlay={playDemo} />
            ) : (
              <div className="thread-inner">
                {messages.map((m) => <ThreadItem key={m.id} m={m} invoices={invoices} role={role}
                  onResolve={resolveInvoice} onTrail={openTrail} onApproveRule={approveRule}
                  onDismissRule={() => { setMessages((x) => x.filter((q) => q.kind !== "learn")); presentNext(); }} />)}
              </div>
            )}
          </div>

          <Composer onSend={handleSend} suggestions={suggestions} busy={playing} />
        </section>

        {drawer && drawer.type === "audit" && <AuditDrawer inv={trailInv} events={trailEvents} chainVerified={mode === "live" ? liveChainVerified : true} onClose={() => setDrawer(null)} />}
        {drawer && drawer.type === "rules" && <RulesDrawer rules={rules} onToggle={(id) => {
          const r = rules.find((x) => x.id === id);
          const newStatus = r && r.status === "active" ? "disabled" : "active";
          if (mode === "live") {
            IC_API.setRuleStatus(id, newStatus).catch(() => {});
          }
          setRules((rs) => rs.map((x) => (x.id === id ? { ...x, status: newStatus } : x)));
        }} onClose={() => setDrawer(null)} />}
      </div>

      <TweaksPanel>
        <TweakSection label="Appearance" />
        <TweakToggle label="Dark mode" value={t.dark} onChange={(v) => setTweak("dark", v)} />
        <TweakColor label="Accent" value={t.accent} options={["#4f46e5", "#0e7490", "#7c3aed", "#b45309"]} onChange={(v) => setTweak("accent", v)} />
        <TweakSection label="Autonomy" />
        <TweakSlider label="Auto-clear cap" value={t.tAmount} min={2000} max={25000} step={500} unit="$" onChange={(v) => setTweak("tAmount", v)} />
        <TweakSection label="Agent" />
        <TweakRadio label="Tone" value={t.tone} options={["terse", "friendly"]} onChange={(v) => setTweak("tone", v)} />
        <TweakSelect label="Provider" value={t.provider} options={["anthropic", "openai", "mock"]} onChange={(v) => setTweak("provider", v)} />
      </TweaksPanel>
    </div>
  );
}

/* ---------- intro / empty state ---------- */
function Intro({ onStart, onPlay }) {
  return (
    <div className="empty">
      <div className="empty-inner">
        <div className="empty-mark"><window.Icon.inbox /></div>
        <h3>Maya has 60 invoices and 90 minutes.</h3>
        <p>Most are routine; a few will bite her. Hand the batch to Copilot &mdash; it clears the safe ones, asks about the rest, learns how you decide, and logs every move for audit.</p>
        <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
          <button className="btn primary" onClick={onStart}><window.Icon.send style={{ width: 14, height: 14 }} /> Process today&rsquo;s invoices</button>
          <button className="btn" onClick={onPlay}><window.Icon.play style={{ width: 13, height: 13 }} /> Play the 7-beat demo</button>
        </div>
      </div>
    </div>
  );
}

/* ---------- one thread item ---------- */
function ThreadItem({ m, invoices, role, onResolve, onTrail, onApproveRule, onDismissRule }) {
  if (m.kind === "user")
    return (
      <div className={"msg user " + (m.actor === "priya" ? "priya" : "")}>
        <div className="bubble">{m.text}</div>
      </div>
    );
  if (m.kind === "system")
    return <div style={{ textAlign: "center", fontSize: 11.5, color: "var(--ink-faint)", padding: "2px 0" }}>{m.text}</div>;
  if (m.kind === "typing")
    return (
      <div className="msg agent">
        <div className="ava"><window.Icon.spark2 style={{ width: 13, height: 13 }} /></div>
        <div className="msg-body"><div className="typing"><i /><i /><i /></div></div>
      </div>
    );
  if (m.kind === "agent")
    return (
      <div className="msg agent">
        <div className="ava"><window.Icon.spark2 style={{ width: 13, height: 13 }} /></div>
        <div className="msg-body">
          <div className="msg-name">Copilot</div>
          <div className="msg-text">{m.text}</div>
        </div>
      </div>
    );
  if (m.kind === "narration")
    return (
      <div className="msg agent">
        <div className="ava"><window.Icon.spark2 style={{ width: 13, height: 13 }} /></div>
        <div className="msg-body"><BatchNarration steps={m.steps} /></div>
      </div>
    );
  if (m.kind === "card") {
    const inv = invoices.find((i) => i.id === m.invId); if (!inv) return null;
    return (
      <div className="msg agent">
        <div className="ava"><window.Icon.spark2 style={{ width: 13, height: 13 }} /></div>
        <div className="msg-body"><ApprovalCard inv={inv} onResolve={onResolve} onTrail={onTrail} /></div>
      </div>
    );
  }
  if (m.kind === "resolved") {
    const inv = invoices.find((i) => i.id === m.invId); if (!inv) return null;
    return (
      <div className="msg agent">
        <div className="ava" style={{ visibility: "hidden" }} />
        <div className="msg-body"><ResolvedSummary inv={inv} action={m.action} actor={m.actor} onTrail={onTrail} /></div>
      </div>
    );
  }
  if (m.kind === "learn")
    return (
      <div className="msg agent">
        <div className="ava"><window.Icon.spark2 style={{ width: 13, height: 13 }} /></div>
        <div className="msg-body"><LearnedRuleCard proposal={m.proposal} onApprove={onApproveRule} onDismiss={onDismissRule} /></div>
      </div>
    );
  if (m.kind === "rule-saved")
    return (
      <div className="msg agent">
        <div className="ava" style={{ visibility: "hidden" }} />
        <div className="msg-body">
          <div className="resolved route">
            <span className="rdot"><window.Icon.spark style={{ width: 14, height: 14 }} /></span>
            <span className="rtext"><b>Rule R-7 saved</b> &middot; active &middot; Acme over-PO &lt; <span className="mono">{m.threshold}%</span> &rarr; Priya</span>
          </div>
        </div>
      </div>
    );
  return null;
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
