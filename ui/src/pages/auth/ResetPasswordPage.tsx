import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  KeyRound,
  Loader2,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Eye,
  EyeOff,
} from 'lucide-react'
import { authApi } from '@/api/auth'

const schema = z
  .object({
    new_password: z
      .string()
      .min(8, 'Password must be at least 8 characters'),
    confirm_password: z.string(),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: 'Passwords do not match',
    path: ['confirm_password'],
  })
type FormData = z.infer<typeof schema>

type TokenState = 'loading' | 'valid' | 'invalid' | 'success'

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token') ?? ''

  const [tokenState, setTokenState] = useState<TokenState>('loading')
  const [tokenEmail, setTokenEmail] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [showPw, setShowPw] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  // Verify the token as soon as the page loads
  useEffect(() => {
    if (!token) {
      setTokenState('invalid')
      return
    }
    authApi
      .verifyResetToken(token)
      .then((res) => {
        if (res.valid) {
          setTokenEmail(res.email ?? '')
          setTokenState('valid')
        } else {
          setTokenState('invalid')
        }
      })
      .catch(() => setTokenState('invalid'))
  }, [token])

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      await authApi.resetPassword(token, data.new_password)
      setTokenState('success')
      // Auto-redirect to login after 3 seconds
      setTimeout(() => navigate('/login'), 3000)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } } }
      const detail = e?.response?.data?.detail
      setError(
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? (detail as Array<{ msg?: string }>)[0]?.msg ?? 'Failed to reset password.'
            : 'Failed to reset password. Please request a new link.',
      )
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-500 mb-4">
            <KeyRound className="h-7 w-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">authYantra</h1>
          <p className="text-slate-400 text-sm mt-1">Identity & Access Management</p>
        </div>

        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {/* ── Loading ── */}
          {tokenState === 'loading' && (
            <div className="flex flex-col items-center py-4 gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
              <p className="text-sm text-slate-500">Verifying reset link…</p>
            </div>
          )}

          {/* ── Invalid / expired ── */}
          {tokenState === 'invalid' && (
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-rose-100 mb-4">
                <XCircle className="h-6 w-6 text-rose-600" />
              </div>
              <h2 className="text-lg font-semibold text-slate-800 mb-2">Link invalid or expired</h2>
              <p className="text-sm text-slate-500 mb-6">
                This password reset link is no longer valid. Reset links expire after 1 hour and
                can only be used once.
              </p>
              <Link
                to="/forgot-password"
                className="inline-block px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Request a new link
              </Link>
            </div>
          )}

          {/* ── Success ── */}
          {tokenState === 'success' && (
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-100 mb-4">
                <CheckCircle2 className="h-6 w-6 text-emerald-600" />
              </div>
              <h2 className="text-lg font-semibold text-slate-800 mb-2">Password reset!</h2>
              <p className="text-sm text-slate-500 mb-6">
                Your password has been updated. Redirecting you to sign in…
              </p>
              <Link
                to="/login"
                className="inline-block px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Sign in now
              </Link>
            </div>
          )}

          {/* ── Form ── */}
          {tokenState === 'valid' && (
            <>
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-slate-800">Set new password</h2>
                {tokenEmail && (
                  <p className="text-sm text-slate-500 mt-1">
                    Resetting password for{' '}
                    <span className="font-medium text-slate-700">{tokenEmail}</span>
                  </p>
                )}
              </div>

              {error && (
                <div className="flex items-start gap-2 p-3 mb-5 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
                  <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                  {error}
                </div>
              )}

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    New password
                  </label>
                  <div className="relative">
                    <input
                      {...register('new_password')}
                      type={showPw ? 'text' : 'password'}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      className="w-full px-3 py-2 pr-10 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPw(!showPw)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                  {errors.new_password && (
                    <p className="text-rose-500 text-xs mt-1">{errors.new_password.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Confirm new password
                  </label>
                  <div className="relative">
                    <input
                      {...register('confirm_password')}
                      type={showConfirm ? 'text' : 'password'}
                      placeholder="••••••••"
                      autoComplete="new-password"
                      className="w-full px-3 py-2 pr-10 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                    <button
                      type="button"
                      onClick={() => setShowConfirm(!showConfirm)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      {showConfirm ? (
                        <EyeOff className="h-4 w-4" />
                      ) : (
                        <Eye className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                  {errors.confirm_password && (
                    <p className="text-rose-500 text-xs mt-1">{errors.confirm_password.message}</p>
                  )}
                </div>

                <p className="text-xs text-slate-400">Minimum 8 characters.</p>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-medium rounded-lg text-sm transition-colors"
                >
                  {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  Reset password
                </button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
