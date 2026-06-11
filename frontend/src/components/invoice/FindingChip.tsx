import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Badge } from '@/components/ui/badge'
import { displayFinding, FINDING_EXPLANATIONS } from '@/lib/utils'
import type { Finding, FindingDisplay } from '@/lib/types'

interface FindingChipProps {
  /** Pass either a raw Finding (from the API) or a pre-computed FindingDisplay */
  finding: Finding | FindingDisplay
}

function isFindingDisplay(f: Finding | FindingDisplay): f is FindingDisplay {
  return 'label' in f && 'severity' in f
}

export function FindingChip({ finding }: FindingChipProps) {
  const display = isFindingDisplay(finding)
    ? finding
    : displayFinding(finding.code, finding.detail)

  const explanation = FINDING_EXPLANATIONS[display.code] ?? display.detail ?? null

  if (!explanation) {
    return (
      <Badge variant={display.severity} className="text-[10px] cursor-default">
        {display.label}
      </Badge>
    )
  }

  return (
    <Popover>
      <PopoverTrigger asChild>
        <button type="button" className="focus:outline-none">
          <Badge
            variant={display.severity}
            className="text-[10px] cursor-pointer hover:opacity-80 transition-opacity underline-offset-2 hover:underline"
          >
            {display.label}
          </Badge>
        </button>
      </PopoverTrigger>
      <PopoverContent className="text-xs leading-relaxed" side="top">
        <p className="font-semibold text-foreground mb-1">{display.label}</p>
        <p className="text-muted-foreground">{explanation}</p>
        {display.detail && display.detail !== explanation && (
          <p className="mt-1.5 font-mono text-[10px] text-muted-foreground/70 border-t border-border pt-1.5">
            {display.detail}
          </p>
        )}
      </PopoverContent>
    </Popover>
  )
}
