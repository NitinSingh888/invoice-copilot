import { CheckCircle2, PauseCircle, ArrowRight, Check, X } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { bulkAction } from '@/lib/api'
import type { BulkConfirmResult, BulkConfirmState } from '@/lib/types'

interface BulkConfirmCardProps {
  data: BulkConfirmResult['bulk']
  state: BulkConfirmState
  applied?: number
  onConfirm: (applied: number) => void
  onCancel: () => void
}

const ACTION_ICON = {
  approve: <CheckCircle2 className="h-4 w-4 text-[hsl(var(--success))]" />,
  hold: <PauseCircle className="h-4 w-4 text-[hsl(var(--warning))]" />,
  route: <ArrowRight className="h-4 w-4 text-primary" />,
}

const ACTION_LABEL = {
  approve: 'Approve',
  hold: 'Hold',
  route: 'Route',
}

const ACTION_COLOR = {
  approve: 'text-[hsl(var(--success))]',
  hold: 'text-[hsl(var(--warning))]',
  route: 'text-primary',
}

export function BulkConfirmCard({
  data,
  state,
  applied,
  onConfirm,
  onCancel,
}: BulkConfirmCardProps) {
  const { action, count, total, label, route_to } = data

  if (state === 'dismissed') {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-3.5 py-2.5 text-sm text-muted-foreground">
        <X className="h-3.5 w-3.5 shrink-0" />
        Cancelled
      </div>
    )
  }

  if (state === 'done') {
    const verb =
      action === 'approve' ? 'Approved' : action === 'hold' ? 'Held' : 'Routed'
    return (
      <div className={`flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-3.5 py-2.5 text-sm font-medium ${ACTION_COLOR[action]}`}>
        <Check className="h-3.5 w-3.5 shrink-0" />
        {verb} {applied} invoice{applied !== 1 ? 's' : ''}
      </div>
    )
  }

  const busy = state === 'loading'

  async function handleConfirm() {
    try {
      const res = await bulkAction(data.ids, action, data.route_to)
      onConfirm(res.applied)
    } catch (err) {
      console.error(err)
      onConfirm(0)
    }
  }

  return (
    <Card className="border-border shadow-none">
      <CardContent className="px-4 py-3">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 shrink-0">{ACTION_ICON[action]}</div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-foreground">
              {ACTION_LABEL[action]}{' '}
              <span className={ACTION_COLOR[action]}>{count} invoice{count !== 1 ? 's' : ''}</span>
            </div>
            <div className="mt-0.5 text-xs text-muted-foreground">
              {label}
              {total && (
                <> · <span className="font-mono tabular-nums">{total}</span> total</>
              )}
              {route_to && (
                <> · Route to <span className="font-medium text-foreground">{route_to}</span></>
              )}
            </div>
            <p className="mt-1.5 text-xs text-muted-foreground italic">
              No action has been taken yet — confirm to proceed.
            </p>
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2">
          <Button
            size="sm"
            className="h-7 text-xs"
            disabled={busy}
            onClick={handleConfirm}
          >
            {busy ? (
              <span className="animate-pulse">Processing…</span>
            ) : (
              <>
                <Check className="h-3 w-3" />
                Confirm
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="h-7 text-xs"
            disabled={busy}
            onClick={onCancel}
          >
            <X className="h-3 w-3" />
            Cancel
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
