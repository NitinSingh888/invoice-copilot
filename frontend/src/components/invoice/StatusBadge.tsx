import {
  Clock,
  AlertCircle,
  XCircle,
  CheckCircle,
  ArrowRight,
  PauseCircle,
  Inbox,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { statusLabel, statusVariant } from '@/lib/utils'
import type { InvoiceStatus } from '@/lib/types'

interface StatusBadgeProps {
  status: InvoiceStatus
  className?: string
}

const STATUS_ICONS: Record<InvoiceStatus, React.ReactNode> = {
  received: <Inbox className="h-3 w-3" />,
  queued: <CheckCircle className="h-3 w-3" />,
  needs: <AlertCircle className="h-3 w-3" />,
  blocked: <XCircle className="h-3 w-3" />,
  routed: <ArrowRight className="h-3 w-3" />,
  held: <PauseCircle className="h-3 w-3" />,
  cleared: <Clock className="h-3 w-3" />,
  rejected: <XCircle className="h-3 w-3" />,
}

const STATUS_TOOLTIPS: Record<InvoiceStatus, string> = {
  received: 'Received — waiting to be processed by Copilot',
  queued: 'Queued — passed all checks, scheduled for payment',
  needs: 'Needs you — Copilot flagged a risk and needs your decision',
  blocked: 'Blocked — stopped by a policy rule (e.g. duplicate invoice)',
  routed: 'Routed — sent to a colleague for approval',
  held: 'On hold — paused pending more information',
  cleared: 'Cleared — payment has been executed',
  rejected: 'Rejected — declined with reason',
}

const VARIANT_MAP: Record<
  ReturnType<typeof statusVariant>,
  'default' | 'success' | 'warning' | 'destructive' | 'muted'
> = {
  default: 'default',
  success: 'success',
  warning: 'warning',
  destructive: 'destructive',
  muted: 'muted',
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const variant = statusVariant(status)
  const mappedVariant = VARIANT_MAP[variant]
  const tooltip = STATUS_TOOLTIPS[status]

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="cursor-default">
          <Badge variant={mappedVariant} className={className}>
            {STATUS_ICONS[status]}
            {statusLabel(status)}
          </Badge>
        </span>
      </TooltipTrigger>
      <TooltipContent side="top">{tooltip}</TooltipContent>
    </Tooltip>
  )
}
