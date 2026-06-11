import { Clock } from 'lucide-react'
import { VendorAvatar } from './VendorAvatar'
import { StatusBadge } from './StatusBadge'
import { Skeleton } from '@/components/ui/skeleton'
import { formatMoney, minutesSaved } from '@/lib/utils'
import type { InvoiceOut, InvoiceStatus } from '@/lib/types'

interface InvoiceQueueProps {
  invoices: InvoiceOut[]
  loading: boolean
  onInvoiceClick: (id: string) => void
}

const STATUS_GROUPS: { statuses: InvoiceStatus[]; label: string }[] = [
  { statuses: ['needs'], label: 'NEEDS YOU' },
  { statuses: ['blocked'], label: 'BLOCKED' },
  { statuses: ['queued'], label: 'QUEUED FOR PAYMENT RUN' },
  { statuses: ['routed', 'held'], label: 'ROUTED / ON HOLD' },
  { statuses: ['received'], label: 'RECEIVED' },
]

function InvoiceRow({
  invoice,
  onClick,
}: {
  invoice: InvoiceOut
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-3 px-3 py-2.5 hover:bg-accent/50 transition-colors rounded-md group text-left"
    >
      <VendorAvatar vendor={invoice.vendor} size="sm" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="text-xs font-medium text-foreground truncate">{invoice.vendor}</span>
        </div>
        <div className="flex items-center gap-1 mt-0.5">
          <span className="text-[10px] font-mono text-muted-foreground">
            {invoice.id}
          </span>
          {invoice.po_number && (
            <>
              <span className="text-[10px] text-muted-foreground">·</span>
              <span className="text-[10px] font-mono text-muted-foreground">
                {invoice.po_number}
              </span>
            </>
          )}
        </div>
      </div>
      <div className="flex flex-col items-end gap-1">
        <span className="text-xs font-mono font-medium text-foreground tabular-nums">
          {formatMoney(invoice.amount)}
        </span>
        <StatusBadge status={invoice.status} />
      </div>
    </button>
  )
}

export function InvoiceQueue({ invoices, loading, onInvoiceClick }: InvoiceQueueProps) {
  const visible = invoices.filter((i) => i.status !== 'cleared')
  const queued = invoices.filter((i) => i.status === 'queued').length
  const needs = invoices.filter((i) => i.status === 'needs').length
  const blocked = invoices.filter((i) => i.status === 'blocked').length
  const saved = minutesSaved(visible.length)

  return (
    <div className="flex flex-col h-full border-r border-border">
      {/* Header */}
      <div className="px-3 py-3 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xs font-semibold text-foreground">Invoice Queue</h2>
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>~{saved} min saved</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <StatPill color="warning" label="Needs" count={needs} />
          <StatPill color="success" label="Queued" count={queued} />
          <StatPill color="destructive" label="Blocked" count={blocked} />
        </div>
      </div>

      {/* Rows */}
      <div className="flex-1 overflow-y-auto scrollbar-thin px-1 py-1">
        {loading && (
          <div className="space-y-1 p-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 px-2 py-2">
                <Skeleton className="h-6 w-6 rounded-full" />
                <div className="flex-1 space-y-1">
                  <Skeleton className="h-3 w-2/3" />
                  <Skeleton className="h-2.5 w-1/2" />
                </div>
                <Skeleton className="h-5 w-14" />
              </div>
            ))}
          </div>
        )}
        {!loading &&
          STATUS_GROUPS.map(({ statuses, label }) => {
            const group = visible.filter((i) => statuses.includes(i.status as InvoiceStatus))
            if (group.length === 0) return null
            return (
              <div key={label} className="mb-3">
                <div className="px-3 py-1">
                  <span className="text-[10px] font-semibold text-muted-foreground tracking-wider">
                    {label}
                  </span>
                </div>
                {group.map((invoice) => (
                  <InvoiceRow
                    key={invoice.id}
                    invoice={invoice}
                    onClick={() => onInvoiceClick(invoice.id)}
                  />
                ))}
              </div>
            )
          })}
        {!loading && visible.length === 0 && (
          <div className="flex flex-col items-center justify-center h-32 text-center">
            <p className="text-xs text-muted-foreground">Queue is empty</p>
          </div>
        )}
      </div>
    </div>
  )
}

function StatPill({
  color,
  label,
  count,
}: {
  color: 'warning' | 'success' | 'destructive'
  label: string
  count: number
}) {
  const colorClasses = {
    warning: 'text-[hsl(var(--warning))] bg-warning/10',
    success: 'text-[hsl(var(--success))] bg-success/10',
    destructive: 'text-destructive bg-destructive/10',
  }

  return (
    <div
      className={`flex items-center gap-1 rounded px-1.5 py-0.5 ${colorClasses[color]}`}
    >
      <span className="text-[10px] font-medium">{label}</span>
      <span className="text-[10px] font-mono font-semibold">{count}</span>
    </div>
  )
}
