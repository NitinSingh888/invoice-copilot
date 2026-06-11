import { useState } from 'react'
import { Sparkles, Check, X, Pencil } from 'lucide-react'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { activateRule } from '@/lib/api'
import type { RuleProposeResponse, RuleOut } from '@/lib/types'

interface LearnedRuleCardProps {
  proposal: RuleProposeResponse
  onApproved: (rule: RuleOut) => void
  onDismiss: () => void
}

export function LearnedRuleCard({ proposal, onApproved, onDismiss }: LearnedRuleCardProps) {
  const { candidate, threshold_pct, route } = proposal
  // Stored as a fraction (0.08); shown/edited as a percent (8).
  const [editThreshold, setEditThreshold] = useState(String(+(threshold_pct * 100).toFixed(2)))
  const [editRoute, setEditRoute] = useState(route ?? '')
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleApprove() {
    setLoading(true)
    try {
      const rule = await activateRule({
        threshold_pct: (parseFloat(editThreshold) || threshold_pct * 100) / 100,
        route: editRoute || null,
      })
      onApproved(rule)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="border-primary/30 bg-accent/30 shadow-none">
      <CardHeader className="pb-2">
        <div className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          <span className="text-xs font-semibold text-foreground">A pattern in how you decide</span>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* WHEN / THEN */}
        <div className="space-y-1.5 text-xs">
          <div className="flex gap-2 items-start">
            <span className="font-semibold text-muted-foreground w-10 shrink-0 text-[10px] pt-0.5">WHEN</span>
            <div className="flex-1">
              <span className="text-foreground">
                {candidate.vendor ? `Vendor is ${candidate.vendor}` : 'Any vendor'}
                {' '}and invoice exceeds PO by ≤{' '}
              </span>
              {editing ? (
                <Input
                  className="inline-block w-16 h-5 text-xs px-1.5 font-mono"
                  value={editThreshold}
                  onChange={(e) => setEditThreshold(e.target.value)}
                />
              ) : (
                <span className="font-mono font-medium text-primary">
                  {editThreshold}%
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-2 items-start">
            <span className="font-semibold text-muted-foreground w-10 shrink-0 text-[10px] pt-0.5">THEN</span>
            <div className="flex-1">
              {editing ? (
                <Input
                  className="inline-block w-32 h-5 text-xs px-1.5"
                  value={editRoute}
                  onChange={(e) => setEditRoute(e.target.value)}
                  placeholder="auto-approve"
                />
              ) : (
                <span className="text-foreground">
                  {editRoute ? `Route to ${editRoute}` : 'Auto-approve'}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Evidence chips */}
        {candidate.example_ids.length > 0 && (
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[10px] text-muted-foreground">From:</span>
            {candidate.example_ids.slice(0, 4).map((id) => (
              <Badge key={id} variant="secondary" className="text-[10px] font-mono">
                {id}
              </Badge>
            ))}
            {candidate.example_ids.length > 4 && (
              <span className="text-[10px] text-muted-foreground">
                +{candidate.example_ids.length - 4} more
              </span>
            )}
          </div>
        )}

        {/* Actions */}
        <div className="flex items-center gap-2 pt-1">
          <Button
            size="sm"
            onClick={handleApprove}
            disabled={loading}
            className="h-7 text-xs"
          >
            {loading ? (
              <span className="animate-pulse">Saving…</span>
            ) : (
              <>
                <Check className="h-3 w-3" />
                Approve rule
              </>
            )}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setEditing((e) => !e)}
            disabled={loading}
            className="h-7 text-xs"
          >
            <Pencil className="h-3 w-3" />
            {editing ? 'Done' : 'Edit'}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDismiss}
            disabled={loading}
            className="h-7 text-xs text-muted-foreground ml-auto"
          >
            <X className="h-3 w-3" />
            Dismiss
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
