"use client"

import { useEffect, useState } from "react"
import { AlertCircle, Info, Settings, ShieldCheck, Bot, X, Loader2 } from "lucide-react"
import { cn } from "@/lib/cn"
import { apiFetch } from "@/lib/api"

export type GovernanceLogItem = {
  id?: string
  time: number | string
  event: string
  status: "Success" | "Audited" | "Nominal" | "Warning" | "Error"
  riskId?: string
}

function CopilotModal({ riskId, onClose }: { riskId: string, onClose: () => void }) {
  const [report, setReport] = useState<string | null>(null);
  
  useEffect(() => {
    apiFetch(`/risk/forensics/${riskId}`)
      .then(res => setReport(res.forensics_report))
      .catch(err => {
          console.error("Forensics Engine Error:", err);
          setReport(`> **Critical Neural Outage:** Vantix Engine requires an active \`GEMINI_API_KEY\` to synthesize structural forensics.\n\nBackend Traced Error: ${err.message}`);
      });
  }, [riskId]);

  return (
    <div className="fixed inset-0 z-50 bg-zinc-900/40 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in zoom-in-95 duration-200">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl overflow-hidden flex flex-col border border-zinc-200">
        <div className="p-4 border-b border-zinc-100 flex items-center justify-between bg-zinc-50/80">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-full bg-indigo-100 flex items-center justify-center border border-indigo-200">
              <Bot className="h-4 w-4 text-indigo-600" />
            </div>
            <div>
              <h3 className="text-sm font-bold tracking-tight text-zinc-900">Gemini Forensics Copilot</h3>
              <p className="text-[10px] uppercase font-bold tracking-widest text-zinc-500">Autonomous Threat Analysis</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-full hover:bg-zinc-200 text-zinc-400 hover:text-zinc-600 transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-6 max-h-[60vh] overflow-y-auto whitespace-pre-wrap text-sm text-zinc-700 font-medium leading-relaxed tracking-tight">
          {report || (
            <div className="flex flex-col items-center justify-center py-12 text-indigo-600 opacity-80">
              <Loader2 className="h-8 w-8 animate-spin mb-4" />
              <p className="text-sm font-semibold tracking-wide">Synthesizing deep neural analysis via Google Gemini Flash...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
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
  const [activeRiskId, setActiveRiskId] = useState<string | null>(null);

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
    Success: "bg-emerald-50 text-emerald-700 border border-emerald-100",
    Audited: "bg-zinc-100 text-zinc-700 border border-zinc-200",
    Nominal: "bg-blue-50 text-blue-700 border border-blue-100",
    Warning: "bg-amber-50 text-amber-700 border border-amber-100",
    Error: "bg-red-50 text-red-700 border border-red-100",
  }

  return (
    <div className="space-y-1">
      {logs.map((log, idx) => (
        <div key={log.id || `${log.time}-${idx}`} className="flex flex-col py-2.5 border-b border-zinc-100 last:border-0 group animate-in fade-in-up duration-300">
          <div className="flex items-center gap-4">
            <TimeDisplay timestamp={log.time} />
            <p className="flex-1 text-[13px] font-medium text-zinc-700 tracking-tight group-hover:text-zinc-900 transition-colors">
              {log.event}
            </p>
            <span className={cn("inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-[10px] uppercase font-bold tracking-widest", colorByStatus[log.status])}>
              {iconByStatus[log.status]}
              {log.status === "Error" ? "BLOCKED" : log.status}
            </span>
          </div>
          
          {log.riskId && log.status === "Error" && (
            <div className="ml-[5.1rem] mt-2 block">
              <button 
                onClick={() => setActiveRiskId(log.riskId!)} 
                className="inline-flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-indigo-700 bg-indigo-50 border border-indigo-100 hover:bg-indigo-100 px-2.5 py-1 rounded transition-colors shadow-sm"
              >
                <Bot className="h-3.5 w-3.5" /> AI Forensics
              </button>
            </div>
          )}
        </div>
      ))}

      {activeRiskId && <CopilotModal riskId={activeRiskId} onClose={() => setActiveRiskId(null)} />}
    </div>
  )
}
