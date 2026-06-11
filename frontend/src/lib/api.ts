import type {
  InvoiceOut,
  CreateInvoiceRequest,
  CreateInvoiceResponse,
  ActionRequest,
  Role,
  ChatMessage,
  ChatResponse,
  AuditResponse,
  RuleOut,
  RuleProposeResponse,
  DemoResetResponse,
} from './types'

const BASE = '/api/v1'

let currentRole: Role = 'maya'

export function setRole(role: Role) {
  currentRole = role
}

export function getRole(): Role {
  return currentRole
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  useRole = false,
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  if (useRole) {
    headers['X-Role'] = currentRole
  }

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
  })

  if (res.status === 204) {
    return null as T
  }

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }

  return res.json() as Promise<T>
}

// ────────────────────────────────────────────────────────────────────────────
// Health
// ────────────────────────────────────────────────────────────────────────────

export async function getHealth(): Promise<{ status: string; provider: string; live: boolean }> {
  return request('/health')
}

// ────────────────────────────────────────────────────────────────────────────
// Invoices
// ────────────────────────────────────────────────────────────────────────────

export async function listInvoices(): Promise<InvoiceOut[]> {
  return request('/invoices')
}

export async function getInvoice(id: string): Promise<InvoiceOut> {
  return request(`/invoices/${id}`)
}

export async function createInvoice(
  body: CreateInvoiceRequest,
): Promise<CreateInvoiceResponse> {
  return request('/invoices', { method: 'POST', body: JSON.stringify(body) })
}

export async function invoiceAction(
  id: string,
  body: ActionRequest,
): Promise<InvoiceOut> {
  return request(`/invoices/${id}/action`, { method: 'POST', body: JSON.stringify(body) }, true)
}

// ────────────────────────────────────────────────────────────────────────────
// Chat
// ────────────────────────────────────────────────────────────────────────────

export async function chat(
  message: string,
  history: ChatMessage[],
): Promise<ChatResponse> {
  return request('/chat', { method: 'POST', body: JSON.stringify({ message, history }) }, true)
}

// ────────────────────────────────────────────────────────────────────────────
// Audit
// ────────────────────────────────────────────────────────────────────────────

export async function getAudit(id: string): Promise<AuditResponse> {
  return request(`/audit/${id}`)
}

export async function getAuditLog(): Promise<AuditResponse> {
  return request('/audit')
}

// ────────────────────────────────────────────────────────────────────────────
// Rules
// ────────────────────────────────────────────────────────────────────────────

export async function listRules(): Promise<RuleOut[]> {
  return request('/rules')
}

export async function proposeRule(): Promise<RuleProposeResponse | null> {
  return request('/rules/propose', { method: 'POST' })
}

export async function activateRule(body: {
  threshold_pct: number
  route: string | null
}): Promise<RuleOut> {
  return request('/rules/activate', { method: 'POST', body: JSON.stringify(body) })
}

export async function patchRule(
  id: string,
  status: 'active' | 'disabled',
): Promise<RuleOut> {
  return request(`/rules/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) })
}

// ────────────────────────────────────────────────────────────────────────────
// Demo
// ────────────────────────────────────────────────────────────────────────────

export async function demoReset(): Promise<DemoResetResponse> {
  return request('/demo/reset', { method: 'POST' })
}
