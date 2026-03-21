"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Lock, CheckCircle2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

export default function PaymentForm({ plan }: { plan: string }) {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [form, setForm] = useState({
    name: "",
    card: "",
    exp: "",
    cvc: ""
  });

  const handleCardChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value.replace(/\D/g, "");
    if (value.length > 16) value = value.slice(0, 16);
    const groups = value.match(/.{1,4}/g);
    setForm({ ...form, card: groups ? groups.join(" ") : "" });
  };

  const handleExpChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value.replace(/\D/g, "");
    if (value.length > 4) value = value.slice(0, 4);
    if (value.length >= 2) {
      value = `${value.slice(0, 2)}/${value.slice(2)}`;
    }
    setForm({ ...form, exp: value });
  };

  const handleCvcChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let value = e.target.value.replace(/\D/g, "");
    if (value.length > 4) value = value.slice(0, 4);
    setForm({ ...form, cvc: value });
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const [expMonth, expYear] = form.exp.split("/");
      const res = await apiFetch("/merchant/billing/checkout", {
        method: "POST",
        body: JSON.stringify({
          plan_tier: plan,
          card_number: form.card.replace(/\s/g, ""),
          exp_month: expMonth || "",
          exp_year: expYear || "",
          cvc: form.cvc,
          name_on_card: form.name
        })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Payment failed to process.");
      }

      setSuccess(true);
      setTimeout(() => {
        router.push("/dashboard");
      }, 2000);

    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center animate-in fade-in zoom-in duration-500">
        <div className="h-16 w-16 bg-emerald-100 rounded-full flex items-center justify-center mb-6">
          <CheckCircle2 className="h-8 w-8 text-emerald-600" />
        </div>
        <h3 className="text-2xl font-bold text-zinc-900 mb-2">Payment Successful</h3>
        <p className="text-zinc-500">Your organization has been upgraded. Redirecting to dashboard...</p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-zinc-700 mb-1.5">Cardholder Name</label>
          <input
            type="text"
            required
            className="w-full px-4 py-2 bg-white border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-zinc-900 outline-none transition-all placeholder:text-zinc-300"
            placeholder="Jane Doe"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            disabled={loading}
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-zinc-700 mb-1.5">Card Number</label>
          <div className="relative">
            <input
              type="text"
              required
              className="w-full pl-11 pr-4 py-2 bg-white border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-zinc-900 outline-none transition-all placeholder:text-zinc-300 font-mono"
              placeholder="0000 0000 0000 0000"
              value={form.card}
              onChange={handleCardChange}
              disabled={loading}
            />
            <svg className="absolute left-3.5 top-1/2 -translate-y-1/2 h-5 w-5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1.5">Expiration</label>
            <input
              type="text"
              required
              className="w-full px-4 py-2 bg-white border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-zinc-900 outline-none transition-all placeholder:text-zinc-300 font-mono"
              placeholder="MM/YY"
              value={form.exp}
              onChange={handleExpChange}
              disabled={loading}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-1.5">CVC</label>
            <input
              type="text"
              required
              className="w-full px-4 py-2 bg-white border border-zinc-200 rounded-lg focus:ring-2 focus:ring-zinc-900 focus:border-zinc-900 outline-none transition-all placeholder:text-zinc-300 font-mono"
              placeholder="123"
              value={form.cvc}
              onChange={handleCvcChange}
              disabled={loading}
            />
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-lg bg-red-50 border border-red-100 text-sm text-red-600 font-medium">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={loading || form.card.length < 19}
        className="w-full relative flex items-center justify-center gap-2 bg-black hover:bg-zinc-800 text-white font-medium py-3 px-4 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {loading ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Processing Network...
          </>
        ) : (
          <>
            <Lock className="h-4 w-4" />
            Pay Now
          </>
        )}
      </button>

      <p className="text-[11px] text-center text-zinc-500 font-medium pt-2">
        Secured by Vantix Simulated Gateway &middot; 256-bit AES
      </p>
    </form>
  );
}
