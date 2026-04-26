import { useQuery } from '@tanstack/react-query'
import { Building2, Users, Shield, Globe, AppWindow, Activity } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { organizationsApi } from '@/api/organizations'
import { rolesApi } from '@/api/roles'
import { endpointsApi } from '@/api/endpoints'
import { StatCard } from '@/components/ui/StatCard'
import { PageHeader } from '@/components/ui/PageHeader'

export function DashboardPage() {
  const { user } = useAuth()
  const orgId = user?.org_id ?? ''

  const { data: org } = useQuery({
    queryKey: ['org', orgId],
    queryFn: () => organizationsApi.getById(orgId),
    enabled: !!orgId,
  })

  const { data: roles = [] } = useQuery({
    queryKey: ['roles', orgId],
    queryFn: () => rolesApi.list(orgId),
    enabled: !!orgId,
  })

  const { data: endpoints = [] } = useQuery({
    queryKey: ['endpoints', orgId],
    queryFn: () => endpointsApi.list(orgId),
    enabled: !!orgId,
  })

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <PageHeader
        title="Dashboard"
        description={`Overview for ${org?.name ?? 'your organization'}`}
      />

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Organization" value={org?.name ?? '—'} icon={Building2} color="indigo" />
        <StatCard label="Roles Defined" value={roles.length} icon={Shield} color="emerald" />
        <StatCard label="Endpoints Registered" value={endpoints.length} icon={Globe} color="amber" />
        <StatCard
          label="Entra ID"
          value={org?.entra_id_tenant_id ? 'Connected' : 'Not set'}
          icon={Activity}
          color={org?.entra_id_tenant_id ? 'emerald' : 'rose'}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Organization info */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Building2 className="h-4 w-4 text-indigo-500" />
            Organization Details
          </h3>
          {org ? (
            <dl className="space-y-2.5">
              {[
                { label: 'Name', value: org.name },
                { label: 'ID', value: org.id },
                { label: 'Status', value: org.is_active ? 'Active' : 'Inactive' },
                { label: 'Entra Tenant', value: org.entra_id_tenant_id ?? 'Not configured' },
                {
                  label: 'Created',
                  value: new Date(org.created_at).toLocaleDateString(),
                },
              ].map(({ label, value }) => (
                <div key={label} className="flex justify-between text-sm">
                  <dt className="text-slate-500">{label}</dt>
                  <dd className="text-slate-800 font-medium text-right max-w-xs truncate">
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-slate-400 text-sm">Loading organization details…</p>
          )}
        </div>

        {/* Roles list */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
            <Shield className="h-4 w-4 text-emerald-500" />
            Active Roles
          </h3>
          {roles.length > 0 ? (
            <ul className="space-y-2">
              {roles.map((role) => (
                <li
                  key={role.id}
                  className="flex items-center justify-between text-sm p-2.5 rounded-lg bg-slate-50"
                >
                  <span className="font-medium text-slate-800">{role.name}</span>
                  <span className="text-slate-400 text-xs">
                    {Object.keys(role.permissions).length} endpoint
                    {Object.keys(role.permissions).length !== 1 ? 's' : ''}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate-400 text-sm">No roles defined yet.</p>
          )}
        </div>

        {/* Quick actions */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 lg:col-span-2">
          <h3 className="font-semibold text-slate-800 mb-4">Quick Actions</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Manage Roles', href: '/roles', icon: Shield, color: 'text-emerald-600 bg-emerald-50' },
              { label: 'Register Endpoint', href: '/endpoints', icon: Globe, color: 'text-amber-600 bg-amber-50' },
              { label: 'Add Application', href: '/apps', icon: AppWindow, color: 'text-indigo-600 bg-indigo-50' },
              { label: 'View Users', href: '/users', icon: Users, color: 'text-rose-600 bg-rose-50' },
            ].map(({ label, href, icon: Icon, color }) => (
              <a
                key={href}
                href={href}
                className="flex flex-col items-center gap-2 p-4 rounded-xl border border-slate-200 hover:border-indigo-200 hover:bg-indigo-50/30 transition-colors"
              >
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color}`}>
                  <Icon className="h-5 w-5" />
                </div>
                <span className="text-xs font-medium text-slate-700 text-center">{label}</span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
