"use client"

import { useState } from "react"
import { Bell, Copy, Key, Mail, RefreshCw, Save, ShieldCheck, User } from "lucide-react"
import { cn } from "@/lib/cn"

export default function SettingsPage() {
  const [apiKey] = useState("vp_live_6f28...9a3d")
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(apiKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="max-w-4xl space-y-5">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
        <p className="text-sm text-slate-600">Manage account profile, credentials, and notification preferences.</p>
      </div>

      <section className="app-card p-5">
        <div className="mb-4 flex items-center gap-2 text-sm font-bold text-slate-900">
          <User className="h-4 w-4" />
          Organization Profile
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Merchant Name" defaultValue="Vantix" disabled />
          <Field label="Business Type" defaultValue="Enterprise Fintech" disabled />
          <div className="sm:col-span-2">
            <label className="mb-1 block text-xs font-semibold text-slate-600">Admin Email</label>
            <div className="relative">
              <Mail className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input className="app-input pl-10" defaultValue="governance@vantix.ai" disabled />
            </div>
          </div>
        </div>
      </section>

      <section className="app-card p-5">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-900">
            <Key className="h-4 w-4" />
            API Credentials
          </div>
          <button className="inline-flex items-center gap-1 text-xs font-semibold text-[var(--primary)] hover:text-blue-700">
            <RefreshCw className="h-3.5 w-3.5" />
            Rotate
          </button>
        </div>

        <div className="relative">
          <input className="app-input pr-10 font-mono text-sm" value={apiKey} readOnly />
          <button onClick={handleCopy} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-slate-500 hover:bg-slate-100">
            {copied ? <ShieldCheck className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
          </button>
        </div>
      </section>

      <section className="app-card p-5">
        <div className="mb-4 flex items-center gap-2 text-sm font-bold text-slate-900">
          <Bell className="h-4 w-4" />
          Notifications
        </div>

        <div className="divide-y divide-slate-200">
          <ToggleItem title="Webhook events" desc="Send live risk events to configured endpoints." defaultChecked />
          <ToggleItem title="Daily digest" desc="Email summary of major prevention trends." defaultChecked />
        </div>
      </section>

      <div className="flex justify-end">
        <button className="inline-flex items-center gap-2 rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700">
          <Save className="h-4 w-4" />
          Save changes
        </button>
      </div>
    </div>
  )
}

function Field({ label, defaultValue, disabled = false }: { label: string; defaultValue: string; disabled?: boolean }) {
  return (
    <div>
      <label className="mb-1 block text-xs font-semibold text-slate-600">{label}</label>
      <input className={cn("app-input", disabled && "cursor-not-allowed bg-slate-50 text-slate-500")} defaultValue={defaultValue} disabled={disabled} />
    </div>
  )
}

function ToggleItem({ title, desc, defaultChecked = false }: { title: string; desc: string; defaultChecked?: boolean }) {
  const [checked, setChecked] = useState(defaultChecked)

  return (
    <div className="flex items-center justify-between py-4">
      <div>
        <p className="text-sm font-semibold text-slate-900">{title}</p>
        <p className="text-sm text-slate-600">{desc}</p>
      </div>
      <button
        onClick={() => setChecked((prev) => !prev)}
        className={cn("relative inline-flex h-6 w-11 items-center rounded-full", checked ? "bg-blue-600" : "bg-slate-300")}
      >
        <span className={cn("inline-block h-4 w-4 transform rounded-full bg-white transition", checked ? "translate-x-6" : "translate-x-1")} />
      </button>
    </div>
  )
}
