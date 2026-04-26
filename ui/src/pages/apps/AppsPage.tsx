import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { Plus, AppWindow, Loader2, AlertCircle, Copy, Check, Eye, EyeOff } from 'lucide-react'
import { organizationsApi } from '@/api/organizations'
import { useAuth } from '@/context/AuthContext'
import { PageHeader } from '@/components/ui/PageHeader'
import type { RegisteredApp } from '@/types'

const appSchema = z.object({
  app_name: z.string().min(2, 'App name must be at least 2 characters'),
  app_type: z.enum(['web', 'desktop', 'mobile']),
  redirect_uris: z.string().min(1, 'At least one redirect URI is required'),
})
type AppForm = z.infer<typeof appSchema>

function ApiKeyDisplay({ apiKey }: { apiKey: string }) {
  const [visible, setVisible] = useState(false)
  const [copied, setCopied] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(apiKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="flex items-center gap-1 mt-1">
      <code className="text-xs font-mono text-slate-600 bg-slate-100 px-2 py-1 rounded flex-1 truncate">
        {visible ? apiKey : '•'.repeat(32)}
      </code>
      <button onClick={() => setVisible(!visible)} className="p-1 rounded hover:bg-slate-100 text-slate-400">
        {visible ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
      </button>
      <button onClick={copy} className="p-1 rounded hover:bg-slate-100 text-slate-400">
        {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
    </div>
  )
}

function AppCard({ app }: { app: RegisteredApp }) {
  const typeColors: Record<string, string> = {
    web: 'bg-indigo-100 text-indigo-700',
    desktop: 'bg-amber-100 text-amber-700',
    mobile: 'bg-emerald-100 text-emerald-700',
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center text-indigo-700">
            <AppWindow className="h-5 w-5" />
          </div>
          <div>
            <p className="font-semibold text-slate-800">{app.app_name}</p>
            <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${typeColors[app.app_type] ?? ''}`}>
              {app.app_type}
            </span>
          </div>
        </div>
        <span
          className={`text-xs px-2 py-0.5 rounded-full font-medium ${
            app.is_active ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-500'
          }`}
        >
          {app.is_active ? 'Active' : 'Inactive'}
        </span>
      </div>

      <div className="space-y-2">
        <div>
          <p className="text-xs text-slate-500 font-medium">API Key</p>
          <ApiKeyDisplay apiKey={app.api_key} />
        </div>
        {app.redirect_uris.length > 0 && (
          <div>
            <p className="text-xs text-slate-500 font-medium mb-1">Redirect URIs</p>
            <ul className="space-y-0.5">
              {app.redirect_uris.map((uri) => (
                <li key={uri}>
                  <code className="text-xs font-mono text-slate-600 bg-slate-50 px-2 py-0.5 rounded block truncate">
                    {uri}
                  </code>
                </li>
              ))}
            </ul>
          </div>
        )}
        <p className="text-xs text-slate-400">
          Registered {new Date(app.created_at).toLocaleDateString()}
        </p>
      </div>
    </div>
  )
}

function CreateAppModal({ orgId, onClose, onCreated }: {
  orgId: string
  onClose: () => void
  onCreated: (app: RegisteredApp) => void
}) {
  const [error, setError] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors } } = useForm<AppForm>({
    resolver: zodResolver(appSchema),
    defaultValues: { app_type: 'web' },
  })

  const mutation = useMutation({
    mutationFn: (data: AppForm) =>
      organizationsApi.createApp(orgId, {
        app_name: data.app_name,
        app_type: data.app_type,
        redirect_uris: data.redirect_uris.split('\n').map((s) => s.trim()).filter(Boolean),
      }),
    onSuccess: (app) => {
      onCreated(app)
      onClose()
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e?.response?.data?.detail ?? 'Failed to register app')
    },
  })

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md p-6">
        <h3 className="text-base font-semibold text-slate-900 mb-5">Register Application</h3>

        {error && (
          <div className="flex items-start gap-2 p-3 mb-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
            <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">App Name</label>
            <input
              {...register('app_name')}
              placeholder="My Application"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.app_name && <p className="text-rose-500 text-xs mt-1">{errors.app_name.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">App Type</label>
            <select
              {...register('app_type')}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="web">Web Application</option>
              <option value="desktop">Desktop Application</option>
              <option value="mobile">Mobile Application</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1.5">
              Redirect URIs <span className="text-slate-400 font-normal">(one per line)</span>
            </label>
            <textarea
              {...register('redirect_uris')}
              rows={3}
              placeholder="https://yourapp.com/auth/callback"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
            {errors.redirect_uris && <p className="text-rose-500 text-xs mt-1">{errors.redirect_uris.message}</p>}
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
              Register App
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function AppsPage() {
  const { user } = useAuth()
  const orgId = user?.org_id ?? ''
  const [apps, setApps] = useState<RegisteredApp[]>([])
  const [showCreate, setShowCreate] = useState(false)

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <PageHeader
        title="Applications"
        description="Registered client applications for your organization"
        action={
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="h-4 w-4" />
            Register App
          </button>
        }
      />

      <div className="mb-4 p-4 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800">
        <p className="font-medium mb-0.5">API Keys are shown once</p>
        <p className="text-amber-700">
          After registering an app, copy the API key immediately. It won't be shown in plain text again.
        </p>
      </div>

      {apps.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {apps.map((app) => (
            <AppCard key={app.id} app={app} />
          ))}
        </div>
      ) : (
        <div className="text-center py-16 bg-white rounded-xl border border-slate-200">
          <AppWindow className="h-10 w-10 text-slate-300 mx-auto mb-3" />
          <p className="text-slate-500 mb-1">No applications registered yet.</p>
          <p className="text-slate-400 text-sm">Register client apps to get API keys for rate limiting and OAuth.</p>
        </div>
      )}

      {showCreate && (
        <CreateAppModal
          orgId={orgId}
          onClose={() => setShowCreate(false)}
          onCreated={(app) => setApps((prev) => [app, ...prev])}
        />
      )}
    </div>
  )
}
