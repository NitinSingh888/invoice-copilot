import { useState } from 'react'
import { ExternalLink, CheckCircle2, PauseCircle, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { VendorAvatar } from './VendorAvatar'
import { StatusBadge } from './StatusBadge'
import { FindingChip } from './FindingChip'
import { invoiceAction } from '@/lib/api'
import { formatMoney, displayFinding } from '@/lib/utils'
import type { ReviewInvoiceFound, InvoiceOut, Role } from '@/lib/types'

interface InvoiceInspectionCardProps {
  data: ReviewInvoiceFound
  role: Role
  onTrail: (id: string) => void
  onResolved: (inv: InvoiceOut, action: string) => void
}

export function InvoiceInspectionCard({
  data,
  role,
  onTrail,
  onResolved,
}: InvoiceInspectionCardProps) {
  const { invoice, findings, summary } = data
  const [loading, setLoading] = useState<string | null>(null)

  const isAcmeOverPO =
    invoice.vendor.toLowerCase().includes('acme') &&
    findings.some((f) => f.code === 'OVER_TOLERANCE')
  const showRouteToPriya = isAcmeOverPO && role === 'maya'
  const canAct = invoice.status === 'needs'

  const displayFindings = findings
    .filter((f) => f.code !== 'PO_MATCH_OK')
    .map((f) => displayFinding(f.code, f.detail))

  async function doAction(action: 'approve' | 'hold' | 'route', extra?: Record<string, string>) {
    setLoading(action)
    try {
      const updated = await invoiceAction(invoice.id, { action, ...extra })
      onResolved(updated, action)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(null)
    }
  }

  return (
    <Card className="border-border shadow-none">
      <CardHeader className="pb-3">
        <div className="flex items-start gap-3">
          <VendorAvatar vendor={invoice.vendor} size="md" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-foreground">{invoice.vendor}</span>
              <StatusBadge status={invoice.status} />
            </div>
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <span className="text-lg font-mono font-semibold text-foreground tabular-nums">
                {formatMoney(invoice.amount)}
              </span>
              {invoice.invoice_number && (
                <span className="text-xs font-mono text-muted-foreground">
                  {invoice.invoice_number}
                </span>
              )}
              {invoice.po_number && (
                <span className="text-xs font-mono text-muted-foreground">
                  PO: {invoice.po_number}
                </span>
              )}
            </div>
            {invoice.verdict && (
              <div className="flex items-center gap-1.5 mt-1">
                <span className="text-xs text-muted-foreground">Verdict:</span>
                <span className="text-xs font-medium text-foreground">{invoice.verdict}</span>
                {invoice.confidence != null && (
                  <span className="text-[10px] font-mono text-muted-foreground">
                    · {Math.round(invoice.confidence * 100)}% conf
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Summary */}
        {summary && (
          <div className="bg-muted/50 rounded-md px-3 py-2">
            <p className="text-xs text-muted-foreground leading-relaxed">{summary}</p>
          </div>
        )}

        {/* Findings */}
        {displayFindings.length > 0 && (
          <div>
            <p className="text-[10px] font-semibold text-muted-foreground mb-1.5 tracking-wide">
              FINDINGS
            </p>
            <div className="flex flex-wrap gap-1.5">
              {displayFindings.map((f) => (
                <FindingChip key={f.code} finding={f} />
              ))}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 flex-wrap pt-1">
          {canAct && (
            <>
              {showRouteToPriya ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      onClick={() => doAction('route', { route: 'priya' })}
                      disabled={loading !== null}
                      className="h-7 text-xs"
                    >
                      {loading === 'route' ? (
                        <span className="animate-pulse">Routing…</span>
                      ) : (
                        <>
                          <ArrowRight className="h-3 w-3" />
                          Route to Priya
                        </>
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Send to a colleague to approve</TooltipContent>
                </Tooltip>
              ) : (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      size="sm"
                      onClick={() => doAction('approve')}
                      disabled={loading !== null}
                      className="h-7 text-xs"
                    >
                      {loading === 'approve' ? (
                        <span className="animate-pulse">Approving…</span>
                      ) : (
                        <>
                          <CheckCircle2 className="h-3 w-3" />
                          Approve
                        </>
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Approve &amp; queue for payment</TooltipContent>
                </Tooltip>
              )}

              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => doAction('hold')}
                    disabled={loading !== null}
                    className="h-7 text-xs"
                  >
                    {loading === 'hold' ? (
                      <span className="animate-pulse">Holding…</span>
                    ) : (
                      <>
                        <PauseCircle className="h-3 w-3" />
                        Hold
                      </>
                    )}
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Pause — needs more info</TooltipContent>
              </Tooltip>
            </>
          )}

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onTrail(invoice.id)}
                className="h-7 text-xs ml-auto text-muted-foreground"
              >
                <ExternalLink className="h-3 w-3" />
                View audit trail
              </Button>
            </TooltipTrigger>
            <TooltipContent>See every step the agent took</TooltipContent>
          </Tooltip>
        </div>
      </CardContent>
    </Card>
  )
}
