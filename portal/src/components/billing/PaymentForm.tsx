"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Lock, CheckCircle2, ShieldCheck, CreditCard } from "lucide-react";
import { apiFetch } from "@/lib/api";

export default function PaymentForm({ plan }: { plan: string }) {
  const router = useRouter();
  
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [step, setStep] = useState<"PLAN" | "VERIFYING">("PLAN");

  const onMockPay = async () => {
    setLoading(true);
    setError(null);

    try {
      // Step 1: Create Order in Go Engine
      const orderData = await apiFetch("/merchant/payments/orders", {
        method: "POST",
        body: JSON.stringify({ amount: 49.99 })
      });

      const orderId = orderData.id;

      // Step 2: Simulate Razorpay Handshake (2.5s simulated gateway processing)
      setStep("VERIFYING");
      await new Promise(resolve => setTimeout(resolve, 2500));

      // Step 3: Verify & Settle
      const verifyRes = await apiFetch("/merchant/payments/verify", {
        method: "POST",
        body: JSON.stringify({
          razorpay_order_id: orderId,
          razorpay_payment_id: `pay_mock_${Date.now()}`,
          razorpay_signature: "mock_sig_v1_vp_sovereign"
        })
      });

      // apiFetch throws if not ok, so no need for manual check if we just want the error reported.
      // But VerifyOrder returns json which apiFetch parses.

      setSuccess(true);
      setTimeout(() => {
        router.push("/dashboard");
      }, 2000);

    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Financial rail error. Contact support.");
      setLoading(false);
      setStep("PLAN");
    }
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center animate-in fade-in zoom-in duration-500">
        <div className="h-20 w-20 bg-emerald-100 rounded-full flex items-center justify-center mb-8 shadow-inner shadow-emerald-200">
          <CheckCircle2 className="h-10 w-10 text-emerald-600" />
        </div>
        <h3 className="text-[28px] font-bold text-zinc-900 mb-3 tracking-tight">Access Granted</h3>
        <p className="text-zinc-500 font-medium max-w-[280px] leading-relaxed">Your sovereign workspace has been upgraded to <strong>{plan}</strong>.</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="bg-zinc-50/50 rounded-2xl border border-zinc-100 p-6">
        <div className="flex items-center justify-between mb-6">
          <h4 className="text-sm font-bold text-zinc-500 uppercase tracking-widest">Plan Selection</h4>
          <span className="bg-zinc-900 text-white text-[10px] font-black px-2 py-1 rounded-md uppercase tracking-tighter">Billed Monthly</span>
        </div>
        <div className="flex items-baseline gap-1">
          <span className="text-[40px] font-black text-zinc-900">₹4,999</span>
          <span className="text-zinc-400 font-bold text-lg">/mo</span>
        </div>
        <p className="mt-2 text-sm font-medium text-zinc-600 italic">Advanced Neural Risk Intelligence with T-0 Settlement.</p>
      </div>

      <div className="space-y-4">
        <div className="flex items-center gap-3 p-4 rounded-xl border border-blue-50 bg-blue-50/30">
          <ShieldCheck className="h-5 w-5 text-blue-600" />
          <p className="text-xs font-semibold text-blue-800 leading-tight">
            Razorpay Integration is currently in "Mock Mode". No real money will be deducted during this final verification phase.
          </p>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-red-50 border border-red-100 text-sm text-red-600 font-bold">
            {error}
          </div>
        )}

        <button
          onClick={onMockPay}
          disabled={loading}
          className="w-full relative h-[60px] flex items-center justify-center gap-3 bg-zinc-900 hover:bg-zinc-800 text-white font-bold text-lg rounded-xl transition-all hover:scale-[1.01] active:scale-[0.99] shadow-xl shadow-zinc-200 disabled:opacity-70"
        >
          {loading ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              {step === "PLAN" ? "Initializing..." : "Quantum Settlement..."}
            </>
          ) : (
            <>
              <CreditCard className="h-5 w-5" />
              Upgrade to {plan}
            </>
          )}
        </button>
      </div>

      <div className="flex flex-col items-center gap-4 pt-4">
        <div className="flex items-center gap-2 opacity-30 grayscale cursor-not-allowed">
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-900">Razorpay</span>
            <div className="h-3 w-[1px] bg-zinc-300" />
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-900">VISA</span>
            <div className="h-3 w-[1px] bg-zinc-300" />
            <span className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-900">Mastercard</span>
        </div>
        <p className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest flex items-center gap-1.5">
          <Lock className="h-3 w-3" /> Secure Bank-Grade Infrastructure
        </p>
      </div>
    </div>
  );
}
