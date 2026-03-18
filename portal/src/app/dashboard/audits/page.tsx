"use client"

import { useState, useEffect } from "react"
import { apiFetch } from "@/lib/api"
import { 
  Search, 
  Filter, 
  ChevronRight, 
  ShieldCheck, 
  ShieldAlert, 
  ExternalLink,
  Eye
} from "lucide-react"
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export default function AuditFeed() {
  const [searchTerm, setSearchTerm] = useState("")
  const [audits, setAudits] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const data = await apiFetch("/merchant/reporting/summary")
        // In the real app, this would be a specialized /audits endpoint
        // For now we use the recent_activity from summary
        setAudits(data.recent_activity || [])
      } catch (err) {
        console.error("Audit load failed:", err)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Audit Feed</h1>
          <p className="text-slate-500">Deep-dive into every risk adjudication in real-time.</p>
        </div>
        <div className="flex gap-3">
           <div className="relative">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input 
                type="text" 
                placeholder="Search by UID, Email..." 
                className="h-10 w-64 rounded-lg border border-slate-200 bg-white pl-10 pr-4 text-sm focus:border-indigo-500 focus:outline-none dark:border-slate-800 dark:bg-slate-900"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
           </div>
           <button className="flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-medium text-slate-600 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
              <Filter className="h-4 w-4" />
              Filters
           </button>
        </div>
      </div>

      {/* Table Section */}
      <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden dark:border-slate-800 dark:bg-slate-900">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b bg-slate-50/50 text-xs font-semibold uppercase tracking-wider text-slate-500 dark:bg-slate-800/50">
              <th className="px-6 py-4">Transaction ID</th>
              <th className="px-6 py-4">User Identity</th>
              <th className="px-6 py-4">Amount</th>
              <th className="px-6 py-4">Risk Score</th>
              <th className="px-6 py-4">Decision</th>
              <th className="px-6 py-4">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            {audits.length === 0 && !loading && (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-slate-400 italic">No recent audits found.</td>
              </tr>
            )}
            {audits.map((audit: any) => (
              <tr key={audit.id || audit.uid} className="group hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                <td className="px-6 py-4">
                  <span className="font-mono text-sm text-slate-400">{audit.id}</span>
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-col">
                    <span className="text-sm font-medium text-slate-900 dark:text-white">{audit.user}</span>
                    <span className="text-xs text-slate-400">{audit.time}</span>
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-slate-600 dark:text-slate-300">
                  {audit.amt}
                </td>
                <td className="px-6 py-4">
                   <div className="flex items-center gap-2">
                      <div className="h-1.5 w-16 rounded-full bg-slate-100 dark:bg-slate-800">
                        <div 
                          className={cn(
                            "h-full rounded-full",
                            audit.score > 70 ? "bg-red-500" : audit.score > 30 ? "bg-amber-500" : "bg-emerald-500"
                          )} 
                          style={{ width: `${audit.score}%` }}
                        />
                      </div>
                      <span className="text-xs font-bold text-slate-500">{audit.score}%</span>
                   </div>
                </td>
                <td className="px-6 py-4">
                  <span className={cn(
                    "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-bold ring-1 ring-inset",
                    audit.status === "BLOCK" 
                      ? "bg-red-50 text-red-700 ring-red-600/20 dark:bg-red-900/20 dark:text-red-400" 
                      : "bg-emerald-50 text-emerald-700 ring-emerald-600/20 dark:bg-emerald-900/20 dark:text-emerald-400"
                  )}>
                    {audit.status === "BLOCK" ? <ShieldAlert className="h-3 w-3" /> : <ShieldCheck className="h-3 w-3" />}
                    {audit.status}
                  </span>
                </td>
                <td className="px-6 py-4 text-right">
                  <button className="flex items-center gap-1.5 text-sm font-medium text-indigo-600 hover:text-indigo-700 dark:text-indigo-400">
                    <Eye className="h-4 w-4" />
                    Details
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
