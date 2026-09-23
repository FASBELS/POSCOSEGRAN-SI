import { View } from '../types'
import {
  IconHome,
  IconClipboard,
  IconActivity,
  IconBook,
  IconPackage,
  IconShield,
  IconTrending,
  IconSettings,
  IconChevronLeft,
  IconChevronRight,
} from './Icons'

interface SidebarProps {
  activeView: View
  onNavigate: (view: View) => void
  collapsed: boolean
  onToggle: () => void
  roles: string[]
}

// `roles` vacío: visible para todos. Si no, solo para esos roles.
const NAV_ITEMS: { id: View; label: string; Icon: React.FC<{ size?: number; className?: string }>; roles?: string[] }[] = [
  { id: 'dashboard', label: 'Inicio', Icon: IconHome },
  { id: 'almacenes', label: 'Almacenes y lotes', Icon: IconPackage, roles: ['PRODUCTOR', 'TECNICO'] },
  { id: 'evaluacion', label: 'Evaluaciones', Icon: IconClipboard, roles: ['PRODUCTOR', 'TECNICO'] },
  { id: 'seguimiento', label: 'Seguimiento', Icon: IconActivity, roles: ['PRODUCTOR', 'TECNICO'] },
  { id: 'revision', label: 'Revisión técnica', Icon: IconShield, roles: ['TECNICO'] },
  { id: 'conocimiento', label: 'Base de Conocimiento', Icon: IconBook },
  { id: 'adquisicion', label: 'Adquisición', Icon: IconTrending, roles: ['INGENIERO_CONOCIMIENTO'] },
  { id: 'configuracion', label: 'Configuración', Icon: IconSettings },
]

export default function Sidebar({ activeView, onNavigate, collapsed, onToggle, roles }: SidebarProps) {
  const visibles = NAV_ITEMS.filter(item => !item.roles || item.roles.some(r => roles.includes(r)))
  return (
    <div
      className="sidebar fixed left-0 top-0 h-screen flex flex-col z-30 transition-all duration-300"
      style={{
        width: collapsed ? 64 : 240,
        backgroundColor: '#1B3B2B',
        borderRight: '1px solid rgba(255,255,255,0.08)',
      }}
    >
      {/* Logo */}
      <div
        className="flex items-center gap-3 px-4 py-5 border-b"
        style={{ borderColor: 'rgba(255,255,255,0.1)', minHeight: 64 }}
      >
        <div
          className="flex items-center justify-center rounded-lg flex-shrink-0"
          style={{ width: 32, height: 32, backgroundColor: '#E5A93C' }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#1B3B2B" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="M12 2C8 2 5 5 5 9c0 5 7 13 7 13s7-8 7-13c0-4-3-7-7-7z" />
            <circle cx="12" cy="9" r="2" />
          </svg>
        </div>
        {!collapsed && (
          <div className="overflow-hidden">
            <p className="text-white font-bold text-sm leading-tight tracking-wide">POSCOSEGRAN</p>
            <p className="text-xs leading-tight" style={{ color: 'rgba(229,169,60,0.8)' }}>Gestión Poscosecha</p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 overflow-y-auto">
        {visibles.map(({ id, label, Icon }) => {
          const active = activeView === id
          return (
            <button
              key={id}
              onClick={() => onNavigate(id)}
              title={collapsed ? label : undefined}
              className="w-full flex items-center gap-3 rounded-lg mb-1 text-left transition-all duration-150 group"
              style={{
                padding: collapsed ? '10px 12px' : '10px 12px',
                backgroundColor: active ? 'rgba(229,169,60,0.18)' : 'transparent',
                borderLeft: active ? '3px solid #E5A93C' : '3px solid transparent',
                color: active ? '#E5A93C' : 'rgba(255,255,255,0.65)',
                minHeight: 44,
              }}
              onMouseEnter={e => {
                if (!active) {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'rgba(255,255,255,0.07)'
                  ;(e.currentTarget as HTMLButtonElement).style.color = '#ffffff'
                }
              }}
              onMouseLeave={e => {
                if (!active) {
                  (e.currentTarget as HTMLButtonElement).style.backgroundColor = 'transparent'
                  ;(e.currentTarget as HTMLButtonElement).style.color = 'rgba(255,255,255,0.65)'
                }
              }}
            >
              <Icon size={18} className="flex-shrink-0" />
              {!collapsed && (
                <span className="text-sm font-medium whitespace-nowrap overflow-hidden">{label}</span>
              )}
            </button>
          )
        })}
      </nav>

      {/* Version */}
      {!collapsed && (
        <div className="px-4 py-3 border-t" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
          <p className="text-xs" style={{ color: 'rgba(255,255,255,0.3)' }}>Sistema experto · Prototipo académico</p>
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={onToggle}
        className="flex items-center justify-center border-t"
        style={{
          minHeight: 44,
          borderColor: 'rgba(255,255,255,0.1)',
          color: 'rgba(255,255,255,0.4)',
          backgroundColor: 'transparent',
          transition: 'color 0.15s',
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.color = '#ffffff' }}
        onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.color = 'rgba(255,255,255,0.4)' }}
        title={collapsed ? 'Expandir menú' : 'Colapsar menú'}
      >
        {collapsed ? <IconChevronRight size={16} /> : <IconChevronLeft size={16} />}
      </button>
    </div>
  )
}
