import { FormEvent, useEffect, useState } from 'react'
import { buildSubscriptionLink, createService, ensureServiceToken, fetchServices, type Service, type User } from '../api'

interface Props {
  user: User
}

export function AdminDashboard({ user }: Props) {
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  const [name, setName] = useState('Core VPN')
  const [userId, setUserId] = useState('')
  const [resellerId, setResellerId] = useState('')
  const [endpoint, setEndpoint] = useState('vpn.example.com:443')

  const loadServices = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await fetchServices()
      setServices(result.items)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadServices()
  }, [])

  const onCreateService = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFormError(null)
    setCreating(true)
    try {
      if (!userId) throw new Error('User ID is required')
      await createService({
        name,
        user_id: Number(userId),
        reseller_id: resellerId ? Number(resellerId) : null,
        endpoint,
      })
      setName('Core VPN')
      setUserId('')
      setResellerId('')
      setEndpoint('vpn.example.com:443')
      await loadServices()
    } catch (err) {
      setFormError((err as Error).message)
    } finally {
      setCreating(false)
    }
  }

  const onEnsureToken = async (serviceId: number) => {
    try {
      const token = await ensureServiceToken(serviceId)
      setServices((prev) =>
        prev.map((svc) => (svc.id === serviceId ? { ...svc, subscription_token: token } : svc)),
      )
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const onCopyLink = async (token: string) => {
    const link = buildSubscriptionLink(token)
    await navigator.clipboard.writeText(link)
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <div className="mx-auto max-w-5xl px-6 py-12">
        <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        <p className="mt-2 text-slate-300">Welcome back, {user.username}. Manage your VPN fleet and resellers here.</p>
        <div className="mt-8 grid gap-6 lg:grid-cols-5">
          <form onSubmit={onCreateService} className="lg:col-span-2 space-y-4 rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
            <h2 className="text-lg font-semibold">Create Service</h2>
            <div>
              <label className="text-sm text-slate-300" htmlFor="name">
                Name
              </label>
              <input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1 w-full rounded-lg bg-slate-900/70 px-3 py-2 text-white ring-1 ring-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                required
              />
            </div>
            <div>
              <label className="text-sm text-slate-300" htmlFor="user">
                User ID
              </label>
              <input
                id="user"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="mt-1 w-full rounded-lg bg-slate-900/70 px-3 py-2 text-white ring-1 ring-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="User ID"
                required
              />
            </div>
            <div>
              <label className="text-sm text-slate-300" htmlFor="reseller">
                Reseller ID (optional)
              </label>
              <input
                id="reseller"
                value={resellerId}
                onChange={(e) => setResellerId(e.target.value)}
                className="mt-1 w-full rounded-lg bg-slate-900/70 px-3 py-2 text-white ring-1 ring-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="Reseller scope"
              />
            </div>
            <div>
              <label className="text-sm text-slate-300" htmlFor="endpoint">
                Endpoint (host:port)
              </label>
              <input
                id="endpoint"
                value={endpoint}
                onChange={(e) => setEndpoint(e.target.value)}
                className="mt-1 w-full rounded-lg bg-slate-900/70 px-3 py-2 text-white ring-1 ring-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="vpn.example.com:443"
              />
            </div>
            {formError ? <p className="text-sm text-rose-400">{formError}</p> : null}
            <button
              type="submit"
              disabled={creating}
              className="w-full rounded-lg bg-emerald-500 px-4 py-2 font-semibold text-slate-900 shadow-lg transition hover:bg-emerald-400 disabled:opacity-70"
            >
              {creating ? 'Creating…' : 'Create service'}
            </button>
          </form>

          <div className="lg:col-span-3 space-y-3 rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Services</h2>
              <button
                className="text-sm text-emerald-400 hover:text-emerald-300"
                onClick={() => {
                  void loadServices()
                }}
              >
                Refresh
              </button>
            </div>
            {loading ? <p className="text-slate-300">Loading services…</p> : null}
            {error ? <p className="text-rose-400">{error}</p> : null}
            {!loading && services.length === 0 ? <p className="text-slate-300">No services yet.</p> : null}

            <div className="space-y-4">
              {services.map((svc) => (
                <div key={svc.id} className="rounded-lg bg-slate-900/60 p-4 ring-1 ring-slate-700">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-slate-400">Service #{svc.id}</p>
                      <h3 className="text-xl font-semibold">{svc.name}</h3>
                      <p className="text-sm text-slate-300">User ID: {svc.user_id}</p>
                      {svc.endpoint ? <p className="text-sm text-slate-300">Endpoint: {svc.endpoint}</p> : null}
                    </div>
                    <button
                      className="rounded bg-slate-700 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-600"
                      onClick={() => void onEnsureToken(svc.id)}
                    >
                      Ensure token
                    </button>
                  </div>
                  {svc.subscription_token ? (
                    <div className="mt-3 space-y-1 rounded-lg bg-slate-800/60 p-3 text-sm ring-1 ring-slate-700">
                      <p className="font-mono text-emerald-300 break-all">Token: {svc.subscription_token.token}</p>
                      <div className="flex flex-wrap items-center gap-3">
                        <span className="text-slate-300">Subscription link:</span>
                        <code className="rounded bg-slate-900/80 px-2 py-1 font-mono text-xs">
                          {buildSubscriptionLink(svc.subscription_token.token)}
                        </code>
                        <button
                          className="rounded bg-emerald-500 px-2 py-1 text-xs font-semibold text-slate-900 hover:bg-emerald-400"
                          onClick={() => void onCopyLink(svc.subscription_token!.token)}
                        >
                          Copy link
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="mt-2 text-sm text-amber-300">No token yet. Generate to enable subscriptions.</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
