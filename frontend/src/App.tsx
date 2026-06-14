import { useCallback, useEffect, useRef, useState } from 'react'
import { Routes, Route, useNavigate, Navigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Toaster } from '@/components/ui/sonner'
import { Sidebar, type View } from '@/components/layout/Sidebar'
import { Dashboard } from '@/pages/Dashboard'
import { Inbox } from '@/pages/Inbox'
import { History } from '@/pages/History'
import { Rules } from '@/pages/Rules'
import { Guide } from '@/pages/Guide'
import { Usage } from '@/pages/Usage'
import { AuditLog } from '@/pages/AuditLog'
import { AuditSheet } from '@/components/invoice/AuditSheet'
import { InvoiceDetailSheet } from '@/components/invoice/InvoiceDetailSheet'
import {
  chat,
  clearToken,
  getAudit,
  getHealth,
  getInvoice,
  listInvoices,
  proposeRule,
} from '@/lib/api'

import { displayFinding, formatMoney, isToday } from '@/lib/utils'
import type {
  BatchResult,
  ChatMessage,
  InvoiceOut,
  OrgRole,
  ThreadMessage,
  ReviewInvoiceResult,
  ListResult,
  AggregateResult,
  BulkConfirmResult,
  BulkConfirmState,
} from '@/lib/types'
import { isReviewFound } from '@/lib/types'
import { useTour } from '@/hooks/useTour'

function isBatchResult(r: unknown): r is BatchResult {
  return !!r && typeof r === 'object' && 'queued' in r && 'needs' in r
}

function isReviewInvoiceResult(r: unknown): r is ReviewInvoiceResult {
  return !!r && typeof r === 'object' && ('invoice' in r || 'not_found' in r)
}

function isListResult(r: unknown): r is ListResult {
  return !!r && typeof r === 'object' && 'list' in r && Array.isArray((r as ListResult).list)
}

function isAggregateResult(r: unknown): r is AggregateResult {
  return !!r && typeof r === 'object' && 'aggregate' in r
}

function isBulkConfirmResult(r: unknown): r is BulkConfirmResult {
  return !!r && typeof r === 'object' && 'bulk' in r
}

const HEALTH_POLL_MS = 20_000

interface AppProps {
  userEmail: string
  orgName?: string | null
  orgRole?: OrgRole | null
}

export default function App({ userEmail, orgName, orgRole }: AppProps) {
  const navigate = useNavigate()

  const setView = useCallback(
    (v: View) => navigate(v === 'inbox' ? '/' : `/${v}`),
    [navigate],
  )

  const [theme, setTheme] = useState<'light' | 'dark'>(
    () =>
      (localStorage.getItem('ic-theme') as 'light' | 'dark') ||
      (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
  )
  const [invoices, setInvoices] = useState<InvoiceOut[]>([])
  const [thread, setThread] = useState<ThreadMessage[]>(() => {
    try {
      const saved = localStorage.getItem('ic_thread')
      return saved ? (JSON.parse(saved) as ThreadMessage[]) : []
    } catch {
      return []
    }
  })
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
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

  // The guided tour auto-runs on first visit and resumes on refresh entirely
  // from its own localStorage state — no coupling to the intro modal.
  const { startTour } = useTour()

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
    // Show actionable invoices that were created or touched today.
    // Excludes terminal states (queued/cleared/rejected = already resolved)
    // and old seed history that hasn't been touched today.
    const terminal = new Set(['cleared', 'queued', 'rejected'])
    const live = rows.filter(
      (i) =>
        !terminal.has(i.status) &&
        (isToday(i.created_at) || (i.updated_at != null && isToday(i.updated_at))),
    )
    setInvoices(live)
    return live
  }, [])

  // initial load — load PERSISTED state (the backend seeds on boot; refresh
  // preserves processed/pending status). Use the Reset button to start fresh.
  useEffect(() => {
    void (async () => {
      try {
        await refreshInvoices()
      } finally {
        setLoading(false)
      }
    })()
  }, [refreshInvoices])

  // Persist the conversation so a refresh keeps it.
  useEffect(() => {
    try {
      localStorage.setItem('ic_thread', JSON.stringify(thread))
    } catch {
      /* ignore quota errors */
    }
  }, [thread])

  const push = (m: ThreadMessage) => setThread((t) => [...t, m])

  function toggleTheme() {
    setTheme((t) => (t === 'light' ? 'dark' : 'light'))
  }

  function handleLogout() {
    clearToken()
    window.dispatchEvent(new Event('ic-unauthorized'))
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
      } else if (res.intent === 'list' && isListResult(res.result)) {
        push({ type: 'list', data: res.result })
      } else if (res.intent === 'aggregate' && isAggregateResult(res.result)) {
        push({ type: 'aggregate', data: res.result.aggregate })
      } else if (res.intent === 'bulk_confirm' && isBulkConfirmResult(res.result)) {
        push({ type: 'bulk_confirm', data: res.result.bulk, state: 'idle' })
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
          ? { type: 'resolved', invoice: updated, action }
          : m,
      ),
    )
    await refreshInvoices()

    // Toast for resolved action
    const verb =
      action === 'route' ? 'Routed' : action === 'hold' ? 'Held' : 'Approved'
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

  function handleBulkStateChange(idx: number, state: BulkConfirmState, applied?: number) {
    setThread((t) =>
      t.map((m, i) =>
        i === idx && m.type === 'bulk_confirm'
          ? { ...m, state, applied }
          : m,
      ),
    )
  }

  const needsCount = invoices.filter((i) => i.status === 'needs').length

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar
        inboxCount={needsCount}
        theme={theme}
        onThemeToggle={toggleTheme}
        providerLabel={providerLabel}
        providerLive={healthLive === true}
        userEmail={userEmail}
        orgName={orgName}
        orgRole={orgRole}
        onLogout={handleLogout}
      />

      <div className="flex-1 min-w-0 flex flex-col h-full overflow-hidden">
        <Routes>
          <Route
            path="/"
            element={
              <Inbox
                invoices={invoices}
                loading={loading}
                thread={thread}
                input={input}
                busy={busy}
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
                onRefresh={() => void refreshInvoices()}
                onBulkConfirmed={() => void refreshInvoices()}
                onBulkStateChange={handleBulkStateChange}
                onClearThread={() => setThread([])}
                onTakeTour={startTour}
              />
            }
          />
          <Route
            path="/dashboard"
            element={
              <Dashboard
                invoices={invoices}
                loading={loading}
                onProcessBatch={() => {
                  setView('inbox')
                  setTimeout(() => send("Process today's invoices"), 100)
                }}
                onSwitchToInbox={() => setView('inbox')}
              />
            }
          />
          <Route path="/history" element={<History onInvoiceClick={openDetail} />} />
          <Route path="/rules" element={<Rules orgRole={orgRole} />} />
          <Route path="/audit" element={<AuditLog live={healthLive} />} />
          <Route path="/guide" element={<Guide onStartTour={startTour} />} />
          <Route path="/usage" element={<Usage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>

      <AuditSheet invoiceId={auditId} open={auditOpen} onOpenChange={setAuditOpen} />
      <InvoiceDetailSheet
        invoiceId={detailId}
        open={detailOpen}
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
