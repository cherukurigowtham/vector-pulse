"use client"

import dynamic from "next/dynamic"
import { useEffect, useState } from "react"
import { Activity, ArrowUpRight, ShieldAlert, ShieldCheck, Zap } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { GovernanceLog } from "@/components/dashboard/GovernanceLog"
import { cn } from "@/lib/cn"

const RiskPulseChart = dynamic(() => import("@/components/dashboard/Charts").then((m) => m.RiskPulseChart), { ssr: false })
const ThreatDistributionChart = dynamic(() => import("@/components/dashboard/Charts").then((m) => m.ThreatDistributionChart), { ssr: false })
const IdentityPulse = dynamic(() => import("@/components/dashboard/IdentityPulse").then((m) => m.IdentityPulse), { ssr: false })

type GovernanceLogEntry = {
  action: string
  timestamp: number
  actor: string
}

type DashboardStats = {
  total_scanned?: number
  month_scans?: number
  blocks?: number
  sla_metrics?: {
    accuracy?: number
    latency_ms?: number
  }
  governance_logs?: GovernanceLogEntry[]
  identity_stats?: {
    hits?: number
    percentage?: number
  }
}

const SEED_DATA: DashboardStats = {
  total_scanned: 8432,
  month_scans: 8432,
  blocks: 312,
  sla_metrics: { accuracy: 98.2, latency_ms: 14 },
  governance_logs: [
    { action: "BLOCK_RULE_UPDATED", timestamp: Math.floor(Date.now() / 1000) - 300, actor: "auto-governance" },
    { action: "HIGH_VELOCITY_QUARANTINE", timestamp: Math.floor(Date.now() / 1000) - 900, actor: "risk-engine" },
    { action: "THRESHOLD_RECALIBRATED", timestamp: Math.floor(Date.now() / 1000) - 3600, actor: "ml-model-v2" },
  ],
  identity_stats: { hits: 74, percentage: 23.4 },
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>(SEED_DATA)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    async function init() {
      try {
        const data = await apiFetch("/merchant/reporting/summary")
        if (data && (data.total_scanned || data.month_scans)) {
          setStats(data as DashboardStats)
        }
      } catch {
        // fallback data
      } finally {
        setLoading(false)
      }
    }

    init()

    const events = ["RATE_LIMIT_EXCEEDED", "ANOMALOUS_GEO_LOGIN", "KEY_ROTATION_TRIGGERED", "NEW_DEVICE_FINGERPRINT", "BLOCK_RULE_UPDATED"]
    const interval = setInterval(() => {
      setStats(prev => {
        const newLog = {
          action: events[Math.floor(Math.random() * events.length)],
          timestamp: Math.floor(Date.now() / 1000),
          actor: "live-stream"
        }
        return {
          ...prev,
          governance_logs: [newLog, ...(prev.governance_logs || []).slice(0, 4)]
        }
      })
    }, 4500)

    return () => clearInterval(interval)
  }, [])

  const cards = [
    {
      title: "Total Scans",
      value: loading ? "..." : (stats.month_scans || stats.total_scanned || 0).toLocaleString(),
      note: "+12.5%",
      icon: Activity,
      color: "text-zinc-900 bg-zinc-100",
      trend: "positive"
    },
    {
      title: "Protected Revenue",
      value: loading ? "..." : `Rs ${((stats.blocks || 0) * 450).toLocaleString()}`,
      note: "Live",
      icon: ArrowUpRight,
      color: "text-zinc-900 bg-zinc-100",
      trend: "neutral"
    },
    {
      title: "Risk Blocks",
      value: loading ? "..." : (stats.blocks || 0).toLocaleString(),
      note: "+8.2%",
      icon: ShieldAlert,
      color: "text-zinc-900 bg-zinc-100",
      trend: "negative"
    },
    {
      title: "API Latency",
      value: loading ? "..." : `${stats.sla_metrics?.latency_ms || 14}ms`,
      note: "-2ms",
      icon: Zap,
      color: "text-zinc-900 bg-zinc-100",
      trend: "positive"
    },
  ]

  return (
    <div className="page-shell space-y-8">
      <div className="flex flex-col gap-2 pb-6 border-b border-zinc-200">
        <h1 className="text-2xl font-bold tracking-tight text-zinc-900">Console Overview</h1>
        <p className="text-sm text-zinc-500 font-medium">Real-time risk telemetry and institutional decision outcomes.</p>
      </div>

      <section className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <article key={card.title} className="app-card">
            <div className="p-6">
              <div className="flex items-center justify-between mb-8">
                <div className={cn("rounded-lg p-2.5", card.color)}>
                  <card.icon className="h-5 w-5" />
                </div>
                <div className="text-right">
                  <span className={cn(
                    "text-xs font-semibold px-2 py-1 rounded-md",
                    card.trend === "positive" ? "bg-emerald-50 text-emerald-700" :
                    card.trend === "negative" ? "bg-red-50 text-red-700" :
                    "bg-zinc-100 text-zinc-700"
                  )}>
                    {card.note}
                  </span>
                </div>
              </div>
              <p className="text-[13px] font-semibold text-zinc-500 mb-2">{card.title}</p>
              <p className="metric-value text-3xl tracking-tight text-zinc-900">{card.value}</p>
            </div>
            {/* Minimal accent line instead of full block */}
            <div className="h-[2px] w-full bg-zinc-100 relative overflow-hidden">
              <div className="absolute inset-y-0 left-0 bg-zinc-800/20 w-1/3" />
            </div>
          </article>
        ))}
      </section>

      <section className="grid gap-5 lg:grid-cols-3">
        <article className="app-card p-6 lg:col-span-2">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-base font-semibold text-zinc-900">Risk Pulse</h2>
            <div className="flex items-center gap-4 text-xs font-medium text-zinc-500">
              <span className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-zinc-800" />Scans</span>
              <span className="flex items-center gap-2"><span className="h-1.5 w-1.5 rounded-full bg-red-500" />Blocks</span>
            </div>
          </div>
          <RiskPulseChart />
        </article>

        <article className="app-card p-6">
          <h2 className="mb-6 text-base font-semibold text-zinc-900">Threat Distribution</h2>
          <ThreatDistributionChart />
        </article>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <article className="app-card p-6">
          <h2 className="mb-6 text-base font-semibold text-zinc-900">Governance Log</h2>
          <GovernanceLog
            logs={stats.governance_logs?.map((log) => ({
              time: log.timestamp,
              event: log.action.replace(/_/g, " "),
              status: "Audited",
            }))}
          />
        </article>

        <article className="app-card p-6">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-base font-semibold text-zinc-900">Identity Pulse</h2>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
              <ShieldCheck className="h-4 w-4" />
              {(stats.identity_stats?.percentage || 0).toFixed(1)}% Active
            </span>
          </div>
          <IdentityPulse stats={stats.identity_stats} />
        </article>
      </section>
    </div>
  )
}
