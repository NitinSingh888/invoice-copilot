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
    case 'blocked': return 'destructive'
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

const FINDING_MAP: Record<string, { label: string; severity: FindingDisplay['severity'] }> = {
  OVER_TOLERANCE: { label: 'Over PO tolerance', severity: 'warning' },
  UNKNOWN_VENDOR: { label: 'Vendor not approved', severity: 'warning' },
  NO_PO_MATCH: { label: 'No matching PO', severity: 'warning' },
  MISSING_PO: { label: 'No matching PO', severity: 'warning' },
  DUPLICATE_EXACT: { label: 'Exact duplicate', severity: 'destructive' },
  PO_MATCH_OK: { label: 'Matched PO', severity: 'success' },
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
// Time saved estimate
// ────────────────────────────────────────────────────────────────────────────

export function minutesSaved(count: number): number {
  // ~3 min per invoice (manual review)
  return count * 3
}
