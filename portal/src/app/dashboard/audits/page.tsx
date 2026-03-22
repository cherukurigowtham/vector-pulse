"use client"

import { useEffect, useState } from "react"
import { Eye, Filter, Search, ShieldAlert, ShieldCheck } from "lucide-react"
import { apiFetch } from "@/lib/api"
import { cn } from "@/lib/cn"

type AuditItem = {
  id?: string
  uid?: string
  user?: string
  time?: string
  amt?: string | number
  score?: number
  status?: string
}

export default function AuditFeed() {
  const [searchTerm, setSearchTerm] = useState("")
  const [audits, setAudits] = useState<AuditItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch("/merchant/reporting/summary")
        setAudits((data.recent_activity || []) as AuditItem[])
      } catch {
        // keep empty
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  const filtered = audits.filter((audit) => {
    if (!searchTerm.trim()) return true
    return `${audit.user || ""} ${audit.id || ""}`.toLowerCase().includes(searchTerm.toLowerCase())
  })

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Audit Feed</h1>
          <p className="text-sm text-slate-600">Track every risk decision and transaction outcome.</p>
        </div>

        <div className="flex flex-col gap-3 sm:flex-row">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search user or ID"
              className="app-input w-full pl-10 sm:w-72"
            />
          </div>
          <button className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-slate-300 bg-white px-4 text-sm font-semibold text-slate-700 hover:border-slate-400">
            <Filter className="h-4 w-4" />
            Filter
          </button>
        </div>
      </div>

      <div className="app-card overflow-x-auto">
        <table className="w-full min-w-[760px] border-collapse text-left">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">User</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-sm text-slate-500">Loading audit data...</td>
              </tr>
            ) : filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-12 text-center text-sm text-slate-500">No records found.</td>
              </tr>
            ) : (
              filtered.map((audit) => {
                const score = audit.score || 0
                const blocked = (audit.status || "").toUpperCase() === "BLOCK"
                return (
                  <tr key={audit.id || audit.uid} className="hover:bg-slate-50">
                    <td className="px-4 py-3 font-mono text-xs text-slate-600">{audit.id || audit.uid || "-"}</td>
                    <td className="px-4 py-3">
                      <p className="text-sm font-semibold text-slate-900">{audit.user || "Unknown"}</p>
                      <p className="text-xs text-slate-500">{audit.time || "--:--"}</p>
                    </td>
                    <td className="px-4 py-3 text-sm text-slate-700">{audit.amt || "-"}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <div className="h-1.5 w-24 rounded-full bg-slate-100">
                          <div className={cn("h-full rounded-full", score > 70 ? "bg-red-500" : score > 30 ? "bg-amber-500" : "bg-emerald-500")} style={{ width: `${score}%` }} />
                        </div>
                        <span className="text-xs text-slate-500">{score}%</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={cn("inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold", blocked ? "bg-red-50 text-red-700" : "bg-emerald-50 text-emerald-700")}>
                        {blocked ? <ShieldAlert className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
                        {audit.status || "ALLOW"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:border-slate-300">
                        <Eye className="h-4 w-4" />
                      </button>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
