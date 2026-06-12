import { useState, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { InboxIcon, CheckCircle2, UserCheck, Shield, HelpCircle, Map } from 'lucide-react'

const STORAGE_KEY = 'ic_intro_seen'

const STEPS = [
  {
    icon: <InboxIcon className="h-5 w-5" />,
    title: 'Hand it the batch',
    description:
      'Say "Process today\'s invoices" — the agent reads every invoice, extracts amounts, and matches purchase orders automatically.',
  },
  {
    icon: <CheckCircle2 className="h-5 w-5" />,
    title: 'Auto-clears the safe ones',
    description:
      'Invoices that match a PO within tolerance are queued for payment instantly. Risky ones are escalated to you as cards.',
  },
  {
    icon: <UserCheck className="h-5 w-5" />,
    title: 'You decide — it learns',
    description:
      'Approve, Hold, or Route the escalations. After a few consistent decisions, Invoice Copilot proposes a rule so it handles the same pattern automatically next time.',
  },
  {
    icon: <Shield className="h-5 w-5" />,
    title: 'Every action is logged',
    description:
      'Every step the agent takes is written to a tamper-evident audit trail. Click "View audit trail" on any invoice to inspect the full chain.',
  },
]

interface IntroModalProps {
  /** Controlled open/closed for the re-open via Help button */
  open?: boolean
  onOpenChange?: (v: boolean) => void
  /** Called when the modal is dismissed (first-run or re-run) */
  onDismiss?: () => void
  /** Called when user clicks "Take the tour" in the footer */
  onTakeTour?: () => void
}

export function IntroModal({ open: controlledOpen, onOpenChange, onDismiss, onTakeTour }: IntroModalProps) {
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) {
      setOpen(true)
    }
  }, [])

  // If externally controlled (Help button), sync
  useEffect(() => {
    if (controlledOpen !== undefined) setOpen(controlledOpen)
  }, [controlledOpen])

  function dismiss() {
    localStorage.setItem(STORAGE_KEY, '1')
    setOpen(false)
    onOpenChange?.(false)
    onDismiss?.()
  }

  function handleTakeTour() {
    dismiss()
    onTakeTour?.()
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { if (!v) dismiss() }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="text-base">How Invoice Copilot works</DialogTitle>
          <DialogDescription>
            A 90-second walkthrough for first-time users
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {STEPS.map((step, i) => (
            <div key={i} className="flex gap-3">
              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                {step.icon}
              </div>
              <div>
                <p className="text-sm font-semibold text-foreground leading-snug">{step.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5 leading-relaxed">
                  {step.description}
                </p>
              </div>
            </div>
          ))}
        </div>

        <div className="flex flex-col gap-2 mt-1">
          <Button onClick={dismiss} className="w-full">
            Got it — let's go
          </Button>
          {onTakeTour && (
            <Button
              variant="outline"
              className="w-full gap-2"
              onClick={handleTakeTour}
            >
              <Map className="h-4 w-4" />
              Take the tour
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}

/** Small help trigger button — place in PageHeader actions */
export function HelpButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      data-tour="help-btn"
      onClick={onClick}
      className="flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
      title="How Invoice Copilot works"
    >
      <HelpCircle className="h-3.5 w-3.5" />
      Help
    </button>
  )
}
