import { SideNav } from "@/components/dashboard/SideNav"

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex h-screen bg-white dark:bg-slate-950">
      <SideNav />
      <main className="flex-1 overflow-y-auto bg-slate-50/30 p-8 dark:bg-slate-950/30">
        <div className="mx-auto max-w-7xl">
          {children}
        </div>
      </main>
    </div>
  )
}
