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

export { API_BASE_URL }
