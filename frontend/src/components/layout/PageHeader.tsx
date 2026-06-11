import { Clock } from 'lucide-react'
import { minutesSaved } from '@/lib/utils'
import { cn } from '@/lib/utils'

interface PageHeaderProps {
  title: string
  subtitle?: string
  savedCount?: number
  className?: string
  actions?: React.ReactNode
}

export function PageHeader({ title, subtitle, savedCount, className, actions }: PageHeaderProps) {
  const hours = savedCount !== undefined ? (minutesSaved(savedCount) / 60).toFixed(1) : null

  return (
    <div className={cn('flex items-center justify-between gap-4 px-6 py-4 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shrink-0', className)}>
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground leading-none">{title}</h1>
        {subtitle && (
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-3 shrink-0">
        {/* Search (cosmetic) */}
        <div className="hidden sm:flex items-center gap-2 h-8 px-3 rounded-md border border-border bg-muted/40 text-muted-foreground text-xs">
          <svg className="h-3.5 w-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <circle cx="6.5" cy="6.5" r="4" />
            <path d="M10 10l3 3" strokeLinecap="round" />
          </svg>
          <span>Search…</span>
          <span className="hidden md:inline font-mono text-[10px] opacity-60">⌘K</span>
        </div>

        {/* Time saved stat */}
        {hours !== null && parseFloat(hours) > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5 text-[hsl(var(--success))]" />
            <span className="font-medium text-[hsl(var(--success))]">~{hours}h saved today</span>
          </div>
        )}

        {/* Live/mock indicator */}
        <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-[hsl(var(--success))] animate-pulse" />
          <span>Live</span>
        </div>

        {actions}
      </div>
    </div>
  )
}
