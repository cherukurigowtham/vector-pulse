"use client"

import { RiskPulseChart, ThreatDistributionChart } from "@/components/dashboard/Charts"
import { GovernanceLog } from "@/components/dashboard/GovernanceLog"
import { IdentityPulse } from "@/components/dashboard/IdentityPulse"
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"
import { useEffect, useState } from "react"
import { apiFetch } from "@/lib/api"
import { History, ShieldCheck, Zap, Activity, ShieldAlert, TrendingDown, ArrowUpRight, Clock, Target } from "lucide-react"

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export default function Dashboard() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function init() {
      try {
        const data = await apiFetch("/merchant/reporting/summary")
        setStats(data)
      } catch (err) {
        console.error("Failed to fetch dashboard stats:", err)
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Enterprise Overview</h1>
          <p className="text-slate-500">Real-time fraud intelligence at your fingertips.</p>
        </div>
        <div className="flex gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-700 border border-emerald-100 dark:bg-emerald-900/20 dark:text-emerald-400 dark:border-emerald-800 text-[10px] font-black uppercase tracking-widest shadow-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
            System Live
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard 
          title="Total Scanned" 
          value={loading ? "..." : stats?.total_scanned?.toLocaleString() || "0"} 
          change="+12.5%" 
          trend="up" 
          icon={Activity} 
        />
        <StatCard 
          title="Blocked Orders" 
          value={loading ? "..." : stats?.blocks?.toLocaleString() || "0"} 
          change="+8.2%" 
          trend="up" 
          icon={ShieldAlert} 
          color="red"
        />
        <StatCard 
          title="Model Accuracy" 
          value={loading ? "..." : `${stats?.sla_metrics?.accuracy || "94.2"}%`} 
          change="+0.8%" 
          trend="up" 
          icon={Target} 
          color="green"
        />
        <StatCard 
          title="Avg Latency" 
          value={loading ? "..." : `${stats?.sla_metrics?.latency_ms || "82"}ms`} 
          change="-5.1%" 
          trend="down" 
          icon={Zap} 
          color="indigo"
        />
      </div>

      {/* Main Charts Section */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
           <div className="flex items-center justify-between mb-6">
              <h3 className="font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                <Activity className="h-4 w-4 text-indigo-500" />
                Risk Pulse (Last 24h)
              </h3>
              <div className="flex items-center gap-4 text-xs font-medium text-slate-500 uppercase tracking-wider">
                <span className="flex items-center gap-1.5 font-bold"><span className="h-2 w-2 rounded-full bg-indigo-500"></span> Total Scans</span>
                <span className="flex items-center gap-1.5 font-bold"><span className="h-2 w-2 rounded-full bg-red-500"></span> Blocked</span>
              </div>
           </div>
           <RiskPulseChart />
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
           <h3 className="font-semibold text-slate-800 dark:text-slate-100 mb-6 flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-red-500" />
              Threat Vectors
           </h3>
           <ThreatDistributionChart />
           <div className="mt-6 space-y-3">
              <p className="text-xs text-slate-400 font-medium uppercase tracking-widest">Key Findings</p>
              <div className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed italic border-l-2 border-amber-400 pl-3">
                "Velocity spikes in Mumbai region account for 45% of recent blocks. Suggest enabling high-risk PIN quarantine."
              </div>
           </div>
        </div>
      </div>

      {/* Intelligence Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
         {/* Governance Log */}
         <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <h3 className="font-semibold text-slate-800 dark:text-slate-100 mb-6 flex items-center gap-2">
              <History className="h-4 w-4 text-slate-500" />
              Autonomous Governance Log
            </h3>
            <GovernanceLog logs={stats?.governance_logs} />
         </div>

         {/* Identity Pulse */}
         <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-semibold text-slate-800 dark:text-slate-100 flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-emerald-500" />
                Identity Security Pulse
              </h3>
              <span className="text-xs font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full dark:bg-emerald-900/20 dark:text-emerald-400">
                {stats?.identity_stats?.percentage?.toFixed(1) || "0.0"}% Threat Ratio
              </span>
            </div>
            <IdentityPulse stats={stats?.identity_stats} />
            <p className="mt-4 text-xs text-slate-500 leading-relaxed italic border-t pt-4">
              Real-time monitoring of Email risk patterns and Sybil clusters across the Vantix network.
            </p>
         </div>
      </div>
    </div>
  )
}

function StatCard({ 
  title, 
  value, 
  change, 
  trend, 
  icon: Icon, 
  color = "indigo" 
}: any) {
  const colors: any = {
    indigo: "bg-indigo-50 text-indigo-600 dark:bg-indigo-900/20 dark:text-indigo-400",
    red: "bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400",
    green: "bg-emerald-50 text-emerald-600 dark:bg-emerald-900/20 dark:text-emerald-400",
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm transition-all hover:shadow-md dark:border-slate-800 dark:bg-slate-900">
      <div className="flex items-center justify-between">
        <div className={cn("rounded-lg p-2.5", colors[color])}>
          <Icon className="h-5 w-5" />
        </div>
        <div className={cn(
          "flex items-center gap-0.5 text-sm font-medium",
          trend === "up" ? "text-emerald-600" : "text-indigo-600"
        )}>
          {change}
          <ArrowUpRight className={cn("h-4 w-4", trend === "down" && "rotate-90")} />
        </div>
      </div>
      <div className="mt-4">
        <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{title}</p>
        <p className="text-2xl font-bold text-slate-900 dark:text-white mt-1">{value}</p>
      </div>
    </div>
  )
}


