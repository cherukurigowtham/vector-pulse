"use client"

import { useState } from "react"
import { 
  User, 
  Building2, 
  Key, 
  Mail, 
  Globe, 
  ShieldCheck, 
  Copy, 
  RefreshCw,
  Save,
  BellRing
} from "lucide-react"
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export default function SettingsPage() {
  const [apiKey, setApiKey] = useState("vp_live_6f28...9a3d")
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="max-w-4xl space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <SettingsIcon className="h-6 w-6 text-slate-500" />
          Merchant Settings
        </h1>
        <p className="text-slate-500">Manage your profile, API keys, and notification preferences.</p>
      </div>

      <div className="grid gap-8">
        {/* Profile Section */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
           <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-6">
              <Building2 className="h-4 w-4 text-indigo-500" />
              Organization Profile
           </h3>
           <div className="grid gap-6 sm:grid-cols-2">
              <div className="space-y-1.5">
                 <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Company Name</label>
                 <input 
                  type="text" 
                  defaultValue="Vantix Technologies"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-4 py-2.5 text-sm focus:border-indigo-500 focus:outline-none dark:border-slate-800 dark:bg-slate-800/50 dark:text-white"
                 />
              </div>
              <div className="space-y-1.5">
                 <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Business Category</label>
                 <select className="w-full rounded-xl border border-slate-200 bg-slate-50/50 px-4 py-2.5 text-sm focus:border-indigo-500 focus:outline-none dark:border-slate-800 dark:bg-slate-800/50 dark:text-white">
                    <option>E-commerce / Retail</option>
                    <option>Fintech / Payments</option>
                    <option>SaaS / Digital Services</option>
                 </select>
              </div>
              <div className="space-y-1.5 sm:col-span-2">
                 <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">Contact Email</label>
                 <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
                    <input 
                      type="email" 
                      defaultValue="ceo@vantix.com"
                      className="w-full rounded-xl border border-slate-200 bg-slate-50/50 pl-10 pr-4 py-2.5 text-sm dark:border-slate-800 dark:bg-slate-800/50 dark:text-white"
                    />
                 </div>
              </div>
           </div>
        </section>

        {/* API Key Section */}
        <section className="rounded-2xl border border-indigo-100 bg-indigo-50/20 p-6 shadow-sm dark:border-indigo-900/30 dark:bg-indigo-900/10">
           <div className="flex items-center justify-between mb-6">
              <h3 className="text-sm font-bold text-indigo-900 dark:text-indigo-400 flex items-center gap-2">
                 <Key className="h-4 w-4" />
                 API Authentication
              </h3>
              <button className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1">
                 <RefreshCw className="h-3 w-3" />
                 Rotate Key
              </button>
           </div>
           
           <div className="space-y-4">
              <div className="flex gap-2">
                 <div className="flex-1 rounded-xl border border-indigo-200 bg-white px-4 py-2.5 font-mono text-xs text-slate-600 dark:border-indigo-950 dark:bg-slate-900 dark:text-slate-400 flex items-center justify-between shadow-sm italic">
                    {apiKey}
                    <button onClick={handleCopy} className="text-indigo-500 hover:text-indigo-600 p-1 rounded-md hover:bg-indigo-50 transition-colors">
                       {copied ? <ShieldCheck className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                    </button>
                 </div>
              </div>
              <p className="text-[11px] text-indigo-700/60 dark:text-indigo-400/50 leading-relaxed italic">
                 "This key grants full access to the Risk Scoping engine. Never share it in client-side code."
              </p>
           </div>
        </section>

        {/* Preferences Section */}
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
           <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-6">
              <BellRing className="h-4 w-4 text-amber-500" />
              Notifications & Security
           </h3>
           <div className="space-y-4">
              <ToggleRow title="Critical Alert Webhook" desc="Receive POST requests for high-confidence fraud blocks." active={true} />
              <ToggleRow title="Weekly CEO Report" desc="Email summary of prevented RTO and network trends." active={true} />
              <ToggleRow title="Two-Factor Auth" desc="Enforce 2FA for all team members." active={false} />
           </div>
        </section>

        <div className="flex justify-end gap-3 pt-4">
           <button className="px-6 py-2.5 rounded-xl border border-slate-200 text-sm font-bold text-slate-600 hover:bg-slate-50 transition-all dark:border-slate-800 dark:text-slate-400">
              Discard
           </button>
           <button className="px-6 py-2.5 rounded-xl bg-indigo-600 text-sm font-bold text-white shadow-lg shadow-indigo-200 hover:bg-indigo-700 transition-all hover:scale-[1.02] dark:shadow-none flex items-center gap-2">
              <Save className="h-4 w-4" />
              Save Changes
           </button>
        </div>
      </div>
    </div>
  )
}

function ToggleRow({ title, desc, active }: any) {
  return (
    <div className="flex items-center justify-between py-2">
       <div className="space-y-0.5">
          <p className="text-sm font-bold text-slate-900 dark:text-white">{title}</p>
          <p className="text-xs text-slate-500">{desc}</p>
       </div>
       <button className={cn(
         "relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
         active ? "bg-indigo-600" : "bg-slate-200 dark:bg-slate-800"
       )}>
          <span className={cn(
            "pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out",
            active ? "translate-x-5" : "translate-x-0"
          )} />
       </button>
    </div>
  )
}

function SettingsIcon(props: any) {
   return (
      <svg
        {...props}
        xmlns="http://www.w3.org/2000/svg"
        width="24"
        height="24"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
   )
}
