import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2, KeyRound, AlertCircle, Building2, Check } from 'lucide-react'
import { authApi } from '@/api/auth'
import { useAuth } from '@/context/AuthContext'
import type { OrgSummary } from '@/types'

// ── Schemas ───────────────────────────────────────────────────────────────────

const loginSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(1, 'Password is required'),
})
type LoginForm = z.infer<typeof loginSchema>

const registerSchema = z.object({
  email: z.string().email('Enter a valid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  username: z.string().optional(),
})
type RegisterForm = z.infer<typeof registerSchema>

// ── Org selection overlay ─────────────────────────────────────────────────────

function OrgSelector({
  orgs,
  onSelect,
  loading,
}: {
  orgs: OrgSummary[]
  onSelect: (orgId: string) => void
  loading: boolean
}) {
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-500 mb-4">
        You belong to multiple organizations. Select one to continue.
      </p>
      {orgs.map((org) => (
        <button
          key={org.id}
          onClick={() => onSelect(org.id)}
          disabled={loading}
          className="w-full flex items-center gap-3 p-3 border border-slate-200 rounded-lg hover:border-indigo-300 hover:bg-indigo-50 transition-colors text-left disabled:opacity-60"
        >
          <div className="w-9 h-9 rounded-lg bg-indigo-100 flex items-center justify-center shrink-0">
            <Building2 className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-slate-800 truncate">{org.name}</p>
            <p className="text-xs text-slate-400 capitalize">{org.role}</p>
          </div>
          {loading && <Loader2 className="h-4 w-4 animate-spin text-indigo-500 shrink-0" />}
        </button>
      ))}
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export function LoginPage() {
  const { login, completeOrgSelection, setPendingOrgs } = useAuth()
  const navigate = useNavigate()
  const [tab, setTab] = useState<'login' | 'register'>('login')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [selectingOrg, setSelectingOrg] = useState(false)
  const [pendingOrgs, setPendingOrgsLocal] = useState<OrgSummary[] | null>(null)
  const [pendingTokens, setPendingTokens] = useState<{ access: string; refresh: string } | null>(null)

  const loginForm = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })
  const registerForm = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) })

  const onLogin = async (data: LoginForm) => {
    setError(null)
    try {
      const resp = await authApi.login(data)

      if (resp.needs_org_selection) {
        // Store partial tokens and show org picker
        setPendingTokens({ access: resp.access_token, refresh: resp.refresh_token })
        setPendingOrgsLocal(resp.organizations)
        setPendingOrgs(resp.organizations)
        return
      }

      login(resp.access_token, resp.refresh_token)
      navigate('/')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } } }
      const detail = e?.response?.data?.detail
      setError(
        typeof detail === 'string' ? detail :
        Array.isArray(detail) ? ((detail as Array<{ msg?: string }>)[0]?.msg ?? 'Login failed.') :
        'Login failed. Please check your credentials.'
      )
    }
  }

  const onSelectOrg = async (orgId: string) => {
    if (!pendingTokens) return
    setSelectingOrg(true)
    setError(null)
    try {
      // Temporarily set the partial token so apiClient can attach it
      const { tokenStorage } = await import('@/utils/token')
      tokenStorage.setAccessToken(pendingTokens.access)
      tokenStorage.setRefreshToken(pendingTokens.refresh)

      const resp = await authApi.switchOrg(orgId)
      completeOrgSelection(resp.access_token, resp.refresh_token)
      navigate('/')
    } catch {
      setError('Failed to select organization. Please try again.')
    } finally {
      setSelectingOrg(false)
    }
  }

  const onRegister = async (data: RegisterForm) => {
    setError(null)
    setSuccess(null)
    try {
      await authApi.register(data)
      setSuccess('Account created! You can now sign in.')
      setTab('login')
      loginForm.setValue('email', data.email)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: unknown } } }
      const detail = e?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : 'Registration failed.')
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
          {pendingOrgs ? (
            <>
              <h2 className="text-lg font-semibold text-slate-800 mb-2">Select Organization</h2>
              {error && (
                <div className="flex items-start gap-2 p-3 mb-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
                  <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />{error}
                </div>
              )}
              <OrgSelector orgs={pendingOrgs} onSelect={onSelectOrg} loading={selectingOrg} />
            </>
          ) : (
            <>
              {/* Tabs */}
              <div className="flex gap-1 p-1 bg-slate-100 rounded-lg mb-6">
                {(['login', 'register'] as const).map((t) => (
                  <button
                    key={t}
                    onClick={() => { setTab(t); setError(null); setSuccess(null) }}
                    className={`flex-1 py-1.5 text-sm font-medium rounded-md transition-colors capitalize ${
                      tab === t ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
                    }`}
                  >
                    {t === 'login' ? 'Sign in' : 'Register'}
                  </button>
                ))}
              </div>

              {error && (
                <div className="flex items-start gap-2 p-3 mb-5 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
                  <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" /><span>{error}</span>
                </div>
              )}

              {success && (
                <div className="flex items-start gap-2 p-3 mb-5 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-sm">
                  <Check className="h-4 w-4 mt-0.5 shrink-0" /><span>{success}</span>
                </div>
              )}

              {tab === 'login' ? (
                <form onSubmit={loginForm.handleSubmit(onLogin)} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 mb-1.5">Email address</label>
                    <input
                      {...loginForm.register('email')}
                      type="email"
                      autoComplete="email"
                      placeholder="you@example.com"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    {loginForm.formState.errors.email && (
                      <p className="text-rose-500 text-xs mt-1">{loginForm.formState.errors.email.message}</p>
                    )}
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-sm font-medium text-slate-700">Password</label>
                      <Link to="/forgot-password" className="text-xs text-indigo-600 hover:text-indigo-800 font-medium">
                        Forgot password?
                      </Link>
                    </div>
                    <input
                      {...loginForm.register('password')}
                      type="password"
                      autoComplete="current-password"
                      placeholder="••••••••"
                      className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    />
                    {loginForm.formState.errors.password && (
                      <p className="text-rose-500 text-xs mt-1">{loginForm.formState.errors.password.message}</p>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={loginForm.formState.isSubmitting}
                    className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-medium rounded-lg text-sm transition-colors"
                  >
                    {loginForm.formState.isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                    Sign in
                  </button>
                </form>
              ) : (
                <form onSubmit={registerForm.handleSubmit(onRegister)} className="space-y-4">
                  {[
                    { name: 'email' as const, label: 'Email address', type: 'email', placeholder: 'you@example.com' },
                    { name: 'username' as const, label: 'Username (optional)', type: 'text', placeholder: 'johndoe' },
                    { name: 'password' as const, label: 'Password', type: 'password', placeholder: '••••••••' },
                  ].map(({ name, label, type, placeholder }) => (
                    <div key={name}>
                      <label className="block text-sm font-medium text-slate-700 mb-1.5">{label}</label>
                      <input
                        {...registerForm.register(name)}
                        type={type}
                        placeholder={placeholder}
                        className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                      {registerForm.formState.errors[name] && (
                        <p className="text-rose-500 text-xs mt-1">{registerForm.formState.errors[name]?.message}</p>
                      )}
                    </div>
                  ))}
                  <button
                    type="submit"
                    disabled={registerForm.formState.isSubmitting}
                    className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-60 text-white font-medium rounded-lg text-sm transition-colors"
                  >
                    {registerForm.formState.isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
                    Create account
                  </button>
                </form>
              )}

              {tab === 'login' && (
                <>
                  <div className="relative my-5">
                    <div className="absolute inset-0 flex items-center"><div className="w-full border-t border-slate-200" /></div>
                    <div className="relative flex justify-center text-xs text-slate-400 bg-white px-2">or continue with</div>
                  </div>
                  <button
                    onClick={() => { window.location.href = '/auth/entra/authorize' }}
                    className="w-full flex items-center justify-center gap-2 py-2.5 px-4 border border-slate-300 hover:bg-slate-50 text-slate-700 font-medium rounded-lg text-sm transition-colors"
                  >
                    <svg className="h-4 w-4" viewBox="0 0 21 21" fill="none">
                      <rect x="1" y="1" width="9" height="9" fill="#F25022" />
                      <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
                      <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
                      <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
                    </svg>
                    Microsoft Entra ID
                  </button>
                </>
              )}
            </>
          )}
        </div>

        <p className="text-center text-slate-500 text-xs mt-6">
          authYantra Identity & Access Management Service
        </p>
      </div>
    </div>
  )
}
