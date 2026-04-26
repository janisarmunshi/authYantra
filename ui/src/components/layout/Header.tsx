import { Menu, Bell } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

interface HeaderProps {
  onMenuClick: () => void
  title?: string
}

export function Header({ onMenuClick, title }: HeaderProps) {
  const { user } = useAuth()

  return (
    <header className="h-14 bg-white border-b border-slate-200 flex items-center px-4 gap-4 shrink-0">
      <button
        onClick={onMenuClick}
        className="lg:hidden p-1.5 rounded-md hover:bg-slate-100 transition-colors"
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5 text-slate-600" />
      </button>

      {title && (
        <h1 className="text-base font-semibold text-slate-800 hidden sm:block">{title}</h1>
      )}

      <div className="flex-1" />

      <div className="flex items-center gap-2">
        <button className="p-1.5 rounded-md hover:bg-slate-100 transition-colors relative">
          <Bell className="h-5 w-5 text-slate-500" />
        </button>

        <div className="flex items-center gap-2 pl-2 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-indigo-100 flex items-center justify-center text-indigo-700 font-semibold text-xs uppercase">
            {user?.email?.[0] ?? 'U'}
          </div>
          <div className="hidden sm:block">
            <p className="text-xs font-medium text-slate-800 leading-none">
              {user?.email ?? 'User'}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">
              {user?.roles?.[0] ?? '—'}
            </p>
          </div>
        </div>
      </div>
    </header>
  )
}
