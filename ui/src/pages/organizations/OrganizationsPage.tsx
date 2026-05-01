import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Plus, Building2, Loader2, AlertCircle, ChevronRight, Star } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { organizationsApi } from '@/api/organizations'
import { authApi } from '@/api/auth'
import { useAuth } from '@/context/AuthContext'
import { PageHeader } from '@/components/ui/PageHeader'
import type { OrgSummary } from '@/types'

const createSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
})
type CreateForm = z.infer<typeof createSchema>

function CreateOrgModal({ onClose }: { onClose: () => void }) {
  const queryClient = useQueryClient()
  const { completeOrgSelection } = useAuth()
  const [error, setError] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<CreateForm>({
    resolver: zodResolver(createSchema),
  })

  const mutation = useMutation({
    mutationFn: async (data: CreateForm) => {
      const org = await organizationsApi.create(data)
      // Refresh token so the new org appears in JWT context
      const tokens = await authApi.switchOrg(org.id)
      return { org, tokens }
    },
    onSuccess: ({ tokens }) => {
      completeOrgSelection(tokens.access_token, tokens.refresh_token)
      queryClient.invalidateQueries({ queryKey: ['my-orgs'] })
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
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Organization Name</label>
            <input
              {...register('name')}
              placeholder="Acme Corp"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.name && <p className="text-rose-500 text-xs mt-1">{errors.name.message}</p>}
          </div>

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose}
              className="flex-1 py-2 px-4 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50">
              Cancel
            </button>
            <button type="submit" disabled={isSubmitting || mutation.isPending}
              className="flex-1 flex items-center justify-center gap-2 py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-60">
              {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function OrgCard({ org, isCurrent }: { org: OrgSummary; isCurrent: boolean }) {
  const navigate = useNavigate()
  const { completeOrgSelection } = useAuth()
  const queryClient = useQueryClient()

  const switchMutation = useMutation({
    mutationFn: () => authApi.switchOrg(org.id),
    onSuccess: (tokens) => {
      completeOrgSelection(tokens.access_token, tokens.refresh_token)
      queryClient.invalidateQueries()
      navigate(`/organizations/${org.id}`)
    },
  })

  return (
    <div
      className={`bg-white rounded-xl border p-5 cursor-pointer transition-all group ${
        isCurrent ? 'border-indigo-300 shadow-sm' : 'border-slate-200 hover:border-indigo-300 hover:shadow-sm'
      }`}
      onClick={() => isCurrent ? navigate(`/organizations/${org.id}`) : switchMutation.mutate()}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-700 font-bold text-sm uppercase">
            {org.name[0]}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <p className="font-semibold text-slate-900">{org.name}</p>
              {org.is_default && <Star className="h-3.5 w-3.5 text-amber-400 fill-amber-400" title="Default" />}
              {isCurrent && (
                <span className="text-xs px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded font-medium">Active</span>
              )}
            </div>
            <p className="text-xs text-slate-400 capitalize mt-0.5">{org.role}</p>
          </div>
        </div>
        {switchMutation.isPending
          ? <Loader2 className="h-4 w-4 animate-spin text-indigo-500" />
          : <ChevronRight className="h-4 w-4 text-slate-400 group-hover:text-indigo-500 transition-colors" />
        }
      </div>
    </div>
  )
}

export function OrganizationsPage() {
  const { user } = useAuth()
  const [showCreate, setShowCreate] = useState(false)

  const { data: orgs = [], isLoading } = useQuery({
    queryKey: ['my-orgs'],
    queryFn: authApi.myOrgs,
    enabled: !!user,
  })

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <PageHeader
        title="Organizations"
        description="Manage your organizations"
        action={
          <button onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors">
            <Plus className="h-4 w-4" />
            New Organization
          </button>
        }
      />

      {isLoading && (
        <div className="flex items-center gap-2 text-slate-500 text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />Loading…
        </div>
      )}

      <div className="space-y-3">
        {orgs.map((org) => (
          <OrgCard key={org.id} org={org} isCurrent={org.id === user?.org_id} />
        ))}
      </div>

      {!isLoading && orgs.length === 0 && (
        <div className="text-center py-12">
          <Building2 className="h-10 w-10 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 mb-4">You don't belong to any organization yet.</p>
          <button onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium">
            <Plus className="h-4 w-4" />Create your first organization
          </button>
        </div>
      )}

      {showCreate && <CreateOrgModal onClose={() => setShowCreate(false)} />}
    </div>
  )
}
