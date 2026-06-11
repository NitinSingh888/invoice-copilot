import { useRef, useEffect } from 'react'
import { Clock, X } from 'lucide-react'
import { minutesSaved } from '@/lib/utils'
import { cn } from '@/lib/utils'

interface PageHeaderProps {
  title: string
  subtitle?: string
  savedCount?: number
  className?: string
  actions?: React.ReactNode
  /** Show the live/offline indicator */
  live?: boolean | null
  /** Show a real search input (Inbox only) */
  showSearch?: boolean
  searchQuery?: string
  onSearchChange?: (q: string) => void
}

export function PageHeader({
  title,
  subtitle,
  savedCount,
  className,
  actions,
  live,
  showSearch,
  searchQuery,
  onSearchChange,
}: PageHeaderProps) {
  const hours = savedCount !== undefined ? (minutesSaved(savedCount) / 60).toFixed(1) : null
  const inputRef = useRef<HTMLInputElement>(null)

  // Wire ⌘K to focus the search input when it is rendered
  useEffect(() => {
    if (!showSearch) return
    function handler(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        inputRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [showSearch])

  return (
    <div className={cn('flex items-center justify-between gap-4 px-6 py-4 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shrink-0', className)}>
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-foreground leading-none">{title}</h1>
        {subtitle && (
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>

      <div className="flex items-center gap-3 shrink-0">
        {/* Real search input — Inbox only */}
        {showSearch && (
          <div className="hidden sm:flex items-center gap-2 h-8 px-3 rounded-md border border-border bg-muted/40 text-muted-foreground text-xs focus-within:border-primary/50 focus-within:bg-background transition-colors">
            <svg className="h-3.5 w-3.5 shrink-0" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="6.5" cy="6.5" r="4" />
              <path d="M10 10l3 3" strokeLinecap="round" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={searchQuery ?? ''}
              onChange={(e) => onSearchChange?.(e.target.value)}
              placeholder="Search vendor, ID, PO…"
              className="bg-transparent outline-none placeholder:text-muted-foreground text-foreground w-36 md:w-48"
            />
            {searchQuery && (
              <button
                onClick={() => onSearchChange?.('')}
                className="ml-1 text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Clear search"
              >
                <X className="h-3 w-3" />
              </button>
            )}
            <span className="hidden md:inline font-mono text-[10px] opacity-60 shrink-0">⌘K</span>
          </div>
        )}

        {/* Time saved stat */}
        {hours !== null && parseFloat(hours) > 0 && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="h-3.5 w-3.5 text-[hsl(var(--success))]" />
            <span className="font-medium text-[hsl(var(--success))]">~{hours}h saved today</span>
          </div>
        )}

        {/* Live/Offline indicator — driven from health state */}
        {live !== undefined && (
          <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
            <span className={cn(
              'h-1.5 w-1.5 rounded-full',
              live === null
                ? 'bg-muted-foreground'
                : live
                ? 'bg-[hsl(var(--success))] animate-pulse'
                : 'bg-amber-500',
            )} />
            <span>{live === null ? 'Connecting…' : live ? 'Live' : 'Offline'}</span>
          </div>
        )}

        {actions}
      </div>
    </div>
  )
}
