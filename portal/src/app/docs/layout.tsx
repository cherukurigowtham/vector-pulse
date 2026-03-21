import Navigation from "@/components/Navigation"

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <Navigation />
      <div className="container grid gap-8 pb-14 pt-32 lg:grid-cols-[220px,1fr]">
        <aside className="app-card h-fit p-4">
          <p className="kicker mb-3">Documentation</p>
          <nav className="space-y-2 text-sm font-medium text-slate-600">
            <a href="#installation" className="block rounded-lg px-2 py-1 hover:bg-slate-50 hover:text-slate-900">Installation</a>
            <a href="#sdk-usage" className="block rounded-lg px-2 py-1 hover:bg-slate-50 hover:text-slate-900">SDK Usage</a>
            <a href="#api-reference" className="block rounded-lg px-2 py-1 hover:bg-slate-50 hover:text-slate-900">API Reference</a>
          </nav>
        </aside>
        <main>{children}</main>
      </div>
    </div>
  )
}
