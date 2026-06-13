import { useCallback, useEffect, useRef } from 'react'
import { driver, type DriveStep } from 'driver.js'
import 'driver.js/dist/driver.css'

// Persisted tour progress. Drives a simple state machine:
//   (no key)            -> auto-run from step 0 on first visit
//   {status:'started'}  -> tour in progress; `step` is the last highlighted
//                          index, so a mid-tour refresh resumes from there
//   {status:'completed'}-> finished or dismissed; never auto-runs again
const TOUR_KEY = 'ic_tour_state'

type TourState = { status?: 'started' | 'completed'; step?: number }

function readTourState(): TourState {
  try {
    return JSON.parse(localStorage.getItem(TOUR_KEY) || '{}') as TourState
  } catch {
    return {}
  }
}

function writeTourState(s: TourState): void {
  try {
    localStorage.setItem(TOUR_KEY, JSON.stringify(s))
  } catch {
    /* localStorage unavailable (private mode quota etc.) — tour still works, just not resumable */
  }
}

const STEPS: DriveStep[] = [
  {
    element: '[data-tour="sidebar"]',
    popover: {
      title: 'Navigation',
      description: 'Switch between Dashboard, Inbox, Rules, and Audit Log here.',
      side: 'right',
      align: 'start',
    },
  },
  {
    element: '[data-tour="process-btn"]',
    popover: {
      title: "Process today's invoices",
      description:
        'Click this to start the agent. It reads every invoice, matches POs, auto-clears the safe ones, and hands you the rest.',
      side: 'bottom',
      align: 'start',
    },
  },
  {
    element: '[data-tour="search"]',
    popover: {
      title: 'Search the queue',
      description: 'Filter by vendor, invoice ID, or PO number. Also reachable with ⌘K.',
      side: 'bottom',
      align: 'end',
    },
  },
  {
    element: '[data-tour="add-invoice"]',
    popover: {
      title: 'Add an invoice',
      description: 'Upload a PDF or enter details manually to inject a new invoice into the queue.',
      side: 'bottom',
      align: 'start',
    },
  },
  {
    element: '[data-tour="help-btn"]',
    popover: {
      title: 'Help',
      description: 'Reopen the intro walkthrough any time.',
      side: 'bottom',
      align: 'end',
    },
  },
  {
    element: '[data-tour="guide-nav"]',
    popover: {
      title: 'Guide',
      description:
        'The full picture: pipeline steps, decision rules, safety model, and how Copilot learns. You can replay this tour from here any time.',
      side: 'right',
      align: 'start',
    },
  },
]

/**
 * Guided product tour.
 *
 * Returns `startTour(fromStep?)` to launch or replay the tour. The tour also
 * auto-runs once on a user's first visit (no `ic_tour_state` key yet) and, if a
 * refresh happens mid-tour, resumes from the last step the user reached.
 * Completing or closing it marks the tour done so it never auto-runs again —
 * after that it's only reachable from the Guide page's "Take the guided tour".
 * Respects `prefers-reduced-motion`.
 */
export function useTour() {
  const driverRef = useRef<ReturnType<typeof driver> | null>(null)
  // True while we tear down an in-progress tour to start a new one, so the
  // teardown's onDestroyed doesn't mark the tour "completed" by mistake.
  const suppressDestroyRef = useRef(false)

  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const startTour = useCallback(
    (fromStep = 0) => {
      if (driverRef.current) {
        suppressDestroyRef.current = true
        driverRef.current.destroy()
        suppressDestroyRef.current = false
      }

      const d = driver({
        animate: !prefersReducedMotion,
        showProgress: true,
        smoothScroll: true,
        allowClose: true,
        overlayColor: 'rgba(0,0,0,0.45)',
        steps: STEPS,
        // Persist progress on every step so a refresh can resume here.
        onHighlighted: (_el, _step, opts) => {
          writeTourState({ status: 'started', step: opts.state.activeIndex ?? 0 })
        },
        // Fired on finish AND on early close → don't auto-run again.
        onDestroyed: () => {
          if (suppressDestroyRef.current) return
          writeTourState({ status: 'completed', step: STEPS.length })
          driverRef.current = null
        },
      })

      driverRef.current = d
      // Guard against being used directly as an onClick handler (which would
      // pass a MouseEvent as fromStep) — fall back to starting from the top.
      const start =
        typeof fromStep === 'number' && Number.isFinite(fromStep)
          ? Math.min(Math.max(fromStep, 0), STEPS.length - 1)
          : 0
      d.drive(start)
    },
    [prefersReducedMotion],
  )

  // Auto-run on first visit; resume from the saved step after a mid-tour refresh.
  // Polls for the page's tour anchors so it never starts before the Inbox has
  // rendered them (a fixed delay could fire too early and silently no-op).
  const autoRanRef = useRef(false)
  useEffect(() => {
    if (autoRanRef.current) return
    const st = readTourState()
    if (st.status === 'completed') return
    autoRanRef.current = true

    let cancelled = false
    let tries = 0
    const tick = () => {
      if (cancelled) return
      const sidebar = document.querySelector('[data-tour="sidebar"]')
      const processBtn = document.querySelector('[data-tour="process-btn"]')
      // Start once both primary anchors exist, or after ~6s with just the
      // sidebar (the process button is absent once the queue is worked).
      if ((sidebar && processBtn) || (sidebar && tries > 40)) {
        startTour(st.step ?? 0)
        return
      }
      tries += 1
      window.setTimeout(tick, 150)
    }
    const id = window.setTimeout(tick, 400)
    return () => {
      cancelled = true
      window.clearTimeout(id)
    }
  }, [startTour])

  return { startTour }
}
