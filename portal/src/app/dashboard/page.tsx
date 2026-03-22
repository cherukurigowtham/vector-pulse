"use client"

import dynamic from "next/dynamic"
import { useEffect, useState } from "react"
import { Activity, ArrowUpRight, ShieldCheck, Zap, Lock } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { GovernanceLog } from "@/components/dashboard/GovernanceLog"
import { cn } from "@/lib/cn"

export type WSMetricPayload = {
  score: number;
  latency_ms: number;
  action: string;
  vector: string;
} | null;

const RiskPulseChart = dynamic(() => import("@/components/dashboard/Charts").then((m) => m.RiskPulseChart), { ssr: false })
const ThreatDistributionChart = dynamic(() => import("@/components/dashboard/Charts").then((m) => m.ThreatDistributionChart), { ssr: false })
const IdentityPulse = dynamic(() => import("@/components/dashboard/IdentityPulse").then((m) => m.IdentityPulse), { ssr: false })

type GovernanceLogEntry = {
  action: string
  timestamp: number
  actor: string
}

type DashboardStats = {
  revenue_recovered?: number
  settlement_velocity?: number
  active_risk_score?: number
  total_scanned?: number
  blocks?: number
  sla_latency?: number
  governance_logs?: GovernanceLogEntry[]
  api_key?: string
}

const SEED_DATA: DashboardStats = {
  revenue_recovered: 12450840,
  settlement_velocity: 98.4,
  active_risk_score: 1.2,
  total_scanned: 8432,
  blocks: 312,
  sla_latency: 14,
  api_key: "VANTIX_SOVEREIGN_2026",
  governance_logs: [
    { action: "BLOCK_RULE_UPDATED", timestamp: Math.floor(Date.now() / 1000) - 300, actor: "auto-governance" },
    { action: "HIGH_VELOCITY_QUARANTINE", timestamp: Math.floor(Date.now() / 1000) - 900, actor: "risk-engine" },
    { action: "THRESHOLD_RECALIBRATED", timestamp: Math.floor(Date.now() / 1000) - 3600, actor: "ml-model-v2" },
  ],
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>(SEED_DATA)
  const [loading, setLoading] = useState(false)
  const [userTier, setUserTier] = useState<string>("Free")
  const [wsMetrics, setWsMetrics] = useState<WSMetricPayload>(null)

  useEffect(() => {
    async function init() {
      try {
        const data = await apiFetch("/merchant/reporting/summary")
        if (data && (data.total_scanned || data.month_scans)) {
          setStats(data as DashboardStats)
        }
        
        const authData = await apiFetch("/security/auth/me").then(r => r.json());
        if (authData && authData.user && authData.user.plan) {
          setUserTier(authData.user.plan);
        } else {
          setUserTier("Growth"); 
        }
      } catch {} finally {
        setLoading(false)
      }
    }
    init()

    const token = localStorage.getItem("vp_token");
    if (!token) return;
    
    const baseUrl = process.env.NEXT_PUBLIC_API_BASE || "https://vantix-wjsk.onrender.com";
    const wsUrl = baseUrl.replace(/^http/, "ws") + `/api/v1/stream/ws/noc?token=${token}`;
    
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.event === "live_telemetry") {
          setWsMetrics(data.metrics);
          
          // Physically update the overarching state layer without polling
          setStats(prev => {
            const isBlocked = data.metrics.action === "BLOCKED";
            return {
              ...prev,
              total_scanned: (prev.total_scanned || 0) + 1,
              blocks: isBlocked ? (prev.blocks || 0) + 1 : prev.blocks,
              governance_logs: isBlocked ? [{
                action: data.metrics.vector,
                timestamp: data.timestamp,
                actor: "live-stream(ai)"
              }, ...(prev.governance_logs || []).slice(0, 4)] : prev.governance_logs
            }
          });
        }
      } catch (_err) {}
    };

    return () => ws.close()
  }, [])

  const cards = [
    {
      title: "Revenue Recovered",
      value: loading ? "..." : `Rs ${(stats.revenue_recovered || 0).toLocaleString()}`,
      note: "+12.4%",
      icon: ShieldCheck,
      color: "text-emerald-900 bg-emerald-100",
      trend: "positive"
    },
    {
      title: "Settlement Velocity",
      value: loading ? "..." : `${stats.settlement_velocity || 0}%`,
      note: "Instant",
      icon: Zap,
      color: "text-blue-900 bg-blue-100",
      trend: "positive"
    },
    {
      title: "Active Risk Score",
      value: loading ? "..." : `${(stats.active_risk_score || 0).toFixed(1)}`,
      note: "Optimal",
      icon: Activity,
      color: "text-zinc-900 bg-zinc-100",
      trend: "positive"
    },
    {
      title: "Service Latency",
      value: loading ? "..." : `${stats.sla_latency || 12}ms`,
      note: "FAANG GRADE",
      icon: Zap,
      color: "text-amber-900 bg-amber-100",
      trend: "positive"
    },
  ]

  return (
    <div className="page-shell space-y-8">
      <div className="flex flex-col gap-2 pb-6 border-b border-zinc-200">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900">Console Overview</h1>
          {userTier && (
            <div className="flex items-center gap-1.5 px-3 py-1 bg-zinc-900 rounded-full shadow-md text-white border border-black transform transition-transform hover:scale-105">
              <Zap className="h-3.5 w-3.5 fill-emerald-400 text-emerald-400" />
              <span className="text-[10px] font-bold tracking-widest uppercase">{userTier} Tier</span>
            </div>
          )}
        </div>
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
          <RiskPulseChart wsMetrics={wsMetrics} />
        </article>

        <article className="app-card p-6">
          <h2 className="mb-6 text-base font-semibold text-zinc-900">Threat Distribution</h2>
          <ThreatDistributionChart wsMetrics={wsMetrics} />
        </article>
      </section>

      <section className="grid gap-5 lg:grid-cols-2">
        <article className="app-card p-6">
          <h2 className="mb-6 text-base font-semibold text-zinc-900">Governance Log</h2>
          <GovernanceLog
            logs={stats.governance_logs?.map((log) => {
              const isThreat = log.actor?.includes("(ai)");
              return {
                id: log.timestamp.toString(),
                time: log.timestamp,
                event: log.action.replace(/_/g, " "),
                status: isThreat ? "Error" : "Audited",
                riskId: isThreat ? `mc_tx_${log.timestamp}` : undefined
              };
            })}
          />
        </article>

        <article className="app-card p-6">
          <div className="flex flex-col h-full bg-zinc-900 rounded-2xl p-6 text-white overflow-hidden relative">
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-8">
                <div className="h-10 w-10 rounded-xl bg-white/10 flex items-center justify-center border border-white/10">
                  <Lock className="h-5 w-5 text-zinc-400" />
                </div>
                <div>
                  <h2 className="text-sm font-bold tracking-tight">Vantix Service Mesh</h2>
                  <p className="text-[10px] text-zinc-500 font-bold uppercase tracking-widest">Sovereign API access</p>
                </div>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-[10px] font-black uppercase tracking-widest text-zinc-500 mb-2">Primary API Key</label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 bg-black/40 border border-white/5 rounded-lg px-4 py-3 text-xs font-mono text-zinc-400">
                      {stats.api_key || "Generating..."}
                    </code>
                  </div>
                </div>
                <p className="text-[11px] text-zinc-500 leading-relaxed font-medium">
                  Use this key for high-velocity (10k+ TPS) risk scoring via the Vantix Go engine. 
                  JWT fallback is disabled for server-to-server sovereign forensics.
                </p>
              </div>
            </div>
            {/* Background decorative element */}
            <div className="absolute top-0 right-0 -mr-16 -mt-16 h-64 w-64 rounded-full bg-zinc-800/10 blur-3xl pointer-events-none" />
          </div>
        </article>
      </section>
    </div>
  )
}
