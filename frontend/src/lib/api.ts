import type {
  InvoiceOut,
  InvoiceComment,
  OrgMember,
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
  SampleInvoice,
  ProcessResultOut,
  CreateRuleBody,
  BulkActionResponse,
} from './types'

const BASE = '/api/v1'
const TOKEN_KEY = 'ic_token'

let currentRole: Role = 'maya'

export function setRole(role: Role) {
  currentRole = role
}

export function getRole(): Role {
  return currentRole
}

// ────────────────────────────────────────────────────────────────────────────
// Token helpers
// ────────────────────────────────────────────────────────────────────────────

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
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

  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers,
  })

  if (res.status === 401) {
    clearToken()
    window.dispatchEvent(new Event('ic-unauthorized'))
    throw new Error('Unauthorized')
  }

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
// Auth
// ────────────────────────────────────────────────────────────────────────────

export interface SignupResponse {
  message: string
  status: 'active' | 'pending'
  verify_token?: string
}

export interface VerifyResponse {
  verified: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: string
}

export interface MeResponse {
  email: string
  is_verified: boolean
  org_id: string | null
  org_name: string | null
  role: 'admin' | 'member' | null
}

async function authRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  }

  const token = getToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`/api/v1${path}`, { ...options, headers })

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    const err = new Error(`API ${res.status}: ${text}`) as Error & { status: number }
    err.status = res.status
    throw err
  }

  return res.json() as Promise<T>
}

export async function authSignup(email: string, password: string, orgName: string): Promise<SignupResponse> {
  return authRequest<SignupResponse>('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password, org_name: orgName }),
  })
}

export async function authVerify(token: string): Promise<VerifyResponse> {
  return authRequest<VerifyResponse>('/auth/verify', {
    method: 'POST',
    body: JSON.stringify({ token }),
  })
}

export async function authLogin(email: string, password: string): Promise<LoginResponse> {
  return authRequest<LoginResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function authMe(): Promise<MeResponse> {
  return authRequest<MeResponse>('/auth/me')
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

export async function bulkAction(
  ids: string[],
  action: 'approve' | 'hold' | 'route',
  route?: string | null,
): Promise<BulkActionResponse> {
  return request(
    '/invoices/bulk-action',
    { method: 'POST', body: JSON.stringify({ ids, action, route: route ?? null }) },
    true,
  )
}

export async function getSamples(): Promise<SampleInvoice[]> {
  return request('/invoices/samples')
}

export async function uploadInvoice(file: File): Promise<ProcessResultOut> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/invoices/upload`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<ProcessResultOut>
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

export async function createRule(body: CreateRuleBody): Promise<RuleOut> {
  return request('/rules', { method: 'POST', body: JSON.stringify(body) })
}

// ────────────────────────────────────────────────────────────────────────────
// Demo
// ────────────────────────────────────────────────────────────────────────────

export async function demoReset(): Promise<DemoResetResponse> {
  return request('/demo/reset', { method: 'POST' })
}

// ────────────────────────────────────────────────────────────────────────────
// File preview
// ────────────────────────────────────────────────────────────────────────────

export function invoiceFileUrl(id: string): string {
  // <iframe>/<img> can't send the Authorization header, so pass the JWT as a
  // query param; the /file endpoint accepts it as a fallback and still enforces
  // org ownership.
  const t = getToken()
  const q = t ? `?token=${encodeURIComponent(t)}` : ''
  return `${BASE}/invoices/${id}/file${q}`
}

// ────────────────────────────────────────────────────────────────────────────
// Comments
// ────────────────────────────────────────────────────────────────────────────

export async function getComments(invoiceId: string): Promise<InvoiceComment[]> {
  return request(`/invoices/${invoiceId}/comments`)
}

export async function addComment(invoiceId: string, body: string): Promise<InvoiceComment> {
  return request(
    `/invoices/${invoiceId}/comments`,
    { method: 'POST', body: JSON.stringify({ body }) },
    true,
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Reject with reason
// ────────────────────────────────────────────────────────────────────────────

export async function rejectInvoice(invoiceId: string, reason: string): Promise<InvoiceOut> {
  return request(
    `/invoices/${invoiceId}/action`,
    { method: 'POST', body: JSON.stringify({ action: 'reject', reason }) },
    true,
  )
}

// ────────────────────────────────────────────────────────────────────────────
// Org / admin
// ────────────────────────────────────────────────────────────────────────────

export async function getOrgMembers(): Promise<OrgMember[]> {
  return authRequest<OrgMember[]>('/auth/org/members')
}

export async function getPendingMembers(): Promise<OrgMember[]> {
  return authRequest<OrgMember[]>('/auth/org/pending')
}

export async function verifyMember(userId: string): Promise<void> {
  await authRequest<unknown>('/auth/org/verify-user', {
    method: 'POST',
    body: JSON.stringify({ user_id: userId }),
  })
}

// ────────────────────────────────────────────────────────────────────────────
// AI usage / cost
// ────────────────────────────────────────────────────────────────────────────

export interface UsageCall {
  id: string
  purpose: string
  reason: string
  entity_type: string | null
  entity_id: string | null
  provider: string
  model: string
  input_tokens: number
  output_tokens: number
  cost_usd: string
  latency_ms: number
  status: string
  user_id: string | null
  created_at: string
}

export interface UsageSummary {
  currency: string
  total_calls: number
  total_cost_usd: string
  total_input_tokens: number
  total_output_tokens: number
  by_purpose: { purpose: string; calls: number; cost_usd: string; tokens: number }[]
  by_model: { model: string; calls: number; cost_usd: string }[]
  by_user: { user: string; calls: number; cost_usd: string }[]
  recent: UsageCall[]
}

export async function getUsage(): Promise<UsageSummary> {
  return request<UsageSummary>('/usage')
}
