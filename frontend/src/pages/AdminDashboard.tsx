import { User } from '../api'

interface Props {
  user: User
}

export function AdminDashboard({ user }: Props) {
  return (
    <div className="min-h-screen bg-slate-900 text-white">
      <div className="mx-auto max-w-5xl px-6 py-12">
        <h1 className="text-3xl font-bold">Admin Dashboard</h1>
        <p className="mt-2 text-slate-300">Welcome back, {user.username}. Manage your VPN fleet and resellers here.</p>
        <div className="mt-8 grid gap-4 md:grid-cols-2">
          <div className="rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
            <h2 className="text-lg font-semibold">Gateways</h2>
            <p className="text-sm text-slate-300">Track connected VPN gateways and their health.</p>
          </div>
          <div className="rounded-xl bg-slate-800/80 p-5 ring-1 ring-slate-700">
            <h2 className="text-lg font-semibold">Users</h2>
            <p className="text-sm text-slate-300">Provision admins and resellers with role-based access control.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
