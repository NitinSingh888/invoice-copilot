import { Sun, Moon, RotateCcw, BookOpen, Zap } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip'
import type { Role } from '@/lib/types'

interface TopBarProps {
  theme: 'light' | 'dark'
  onThemeToggle: () => void
  role: Role
  onRoleToggle: () => void
  autoClearLimit: number
  onAutoClearChange: (v: number) => void
  onReset: () => void
  onRulesOpen: () => void
  resetting: boolean
}

export function TopBar({
  theme,
  onThemeToggle,
  role,
  onRoleToggle,
  autoClearLimit,
  onAutoClearChange,
  onReset,
  onRulesOpen,
  resetting,
}: TopBarProps) {
  return (
    <TooltipProvider>
      <header className="flex items-center justify-between gap-3 px-4 h-12 border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 shrink-0 z-10">
        {/* Brand */}
        <div className="flex items-center gap-2">
          <Zap className="h-4 w-4 text-primary" />
          <span className="font-semibold text-sm text-foreground tracking-tight">
            Invoice Copilot
          </span>
          <span className="text-[10px] font-mono text-muted-foreground border border-border rounded px-1.5 py-0.5 hidden sm:inline">
            mock-safe · v1
          </span>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Auto-clear slider */}
          <div className="hidden md:flex items-center gap-2">
            <span className="text-[11px] text-muted-foreground whitespace-nowrap">
              Auto-clear ≤{' '}
              <span className="font-mono text-foreground">${autoClearLimit.toLocaleString()}</span>
            </span>
            <Slider
              min={1000}
              max={100000}
              step={1000}
              value={[autoClearLimit]}
              onValueChange={([v]) => onAutoClearChange(v)}
              className="w-24"
            />
          </div>

          {/* Role toggle */}
          <Tooltip>
            <TooltipTrigger asChild>
              <div
                className="flex items-center gap-0.5 border border-border rounded-md h-7 p-0.5 cursor-pointer select-none"
                onClick={onRoleToggle}
              >
                <button
                  className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                    role === 'maya'
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Maya
                </button>
                <button
                  className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                    role === 'priya'
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  Priya
                </button>
              </div>
            </TooltipTrigger>
            <TooltipContent>Acting role for approvals</TooltipContent>
          </Tooltip>

          {/* Rules */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={onRulesOpen} className="h-7 w-7">
                <BookOpen className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Learned rules</TooltipContent>
          </Tooltip>

          {/* Theme toggle */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="ghost" size="icon" onClick={onThemeToggle} className="h-7 w-7">
                {theme === 'dark' ? (
                  <Sun className="h-3.5 w-3.5" />
                ) : (
                  <Moon className="h-3.5 w-3.5" />
                )}
              </Button>
            </TooltipTrigger>
            <TooltipContent>Toggle theme</TooltipContent>
          </Tooltip>

          {/* Reset */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={onReset}
                disabled={resetting}
                className="h-7 w-7"
              >
                <RotateCcw className={`h-3.5 w-3.5 ${resetting ? 'animate-spin' : ''}`} />
              </Button>
            </TooltipTrigger>
            <TooltipContent>Reset demo</TooltipContent>
          </Tooltip>
        </div>
      </header>
    </TooltipProvider>
  )
}
