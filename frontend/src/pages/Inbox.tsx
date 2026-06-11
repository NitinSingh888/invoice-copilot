import { useRef, useEffect } from 'react'
import { Send, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { InvoiceQueue } from '@/components/invoice/InvoiceQueue'
import { ApprovalCard } from '@/components/invoice/ApprovalCard'
import { LearnedRuleCard } from '@/components/invoice/LearnedRuleCard'
import { VendorAvatar } from '@/components/invoice/VendorAvatar'
import { PageHeader } from '@/components/layout/PageHeader'
import { formatMoney } from '@/lib/utils'
import type { InvoiceOut, ThreadMessage, Role } from '@/lib/types'

const SUGGESTIONS = ["Process today's invoices", 'Open the rules']

interface InboxProps {
  invoices: InvoiceOut[]
  loading: boolean
  thread: ThreadMessage[]
  input: string
  busy: boolean
  role: Role
  onInputChange: (v: string) => void
  onSend: (text: string) => void
  onResolved: (inv: InvoiceOut, action: string) => void
  onTrail: (id: string) => void
  onRuleApproved: () => void
  onRuleDismiss: () => void
  onInvoiceClick: (id: string) => void
  onRulesOpen: () => void
}

export function Inbox({
  invoices,
  loading,
  thread,
  input,
  busy,
  role,
  onInputChange,
  onSend,
  onResolved,
  onTrail,
  onRuleApproved,
  onRuleDismiss,
  onInvoiceClick,
  onRulesOpen,
}: InboxProps) {
  const threadEndRef = useRef<HTMLDivElement>(null)
  const intro = thread.length === 0
  const needsCount = invoices.filter((i) => i.status === 'needs').length

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [thread])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader
        title="Inbox"
        subtitle={needsCount > 0 ? `${needsCount} invoice${needsCount !== 1 ? 's' : ''} need your attention` : 'Agent workspace'}
        savedCount={invoices.length}
      />

      <div className="flex min-h-0 flex-1">
        {/* Queue panel */}
        <aside className="w-[300px] shrink-0 border-r border-border bg-muted/20">
          <InvoiceQueue
            invoices={invoices}
            loading={loading}
            onInvoiceClick={onInvoiceClick}
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
                AP agent · acting for {role === 'maya' ? 'Maya' : 'Priya'}
              </div>
            </div>
            <div className="ml-auto flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-[hsl(var(--success))] animate-pulse" />
              <span className="text-xs text-muted-foreground">Connected</span>
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
                    Maya has 60 invoices and 90 minutes.
                  </h2>
                  <p className="mt-2 max-w-md text-sm text-muted-foreground">
                    Hand the batch to Copilot — it clears the safe ones, asks about the rest,
                    learns how you decide, and logs every move for audit.
                  </p>
                  <Button
                    className="mt-5 gap-2"
                    onClick={() => onSend("Process today's invoices")}
                  >
                    <Send className="h-4 w-4" />
                    Process today's invoices
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
                      onTrail={onTrail}
                      onRuleApproved={onRuleApproved}
                      onRuleDismiss={onRuleDismiss}
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
                      onClick={() => (s === 'Open the rules' ? onRulesOpen() : onSend(s))}
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
  return null
}
