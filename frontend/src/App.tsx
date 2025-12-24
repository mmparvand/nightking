import { useEffect, useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function App() {
  const [healthStatus, setHealthStatus] = useState<'unknown' | 'ok' | 'error'>('unknown')
  const [message, setMessage] = useState<string>('Checking service health...')

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/health`)
        if (!response.ok) {
          throw new Error('Health check failed')
        }
        const data = (await response.json()) as { status?: string }
        setHealthStatus(data.status === 'ok' ? 'ok' : 'error')
        setMessage('Backend is reachable')
      } catch (error) {
        console.error('Health check error', error)
        setHealthStatus('error')
        setMessage('Unable to reach backend')
      }
    }

    void checkHealth()
  }, [])

  const statusColor = healthStatus === 'ok' ? 'text-emerald-400' : healthStatus === 'error' ? 'text-rose-400' : 'text-amber-300'

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="mx-auto flex max-w-4xl flex-col gap-12 px-6 py-16 text-white">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-sm uppercase tracking-widest text-slate-400">Self-hosted VPN</p>
            <h1 className="text-3xl font-bold">Nightking VPN Panel</h1>
          </div>
          <div className="rounded-full bg-slate-800 px-4 py-2 text-sm text-slate-200 shadow-lg">Dashboard Preview</div>
        </header>

        <main className="grid gap-8 md:grid-cols-2">
          <section className="rounded-2xl bg-slate-800/70 p-8 shadow-xl ring-1 ring-slate-700">
            <h2 className="text-2xl font-semibold">Manage your VPN fleet</h2>
            <p className="mt-3 text-slate-300">
              Bring up a production-ready control plane to manage gateways, users, and access policies. Ship securely with
              FastAPI, PostgreSQL, Redis, and a React + Tailwind dashboard.
            </p>
            <div className="mt-6 flex flex-col gap-3 text-sm text-slate-200">
              <div className="flex items-center gap-2">
                <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                Health endpoints: <code className="font-mono text-emerald-300">/health</code> and{' '}
                <code className="font-mono text-emerald-300">/ready</code>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                Docker Compose stack: backend, frontend, PostgreSQL, Redis
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex h-2 w-2 rounded-full bg-emerald-400" />
                Ready to extend with authentication, RBAC, and VPN automation
              </div>
            </div>
          </section>

          <section className="rounded-2xl bg-slate-800/70 p-8 shadow-xl ring-1 ring-slate-700">
            <h2 className="text-2xl font-semibold">Live status</h2>
            <p className={`mt-2 text-lg font-medium ${statusColor}`}>{message}</p>
            <div className="mt-6 grid grid-cols-2 gap-4 text-sm text-slate-200">
              <div className="rounded-xl bg-slate-900/60 p-4 ring-1 ring-slate-700">
                <p className="text-slate-400">API Base</p>
                <p className="font-semibold">{API_BASE_URL}</p>
              </div>
              <div className="rounded-xl bg-slate-900/60 p-4 ring-1 ring-slate-700">
                <p className="text-slate-400">Health</p>
                <p className={`font-semibold ${statusColor}`}>{healthStatus}</p>
              </div>
            </div>
          </section>
        </main>
      </div>
    </div>
  )
}

export default App
