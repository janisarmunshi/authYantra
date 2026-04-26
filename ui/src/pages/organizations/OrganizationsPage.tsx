import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Plus, Building2, Loader2, AlertCircle, ChevronRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { organizationsApi } from '@/api/organizations'
import { useAuth } from '@/context/AuthContext'
import { PageHeader } from '@/components/ui/PageHeader'
import type { Organization } from '@/types'

const createSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
})
type CreateForm = z.infer<typeof createSchema>

function CreateOrgModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
  })

  const mutation = useMutation({
    mutationFn: (data: CreateForm) => organizationsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org'] })
      onClose()
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e?.response?.data?.detail ?? 'Failed to create organization')
    },
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-base font-semibold text-slate-900 mb-5">Create Organization</h3>

        {error && (
          <div className="flex items-start gap-2 p-3 mb-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Organization Name
            </label>
            <input
              {...register('name')}
              placeholder="Acme Corp"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.name && (
              <p className="text-rose-500 text-xs mt-1">{errors.name.message}</p>
            )}
          </div>

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 px-4 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || mutation.isPending}
              className="flex-1 flex items-center justify-center gap-2 py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-60"
            >
              {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function OrgCard({ org }: { org: Organization }) {
  const navigate = useNavigate()
  return (
    <div
      onClick={() => navigate(`/organizations/${org.id}`)}
      className="bg-white rounded-xl border border-slate-200 p-5 hover:border-indigo-300 hover:shadow-sm cursor-pointer transition-all group"
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-sm uppercase">
            {org.name[0]}
          </div>
          <div>
            <p className="font-semibold text-slate-900">{org.name}</p>
            <p className="text-xs text-slate-400 font-mono mt-0.5">{org.id}</p>
          </div>
        </div>
        <ChevronRight className="h-4 w-4 text-slate-400 group-hover:text-indigo-500 transition-colors" />
      </div>
      <div className="flex items-center gap-4 mt-4">
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            org.is_active
              ? 'bg-emerald-100 text-emerald-700'
              : 'bg-slate-100 text-slate-500'
          }`}
        >
          {org.is_active ? 'Active' : 'Inactive'}
        </span>
        {org.entra_id_tenant_id && (
          <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-blue-100 text-blue-700">
            Entra ID
          </span>
        )}
        <span className="text-xs text-slate-400 ml-auto">
          {new Date(org.created_at).toLocaleDateString()}
        </span>
      </div>
    </div>
  )
}

export function OrganizationsPage() {
  const { user } = useAuth()
  const [showCreate, setShowCreate] = useState(false)

  // In real multi-tenant setup, you'd list orgs from an admin endpoint.
  // For now we show the current user's org.
  const { data: org, isLoading } = useQuery({
    queryKey: ['org', user?.org_id],
    queryFn: () => organizationsApi.getById(user!.org_id),
    enabled: !!user?.org_id,
  })

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <PageHeader
        title="Organizations"
        description="Manage organizations and their configurations"
        action={
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="h-4 w-4" />
            New Organization
          </button>
        }
      />

      {isLoading && (
        <div className="flex items-center gap-2 text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading…
        </div>
      )}

      <div className="space-y-3">
        {org && <OrgCard org={org} />}
      </div>

      {!isLoading && !org && (
        <div className="text-center py-12">
          <Building2 className="h-10 w-10 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500">No organizations found.</p>
        </div>
      )}

      {showCreate && <CreateOrgModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
