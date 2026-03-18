"use client"

import { useState, useEffect } from "react"
import { 
  CreditCard, 
  ArrowUpRight, 
  CheckCircle, 
  Clock, 
  Download, 
  ShieldCheck,
  Zap,
  Layout
} from "lucide-react"
import { apiFetch } from "@/lib/api"
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export default function BillingPage() {
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [paying, setPaying] = useState(false)
  const [paymentSuccess, setPaymentSuccess] = useState(false)

  const fetchHistory = async () => {
    try {
      const data = await apiFetch("/merchant/payments/history")
      setHistory(data.history || [])
    } catch (err) {
      console.error("Failed to fetch billing history:", err)
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
      // 1. Create Order
      const order = await apiFetch("/merchant/payments/orders", {
          method: "POST",
          body: JSON.stringify({ amount: 49.99 })
      })

      // 2. Simulate Local Mock Delay (User interaction with Razorpay Modal)
      await new Promise(r => setTimeout(r, 2000))

      // 3. Verify Payment with Mock Signature
      const verification = await apiFetch("/merchant/payments/verify", {
          method: "POST",
          body: JSON.stringify({
              razorpay_order_id: order.id,
              razorpay_payment_id: `pay_${Math.random().toString(36).substring(7)}`,
              razorpay_signature: "mock_sig_verification_passed_123"
          })
      })

      if (verification.status === "success") {
        setPaymentSuccess(true)
        fetchHistory()
        setTimeout(() => setPaymentSuccess(false), 5000)
      }
    } catch (err) {
      alert("Payment simulation failed. Check console.")
    } finally {
      setPaying(false)
    }
  }

  return (
    <div className="space-y-8 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Billing & Subscription</h1>
          <p className="text-slate-500">Manage your "Safe Scans" balance and transaction history.</p>
        </div>
        <button 
          onClick={handlePayNow}
          disabled={paying}
          className={cn(
            "flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold text-sm transition-all shadow-lg",
            paying ? "bg-slate-100 text-slate-400 cursor-not-allowed" : "bg-indigo-600 text-white hover:bg-indigo-700 active:scale-95 shadow-indigo-200 dark:shadow-none"
          )}
        >
          {paying ? (
             <>
               <Clock className="h-4 w-4 animate-spin" />
               Processing...
             </>
          ) : (
             <>
               <Zap className="h-4 w-4 fill-current" />
               Settlement: Pay ₹4,150.00
             </>
          )}
        </button>
      </div>

      {paymentSuccess && (
        <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-100 text-emerald-700 flex items-center gap-3 animate-in fade-in slide-in-from-top-4">
          <CheckCircle className="h-5 w-5" />
          <span className="font-medium text-sm">Payment Successful! Your account has been updated.</span>
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid gap-6 md:grid-cols-3">
        <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm dark:bg-slate-900 dark:border-slate-800">
           <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Total Safe Scans</p>
           <h3 className="text-3xl font-black text-slate-900 dark:text-white">1,402</h3>
           <p className="text-xs text-emerald-600 mt-2 font-medium">+12.4% vs last month</p>
        </div>
        <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm dark:bg-slate-900 dark:border-slate-800">
           <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-4">Pending Settlement</p>
           <h3 className="text-3xl font-black text-slate-900 dark:text-white">₹4,150</h3>
           <p className="text-xs text-amber-600 mt-2 font-medium">Due in 5 days</p>
        </div>
        <div className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm dark:bg-slate-900 dark:border-slate-800 border-l-4 border-l-indigo-500">
           <p className="text-xs font-bold text-indigo-500 uppercase tracking-widest mb-4">Current Plan</p>
           <h3 className="text-3xl font-black text-slate-900 dark:text-white">Enterprise AI</h3>
           <p className="text-xs text-slate-400 mt-2 font-medium">Volume-based Pricing</p>
        </div>
      </div>

      {/* Transaction History */}
      <div className="rounded-2xl border border-slate-200 bg-white overflow-hidden shadow-sm dark:bg-slate-900 dark:border-slate-800">
        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <h2 className="font-bold text-slate-800 dark:text-slate-100">Transaction History</h2>
          <button className="text-xs font-bold text-indigo-600 flex items-center gap-1 hover:underline">
             Download CSV <Download className="h-3 w-3" />
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50/50 dark:bg-slate-800/50 text-slate-500 font-medium border-b border-slate-100 dark:border-slate-800">
              <tr>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Transaction ID</th>
                <th className="px-6 py-4">Amount</th>
                <th className="px-6 py-4">Date</th>
                <th className="px-6 py-4">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {loading ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400">Loading your history...</td>
                </tr>
              ) : history.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-12 text-center text-slate-400">No transactions recorded yet.</td>
                </tr>
              ) : (
                history.map((tx, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors">
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md bg-emerald-50 text-emerald-700 text-[10px] font-bold uppercase dark:bg-emerald-900/20 dark:text-emerald-400">
                        <CheckCircle className="h-3 w-3" /> {tx.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 font-mono text-xs">{tx.payment_id}</td>
                    <td className="px-6 py-4 font-bold text-slate-900 dark:text-white">₹{tx.amount.toFixed(2)}</td>
                    <td className="px-6 py-4 text-slate-500">{new Date(tx.timestamp * 1000).toLocaleDateString()}</td>
                    <td className="px-6 py-4">
                        <button className="p-2 text-slate-400 hover:text-indigo-600 transition-colors">
                           <Layout className="h-4 w-4" />
                        </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
