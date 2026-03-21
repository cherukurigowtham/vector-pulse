"use client"

import Link from "next/link"
import { ArrowRight, CheckCircle2, ShieldCheck, Activity, Sparkles, Code, Terminal, Cpu } from "lucide-react"
import Navigation from "@/components/Navigation"
import Footer from "@/components/Footer"
import { cn } from "@/lib/cn"

const features = [
  {
    title: "Real-time risk decisions",
    desc: "Evaluate each transaction with consistent low-latency scoring and policy enforcement.",
    icon: Activity,
  },
  {
    title: "Audit-ready governance",
    desc: "Capture every decision event with timestamps and actor context for compliance reviews.",
    icon: ShieldCheck,
  },
  {
    title: "Simple team operations",
    desc: "Give product, risk, and ops teams one clean dashboard for daily decision workflows.",
    icon: Sparkles,
  },
]

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)]">
      <Navigation />

      <main className="container pb-40 lg:pb-48 pt-36">
        <section className="flex flex-col lg:flex-row gap-16 lg:items-center">
          <div className="flex-1 animate-fade-in-up mt-12">

            <h1 className="max-w-2xl text-[56px] font-bold leading-[1.05] tracking-tight text-zinc-900 sm:text-[72px] lg:text-[84px] mb-8">
              Precision Risk <br/>
              Intelligence.
            </h1>
            <p className="max-w-xl text-lg lg:text-xl text-zinc-500 font-normal leading-relaxed">
              Built for Scale. Vantix provides deterministic decisioning and cryptographic audit trails for high-volume engineering teams.
            </p>
            <div className="mt-10 flex flex-col gap-4 sm:flex-row">
              <Link href="/dashboard" className="inline-flex items-center justify-center gap-2 rounded-xl bg-zinc-900 px-6 py-3.5 text-sm font-medium !text-white hover:bg-zinc-800 transition-colors shadow-sm">
                Open dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
              <a href="#docs" className="inline-flex items-center justify-center rounded-xl border border-zinc-200 bg-white px-6 py-3.5 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors shadow-sm">
                Read documentation
              </a>
            </div>

            <div className="mt-10 flex items-center gap-6 text-sm font-medium text-zinc-500">
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="h-4 w-4 text-zinc-400" />
                Go backend compatible
              </div>
              <div className="flex items-center gap-2.5">
                <CheckCircle2 className="h-4 w-4 text-zinc-400" />
                Postgres-ready data model
              </div>
            </div>
          </div>

          <div className="flex-1 w-full relative">
            {/* Soft background glow */}
            <div className="absolute -inset-4 bg-zinc-200/50 rounded-[32px] blur-2xl -z-10" />
            
            <div className="app-card p-8 bg-white/60 backdrop-blur-xl border-zinc-200/60 shadow-xl shadow-zinc-200/40">
              <div className="flex items-center justify-between mb-8">
                <p className="kicker text-zinc-500">Live Snapshot</p>
                <div className="flex items-center gap-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="text-xs font-medium text-zinc-500">Systems Operational</span>
                </div>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <MetricCard title="Risk Checks (24h)" value="84,320" trend="+12%" />
                <MetricCard title="Blocked Events" value="312" trend="-4%" neutral />
                <MetricCard title="Median Latency" value="14ms" trend="-2ms" />
                <MetricCard title="Platform Uptime" value="99.99%" />
              </div>
            </div>
          </div>
        </section>

        <section id="product" className="mt-40">
          <div className="mb-12">
            <h2 className="text-3xl font-bold tracking-tight text-zinc-900">Platform Capabilities</h2>
            <p className="mt-4 text-zinc-500">Engineered for reliability and instant insight.</p>
          </div>
          <div className="grid gap-6 md:grid-cols-3">
            {features.map((feature) => (
              <article key={feature.title} className="app-card p-8 group">
                <div className="mb-6 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-zinc-100 text-zinc-700 group-hover:bg-zinc-900 group-hover:text-white transition-colors duration-300">
                  <feature.icon className="h-5 w-5" />
                </div>
                <h3 className="text-lg font-semibold text-zinc-900">{feature.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-zinc-500">{feature.desc}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="docs" className="mt-40 scroll-mt-28">
          <div className="mb-12">
            <h2 className="text-3xl font-bold tracking-tight text-zinc-900">Integration Guide</h2>
            <p className="mt-4 text-zinc-500">Everything you need to connect your application to Vantix APIs and run real-time risk checks in production.</p>
          </div>
          
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="app-card p-6 flex flex-col gap-4">
              <div className="flex items-center gap-2 text-sm font-bold text-zinc-900">
                <Terminal className="h-4 w-4" />
                1. Installation
              </div>
              <p className="text-sm text-zinc-500">Install the SDK package in your Next.js or Node.js backend service.</p>
              <pre className="overflow-x-auto rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-sm font-semibold text-zinc-800">
                <code>npm install @vector-pulse/node</code>
              </pre>

              <div className="mt-4 flex items-center gap-2 text-sm font-bold text-zinc-900">
                <Cpu className="h-4 w-4" />
                2. Live Scoring Endpoint
              </div>
              <p className="text-sm text-zinc-500">Send context directly to the Vantix pulse API to receive deterministic decisions.</p>
              <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4">
                <p className="font-mono text-xs font-semibold text-zinc-900">POST /api/v1/risk/scan</p>
                <p className="mt-2 text-xs font-semibold text-zinc-500">Header: X-API-Key: your_live_key</p>
              </div>
            </div>

            <div className="app-card p-6 flex flex-col gap-4">
              <div className="flex items-center gap-2 text-sm font-bold text-zinc-900">
                <Code className="h-4 w-4" />
                3. Code Implementation
              </div>
              <pre className="flex-1 overflow-x-auto rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-xs leading-[1.6] text-zinc-800">
                <code>{`const { VectorPulseClient } = require('@vector-pulse/node')

// Initialize with your private live key
const client = new VectorPulseClient('vp_live_key...')

async function processOrder(order) {
  // Synchronous risk computation
  const result = await client.scanOrder({
    uid: order.user_id,
    amount: order.total_amount,
    address: order.shipping_address,
    zip: order.postal_code,
  })

  // Act strictly on the pulse response
  if (result.decision === 'BLOCK') {
    return { status: 'FORCE_PREPAID_OR_DENY' }
  }
}`}</code>
              </pre>
            </div>
          </div>
        </section>

        <section id="pricing" className="mt-40 scroll-mt-28">
          <div className="text-center mb-16 max-w-2xl mx-auto">
            <h2 className="text-4xl font-bold tracking-tight text-zinc-900">Simple, transparent pricing.</h2>
            <p className="mt-4 text-lg text-zinc-500">Start for free, scale as you grow. All tiers include a 14-day free trial.</p>
          </div>
          
          <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4 mt-12 max-w-6xl mx-auto">
            {[
              { 
                name: "Basic", 
                price: "₹499", 
                desc: "Essential protection for early-stage developers.",
                features: ["Up to 1k scans/mo", "Basic risk rules", "7-day audit history", "14 days free trial"],
                cta: "Start trial",
                highlight: false
              },
              { 
                name: "Growth", 
                price: "₹1,999", 
                desc: "High-performance guardrails for active products.",
                features: ["Up to 25k scans/mo", "Custom risk rules", "30-day audit history", "14 days free trial"],
                cta: "Start trial",
                highlight: false
              },
              { 
                name: "Professional", 
                price: "₹4,999", 
                desc: "Advanced intelligence for scaling risk teams.",
                features: ["Up to 100k scans/mo", "AI forensics", "90-day audit history", "14 days free trial"],
                cta: "Start trial",
                highlight: true
              },
              { 
                name: "Enterprise", 
                price: "Custom", 
                desc: "Institutional governance for high-volume giants.",
                features: ["Unlimited scans/mo", "Dedicated models", "Full audit archive", "14 days free trial"],
                cta: "Contact sales",
                highlight: false
              }
            ].map((plan) => (
              <article key={plan.name} className={cn(
                "app-card p-8 flex flex-col",
                plan.highlight ? "ring-2 ring-zinc-900 ring-offset-4 ring-offset-[var(--bg)] z-10" : ""
              )}>
                <div className="mb-8 border-b border-zinc-100 pb-8">
                  <h3 className="text-lg font-semibold text-zinc-900 mb-2">{plan.name}</h3>
                  <div className="flex items-baseline gap-1 mb-4">
                    <span className="text-4xl font-bold tracking-tight text-zinc-900">{plan.price}</span>
                    {plan.price !== "Custom" && <span className="text-sm font-medium text-zinc-500">/mo</span>}
                  </div>
                  <p className="text-sm text-zinc-500 font-normal leading-relaxed">{plan.desc}</p>
                </div>
                
                <ul className="space-y-4 mb-10 flex-1">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-3 text-sm font-medium text-zinc-600">
                      <CheckCircle2 className="h-4 w-4 text-zinc-900 shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                
                {plan.name === "Enterprise" ? (
                  <button className={cn(
                    "w-full py-3 rounded-xl text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:ring-offset-2",
                    plan.highlight 
                      ? "bg-zinc-900 !text-white hover:bg-zinc-800 shadow-md" 
                      : "bg-white text-zinc-900 border border-zinc-200 hover:bg-zinc-50 shadow-sm"
                  )}>
                    {plan.cta}
                  </button>
                ) : (
                  <Link href={`/checkout?plan=${plan.name.toLowerCase()}`} className={cn(
                    "block text-center w-full py-3 rounded-xl text-sm font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-zinc-900 focus:ring-offset-2",
                    plan.highlight 
                      ? "bg-zinc-900 !text-white hover:bg-zinc-800 shadow-md" 
                      : "bg-white text-zinc-900 border border-zinc-200 hover:bg-zinc-50 shadow-sm"
                  )}>
                    {plan.cta}
                  </Link>
                )}
              </article>
            ))}
          </div>
        </section>
      </main>
      <Footer />
    </div>
  )
}

function MetricCard({ title, value, trend, neutral }: { title: string; value: string; trend?: string; neutral?: boolean }) {
  return (
    <div className="rounded-xl border border-zinc-100 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-2">
        <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider">{title}</p>
        {trend && (
          <span className={cn(
            "text-[10px] font-bold px-1.5 py-0.5 rounded-full",
            neutral ? "bg-zinc-100 text-zinc-600" : "bg-emerald-50 text-emerald-600"
          )}>
            {trend}
          </span>
        )}
      </div>
      <p className="metric-value text-3xl font-bold text-zinc-900 tracking-tight">{value}</p>
    </div>
  )
}
