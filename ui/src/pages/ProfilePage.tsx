import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  KeyRound, Loader2, AlertCircle, CheckCircle2,
  User, Trash2, Shield, QrCode, Copy, Check,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@/api/auth'
import { mfaApi } from '@/api/mfa'
import { useAuth } from '@/context/AuthContext'
import { PageHeader } from '@/components/ui/PageHeader'
import type { MfaSetupResponse } from '@/types'

// ── Password form ─────────────────────────────────────────────────────────────

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

// ── MFA section ───────────────────────────────────────────────────────────────

function MfaSection() {
  const queryClient = useQueryClient()
  const [setupData, setSetupData] = useState<MfaSetupResponse | null>(null)
  const [verifyCode, setVerifyCode] = useState('')
  const [verifyError, setVerifyError] = useState<string | null>(null)
  const [verifySuccess, setVerifySuccess] = useState(false)
  const [copiedSecret, setCopiedSecret] = useState(false)
  const [disableError, setDisableError] = useState<string | null>(null)
  const [confirmDisable, setConfirmDisable] = useState(false)

  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['mfa-status'],
    queryFn: mfaApi.status,
  })

  const setupMutation = useMutation({
    mutationFn: mfaApi.setupTotp,
    onSuccess: (data) => setSetupData(data),
  })

  const verifyMutation = useMutation({
    mutationFn: () => mfaApi.verifyTotp(setupData!.credential_id, verifyCode),
    onSuccess: () => {
      setVerifySuccess(true)
      setSetupData(null)
      queryClient.invalidateQueries({ queryKey: ['mfa-status'] })
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setVerifyError(e?.response?.data?.detail ?? 'Invalid code')
    },
  })

  const disableMutation = useMutation({
    mutationFn: mfaApi.disable,
    onSuccess: () => {
      setConfirmDisable(false)
      queryClient.invalidateQueries({ queryKey: ['mfa-status'] })
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setDisableError(e?.response?.data?.detail ?? 'Failed to disable MFA')
    },
  })

  const copySecret = () => {
    if (setupData) {
      navigator.clipboard.writeText(setupData.secret)
      setCopiedSecret(true)
      setTimeout(() => setCopiedSecret(false), 2000)
    }
  }

  if (statusLoading) {
    return (
      <div className="flex items-center gap-2 text-slate-400 text-sm p-5">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading MFA status…
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 mb-5">
      <h3 className="font-semibold text-slate-800 mb-1 flex items-center gap-2">
        <Shield className="h-4 w-4 text-indigo-500" />
        Two-Factor Authentication (TOTP)
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        Protect your account with an authenticator app (Google Authenticator, Authy, etc.)
      </p>

      {verifySuccess && (
        <div className="flex items-center gap-2 p-3 mb-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-sm">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          MFA activated successfully. Your account is now protected.
        </div>
      )}

      {/* Already enabled */}
      {status?.enabled && !setupData && (
        <div className="space-y-3">
          <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 px-3 py-2 rounded-lg border border-emerald-200">
            <CheckCircle2 className="h-4 w-4 shrink-0" />
            MFA is active ({status.type})
            {status.last_used_at && (
              <span className="text-emerald-600 ml-1">
                · last used {new Date(status.last_used_at).toLocaleDateString()}
              </span>
            )}
          </div>
          {disableError && (
            <p className="text-rose-600 text-sm flex items-center gap-1">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" /> {disableError}
            </p>
          )}
          {!confirmDisable ? (
            <button
              onClick={() => setConfirmDisable(true)}
              className="text-sm text-rose-500 hover:text-rose-700 font-medium"
            >
              Disable MFA
            </button>
          ) : (
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-600">Disable MFA?</span>
              <button
                onClick={() => disableMutation.mutate()}
                disabled={disableMutation.isPending}
                className="text-xs px-3 py-1 bg-rose-600 text-white rounded hover:bg-rose-700 disabled:opacity-60 flex items-center gap-1"
              >
                {disableMutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
                Yes, disable
              </button>
              <button
                onClick={() => setConfirmDisable(false)}
                className="text-xs px-3 py-1 border border-slate-300 rounded hover:bg-slate-50"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      )}

      {/* Not enabled — show setup button or flow */}
      {!status?.enabled && !setupData && (
        <button
          onClick={() => setupMutation.mutate()}
          disabled={setupMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-60"
        >
          {setupMutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <QrCode className="h-4 w-4" />
          )}
          Enable MFA
        </button>
      )}

      {/* Setup flow */}
      {setupData && (
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Scan this QR code with your authenticator app, or enter the secret manually.
          </p>

          {/* QR code via img tag using the otpauth URI */}
          <div className="flex flex-col sm:flex-row gap-4 items-start">
            <img
              src={`https://api.qrserver.com/v1/create-qr-code/?data=${encodeURIComponent(setupData.totp_uri)}&size=160x160`}
              alt="TOTP QR Code"
              className="border border-slate-200 rounded-lg p-2 bg-white"
              width={160}
              height={160}
            />
            <div className="space-y-2 flex-1">
              <p className="text-xs font-medium text-slate-500">Manual entry secret</p>
              <div className="flex items-center gap-2">
                <code className="text-xs font-mono bg-slate-100 px-3 py-2 rounded flex-1 break-all">
                  {setupData.secret}
                </code>
                <button onClick={copySecret} className="p-2 hover:bg-slate-100 rounded text-slate-400">
                  {copiedSecret ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
                </button>
              </div>
              <p className="text-xs text-slate-400">
                Save these backup codes somewhere safe — each can only be used once:
              </p>
              <div className="grid grid-cols-2 gap-1">
                {setupData.backup_codes.map((c) => (
                  <code key={c} className="text-xs font-mono bg-slate-100 px-2 py-1 rounded text-center">
                    {c}
                  </code>
                ))}
              </div>
            </div>
          </div>

          {verifyError && (
            <p className="text-rose-600 text-sm flex items-center gap-1">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" /> {verifyError}
            </p>
          )}

          <div className="flex items-center gap-3">
            <input
              value={verifyCode}
              onChange={(e) => { setVerifyCode(e.target.value); setVerifyError(null) }}
              placeholder="Enter 6-digit code"
              maxLength={6}
              className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 w-44 font-mono tracking-widest"
            />
            <button
              onClick={() => verifyMutation.mutate()}
              disabled={verifyMutation.isPending || verifyCode.length < 6}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-60"
            >
              {verifyMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              Verify & Activate
            </button>
            <button
              onClick={() => { setSetupData(null); setVerifyCode(''); setVerifyError(null) }}
              className="text-sm text-slate-500 hover:text-slate-700"
            >
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function ProfilePage() {
  const { user: authUser, logout } = useAuth()
  const navigate = useNavigate()
  const [pwSuccess, setPwSuccess] = useState(false)
  const [pwError, setPwError] = useState<string | null>(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data: me, isLoading } = useQuery({
    queryKey: ['me'],
    queryFn: authApi.getMe,
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
  })

  const passwordMutation = useMutation({
    mutationFn: (data: PasswordForm) =>
      authApi.changePassword({ old_password: data.current_password, new_password: data.new_password }),
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

  const deleteMutation = useMutation({
    mutationFn: authApi.deleteMe,
    onSuccess: () => { logout(); navigate('/login') },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setDeleteError(e?.response?.data?.detail ?? 'Failed to delete account')
    },
  })

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <PageHeader title="Profile" description="Account details, security settings, and MFA" />

      {/* Account info */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-5">
        <h3 className="font-semibold text-slate-800 mb-4 flex items-center gap-2">
          <User className="h-4 w-4 text-indigo-500" />
          Account Information
        </h3>
        {isLoading ? (
          <div className="flex items-center gap-2 text-slate-500"><Loader2 className="h-4 w-4 animate-spin" />Loading…</div>
        ) : me ? (
          <dl className="space-y-2.5">
            {[
              { label: 'Email', value: me.email },
              { label: 'Username', value: me.username ?? '—' },
              { label: 'User ID', value: me.id },
              { label: 'Organization ID', value: me.organization_id ?? '—' },
              { label: 'Status', value: me.is_active ? 'Active' : 'Inactive' },
              { label: 'Roles', value: authUser?.roles?.join(', ') || 'No roles' },
              { label: 'MFA', value: me.mfa_enabled ? 'Enabled' : 'Disabled' },
              { label: 'Last login', value: me.last_login_at ? new Date(me.last_login_at).toLocaleString() : '—' },
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

      {/* MFA */}
      <MfaSection />

      {/* Change password */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 mb-5">
        <h3 className="font-semibold text-slate-800 mb-1 flex items-center gap-2">
          <KeyRound className="h-4 w-4 text-indigo-500" />
          Change Password
        </h3>
        <p className="text-sm text-slate-500 mb-4">Update your account password.</p>

        {pwError && (
          <div className="flex items-start gap-2 p-3 mb-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />{pwError}
          </div>
        )}
        {pwSuccess && (
          <div className="flex items-center gap-2 p-3 mb-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-sm">
            <CheckCircle2 className="h-4 w-4 shrink-0" />Password changed successfully.
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
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium disabled:opacity-60"
          >
            {passwordMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Update Password
          </button>
        </form>
      </div>

      {/* Delete account */}
      <div className="bg-white rounded-xl border border-rose-200 p-5">
        <h3 className="font-semibold text-slate-800 mb-1 flex items-center gap-2">
          <Trash2 className="h-4 w-4 text-rose-500" />
          Delete Account
        </h3>
        <p className="text-sm text-slate-500 mb-4">
          Permanently delete your account and remove you from all organizations. Cannot be undone.
        </p>
        {deleteError && (
          <div className="flex items-start gap-2 p-3 mb-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />{deleteError}
          </div>
        )}
        {!confirmDelete ? (
          <button
            onClick={() => setConfirmDelete(true)}
            className="flex items-center gap-2 px-4 py-2 border border-rose-300 text-rose-600 hover:bg-rose-50 rounded-lg text-sm font-medium"
          >
            <Trash2 className="h-4 w-4" />Delete My Account
          </button>
        ) : (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg">
            <p className="text-sm font-medium text-rose-800 mb-3">
              Are you sure? This action is permanent and cannot be undone.
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => { setConfirmDelete(false); setDeleteError(null) }}
                className="flex-1 py-2 border border-slate-300 text-slate-700 rounded-lg text-sm font-medium hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={() => deleteMutation.mutate()}
                disabled={deleteMutation.isPending}
                className="flex-1 flex items-center justify-center gap-2 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-medium disabled:opacity-60"
              >
                {deleteMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
                Yes, Delete My Account
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
