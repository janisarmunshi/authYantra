import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ShieldCheck, Loader2, AlertCircle, CheckCircle2, XCircle, Filter } from 'lucide-react'
import { auditApi, type AuditLogFilters } from '@/api/audit'
import { useAuth } from '@/context/AuthContext'
import { PageHeader } from '@/components/ui/PageHeader'
import type { AuditLog } from '@/types'

const ACTION_COLORS: Record<string, string> = {
  'user.login': 'bg-indigo-100 text-indigo-700',
  'user.login_failed': 'bg-rose-100 text-rose-700',
  'org.create': 'bg-emerald-100 text-emerald-700',
  'org.delete': 'bg-rose-100 text-rose-700',
  'org.member_added': 'bg-blue-100 text-blue-700',
  'org.invite_accepted': 'bg-teal-100 text-teal-700',
  'mfa.totp_activated': 'bg-violet-100 text-violet-700',
  'mfa.disabled': 'bg-amber-100 text-amber-700',
}

function LogRow({ log }: { log: AuditLog }) {
  const [expanded, setExpanded] = useState(false)
  const color = ACTION_COLORS[log.action] ?? 'bg-slate-100 text-slate-600'

  return (
    <>
      <tr
        className="border-b border-slate-100 hover:bg-slate-50 cursor-pointer transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="px-4 py-3 text-xs text-slate-400 whitespace-nowrap">
          {new Date(log.created_at).toLocaleString()}
        </td>
        <td className="px-4 py-3">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${color}`}>
            {log.action}
          </span>
        </td>
        <td className="px-4 py-3 text-xs text-slate-600 hidden md:table-cell">
          {log.resource_type && (
            <span className="text-slate-400">{log.resource_type}: </span>
          )}
          <span className="font-mono">{log.resource_id?.slice(0, 8) ?? '—'}</span>
        </td>
        <td className="px-4 py-3 text-xs text-slate-500 hidden sm:table-cell">
          {log.user_id?.slice(0, 8) ?? '—'}
        </td>
        <td className="px-4 py-3">
          {log.status === 'success' ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
          ) : (
            <XCircle className="h-4 w-4 text-rose-500" />
          )}
        </td>
        <td className="px-4 py-3 text-xs text-slate-400 hidden lg:table-cell">
          {log.ip_address ?? '—'}
        </td>
      </tr>
      {expanded && log.details && (
        <tr className="bg-slate-50">
          <td colSpan={6} className="px-4 py-3">
            <pre className="text-xs font-mono text-slate-600 whitespace-pre-wrap break-all">
              {JSON.stringify(log.details, null, 2)}
            </pre>
          </td>
        </tr>
      )}
    </>
  )
}

export function AuditLogsPage() {
  const { user } = useAuth()
  const orgId = user?.org_id ?? ''
  const [filters, setFilters] = useState<AuditLogFilters>({ limit: 100 })
  const [actionFilter, setActionFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')

  const { data: logs = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['audit-logs', orgId, filters],
    queryFn: () => auditApi.list(orgId, filters),
    enabled: !!orgId,
  })

  const applyFilters = () => {
    setFilters({
      limit: 100,
      action: actionFilter || undefined,
      status: (statusFilter as 'success' | 'failure') || undefined,
    })
  }

  if (!orgId) {
    return (
      <div className="p-6 text-center py-20">
        <ShieldCheck className="h-10 w-10 text-slate-300 mx-auto mb-3" />
        <p className="text-slate-500">Select an organization to view audit logs.</p>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <PageHeader
        title="Audit Logs"
        description="Immutable record of all security-relevant events in your organization"
      />

      {/* Filters */}
      <div className="bg-white rounded-xl border border-slate-200 p-4 mb-5 flex flex-wrap gap-3 items-end">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Action</label>
          <input
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            placeholder="e.g. user.login"
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-48"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">Status</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">All</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
          </select>
        </div>
        <button
          onClick={applyFilters}
          className="flex items-center gap-2 px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium"
        >
          <Filter className="h-3.5 w-3.5" />
          Filter
        </button>
        <button
          onClick={() => { setActionFilter(''); setStatusFilter(''); setFilters({ limit: 100 }) }}
          className="px-4 py-1.5 border border-slate-300 text-slate-600 rounded-lg text-sm"
        >
          Clear
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        {isLoading && (
          <div className="flex items-center justify-center gap-2 py-12 text-slate-400">
            <Loader2 className="h-5 w-5 animate-spin" />
            Loading audit logs…
          </div>
        )}
        {isError && (
          <div className="flex items-center gap-2 p-4 text-rose-600 text-sm">
            <AlertCircle className="h-4 w-4" />
            Failed to load audit logs. You may need admin access.
          </div>
        )}
        {!isLoading && !isError && (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Time</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden md:table-cell">Resource</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden sm:table-cell">User ID</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden lg:table-cell">IP</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => <LogRow key={log.id} log={log} />)}
              </tbody>
            </table>
            {logs.length === 0 && (
              <div className="text-center py-12">
                <ShieldCheck className="h-10 w-10 text-slate-300 mx-auto mb-3" />
                <p className="text-slate-500 text-sm">No audit events found.</p>
              </div>
            )}
          </div>
        )}
      </div>
      <p className="text-xs text-slate-400 mt-2">Showing up to {filters.limit} most recent events. Click a row to expand details.</p>
    </div>
  )
}
