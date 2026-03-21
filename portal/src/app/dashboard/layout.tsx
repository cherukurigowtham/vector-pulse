"use client"

import { useState } from "react"
import { Menu, ChevronRight, Home, LogOut } from "lucide-react"
import { SideNav } from "@/components/dashboard/SideNav"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/cn"

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const pathname = usePathname()

  const pathParts = pathname.split('/').filter(Boolean)

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <div className="flex min-h-screen">
        {isSidebarOpen ? (
          <button
            className="fixed inset-0 z-40 bg-slate-900/30 lg:hidden"
            onClick={() => setIsSidebarOpen(false)}
            aria-label="Close sidebar"
          />
        ) : null}

        <SideNav isOpen={isSidebarOpen} onClose={() => setIsSidebarOpen(false)} />

        <main className="flex-1">
          {/* Engineered Pinned Header */}
          <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/80 backdrop-blur-md">
            <div className="mx-auto flex h-[72px] w-full max-w-7xl items-center justify-between px-6 lg:px-10">
              <div className="flex items-center gap-6">
                <button onClick={() => setIsSidebarOpen(true)} className="text-slate-600 lg:hidden p-2 hover:bg-slate-50 rounded-lg">
                  <Menu className="h-6 w-6" />
                </button>
                
                {/* Advanced Breadcrumbs */}
                <nav className="hidden md:flex items-center gap-2.5 text-sm font-bold">
                  <Home className="h-4 w-4 text-slate-400" />
                  <ChevronRight className="h-4 w-4 text-slate-300" />
                  <span className="text-slate-400">Console</span>
                  {pathParts.map((part, index) => (
                    <div key={part} className="flex items-center gap-2.5">
                      <ChevronRight className="h-4 w-4 text-slate-300" />
                      <span className={cn(
                        "capitalize",
                        index === pathParts.length - 1 ? "text-blue-600" : "text-slate-400"
                      )}>
                        {part.replace(/-/g, ' ')}
                      </span>
                    </div>
                  ))}
                </nav>
              </div>

              <div className="flex items-center gap-4">
                <button
                  onClick={() => {
                    localStorage.removeItem('vp_token')
                    window.location.href = '/'
                  }}
                  className="flex items-center gap-2 rounded-xl border border-zinc-200 bg-white px-4 py-2 text-xs font-bold text-zinc-600 hover:bg-zinc-50 hover:text-zinc-900 transition-colors shadow-sm"
                >
                  <LogOut className="h-4 w-4" />
                  <span className="hidden sm:inline">Log out</span>
                </button>
              </div>
            </div>
          </header>

          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</div>
        </main>
      </div>
    </div>
  )
}
