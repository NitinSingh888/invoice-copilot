import { useCallback, useEffect, useRef } from 'react'
import { driver } from 'driver.js'
import 'driver.js/dist/driver.css'

const TOUR_KEY = 'ic_tour_done'

/**
 * Returns a `startTour` function and a flag indicating whether the tour has
 * ever been completed. Call `startTour()` to launch (or replay) the tour.
 *
 * The tour auto-runs once after the intro modal is dismissed — detected by
 * watching for `ic_intro_seen` in localStorage (set by IntroModal.dismiss).
 * Respects `prefers-reduced-motion`.
 */
export function useTour(introSeen: boolean) {
  const driverRef = useRef<ReturnType<typeof driver> | null>(null)

  const prefersReducedMotion =
    typeof window !== 'undefined' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches

  const startTour = useCallback(() => {
    // Destroy any in-progress tour
    driverRef.current?.destroy()

    const d = driver({
      animate: !prefersReducedMotion,
      showProgress: true,
      smoothScroll: true,
      allowClose: true,
      overlayColor: 'rgba(0,0,0,0.45)',
      steps: [
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
              'The full picture: pipeline steps, decision rules, safety model, and how Copilot learns. Open it whenever you want a deep dive.',
            side: 'right',
            align: 'start',
          },
        },
      ],
      onDestroyed() {
        localStorage.setItem(TOUR_KEY, '1')
      },
    })

    driverRef.current = d
    d.drive()
  }, [prefersReducedMotion])

  // Auto-run once when intro is dismissed (introSeen flips from false → true)
  const autoRanRef = useRef(false)
  useEffect(() => {
    if (!introSeen) return
    if (autoRanRef.current) return
    if (localStorage.getItem(TOUR_KEY)) return
    autoRanRef.current = true
    // Small delay so the modal finish animation completes
    const id = setTimeout(startTour, 400)
    return () => clearTimeout(id)
  }, [introSeen, startTour])

  return { startTour }
}
