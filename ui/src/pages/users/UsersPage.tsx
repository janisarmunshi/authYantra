import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  Plus, Users, Loader2, AlertCircle, Shield, Trash2, UserCheck,
} from 'lucide-react'
import { authApi } from '@/api/auth'
import { rolesApi } from '@/api/roles'
import { usersApi } from '@/api/users'
import { useAuth } from '@/context/AuthContext'
import { PageHeader } from '@/components/ui/PageHeader'
import type { User, Role } from '@/types'

const registerSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  username: z.string().optional(),
})
type RegisterForm = z.infer<typeof registerSchema>

function CreateUserModal({ orgId, onClose }: { orgId: string; onClose: () => void }) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterForm>({
    resolver: zodResolver(registerSchema),
  })

  const onSubmit = async (data: RegisterForm) => {
    setError(null)
    try {
      await authApi.register({ ...data, organization_id: orgId })
      queryClient.invalidateQueries({ queryKey: ['users', orgId] })
      onClose()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e?.response?.data?.detail ?? 'Failed to create user')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-base font-semibold text-slate-900 mb-5">Create User</h3>

        {error && (
          <div className="flex items-start gap-2 p-3 mb-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {[
            { name: 'email' as const, label: 'Email', type: 'email', placeholder: 'user@example.com' },
            { name: 'username' as const, label: 'Username (optional)', type: 'text', placeholder: 'johndoe' },
            { name: 'password' as const, label: 'Password', type: 'password', placeholder: '••••••••' },
          ].map(({ name, label, type, placeholder }) => (
            <div key={name}>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">{label}</label>
              <input
                {...register(name)}
                type={type}
                placeholder={placeholder}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              {errors[name] && (
                <p className="text-rose-500 text-xs mt-1">{errors[name]?.message}</p>
              )}
            </div>
          ))}

          <div className="flex gap-3 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 px-4 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 flex items-center justify-center gap-2 py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-60"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              Create User
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function RoleAssignModal({
  user,
  orgId,
  roles,
  currentRoles,
  onClose,
}: {
  user: User
  orgId: string
  roles: Role[]
  currentRoles: Role[]
  onClose: () => void
}) {
  const queryClient = useQueryClient()
  const [error, setError] = useState<string | null>(null)

  const assignMutation = useMutation({
    mutationFn: (roleId: string) => rolesApi.assignRole(user.id, orgId, roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userRoles', user.id, orgId] })
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e?.response?.data?.detail ?? 'Failed to assign role')
    },
  })

  const removeMutation = useMutation({
    mutationFn: (roleId: string) => rolesApi.removeRole(user.id, orgId, roleId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['userRoles', user.id, orgId] })
    },
  })

  const currentRoleIds = new Set(currentRoles.map((r) => r.id))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-base font-semibold text-slate-900 mb-1">Manage Roles</h3>
        <p className="text-sm text-slate-500 mb-5">{user.email}</p>

        {error && (
          <div className="text-rose-600 text-sm mb-3 flex items-start gap-2">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        <div className="space-y-2">
          {roles.map((role) => {
            const hasRole = currentRoleIds.has(role.id)
            return (
              <div
                key={role.id}
                className={`flex items-center justify-between p-3 rounded-lg border ${
                  hasRole ? 'border-indigo-200 bg-indigo-50' : 'border-slate-200'
                }`}
              >
                <div className="flex items-center gap-2">
                  <Shield className={`h-4 w-4 ${hasRole ? 'text-indigo-500' : 'text-slate-400'}`} />
                  <span className="text-sm font-medium text-slate-800">{role.name}</span>
                </div>
                {hasRole ? (
                  <button
                    onClick={() => removeMutation.mutate(role.id)}
                    disabled={removeMutation.isPending}
                    className="text-xs text-rose-500 hover:text-rose-700 flex items-center gap-1"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    Remove
                  </button>
                ) : (
                  <button
                    onClick={() => assignMutation.mutate(role.id)}
                    disabled={assignMutation.isPending}
                    className="text-xs text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                  >
                    <UserCheck className="h-3.5 w-3.5" />
                    Assign
                  </button>
                )}
              </div>
            )
          })}
        </div>

        <button
          onClick={onClose}
          className="mt-5 w-full py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50"
        >
          Done
        </button>
      </div>
    </div>
  )
}

function UserRow({
  user,
  orgId,
  currentUserId,
  roles,
}: {
  user: User
  orgId: string
  currentUserId: string
  roles: Role[]
}) {
  const queryClient = useQueryClient()
  const [showRoles, setShowRoles] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)

  const { data: userRoles = [] } = useQuery({
    queryKey: ['userRoles', user.id, orgId],
    queryFn: () => rolesApi.getUserRoles(user.id, orgId),
  })

  const deleteMutation = useMutation({
    mutationFn: () => usersApi.delete(orgId, user.id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', orgId] })
      setConfirmDelete(false)
    },
  })

  const isSelf = user.id === currentUserId

  return (
    <>
      <tr className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
        <td className="px-4 py-3">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold text-xs uppercase shrink-0">
              {user.email[0]}
            </div>
            <div>
              <p className="text-sm font-medium text-slate-800">{user.email}</p>
              {user.username && <p className="text-xs text-slate-400">{user.username}</p>}
            </div>
          </div>
        </td>
        <td className="px-4 py-3 hidden sm:table-cell">
          <div className="flex flex-wrap gap-1">
            {userRoles.length > 0 ? (
              userRoles.map((r) => (
                <span
                  key={r.id}
                  className="text-xs px-1.5 py-0.5 bg-indigo-100 text-indigo-700 rounded font-medium"
                >
                  {r.name}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-400">No roles</span>
            )}
          </div>
        </td>
        <td className="px-4 py-3 hidden md:table-cell">
          <span
            className={`text-xs px-2 py-0.5 rounded-full font-medium ${
              user.is_active
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-slate-100 text-slate-500'
            }`}
          >
            {user.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>
        <td className="px-4 py-3 hidden lg:table-cell">
          <span className="text-xs text-slate-400">
            {new Date(user.created_at).toLocaleDateString()}
          </span>
        </td>
        <td className="px-4 py-3 text-right">
          <div className="flex items-center justify-end gap-3">
            <button
              onClick={() => setShowRoles(true)}
              className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center gap-1"
            >
              <Shield className="h-3.5 w-3.5" />
              Roles
            </button>
            {!isSelf && (
              <button
                onClick={() => setConfirmDelete(true)}
                className="text-xs text-rose-500 hover:text-rose-700 font-medium flex items-center gap-1"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Delete
              </button>
            )}
          </div>
        </td>
      </tr>

      {showRoles && (
        <RoleAssignModal
          user={user}
          orgId={orgId}
          roles={roles}
          currentRoles={userRoles}
          onClose={() => setShowRoles(false)}
        />
      )}

      {confirmDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm p-6">
            <h3 className="text-base font-semibold text-slate-900 mb-2">Delete user?</h3>
            <p className="text-sm text-slate-500 mb-5">
              <span className="font-medium text-slate-700">{user.email}</span> will be permanently
              removed along with all their role assignments.
            </p>
            {deleteMutation.isError && (
              <p className="text-rose-600 text-sm mb-3">
                {(deleteMutation.error as { response?: { data?: { detail?: string } } })
                  ?.response?.data?.detail ?? 'Failed to delete user'}
              </p>
            )}
            <div className="flex gap-3">
              <button
                onClick={() => setConfirmDelete(false)}
                className="flex-1 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-medium disabled:opacity-60"
              >
                {deleteMutation.isPending && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export function UsersPage() {
  const { user: currentUser } = useAuth()
  const orgId = currentUser?.org_id ?? ''
  const [showCreate, setShowCreate] = useState(false)

  const { data: users = [], isLoading: usersLoading } = useQuery({
    queryKey: ['users', orgId],
    queryFn: () => usersApi.list(orgId),
    enabled: !!orgId,
  })

  const { data: roles = [] } = useQuery({
    queryKey: ['roles', orgId],
    queryFn: () => rolesApi.list(orgId),
    enabled: !!orgId,
  })

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <PageHeader
        title="Users"
        description="Manage users and their role assignments"
        action={
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="h-4 w-4" />
            New User
          </button>
        }
      />

      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-100">
          <p className="text-xs text-slate-500">
            Showing users in your organization. A bulk list endpoint is available via the API.
          </p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">User</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden sm:table-cell">Roles</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden md:table-cell">Status</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden lg:table-cell">Created</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <UserRow key={u.id} user={u} orgId={orgId} currentUserId={currentUser?.user_id ?? ''} roles={roles} />
              ))}
            </tbody>
          </table>
        </div>

        {usersLoading && (
          <div className="text-center py-12 text-slate-400 text-sm">Loading users…</div>
        )}
        {!usersLoading && users.length === 0 && (
          <div className="text-center py-12">
            <Users className="h-10 w-10 text-slate-300 mx-auto mb-3" />
            <p className="text-slate-500">No users to display.</p>
          </div>
        )}
      </div>

      {showCreate && <CreateUserModal orgId={orgId} onClose={() => setShowCreate(false)} />}
    </div>
  )
}
