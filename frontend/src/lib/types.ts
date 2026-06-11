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

export interface ChatResponse {
  reply: string
  intent: string
  result: BatchResult | ExplainResult | null
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

// ────────────────────────────────────────────────────────────────────────────
// UI-level types
// ────────────────────────────────────────────────────────────────────────────

export type ThreadMessage =
  | { type: 'user'; content: string }
  | { type: 'agent'; content: string }
  | { type: 'narration'; queued: number; needs: number; blocked: number }
  | { type: 'approval'; invoice: InvoiceOut; findings: FindingDisplay[]; rationale: string }
  | { type: 'resolved'; invoice: InvoiceOut; action: string; byRole: Role }
  | { type: 'rule_proposal'; proposal: RuleProposeResponse }

export interface FindingDisplay {
  code: string
  label: string
  severity: 'success' | 'warning' | 'destructive'
  detail: string
}
