import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import {
  ArrowLeft, Settings2, Loader2, AlertCircle, CheckCircle2, Plus, AppWindow,
} from 'lucide-react'
import { organizationsApi } from '@/api/organizations'
import { PageHeader } from '@/components/ui/PageHeader'
import type { CreateAppRequest } from '@/types'

const entraSchema = z.object({
  tenant_id: z.string().min(1, 'Tenant ID is required'),
  client_id: z.string().min(1, 'Client ID is required'),
  client_secret: z.string().min(1, 'Client secret is required'),
})
type EntraForm = z.infer<typeof entraSchema>

const appSchema = z.object({
  app_name: z.string().min(2, 'App name is required'),
  app_type: z.enum(['web', 'desktop', 'mobile']),
  redirect_uris: z.string().min(1, 'At least one redirect URI is required'),
})
type AppForm = z.infer<typeof appSchema>

function EntraIdSection({ orgId }: { orgId: string }) {
  const queryClient = useQueryClient()
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors } } = useForm<EntraForm>({
    resolver: zodResolver(entraSchema),
  })

  const mutation = useMutation({
    mutationFn: (data: EntraForm) => organizationsApi.updateEntraId(orgId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['org', orgId] })
      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e?.response?.data?.detail ?? 'Failed to update Entra ID config')
    },
  })

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <h3 className="font-semibold text-slate-800 mb-1 flex items-center gap-2">
        <Settings2 className="h-4 w-4 text-blue-500" />
        Microsoft Entra ID SSO
      </h3>
      <p className="text-sm text-slate-500 mb-4">
        Configure Entra ID (Azure AD) for Single Sign-On for this organization.
      </p>

      {error && (
        <div className="flex items-start gap-2 p-3 mb-4 bg-rose-50 border border-rose-200 rounded-lg text-rose-700 text-sm">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          {error}
        </div>
      )}
      {success && (
        <div className="flex items-center gap-2 p-3 mb-4 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-700 text-sm">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          Entra ID configured successfully.
        </div>
      )}

      <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-3">
        {[
          { name: 'tenant_id' as const, label: 'Directory (Tenant) ID' },
          { name: 'client_id' as const, label: 'Application (Client) ID' },
          { name: 'client_secret' as const, label: 'Client Secret', type: 'password' },
        ].map(({ name, label, type }) => (
          <div key={name}>
            <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
            <input
              {...register(name)}
              type={type ?? 'text'}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors[name] && (
              <p className="text-rose-500 text-xs mt-1">{errors[name]?.message}</p>
            )}
          </div>
        ))}
        <button
          type="submit"
          disabled={mutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-60"
        >
          {mutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
          Save Entra ID Config
        </button>
      </form>
    </div>
  )
}

function AddAppSection({ orgId }: { orgId: string }) {
  const queryClient = useQueryClient()
  const [show, setShow] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { register, handleSubmit, reset, formState: { errors } } = useForm<AppForm>({
    resolver: zodResolver(appSchema),
    defaultValues: { app_type: 'web' },
  })

  const mutation = useMutation({
    mutationFn: (data: AppForm) => {
      const payload: CreateAppRequest = {
        app_name: data.app_name,
        app_type: data.app_type,
        redirect_uris: data.redirect_uris.split('\n').map((s) => s.trim()).filter(Boolean),
      }
      return organizationsApi.createApp(orgId, payload)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['apps', orgId] })
      reset()
      setShow(false)
    },
    onError: (err: unknown) => {
      const e = err as { response?: { data?: { detail?: string } } }
      setError(e?.response?.data?.detail ?? 'Failed to register app')
    },
  })

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-slate-800 flex items-center gap-2">
          <AppWindow className="h-4 w-4 text-indigo-500" />
          Applications
        </h3>
        <button
          onClick={() => setShow(!show)}
          className="flex items-center gap-1.5 text-xs text-indigo-600 hover:text-indigo-800 font-medium"
        >
          <Plus className="h-3.5 w-3.5" />
          Register App
        </button>
      </div>

      {show && (
        <form onSubmit={handleSubmit((d) => mutation.mutate(d))} className="space-y-3 mb-4 p-4 bg-slate-50 rounded-lg border border-slate-200">
          {error && (
            <div className="text-rose-600 text-xs flex items-start gap-1.5">
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              {error}
            </div>
          )}
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">App Name</label>
            <input
              {...register('app_name')}
              className="w-full px-3 py-1.5 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {errors.app_name && <p className="text-rose-500 text-xs mt-0.5">{errors.app_name.message}</p>}
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">App Type</label>
            <select
              {...register('app_type')}
              className="w-full px-3 py-1.5 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="web">Web</option>
              <option value="desktop">Desktop</option>
              <option value="mobile">Mobile</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">
              Redirect URIs <span className="text-slate-400">(one per line)</span>
            </label>
            <textarea
              {...register('redirect_uris')}
              rows={3}
              placeholder="https://yourapp.com/callback"
              className="w-full px-3 py-1.5 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
            />
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={() => setShow(false)} className="px-3 py-1.5 border border-slate-300 text-slate-700 rounded-md text-xs font-medium">Cancel</button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-600 text-white rounded-md text-xs font-medium disabled:opacity-60"
            >
              {mutation.isPending && <Loader2 className="h-3 w-3 animate-spin" />}
              Register
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

export function OrganizationDetailPage() {
  const { orgId } = useParams<{ orgId: string }>()
  const navigate = useNavigate()

  const { data: org, isLoading } = useQuery({
    queryKey: ['org', orgId],
    queryFn: () => organizationsApi.getById(orgId!),
    enabled: !!orgId,
  })

  if (isLoading) {
    return (
      <div className="p-6 flex items-center gap-2 text-slate-500">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading organization…
      </div>
    )
  }

  if (!org) {
    return (
      <div className="p-6">
        <p className="text-slate-500">Organization not found.</p>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <button
        onClick={() => navigate('/organizations')}
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-800 mb-5 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Organizations
      </button>

      <PageHeader
        title={org.name}
        description={`ID: ${org.id}`}
        action={
          <span
            className={`text-xs px-2.5 py-1 rounded-full font-medium ${
              org.is_active
                ? 'bg-emerald-100 text-emerald-700'
                : 'bg-slate-100 text-slate-500'
            }`}
          >
            {org.is_active ? 'Active' : 'Inactive'}
          </span>
        }
      />

      <div className="space-y-5">
        {/* Details */}
        <div className="bg-white rounded-xl border border-slate-200 p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Organization Details</h3>
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { label: 'Name', value: org.name },
              { label: 'ID', value: org.id },
              { label: 'Created', value: new Date(org.created_at).toLocaleString() },
              { label: 'Updated', value: new Date(org.updated_at).toLocaleString() },
              { label: 'Entra Tenant ID', value: org.entra_id_tenant_id ?? 'Not set' },
              { label: 'Entra Client ID', value: org.entra_id_client_id ?? 'Not set' },
            ].map(({ label, value }) => (
              <div key={label} className="p-3 bg-slate-50 rounded-lg">
                <dt className="text-xs text-slate-500 mb-0.5">{label}</dt>
                <dd className="text-sm font-medium text-slate-800 break-all">{value}</dd>
              </div>
            ))}
          </dl>
        </div>

        <EntraIdSection orgId={orgId!} />
        <AddAppSection orgId={orgId!} />
      </div>
    </div>
  )
}
