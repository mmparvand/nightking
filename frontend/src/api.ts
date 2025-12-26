const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const SUBSCRIPTION_DOMAIN = import.meta.env.VITE_SUBSCRIPTION_DOMAIN || 'localhost'
const SUBSCRIPTION_PORT = import.meta.env.VITE_SUBSCRIPTION_PORT || '2053'
const SUBSCRIPTION_SCHEME = import.meta.env.VITE_SUBSCRIPTION_SCHEME || 'https'

export type Role = 'ADMIN' | 'RESELLER'

export interface User {
  username: string
  role: Role
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface SubscriptionToken {
  id: number
  token: string
  service_id: number
}

export interface Service {
  id: number
  name: string
  user_id: number
  reseller_id?: number | null
  protocol: 'XRAY_VLESS'
  endpoint?: string | null
  subscription_token?: SubscriptionToken | null
  traffic_limit_bytes?: number | null
  traffic_used_bytes?: number | null
  expires_at?: string | null
  ip_limit?: number | null
  concurrent_limit?: number | null
  is_active?: boolean | null
}

export interface PaginatedServices {
  items: Service[]
  limit: number
  offset: number
}

export interface XrayRenderResponse {
  generated_at: string
  config: Record<string, unknown>
}

export interface XrayApplyResponse {
  snapshot_id: number
  applied_at: string
  status: string
  healthy: boolean
  error?: string | null
}

export interface XrayStatus {
  healthy: boolean
  last_apply_status?: string | null
  last_apply_error?: string | null
  last_applied_at?: string | null
}

export interface ResellerPlan {
  id: number
  name: string
  price: number
  duration_days: number
  max_users?: number | null
  max_services?: number | null
  max_traffic_bytes?: number | null
  max_concurrent_total?: number | null
  is_active?: boolean
}

export interface ResellerReport {
  reseller_id: number
  users: number
  services: number
  traffic_used_bytes: number
  plan?: { plan: ResellerPlan } | any
  wallet_balance: number
}

export interface BackupInfo {
  id: string
  path: string
  created_at?: string | null
}

export interface MigrationPreview {
  users: number
  services: number
  tokens: number
}

export interface MigrationResult {
  created_users: number
  created_services: number
  skipped_tokens: number
}

export async function login(username: string, password: string, role: Role): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ username, password, role_tab: role }),
  })
  if (!response.ok) {
    const detail = (await response.json().catch(() => ({})))?.detail ?? 'Login failed'
    throw new Error(detail)
  }
  return (await response.json()) as LoginResponse
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    credentials: 'include',
  })
  if (!response.ok) {
    throw new Error('Not authenticated')
  }
  return (await response.json()) as User
}

export async function fetchHealth(): Promise<'ok' | 'error'> {
  try {
    const response = await fetch(`${API_BASE_URL}/health`)
    if (!response.ok) return 'error'
    const data = (await response.json()) as { status?: string }
    return data.status === 'ok' ? 'ok' : 'error'
  } catch {
    return 'error'
  }
}

export async function fetchServices(): Promise<PaginatedServices> {
  const response = await fetch(`${API_BASE_URL}/api/services`, { credentials: 'include' })
  if (!response.ok) {
    throw new Error('Failed to load services')
  }
  return (await response.json()) as PaginatedServices
}

export async function ensureServiceToken(serviceId: number): Promise<SubscriptionToken> {
  const response = await fetch(`${API_BASE_URL}/api/services/${serviceId}/token`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!response.ok) {
    const detail = (await response.json().catch(() => ({})))?.detail ?? 'Unable to generate token'
    throw new Error(detail)
  }
  return (await response.json()) as SubscriptionToken
}

export async function createService(payload: {
  name: string
  user_id: number
  reseller_id?: number | null
  protocol?: 'XRAY_VLESS'
  endpoint?: string
  traffic_limit_bytes?: number | null
  expires_at?: string
  ip_limit?: number | null
  concurrent_limit?: number | null
  is_active?: boolean
}): Promise<Service> {
  const response = await fetch(`${API_BASE_URL}/api/services`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ protocol: 'XRAY_VLESS', ...payload }),
  })
  if (!response.ok) {
    const detail = (await response.json().catch(() => ({})))?.detail ?? 'Unable to create service'
    throw new Error(detail)
  }
  return (await response.json()) as Service
}

export function buildSubscriptionLink(token: string): string {
  return `${SUBSCRIPTION_SCHEME}://${SUBSCRIPTION_DOMAIN}:${SUBSCRIPTION_PORT}/sub/${encodeURIComponent(token)}`
}

export async function renderXrayConfig(): Promise<XrayRenderResponse> {
  const res = await fetch(`${API_BASE_URL}/xray/render`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({})))?.detail ?? 'Failed to render config'
    throw new Error(detail)
  }
  return (await res.json()) as XrayRenderResponse
}

export async function applyXrayConfig(): Promise<XrayApplyResponse> {
  const res = await fetch(`${API_BASE_URL}/xray/apply`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({})))?.detail ?? 'Failed to apply config'
    throw new Error(detail)
  }
  return (await res.json()) as XrayApplyResponse
}

export async function fetchXrayStatus(): Promise<XrayStatus> {
  const res = await fetch(`${API_BASE_URL}/xray/status`, { credentials: 'include' })
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({})))?.detail ?? 'Failed to load status'
    throw new Error(detail)
  }
  return (await res.json()) as XrayStatus
}

export async function listBackups(): Promise<BackupInfo[]> {
  const res = await fetch(`${API_BASE_URL}/api/backups`, { credentials: 'include' })
  if (!res.ok) throw new Error('Failed to load backups')
  return (await res.json()) as BackupInfo[]
}

export async function createBackup(): Promise<BackupInfo> {
  const res = await fetch(`${API_BASE_URL}/api/backups/create`, { method: 'POST', credentials: 'include' })
  if (!res.ok) throw new Error('Failed to create backup')
  return (await res.json()) as BackupInfo
}

export async function restoreBackup(id: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/backups/${id}/restore`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(true),
  })
  if (!res.ok) throw new Error('Failed to restore backup')
}

export async function uploadBackup(file: File): Promise<BackupInfo> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE_URL}/api/backups/upload`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  })
  if (!res.ok) throw new Error('Failed to upload backup')
  return (await res.json()) as BackupInfo
}

export async function migrationPreview(file: File): Promise<MigrationPreview> {
  const form = new FormData()
  form.append('method', 'json')
  form.append('file', file)
  const res = await fetch(`${API_BASE_URL}/api/migration/marzban/preview`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  })
  if (!res.ok) throw new Error('Failed to preview migration')
  return (await res.json()) as MigrationPreview
}

export async function migrationRun(file: File): Promise<MigrationResult> {
  const form = new FormData()
  form.append('method', 'json')
  form.append('file', file)
  const res = await fetch(`${API_BASE_URL}/api/migration/marzban/run`, {
    method: 'POST',
    credentials: 'include',
    body: form,
  })
  if (!res.ok) throw new Error('Failed to run migration')
  return (await res.json()) as MigrationResult
}

export interface Node {
  id: number
  name: string
  location: string
  ip_address: string
  api_base_url: string
  is_active: boolean
  last_seen_at?: string | null
}

export async function listNodes(): Promise<Node[]> {
  const res = await fetch(`${API_BASE_URL}/api/nodes`, { credentials: 'include' })
  if (!res.ok) throw new Error('Failed to load nodes')
  return (await res.json()) as Node[]
}

export async function createNode(payload: {
  name: string
  location: string
  ip_address: string
  api_base_url: string
  auth_token: string
}): Promise<Node> {
  const res = await fetch(`${API_BASE_URL}/api/nodes`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error('Failed to create node')
  return (await res.json()) as Node
}

export async function setServiceNodes(serviceId: number, nodeIds: number[]): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/services/${serviceId}/nodes`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(nodeIds),
  })
  if (!res.ok) throw new Error('Failed to assign nodes')
}

export async function fetchResellerReport(resellerId: number): Promise<ResellerReport> {
  const res = await fetch(`${API_BASE_URL}/api/resellers/${resellerId}/report`, { credentials: 'include' })
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({})))?.detail ?? 'Failed to load report'
    throw new Error(detail)
  }
  return (await res.json()) as ResellerReport
}

export async function listPlans(): Promise<ResellerPlan[]> {
  const res = await fetch(`${API_BASE_URL}/api/plans`, { credentials: 'include' })
  if (!res.ok) {
    throw new Error('Failed to load plans')
  }
  return (await res.json()) as ResellerPlan[]
}

export async function subscribePlan(resellerId: number, planId: number): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/resellers/${resellerId}/subscribe?plan_id=${planId}`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!res.ok) {
    const detail = (await res.json().catch(() => ({})))?.detail ?? 'Failed to subscribe'
    throw new Error(detail)
  }
}

export { API_BASE_URL }
