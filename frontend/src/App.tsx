import { useCallback, useEffect, useRef, useState } from 'react'
import { Send, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { TopBar } from '@/components/invoice/TopBar'
import { InvoiceQueue } from '@/components/invoice/InvoiceQueue'
import { ApprovalCard } from '@/components/invoice/ApprovalCard'
import { LearnedRuleCard } from '@/components/invoice/LearnedRuleCard'
import { AuditSheet } from '@/components/invoice/AuditSheet'
import { RulesSheet } from '@/components/invoice/RulesSheet'
import { VendorAvatar } from '@/components/invoice/VendorAvatar'
import {
  chat,
  demoReset,
  getAudit,
  getInvoice,
  listInvoices,
  proposeRule,
  setRole as setApiRole,
} from '@/lib/api'
import { displayFinding, formatMoney } from '@/lib/utils'
import type {
  BatchResult,
  ChatMessage,
  InvoiceOut,
  Role,
  ThreadMessage,
} from '@/lib/types'

const SUGGESTIONS = ['Process today’s invoices', 'Open the rules']

function isBatchResult(r: unknown): r is BatchResult {
  return !!r && typeof r === 'object' && 'queued' in r && 'needs' in r
}

export default function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>(
    () => (localStorage.getItem('ic-theme') as 'light' | 'dark') || 'light',
  )
  const [role, setRole] = useState<Role>('maya')
  const [invoices, setInvoices] = useState<InvoiceOut[]>([])
  const [thread, setThread] = useState<ThreadMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)
  const [busy, setBusy] = useState(false)
  const [autoClear, setAutoClear] = useState(10000)
  const [auditId, setAuditId] = useState<string | null>(null)
  const [auditOpen, setAuditOpen] = useState(false)
  const [rulesOpen, setRulesOpen] = useState(false)

  const escalRef = useRef<string[]>([])
  const ruleShownRef = useRef(false)
  const threadEndRef = useRef<HTMLDivElement>(null)

  // theme
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('ic-theme', theme)
  }, [theme])

  // autoscroll
  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [thread])

  const refreshInvoices = useCallback(async (): Promise<InvoiceOut[]> => {
    const rows = await listInvoices()
    const live = rows.filter((i) => i.status !== 'cleared')
    setInvoices(live)
    return live
  }, [])

  // initial load
  useEffect(() => {
    void (async () => {
      try {
        await demoReset()
        await refreshInvoices()
      } finally {
        setLoading(false)
      }
    })()
  }, [refreshInvoices])

  const push = (m: ThreadMessage) => setThread((t) => [...t, m])

  function toggleTheme() {
    setTheme((t) => (t === 'light' ? 'dark' : 'light'))
  }
  function toggleRole() {
    setRole((r) => {
      const next: Role = r === 'maya' ? 'priya' : 'maya'
      setApiRole(next)
      return next
    })
  }

  async function handleReset() {
    setResetting(true)
    try {
      await demoReset()
      await refreshInvoices()
      setThread([])
      escalRef.current = []
      ruleShownRef.current = false
    } finally {
      setResetting(false)
    }
  }

  async function presentNextEscalation() {
    const next = escalRef.current.shift()
    if (!next) return
    try {
      const [inv, audit] = await Promise.all([getInvoice(next), getAudit(next)])
      const policy = audit.events.find((e) => e.action === 'findings_computed')
      const guard = audit.events.find((e) => e.action.startsWith('verdict:'))
      const codes = ((policy?.outputs?.findings as string[] | undefined) ?? []).filter(
        (c) => c !== 'PO_MATCH_OK',
      )
      const findings = codes.map((c) => displayFinding(c, ''))
      push({ type: 'approval', invoice: inv, findings, rationale: guard?.rationale ?? '' })
    } catch {
      /* skip on error */
    }
  }

  async function maybeProposeRule() {
    if (ruleShownRef.current) return
    const proposal = await proposeRule()
    if (proposal) {
      ruleShownRef.current = true
      push({ type: 'rule_proposal', proposal })
    }
  }

  async function send(text: string) {
    const msg = text.trim()
    if (!msg || busy) return
    setInput('')
    setBusy(true)
    push({ type: 'user', content: msg })
    try {
      const history: ChatMessage[] = thread
        .filter(
          (m): m is { type: 'user' | 'agent'; content: string } =>
            m.type === 'user' || m.type === 'agent',
        )
        .map((m) => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.content }))
      const res = await chat(msg, history)
      push({ type: 'agent', content: res.reply })
      if (isBatchResult(res.result)) {
        const { queued, needs, blocked } = res.result
        push({ type: 'narration', queued, needs, blocked })
        const live = await refreshInvoices()
        escalRef.current = live.filter((i) => i.status === 'needs').map((i) => i.id)
        await presentNextEscalation()
      }
    } catch (e) {
      push({ type: 'agent', content: `Something went wrong: ${(e as Error).message}` })
    } finally {
      setBusy(false)
    }
  }

  async function onResolved(updated: InvoiceOut, action: string) {
    setThread((t) =>
      t.map((m) =>
        m.type === 'approval' && m.invoice.id === updated.id
          ? { type: 'resolved', invoice: updated, action, byRole: role }
          : m,
      ),
    )
    await refreshInvoices()
    await maybeProposeRule()
    if (!ruleShownRef.current) await presentNextEscalation()
  }

  function openTrail(id: string) {
    setAuditId(id)
    setAuditOpen(true)
  }

  const intro = thread.length === 0

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      <TopBar
        theme={theme}
        onThemeToggle={toggleTheme}
        role={role}
        onRoleToggle={toggleRole}
        autoClearLimit={autoClear}
        onAutoClearChange={setAutoClear}
        onReset={handleReset}
        onRulesOpen={() => setRulesOpen(true)}
        resetting={resetting}
      />

      <div className="flex min-h-0 flex-1">
        {/* Queue */}
        <aside className="w-[360px] shrink-0 border-r border-border bg-muted/30">
          <InvoiceQueue invoices={invoices} loading={loading} onInvoiceClick={openTrail} />
        </aside>

        {/* Conversation */}
        <main className="flex min-w-0 flex-1 flex-col">
          <div className="flex items-center gap-2.5 border-b border-border px-5 py-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold">Copilot</div>
              <div className="text-xs text-muted-foreground">
                AP agent · acting for {role === 'maya' ? 'Maya' : 'Priya'}
              </div>
            </div>
          </div>

          <ScrollArea className="flex-1">
            <div className="mx-auto max-w-3xl px-5 py-6">
              {intro ? (
                <div className="flex flex-col items-center py-20 text-center">
                  <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <Sparkles className="h-7 w-7" />
                  </div>
                  <h2 className="text-xl font-semibold tracking-tight">
                    Maya has 60 invoices and 90 minutes.
                  </h2>
                  <p className="mt-2 max-w-md text-sm text-muted-foreground">
                    Hand the batch to Copilot — it clears the safe ones, asks about the rest,
                    learns how you decide, and logs every move for audit.
                  </p>
                  <Button className="mt-5" onClick={() => send('Process today’s invoices')}>
                    <Send className="mr-1.5 h-4 w-4" /> Process today’s invoices
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  {thread.map((m, i) => (
                    <ThreadItem
                      key={i}
                      m={m}
                      role={role}
                      onResolved={onResolved}
                      onTrail={openTrail}
                      onRuleApproved={() => {
                        void refreshInvoices()
                        setThread((t) => t.filter((x) => x.type !== 'rule_proposal'))
                      }}
                      onRuleDismiss={() =>
                        setThread((t) => t.filter((x) => x.type !== 'rule_proposal'))
                      }
                    />
                  ))}
                  <div ref={threadEndRef} />
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Composer */}
          <div className="border-t border-border px-5 py-3">
            <div className="mx-auto max-w-3xl">
              {!busy && (
                <div className="mb-2 flex flex-wrap gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => (s === 'Open the rules' ? setRulesOpen(true) : send(s))}
                      className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground transition-colors hover:bg-muted"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex items-end gap-2">
                <Textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      send(input)
                    }
                  }}
                  placeholder="Ask Copilot, or type an instruction…"
                  className="min-h-[44px] resize-none"
                  rows={1}
                />
                <Button size="icon" disabled={!input.trim() || busy} onClick={() => send(input)}>
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </main>
      </div>

      <AuditSheet invoiceId={auditId} open={auditOpen} onOpenChange={setAuditOpen} />
      <RulesSheet open={rulesOpen} onOpenChange={setRulesOpen} />
    </div>
  )
}

function ThreadItem({
  m,
  role,
  onResolved,
  onTrail,
  onRuleApproved,
  onRuleDismiss,
}: {
  m: ThreadMessage
  role: Role
  onResolved: (inv: InvoiceOut, action: string) => void
  onTrail: (id: string) => void
  onRuleApproved: () => void
  onRuleDismiss: () => void
}) {
  if (m.type === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-lg bg-primary px-3.5 py-2 text-sm text-primary-foreground">
          {m.content}
        </div>
      </div>
    )
  }
  if (m.type === 'agent') {
    return (
      <div className="flex gap-2.5">
        <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
          <Sparkles className="h-3.5 w-3.5" />
        </div>
        <div className="text-sm leading-relaxed">{m.content}</div>
      </div>
    )
  }
  if (m.type === 'narration') {
    const rows = [
      { label: 'Queued for payment run', meta: `${m.queued}` },
      { label: 'Need your review', meta: `${m.needs}` },
      { label: 'Blocked', meta: `${m.blocked}` },
    ]
    return (
      <div className="ml-8 rounded-lg border border-border bg-card p-3.5">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between py-0.5 text-sm">
            <span className="text-foreground">{r.label}</span>
            <span className="font-mono text-xs text-muted-foreground">{r.meta}</span>
          </div>
        ))}
      </div>
    )
  }
  if (m.type === 'approval') {
    return (
      <div className="ml-8">
        <ApprovalCard
          invoice={m.invoice}
          findings={m.findings}
          rationale={m.rationale}
          role={role}
          onResolved={onResolved}
          onTrailOpen={onTrail}
        />
      </div>
    )
  }
  if (m.type === 'resolved') {
    const verb =
      m.action === 'route' ? 'Routed to Priya' : m.action === 'hold' ? 'Held' : 'Approved'
    return (
      <div className="ml-8 flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-3.5 py-2 text-sm">
        <VendorAvatar vendor={m.invoice.vendor} size="sm" />
        <span className="font-medium">{verb}</span>
        <span className="text-muted-foreground">
          · {m.invoice.vendor} <span className="font-mono text-xs">{m.invoice.id}</span> ·{' '}
          <span className="font-mono text-xs">{formatMoney(m.invoice.amount)}</span>
        </span>
        <button
          className="ml-auto text-xs text-primary hover:underline"
          onClick={() => onTrail(m.invoice.id)}
        >
          Trail
        </button>
      </div>
    )
  }
  if (m.type === 'rule_proposal') {
    return (
      <div className="ml-8">
        <LearnedRuleCard
          proposal={m.proposal}
          onApproved={onRuleApproved}
          onDismiss={onRuleDismiss}
        />
      </div>
    )
  }
  return null
}
