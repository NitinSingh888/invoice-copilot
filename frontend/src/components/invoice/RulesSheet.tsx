import { useEffect, useState } from 'react'
import { BookOpen, ToggleLeft } from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Switch } from '@/components/ui/switch'
import { Skeleton } from '@/components/ui/skeleton'
import { listRules, patchRule } from '@/lib/api'
import type { RuleOut } from '@/lib/types'

interface RulesSheetProps {
  open: boolean
  onOpenChange: (v: boolean) => void
}

function RuleRow({ rule, onToggle }: { rule: RuleOut; onToggle: (id: string, status: 'active' | 'disabled') => void }) {
  const isActive = rule.status === 'active'

  return (
    <div className="border border-border rounded-md p-3 space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant={isActive ? 'success' : 'muted'} className="text-[10px]">
              {isActive ? 'Active' : 'Disabled'}
            </Badge>
            {rule.vendor && (
              <Badge variant="secondary" className="text-[10px]">
                {rule.vendor}
              </Badge>
            )}
          </div>
        </div>
        <Switch
          checked={isActive}
          onCheckedChange={(checked) =>
            onToggle(rule.id, checked ? 'active' : 'disabled')
          }
        />
      </div>

      <div className="space-y-1 text-xs">
        <div className="flex gap-2">
          <span className="font-medium text-muted-foreground w-10 shrink-0">WHEN</span>
          <span className="text-foreground">
            {rule.vendor ? `Vendor is ${rule.vendor}` : 'Any vendor'}
            {rule.max_over_pct != null && ` and invoice is over PO by ≤ ${rule.max_over_pct}%`}
            {rule.min_amount && ` and amount ≥ $${rule.min_amount}`}
          </span>
        </div>
        <div className="flex gap-2">
          <span className="font-medium text-muted-foreground w-10 shrink-0">THEN</span>
          <span className="text-foreground">
            {rule.route ? `Route to ${rule.route}` : 'Auto-approve'}
          </span>
        </div>
      </div>

      {rule.reasoning_note && (
        <p className="text-[11px] text-muted-foreground border-t border-border pt-2">
          {rule.reasoning_note}
        </p>
      )}

      {rule.source_correction_ids.length > 0 && (
        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-[10px] text-muted-foreground">Sources:</span>
          {rule.source_correction_ids.map((id) => (
            <Badge key={id} variant="secondary" className="text-[10px] font-mono">
              INV-{id}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}

export function RulesSheet({ open, onOpenChange }: RulesSheetProps) {
  const [rules, setRules] = useState<RuleOut[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    listRules()
      .then(setRules)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [open])

  function handleToggle(id: string, status: 'active' | 'disabled') {
    patchRule(id, status)
      .then((updated) =>
        setRules((prev) => prev.map((r) => (r.id === updated.id ? updated : r))),
      )
      .catch(console.error)
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-xl flex flex-col gap-0 p-0">
        <SheetHeader className="p-4 pb-3 border-b border-border">
          <SheetTitle className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-primary" />
            Learned Rules
          </SheetTitle>
          <SheetDescription>
            Rules inferred from your approval patterns. Toggle to enable or disable.
          </SheetDescription>
          {!loading && (
            <div className="flex items-center gap-1.5 mt-1">
              <ToggleLeft className="h-3 w-3 text-muted-foreground" />
              <span className="text-[11px] text-muted-foreground">
                {rules.filter((r) => r.status === 'active').length} active ·{' '}
                {rules.length} total
              </span>
            </div>
          )}
        </SheetHeader>

        <ScrollArea className="flex-1 p-4">
          {loading && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-24 w-full rounded-md" />
              ))}
            </div>
          )}
          {!loading && rules.length === 0 && (
            <div className="text-center py-8">
              <BookOpen className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
              <p className="text-xs text-muted-foreground">
                No learned rules yet. Approve invoices to train the system.
              </p>
            </div>
          )}
          {!loading && rules.length > 0 && (
            <div className="space-y-3">
              {rules.map((rule) => (
                <RuleRow key={rule.id} rule={rule} onToggle={handleToggle} />
              ))}
            </div>
          )}
        </ScrollArea>
      </SheetContent>
    </Sheet>
  )
}
