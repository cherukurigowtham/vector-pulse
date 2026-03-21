import { BookOpen, Code, Cpu, Terminal } from "lucide-react"

export default function DocsPage() {
  return (
    <div className="space-y-8">
      <header className="app-card p-6">
        <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600">
          <BookOpen className="h-5 w-5" />
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Integration Guide</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-600">
          Everything you need to connect your application to Vantix APIs and run real-time risk checks in production.
        </p>
      </header>

      <section id="installation" className="app-card p-6">
        <div className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900">
          <Terminal className="h-4 w-4" />
          1. Installation
        </div>
        <p className="text-sm text-slate-600">Install the SDK package in your Next.js or Node.js backend service.</p>
        <pre className="mt-4 overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm font-semibold text-slate-800">
          <code>npm install @vector-pulse/node</code>
        </pre>
      </section>

      <section id="sdk-usage" className="app-card p-6">
        <div className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900">
          <Code className="h-4 w-4" />
          2. SDK Usage
        </div>
        <pre className="overflow-x-auto rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm leading-relaxed text-slate-800">
          <code>{`const { VectorPulseClient } = require('@vector-pulse/node')
const client = new VectorPulseClient('vp_live_key')

async function processOrder(order) {
  const result = await client.scanOrder({
    uid: order.user_id,
    amt: order.total_amount,
    addr: order.shipping_address,
    pin: order.postal_code,
  })

  if (result.decision === 'BLOCK') {
    return { status: 'FORCE_PREPAID' }
  }
}`}</code>
        </pre>
      </section>

      <section id="api-reference" className="app-card p-6">
        <div className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-900">
          <Cpu className="h-4 w-4" />
          3. API Reference
        </div>
        <p className="text-sm text-slate-600">Primary endpoint for live scoring:</p>
        <div className="mt-3 rounded-xl border border-slate-200 bg-slate-50 p-4">
          <p className="font-mono text-sm font-semibold text-slate-900">POST /api/v1/risk/scan</p>
          <p className="mt-2 text-sm text-slate-600">Send user and transaction context. Response includes risk score and decision.</p>
          <p className="mt-2 text-xs font-semibold text-slate-500">Header: X-API-Key: your_secret_key</p>
        </div>
      </section>
    </div>
  )
}
