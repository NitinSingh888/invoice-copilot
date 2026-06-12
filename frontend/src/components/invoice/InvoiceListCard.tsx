import { List } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { VendorAvatar } from './VendorAvatar'
import { StatusBadge } from './StatusBadge'
import { formatMoney } from '@/lib/utils'
import type { ListResult } from '@/lib/types'

interface InvoiceListCardProps {
  data: ListResult
  onRowClick: (id: string) => void
}

export function InvoiceListCard({ data, onRowClick }: InvoiceListCardProps) {
  const { list, label, count } = data
  const truncated = count > list.length

  return (
    <Card className="border-border shadow-none">
      <CardHeader className="pb-2 pt-3 px-4">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary/10 text-primary shrink-0">
            <List className="h-3.5 w-3.5" />
          </div>
          <span className="text-sm font-semibold text-foreground">
            {count} invoice{count !== 1 ? 's' : ''}
          </span>
          <span className="text-xs text-muted-foreground">· {label}</span>
        </div>
      </CardHeader>

      <CardContent className="px-4 pb-3 pt-0">
        <div className="divide-y divide-border rounded-md border border-border overflow-hidden">
          {list.map((inv) => (
            <button
              key={inv.id}
              type="button"
              onClick={() => onRowClick(inv.id)}
              className="flex w-full items-center gap-3 px-3 py-2 text-left hover:bg-muted/50 transition-colors duration-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-inset"
            >
              <VendorAvatar vendor={inv.vendor} size="sm" />
              <span className="flex-1 min-w-0">
                <span className="block text-sm font-medium text-foreground truncate">
                  {inv.vendor}
                </span>
                {inv.invoice_number && (
                  <span className="block font-mono text-[10px] text-muted-foreground truncate">
                    {inv.invoice_number}
                  </span>
                )}
              </span>
              <span className="font-mono text-sm tabular-nums text-foreground shrink-0">
                {formatMoney(inv.amount)}
              </span>
              <StatusBadge status={inv.status} />
            </button>
          ))}
        </div>

        {truncated && (
          <p className="mt-2 text-center text-xs text-muted-foreground">
            Showing first {list.length} of {count}
          </p>
        )}
      </CardContent>
    </Card>
  )
}
