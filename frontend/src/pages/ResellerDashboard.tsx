import { User } from '../api'

interface Props {
  user: User
}

export function ResellerDashboard({ user }: Props) {
  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <div className="mx-auto max-w-5xl px-6 py-12">
        <h1 className="text-3xl font-bold">Reseller Dashboard</h1>
        <p className="mt-2 text-slate-300">Hello {user.username}. Manage downstream tenants and VPN access here.</p>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
            <h2 className="text-lg font-semibold">Tenants</h2>
            <p className="text-sm text-slate-300">Placeholder for tenant and subscription management.</p>
          </div>
          <div className="rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
            <h2 className="text-lg font-semibold">Activity</h2>
            <p className="text-sm text-slate-300">Track VPN usage and recent logins.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
