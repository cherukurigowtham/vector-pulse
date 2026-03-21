"use client"

import { useState } from "react"
import { Bell, ChevronRight, Pause, Play, Plus, ShieldAlert, ShieldCheck, Trash2 } from "lucide-react"
import { cn } from "@/lib/cn"
import type { LucideIcon } from "lucide-react"

type RuleAction = "CANCEL" | "VERIFY" | "NOTIFY"
type RuleStatus = "ACTIVE" | "PAUSED"

type RuleItem = {
  id: string
  name: string
  threshold: number
  action: RuleAction
  status: RuleStatus
}

const mockRules: RuleItem[] = [
  { id: "R-101", name: "High value protection", threshold: 85, action: "CANCEL", status: "ACTIVE" },
  { id: "R-102", name: "Velocity threshold", threshold: 60, action: "VERIFY", status: "ACTIVE" },
  { id: "R-103", name: "New user safeguard", threshold: 45, action: "NOTIFY", status: "PAUSED" },
]

export default function RuleManager() {
  const [rules] = useState(mockRules)

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Risk Rules</h1>
          <p className="text-sm text-slate-600">Configure automated actions based on risk score thresholds.</p>
        </div>

        <button className="inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
          <Plus className="h-4 w-4" />
          New rule
        </button>
      </div>

      <div className="space-y-3">
        {rules.map((rule) => (
          <article key={rule.id} className="app-card p-4">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center">
              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h2 className="text-base font-bold text-slate-900">{rule.name}</h2>
                  <span className={cn("rounded-full px-2.5 py-1 text-xs font-semibold", rule.status === "ACTIVE" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-700")}>
                    {rule.status}
                  </span>
                </div>

                <p className="mt-1 text-sm text-slate-600">
                  Trigger when score &gt; <span className="font-semibold text-slate-900">{rule.threshold}%</span> and apply action <span className="font-semibold text-slate-900">{rule.action}</span>.
                </p>

                <div className="mt-3 h-1.5 w-full rounded-full bg-slate-100">
                  <div className={cn("h-full rounded-full", rule.action === "CANCEL" ? "bg-red-500" : rule.action === "VERIFY" ? "bg-amber-500" : "bg-blue-500")} style={{ width: `${rule.threshold}%` }} />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-600 hover:border-slate-400">
                  {rule.status === "ACTIVE" ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                </button>
                <button className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-600 hover:border-slate-400">
                  <Trash2 className="h-4 w-4" />
                </button>
                <button className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-300 bg-white text-slate-600 hover:border-slate-400">
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          </article>
        ))}
      </div>

      <section className="grid gap-3 sm:grid-cols-3">
        <ActionInfo icon={ShieldAlert} title="CANCEL" desc="Immediately stop and block the transaction." color="red" />
        <ActionInfo icon={ShieldCheck} title="VERIFY" desc="Require additional verification before approval." color="amber" />
        <ActionInfo icon={Bell} title="NOTIFY" desc="Allow but notify risk operations for follow-up." color="blue" />
      </section>
    </div>
  )
}

function ActionInfo({ icon: Icon, title, desc, color }: { icon: LucideIcon; title: RuleAction; desc: string; color: "red" | "amber" | "blue" }) {
  const colorMap: Record<string, string> = {
    red: "bg-red-50 text-red-700",
    amber: "bg-amber-50 text-amber-700",
    blue: "bg-blue-50 text-blue-700",
  }

  return (
    <article className="app-card p-4">
      <div className={cn("inline-flex rounded-xl p-2.5", colorMap[color])}>
        <Icon className="h-4 w-4" />
      </div>
      <h3 className="mt-3 text-sm font-bold text-slate-900">{title}</h3>
      <p className="mt-1 text-sm text-slate-600">{desc}</p>
    </article>
  )
}
