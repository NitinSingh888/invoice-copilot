import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { InvoiceStatus, FindingDisplay } from './types'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

// ────────────────────────────────────────────────────────────────────────────
// Status helpers
// ────────────────────────────────────────────────────────────────────────────

export type StatusVariant = 'success' | 'warning' | 'destructive' | 'muted' | 'default'

export function statusVariant(status: InvoiceStatus): StatusVariant {
  switch (status) {
    case 'queued': return 'success'
    case 'needs': return 'warning'
    case 'blocked':
    case 'rejected': return 'destructive'
    case 'routed':
    case 'held': return 'muted'
    default: return 'default'
  }
}

export function statusLabel(status: InvoiceStatus): string {
  switch (status) {
    case 'received': return 'Received'
    case 'queued': return 'Queued'
    case 'needs': return 'Needs you'
    case 'blocked': return 'Blocked'
    case 'routed': return 'Routed'
    case 'held': return 'On hold'
    case 'cleared': return 'Cleared'
    case 'rejected': return 'Rejected'
    default: return status
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Vendor avatar color
// ────────────────────────────────────────────────────────────────────────────

const AVATAR_COLORS = [
  'bg-violet-500',
  'bg-blue-500',
  'bg-emerald-500',
  'bg-orange-500',
  'bg-pink-500',
  'bg-cyan-500',
  'bg-amber-500',
  'bg-rose-500',
  'bg-teal-500',
  'bg-indigo-500',
]

export function vendorColor(vendor: string): string {
  let hash = 0
  for (let i = 0; i < vendor.length; i++) {
    hash = vendor.charCodeAt(i) + ((hash << 5) - hash)
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

// ────────────────────────────────────────────────────────────────────────────
// Money formatting
// ────────────────────────────────────────────────────────────────────────────

export function formatMoney(amount: string): string {
  const n = parseFloat(amount)
  if (isNaN(n)) return amount
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

// ────────────────────────────────────────────────────────────────────────────
// Finding code → display
// ────────────────────────────────────────────────────────────────────────────

export const FINDING_EXPLANATIONS: Record<string, string> = {
  OVER_TOLERANCE: 'Amount is over the allowed % above its purchase order. Needs human approval before payment.',
  UNKNOWN_VENDOR: "Vendor isn't in the approved-vendor list yet. A human needs to OK first-time suppliers.",
  NO_PO_MATCH: 'No matching purchase order was found. Could be a new vendor or a typo in the PO number.',
  MISSING_PO: 'No purchase order number was provided. All payable invoices need a linked PO.',
  DUPLICATE_EXACT: 'Same vendor + invoice number already paid. Blocked to prevent double-payment.',
  DUPLICATE_SUSPECT: 'Same vendor + amount seen recently. May be a duplicate — verify before paying.',
  PO_MATCH_OK: 'Invoice matched a purchase order within tolerance. Safe to queue for payment.',
  MULTI_PO_MATCH: 'Multiple purchase orders match this invoice. Manual selection needed.',
  UNDER_TOLERANCE: 'Amount is slightly under the PO — usually fine, but flagged for awareness.',
  PARTIAL_PO: 'Only part of the PO is covered by this invoice. May be a partial delivery.',
  VENDOR_BLOCKED: 'This vendor has been manually blocked. Contact finance before proceeding.',
}

const FINDING_MAP: Record<string, { label: string; severity: FindingDisplay['severity'] }> = {
  OVER_TOLERANCE: { label: 'Over PO tolerance', severity: 'warning' },
  UNKNOWN_VENDOR: { label: 'Vendor not approved', severity: 'warning' },
  NO_PO_MATCH: { label: 'No matching PO', severity: 'warning' },
  MISSING_PO: { label: 'No matching PO', severity: 'warning' },
  DUPLICATE_EXACT: { label: 'Exact duplicate', severity: 'destructive' },
  DUPLICATE_SUSPECT: { label: 'Possible duplicate', severity: 'destructive' },
  PO_MATCH_OK: { label: 'Matched PO', severity: 'success' },
  MULTI_PO_MATCH: { label: 'Multiple POs matched', severity: 'warning' },
  UNDER_TOLERANCE: { label: 'Under PO tolerance', severity: 'success' },
  PARTIAL_PO: { label: 'Partial PO', severity: 'warning' },
  VENDOR_BLOCKED: { label: 'Vendor blocked', severity: 'destructive' },
}

export function displayFinding(code: string, detail: string): FindingDisplay {
  const mapped = FINDING_MAP[code]
  return {
    code,
    label: mapped?.label ?? code.replace(/_/g, ' '),
    severity: mapped?.severity ?? 'warning',
    detail,
  }
}

// ────────────────────────────────────────────────────────────────────────────
// Date helpers
// ────────────────────────────────────────────────────────────────────────────

/** Returns true when an ISO-8601 timestamp falls on the current local date. */
export function isToday(isoString: string): boolean {
  const d = new Date(isoString)
  const now = new Date()
  return (
    d.getFullYear() === now.getFullYear() &&
    d.getMonth() === now.getMonth() &&
    d.getDate() === now.getDate()
  )
}

/**
 * Format an ISO-8601 date string as a human-readable group header:
 * "Yesterday", "Mon, Jun 9", etc.
 */
export function formatDayHeader(isoString: string): string {
  const d = new Date(isoString)
  const now = new Date()
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)

  if (
    d.getFullYear() === yesterday.getFullYear() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getDate() === yesterday.getDate()
  ) {
    return 'Yesterday'
  }

  return d.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}

/**
 * Extract the local YYYY-MM-DD date key from an ISO-8601 string.
 * Used to group invoices by day.
 */
export function localDateKey(isoString: string): string {
  const d = new Date(isoString)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

// ────────────────────────────────────────────────────────────────────────────
// Time saved estimate
// ────────────────────────────────────────────────────────────────────────────

export function minutesSaved(count: number): number {
  // ~3 min per invoice (manual review)
  return count * 3
}
