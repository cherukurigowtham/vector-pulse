"use client"

import { ShieldAlert, Users, Key, Database, Activity } from "lucide-react"

export default function AdminConsole() {
  return (
    <div className="page-shell space-y-8 animate-fade-in-up">
      <div className="flex flex-col gap-2 pb-6 border-b border-zinc-200">
        <div className="inline-flex items-center gap-2 mb-2 rounded-full border border-red-200 bg-red-50 px-3 py-1 text-xs font-semibold text-red-600 shadow-sm w-max">
          <ShieldAlert className="h-4 w-4" />
          Elevated Access Active
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900">System Governance</h1>
        <p className="text-sm text-zinc-500 font-medium">Global platform controls and cross-tenant intelligence.</p>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Users Card */}
        <article className="app-card p-6 border-t-4 border-t-zinc-900">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-zinc-100 text-zinc-900"><Users className="h-5 w-5" /></div>
            <h2 className="text-sm font-semibold text-zinc-900">Workspace Members</h2>
          </div>
          <p className="font-mono text-4xl font-bold tracking-tight text-zinc-900 mb-6">14,204</p>
          <button className="w-full py-2.5 rounded-lg text-xs font-semibold bg-zinc-900 text-white hover:bg-zinc-800 transition-colors shadow-sm">Manage Accounts</button>
        </article>

        {/* Global Policy Card */}
        <article className="app-card p-6 border-t-4 border-t-zinc-900">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-zinc-100 text-zinc-900"><Database className="h-5 w-5" /></div>
            <h2 className="text-sm font-semibold text-zinc-900">Global Neural Weights</h2>
          </div>
          <p className="font-mono text-4xl font-bold tracking-tight text-zinc-900 mb-6">v4.2.0-rc</p>
          <button className="w-full py-2.5 rounded-lg border border-zinc-200 bg-white text-xs font-semibold text-zinc-700 hover:bg-zinc-50 transition-colors shadow-sm">Force Sync Cluster</button>
        </article>

        {/* API Infrastructure */}
        <article className="app-card p-6 border-t-4 border-t-zinc-900">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2 rounded-lg bg-zinc-100 text-zinc-900"><Key className="h-5 w-5" /></div>
            <h2 className="text-sm font-semibold text-zinc-900">Infrastructure Keys</h2>
          </div>
          <p className="font-mono text-4xl font-bold tracking-tight text-zinc-900 mb-6">9 Active</p>
          <button className="w-full py-2.5 rounded-lg border border-red-200 bg-red-50 text-xs font-semibold text-red-700 hover:bg-red-100 transition-colors shadow-sm">Rotate Root Keys</button>
        </article>
      </div>

      <article className="app-card p-6">
        <h2 className="text-base font-semibold text-zinc-900 mb-6">System Alert Feed (Global)</h2>
        <div className="space-y-4">
          <div className="flex items-center justify-between py-3 border-b border-zinc-100 group">
            <div className="flex items-center gap-4">
              <div className="p-2 rounded-full bg-red-50 text-red-600"><Activity className="h-4 w-4" /></div>
              <div>
                <p className="text-sm font-semibold text-zinc-900 tracking-tight">DDoS Mitigation Engaged</p>
                <p className="text-[13px] font-medium text-zinc-500">Auto-scaling edge nodes on AP-South-1</p>
              </div>
            </div>
            <span className="text-[11px] font-mono font-bold text-zinc-400">2 min ago</span>
          </div>
          <div className="flex items-center justify-between py-3 border-b border-zinc-100 group last:border-0">
            <div className="flex items-center gap-4">
              <div className="p-2 rounded-full bg-emerald-50 text-emerald-600"><Database className="h-4 w-4" /></div>
              <div>
                <p className="text-sm font-semibold text-zinc-900 tracking-tight">Neural Net Reallocation</p>
                <p className="text-[13px] font-medium text-zinc-500">Weight sync to all worker clusters completed.</p>
              </div>
            </div>
            <span className="text-[11px] font-mono font-bold text-zinc-400">45 min ago</span>
          </div>
        </div>
      </article>
    </div>
  )
}
