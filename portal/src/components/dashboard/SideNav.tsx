"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  History,
  Activity,
  BrainCircuit,
  ShieldCheck,
  CreditCard,
  Settings,
  LogOut,
  X,
  Zap,
} from "lucide-react"
import { cn } from "@/lib/cn"

const navGroups = [
  {
    title: "Intelligence Hub",
    items: [
      { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
      { name: "Admin Console", href: "/dashboard/admin", icon: ShieldCheck },
      { name: "AI Forensics", href: "/dashboard/forensics", icon: BrainCircuit },
      { name: "SLA Monitor", href: "/dashboard/sla", icon: Activity },
    ]
  },
  {
    title: "Operations",
    items: [
      { name: "Audit Feed", href: "/dashboard/audits", icon: History },
      { name: "Risk Rules", href: "/dashboard/rules", icon: ShieldCheck },
    ]
  },
  {
    title: "Governance & Billing",
    items: [
      { name: "Billing", href: "/dashboard/billing", icon: CreditCard },
      { name: "Settings", href: "/dashboard/settings", icon: Settings },
    ]
  }
]

export function SideNav({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const pathname = usePathname()

  return (
    <aside
      className={cn(
        "fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-slate-200 bg-white transition-transform duration-300 lg:relative lg:translate-x-0",
        isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0",
      )}
    >
      <div className="flex h-[72px] items-center justify-between border-b border-slate-200 px-5">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--primary)] text-[var(--bg)]">
            <Zap className="h-4 w-4" />
          </div>
          <span className="text-base font-bold tracking-tight text-[var(--text)]">Vantix</span>
        </Link>

        <button onClick={onClose} className="text-slate-500 lg:hidden">
          <X className="h-5 w-5" />
        </button>
      </div>

      <nav className="flex-1 space-y-8 p-4 pt-6">
        {navGroups.map((group) => (
          <div key={group.title} className="space-y-2">
            <h4 className="px-3 text-[10px] font-black uppercase tracking-[0.2em] text-slate-400">
              {group.title}
            </h4>
            <div className="space-y-1">
              {group.items.map((item) => {
                const active = pathname === item.href
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={onClose}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-bold transition-all duration-200",
                      active 
                        ? "bg-blue-50 text-blue-600 shadow-sm" 
                        : "text-slate-500 hover:bg-slate-50 hover:text-slate-900",
                    )}
                  >
                    <item.icon className={cn("h-4.5 w-4.5 transition-colors", active ? "text-blue-600" : "text-slate-400")} />
                    <span>{item.name}</span>
                  </Link>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="border-t border-slate-200 p-3">
        <button 
          onClick={() => {
            localStorage.removeItem('vp_token')
            window.location.href = '/'
          }}
          className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50 hover:text-slate-900"
        >
          <LogOut className="h-4.5 w-4.5" />
          Sign out
        </button>
      </div>
    </aside>
  )
}
