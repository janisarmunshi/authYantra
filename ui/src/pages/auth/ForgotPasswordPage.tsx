import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { KeyRound, Loader2, AlertCircle, CheckCircle2, ArrowLeft } from 'lucide-react'
import { authApi } from '@/api/auth'

const schema = z.object({
  organization_id: z.string().min(1, 'Organization ID is required'),
  email: z.string().email('Enter a valid email address'),
})
type FormData = z.infer<typeof schema>

export function ForgotPasswordPage() {
  const [submitted, setSubmitted] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormData) => {
    setError(null)
    try {
      await authApi.forgotPassword(data.email, data.organization_id)
      setSubmitted(true)
    } catch {
      // Always show success to prevent email enumeration —
      // only surface genuine network / server errors
      setError('Something went wrong. Please try again.')
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
          {submitted ? (
            /* ── Success state ── */
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-100 mb-4">
                <CheckCircle2 className="h-6 w-6 text-emerald-600" />
              </div>
              <h2 className="text-lg font-semibold text-slate-800 mb-2">Check your inbox</h2>
              <p className="text-sm text-slate-500 mb-1">
                If <span className="font-medium text-slate-700">{getValues('email')}</span> is
                registered in this organization, we've sent a password reset link.
              </p>
              <p className="text-xs text-slate-400 mb-6">
                The link expires in <strong>1 hour</strong>. Check your spam folder if you don't
                see it.
              </p>
              <Link
                to="/login"
                className="inline-flex items-center gap-2 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to sign in
              </Link>
            </div>
          ) : (
            /* ── Form state ── */
            <>
              <div className="mb-6">
                <h2 className="text-lg font-semibold text-slate-800">Forgot your password?</h2>
                <p className="text-sm text-slate-500 mt-1">
                  Enter your organization ID and email address and we'll send you a reset link.
                </p>
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
                    Organization ID
                  </label>
                  <input
                    {...register('organization_id')}
                    placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                  {errors.organization_id && (
                    <p className="text-rose-500 text-xs mt-1">{errors.organization_id.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1.5">
                    Email address
                  </label>
                  <input
                    {...register('email')}
                    type="email"
                    autoComplete="email"
                    placeholder="you@example.com"
                    className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                  {errors.email && (
                    <p className="text-rose-500 text-xs mt-1">{errors.email.message}</p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-medium rounded-lg text-sm transition-colors"
                >
                  {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                  Send reset link
                </button>
              </form>

              <div className="mt-5 text-center">
                <Link
                  to="/login"
                  className="inline-flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700"
                >
                  <ArrowLeft className="h-3.5 w-3.5" />
                  Back to sign in
                </Link>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
