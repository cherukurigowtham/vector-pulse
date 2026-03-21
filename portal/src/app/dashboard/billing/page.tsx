"use client"

import { useEffect, useState } from "react"
import { CheckCircle, Clock, CreditCard, Download, Receipt, Zap } from "lucide-react"
import { apiFetch } from "@/lib/api"

type PaymentHistoryItem = {
  status: string
  payment_id: string
  amount: number
  timestamp: number
}

export default function BillingPage() {
  const [history, setHistory] = useState<PaymentHistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState(false)
  const [paymentSuccess, setPaymentSuccess] = useState(false)

  const fetchHistory = async () => {
    try {
      const data = await apiFetch("/merchant/payments/history")
      setHistory((data.history || []) as PaymentHistoryItem[])
    } catch {
      // noop
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  const handlePayNow = async () => {
    setPaying(true)
    try {
      const order = await apiFetch("/merchant/payments/orders", {
        method: "POST",
        body: JSON.stringify({ amount: 49.99 }),
      })

      await new Promise((resolve) => setTimeout(resolve, 800))

      const verification = await apiFetch("/merchant/payments/verify", {
        method: "POST",
        body: JSON.stringify({
          razorpay_order_id: order.id,
          razorpay_payment_id: `pay_${Math.random().toString(36).substring(7)}`,
          razorpay_signature: "mock_sig_verification_passed_123",
        }),
      })

      if (verification.status === "success") {
        setPaymentSuccess(true)
        fetchHistory()
        setTimeout(() => setPaymentSuccess(false), 5000)
      }
    } catch {
      // noop
    } finally {
      setPaying(false)
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Billing</h1>
          <p className="text-sm text-slate-600">Subscription details and transaction history.</p>
        </div>
        <button
          onClick={handlePayNow}
          disabled={paying}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--primary)] px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {paying ? <Clock className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
          {paying ? "Processing..." : "Pay Rs 4,150.00"}
        </button>
      </div>

      {paymentSuccess ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-700">
          Payment completed and credits updated successfully.
        </div>
      ) : null}

      <section className="grid gap-4 md:grid-cols-2">
        <article className="app-card p-5">
          <p className="kicker mb-3">Plan</p>
          <h2 className="text-2xl font-bold text-slate-900">Enterprise</h2>
          <p className="mt-1 text-sm text-slate-600">500k scans / month with advanced governance features.</p>

          <ul className="mt-4 space-y-2 text-sm text-slate-700">
            <li className="flex items-center gap-2"><CheckCircle className="h-4 w-4 text-emerald-600" /> Dedicated support</li>
            <li className="flex items-center gap-2"><CheckCircle className="h-4 w-4 text-emerald-600" /> Real-time audit stream</li>
            <li className="flex items-center gap-2"><CheckCircle className="h-4 w-4 text-emerald-600" /> Rule automation</li>
          </ul>
        </article>

        <article className="app-card p-5">
          <p className="kicker mb-3">Usage</p>
          <MetricRow icon={CreditCard} label="Scans used" value="14,204 / 500,000" />
          <MetricRow icon={Zap} label="Signal threshold" value="82%" />
          <MetricRow icon={Receipt} label="Next invoice" value="April 01, 2026" />
        </article>
      </section>

      <section className="app-card overflow-x-auto">
        <div className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
          <h2 className="text-sm font-bold text-slate-900">Transaction History</h2>
          <span className="inline-flex items-center gap-1 text-xs text-slate-500"><Download className="h-3.5 w-3.5" /> Export</span>
        </div>
        <table className="w-full min-w-[680px] border-collapse text-left">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50 text-xs font-semibold uppercase tracking-wide text-slate-500">
              <th className="px-4 py-3">Payment ID</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Amount</th>
              <th className="px-4 py-3">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 bg-white">
            {loading ? (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center text-sm text-slate-500">Loading payments...</td>
              </tr>
            ) : history.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-12 text-center text-sm text-slate-500">No payment history yet.</td>
              </tr>
            ) : (
              history.map((item) => (
                <tr key={item.payment_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3 font-mono text-xs text-slate-600">{item.payment_id}</td>
                  <td className="px-4 py-3 text-sm text-slate-700">
                    {new Date(item.timestamp * 1000).toLocaleDateString("en-IN", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </td>
                  <td className="px-4 py-3 text-sm font-semibold text-slate-900">Rs {item.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                  <td className="px-4 py-3">
                    <span className="inline-flex items-center rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">
                      {item.status}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </div>
  )
}

function MetricRow({ icon: Icon, label, value }: { icon: React.ComponentType<{ className?: string }>; label: string; value: string }) {
  return (
    <div className="mt-3 flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5">
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <Icon className="h-4 w-4" />
        {label}
      </div>
      <span className="text-sm font-semibold text-slate-900">{value}</span>
    </div>
  )
}
