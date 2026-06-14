import { useState, useEffect } from 'react'
import { VendorAvatar } from './VendorAvatar'
import { StatusBadge } from './StatusBadge'
import { AddInvoiceDialog } from './AddInvoiceDialog'
import { Skeleton } from '@/components/ui/skeleton'
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card'
import { formatMoney } from '@/lib/utils'
import { fetchInvoiceFile } from '@/lib/api'
import type { InvoiceOut, InvoiceStatus } from '@/lib/types'

interface InvoiceQueueProps {
  invoices: InvoiceOut[]
  loading: boolean
  onInvoiceClick: (id: string) => void
  onRefresh: () => void
}

const STATUS_GROUPS: { statuses: InvoiceStatus[]; label: string; hint: string }[] = [
  {
    statuses: ['needs'],
    label: 'NEEDS YOU',
    hint: 'your decision required — approve, hold, or route',
  },
  {
    statuses: ['received'],
    label: 'RECEIVED',
    hint: 'waiting to be processed',
  },
  {
    statuses: ['queued'],
    label: 'QUEUED FOR PAYMENT RUN',
    hint: 'cleared — scheduled for payment',
  },
  {
    statuses: ['blocked'],
    label: 'BLOCKED',
    hint: 'stopped by policy (e.g. duplicate)',
  },
  {
    statuses: ['rejected'],
    label: 'REJECTED',
    hint: 'declined with reason',
  },
  {
    statuses: ['routed', 'held'],
    label: 'ROUTED / ON HOLD',
    hint: 'sent to a colleague or paused pending more info',
  },
]

function truncate(s: string | null, max = 20): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}

function useInvoiceFileUrl(invoiceId: string, hasFile: boolean) {
  const [url, setUrl] = useState<string | null>(null)
  useEffect(() => {
    if (!hasFile) return
    let revoked = false
    fetchInvoiceFile(invoiceId)
      .then((blobUrl) => {
        if (!revoked) setUrl(blobUrl)
        else URL.revokeObjectURL(blobUrl)
      })
      .catch(() => {/* ignore */})
    return () => {
      revoked = true
      setUrl((prev) => { if (prev) URL.revokeObjectURL(prev); return null })
    }
  }, [invoiceId, hasFile])
  return url
}

function InvoiceRow({
  invoice,
  onClick,
}: {
  invoice: InvoiceOut
  onClick: () => void
}) {
  const fileUrl = useInvoiceFileUrl(invoice.id, !!invoice.source_file)

  return (
    <HoverCard openDelay={400} closeDelay={100}>
      <HoverCardTrigger asChild>
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
              {invoice.invoice_number ? (
                <span
                  className="text-[10px] font-mono text-muted-foreground truncate max-w-[110px]"
                  title={invoice.invoice_number}
                >
                  {truncate(invoice.invoice_number)}
                </span>
              ) : (
                <span className="text-[10px] font-mono text-muted-foreground">{invoice.id}</span>
              )}
              {invoice.po_number && (
                <>
                  <span className="text-[10px] text-muted-foreground">·</span>
                  <span
                    className="text-[10px] font-mono text-muted-foreground truncate max-w-[80px]"
                    title={invoice.po_number}
                  >
                    {truncate(invoice.po_number, 14)}
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
      </HoverCardTrigger>
      <HoverCardContent
        side="right"
        align="start"
        className="w-[280px] p-0 overflow-hidden"
      >
        {/* Header */}
        <div className="flex items-center gap-2.5 px-3 pt-3 pb-2 border-b border-border">
          <VendorAvatar vendor={invoice.vendor} size="sm" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-foreground truncate">{invoice.vendor}</p>
            <p className="text-[10px] font-mono text-muted-foreground">
              {formatMoney(invoice.amount)}
            </p>
          </div>
          <StatusBadge status={invoice.status} />
        </div>
        {/* Doc preview — only mount the iframe when the hover is open and source_file exists */}
        {invoice.source_file && fileUrl ? (
          invoice.source_file.toLowerCase().endsWith('.pdf') ? (
            <iframe
              src={fileUrl}
              className="w-[280px] h-[340px] pointer-events-none block"
              title={`Preview of ${invoice.vendor} invoice`}
            />
          ) : (
            <div className="w-[280px] h-[340px] overflow-hidden bg-muted/40">
              <img
                src={fileUrl}
                alt={`Preview of ${invoice.vendor} invoice`}
                className="w-[280px] h-auto block"
              />
            </div>
          )
        ) : (
          <div className="w-[280px] h-[160px] flex flex-col items-center justify-center gap-2 text-muted-foreground bg-muted/20 px-3">
            {invoice.invoice_number && (
              <p
                className="text-[10px] font-mono text-center text-muted-foreground break-all"
                title={invoice.invoice_number}
              >
                {truncate(invoice.invoice_number, 32)}
              </p>
            )}
            {invoice.po_number && (
              <p
                className="text-[10px] font-mono text-center text-muted-foreground break-all"
                title={invoice.po_number}
              >
                PO: {truncate(invoice.po_number, 28)}
              </p>
            )}
            <p className="text-[11px] text-muted-foreground/60 mt-1">No document attached</p>
          </div>
        )}
      </HoverCardContent>
    </HoverCard>
  )
}

type StatusFilter = 'needs' | 'received' | 'blocked' | null

export function InvoiceQueue({ invoices, loading, onInvoiceClick, onRefresh }: InvoiceQueueProps) {
  const [activeFilter, setActiveFilter] = useState<StatusFilter>(null)
  const allVisible = invoices.filter((i) => i.status !== 'cleared')
  const needs = invoices.filter((i) => i.status === 'needs').length
  const blocked = invoices.filter((i) => i.status === 'blocked').length
  const received = invoices.filter((i) => i.status === 'received').length

  const visible = activeFilter
    ? allVisible.filter((i) => i.status === activeFilter)
    : allVisible

  function toggleFilter(status: StatusFilter) {
    setActiveFilter((prev) => (prev === status ? null : status))
  }

  return (
    <div className="flex flex-col h-full border-r border-border">
      {/* Header */}
      <div className="px-3 py-3 border-b border-border">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xs font-semibold text-foreground">Invoice Queue</h2>
          <AddInvoiceDialog onAdded={onRefresh} />
        </div>
        <div className="flex items-center gap-2">
          <StatPill color="warning" label="Needs review" count={needs} active={activeFilter === 'needs'} onClick={() => toggleFilter('needs')} />
          <StatPill color="muted" label="Received" count={received} active={activeFilter === 'received'} onClick={() => toggleFilter('received')} />
          <StatPill color="destructive" label="Blocked" count={blocked} active={activeFilter === 'blocked'} onClick={() => toggleFilter('blocked')} />
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
          STATUS_GROUPS.map(({ statuses, label, hint }) => {
            const group = visible.filter((i) => statuses.includes(i.status as InvoiceStatus))
            if (group.length === 0) return null
            return (
              <div key={label} className="mb-3">
                <div className="px-3 py-1">
                  <span className="text-[10px] font-semibold text-muted-foreground tracking-wider">
                    {label}
                  </span>
                  <p className="text-[10px] text-muted-foreground/60 mt-0.5 leading-tight">{hint}</p>
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
          <div className="flex flex-col items-center justify-center h-40 text-center px-4">
            <p className="text-xs font-medium text-foreground mb-1">No invoices in queue</p>
            <p className="text-[11px] text-muted-foreground leading-relaxed">
              Click <strong>Add invoice</strong> above to upload a PDF or pick a sample, or tell Copilot to "Process today's invoices".
            </p>
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
  active,
  onClick,
}: {
  color: 'warning' | 'success' | 'destructive' | 'muted'
  label: string
  count: number
  active?: boolean
  onClick?: () => void
}) {
  const colorClasses = {
    warning: 'text-[hsl(var(--warning))] bg-warning/10',
    success: 'text-[hsl(var(--success))] bg-success/10',
    destructive: 'text-destructive bg-destructive/10',
    muted: 'text-muted-foreground bg-muted',
  }

  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex items-center gap-1 rounded px-1.5 py-0.5 cursor-pointer transition-all ${colorClasses[color]} ${active ? 'ring-2 ring-primary ring-offset-1' : 'hover:opacity-80'}`}
    >
      <span className="text-[10px] font-medium">{label}</span>
      <span className="text-[10px] font-mono font-semibold">{count}</span>
    </button>
  )
}
