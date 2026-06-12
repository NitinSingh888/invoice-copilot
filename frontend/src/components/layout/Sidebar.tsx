import { useState } from 'react'
import { LayoutDashboard, Inbox, BookOpen, ScrollText, Sun, Moon, RotateCcw, GraduationCap, History, LogOut, Users } from 'lucide-react'
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { TeamDialog } from './TeamDialog'
import type { Role, OrgRole } from '@/lib/types'

export type View = 'dashboard' | 'inbox' | 'history' | 'rules' | 'audit' | 'guide'

interface SidebarProps {
  view: View
  onViewChange: (v: View) => void
  inboxCount: number
  theme: 'light' | 'dark'
  onThemeToggle: () => void
  role: Role
  onRoleToggle: () => void
  onReset: () => void
  resetting: boolean
  providerLabel: string
  providerLive: boolean
  userEmail?: string
  orgName?: string | null
  orgRole?: OrgRole | null
  onLogout?: () => void
}

const NAV = [
  { id: 'dashboard' as View, label: 'Dashboard', Icon: LayoutDashboard },
  { id: 'inbox' as View, label: 'Inbox', Icon: Inbox },
  { id: 'history' as View, label: 'History', Icon: History },
  { id: 'rules' as View, label: 'Rules', Icon: BookOpen },
]

export function Sidebar({
  view,
  onViewChange,
  inboxCount,
  theme,
  onThemeToggle,
  role,
  onRoleToggle,
  onReset,
  resetting,
  providerLabel,
  providerLive,
  userEmail,
  orgName,
  orgRole,
  onLogout,
}: SidebarProps) {
  const [teamOpen, setTeamOpen] = useState(false)
  const isAdmin = orgRole === 'admin'

  return (
    <TooltipProvider>
      <aside
        className="w-[220px] shrink-0 flex flex-col h-full bg-card border-r border-border select-none"
        data-tour="sidebar"
      >
        {/* Brand */}
        <div className="flex items-center gap-2.5 px-4 py-4 border-b border-border">
          {/* SVG Logo mark */}
          <div className="shrink-0">
            <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="28" height="28" rx="7" fill="hsl(var(--primary))" />
              {/* Receipt body */}
              <rect x="7" y="6" width="14" height="16" rx="2" fill="white" fillOpacity="0.15" />
              <rect x="7" y="6" width="14" height="16" rx="2" stroke="white" strokeOpacity="0.6" strokeWidth="1.2" />
              {/* Receipt lines */}
              <line x1="10" y1="11" x2="18" y2="11" stroke="white" strokeOpacity="0.7" strokeWidth="1.2" strokeLinecap="round" />
              <line x1="10" y1="14" x2="16" y2="14" stroke="white" strokeOpacity="0.5" strokeWidth="1.2" strokeLinecap="round" />
              <line x1="10" y1="17" x2="14" y2="17" stroke="white" strokeOpacity="0.5" strokeWidth="1.2" strokeLinecap="round" />
              {/* Spark check */}
              <circle cx="20" cy="20" r="5" fill="hsl(var(--primary))" />
              <circle cx="20" cy="20" r="5" stroke="hsl(var(--card))" strokeWidth="1.5" />
              <path d="M17.5 20L19.2 21.7L22.5 18.5" stroke="white" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </div>
          <div>
            <span className="text-sm font-semibold text-foreground tracking-tight leading-none block">
              Invoice Copilot
            </span>
            <span className="text-[10px] text-muted-foreground leading-none mt-0.5 block">
              AI accounts-payable assistant
            </span>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-3 px-2 space-y-0.5">
          {NAV.map(({ id, label, Icon }) => {
            const isActive = view === id
            return (
              <button
                key={id}
                onClick={() => onViewChange(id)}
                className={cn(
                  'relative w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-all duration-150',
                  'group',
                  isActive
                    ? 'bg-accent text-accent-foreground'
                    : 'text-muted-foreground hover:text-foreground hover:bg-muted/60',
                )}
              >
                {/* Active left indicator */}
                {isActive && (
                  <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-r-full bg-primary" />
                )}
                <Icon className={cn('h-4 w-4 shrink-0', isActive ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground')} />
                <span className="flex-1 text-left">{label}</span>
                {id === 'inbox' && inboxCount > 0 && (
                  <span className={cn(
                    'flex items-center justify-center h-4.5 min-w-[18px] px-1 rounded-full text-[10px] font-semibold leading-none',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-warning/20 text-[hsl(var(--warning))]'
                  )}>
                    {inboxCount}
                  </span>
                )}
              </button>
            )
          })}

          <div className="pt-2 pb-1">
            <div className="h-px bg-border" />
          </div>

          <button
            onClick={() => onViewChange('audit')}
            className={cn(
              'relative w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-all duration-150',
              'group',
              view === 'audit'
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/60',
            )}
          >
            {view === 'audit' && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-r-full bg-primary" />
            )}
            <ScrollText className={cn('h-4 w-4 shrink-0', view === 'audit' ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground')} />
            <span>Audit Log</span>
          </button>

          {/* Guide nav item */}
          <button
            data-tour="guide-nav"
            onClick={() => onViewChange('guide')}
            className={cn(
              'relative w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-all duration-150',
              'group',
              view === 'guide'
                ? 'bg-accent text-accent-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/60',
            )}
          >
            {view === 'guide' && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-r-full bg-primary" />
            )}
            <GraduationCap className={cn('h-4 w-4 shrink-0', view === 'guide' ? 'text-primary' : 'text-muted-foreground group-hover:text-foreground')} />
            <span>Guide</span>
          </button>

          {/* Admin-only: Team */}
          {isAdmin && (
            <button
              onClick={() => setTeamOpen(true)}
              className={cn(
                'relative w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm font-medium transition-all duration-150',
                'group text-muted-foreground hover:text-foreground hover:bg-muted/60',
              )}
            >
              <Users className="h-4 w-4 shrink-0 text-muted-foreground group-hover:text-foreground" />
              <span>Team</span>
            </button>
          )}
        </nav>

        {/* Bottom: role switcher + theme + reset */}
        <div className="border-t border-border p-3 space-y-2">
          {/* Role switcher */}
          <div className="flex items-center gap-1 bg-muted rounded-md p-0.5">
            {(['maya', 'priya'] as Role[]).map((r) => (
              <button
                key={r}
                onClick={() => r !== role && onRoleToggle()}
                className={cn(
                  'flex-1 py-1.5 rounded text-xs font-medium transition-all duration-150 capitalize',
                  role === r
                    ? 'bg-card text-foreground shadow-sm'
                    : 'text-muted-foreground hover:text-foreground',
                )}
              >
                {r}
              </button>
            ))}
          </div>

          {/* Theme + Reset row */}
          <div className="flex items-center gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={onThemeToggle}
                  className="flex-1 flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md text-xs text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-all duration-150"
                >
                  {theme === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
                  <span>{theme === 'dark' ? 'Light' : 'Dark'}</span>
                </button>
              </TooltipTrigger>
              <TooltipContent side="top">Toggle theme</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={onReset}
                  disabled={resetting}
                  className="flex items-center justify-center p-2 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/60 transition-all duration-150 disabled:opacity-50"
                >
                  <RotateCcw className={cn('h-3.5 w-3.5', resetting && 'animate-spin')} />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top">Reset demo</TooltipContent>
            </Tooltip>
          </div>

          {/* Logged-in user + org + role + logout */}
          {userEmail && (
            <div className="flex items-start gap-1.5 px-1">
              <div className="flex-1 min-w-0">
                <span
                  className="block truncate text-[10px] text-muted-foreground font-mono leading-tight"
                  title={userEmail}
                >
                  {userEmail}
                </span>
                {(orgName || orgRole) && (
                  <span className="block truncate text-[10px] text-muted-foreground leading-tight mt-0.5">
                    {[orgName, orgRole].filter(Boolean).join(' · ')}
                  </span>
                )}
              </div>
              {onLogout && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={onLogout}
                      className="flex items-center justify-center p-1 rounded text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all duration-150 shrink-0 mt-0.5"
                      aria-label="Log out"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="top">Log out</TooltipContent>
                </Tooltip>
              )}
            </div>
          )}

          {/* Provider pill — driven from health endpoint */}
          <div className="flex justify-center">
            <span className="flex items-center gap-1.5 text-[10px] font-mono text-muted-foreground border border-border rounded px-2 py-0.5">
              <span className={cn(
                'h-1.5 w-1.5 rounded-full shrink-0',
                providerLive ? 'bg-[hsl(var(--success))]' : 'bg-muted-foreground',
              )} />
              {providerLabel}
            </span>
          </div>
        </div>
      </aside>

      <TeamDialog open={teamOpen} onOpenChange={setTeamOpen} />
    </TooltipProvider>
  )
}
