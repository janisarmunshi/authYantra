import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { KeyRound, Loader2, AlertCircle, CheckCircle2, User } from 'lucide-react'
import { authApi } from '@/api/auth'
import { useAuth } from '@/context/AuthContext'
import { PageHeader } from '@/components/ui/PageHeader'

const passwordSchema = z
  .object({
    current_password: z.string().min(1, 'Current password is required'),
    new_password: z.string().min(8, 'New password must be at least 8 characters'),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  })
type PasswordForm = z.infer<typeof passwordSchema>

export function ProfilePage() {
  const { user: authUser } = useAuth()
  const [pwSuccess, setPwSuccess] = useState(false)
  const [pwError, setPwError] = useState<string | null>(null)

  const { data: me, isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: authApi.getMe,
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
  })

  const passwordMutation = useMutation({
    mutationFn: (data: PasswordForm) =>
      authApi.changePassword({
        current_password: data.current_password,
        new_password: data.new_password,
      }),
    onSuccess: () => {
      reset()
      setPwSuccess(true)
      setPwError(null)
      setTimeout(() => setPwSuccess(false), 4000)
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setPwError(e?.response?.data?.detail ?? 'Failed to change password')
    },
  })

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <PageHeader
        title="Profile"
        description="View your account details and manage security settings"
      />

      {/* Account info */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-5">
        <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <User className="h-4 w-4 text-indigo-500" />
          Account Information
        </h3>

        {isLoading ? (
          <div className="flex items-center gap-2 text-slate-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            Loading…
          </div>
        ) : me ? (
          <dl className="space-y-2.5">
            {[
              { label: 'Email', value: me.email },
              { label: 'Username', value: me.username ?? '—' },
              { label: 'User ID', value: me.id },
              { label: 'Organization ID', value: me.organization_id },
              { label: 'Status', value: me.is_active ? 'Active' : 'Inactive' },
              { label: 'Roles', value: authUser?.roles?.join(', ') || 'No roles' },
              { label: 'Entra ID', value: me.entra_id ? 'Linked' : 'Not linked' },
              { label: 'Member since', value: new Date(me.created_at).toLocaleDateString() },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between items-center text-sm py-1.5 border-b border-slate-100 last:border-0">
                <dt className="text-slate-500">{label}</dt>
                <dd className="text-slate-800 font-medium text-right max-w-xs truncate">{value}</dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="text-slate-400 text-sm">Could not load profile.</p>
        )}
      </div>

      {/* Change password */}
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h3 className="font-semibold text-slate-800 mb-1 flex items-center gap-2">
          <KeyRound className="h-4 w-4 text-indigo-500" />
          Change Password
        </h3>
        <p className="text-sm text-slate-500 mb-4">Update your account password.</p>

        {pwError && (
          <div className="flex items-start gap-2 p-3 mb-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            {pwError}
          </div>
        )}
        {pwSuccess && (
          <div className="flex items-center gap-2 p-3 mb-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-sm">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            Password changed successfully.
          </div>
        )}

        <form onSubmit={handleSubmit((d) => passwordMutation.mutate(d))} className="space-y-4">
          {[
            { name: 'current_password' as const, label: 'Current Password' },
            { name: 'new_password' as const, label: 'New Password' },
            { name: 'confirm_password' as const, label: 'Confirm New Password' },
          ].map(({ name, label }) => (
            <div key={name}>
              <label className="block text-sm font-medium text-slate-700 mb-1.5">{label}</label>
              <input
                {...register(name)}
                type="password"
                placeholder="••••••••"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              {errors[name] && <p className="text-rose-500 text-xs mt-1">{errors[name]?.message}</p>}
            </div>
          ))}

          <button
            type="submit"
            disabled={passwordMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-60"
          >
            {passwordMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Update Password
          </button>
        </form>
      </div>
    </div>
  )
}
