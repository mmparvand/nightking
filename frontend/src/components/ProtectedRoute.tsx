import { cloneElement, useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { fetchCurrentUser, type Role, type User } from '../api'

interface Props {
  requiredRole: Role
  children: React.ReactElement<{ user: User }>
}

export function ProtectedRoute({ requiredRole, children }: Props) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      try {
        const u = await fetchCurrentUser()
        if (!cancelled) setUser(u)
      } catch (err) {
        if (!cancelled) setError((err as Error).message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void run()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900 text-white">
        <div className="animate-pulse rounded-xl bg-slate-800 px-4 py-3 text-sm text-slate-200">Checking session…</div>
      </div>
    )
  }

  if (error || !user) {
    return <Navigate to="/login" replace />
  }

  if (user.role !== requiredRole) {
    return <Navigate to="/login" replace />
  }

  return cloneElement(children, { user })
}
