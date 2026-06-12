import { useState, useEffect } from 'react'
import { FileText, ExternalLink, CheckCircle2, PauseCircle, ArrowRight } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { VendorAvatar } from './VendorAvatar'
import { StatusBadge } from './StatusBadge'
import { FindingChip } from './FindingChip'
import { getInvoice, getAudit, invoiceAction, invoiceFileUrl } from '@/lib/api'
import { formatMoney, displayFinding } from '@/lib/utils'
import type { InvoiceOut, FindingDisplay, Role } from '@/lib/types'

interface InvoiceDetailSheetProps {
  invoiceId: string | null
  open: boolean
  role: Role
  onOpenChange: (v: boolean) => void
  onTrail: (id: string) => void
  onResolved: (inv: InvoiceOut, action: string) => void
}

export function InvoiceDetailSheet({
  invoiceId,
  open,
  role,
  onOpenChange,
  onTrail,
  onResolved,
}: InvoiceDetailSheetProps) {
  const [invoice, setInvoice] = useState<InvoiceOut | null>(null)
  const [findings, setFindings] = useState<FindingDisplay[]>([])
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !invoiceId) return
    setLoading(true)
    setInvoice(null)
    setFindings([])

    Promise.all([getInvoice(invoiceId), getAudit(invoiceId)])
      .then(([inv, audit]) => {
        setInvoice(inv)
        const policyEvent = audit.events.find((e) => e.action === 'findings_computed')
        const codes = (
          (policyEvent?.outputs?.findings as string[] | undefined) ?? []
        ).filter((c) => c !== 'PO_MATCH_OK')
        setFindings(codes.map((c) => displayFinding(c, '')))
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [open, invoiceId])

  async function doAction(
    action: 'approve' | 'hold' | 'route',
    extra?: Record<string, string>,
  ) {
    if (!invoice) return
    setActionLoading(action)
    try {
      const updated = await invoiceAction(invoice.id, { action, ...extra })
      setInvoice(updated)
      onResolved(updated, action)
    } catch (err) {
      console.error(err)
    } finally {
      setActionLoading(null)
    }
  }

  const isAcmeOverPO =
    invoice?.vendor.toLowerCase().includes('acme') &&
    findings.some((f) => f.code === 'OVER_TOLERANCE')
  const showRouteToPriya = isAcmeOverPO && role === 'maya'
  const canAct = invoice?.status === 'needs'

  // Truncate long invoice/po numbers for display while preserving full value in title attr
  function truncate(s: string | null, max = 24): string {
    if (!s) return ''
    return s.length > max ? s.slice(0, max) + '…' : s
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-[640px] flex flex-col gap-0 p-0"
      >
        <SheetHeader className="p-4 pb-3 border-b border-border shrink-0">
          {loading ? (
            <div className="space-y-2">
              <Skeleton className="h-5 w-48" />
              <Skeleton className="h-4 w-32" />
            </div>
          ) : invoice ? (
            <>
              <SheetTitle asChild>
                <div className="flex items-center gap-3">
                  <VendorAvatar vendor={invoice.vendor} size="md" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-sm font-semibold text-foreground">
                        {invoice.vendor}
                      </span>
                      <StatusBadge status={invoice.status} />
                    </div>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      <span className="text-base font-mono font-semibold text-foreground tabular-nums">
                        {formatMoney(invoice.amount)}
                      </span>
                      {invoice.invoice_number && (
                        <span
                          className="text-[11px] font-mono text-muted-foreground truncate max-w-[180px]"
                          title={invoice.invoice_number}
                        >
                          {truncate(invoice.invoice_number)}
                        </span>
                      )}
                      {invoice.po_number && (
                        <span
                          className="text-[11px] font-mono text-muted-foreground truncate max-w-[140px]"
                          title={invoice.po_number}
                        >
                          PO: {truncate(invoice.po_number)}
                        </span>
                      )}
                    </div>
                    {invoice.verdict && (
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span className="text-xs text-muted-foreground">
                          {invoice.verdict}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </SheetTitle>
              <SheetDescription className="sr-only">
                Invoice detail for {invoice.vendor}
              </SheetDescription>
            </>
          ) : (
            <SheetTitle>Invoice Detail</SheetTitle>
          )}
        </SheetHeader>

        <ScrollArea className="flex-1 min-h-0">
          <div className="p-4 space-y-4">
            {/* Document preview */}
            <div>
              <p className="text-[10px] font-semibold text-muted-foreground mb-2 tracking-wider uppercase">
                Document
              </p>
              {loading ? (
                <Skeleton className="w-full h-[70vh] rounded-lg" />
              ) : invoice?.source_file ? (
                invoice.source_file.toLowerCase().endsWith('.pdf') ? (
                  <iframe
                    src={invoiceFileUrl(invoice.id)}
                    className="w-full h-[70vh] rounded-lg border border-border bg-muted"
                    title={`Invoice from ${invoice?.vendor ?? ''}`}
                  />
                ) : (
                  // Image: fit to width (zoomed out) in a scrollable frame.
                  <div className="w-full h-[70vh] overflow-auto rounded-lg border border-border bg-muted/40">
                    <img
                      src={invoiceFileUrl(invoice.id)}
                      alt={`Invoice from ${invoice?.vendor ?? ''}`}
                      className="w-full h-auto block"
                    />
                  </div>
                )
              ) : (
                <div className="w-full h-40 rounded-lg border border-dashed border-border bg-muted/30 flex flex-col items-center justify-center gap-2 text-muted-foreground">
                  <FileText className="h-8 w-8 opacity-40" />
                  <p className="text-xs">No document available</p>
                </div>
              )}
            </div>

            {/* Findings */}
            {!loading && findings.length > 0 && (
              <div>
                <p className="text-[10px] font-semibold text-muted-foreground mb-1.5 tracking-wider uppercase">
                  Findings
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {findings.map((f) => (
                    <FindingChip key={f.code} finding={f} />
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            {!loading && invoice && (
              <div className="flex items-center gap-2 flex-wrap pt-1">
                {canAct && (
                  <>
                    {showRouteToPriya ? (
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            size="sm"
                            onClick={() => doAction('route', { route: 'priya' })}
                            disabled={actionLoading !== null}
                            className="h-7 text-xs"
                          >
                            {actionLoading === 'route' ? (
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
                            disabled={actionLoading !== null}
                            className="h-7 text-xs"
                          >
                            {actionLoading === 'approve' ? (
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
                          disabled={actionLoading !== null}
                          className="h-7 text-xs"
                        >
                          {actionLoading === 'hold' ? (
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
                      onClick={() => {
                        if (invoice) onTrail(invoice.id)
                      }}
                      className="h-7 text-xs ml-auto text-muted-foreground"
                    >
                      <ExternalLink className="h-3 w-3" />
                      View audit trail
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>See every step the agent took</TooltipContent>
                </Tooltip>
              </div>
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
