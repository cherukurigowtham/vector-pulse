"use client"

import { useState } from "react"
import { 
  Plus, 
  Trash2, 
  Play, 
  Pause, 
  ShieldCheck, 
  ShieldAlert, 
  Bell, 
  ChevronRight,
  GripVertical,
  Zap
} from "lucide-react"
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

const mockRules = [
  { id: "R-101", name: "High Risk High Value", threshold: 85, action: "CANCEL", status: "ACTIVE" },
  { id: "R-102", name: "Suspicious Velocity", threshold: 60, action: "VERIFY", status: "ACTIVE" },
  { id: "R-103", name: "New User Check", threshold: 45, action: "NOTIFY", status: "PAUSED" },
]

export default function RuleManager() {
  const [rules, setRules] = useState(mockRules)

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Zap className="h-6 w-6 text-amber-500" />
            Rule Manager
          </h1>
          <p className="text-slate-500">Define automated actions based on AI risk intelligence.</p>
        </div>
        <button className="flex h-10 items-center gap-2 rounded-xl bg-indigo-600 px-4 text-sm font-bold text-white shadow-lg shadow-indigo-200 transition-all hover:bg-indigo-700 hover:shadow-indigo-300 active:scale-95 dark:shadow-none">
          <Plus className="h-4 w-4" />
          Create New Rule
        </button>
      </div>

      {/* Rules List */}
      <div className="grid gap-4">
        {rules.map((rule) => (
          <div key={rule.id} className="group relative flex items-center gap-6 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition-all hover:border-indigo-200 hover:shadow-md dark:border-slate-800 dark:bg-slate-900">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-slate-50 text-slate-400 group-hover:bg-indigo-50 group-hover:text-indigo-500 transition-colors">
               <GripVertical className="h-5 w-5" />
            </div>
            
            <div className="flex-1 space-y-1">
               <div className="flex items-center gap-3">
                  <h3 className="font-bold text-slate-900 dark:text-white">{rule.name}</h3>
                  <span className={cn(
                    "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-black uppercase tracking-wider ring-1 ring-inset",
                    rule.status === "ACTIVE" 
                      ? "bg-emerald-50 text-emerald-700 ring-emerald-600/20" 
                      : "bg-slate-100 text-slate-600 ring-slate-400/20"
                  )}>
                    {rule.status}
                  </span>
               </div>
               <p className="text-xs text-slate-500">
                 IF RISK SCORE <span className="font-bold text-indigo-600">&gt; {rule.threshold}%</span> THEN <span className={cn(
                   "font-bold",
                   rule.action === "CANCEL" ? "text-red-600" : rule.action === "VERIFY" ? "text-amber-600" : "text-blue-600"
                 )}>{rule.action}</span>
               </p>
            </div>

            <div className="flex items-center gap-2">
               <button className="p-2 text-slate-400 hover:bg-slate-50 hover:text-slate-900 rounded-lg transition-colors">
                  {rule.status === "ACTIVE" ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
               </button>
               <button className="p-2 text-slate-400 hover:bg-red-50 hover:text-red-600 rounded-lg transition-colors">
                  <Trash2 className="h-4 w-4" />
               </button>
               <div className="h-4 w-[1px] bg-slate-200 mx-2" />
               <button className="p-2 text-slate-400 hover:bg-indigo-50 hover:text-indigo-600 rounded-lg transition-colors">
                  <ChevronRight className="h-5 w-5" />
               </button>
            </div>

            {/* Progress bar visualizing the threshold */}
            <div className="absolute bottom-0 left-0 h-1.5 w-full bg-slate-50/50 rounded-b-2xl overflow-hidden opacity-0 group-hover:opacity-100 transition-opacity">
               <div 
                className={cn(
                  "h-full rounded-r-full transition-all duration-700",
                  rule.action === "CANCEL" ? "bg-red-500" : rule.action === "VERIFY" ? "bg-amber-500" : "bg-indigo-500"
                )} 
                style={{ width: `${rule.threshold}%` }} 
               />
            </div>
          </div>
        ))}
      </div>

      {/* Action Definitions (Legend) */}
      <div className="grid gap-6 sm:grid-cols-3">
         <ActionInfo 
          icon={ShieldAlert} 
          title="CANCEL" 
          desc="Automatically marks the order as high-risk and prevents processing."
          color="red"
         />
         <ActionInfo 
          icon={ShieldCheck} 
          title="VERIFY" 
          desc="Triggers an Out-of-Band verification (Email/Phone) for the user."
          color="amber"
         />
         <ActionInfo 
          icon={Bell} 
          title="NOTIFY" 
          desc="Continues processing but sends an immediate alert to your team."
          color="indigo"
         />
      </div>
    </div>
  )
}

function ActionInfo({ icon: Icon, title, desc, color }: any) {
  const colors: any = {
    red: "text-red-500 bg-red-50 border-red-100",
    amber: "text-amber-500 bg-amber-50 border-amber-100",
    indigo: "text-indigo-500 bg-indigo-50 border-indigo-100",
  }
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50/30 p-5 dark:border-slate-800 dark:bg-slate-900/50">
       <div className={cn("inline-flex h-10 w-10 items-center justify-center rounded-xl border mb-4", colors[color])}>
          <Icon className="h-5 w-5" />
       </div>
       <h4 className="font-bold text-slate-900 dark:text-white text-sm">{title}</h4>
       <p className="mt-1 text-xs text-slate-500 leading-relaxed">{desc}</p>
    </div>
  )
}
