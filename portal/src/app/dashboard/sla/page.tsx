"use client"

import { useState } from "react"
import { Activity, ArrowUpRight, History, ShieldCheck } from "lucide-react"
import type { LucideIcon } from "lucide-react"
import { GovernanceLog } from "@/components/dashboard/GovernanceLog"
import type { GovernanceLogItem } from "@/components/dashboard/GovernanceLog"

const SEED_DATA: {
  avg_latency: number
  uptime: number
  accuracy: number
  total_scans: number
  governance_logs: GovernanceLogItem[]
} = {
  avg_latency: 12.42,
  uptime: 100,
  accuracy: 99.98,
  total_scans: 1284902,
  governance_logs: [
    { time: "10:45", event: "Weight tuning completed for block_rule_7", status: "Success" },
    { time: "10:48", event: "Merchant key rotation audited", status: "Audited" },
    { time: "10:50", event: "Latency SLA check passed", status: "Nominal" },
    { time: "11:02", event: "Risk cache synchronization complete", status: "Success" },
  ],
}

export default function SLAMonitor() {
  const [stats] = useState(SEED_DATA)

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">SLA Monitor</h1>
        <p className="text-sm text-slate-600">Availability, latency, and model accuracy tracking.</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard title="Accuracy" value={`${stats.accuracy}%`} change="Stable" icon={ShieldCheck} />
        <StatCard title="Avg Latency" value={`${stats.avg_latency}ms`} change="-1.2ms" icon={Activity} />
        <StatCard title="Uptime" value={`${stats.uptime}%`} change="Target met" icon={History} />
      </div>

      <section className="app-card p-5">
        <h2 className="mb-4 flex items-center gap-2 text-sm font-bold text-slate-900">
          <History className="h-4 w-4" />
          Service Events
        </h2>
        <GovernanceLog logs={stats.governance_logs} />
      </section>
    </div>
  )
}

function StatCard({ title, value, change, icon: Icon }: { title: string; value: string; change: string; icon: LucideIcon }) {
  return (
    <article className="app-card p-5">
      <div className="flex items-center justify-between">
        <div className="rounded-xl bg-blue-50 p-2.5 text-blue-600">
          <Icon className="h-5 w-5" />
        </div>
        <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500">
          {change}
          <ArrowUpRight className="h-3.5 w-3.5" />
        </span>
      </div>
      <p className="mt-3 text-sm font-semibold text-slate-500">{title}</p>
      <p className="metric-value mt-1 text-2xl font-bold text-slate-900">{value}</p>
    </article>
  )
}
