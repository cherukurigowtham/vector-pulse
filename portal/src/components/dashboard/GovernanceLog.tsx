"use client"

import { History, ShieldAlert, Settings, ArrowRight } from "lucide-react"

export function GovernanceLog({ logs }: { logs: any[] }) {
  if (!logs || logs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-slate-400 italic text-sm border border-dashed rounded-xl">
        No recent governance events.
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {logs.map((log, idx) => (
        <div key={idx} className="flex gap-4 p-3 rounded-xl hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors border border-transparent hover:border-slate-100 dark:hover:border-slate-800">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-indigo-50 dark:bg-indigo-950/30 text-indigo-600 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-900/50">
            <Settings className="h-4 w-4" />
          </div>
          <div className="flex-1 space-y-1">
            <div className="flex items-center justify-between">
              <p className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">{log.action}</p>
              <span className="text-[10px] text-slate-400 font-mono">
                {new Date(log.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </span>
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400 line-clamp-1 italic">
              {log.actor} modified risk parameters
            </p>
          </div>
        </div>
      ))}
    </div>
  )
}
