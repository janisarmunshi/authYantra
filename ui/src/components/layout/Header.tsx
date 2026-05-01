import { useState } from 'react'
import { Menu, Bell, Building2, ChevronDown, Check, LogOut, Plus } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { authApi } from '@/api/auth'
import { useNavigate } from 'react-router-dom'

interface HeaderProps {
  onMenuClick: () => void
  title?: string
}

export function Header({ onMenuClick, title }: HeaderProps) {
  const { user, logout, completeOrgSelection } = useAuth()
  const [orgOpen, setOrgOpen] = useState(false)
  const [userOpen, setUserOpen] = useState(false)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: orgs = [] } = useQuery({
    queryKey: ['my-orgs'],
    queryFn: authApi.myOrgs,
    enabled: !!user,
  })

  const switchMutation = useMutation({
    mutationFn: (orgId: string) => authApi.switchOrg(orgId),
    onSuccess: (data) => {
      completeOrgSelection(data.access_token, data.refresh_token)
      queryClient.invalidateQueries()
      setOrgOpen(false)
    },
  })

  const setDefaultMutation = useMutation({
    mutationFn: (orgId: string) => authApi.setDefaultOrg(orgId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['my-orgs'] }),
  })

  const currentOrg = orgs.find((o) => o.id === user?.org_id)

  const handleLogout = async () => {
    const refresh = localStorage.getItem('refresh_token')
    if (refresh) { try { await authApi.revokeToken(refresh) } catch {} }
    logout()
    navigate('/login')
  }

  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center px-4 gap-4 shrink-0 relative z-30">
      <button
        onClick={onMenuClick}
        className="lg:hidden p-1.5 rounded-md hover:bg-slate-100 transition-colors"
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5 text-slate-600" />
      </button>

      {title && <h1 className="text-base font-semibold text-slate-800 hidden sm:block">{title}</h1>}

      <div className="flex-1" />

      <div className="flex items-center gap-2">
        {/* Org Switcher */}
        {user && (
          <div className="relative">
            <button
              onClick={() => { setOrgOpen((o) => !o); setUserOpen(false) }}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-slate-50 transition-colors text-sm"
            >
              <Building2 className="h-4 w-4 text-slate-500" />
              <span className="hidden sm:block text-slate-700 font-medium max-w-[140px] truncate">
                {currentOrg?.name ?? 'No organization'}
              </span>
              <ChevronDown className="h-3.5 w-3.5 text-slate-400" />
            </button>

            {orgOpen && (
              <div className="absolute right-0 top-full mt-1 w-64 bg-white border border-slate-200 rounded-xl shadow-lg py-1 z-50">
                <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide px-3 py-2">
                  Your Organizations
                </p>
                {orgs.map((org) => (
                  <div key={org.id} className="flex items-center gap-2 px-2">
                    <button
                      onClick={() => switchMutation.mutate(org.id)}
                      className={`flex-1 flex items-center gap-2 px-2 py-2 rounded-lg text-sm transition-colors ${
                        org.id === user.org_id ? 'bg-indigo-50 text-indigo-700' : 'hover:bg-slate-50 text-slate-700'
                      }`}
                    >
                      <div className="w-6 h-6 rounded bg-indigo-100 flex items-center justify-center text-indigo-600 text-xs font-bold shrink-0">
                        {org.name[0].toUpperCase()}
                      </div>
                      <span className="truncate font-medium">{org.name}</span>
                      {org.id === user.org_id && <Check className="h-3.5 w-3.5 ml-auto shrink-0" />}
                    </button>
                    {!org.is_default && (
                      <button
                        onClick={() => setDefaultMutation.mutate(org.id)}
                        title="Set as default"
                        className="text-xs text-slate-400 hover:text-indigo-600 px-1 py-1 rounded"
                      >
                        default
                      </button>
                    )}
                    {org.is_default && (
                      <span className="text-xs text-indigo-400 px-1">★</span>
                    )}
                  </div>
                ))}

                <div className="border-t border-slate-100 mt-1 pt-1">
                  <button
                    onClick={() => { navigate('/organizations'); setOrgOpen(false) }}
                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-600 hover:bg-slate-50 transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                    Create or manage orgs
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        <button className="p-1.5 rounded-md hover:bg-slate-100 transition-colors relative">
          <Bell className="h-5 w-5 text-slate-500" />
        </button>

        {/* User menu */}
        <div className="relative">
          <button
            onClick={() => { setUserOpen((o) => !o); setOrgOpen(false) }}
            className="flex items-center gap-2 pl-2 border-l border-slate-200"
          >
            <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold text-xs uppercase">
              {user?.email?.[0] ?? 'U'}
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-xs font-medium text-slate-800 leading-none">{user?.email ?? 'User'}</p>
              <p className="text-xs text-slate-400 mt-0.5">{user?.roles?.[0] ?? '—'}</p>
            </div>
          </button>

          {userOpen && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-white border border-slate-200 rounded-xl shadow-lg py-1 z-50">
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2 px-3 py-2 text-sm text-rose-600 hover:bg-rose-50 transition-colors"
              >
                <LogOut className="h-4 w-4" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Close dropdowns on outside click */}
      {(orgOpen || userOpen) && (
        <div className="fixed inset-0 z-20" onClick={() => { setOrgOpen(false); setUserOpen(false) }} />
      )}
    </header>
  )
}
