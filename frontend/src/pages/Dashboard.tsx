import {
  CheckCircle2,
  AlertCircle,
  XCircle,
  Zap,
  Clock,
  TrendingUp,
  ArrowRight,
  Sparkles,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { VendorAvatar } from '@/components/invoice/VendorAvatar'
import { StatusBadge } from '@/components/invoice/StatusBadge'
import { PageHeader } from '@/components/layout/PageHeader'
import { formatMoney, minutesSaved } from '@/lib/utils'
import type { InvoiceOut } from '@/lib/types'
import { cn } from '@/lib/utils'

interface DashboardProps {
  invoices: InvoiceOut[]
  loading: boolean
  onProcessBatch: () => void
  onSwitchToInbox: () => void
}

interface KpiCardProps {
  label: string
  value: string | number
  sub?: string
  icon: React.ReactNode
  variant?: 'default' | 'success' | 'warning' | 'destructive'
  loading?: boolean
}

function KpiCard({ label, value, sub, icon, variant = 'default', loading }: KpiCardProps) {
  const variantClasses = {
    default: 'text-foreground',
    success: 'text-[hsl(var(--success))]',
    warning: 'text-[hsl(var(--warning))]',
    destructive: 'text-destructive',
  }
  const iconBg = {
    default: 'bg-primary/10 text-primary',
    success: 'bg-success/10 text-[hsl(var(--success))]',
    warning: 'bg-warning/10 text-[hsl(var(--warning))]',
    destructive: 'bg-destructive/10 text-destructive',
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-card p-4 space-y-3">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-7 w-16" />
        <Skeleton className="h-3 w-20" />
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-border bg-card p-4 flex flex-col gap-3 hover:shadow-sm transition-shadow duration-150">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</span>
        <div className={cn('h-7 w-7 flex items-center justify-center rounded-md', iconBg[variant])}>
          {icon}
        </div>
      </div>
      <div>
        <span className={cn('text-2xl font-semibold font-sans tracking-tight', variantClasses[variant])}>
          {value}
        </span>
        {sub && (
          <p className="text-xs text-muted-foreground mt-0.5">{sub}</p>
        )}
      </div>
    </div>
  )
}

export function Dashboard({ invoices, loading, onProcessBatch, onSwitchToInbox }: DashboardProps) {
  const total = invoices.length
  const queued = invoices.filter((i) => i.status === 'queued').length
  const needs = invoices.filter((i) => i.status === 'needs').length
  const blocked = invoices.filter((i) => i.status === 'blocked').length
  const auto = queued
  const mins = minutesSaved(queued) // time saved = invoices the agent auto-cleared
  const hours = (mins / 60).toFixed(1)
  const throughputPct = total > 0 ? Math.round((queued / total) * 100) : 0

  // Stacked bar widths
  const queuedPct = total > 0 ? (queued / total) * 100 : 0
  const needsPct = total > 0 ? (needs / total) * 100 : 0
  const blockedPct = total > 0 ? (blocked / total) * 100 : 0
  const otherPct = 100 - queuedPct - needsPct - blockedPct

  // Recent activity: last 8 invoices
  const recent = [...invoices].slice(0, 8)

  const hasActivity = total > 0

  return (
    <div className="flex flex-col h-full overflow-y-auto scrollbar-thin">
      <PageHeader
        title="Dashboard"
        subtitle="Today's results at a glance"
        savedCount={queued}
      />

      <div className="flex-1 p-6 space-y-6">
        {/* KPI grid */}
        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
          <KpiCard
            label="Total Today"
            value={total}
            sub="invoices received"
            icon={<Zap className="h-3.5 w-3.5" />}
            variant="default"
            loading={loading}
          />
          <KpiCard
            label="Auto-Cleared"
            value={auto}
            sub="queued for payment"
            icon={<CheckCircle2 className="h-3.5 w-3.5" />}
            variant="success"
            loading={loading}
          />
          <KpiCard
            label="Needs Review"
            value={needs}
            sub={needs > 0 ? 'awaiting decision' : 'all clear'}
            icon={<AlertCircle className="h-3.5 w-3.5" />}
            variant={needs > 0 ? 'warning' : 'default'}
            loading={loading}
          />
          <KpiCard
            label="Blocked"
            value={blocked}
            sub={blocked > 0 ? 'requires attention' : 'none blocked'}
            icon={<XCircle className="h-3.5 w-3.5" />}
            variant={blocked > 0 ? 'destructive' : 'default'}
            loading={loading}
          />
          <KpiCard
            label="Hours Saved"
            value={`~${hours}h`}
            sub={`${mins} min vs. manual`}
            icon={<Clock className="h-3.5 w-3.5" />}
            variant="success"
            loading={loading}
          />
          <KpiCard
            label="Straight-Through"
            value={`${throughputPct}%`}
            sub="of invoices auto-cleared"
            icon={<TrendingUp className="h-3.5 w-3.5" />}
            variant={throughputPct >= 50 ? 'success' : 'warning'}
            loading={loading}
          />
        </div>

        {/* Today's split bar + CTA */}
        <div className="rounded-lg border border-border bg-card p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-sm font-semibold text-foreground">Today's split</h2>
              <p className="text-xs text-muted-foreground mt-0.5">Distribution by status</p>
            </div>
            {needs > 0 && (
              <Button size="sm" onClick={() => { onSwitchToInbox(); onProcessBatch() }} className="h-7 text-xs gap-1.5">
                <Sparkles className="h-3.5 w-3.5" />
                Review {needs} invoice{needs !== 1 ? 's' : ''}
              </Button>
            )}
          </div>

          {loading ? (
            <Skeleton className="h-3 w-full rounded-full" />
          ) : total > 0 ? (
            <>
              <div className="flex h-2.5 rounded-full overflow-hidden gap-px">
                {queuedPct > 0 && (
                  <div
                    className="bg-[hsl(var(--success))] rounded-l-full transition-all duration-500"
                    style={{ width: `${queuedPct}%` }}
                  />
                )}
                {needsPct > 0 && (
                  <div
                    className="bg-[hsl(var(--warning))] transition-all duration-500"
                    style={{ width: `${needsPct}%` }}
                  />
                )}
                {blockedPct > 0 && (
                  <div
                    className="bg-destructive transition-all duration-500"
                    style={{ width: `${blockedPct}%` }}
                  />
                )}
                {otherPct > 0 && (
                  <div
                    className="bg-muted rounded-r-full transition-all duration-500"
                    style={{ width: `${otherPct}%` }}
                  />
                )}
              </div>
              <div className="flex items-center gap-4 mt-3">
                <LegendItem color="bg-[hsl(var(--success))]" label="Queued" count={queued} />
                <LegendItem color="bg-[hsl(var(--warning))]" label="Needs review" count={needs} />
                <LegendItem color="bg-destructive" label="Blocked" count={blocked} />
                <LegendItem color="bg-muted" label="Other" count={total - queued - needs - blocked} />
              </div>
            </>
          ) : (
            <div className="h-2.5 rounded-full bg-muted" />
          )}
        </div>

        {/* CTA when nothing processed */}
        {!loading && !hasActivity && (
          <div className="rounded-lg border border-dashed border-border bg-card/50 p-8 flex flex-col items-center text-center">
            <div className="h-12 w-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4">
              <Sparkles className="h-6 w-6 text-primary" />
            </div>
            <h3 className="text-base font-semibold text-foreground">No invoices yet</h3>
            <p className="text-sm text-muted-foreground mt-1.5 max-w-sm">
              Start the agent to process today's batch. It'll clear the safe ones and escalate the rest.
            </p>
            <Button className="mt-5 gap-2" onClick={() => { onSwitchToInbox(); onProcessBatch() }}>
              <Sparkles className="h-4 w-4" />
              Process today's batch
            </Button>
          </div>
        )}

        {!loading && hasActivity && (
          <div className="rounded-lg border border-dashed border-border bg-card/50 p-6 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center">
                <Sparkles className="h-4.5 w-4.5 text-primary" />
              </div>
              <div>
                <p className="text-sm font-medium text-foreground">Continue in Inbox</p>
                <p className="text-xs text-muted-foreground">Review {needs} pending + full audit trail</p>
              </div>
            </div>
            <Button variant="outline" size="sm" className="gap-1.5 h-8 text-xs" onClick={onSwitchToInbox}>
              Open Inbox <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}

        {/* Recent activity */}
        {(loading || recent.length > 0) && (
          <div className="rounded-lg border border-border bg-card overflow-hidden">
            <div className="px-4 py-3 border-b border-border">
              <h2 className="text-sm font-semibold text-foreground">Recent activity</h2>
            </div>
            <div className="divide-y divide-border">
              {loading
                ? Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-3 px-4 py-3">
                      <Skeleton className="h-7 w-7 rounded-full shrink-0" />
                      <div className="flex-1 space-y-1">
                        <Skeleton className="h-3.5 w-40" />
                        <Skeleton className="h-3 w-24" />
                      </div>
                      <Skeleton className="h-5 w-16" />
                    </div>
                  ))
                : recent.map((inv) => (
                    <div
                      key={inv.id}
                      className="flex items-center gap-3 px-4 py-3 hover:bg-muted/40 transition-colors duration-150"
                    >
                      <VendorAvatar vendor={inv.vendor} size="sm" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-foreground truncate">{inv.vendor}</span>
                          <span className="text-[10px] font-mono text-muted-foreground shrink-0">{inv.id}</span>
                        </div>
                        {inv.po_number && (
                          <p className="text-xs text-muted-foreground font-mono">{inv.po_number}</p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <span className="text-sm font-mono font-medium text-foreground tabular-nums">
                          {formatMoney(inv.amount)}
                        </span>
                        <StatusBadge status={inv.status} />
                      </div>
                    </div>
                  ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function LegendItem({ color, label, count }: { color: string; label: string; count: number }) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <span className={cn('h-2 w-2 rounded-full shrink-0', color)} />
      <span>{label}</span>
      <span className="font-mono font-medium text-foreground">{count}</span>
    </div>
  )
}
