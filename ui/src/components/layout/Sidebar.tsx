import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Building2,
  Users,
  Shield,
  Globe,
  AppWindow,
  LogOut,
  ChevronRight,
  KeyRound,
} from 'lucide-react'
import { useAuth } from '@/context/AuthContext'
import { authApi } from '@/api/auth'
import { tokenStorage } from '@/utils/token'
import { cn } from '@/lib/utils'

const navItems = [
  { label: 'Dashboard', to: '/', icon: LayoutDashboard },
  { label: 'Organizations', to: '/organizations', icon: Building2 },
  { label: 'Users', to: '/users', icon: Users },
  { label: 'Roles', to: '/roles', icon: Shield },
  { label: 'Endpoints', to: '/endpoints', icon: Globe },
  { label: 'Applications', to: '/apps', icon: AppWindow },
  { label: 'Profile', to: '/profile', icon: KeyRound },
]

export function Sidebar({ onClose }: { onClose?: () => void }) {
  const { user, logout } = useAuth()
  const location = useLocation()

  const handleLogout = async () => {
    const refreshToken = tokenStorage.getRefreshToken()
    if (refreshToken) {
      try {
        await authApi.revokeToken(refreshToken)
      } catch {
        // ignore errors on logout
      }
    }
    logout()
  }

  return (
    <div className="flex flex-col h-full bg-slate-900 text-slate-100 w-64 shrink-0">
      {/* Brand */}
      <div className="px-6 py-5 border-b border-slate-700/50">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center text-white font-bold text-sm">
            AY
          </div>
          <div>
            <p className="font-semibold text-white text-sm leading-none">authYantra</p>
            <p className="text-xs text-slate-400 mt-0.5">Identity Service</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-0.5 overflow-y-auto">
        {navItems.map(({ label, to, icon: Icon }) => {
          const isActive =
            to === '/' ? location.pathname === '/' : location.pathname.startsWith(to)
          return (
            <NavLink
              key={to}
              to={to}
              onClick={onClose}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors group',
                isActive
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white hover:bg-slate-800',
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span className="flex-1">{label}</span>
              {isActive && <ChevronRight className="h-3.5 w-3.5 opacity-60" />}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="px-3 py-4 border-t border-slate-700/50 space-y-1">
        {user && (
          <div className="px-3 py-2">
            <p className="text-xs font-medium text-white truncate">{user.email || 'User'}</p>
            <p className="text-xs text-slate-400 truncate">
              {user.roles.join(', ') || 'No roles'}
            </p>
          </div>
        )}
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <LogOut className="h-4 w-4 shrink-0" />
          Sign out
        </button>
      </div>
    </div>
  )
}
