import { useEffect, useState } from 'react'
import {
  FileText,
  Link2,
  Flag,
  Shield,
  CheckCircle2,
  Sparkles,
  User,
  Brain,
  ChevronDown,
  ChevronRight,
  Hash,
} from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { getAudit } from '@/lib/api'
import type { AuditEvent, AuditResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

interface AuditSheetProps {
  invoiceId: string | null
  open: boolean
  onOpenChange: (v: boolean) => void
}

const MODULE_META: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
  extraction: { icon: <FileText className="h-3 w-3" />, label: 'Extraction', color: 'bg-blue-500' },
  enrichment: { icon: <Link2 className="h-3 w-3" />, label: 'Enrichment', color: 'bg-purple-500' },
  policy: { icon: <Flag className="h-3 w-3" />, label: 'Policy', color: 'bg-amber-500' },
  guard: { icon: <Shield className="h-3 w-3" />, label: 'Guard', color: 'bg-emerald-500' },
  execution: { icon: <CheckCircle2 className="h-3 w-3" />, label: 'Execution', color: 'bg-green-500' },
  learning: { icon: <Sparkles className="h-3 w-3" />, label: 'Learning', color: 'bg-violet-500' },
  human: { icon: <User className="h-3 w-3" />, label: 'Human', color: 'bg-orange-500' },
}

function getModuleMeta(module: string) {
  return MODULE_META[module] ?? { icon: <Brain className="h-3 w-3" />, label: module, color: 'bg-muted-foreground' }
}

/** Format action name: "extracted_fields" → "Extracted fields", "verdict:AUTO_CLEAR" → "Auto Clear" */
function formatAction(action: string): string {
  if (action.startsWith('verdict:')) {
    const v = action.slice(8)
    return v.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }
  if (action.startsWith('executed:')) {
    return action.slice(9).replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
  }
  return action.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

/** Render key-value data as a clean table instead of raw JSON */
function DataTable({ data, label }: { data: Record<string, unknown>; label: string }) {
  const entries = Object.entries(data)
  if (entries.length === 0) return null

  return (
    <div>
      <p className="text-[10px] font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">{label}</p>
      <div className="rounded-md border border-border overflow-hidden">
        {entries.map(([key, val], i) => (
          <div
            key={key}
            className={cn(
              'flex items-start gap-3 px-3 py-1.5 text-xs',
              i % 2 === 0 ? 'bg-muted/30' : 'bg-card',
            )}
          >
            <span className="text-muted-foreground font-medium min-w-[100px] shrink-0">
              {key.replace(/_/g, ' ')}
            </span>
            <span className="text-foreground font-mono break-all">
              {typeof val === 'object' ? JSON.stringify(val) : String(val ?? '—')}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

function EventRow({ event, isLast }: { event: AuditEvent; isLast: boolean }) {
  const [expanded, setExpanded] = useState(false)
  const meta = getModuleMeta(event.module)
  const hasData =
    Object.keys(event.inputs).length > 0 || Object.keys(event.outputs).length > 0

  const isVerdict = event.action.startsWith('verdict:')
  const isExecution = event.action.startsWith('executed:')

  return (
    <div className="relative pl-8 pb-5 last:pb-0">
      {/* Timeline line */}
      {!isLast && (
        <div className="absolute left-[11px] top-6 bottom-0 w-px bg-border" />
      )}

      {/* Timeline dot */}
      <div className={cn(
        'absolute left-0 top-0.5 flex h-6 w-6 items-center justify-center rounded-full text-white',
        isVerdict || isExecution ? meta.color : 'bg-muted text-muted-foreground border border-border',
      )}>
        {meta.icon}
      </div>

      {/* Content */}
      <div className={cn(
        'rounded-lg border p-3',
        isVerdict ? 'border-border bg-card shadow-sm' : 'border-transparent',
      )}>
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            {/* Action + module */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className={cn(
                'text-sm font-medium',
                isVerdict ? 'text-foreground' : 'text-foreground/80',
              )}>
                {formatAction(event.action)}
              </span>
              <span className="text-[10px] text-muted-foreground px-1.5 py-0.5 bg-muted rounded">
                {meta.label}
              </span>
              {event.actor && (
                <span className="text-[10px] text-muted-foreground px-1.5 py-0.5 bg-muted rounded">
                  {event.actor}
                </span>
              )}
            </div>

            {/* Rationale */}
            {event.rationale && (
              <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
                {event.rationale}
              </p>
            )}

            {/* Hash — subtle */}
            {event.hash && (
              <p className="mt-1 flex items-center gap-1 font-mono text-[9px] text-muted-foreground/40">
                <Hash className="h-2.5 w-2.5" /> {event.hash.slice(0, 12)}
              </p>
            )}
          </div>

          <span className="text-[10px] text-muted-foreground/50 shrink-0 font-mono">
            #{event.seq}
          </span>
        </div>

        {/* Expandable details */}
        {hasData && (
          <>
            <button
              onClick={() => setExpanded((e) => !e)}
              className="mt-2 flex items-center gap-1 text-[11px] text-primary hover:text-primary/80 transition-colors font-medium"
            >
              {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              {expanded ? 'Hide' : 'View'} details
            </button>
            {expanded && (
              <div className="mt-2.5 space-y-3">
                <DataTable data={event.inputs} label="Inputs" />
                <DataTable data={event.outputs} label="Outputs" />
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export function AuditSheet({ invoiceId, open, onOpenChange }: AuditSheetProps) {
  const [data, setData] = useState<AuditResponse | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open || !invoiceId) return
    setLoading(true)
    setData(null)
    getAudit(invoiceId)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [open, invoiceId])

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-xl flex flex-col gap-0 p-0">
        <SheetHeader className="px-5 py-4 border-b border-border">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Shield className="h-4 w-4" />
            </div>
            <div>
              <SheetTitle className="text-base">Audit Trail</SheetTitle>
              <SheetDescription className="text-xs">
                {invoiceId && (
                  <span className="font-mono">{invoiceId}</span>
                )}
              </SheetDescription>
            </div>
          </div>
          {data && (
            <div className="flex items-center gap-2 mt-3">
              <Badge
                variant={data.chain_verified ? 'success' : 'destructive'}
                className="text-[10px] gap-1"
              >
                {data.chain_verified ? (
                  <><CheckCircle2 className="h-2.5 w-2.5" /> Chain verified</>
                ) : (
                  <><Shield className="h-2.5 w-2.5" /> Chain invalid</>
                )}
              </Badge>
              <span className="text-[11px] text-muted-foreground">
                {data.events.length} event{data.events.length !== 1 ? 's' : ''}
              </span>
            </div>
          )}
        </SheetHeader>

        <ScrollArea className="flex-1 px-5 py-4">
          {loading && (
            <div className="space-y-5">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex gap-3 pl-8">
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-4 w-2/3" />
                    <Skeleton className="h-3 w-1/2" />
                  </div>
                </div>
              ))}
            </div>
          )}
          {!loading && data && (
            <div>
              {data.events.map((event, i) => (
                <EventRow
                  key={event.seq}
                  event={event}
                  isLast={i === data.events.length - 1}
                />
              ))}
            </div>
          )}
          {!loading && !data && (
            <p className="text-sm text-muted-foreground text-center py-12">No audit data available.</p>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
