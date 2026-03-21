import { useEffect, useState } from "react"
import { AlertCircle, Info, Settings, ShieldCheck } from "lucide-react"
import { cn } from "@/lib/cn"

export type GovernanceLogItem = {
  time: number | string
  event: string
  status: "Success" | "Audited" | "Nominal" | "Warning" | "Error"
}

function TimeDisplay({ timestamp }: { timestamp: number | string }) {
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  if (!mounted) return <span className="w-16 shrink-0 opacity-0" />

  let displayTime = String(timestamp)
  if (typeof timestamp === "number") {
    displayTime = new Date(timestamp * 1000).toLocaleTimeString([], { 
      hour: "2-digit", 
      minute: "2-digit",
      hour12: false 
    })
  }

  return (
    <span className="w-16 shrink-0 font-mono text-xs font-medium tracking-tight text-zinc-400">
      {displayTime}
    </span>
  )
}

export function GovernanceLog({ logs }: { logs?: GovernanceLogItem[] }) {
  if (!logs || logs.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-zinc-200 bg-zinc-50/50 p-8 text-center text-[13px] font-medium text-zinc-500">
        Waiting for incoming governance vectors...
      </div>
    )
  }

  const iconByStatus: Record<string, React.ReactNode> = {
    Success: <ShieldCheck className="h-4 w-4 text-emerald-600" />,
    Audited: <Settings className="h-4 w-4 text-zinc-600" />,
    Nominal: <Info className="h-4 w-4 text-blue-600" />,
    Warning: <AlertCircle className="h-4 w-4 text-amber-600" />,
    Error: <AlertCircle className="h-4 w-4 text-red-600" />,
  }

  const colorByStatus: Record<string, string> = {
    Success: "bg-emerald-50 text-emerald-700",
    Audited: "bg-zinc-100 text-zinc-700",
    Nominal: "bg-blue-50 text-blue-700",
    Warning: "bg-amber-50 text-amber-700",
    Error: "bg-red-50 text-red-700",
  }

  return (
    <div className="space-y-3">
      {logs.map((log, idx) => (
        <div key={`${typeof log.time === 'number' ? log.time : log.time.toString()}-${idx}`} className="flex items-center gap-4 py-2 border-b border-zinc-100 last:border-0 group animate-fade-in-up">
          <TimeDisplay timestamp={log.time} />
          <p className="flex-1 text-[13px] font-medium text-zinc-700 tracking-tight group-hover:text-zinc-900 transition-colors">{log.event}</p>
          <span className={cn("inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[11px] font-semibold tracking-wide", colorByStatus[log.status])}>
            {iconByStatus[log.status]}
            {log.status}
          </span>
        </div>
      ))}
    </div>
  )
}
