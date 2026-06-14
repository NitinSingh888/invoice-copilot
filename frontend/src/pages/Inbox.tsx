import { useRef, useEffect, useState } from 'react'
import { Map, Send, Sparkles, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { InvoiceQueue } from '@/components/invoice/InvoiceQueue'
import { ApprovalCard } from '@/components/invoice/ApprovalCard'
import { LearnedRuleCard } from '@/components/invoice/LearnedRuleCard'
import { InvoiceInspectionCard } from '@/components/invoice/InvoiceInspectionCard'
import { InvoiceListCard } from '@/components/invoice/InvoiceListCard'
import { BulkConfirmCard } from '@/components/invoice/BulkConfirmCard'
import { IntroModal, HelpButton } from '@/components/invoice/IntroModal'
import { VendorAvatar } from '@/components/invoice/VendorAvatar'
import { PageHeader } from '@/components/layout/PageHeader'
import { formatMoney } from '@/lib/utils'
import type { InvoiceOut, ThreadMessage, BulkConfirmState } from '@/lib/types'

const SUGGESTIONS = [
  "Process today's invoices",
  'How many need review?',
  'Show me held invoices',
  'What is the total amount pending?',
]

interface InboxProps {
  invoices: InvoiceOut[]
  loading: boolean
  thread: ThreadMessage[]
  input: string
  busy: boolean
  live?: boolean | null
  searchQuery: string
  onSearchChange: (q: string) => void
  onInputChange: (v: string) => void
  onSend: (text: string) => void
  onResolved: (inv: InvoiceOut, action: string) => void
  onTrail: (id: string) => void
  onRuleApproved: () => void
  onRuleDismiss: () => void
  onInvoiceClick: (id: string) => void
  onRefresh: () => void
  onBulkConfirmed: () => void
  onBulkStateChange: (idx: number, state: BulkConfirmState, applied?: number) => void
  onClearThread?: () => void
  /** Called when IntroModal is dismissed — used to trigger the tour auto-launch */
  onIntroModalDismiss?: () => void
  /** Called when user wants to start / replay the tour */
  onTakeTour?: () => void
}

export function Inbox({
  invoices,
  loading,
  thread,
  input,
  busy,
  live,
  searchQuery,
  onSearchChange,
  onInputChange,
  onSend,
  onResolved,
  onTrail,
  onRuleApproved,
  onRuleDismiss,
  onInvoiceClick,
  onRefresh,
  onBulkConfirmed,
  onBulkStateChange,
  onClearThread,
  onIntroModalDismiss,
  onTakeTour,
}: InboxProps) {
  const threadEndRef = useRef<HTMLDivElement>(null)
  const intro = thread.length === 0
  const receivedCount = invoices.filter((i) => i.status === 'received').length
  const [helpOpen, setHelpOpen] = useState(false)

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [thread])

  // Filter invoices by search query (vendor, id, po)
  const query = searchQuery.trim().toLowerCase()
  const filteredInvoices = query
    ? invoices.filter(
        (inv) =>
          inv.vendor.toLowerCase().includes(query) ||
          inv.id.toLowerCase().includes(query) ||
          (inv.po_number ?? '').toLowerCase().includes(query) ||
          (inv.invoice_number ?? '').toLowerCase().includes(query),
      )
    : invoices

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <IntroModal
        open={helpOpen}
        onOpenChange={setHelpOpen}
        onDismiss={onIntroModalDismiss}
        onTakeTour={onTakeTour}
      />
      <PageHeader
        title="Inbox"
        subtitle="Your invoice queue — Copilot clears the safe ones and asks you about the rest"
        savedCount={invoices.filter((i) => i.status === 'queued').length}
        live={live}
        showSearch
        searchQuery={searchQuery}
        onSearchChange={onSearchChange}
        actions={
          <div className="flex items-center gap-1">
            <HelpButton onClick={() => setHelpOpen(true)} />
            {onTakeTour && (
              <button
                type="button"
                onClick={onTakeTour}
                className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                title="Take the product tour"
              >
                <Map className="h-3.5 w-3.5" />
                Tour
              </button>
            )}
          </div>
        }
      />

      <div className="flex min-h-0 flex-1">
        {/* Queue panel */}
        <aside className="w-[300px] shrink-0 border-r border-border bg-muted/20">
          <InvoiceQueue
            invoices={filteredInvoices}
            loading={loading}
            onInvoiceClick={onInvoiceClick}
            onRefresh={onRefresh}
          />
        </aside>

        {/* Conversation panel */}
        <main className="flex min-w-0 flex-1 flex-col">
          {/* Copilot header bar */}
          <div className="flex items-center gap-2.5 border-b border-border px-5 py-3 bg-card/50 shrink-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Sparkles className="h-4 w-4" />
            </div>
            <div className="leading-tight">
              <div className="text-sm font-semibold">Copilot</div>
              <div className="text-xs text-muted-foreground">
                AP agent · acting on your behalf
              </div>
            </div>
            <div className="ml-auto flex items-center gap-3">
              {thread.length > 0 && onClearThread && (
                <button
                  type="button"
                  onClick={onClearThread}
                  className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                  title="Clear conversation"
                >
                  <Trash2 className="h-3 w-3" />
                  Clear
                </button>
              )}
              <div className="flex items-center gap-1.5">
                <span className={[
                  'h-1.5 w-1.5 rounded-full',
                  live === null ? 'bg-muted-foreground' : live ? 'bg-[hsl(var(--success))] animate-pulse' : 'bg-amber-500',
                ].join(' ')} />
                <span className="text-xs text-muted-foreground">
                  {live === null ? 'Connecting…' : live ? 'Connected' : 'Offline'}
                </span>
              </div>
            </div>
          </div>

          {/* Thread */}
          <ScrollArea className="flex-1">
            <div className="mx-auto max-w-3xl px-5 py-6">
              {intro ? (
                <div className="flex flex-col items-center py-20 text-center">
                  <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10 text-primary">
                    <Sparkles className="h-7 w-7" />
                  </div>
                  <h2 className="text-xl font-semibold tracking-tight">
                    {receivedCount > 0
                      ? `You have ${receivedCount} invoice${receivedCount !== 1 ? 's' : ''} to process today.`
                      : 'Ready to process your invoices'}
                  </h2>
                  <p className="mt-2 max-w-md text-sm text-muted-foreground">
                    Copilot reads each one, matches it to its purchase order, auto-clears the safe ones, and asks you about the risky ones — nothing is paid without passing the rules, and every step is logged.
                  </p>
                  <div className="mt-5 flex items-center gap-3 flex-wrap justify-center">
                    <Button
                      data-tour="process-btn"
                      className="gap-2"
                      onClick={() => onSend("Process today's invoices")}
                    >
                      <Send className="h-4 w-4" />
                      {receivedCount > 0
                        ? `Process today's ${receivedCount} invoice${receivedCount !== 1 ? 's' : ''}`
                        : "Process today's invoices"}
                    </Button>
                    <Button
                      variant="outline"
                      className="gap-2"
                      onClick={() => onSend('Review an invoice')}
                    >
                      Review an invoice
                    </Button>
                  </div>
                  <p className="mt-4 text-xs text-muted-foreground">
                    Or use the suggestion chips below, or{' '}
                    <button
                      type="button"
                      className="underline hover:text-foreground"
                      onClick={() => setHelpOpen(true)}
                    >
                      read the quick guide
                    </button>
                    .
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {thread.map((m, i) => (
                    <ThreadItem
                      key={i}
                      idx={i}
                      m={m}
                      onResolved={onResolved}
                      onTrail={onTrail}
                      onRuleApproved={onRuleApproved}
                      onRuleDismiss={onRuleDismiss}
                      onInvoiceClick={onInvoiceClick}
                      onBulkConfirmed={onBulkConfirmed}
                      onBulkStateChange={onBulkStateChange}
                    />
                  ))}
                  <div ref={threadEndRef} />
                </div>
              )}
            </div>
          </ScrollArea>

          {/* Composer */}
          <div className="border-t border-border px-5 py-3 bg-card/30 shrink-0">
            <div className="mx-auto max-w-3xl">
              {!busy && (
                <div className="mb-2 flex flex-wrap gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => onSend(s)}
                      className="rounded-full border border-border px-3 py-1 text-xs text-muted-foreground transition-colors duration-150 hover:bg-muted hover:text-foreground"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
              <div className="flex items-end gap-2">
                <Textarea
                  value={input}
                  onChange={(e) => onInputChange(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault()
                      onSend(input)
                    }
                  }}
                  placeholder="Ask Copilot, or type an instruction…"
                  className="min-h-[44px] resize-none"
                  rows={1}
                />
                <Button
                  size="icon"
                  disabled={!input.trim() || busy}
                  onClick={() => onSend(input)}
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  )
}

function ThreadItem({
  m,
  idx,
  onResolved,
  onTrail,
  onRuleApproved,
  onRuleDismiss,
  onInvoiceClick,
  onBulkConfirmed,
  onBulkStateChange,
}: {
  m: ThreadMessage
  idx: number
  onResolved: (inv: InvoiceOut, action: string) => void
  onTrail: (id: string) => void
  onRuleApproved: () => void
  onRuleDismiss: () => void
  onInvoiceClick: (id: string) => void
  onBulkConfirmed: () => void
  onBulkStateChange: (idx: number, state: BulkConfirmState, applied?: number) => void
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
      { label: 'Queued for payment run', meta: `${m.queued}`, color: 'text-[hsl(var(--success))]' },
      { label: 'Need your review', meta: `${m.needs}`, color: 'text-[hsl(var(--warning))]' },
      { label: 'Blocked', meta: `${m.blocked}`, color: 'text-destructive' },
    ]
    return (
      <div className="ml-8 rounded-lg border border-border bg-card p-3.5 shadow-sm">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between py-1 text-sm">
            <span className="text-foreground">{r.label}</span>
            <span className={`font-mono text-sm font-semibold tabular-nums ${r.color}`}>{r.meta}</span>
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
          onResolved={onResolved}
          onTrailOpen={onTrail}
        />
      </div>
    )
  }
  if (m.type === 'resolved') {
    const verb =
      m.action === 'route' ? 'Routed to Priya' : m.action === 'hold' ? 'Held' : 'Approved'
    const verbColor =
      m.action === 'approve'
        ? 'text-[hsl(var(--success))]'
        : m.action === 'hold'
        ? 'text-[hsl(var(--warning))]'
        : 'text-muted-foreground'
    return (
      <div className="ml-8 flex items-center gap-2.5 rounded-lg border border-border bg-muted/30 px-3.5 py-2.5 text-sm hover:bg-muted/50 transition-colors duration-150">
        <VendorAvatar vendor={m.invoice.vendor} size="sm" />
        <span className={`font-semibold ${verbColor}`}>{verb}</span>
        <span className="text-muted-foreground">
          · {m.invoice.vendor}{' '}
          <span className="font-mono text-xs">{m.invoice.id}</span>
          {' · '}
          <span className="font-mono text-xs tabular-nums">{formatMoney(m.invoice.amount)}</span>
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
  if (m.type === 'inspection') {
    return (
      <div className="ml-8">
        <InvoiceInspectionCard
          data={m.data}
          onTrail={onTrail}
          onResolved={onResolved}
        />
      </div>
    )
  }
  if (m.type === 'list') {
    return (
      <div className="ml-8">
        <InvoiceListCard data={m.data} onRowClick={onInvoiceClick} />
      </div>
    )
  }
  if (m.type === 'aggregate') {
    return (
      <div className="ml-8 rounded-lg border border-border bg-card px-5 py-4 shadow-none">
        <div className="text-3xl font-semibold tabular-nums text-foreground">{m.data.value}</div>
        <div className="mt-1 text-sm text-muted-foreground">{m.data.label}</div>
      </div>
    )
  }
  if (m.type === 'bulk_confirm') {
    return (
      <div className="ml-8">
        <BulkConfirmCard
          data={m.data}
          state={m.state}
          applied={m.applied}
          onConfirm={(applied) => {
            onBulkStateChange(idx, 'done', applied)
            onBulkConfirmed()
          }}
          onCancel={() => onBulkStateChange(idx, 'dismissed')}
        />
      </div>
    )
  }
  return null
}
