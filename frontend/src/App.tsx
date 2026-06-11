import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { Toaster } from '@/components/ui/sonner'
import { Sidebar, type View } from '@/components/layout/Sidebar'
import { Dashboard } from '@/pages/Dashboard'
import { Inbox } from '@/pages/Inbox'
import { Rules } from '@/pages/Rules'
import { AuditSheet } from '@/components/invoice/AuditSheet'
import { RulesSheet } from '@/components/invoice/RulesSheet'
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

function isBatchResult(r: unknown): r is BatchResult {
  return !!r && typeof r === 'object' && 'queued' in r && 'needs' in r
}

export default function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>(
    () => (localStorage.getItem('ic-theme') as 'light' | 'dark') || 'light',
  )
  const [role, setRole] = useState<Role>('maya')
  const [view, setView] = useState<View>('dashboard')
  const [invoices, setInvoices] = useState<InvoiceOut[]>([])
  const [thread, setThread] = useState<ThreadMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)
  const [busy, setBusy] = useState(false)
  const [auditId, setAuditId] = useState<string | null>(null)
  const [auditOpen, setAuditOpen] = useState(false)
  const [rulesOpen, setRulesOpen] = useState(false)

  const escalRef = useRef<string[]>([])
  const ruleShownRef = useRef(false)

  // theme
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('ic-theme', theme)
  }, [theme])

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
      toast.success('Demo reset — fresh batch loaded')
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
        toast.success(`Batch processed · ${queued} queued, ${needs} need review, ${blocked} blocked`)
      }
    } catch (e) {
      push({ type: 'agent', content: `Something went wrong: ${(e as Error).message}` })
      toast.error('Something went wrong — check the console')
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

    // Toast for resolved action
    const verb =
      action === 'route' ? 'Routed to Priya' : action === 'hold' ? 'Held' : 'Approved'
    const amountLabel = formatMoney(updated.amount)
    if (action === 'approve') {
      toast.success(`${verb} · ${updated.vendor} · ${amountLabel}`)
    } else if (action === 'hold') {
      toast.warning(`${verb} · ${updated.vendor} · ${amountLabel}`)
    } else {
      toast.info(`${verb} · ${updated.vendor} · ${amountLabel}`)
    }

    await maybeProposeRule()
    if (!ruleShownRef.current) await presentNextEscalation()
  }

  function openTrail(id: string) {
    setAuditId(id)
    setAuditOpen(true)
  }

  const needsCount = invoices.filter((i) => i.status === 'needs').length

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar
        view={view}
        onViewChange={setView}
        inboxCount={needsCount}
        theme={theme}
        onThemeToggle={toggleTheme}
        role={role}
        onRoleToggle={toggleRole}
        onReset={handleReset}
        resetting={resetting}
      />

      <div className="flex-1 min-w-0 flex flex-col h-full overflow-hidden">
        {view === 'dashboard' && (
          <Dashboard
            invoices={invoices}
            loading={loading}
            onProcessBatch={() => send("Process today's invoices")}
            onSwitchToInbox={() => setView('inbox')}
          />
        )}
        {view === 'inbox' && (
          <Inbox
            invoices={invoices}
            loading={loading}
            thread={thread}
            input={input}
            busy={busy}
            role={role}
            onInputChange={setInput}
            onSend={send}
            onResolved={onResolved}
            onTrail={openTrail}
            onRuleApproved={() => {
              void refreshInvoices()
              setThread((t) => t.filter((x) => x.type !== 'rule_proposal'))
              toast.success('Rule activated — agent will apply it going forward')
            }}
            onRuleDismiss={() =>
              setThread((t) => t.filter((x) => x.type !== 'rule_proposal'))
            }
            onInvoiceClick={openTrail}
            onRulesOpen={() => setRulesOpen(true)}
          />
        )}
        {view === 'rules' && <Rules />}
      </div>

      <AuditSheet invoiceId={auditId} open={auditOpen} onOpenChange={setAuditOpen} />
      <RulesSheet open={rulesOpen} onOpenChange={setRulesOpen} />
      <Toaster richColors position="bottom-right" />
    </div>
  )
}
