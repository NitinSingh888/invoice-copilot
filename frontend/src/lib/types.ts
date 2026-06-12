// ────────────────────────────────────────────────────────────────────────────
// Domain types matching the FastAPI backend schemas
// ────────────────────────────────────────────────────────────────────────────

export type InvoiceStatus =
  | 'received'
  | 'queued'
  | 'needs'
  | 'blocked'
  | 'routed'
  | 'held'
  | 'cleared'

export interface InvoiceOut {
  id: string
  vendor: string
  amount: string
  po_number: string | null
  invoice_number: string | null
  status: InvoiceStatus
  verdict: string | null
  route: string | null
  source_file: string | null
  created_at: string
}

export interface Finding {
  code: string
  severity: string
  detail: string
}

export interface CreateInvoiceRequest {
  vendor: string
  amount: string
  invoice_number: string
  po_number?: string
  confidence?: number
  source_file?: string
}

export interface CreateInvoiceResponse {
  invoice_id: string
  verdict: string
  route: string | null
  reason: string
  status: InvoiceStatus
  findings: Finding[]
}

export interface ActionRequest {
  action: 'approve' | 'hold' | 'edit' | 'route'
  amount?: string
  route?: string
  reason?: string
}

export type Role = 'maya' | 'priya'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface BatchResult {
  queued: number
  needs: number
  blocked: number
}

export interface ExplainResult {
  invoice_id: string
  trail: AuditTrailEntry[]
}

export interface AuditTrailEntry {
  seq: number
  module: string
  action: string
  actor: string
  rationale: string
}

// ────────────────────────────────────────────────────────────────────────────
// Chat / review_invoice result shapes
// ────────────────────────────────────────────────────────────────────────────

export interface ReviewInvoiceFound {
  invoice: {
    id: string
    vendor: string
    amount: string
    invoice_number: string | null
    po_number: string | null
    status: InvoiceStatus
    verdict: string | null
    confidence: number | null
  }
  findings: Finding[]
  summary: string
}

export interface ReviewInvoiceNotFound {
  not_found: true
  query: string
}

export type ReviewInvoiceResult = ReviewInvoiceFound | ReviewInvoiceNotFound

export function isReviewFound(r: ReviewInvoiceResult): r is ReviewInvoiceFound {
  return !('not_found' in r)
}

// ────────────────────────────────────────────────────────────────────────────
// New conversational-command result shapes
// ────────────────────────────────────────────────────────────────────────────

export interface ListResultItem {
  id: string
  vendor: string
  amount: string
  invoice_number: string | null
  status: InvoiceStatus
  po_number: string | null
}

export interface ListResult {
  list: ListResultItem[]
  label: string
  count: number
}

export interface AggregateResult {
  aggregate: {
    label: string
    value: string
  }
}

export interface BulkConfirmResult {
  bulk: {
    action: 'approve' | 'hold' | 'route'
    ids: string[]
    count: number
    total: string
    label: string
    route_to: string | null
  }
}

export interface BulkActionResponse {
  applied: number
  results: { id: string; status: InvoiceStatus }[]
}

export interface ChatResponse {
  reply: string
  intent: string
  result: BatchResult | ExplainResult | ReviewInvoiceResult | ListResult | AggregateResult | BulkConfirmResult | null
}

// ────────────────────────────────────────────────────────────────────────────
// Sample invoices
// ────────────────────────────────────────────────────────────────────────────

export interface SampleInvoice {
  label: string
  expected: string
  vendor: string
  amount: string
  invoice_number: string
  po_number: string
  confidence: number
  source_file: string
}

// ────────────────────────────────────────────────────────────────────────────
// Upload result (same shape as CreateInvoiceResponse / ProcessResultOut)
// ────────────────────────────────────────────────────────────────────────────

export interface ProcessResultOut {
  invoice_id: string
  verdict: string
  route: string | null
  reason: string
  status: InvoiceStatus
  findings: Finding[]
}

export interface AuditEvent {
  seq: number
  invoice_id: string
  actor: string
  module: string
  action: string
  inputs: Record<string, unknown>
  outputs: Record<string, unknown>
  rationale: string
  model_meta: Record<string, unknown>
  prev_hash: string
  hash: string
  ts: string
}

export interface AuditResponse {
  events: AuditEvent[]
  chain_verified: boolean
}

export interface RuleOut {
  id: string
  vendor: string | null
  max_over_pct: number | null
  route: string | null
  status: 'active' | 'disabled'
  min_amount: string | null
  source_correction_ids: string[]
  reasoning_note: string | null
}

export interface RuleCandidate {
  vendor: string | null
  finding_code: string
  action: string
  example_ids: string[]
  over_pcts: number[]
}

export interface RuleProposeResponse {
  candidate: RuleCandidate
  threshold_pct: number
  route: string | null
}

export interface DemoResetResponse {
  status: string
  received: number
}

export interface CreateRuleBody {
  vendor: string
  finding_code?: string
  max_over_pct?: number | null
  min_amount?: number | null
  route: string
}

// ────────────────────────────────────────────────────────────────────────────
// UI-level types
// ────────────────────────────────────────────────────────────────────────────

export type BulkConfirmState = 'idle' | 'loading' | 'done' | 'dismissed'

export type ThreadMessage =
  | { type: 'user'; content: string }
  | { type: 'agent'; content: string }
  | { type: 'narration'; queued: number; needs: number; blocked: number }
  | { type: 'approval'; invoice: InvoiceOut; findings: FindingDisplay[]; rationale: string }
  | { type: 'resolved'; invoice: InvoiceOut; action: string; byRole: Role }
  | { type: 'rule_proposal'; proposal: RuleProposeResponse }
  | { type: 'inspection'; data: ReviewInvoiceFound }
  | { type: 'list'; data: ListResult }
  | { type: 'aggregate'; data: AggregateResult['aggregate'] }
  | { type: 'bulk_confirm'; data: BulkConfirmResult['bulk']; state: BulkConfirmState; applied?: number }

export interface FindingDisplay {
  code: string
  label: string
  severity: 'success' | 'warning' | 'destructive'
  detail: string
}
