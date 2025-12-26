import { FormEvent, useEffect, useState } from 'react'
import {
  applyXrayConfig,
  API_BASE_URL,
  buildSubscriptionLink,
  createService,
  ensureServiceToken,
  fetchServices,
  fetchXrayStatus,
  renderXrayConfig,
  listPlans,
  listBackups,
  createBackup,
  restoreBackup,
  uploadBackup,
  migrationPreview,
  migrationRun,
  type Service,
  type User,
  type XrayStatus,
  type ResellerPlan,
  type BackupInfo,
  listNodes,
  createNode,
  setServiceNodes,
  type Node,
} from '../api'

interface Props {
  user: User
}

export function AdminDashboard({ user }: Props) {
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [xrayStatus, setXrayStatus] = useState<XrayStatus | null>(null)
  const [xrayError, setXrayError] = useState<string | null>(null)
  const [renderedConfig, setRenderedConfig] = useState<string | null>(null)
  const [applying, setApplying] = useState(false)
  const [rendering, setRendering] = useState(false)
  const [plans, setPlans] = useState<ResellerPlan[]>([])
  const [backups, setBackups] = useState<BackupInfo[]>([])
  const [backupError, setBackupError] = useState<string | null>(null)
  const [backupLoading, setBackupLoading] = useState(false)
  const [migrationMessage, setMigrationMessage] = useState<string | null>(null)
  const [nodes, setNodes] = useState<Node[]>([])
  const [nodeForm, setNodeForm] = useState({ name: '', location: '', ip_address: '', api_base_url: '', auth_token: '' })
  const [serviceNodeServiceId, setServiceNodeServiceId] = useState('')
  const [serviceNodeIds, setServiceNodeIds] = useState('')

  const [name, setName] = useState('Core VPN')
  const [userId, setUserId] = useState('')
  const [resellerId, setResellerId] = useState('')
  const [endpoint, setEndpoint] = useState('vpn.example.com:443')
  const [trafficLimit, setTrafficLimit] = useState('')
  const [expiresAt, setExpiresAt] = useState('')
  const [ipLimit, setIpLimit] = useState('')
  const [concurrentLimit, setConcurrentLimit] = useState('')
  const [isActive, setIsActive] = useState(true)

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

  const loadXrayStatus = async () => {
    setXrayError(null)
    try {
      const status = await fetchXrayStatus()
      setXrayStatus(status)
    } catch (err) {
      setXrayError((err as Error).message)
    }
  }

  useEffect(() => {
    void loadServices()
    void loadXrayStatus()
    void loadPlans()
    void loadBackups()
    void loadNodes()
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
        traffic_limit_bytes: trafficLimit ? Number(trafficLimit) : null,
        expires_at: expiresAt ? new Date(expiresAt).toISOString() : undefined,
        ip_limit: ipLimit ? Number(ipLimit) : null,
        concurrent_limit: concurrentLimit ? Number(concurrentLimit) : null,
        is_active: isActive,
      })
      setName('Core VPN')
      setUserId('')
      setResellerId('')
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

  const loadNodes = async () => {
    try {
      const res = await listNodes()
      setNodes(res)
    } catch (err) {
      // ignore
    }
  }

  const onCreateNode = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    try {
      await createNode(nodeForm)
      setNodeForm({ name: '', location: '', ip_address: '', api_base_url: '', auth_token: '' })
      await loadNodes()
    } catch (err) {
      setBackupError((err as Error).message)
    }
  }

  const onAssignServiceNodes = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    try {
      const ids = serviceNodeIds
        .split(',')
        .map((v) => v.trim())
        .filter(Boolean)
        .map((v) => Number(v))
      await setServiceNodes(Number(serviceNodeServiceId), ids)
      setServiceNodeIds('')
      setServiceNodeServiceId('')
    } catch (err) {
      setBackupError((err as Error).message)
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

  const onRenderConfig = async () => {
    setRendering(true)
    setXrayError(null)
    try {
      const res = await renderXrayConfig()
      setRenderedConfig(JSON.stringify(res.config, null, 2))
      await loadXrayStatus()
    } catch (err) {
      setXrayError((err as Error).message)
    } finally {
      setRendering(false)
    }
  }

  const onApplyConfig = async () => {
    setApplying(true)
    setXrayError(null)
    try {
      await applyXrayConfig()
      await loadXrayStatus()
    } catch (err) {
      setXrayError((err as Error).message)
    } finally {
      setApplying(false)
    }
  }

  const loadPlans = async () => {
    try {
      const res = await listPlans()
      setPlans(res)
    } catch (err) {
      // ignore in MVP
    }
  }

  const loadBackups = async () => {
    setBackupError(null)
    try {
      const res = await listBackups()
      setBackups(res)
    } catch (err) {
      setBackupError((err as Error).message)
    }
  }

  const onCreateBackup = async () => {
    setBackupLoading(true)
    setBackupError(null)
    try {
      await createBackup()
      await loadBackups()
    } catch (err) {
      setBackupError((err as Error).message)
    } finally {
      setBackupLoading(false)
    }
  }

  const onRestoreBackup = async (id: string) => {
    setBackupLoading(true)
    setBackupError(null)
    try {
      await restoreBackup(id)
      setBackupError("Restore triggered")
    } catch (err) {
      setBackupError((err as Error).message)
    } finally {
      setBackupLoading(false)
    }
  }

  const onUploadBackup = async (file: File) => {
    setBackupLoading(true)
    setBackupError(null)
    try {
      await uploadBackup(file)
      await loadBackups()
    } catch (err) {
      setBackupError((err as Error).message)
    } finally {
      setBackupLoading(false)
    }
  }

  const onRunMigration = async (file: File) => {
    setMigrationMessage(null)
    try {
      const preview = await migrationPreview(file)
      const result = await migrationRun(file)
      setMigrationMessage(`Preview: ${preview.users} users, run created ${result.created_users} users`)
    } catch (err) {
      setMigrationMessage((err as Error).message)
    }
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

          <div className="lg:col-span-5 space-y-3 rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Xray config</h2>
                <p className="text-sm text-slate-300">
                  Render VLESS config from the database and apply it to the shared config volume.
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => void onRenderConfig()}
                  disabled={rendering}
                  className="rounded bg-slate-700 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-600 disabled:opacity-70"
                >
                  {rendering ? 'Rendering…' : 'Render config'}
                </button>
                <button
                  onClick={() => void onApplyConfig()}
                  disabled={applying}
                  className="rounded bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-900 hover:bg-emerald-400 disabled:opacity-70"
                >
                  {applying ? 'Applying…' : 'Apply config'}
                </button>
              </div>
            </div>
            {xrayError ? <p className="text-sm text-rose-400">{xrayError}</p> : null}
            {xrayStatus ? (
              <div className="flex flex-wrap items-center gap-4 text-sm text-slate-200">
                <span
                  className={`rounded-full px-3 py-1 text-xs font-semibold ${
                    xrayStatus.healthy ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                  }`}
                >
                  Xray {xrayStatus.healthy ? 'Healthy' : 'Unreachable'}
                </span>
                {xrayStatus.last_apply_status ? <span>Status: {xrayStatus.last_apply_status}</span> : null}
                {xrayStatus.last_applied_at ? <span>Last applied: {new Date(xrayStatus.last_applied_at).toLocaleString()}</span> : null}
                {xrayStatus.last_apply_error ? <span className="text-rose-300">Error: {xrayStatus.last_apply_error}</span> : null}
              </div>
            ) : null}
            {renderedConfig ? (
              <pre className="max-h-80 overflow-auto rounded-lg bg-slate-900/70 p-3 text-xs text-emerald-200 ring-1 ring-slate-700">
                {renderedConfig}
              </pre>
            ) : null}
          </div>

          <div className="lg:col-span-5 space-y-3 rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
            <h2 className="text-lg font-semibold">Reseller plans (read-only)</h2>
            <div className="grid gap-3 md:grid-cols-3">
              {plans.map((plan) => (
                <div key={plan.id} className="rounded-lg bg-slate-900/60 p-3 text-sm ring-1 ring-slate-700">
                  <div className="font-semibold text-white">{plan.name}</div>
                  <div className="text-slate-300">Price: {plan.price}</div>
                  <div className="text-slate-300">Duration: {plan.duration_days} days</div>
                  {plan.max_services ? <div className="text-slate-300">Max services: {plan.max_services}</div> : null}
                  {plan.max_users ? <div className="text-slate-300">Max users: {plan.max_users}</div> : null}
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-5 space-y-3 rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
            <h2 className="text-lg font-semibold">Nodes</h2>
            <form className="grid gap-3 md:grid-cols-5" onSubmit={onCreateNode}>
              <input
                className="rounded bg-slate-900/70 px-3 py-2 text-sm text-white ring-1 ring-slate-700 focus:ring-emerald-500"
                placeholder="Name"
                value={nodeForm.name}
                onChange={(e) => setNodeForm({ ...nodeForm, name: e.target.value })}
              />
              <input
                className="rounded bg-slate-900/70 px-3 py-2 text-sm text-white ring-1 ring-slate-700 focus:ring-emerald-500"
                placeholder="Location"
                value={nodeForm.location}
                onChange={(e) => setNodeForm({ ...nodeForm, location: e.target.value })}
              />
              <input
                className="rounded bg-slate-900/70 px-3 py-2 text-sm text-white ring-1 ring-slate-700 focus:ring-emerald-500"
                placeholder="IP"
                value={nodeForm.ip_address}
                onChange={(e) => setNodeForm({ ...nodeForm, ip_address: e.target.value })}
              />
              <input
                className="rounded bg-slate-900/70 px-3 py-2 text-sm text-white ring-1 ring-slate-700 focus:ring-emerald-500"
                placeholder="API URL"
                value={nodeForm.api_base_url}
                onChange={(e) => setNodeForm({ ...nodeForm, api_base_url: e.target.value })}
              />
              <input
                className="rounded bg-slate-900/70 px-3 py-2 text-sm text-white ring-1 ring-slate-700 focus:ring-emerald-500"
                placeholder="Token"
                value={nodeForm.auth_token}
                onChange={(e) => setNodeForm({ ...nodeForm, auth_token: e.target.value })}
              />
              <button className="rounded bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-900 hover:bg-emerald-400">Add</button>
            </form>
            <div className="grid gap-3 md:grid-cols-3">
              {nodes.map((node) => (
                <div key={node.id} className="rounded bg-slate-900/60 p-3 text-sm ring-1 ring-slate-700">
                  <div className="font-semibold text-white">{node.name}</div>
                  <div className="text-slate-300">{node.location}</div>
                  <div className="text-slate-400 text-xs">Last seen: {node.last_seen_at || 'n/a'}</div>
                </div>
              ))}
            </div>
            <form className="flex flex-wrap gap-2 text-sm" onSubmit={onAssignServiceNodes}>
              <input
                className="rounded bg-slate-900/70 px-3 py-2 text-sm text-white ring-1 ring-slate-700 focus:ring-emerald-500"
                placeholder="Service ID"
                value={serviceNodeServiceId}
                onChange={(e) => setServiceNodeServiceId(e.target.value)}
              />
              <input
                className="rounded bg-slate-900/70 px-3 py-2 text-sm text-white ring-1 ring-slate-700 focus:ring-emerald-500"
                placeholder="Node IDs (comma)"
                value={serviceNodeIds}
                onChange={(e) => setServiceNodeIds(e.target.value)}
              />
              <button className="rounded bg-slate-700 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-600">Assign</button>
            </form>
          </div>

          <div className="lg:col-span-5 space-y-3 rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-semibold">Backups</h2>
              <div className="flex gap-2">
                <button
                  onClick={() => void onCreateBackup()}
                  disabled={backupLoading}
                  className="rounded bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-900 hover:bg-emerald-400 disabled:opacity-70"
                >
                  {backupLoading ? 'Working…' : 'Create backup'}
                </button>
                <label className="cursor-pointer rounded bg-slate-700 px-3 py-2 text-sm font-semibold text-white hover:bg-slate-600">
                  Upload
                  <input
                    type="file"
                    className="hidden"
                    accept=".tar.gz"
                    onChange={(e) => {
                      const f = e.target.files?.[0]
                      if (f) void onUploadBackup(f)
                    }}
                  />
                </label>
              </div>
            </div>
            {backupError ? <p className="text-sm text-rose-400">{backupError}</p> : null}
            <div className="space-y-2 text-sm text-slate-200">
              {backups.map((b) => (
                <div key={b.id} className="flex flex-wrap items-center gap-3 rounded bg-slate-900/60 p-3 ring-1 ring-slate-700">
                  <span className="font-mono text-xs">#{b.id}</span>
                  {b.created_at ? <span>Created: {b.created_at}</span> : null}
                  <button
                    className="rounded bg-rose-500 px-2 py-1 text-xs font-semibold text-white hover:bg-rose-400"
                    onClick={() => void onRestoreBackup(b.id)}
                  >
                    Restore
                  </button>
                  <a
                    className="rounded bg-slate-700 px-2 py-1 text-xs font-semibold text-white hover:bg-slate-600"
                    href={`${API_BASE_URL}/api/backups/${b.id}/download`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Download
                  </a>
                </div>
              ))}
            </div>
          </div>

          <div className="lg:col-span-5 space-y-3 rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
            <h2 className="text-lg font-semibold">Marzban migration</h2>
            <p className="text-sm text-slate-300">Import users/services/tokens via JSON export.</p>
            <input
              type="file"
              accept=".json"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) void onRunMigration(f)
              }}
              className="text-sm text-slate-200"
            />
            {migrationMessage ? <p className="text-sm text-emerald-300">{migrationMessage}</p> : null}
          </div>
        </div>
      </div>
    </div>
  )
}
