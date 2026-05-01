import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm, useFieldArray } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  Plus, Shield, Loader2, AlertCircle, Trash2, Edit2, X, Check, ChevronDown, ChevronUp,
} from 'lucide-react'
import { rolesApi } from '@/api/roles'
import { endpointsApi } from '@/api/endpoints'
import { useAuth } from '@/context/AuthContext'
import { PageHeader } from '@/components/ui/PageHeader'
import type { Role } from '@/types'

const ACTIONS = ['read', 'write', 'delete', 'modify'] as const

const permissionRowSchema = z.object({
  endpoint: z.string().min(1, 'Endpoint is required'),
  actions: z.array(z.string()).min(1, 'Select at least one action'),
})

const roleSchema = z.object({
  name: z.string().min(2, 'Role name must be at least 2 characters'),
  permissions: z.array(permissionRowSchema),
})
type RoleForm = z.infer<typeof roleSchema>

function RoleModal({
  orgId,
  role,
  availableEndpoints,
  onClose,
}: {
  orgId: string
  role?: Role
  availableEndpoints: string[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)
  const isEdit = !!role

  const defaultPermissions = role
    ? Object.entries(role.permissions).map(([endpoint, actions]) => ({ endpoint, actions }))
    : [{ endpoint: '', actions: ['read'] }]

  const { register, handleSubmit, control, watch, setValue, formState: { errors } } = useForm<RoleForm>({
    resolver: zodResolver(roleSchema),
    defaultValues: {
      name: role?.name ?? '',
      permissions: defaultPermissions,
    },
  })

  const { fields, append, remove } = useFieldArray({ control, name: 'permissions' })

  const mutation = useMutation({
    mutationFn: (data: RoleForm) => {
      const permissionsObj: Record<string, string[]> = {}
      data.permissions.forEach(({ endpoint, actions }) => {
        permissionsObj[endpoint] = actions
      })
      if (isEdit) {
        return rolesApi.update(orgId, role!.id, { name: data.name, permissions: permissionsObj })
      }
      return rolesApi.create(orgId, { name: data.name, permissions: permissionsObj })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles', orgId] })
      onClose()
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e?.response?.data?.detail ?? 'Failed to save role')
    },
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-base font-semibold text-slate-900">
            {isEdit ? `Edit Role: ${role!.name}` : 'Create Role'}
          </h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-slate-100">
            <X className="h-5 w-5 text-slate-500" />
          </button>
        </div>

        {error && (
          <div className="flex items-start gap-2 p-3 mb-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">Role Name</label>
            <input
              {...register('name')}
              placeholder="e.g. editor, viewer, manager"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.name && <p className="text-rose-500 text-xs mt-1">{errors.name.message}</p>}
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-slate-700">Permissions</label>
              <button
                type="button"
                onClick={() => append({ endpoint: '', actions: ['read'] })}
                className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
              >
                <Plus className="h-3.5 w-3.5" />
                Add endpoint
              </button>
            </div>

            <div className="space-y-2">
              {fields.map((field, idx) => {
                const currentActions = watch(`permissions.${idx}.actions`) ?? []
                return (
                  <div key={field.id} className="flex gap-2 items-start p-3 bg-slate-50 rounded-lg border border-slate-200">
                    <div className="flex-1 min-w-0">
                      {availableEndpoints.length > 0 ? (
                        <select
                          {...register(`permissions.${idx}.endpoint`)}
                          className="w-full px-2 py-1.5 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 mb-2"
                        >
                          <option value="">Select endpoint…</option>
                          {availableEndpoints.map((ep) => (
                            <option key={ep} value={ep}>{ep}</option>
                          ))}
                          <option value="*">* (wildcard - all)</option>
                        </select>
                      ) : (
                        <input
                          {...register(`permissions.${idx}.endpoint`)}
                          placeholder="/api/resource"
                          className="w-full px-2 py-1.5 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 mb-2"
                        />
                      )}
                      <div className="flex flex-wrap gap-2">
                        {ACTIONS.map((action) => {
                          const checked = currentActions.includes(action)
                          return (
                            <label
                              key={action}
                              className={`flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium cursor-pointer border transition-colors ${
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
                                    ? [...currentActions, action]
                                    : currentActions.filter((a) => a !== action)
                                  setValue(`permissions.${idx}.actions`, updated)
                                }}
                              />
                              {checked && <Check className="h-3 w-3" />}
                              {action}
                            </label>
                          )
                        })}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => remove(idx)}
                      className="p-1.5 rounded-md hover:bg-rose-50 text-slate-400 hover:text-rose-500 transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )
              })}
            </div>
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
              {isEdit ? 'Save Changes' : 'Create Role'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function RoleCard({ role, orgId, endpoints }: { role: Role; orgId: string; endpoints: string[] }) {
  const queryClient = useQueryClient()
  const [expanded, setExpanded] = useState(false)
  const [editing, setEditing] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const deleteMutation = useMutation({
    mutationFn: () => rolesApi.delete(orgId, role.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['roles', orgId] })
      setConfirmDelete(false)
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setDeleteError(e?.response?.data?.detail ?? 'Failed to delete role')
    },
  })

  const permCount = Object.keys(role.permissions).length
  const PROTECTED = ['admin', 'user', 'super_user']
  const isProtected = PROTECTED.includes(role.name)

  return (
    <>
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="flex items-center gap-3 px-5 py-4">
          <div className="w-9 h-9 rounded-lg bg-emerald-100 flex items-center justify-center text-emerald-700">
            <Shield className="h-4 w-4" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-semibold text-slate-800">{role.name}</p>
              {isProtected && (
                <span className="text-xs px-1.5 py-0.5 bg-amber-100 text-amber-700 rounded font-medium">system</span>
              )}
            </div>
            <p className="text-xs text-slate-400">
              {permCount} endpoint{permCount !== 1 ? 's' : ''} configured
            </p>
          </div>
          <div className="flex items-center gap-2">
            {!isProtected && (
              <>
                <button onClick={() => setEditing(true)} className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600">
                  <Edit2 className="h-3.5 w-3.5" />
                </button>
                {!confirmDelete ? (
                  <button
                    onClick={() => setConfirmDelete(true)}
                    className="p-1.5 rounded-lg hover:bg-rose-50 text-slate-400 hover:text-rose-500"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                ) : (
                  <div className="flex flex-col items-end gap-1">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => deleteMutation.mutate()}
                        disabled={deleteMutation.isPending}
                        className="text-xs px-2 py-1 bg-rose-600 text-white rounded hover:bg-rose-700 disabled:opacity-60 flex items-center gap-1"
                      >
                        {deleteMutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                        Delete
                      </button>
                      <button
                        onClick={() => { setConfirmDelete(false); setDeleteError(null) }}
                        className="text-xs px-2 py-1 border border-slate-300 rounded hover:bg-slate-50"
                      >
                        Cancel
                      </button>
                    </div>
                    {deleteError && (
                      <p className="text-rose-600 text-xs flex items-center gap-1">
                        <AlertCircle className="h-3 w-3 shrink-0" />
                        {deleteError}
                      </p>
                    )}
                  </div>
                )}
              </>
            )}
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400"
            >
              {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>
          </div>
        </div>

        {expanded && permCount > 0 && (
          <div className="border-t border-slate-100 px-5 py-3">
            <div className="space-y-1.5">
              {Object.entries(role.permissions).map(([endpoint, actions]) => (
                <div key={endpoint} className="flex items-center gap-2 text-sm">
                  <code className="text-xs font-mono text-slate-600 bg-slate-100 px-1.5 py-0.5 rounded flex-1 truncate">
                    {endpoint}
                  </code>
                  <div className="flex gap-1">
                    {(actions as string[]).map((a) => (
                      <span key={a} className="text-xs px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded font-medium">
                        {a}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
        {expanded && permCount === 0 && (
          <div className="border-t border-slate-100 px-5 py-3 text-xs text-slate-400">
            No permissions defined.
          </div>
        )}
      </div>

      {editing && (
        <RoleModal
          orgId={orgId}
          role={role}
          availableEndpoints={endpoints}
          onClose={() => setEditing(false)}
        />
      )}
    </>
  )
}

export function RolesPage() {
  const { user } = useAuth()
  const orgId = user?.org_id ?? ''
  const [showCreate, setShowCreate] = useState(false)

  const { data: roles = [], isLoading } = useQuery({
    queryKey: ['roles', orgId],
    queryFn: () => rolesApi.list(orgId),
    enabled: !!orgId,
  })

  const { data: endpoints = [] } = useQuery({
    queryKey: ['endpoints', orgId],
    queryFn: () => endpointsApi.list(orgId),
    enabled: !!orgId,
  })

  const endpointPaths = endpoints.map((e) => e.endpoint)

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <PageHeader
        title="Roles & Permissions"
        description="Define roles and their endpoint access permissions"
        action={
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="h-4 w-4" />
            New Role
          </button>
        }
      />

      {isLoading ? (
        <div className="flex items-center gap-2 text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading roles…
        </div>
      ) : (
        <div className="space-y-3">
          {roles.map((role) => (
            <RoleCard key={role.id} role={role} orgId={orgId} endpoints={endpointPaths} />
          ))}
          {roles.length === 0 && (
            <div className="text-center py-12 bg-white rounded-xl border border-slate-200">
              <Shield className="h-10 w-10 text-slate-300 mx-auto mb-3" />
              <p className="text-slate-500">No roles defined yet.</p>
            </div>
          )}
        </div>
      )}

      {showCreate && (
        <RoleModal
          orgId={orgId}
          availableEndpoints={endpointPaths}
          onClose={() => setShowCreate(false)}
        />
      )}
    </div>
  )
}
