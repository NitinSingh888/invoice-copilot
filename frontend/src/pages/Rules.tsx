import { useEffect, useState } from 'react'
import { BookOpen, ToggleLeft } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { PageHeader } from '@/components/layout/PageHeader'
import { listRules, patchRule } from '@/lib/api'
import type { RuleOut } from '@/lib/types'

function RuleCard({
  rule,
  onToggle,
}: {
  rule: RuleOut
  onToggle: (id: string, status: 'active' | 'disabled') => void
}) {
  const isActive = rule.status === 'active'

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3 hover:shadow-sm transition-shadow duration-150">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={isActive ? 'success' : 'muted'} className="text-[10px]">
            {isActive ? 'Active' : 'Disabled'}
          </Badge>
          {rule.vendor && (
            <Badge variant="secondary" className="text-[10px]">{rule.vendor}</Badge>
          )}
        </div>
        <Switch
          checked={isActive}
          onCheckedChange={(checked) => onToggle(rule.id, checked ? 'active' : 'disabled')}
        />
      </div>

      <div className="space-y-2">
        <div className="flex gap-3 text-sm">
          <span className="shrink-0 w-10 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground pt-0.5">
            WHEN
          </span>
          <span className="text-foreground">
            {rule.vendor ? `Vendor is ${rule.vendor}` : 'Any vendor'}
            {rule.max_over_pct != null &&
              ` and invoice is over PO by ≤ ${+(parseFloat(String(rule.max_over_pct)) * 100).toFixed(2)}%`}
            {rule.min_amount && ` and amount ≥ $${rule.min_amount}`}
          </span>
        </div>
        <div className="flex gap-3 text-sm">
          <span className="shrink-0 w-10 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground pt-0.5">
            THEN
          </span>
          <span className="text-foreground">
            {rule.route ? `Route to ${rule.route}` : 'Auto-approve'}
          </span>
        </div>
      </div>

      {rule.reasoning_note && (
        <p className="text-xs text-muted-foreground border-t border-border pt-2.5 leading-relaxed">
          {rule.reasoning_note}
        </p>
      )}

      {rule.source_correction_ids.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
          <span className="text-[10px] text-muted-foreground">Sources:</span>
          {rule.source_correction_ids.map((id) => (
            <Badge key={id} variant="secondary" className="text-[10px] font-mono">
              {id}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}

export function Rules() {
  const [rules, setRules] = useState<RuleOut[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    listRules()
      .then(setRules)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  function handleToggle(id: string, status: 'active' | 'disabled') {
    patchRule(id, status)
      .then((updated) =>
        setRules((prev) => prev.map((r) => (r.id === updated.id ? updated : r))),
      )
      .catch(console.error)
  }

  const active = rules.filter((r) => r.status === 'active').length

  return (
    <div className="flex flex-col h-full overflow-y-auto scrollbar-thin">
      <PageHeader
        title="Rules"
        subtitle="Learned from your approval patterns"
      />

      <div className="flex-1 p-6">
        {/* Stats */}
        {!loading && rules.length > 0 && (
          <div className="flex items-center gap-2 mb-5 text-sm text-muted-foreground">
            <ToggleLeft className="h-4 w-4" />
            <span>
              <span className="font-medium text-foreground">{active}</span> active ·{' '}
              <span className="font-medium text-foreground">{rules.length}</span> total
            </span>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="grid gap-3 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-36 w-full rounded-lg" />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!loading && rules.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <div className="h-14 w-14 rounded-xl bg-muted flex items-center justify-center mb-4">
              <BookOpen className="h-7 w-7 text-muted-foreground" />
            </div>
            <h3 className="text-base font-semibold text-foreground">No rules yet</h3>
            <p className="text-sm text-muted-foreground mt-2 max-w-sm">
              No rules yet — correct the agent a few times and it'll propose one.
            </p>
          </div>
        )}

        {/* Rules grid */}
        {!loading && rules.length > 0 && (
          <div className="grid gap-3 grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
            {rules.map((rule) => (
              <RuleCard key={rule.id} rule={rule} onToggle={handleToggle} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
