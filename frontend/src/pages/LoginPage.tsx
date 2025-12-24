import { FormEvent, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { API_BASE_URL, fetchHealth, login, type Role } from '../api'

const tabs: Role[] = ['ADMIN', 'RESELLER']

export function LoginPage() {
  const [activeRole, setActiveRole] = useState<Role>('ADMIN')
  const [healthStatus, setHealthStatus] = useState<'unknown' | 'ok' | 'error'>('unknown')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetchHealth().then((status) => setHealthStatus(status)).catch(() => setHealthStatus('error'))
  }, [])

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError(null)
    setLoading(true)
    const formData = new FormData(event.currentTarget)
    const username = String(formData.get('username') || '')
    const password = String(formData.get('password') || '')

    try {
      const result = await login(username, password, activeRole)
      const target = result.user.role === 'ADMIN' ? '/admin/dashboard' : '/reseller/dashboard'
      navigate(target, { replace: true })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const statusColor =
    healthStatus === 'ok' ? 'text-emerald-400' : healthStatus === 'error' ? 'text-rose-400' : 'text-amber-300'

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white">
      <div className="mx-auto flex max-w-5xl flex-col gap-10 px-6 py-12">
        <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-widest text-slate-400">Self-hosted VPN</p>
            <h1 className="text-3xl font-bold">Nightking VPN Panel</h1>
            <p className="text-slate-300">Manage gateways, users, and resellers from a secure control plane.</p>
          </div>
          <div className="rounded-full bg-slate-800 px-4 py-2 text-sm text-slate-200 shadow-lg">
            API: <span className={`font-semibold ${statusColor}`}>{healthStatus}</span>
          </div>
        </header>

        <div className="grid gap-8 md:grid-cols-2">
          <section className="rounded-2xl bg-slate-800/70 p-8 shadow-xl ring-1 ring-slate-700">
            <h2 className="text-2xl font-semibold">Role-based access</h2>
            <p className="mt-3 text-slate-300">
              Authenticate admins and resellers with JWT. The backend issues HttpOnly cookies so browsers send your token
              automatically on subsequent requests.
            </p>
            <div className="mt-6 space-y-3 text-sm text-slate-200">
              <p>
                Health endpoint:{' '}
                <code className="rounded bg-slate-900/60 px-2 py-1 font-mono text-emerald-300">GET /health</code>
              </p>
              <p>
                Auth endpoints:{' '}
                <code className="rounded bg-slate-900/60 px-2 py-1 font-mono text-emerald-300">POST /auth/login</code>{' '}
                and{' '}
                <code className="rounded bg-slate-900/60 px-2 py-1 font-mono text-emerald-300">GET /auth/me</code>
              </p>
              <p>API base: {API_BASE_URL}</p>
              <p className="text-xs text-slate-400">
                For production, ensure HTTPS and secure cookies; storing tokens outside HttpOnly cookies increases XSS
                risk.
              </p>
            </div>
          </section>

          <section className="rounded-2xl bg-slate-800/70 p-8 shadow-xl ring-1 ring-slate-700">
            <div className="flex gap-3 rounded-xl bg-slate-900/50 p-1">
              {tabs.map((role) => (
                <button
                  key={role}
                  type="button"
                  onClick={() => setActiveRole(role)}
                  className={`flex-1 rounded-lg px-4 py-2 text-sm font-semibold transition ${
                    activeRole === role ? 'bg-emerald-500 text-slate-900' : 'text-slate-200 hover:bg-slate-800'
                  }`}
                >
                  {role === 'ADMIN' ? 'Admin' : 'Reseller'}
                </button>
              ))}
            </div>

            <form className="mt-6 space-y-4" onSubmit={onSubmit}>
              <div>
                <label className="text-sm text-slate-300" htmlFor="username">
                  Username
                </label>
                <input
                  id="username"
                  name="username"
                  className="mt-2 w-full rounded-lg bg-slate-900/70 px-4 py-2 text-white ring-1 ring-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="admin"
                  required
                />
              </div>
              <div>
                <label className="text-sm text-slate-300" htmlFor="password">
                  Password
                </label>
                <input
                  id="password"
                  name="password"
                  type="password"
                  className="mt-2 w-full rounded-lg bg-slate-900/70 px-4 py-2 text-white ring-1 ring-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="••••••••"
                  required
                />
              </div>

              {error ? <p className="text-sm text-rose-400">{error}</p> : null}

              <button
                type="submit"
                className="w-full rounded-lg bg-emerald-500 px-4 py-2 font-semibold text-slate-900 shadow-lg transition hover:bg-emerald-400 disabled:opacity-70"
                disabled={loading}
              >
                {loading ? 'Signing in…' : `Sign in as ${activeRole === 'ADMIN' ? 'Admin' : 'Reseller'}`}
              </button>
            </form>
          </section>
        </div>
      </div>
    </div>
  )
}
