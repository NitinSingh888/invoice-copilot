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
  Link as LinkIcon,
  ChevronDown,
  ChevronRight,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Skeleton } from '@/components/ui/skeleton'
import { PageHeader } from '@/components/layout/PageHeader'
import { getAuditLog } from '@/lib/api'
import type { AuditEvent, AuditResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

function moduleIcon(module: string) {
  switch (module) {
    case 'extraction': return <FileText className="h-3.5 w-3.5" />
    case 'enrichment': return <Link2 className="h-3.5 w-3.5" />
    case 'policy': return <Flag className="h-3.5 w-3.5" />
    case 'guard': return <Shield className="h-3.5 w-3.5" />
    case 'execution': return <CheckCircle2 className="h-3.5 w-3.5" />
    case 'learning': return <Sparkles className="h-3.5 w-3.5" />
    case 'human': return <User className="h-3.5 w-3.5" />
    default: return <Brain className="h-3.5 w-3.5" />
  }
}

function EventRow({ event }: { event: AuditEvent }) {
  const [expanded, setExpanded] = useState(false)

  const hasData =
    Object.keys(event.inputs).length > 0 || Object.keys(event.outputs).length > 0

  return (
    <div className="relative pl-6 pb-4 last:pb-0">
      {/* timeline line */}
      <div className="absolute left-2 top-0 bottom-0 w-px bg-border" />
      {/* dot */}
      <div className="absolute left-0 top-0.5 flex h-4 w-4 items-center justify-center rounded-full border border-border bg-card text-muted-foreground">
        {moduleIcon(event.module)}
      </div>

      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-medium text-foreground">{event.action}</span>
            <span className="text-xs text-muted-foreground">·</span>
            <span className="text-xs text-muted-foreground">{event.module}</span>
            {event.actor && (
              <>
                <span className="text-xs text-muted-foreground">·</span>
                <Badge variant="secondary" className="text-[10px] py-0 h-4">
                  {event.actor}
                </Badge>
              </>
            )}
            {event.invoice_id && (
              <>
                <span className="text-xs text-muted-foreground">·</span>
                <span className="font-mono text-[10px] text-muted-foreground">{event.invoice_id}</span>
              </>
            )}
          </div>
          {event.rationale && (
            <p className="mt-1 text-xs text-muted-foreground leading-relaxed">{event.rationale}</p>
          )}
          {event.model_meta && event.model_meta.provider != null && (
            <p className="mt-1 font-mono text-[10px] text-muted-foreground">
              {String(event.model_meta.provider)}/{String(event.model_meta.model ?? '')}
              {event.model_meta.confidence != null && ` · conf ${String(event.model_meta.confidence)}`}
            </p>
          )}
          {event.hash && (
            <p className="mt-1 flex items-center gap-1 font-mono text-[10px] text-muted-foreground/70">
              <LinkIcon className="h-2.5 w-2.5" /> {event.hash.slice(0, 16)}…
            </p>
          )}
          {hasData && (
            <button
              onClick={() => setExpanded((e) => !e)}
              className="mt-1.5 flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
            >
              {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
              {expanded ? 'Hide' : 'Show'} details
            </button>
          )}
          {expanded && hasData && (
            <div className="mt-2 space-y-2">
              {Object.keys(event.inputs).length > 0 && (
                <div>
                  <p className="text-[10px] font-medium text-muted-foreground mb-1">INPUTS</p>
                  <pre className="text-[10px] bg-muted rounded p-2 overflow-x-auto text-foreground font-mono">
                    {JSON.stringify(event.inputs, null, 2)}
                  </pre>
                </div>
              )}
              {Object.keys(event.outputs).length > 0 && (
                <div>
                  <p className="text-[10px] font-medium text-muted-foreground mb-1">OUTPUTS</p>
                  <pre className="text-[10px] bg-muted rounded p-2 overflow-x-auto text-foreground font-mono">
                    {JSON.stringify(event.outputs, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
        <span className="text-[10px] text-muted-foreground shrink-0 font-mono">
          #{event.seq}
        </span>
      </div>
    </div>
  )
}

interface AuditLogProps {
  live?: boolean | null
}

export function AuditLog({ live }: AuditLogProps) {
  const [data, setData] = useState<AuditResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getAuditLog()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="flex flex-col h-full overflow-hidden">
      <PageHeader
        title="Audit Log"
        subtitle="Every action, hash-chained and verifiable"
        live={live}
        actions={
          data ? (
            <Badge
              variant={data.chain_verified ? 'success' : 'destructive'}
              className="text-[10px]"
            >
              <CheckCircle2 className="h-2.5 w-2.5 mr-1" />
              {data.chain_verified ? 'Chain verified' : 'Chain invalid'}
            </Badge>
          ) : undefined
        }
      />

      <ScrollArea className="flex-1 p-6">
        {loading && (
          <div className="space-y-4 max-w-2xl mx-auto">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex gap-3">
                <Skeleton className="h-4 w-4 rounded-full shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <Skeleton className="h-3 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && data && data.events.length > 0 && (
          <div className={cn('relative max-w-2xl mx-auto')}>
            {data.events.map((event) => (
              <EventRow key={`${event.seq}-${event.invoice_id}`} event={event} />
            ))}
          </div>
        )}

        {!loading && (!data || data.events.length === 0) && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="h-14 w-14 rounded-xl bg-muted flex items-center justify-center mb-4">
              <Shield className="h-7 w-7 text-muted-foreground" />
            </div>
            <h3 className="text-base font-semibold text-foreground">No audit events yet</h3>
            <p className="text-sm text-muted-foreground mt-2 max-w-sm">
              Process some invoices — every agent action is recorded here with a hash-chained trail.
            </p>
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
