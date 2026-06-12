import { useState, useEffect, useRef } from 'react'
import { FileText, ExternalLink, CheckCircle2, PauseCircle, ArrowRight, XCircle, Send } from 'lucide-react'
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
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { VendorAvatar } from './VendorAvatar'
import { StatusBadge } from './StatusBadge'
import { FindingChip } from './FindingChip'
import {
  getInvoice,
  getAudit,
  invoiceAction,
  invoiceFileUrl,
  getComments,
  addComment,
  rejectInvoice,
} from '@/lib/api'
import { formatMoney, displayFinding } from '@/lib/utils'
import type { InvoiceOut, FindingDisplay, Role, InvoiceComment } from '@/lib/types'
import { toast } from 'sonner'
import { cn } from '@/lib/utils'

interface InvoiceDetailSheetProps {
  invoiceId: string | null
  open: boolean
  role: Role
  onOpenChange: (v: boolean) => void
  onTrail: (id: string) => void
  onResolved: (inv: InvoiceOut, action: string) => void
}

function formatRelative(dateStr: string): string {
  const now = Date.now()
  const then = new Date(dateStr).getTime()
  const diffMs = now - then
  const diffSec = Math.floor(diffMs / 1000)
  if (diffSec < 60) return 'just now'
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDays = Math.floor(diffHr / 24)
  return `${diffDays}d ago`
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

  // Reject state
  const [rejectOpen, setRejectOpen] = useState(false)
  const [rejectReason, setRejectReason] = useState('')
  const [rejectBusy, setRejectBusy] = useState(false)

  // Comments state
  const [comments, setComments] = useState<InvoiceComment[]>([])
  const [commentsLoading, setCommentsLoading] = useState(false)
  const [commentBody, setCommentBody] = useState('')
  const [commentBusy, setCommentBusy] = useState(false)
  const commentInputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!open || !invoiceId) return
    setLoading(true)
    setInvoice(null)
    setFindings([])
    setRejectOpen(false)
    setRejectReason('')
    setComments([])

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

    // Load comments independently
    setCommentsLoading(true)
    getComments(invoiceId)
      .then(setComments)
      .catch(console.error)
      .finally(() => setCommentsLoading(false))
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

  async function doReject() {
    if (!invoice) return
    const reason = rejectReason.trim()
    if (!reason) {
      toast.error('A reason is required to reject.')
      return
    }
    setRejectBusy(true)
    try {
      const updated = await rejectInvoice(invoice.id, reason)
      setInvoice(updated)
      setRejectOpen(false)
      setRejectReason('')
      toast.error(`Rejected — ${reason}`)
      onResolved(updated, 'reject')
    } catch (err) {
      console.error(err)
      toast.error('Reject failed. Please try again.')
    } finally {
      setRejectBusy(false)
    }
  }

  async function doAddComment() {
    if (!invoice) return
    const body = commentBody.trim()
    if (!body) return
    setCommentBusy(true)
    try {
      const newComment = await addComment(invoice.id, body)
      setComments((prev) => [...prev, newComment])
      setCommentBody('')
    } catch (err) {
      console.error(err)
      toast.error('Failed to add comment.')
    } finally {
      setCommentBusy(false)
    }
  }

  const isAcmeOverPO =
    invoice?.vendor.toLowerCase().includes('acme') &&
    findings.some((f) => f.code === 'OVER_TOLERANCE')
  const showRouteToPriya = isAcmeOverPO && role === 'maya'
  const canAct = invoice?.status === 'needs' || invoice?.status === 'received'

  // Truncate long invoice/po numbers for display while preserving full value in title attr
  function truncate(s: string | null, max = 24): string {
    if (!s) return ''
    return s.length > max ? s.slice(0, max) + '…' : s
  }

  const hasDecision = invoice?.decided_by || invoice?.decision_reason

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
            {/* Decision banner */}
            {!loading && invoice && hasDecision && (
              <div
                className={cn(
                  'flex items-start gap-2 rounded-md px-3 py-2 text-xs leading-relaxed border',
                  invoice.status === 'rejected'
                    ? 'bg-destructive/10 border-destructive/20 text-destructive'
                    : 'bg-[hsl(var(--success)/0.1)] border-[hsl(var(--success)/0.2)] text-[hsl(var(--success))]',
                )}
              >
                {invoice.status === 'rejected' ? (
                  <XCircle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                ) : (
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                )}
                <span>
                  <span className="font-semibold capitalize">{invoice.status}</span>
                  {invoice.decided_by && (
                    <> by <span className="font-medium">{invoice.decided_by}</span></>
                  )}
                  {invoice.decision_reason && (
                    <> — {invoice.decision_reason}</>
                  )}
                  {invoice.decided_at && (
                    <span className="opacity-60 ml-1">
                      · {formatRelative(invoice.decided_at)}
                    </span>
                  )}
                </span>
              </div>
            )}

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
              <div className="space-y-2">
                <div className="flex items-center gap-2 flex-wrap pt-1">
                  {canAct && (
                    <>
                      {showRouteToPriya ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <Button
                              size="sm"
                              onClick={() => doAction('route', { route: 'priya' })}
                              disabled={actionLoading !== null || rejectOpen}
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
                              disabled={actionLoading !== null || rejectOpen}
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
                            disabled={actionLoading !== null || rejectOpen}
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

                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setRejectOpen((v) => !v)}
                            disabled={actionLoading !== null}
                            className={cn(
                              'h-7 text-xs',
                              rejectOpen
                                ? 'border-destructive/50 text-destructive hover:bg-destructive/10'
                                : 'text-destructive/70 hover:text-destructive hover:border-destructive/50 hover:bg-destructive/5',
                            )}
                          >
                            <XCircle className="h-3 w-3" />
                            Reject
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent>Reject with reason</TooltipContent>
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

                {/* Inline reject reason input */}
                {rejectOpen && canAct && (
                  <div className="flex items-end gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-2">
                    <div className="flex-1 space-y-1">
                      <label className="text-[10px] font-medium text-destructive">
                        Reason for rejection (required)
                      </label>
                      <Input
                        value={rejectReason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        placeholder="e.g. duplicate invoice, incorrect amount…"
                        className="h-7 text-xs border-destructive/30 focus-visible:ring-destructive/30"
                        disabled={rejectBusy}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') void doReject()
                          if (e.key === 'Escape') setRejectOpen(false)
                        }}
                        autoFocus
                      />
                    </div>
                    <Button
                      size="sm"
                      variant="destructive"
                      className="h-7 text-xs shrink-0"
                      disabled={rejectBusy || !rejectReason.trim()}
                      onClick={() => void doReject()}
                    >
                      {rejectBusy ? 'Rejecting…' : 'Confirm'}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      className="h-7 text-xs shrink-0 text-muted-foreground"
                      disabled={rejectBusy}
                      onClick={() => { setRejectOpen(false); setRejectReason('') }}
                    >
                      Cancel
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Comments */}
            {!loading && invoice && (
              <div>
                <p className="text-[10px] font-semibold text-muted-foreground mb-2 tracking-wider uppercase">
                  Comments
                </p>
                {commentsLoading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                ) : comments.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic mb-2">No comments yet.</p>
                ) : (
                  <div className="space-y-2 mb-2">
                    {comments.map((c) => (
                      <div
                        key={c.id}
                        className="rounded-md border border-border bg-muted/30 px-3 py-2 space-y-0.5"
                      >
                        <div className="flex items-baseline gap-2">
                          <span className="text-[11px] font-semibold text-foreground">{c.author}</span>
                          <span className="text-[10px] text-muted-foreground">{formatRelative(c.created_at)}</span>
                        </div>
                        <p className="text-xs text-foreground leading-relaxed whitespace-pre-wrap">{c.body}</p>
                      </div>
                    ))}
                  </div>
                )}

                {/* Add comment */}
                <div className="flex items-end gap-2">
                  <Textarea
                    ref={commentInputRef}
                    value={commentBody}
                    onChange={(e) => setCommentBody(e.target.value)}
                    placeholder="Add a comment…"
                    className="flex-1 text-xs min-h-[60px] resize-none"
                    disabled={commentBusy}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                        e.preventDefault()
                        void doAddComment()
                      }
                    }}
                  />
                  <Button
                    size="sm"
                    className="h-7 text-xs shrink-0 self-end"
                    disabled={commentBusy || !commentBody.trim()}
                    onClick={() => void doAddComment()}
                  >
                    {commentBusy ? (
                      <span className="animate-pulse">Posting…</span>
                    ) : (
                      <>
                        <Send className="h-3 w-3" />
                        Comment
                      </>
                    )}
                  </Button>
                </div>
                <p className="text-[10px] text-muted-foreground mt-1">Cmd+Enter to submit</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
