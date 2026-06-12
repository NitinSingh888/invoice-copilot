import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { Toaster } from '@/components/ui/sonner'
import { Sidebar, type View } from '@/components/layout/Sidebar'
import { Dashboard } from '@/pages/Dashboard'
import { Inbox } from '@/pages/Inbox'
import { History } from '@/pages/History'
import { Rules } from '@/pages/Rules'
import { Guide } from '@/pages/Guide'
import { AuditLog } from '@/pages/AuditLog'
import { AuditSheet } from '@/components/invoice/AuditSheet'
import { InvoiceDetailSheet } from '@/components/invoice/InvoiceDetailSheet'
import {
  chat,
  demoReset,
  getAudit,
  getHealth,
  getInvoice,
  listInvoices,
  proposeRule,
  setRole as setApiRole,
} from '@/lib/api'
import { displayFinding, formatMoney, isToday } from '@/lib/utils'
import type {
  BatchResult,
  ChatMessage,
  InvoiceOut,
  Role,
  ThreadMessage,
  ReviewInvoiceResult,
} from '@/lib/types'
import { isReviewFound } from '@/lib/types'
import { useTour } from '@/hooks/useTour'

function isBatchResult(r: unknown): r is BatchResult {
  return !!r && typeof r === 'object' && 'queued' in r && 'needs' in r
}

function isReviewInvoiceResult(r: unknown): r is ReviewInvoiceResult {
  return !!r && typeof r === 'object' && ('invoice' in r || 'not_found' in r)
}

const HEALTH_POLL_MS = 20_000
const INTRO_SEEN_KEY = 'ic_intro_seen'

export default function App() {
  const [theme, setTheme] = useState<'light' | 'dark'>(
    () => (localStorage.getItem('ic-theme') as 'light' | 'dark') || 'light',
  )
  const [role, setRole] = useState<Role>('maya')
  const [view, setView] = useState<View>('inbox')
  const [invoices, setInvoices] = useState<InvoiceOut[]>([])
  const [thread, setThread] = useState<ThreadMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [resetting, setResetting] = useState(false)
  const [busy, setBusy] = useState(false)
  const [auditId, setAuditId] = useState<string | null>(null)
  const [auditOpen, setAuditOpen] = useState(false)
  const [detailId, setDetailId] = useState<string | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  // health state
  const [healthLive, setHealthLive] = useState<boolean | null>(null)
  const [providerLabel, setProviderLabel] = useState('…')

  // search query for Inbox
  const [searchQuery, setSearchQuery] = useState('')

  // Track whether intro modal has been dismissed (for tour auto-launch)
  const [introSeen, setIntroSeen] = useState(
    () => !!localStorage.getItem(INTRO_SEEN_KEY),
  )

  const { startTour } = useTour(introSeen)

  const escalRef = useRef<string[]>([])
  const ruleShownRef = useRef(false)

  // theme
  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    localStorage.setItem('ic-theme', theme)
  }, [theme])

  // health check + polling
  const checkHealth = useCallback(async () => {
    try {
      const h = await getHealth()
      setHealthLive(h.live)
      setProviderLabel(h.live ? `${h.provider} · live` : `${h.provider} · safe`)
    } catch {
      setHealthLive(false)
      setProviderLabel('offline')
    }
  }, [])

  useEffect(() => {
    void checkHealth()
    const id = setInterval(() => { void checkHealth() }, HEALTH_POLL_MS)
    return () => clearInterval(id)
  }, [checkHealth])

  const refreshInvoices = useCallback(async (): Promise<InvoiceOut[]> => {
    const rows = await listInvoices()
    // Inbox shows only non-cleared invoices from today
    const live = rows.filter(
      (i) => i.status !== 'cleared' && isToday(i.created_at),
    )
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
      } else if (res.intent === 'review_invoice' && isReviewInvoiceResult(res.result)) {
        // res.reply already carries a clean confirmation ("Here's INV-… from …:")
        // or the not-found message; only the found case adds an inspection card.
        if (isReviewFound(res.result)) {
          push({ type: 'inspection', data: res.result })
        }
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

  function openDetail(id: string) {
    setDetailId(id)
    setDetailOpen(true)
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
        providerLabel={providerLabel}
        providerLive={healthLive === true}
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
            live={healthLive}
            searchQuery={searchQuery}
            onSearchChange={setSearchQuery}
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
            onInvoiceClick={openDetail}
            onNavigateRules={() => setView('rules')}
            onRefresh={() => void refreshInvoices()}
            onIntroModalDismiss={() => setIntroSeen(true)}
            onTakeTour={startTour}
          />
        )}
        {view === 'history' && (
          <History onInvoiceClick={openDetail} />
        )}
        {view === 'rules' && <Rules />}
        {view === 'audit' && <AuditLog live={healthLive} />}
        {view === 'guide' && <Guide />}
      </div>

      <AuditSheet invoiceId={auditId} open={auditOpen} onOpenChange={setAuditOpen} />
      <InvoiceDetailSheet
        invoiceId={detailId}
        open={detailOpen}
        role={role}
        onOpenChange={setDetailOpen}
        onTrail={(id) => {
          setDetailOpen(false)
          openTrail(id)
        }}
        onResolved={(updated, action) => {
          void onResolved(updated, action)
        }}
      />
      <Toaster richColors position="bottom-right" />
    </div>
  )
}
