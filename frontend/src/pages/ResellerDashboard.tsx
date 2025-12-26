import { FormEvent, useEffect, useState } from 'react'
import {
  buildSubscriptionLink,
  createService,
  ensureServiceToken,
  fetchResellerReport,
  fetchServices,
  listPlans,
  subscribePlan,
  type ResellerPlan,
  type ResellerReport,
  type Service,
  type User,
} from '../api'

interface Props {
  user: User
}

export function ResellerDashboard({ user }: Props) {
  const resellerId = 1
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [report, setReport] = useState<ResellerReport | null>(null)
  const [plans, setPlans] = useState<ResellerPlan[]>([])
  const [planError, setPlanError] = useState<string | null>(null)

  const [name, setName] = useState('Reseller VPN')
  const [userId, setUserId] = useState('')
  const [endpoint, setEndpoint] = useState('vpn.example.com:443')
  const [trafficLimit, setTrafficLimit] = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [ipLimit, setIpLimit] = useState('')
  const [concurrentLimit, setConcurrentLimit] = useState('')
  const [isActive, setIsActive] = useState(true)

  const loadServices = async () => {
    setError(null)
    setLoading(true)
    try {
      const res = await fetchServices()
      setServices(res.items)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadServices()
    void loadReport()
    void loadPlans()
  }, [])

  const loadReport = async () => {
    try {
      const rep = await fetchResellerReport(resellerId)
      setReport(rep)
    } catch (err) {
      setPlanError((err as Error).message)
    }
  }

  const loadPlans = async () => {
    try {
      const p = await listPlans()
      setPlans(p)
    } catch (err) {
      setPlanError((err as Error).message)
    }
  }

  const onCreateService = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setFormError(null)
    setCreating(true)
    try {
      if (!userId) throw new Error('User ID is required')
      await createService({
        name,
        user_id: Number(userId),
        endpoint,
        traffic_limit_bytes: trafficLimit ? Number(trafficLimit) : null,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : undefined,
        ip_limit: ipLimit ? Number(ipLimit) : null,
        concurrent_limit: concurrentLimit ? Number(concurrentLimit) : null,
        is_active: isActive,
      })
      setName('Reseller VPN')
      setUserId('')
      setEndpoint('vpn.example.com:443')
      setTrafficLimit('')
      setExpiresAt('')
      setIpLimit('')
      setConcurrentLimit('')
      setIsActive(true)
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

  const onSubscribe = async (planId: number) => {
    try {
      setPlanError(null)
      await subscribePlan(resellerId, planId)
      await loadReport()
    } catch (err) {
      setPlanError((err as Error).message)
    }
  }

  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <div className="mx-auto max-w-5xl px-6 py-12">
        <h1 className="text-3xl font-bold">Reseller Dashboard</h1>
        <p className="mt-2 text-slate-300">Hello {user.username}. Manage downstream tenants and VPN access here.</p>

        <div className="mt-6 space-y-4 rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
          <h2 className="text-lg font-semibold">Wallet & plan</h2>
          {planError ? <p className="text-sm text-rose-400">{planError}</p> : null}
          {report ? (
            <div className="flex flex-wrap gap-4 text-sm text-slate-200">
              <span className="rounded bg-slate-900/60 px-3 py-1">Wallet: {report.wallet_balance}</span>
              <span className="rounded bg-slate-900/60 px-3 py-1">Users: {report.users}</span>
              <span className="rounded bg-slate-900/60 px-3 py-1">Services: {report.services}</span>
            </div>
          ) : (
            <p className="text-sm text-slate-300">Loading report…</p>
          )}
          <div className="flex flex-wrap gap-3">
            {plans.map((plan) => (
              <button
                key={plan.id}
                className="rounded bg-emerald-500 px-3 py-1 text-sm font-semibold text-slate-900 hover:bg-emerald-400"
                onClick={() => void onSubscribe(plan.id)}
              >
                Buy {plan.name} (${plan.price})
              </button>
            ))}
          </div>
        </div>

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
              <label className="text-sm text-slate-300" htmlFor="user-id">
                User ID
              </label>
              <input
                id="user-id"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                className="mt-1 w-full rounded-lg bg-slate-900/70 px-3 py-2 text-white ring-1 ring-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                placeholder="User ID"
                required
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
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="text-sm text-slate-300" htmlFor="traffic-limit">
                  Traffic limit (bytes)
                </label>
                <input
                  id="traffic-limit"
                  value={trafficLimit}
                  onChange={(e) => setTrafficLimit(e.target.value)}
                  type="number"
                  min={0}
                  className="mt-1 w-full rounded-lg bg-slate-900/70 px-3 py-2 text-white ring-1 ring-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="e.g. 1073741824"
                />
              </div>
              <div>
                <label className="text-sm text-slate-300" htmlFor="expires-at">
                  Expires at
                </label>
                <input
                  id="expires-at"
                  value={expiresAt}
                  onChange={(e) => setExpiresAt(e.target.value)}
                  type="datetime-local"
                  className="mt-1 w-full rounded-lg bg-slate-900/70 px-3 py-2 text-white ring-1 ring-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-3">
              <div>
                <label className="text-sm text-slate-300" htmlFor="ip-limit">
                  IP limit
                </label>
                <input
                  id="ip-limit"
                  value={ipLimit}
                  onChange={(e) => setIpLimit(e.target.value)}
                  type="number"
                  min={0}
                  className="mt-1 w-full rounded-lg bg-slate-900/70 px-3 py-2 text-white ring-1 ring-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="e.g. 5"
                />
              </div>
              <div>
                <label className="text-sm text-slate-300" htmlFor="concurrent-limit">
                  Concurrent sessions
                </label>
                <input
                  id="concurrent-limit"
                  value={concurrentLimit}
                  onChange={(e) => setConcurrentLimit(e.target.value)}
                  type="number"
                  min={0}
                  className="mt-1 w-full rounded-lg bg-slate-900/70 px-3 py-2 text-white ring-1 ring-slate-700 focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="e.g. 3"
                />
              </div>
              <div className="flex items-end gap-2">
                <input
                  id="is-active"
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-600 bg-slate-900 text-emerald-500"
                />
                <label className="text-sm text-slate-300" htmlFor="is-active">
                  Active
                </label>
              </div>
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
              <h2 className="text-lg font-semibold">My Services</h2>
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
                      <div className="mt-1 flex flex-wrap gap-3 text-xs text-slate-300">
                        <span
                          className={`rounded-full px-2 py-1 ${
                            svc.is_active ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                          }`}
                        >
                          {svc.is_active ? 'Active' : 'Disabled'}
                        </span>
                        {svc.expires_at ? <span>Expires: {new Date(svc.expires_at).toLocaleString()}</span> : null}
                        {svc.traffic_limit_bytes ? (
                          <span>
                            Usage: {svc.traffic_used_bytes ?? 0}/{svc.traffic_limit_bytes} bytes
                          </span>
                        ) : (
                          <span>Usage: {svc.traffic_used_bytes ?? 0} bytes</span>
                        )}
                        {svc.ip_limit ? <span>IP limit: {svc.ip_limit}</span> : null}
                        {svc.concurrent_limit ? <span>Concurrent: {svc.concurrent_limit}</span> : null}
                      </div>
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
