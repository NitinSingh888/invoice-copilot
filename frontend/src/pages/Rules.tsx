import { useEffect, useState } from 'react'
import { BookOpen, Plus, ToggleLeft } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import { ShieldCheck } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { listRules, patchRule, createRule, getPolicy, updatePolicy, type Policy } from '@/lib/api'
import type { RuleOut, OrgRole } from '@/lib/types'

// ─── PolicyCard ─ the editable default auto-approve rule ─────────────────────

function PolicyCard({ isAdmin }: { isAdmin: boolean }) {
  const [policy, setPolicy] = useState<Policy | null>(null)
  const [threshold, setThreshold] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    getPolicy()
      .then((p) => {
        setPolicy(p)
        setThreshold(String(parseFloat(p.auto_approve_threshold)))
      })
      .catch(console.error)
  }, [])

  async function save(next: Partial<Policy>) {
    setSaving(true)
    try {
      const updated = await updatePolicy(next)
      setPolicy(updated)
      setThreshold(String(parseFloat(updated.auto_approve_threshold)))
      toast.success('Auto-approve policy updated')
    } catch (err) {
      toast.error(`Couldn't update policy: ${(err as Error).message}`)
    } finally {
      setSaving(false)
    }
  }

  if (!policy) return null
  const enabled = policy.auto_approve_enabled

  return (
    <div className="rounded-lg border border-primary/30 bg-primary/5 p-4 mb-6">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-primary" />
          <div>
            <div className="text-sm font-semibold text-foreground">Default auto-approve policy</div>
            <div className="text-xs text-muted-foreground">
              Applied to every invoice before any learned rule.
            </div>
          </div>
        </div>
        <Switch
          checked={enabled}
          disabled={!isAdmin || saving}
          onCheckedChange={(v) => save({ auto_approve_enabled: v })}
        />
      </div>

      <p className="text-sm text-foreground mt-3">
        {enabled ? (
          <>
            Auto-approve a clean invoice — approved vendor, matched PO, no flags, high confidence —
            when it&apos;s under{' '}
            <span className="font-semibold tabular-nums">${parseFloat(policy.auto_approve_threshold).toLocaleString()}</span>.
            Anything above, or with any flag, goes to a person. Amount is never the only check.
          </>
        ) : (
          <>Auto-approve is <span className="font-semibold">off</span> — every invoice is sent to a person.</>
        )}
      </p>

      {isAdmin ? (
        <div className="flex items-end gap-2 mt-3">
          <div className="space-y-1">
            <label className="text-[11px] font-medium text-muted-foreground" htmlFor="policy-threshold">
              Auto-approve limit (USD)
            </label>
            <Input
              id="policy-threshold"
              type="number"
              min="0"
              step="1"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              className="h-8 w-32"
              disabled={!enabled || saving}
            />
          </div>
          <Button
            size="sm"
            className="h-8 text-xs"
            disabled={!enabled || saving || threshold === ''}
            onClick={() => save({ auto_approve_threshold: threshold })}
          >
            Save limit
          </Button>
        </div>
      ) : (
        <p className="text-[11px] text-muted-foreground mt-2">Only an admin can change this policy.</p>
      )}
    </div>
  )
}

// ─── RuleCard ────────────────────────────────────────────────────────────────

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

// ─── CreateRuleDialog ────────────────────────────────────────────────────────

type Condition = 'over_pct' | 'any'
type RouteOption = 'priya' | 'hold' | 'auto_approve'

interface CreateRuleDialogProps {
  open: boolean
  onOpenChange: (v: boolean) => void
  onCreated: (rule: RuleOut) => void
}

function CreateRuleDialog({ open, onOpenChange, onCreated }: CreateRuleDialogProps) {
  const [vendor, setVendor] = useState('')
  const [condition, setCondition] = useState<Condition>('over_pct')
  const [overPct, setOverPct] = useState('5')
  const [route, setRoute] = useState<RouteOption>('priya')
  const [submitting, setSubmitting] = useState(false)

  function reset() {
    setVendor('')
    setCondition('over_pct')
    setOverPct('5')
    setRoute('priya')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!vendor.trim()) {
      toast.error('Vendor name is required')
      return
    }
    setSubmitting(true)
    try {
      const body = {
        vendor: vendor.trim(),
        finding_code: condition === 'over_pct' ? 'OVER_TOLERANCE' : undefined,
        max_over_pct:
          condition === 'over_pct' ? parseFloat(overPct) / 100 : null,
        route:
          route === 'priya'
            ? 'priya'
            : route === 'hold'
            ? 'hold'
            : 'auto_approve',
      }
      const created = await createRule(body)
      toast.success(`Rule created for ${vendor.trim()}`)
      onCreated(created)
      reset()
      onOpenChange(false)
    } catch (err) {
      toast.error(`Failed to create rule: ${(err as Error).message}`)
    } finally {
      setSubmitting(false)
    }
  }

  function handleOpenChange(v: boolean) {
    if (!v) reset()
    onOpenChange(v)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base">Create rule</DialogTitle>
          <DialogDescription>
            Tell Copilot how to handle invoices from a specific vendor automatically.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Vendor */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground" htmlFor="rule-vendor">
              Vendor
            </label>
            <Input
              id="rule-vendor"
              placeholder="e.g. Acme Corp"
              value={vendor}
              onChange={(e) => setVendor(e.target.value)}
              required
            />
          </div>

          {/* Condition */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground" htmlFor="rule-condition">
              Condition
            </label>
            <select
              id="rule-condition"
              value={condition}
              onChange={(e) => setCondition(e.target.value as Condition)}
              className="w-full h-9 rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            >
              <option value="over_pct">Invoice is over its PO by more than X%</option>
              <option value="any">Any invoice from this vendor</option>
            </select>
          </div>

          {/* Percent input — only when condition = over_pct */}
          {condition === 'over_pct' && (
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-foreground" htmlFor="rule-pct">
                Over-PO threshold (%)
              </label>
              <div className="flex items-center gap-2">
                <Input
                  id="rule-pct"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  value={overPct}
                  onChange={(e) => setOverPct(e.target.value)}
                  className="w-24"
                />
                <span className="text-sm text-muted-foreground">percent</span>
              </div>
            </div>
          )}

          {/* Then */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-foreground" htmlFor="rule-then">
              Then
            </label>
            <select
              id="rule-then"
              value={route}
              onChange={(e) => setRoute(e.target.value as RouteOption)}
              className="w-full h-9 rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground shadow-sm focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
            >
              <option value="priya">Route to Priya</option>
              <option value="hold">Hold</option>
              <option value="auto_approve">Auto-approve</option>
            </select>
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={submitting}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create rule'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ─── Empty state ─────────────────────────────────────────────────────────────

function EmptyState({ onCreateClick }: { onCreateClick: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center max-w-sm mx-auto">
      <div className="h-14 w-14 rounded-xl bg-muted flex items-center justify-center mb-4">
        <BookOpen className="h-7 w-7 text-muted-foreground" />
      </div>
      <h3 className="text-base font-semibold text-foreground">No rules yet</h3>
      <p className="text-sm text-muted-foreground mt-2 leading-relaxed">
        Rules let Copilot handle repeat decisions automatically. Two ways to get one:
      </p>
      <ol className="text-sm text-muted-foreground mt-3 space-y-2 text-left w-full">
        <li className="flex gap-2.5">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary mt-0.5">
            1
          </span>
          <span>
            <strong className="text-foreground">Copilot learns</strong> — correct it the same
            way 3× and it proposes a rule you approve.
          </span>
        </li>
        <li className="flex gap-2.5">
          <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-[10px] font-bold text-primary mt-0.5">
            2
          </span>
          <span>
            <strong className="text-foreground">Create one</strong> — click{' '}
            <em>Create rule</em> to define a rule from scratch.
          </span>
        </li>
      </ol>
      <Button className="mt-6 gap-2" onClick={onCreateClick}>
        <Plus className="h-4 w-4" />
        Create rule
      </Button>
    </div>
  )
}

// ─── Rules page ──────────────────────────────────────────────────────────────

export function Rules({ orgRole }: { orgRole?: OrgRole | null }) {
  const [rules, setRules] = useState<RuleOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [createOpen, setCreateOpen] = useState(false)
  const isAdmin = orgRole === 'admin'

  useEffect(() => {
    setLoading(true)
    setError(null)
    listRules()
      .then(setRules)
      .catch((err) => {
        console.error(err)
        setError((err as Error).message ?? 'Failed to load rules')
      })
      .finally(() => setLoading(false))
  }, [])

  function handleToggle(id: string, status: 'active' | 'disabled') {
    patchRule(id, status)
      .then((updated) =>
        setRules((prev) => prev.map((r) => (r.id === updated.id ? updated : r))),
      )
      .catch(console.error)
  }

  function handleCreated(rule: RuleOut) {
    setRules((prev) => [rule, ...prev])
  }

  const active = rules.filter((r) => r.status === 'active').length

  return (
    <div className="flex flex-col h-full overflow-y-auto scrollbar-thin">
      <PageHeader
        title="Rules"
        subtitle="Your auto-approve policy, plus patterns Copilot learned from your decisions"
        actions={
          <Button size="sm" className="gap-1.5 h-8 text-xs" onClick={() => setCreateOpen(true)}>
            <Plus className="h-3.5 w-3.5" />
            Create rule
          </Button>
        }
      />

      <div className="flex-1 p-6">
        {/* Default auto-approve policy — the editable rule */}
        <PolicyCard isAdmin={isAdmin} />

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

        {/* Error */}
        {!loading && error && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="text-sm text-destructive font-medium mb-1">Failed to load rules</p>
            <p className="text-xs text-muted-foreground">{error}</p>
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
          <EmptyState onCreateClick={() => setCreateOpen(true)} />
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

      <CreateRuleDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={handleCreated}
      />
    </div>
  )
}
