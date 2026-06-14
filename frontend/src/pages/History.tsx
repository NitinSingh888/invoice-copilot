import { useEffect, useMemo, useState } from 'react'
import { Skeleton } from '@/components/ui/skeleton'
import { PageHeader } from '@/components/layout/PageHeader'
import { VendorAvatar } from '@/components/invoice/VendorAvatar'
import { StatusBadge } from '@/components/invoice/StatusBadge'
import { listAllInvoices } from '@/lib/api'
import { formatMoney, isToday, formatDayHeader, localDateKey } from '@/lib/utils'
import type { InvoiceOut } from '@/lib/types'
import { X } from 'lucide-react'

interface HistoryProps {
  onInvoiceClick: (id: string) => void
}

function truncateInvoiceNumber(s: string | null, max = 24): string {
  if (!s) return ''
  return s.length > max ? s.slice(0, max) + '…' : s
}

function formatTime(isoString: string): string {
  const d = new Date(isoString)
  return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })
}

export function History({ onInvoiceClick }: HistoryProps) {
  const [allInvoices, setAllInvoices] = useState<InvoiceOut[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')

  useEffect(() => {
    setLoading(true)
    listAllInvoices()
      .then((rows) => setAllInvoices(rows))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  // History = a record of completed work: every past invoice, PLUS today's
  // already-decided ones (approved/queued, routed, held, rejected, blocked,
  // cleared). Today's still-pending invoices (received / needs you) stay in the
  // Inbox. Cold-start placeholders (no source_file) are excluded.
  const DECIDED = new Set([
    'queued',
    'cleared',
    'routed',
    'held',
    'rejected',
    'blocked',
  ])
  const pastInvoices = useMemo(
    () =>
      allInvoices.filter(
        (inv) =>
          inv.source_file !== null &&
          (!isToday(inv.created_at) || DECIDED.has(inv.status)),
      ),
    [allInvoices],
  )

  // Apply vendor search
  const query = searchQuery.trim().toLowerCase()
  const filtered = useMemo(
    () =>
      query
        ? pastInvoices.filter(
            (inv) =>
              inv.vendor.toLowerCase().includes(query) ||
              (inv.invoice_number ?? '').toLowerCase().includes(query),
          )
        : pastInvoices,
    [pastInvoices, query],
  )

  // Group by local day, newest first
  const groups = useMemo(() => {
    const byDay = new Map<string, InvoiceOut[]>()
    for (const inv of filtered) {
      const key = localDateKey(inv.created_at)
      const arr = byDay.get(key) ?? []
      arr.push(inv)
      byDay.set(key, arr)
    }
    // Sort keys descending (newest day first)
    const sortedKeys = [...byDay.keys()].sort((a, b) => (a < b ? 1 : -1))
    return sortedKeys.map((key) => ({
      key,
      label: formatDayHeader(byDay.get(key)![0].created_at),
      invoices: byDay.get(key)!.sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      ),
    }))
  }, [filtered])

  const totalCount = filtered.length
  const dayCount = groups.length

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader
        title="History"
        subtitle="Past invoices, grouped by day"
        actions={
          <div className="hidden sm:flex items-center gap-2 h-8 px-3 rounded-md border border-border bg-muted/40 text-muted-foreground text-xs focus-within:border-primary/50 focus-within:bg-background transition-colors">
            <svg
              className="h-3.5 w-3.5 shrink-0"
              viewBox="0 0 16 16"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <circle cx="6.5" cy="6.5" r="4" />
              <path d="M10 10l3 3" strokeLinecap="round" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by vendor…"
              className="bg-transparent outline-none placeholder:text-muted-foreground text-foreground w-36 md:w-48"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery('')}
                className="ml-1 text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Clear filter"
              >
                <X className="h-3 w-3" />
              </button>
            )}
          </div>
        }
      />

      <div className="flex-1 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 py-4">
          {/* Summary line */}
          {!loading && totalCount > 0 && (
            <p className="text-xs text-muted-foreground mb-4 tabular-nums">
              {totalCount} invoice{totalCount !== 1 ? 's' : ''} &middot; {dayCount}{' '}
              day{dayCount !== 1 ? 's' : ''}
            </p>
          )}

          {/* Loading skeletons */}
          {loading && (
            <div className="space-y-6">
              {[1, 2].map((g) => (
                <div key={g}>
                  <Skeleton className="h-4 w-24 mb-3" />
                  <div className="rounded-lg border border-border overflow-hidden">
                    {Array.from({ length: 4 }).map((_, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-3 px-4 py-3 border-b border-border last:border-b-0"
                      >
                        <Skeleton className="h-7 w-7 rounded-full shrink-0" />
                        <div className="flex-1 space-y-1">
                          <Skeleton className="h-3 w-32" />
                          <Skeleton className="h-2.5 w-20" />
                        </div>
                        <Skeleton className="h-4 w-16" />
                        <Skeleton className="h-5 w-20" />
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Empty state */}
          {!loading && totalCount === 0 && !query && (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-muted">
                <svg
                  className="h-7 w-7 text-muted-foreground"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
              </div>
              <h2 className="text-base font-semibold text-foreground mb-1">
                No past invoices yet
              </h2>
              <p className="text-sm text-muted-foreground max-w-xs">
                Invoices processed on previous days will appear here, grouped by day.
              </p>
            </div>
          )}

          {/* No results for search */}
          {!loading && totalCount === 0 && query && (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <p className="text-sm text-muted-foreground">
                No invoices matching &ldquo;{query}&rdquo;
              </p>
              <button
                onClick={() => setSearchQuery('')}
                className="mt-2 text-xs text-primary hover:underline"
              >
                Clear filter
              </button>
            </div>
          )}

          {/* Day groups */}
          {!loading &&
            groups.map(({ key, label, invoices }) => (
              <div key={key} className="mb-6">
                <h2 className="text-xs font-semibold text-muted-foreground tracking-wider uppercase mb-2">
                  {label}
                </h2>
                <div className="rounded-lg border border-border overflow-hidden bg-card">
                  {invoices.map((inv, idx) => (
                    <button
                      key={inv.id}
                      onClick={() => onInvoiceClick(inv.id)}
                      className={[
                        'w-full flex items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-accent/50',
                        idx < invoices.length - 1 ? 'border-b border-border' : '',
                      ].join(' ')}
                    >
                      <VendorAvatar vendor={inv.vendor} size="sm" />

                      {/* Vendor + invoice number */}
                      <div className="flex-1 min-w-0">
                        <span className="text-xs font-medium text-foreground truncate block">
                          {inv.vendor}
                        </span>
                        {inv.invoice_number && (
                          <span
                            className="text-[10px] font-mono text-muted-foreground truncate block"
                            title={inv.invoice_number}
                          >
                            {truncateInvoiceNumber(inv.invoice_number)}
                          </span>
                        )}
                      </div>

                      {/* Amount */}
                      <span className="text-xs font-mono font-medium text-foreground tabular-nums shrink-0">
                        {formatMoney(inv.amount)}
                      </span>

                      {/* Status badge */}
                      <div className="shrink-0">
                        <StatusBadge status={inv.status} />
                      </div>

                      {/* Time */}
                      <span className="text-[10px] font-mono text-muted-foreground shrink-0 w-16 text-right">
                        {formatTime(inv.created_at)}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  )
}
