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
  getOrgMembers,
  getThread,
  listInvoices,
  proposeRule,
  saveThread,
} from '@/lib/api'

import { displayFinding, formatMoney } from '@/lib/utils'
import type {
  BatchResult,
  ChatMessage,
  InvoiceOut,
  OrgMember,
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
  const [thread, setThread] = useState<ThreadMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [auditId, setAuditId] = useState<string | null>(null)
  const [auditOpen, setAuditOpen] = useState(false)
  const [detailId, setDetailId] = useState<string | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [members, setMembers] = useState<OrgMember[]>([])

  // Ref to avoid stale closure over `thread` in send()
  const threadRef = useRef(thread)
  threadRef.current = thread

  // Guard: only persist thread after initial load completes
  const loadedRef = useRef(false)

  // health state
  const [healthLive, setHealthLive] = useState<boolean | null>(null)

  // search query for Inbox
  const [searchQuery, setSearchQuery] = useState('')
  // Pending send from Dashboard — fired once navigation to inbox completes
  const pendingSendRef = useRef<string | null>(null)

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
    } catch {
      setHealthLive(false)
    }
  }, [])

  useEffect(() => {
    void checkHealth()
    const id = setInterval(() => { void checkHealth() }, HEALTH_POLL_MS)
    return () => clearInterval(id)
  }, [checkHealth])

  const refreshInvoices = useCallback(async (): Promise<InvoiceOut[]> => {
    const rows = await listInvoices()
    // Exclude terminal states — only show actionable invoices
    const terminal = new Set(['cleared', 'queued', 'rejected'])
    const live = rows.filter((i) => !terminal.has(i.status))
    setInvoices(live)
    return live
  }, [])

  // initial load — fetch invoices + conversation thread + org members from server
  useEffect(() => {
    void (async () => {
      try {
        const [, threadRes] = await Promise.all([
          refreshInvoices(),
          getThread().catch(() => ({ thread: [] as ThreadMessage[] })),
          getOrgMembers().then(setMembers).catch(() => {/* ignore */}),
        ])
        if (threadRes.thread.length > 0) {
          setThread(threadRes.thread)
        }
      } finally {
        loadedRef.current = true
        setLoading(false)
      }
    })()
  }, [refreshInvoices])

  // Persist conversation to server (debounced) — skip the initial mount
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!loadedRef.current) return
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      void saveThread(thread).catch(() => {/* ignore save errors */})
    }, 500)
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
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
      const history: ChatMessage[] = threadRef.current
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

  // Fire pending send from Dashboard after navigating to inbox
  // (useNavigate is async, so we check on each render after navigation)
  useEffect(() => {
    if (pendingSendRef.current && !busy) {
      const msg = pendingSendRef.current
      pendingSendRef.current = null
      void send(msg)
    }
  })

  const needsCount = invoices.filter((i) => i.status === 'needs').length

  return (
    <div className="flex h-screen overflow-hidden bg-background text-foreground">
      <Sidebar
        inboxCount={needsCount}
        theme={theme}
        onThemeToggle={toggleTheme}
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
                members={members}
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
                  pendingSendRef.current = "Process today's invoices"
                  setView('inbox')
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
