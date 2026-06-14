import { useState, useEffect } from 'react'
import { ExternalLink, Pencil, CheckCircle2, PauseCircle, FileText } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { VendorAvatar } from './VendorAvatar'
import { FindingChip } from './FindingChip'
import { invoiceAction, getInvoiceFileUrl } from '@/lib/api'
import { formatMoney } from '@/lib/utils'
import type { InvoiceOut, FindingDisplay, OrgMember } from '@/lib/types'

interface ApprovalCardProps {
  invoice: InvoiceOut
  findings: FindingDisplay[]
  rationale: string
  members: OrgMember[]
  onResolved: (invoice: InvoiceOut, action: string) => void
  onTrailOpen: (id: string) => void
}

export function ApprovalCard({
  invoice,
  findings,
  rationale,
  members,
  onResolved,
  onTrailOpen,
}: ApprovalCardProps) {
  const [loading, setLoading] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [editAmount, setEditAmount] = useState(invoice.amount)
  const [editRoute, setEditRoute] = useState(invoice.route ?? '')
  const [fileUrl, setFileUrl] = useState<string | null>(null)
  const [showDoc, setShowDoc] = useState(false)

  // Load document preview URL
  useEffect(() => {
    if (invoice.source_file) {
      getInvoiceFileUrl(invoice.id).then(setFileUrl).catch(() => {})
    }
  }, [invoice.id, invoice.source_file])

  async function doAction(action: 'approve' | 'hold' | 'edit' | 'route', extra?: Record<string, string>) {
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

  function handleApprove() {
    doAction('approve')
  }
  function handleHold() {
    doAction('hold')
  }
  function handleEdit() {
    if (!editing) {
      setEditing(true)
      return
    }
    // Save edits: if route is set, route the invoice; otherwise just update amount
    if (editRoute) {
      doAction('route', { amount: editAmount, route: editRoute })
    } else {
      // Just update the amount — keep the invoice in 'needs' status for further action
      doAction('edit', { amount: editAmount })
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
              <Badge variant="warning" className="text-[10px]">Approval needed</Badge>
            </div>
            <div className="flex items-center gap-1.5 mt-1">
              <span className="text-lg font-mono font-semibold text-foreground tabular-nums">
                {formatMoney(invoice.amount)}
              </span>
              <span className="text-[11px] font-mono text-muted-foreground">
                {invoice.id}
              </span>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* Document preview */}
        {fileUrl && (
          <div>
            {showDoc ? (
              <div className="rounded-md border border-border overflow-hidden">
                <div className="flex items-center justify-between px-3 py-1.5 bg-muted/50 border-b border-border">
                  <span className="text-[10px] font-medium text-muted-foreground">DOCUMENT</span>
                  <button
                    type="button"
                    onClick={() => setShowDoc(false)}
                    className="text-[10px] text-muted-foreground hover:text-foreground"
                  >
                    Hide
                  </button>
                </div>
                <iframe
                  src={fileUrl}
                  className="w-full h-[300px] bg-white"
                  title="Invoice document"
                />
              </div>
            ) : (
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs gap-1.5 w-full"
                onClick={() => setShowDoc(true)}
              >
                <FileText className="h-3 w-3" />
                View document
              </Button>
            )}
          </div>
        )}

        {/* Findings */}
        <div>
          <p className="text-[10px] font-semibold text-muted-foreground mb-1.5 tracking-wide">
            WHAT I FOUND
          </p>
          <div className="flex flex-wrap gap-1.5">
            {findings.map((f) => (
              <FindingChip key={f.code} finding={f} />
            ))}
            {findings.length === 0 && (
              <Badge variant="muted" className="text-[10px]">No issues detected</Badge>
            )}
          </div>
        </div>

        {/* Rationale */}
        {rationale && (
          <div className="bg-muted/50 rounded-md px-3 py-2">
            <p className="text-xs text-muted-foreground leading-relaxed">{rationale}</p>
          </div>
        )}

        {/* Inline edit */}
        {editing && (
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-muted-foreground mb-1 block">Amount</label>
              <Input
                value={editAmount}
                onChange={(e) => setEditAmount(e.target.value)}
                className="font-mono text-xs h-7"
              />
            </div>
            <div>
              <label className="text-[10px] text-muted-foreground mb-1 block">Route to (optional)</label>
              <select
                value={editRoute}
                onChange={(e) => setEditRoute(e.target.value)}
                className="flex h-7 w-full rounded-md border border-input bg-background px-2 text-xs ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
              >
                <option value="">No routing — just update amount</option>
                {members.map((m) => (
                  <option key={m.id} value={m.email}>
                    {m.email}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 flex-wrap pt-1">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                size="sm"
                onClick={handleApprove}
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

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                onClick={handleHold}
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

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                onClick={handleEdit}
                disabled={loading !== null}
                className="h-7 text-xs"
              >
                {loading === 'edit' || loading === 'route' ? (
                  <span className="animate-pulse">Saving…</span>
                ) : (
                  <>
                    <Pencil className="h-3 w-3" />
                    {editing ? 'Save' : 'Edit'}
                  </>
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>{editing ? 'Save changes' : 'Adjust amount or routing'}</TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onTrailOpen(invoice.id)}
                className="h-7 text-xs ml-auto text-muted-foreground"
              >
                <ExternalLink className="h-3 w-3" />
                Trail
              </Button>
            </TooltipTrigger>
            <TooltipContent>See every step the agent took</TooltipContent>
          </Tooltip>
        </div>
      </CardContent>
    </Card>
  )
}
