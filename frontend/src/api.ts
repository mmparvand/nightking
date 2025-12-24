const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

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

export { API_BASE_URL }
