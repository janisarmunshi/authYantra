import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Plus, Globe, Loader2, AlertCircle, Check } from 'lucide-react'
import { endpointsApi } from '@/api/endpoints'
import { useAuth } from '@/context/AuthContext'
import { PageHeader } from '@/components/ui/PageHeader'

const ACTIONS = ['read', 'write', 'delete', 'modify'] as const

const endpointSchema = z.object({
  endpoint: z.string().min(1, 'Endpoint path is required').startsWith('/', 'Path must start with /'),
  actions: z.array(z.string()).min(1, 'Select at least one action'),
  description: z.string().optional(),
})
type EndpointForm = z.infer<typeof endpointSchema>

function RegisterModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<EndpointForm>({
    resolver: zodResolver(endpointSchema),
    defaultValues: { actions: ['read'] },
  })

  const selectedActions = watch('actions') ?? []

  const mutation = useMutation({
    mutationFn: (data: EndpointForm) =>
      endpointsApi.register(orgId, {
        endpoint: data.endpoint,
        actions: data.actions,
        description: data.description || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['endpoints', orgId] })
      onClose()
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e?.response?.data?.detail ?? 'Failed to register endpoint')
    },
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-base font-semibold text-slate-900 mb-5">Register Endpoint</h3>

        {error && (
          <div className="flex items-start gap-2 p-3 mb-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Endpoint Path</label>
            <input
              {...register('endpoint')}
              placeholder="/api/resource"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.endpoint && <p className="text-rose-500 text-xs mt-1">{errors.endpoint.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-2">Allowed Actions</label>
            <div className="flex flex-wrap gap-2">
              {ACTIONS.map((action) => {
                const checked = selectedActions.includes(action)
                return (
                  <label
                    key={action}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium cursor-pointer border transition-colors ${
                      checked
                        ? 'bg-indigo-100 border-indigo-300 text-indigo-700'
                        : 'bg-white border-slate-200 text-slate-500 hover:border-indigo-200'
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="sr-only"
                      checked={checked}
                      onChange={(e) => {
                        const updated = e.target.checked
                          ? [...selectedActions, action]
                          : selectedActions.filter((a) => a !== action)
                        setValue('actions', updated)
                      }}
                    />
                    {checked && <Check className="h-3.5 w-3.5" />}
                    {action}
                  </label>
                )
              })}
            </div>
            {errors.actions && <p className="text-rose-500 text-xs mt-1">{errors.actions.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Description <span className="text-slate-400 font-normal">(optional)</span>
            </label>
            <textarea
              {...register('description')}
              rows={2}
              placeholder="Describe what this endpoint does"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
          </div>

          <div className="flex gap-3 pt-1">
            <button type="button" onClick={onClose} className="flex-1 py-2 px-4 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50">
              Cancel
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex-1 flex items-center justify-center gap-2 py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-60"
            >
              {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Register
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function EndpointsPage() {
  const { user } = useAuth()
  const orgId = user?.org_id ?? ''
  const [showRegister, setShowRegister] = useState(false)

  const { data: endpoints = [], isLoading } = useQuery({
    queryKey: ['endpoints', orgId],
    queryFn: () => endpointsApi.list(orgId),
    enabled: !!orgId,
  })

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <PageHeader
        title="Registered Endpoints"
        description="Endpoints that can be used in role permission definitions"
        action={
          <button
            onClick={() => setShowRegister(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="h-4 w-4" />
            Register Endpoint
          </button>
        }
      />

      {isLoading ? (
        <div className="flex items-center gap-2 text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading…
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          {endpoints.length > 0 ? (
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50">
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Endpoint</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden md:table-cell">Description</th>
                  <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden lg:table-cell">Registered</th>
                </tr>
              </thead>
              <tbody>
                {endpoints.map((ep) => (
                  <tr key={ep.id} className="border-b border-slate-100 last:border-0 hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <code className="text-sm font-mono text-slate-800 bg-slate-100 px-2 py-0.5 rounded">
                        {ep.endpoint}
                      </code>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {ep.actions.map((a) => (
                          <span key={a} className="text-xs px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded font-medium">
                            {a}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-sm text-slate-500">{ep.description ?? '—'}</span>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell">
                      <span className="text-xs text-slate-400">
                        {new Date(ep.created_at).toLocaleDateString()}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="text-center py-12">
              <Globe className="h-10 w-10 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500 mb-1">No endpoints registered yet.</p>
              <p className="text-slate-400 text-sm">Register your API endpoints to use them in role permissions.</p>
            </div>
          )}
        </div>
      )}

      {showRegister && <RegisterModal orgId={orgId} onClose={() => setShowRegister(false)} />}
    </div>
  )
}
