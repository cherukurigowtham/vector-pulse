import Link from "next/link";
import { Zap, ShieldCheck } from "lucide-react";
import PaymentForm from "@/components/billing/PaymentForm";

export default function CheckoutPage({ searchParams }: { searchParams: { plan?: string } }) {
  const plan = searchParams.plan || "growth";
  
  const planName = plan.charAt(0).toUpperCase() + plan.slice(1);
  const price = plan === "professional" ? "$999" : "$299";

  return (
    <div className="min-h-screen bg-[#FAFAFA] flex flex-col selection:bg-black selection:text-white">
      <header className="border-b border-zinc-200 bg-white sticky top-0 z-50">
        <div className="container flex h-16 items-center">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex items-center justify-center text-zinc-900">
              <Zap className="h-5 w-5 stroke-[2.5px]" fill="currentColor" />
            </div>
            <span className="text-xl font-bold tracking-tight text-zinc-900">Vantix</span>
          </Link>
          <div className="ml-auto text-sm font-medium text-zinc-500">
            Secure Checkout
          </div>
        </div>
      </header>

      <main className="flex-1 flex items-center justify-center py-12 px-4">
        <div className="w-full max-w-5xl grid md:grid-cols-2 gap-12 lg:gap-24 items-start">
          
          <div className="space-y-8 md:pt-12">
            <div>
              <p className="text-sm font-bold text-zinc-500 mb-3 uppercase tracking-widest">Subscribe to Vantix</p>
              <h1 className="text-4xl lg:text-5xl font-bold tracking-tight text-zinc-900 mb-6">
                {planName} Tier
              </h1>
              <div className="flex items-baseline gap-2 mb-8">
                <span className="text-6xl font-black text-black tracking-tight">{price}</span>
                <span className="text-xl text-zinc-500 font-medium tracking-tight">/month</span>
              </div>
            </div>

            <div className="space-y-6 pt-6 border-t border-zinc-200">
              <div className="flex gap-4">
                <ShieldCheck className="h-6 w-6 text-emerald-500 shrink-0" />
                <div>
                  <h4 className="font-semibold text-zinc-900 text-lg">Enterprise SLA</h4>
                  <p className="text-sm text-zinc-600 leading-relaxed mt-1 tracking-tight">Guaranteed 99.99% uptime with priority multi-regional routing algorithms.</p>
                </div>
              </div>
              <div className="flex gap-4">
                <ShieldCheck className="h-6 w-6 text-emerald-500 shrink-0" />
                <div>
                  <h4 className="font-semibold text-zinc-900 text-lg">Zero-Cost Simulation Engine</h4>
                  <p className="text-sm text-zinc-600 leading-relaxed mt-1 tracking-tight">This gateway will completely simulate financial latency and securely upgrade your account without charging any real bank.</p>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white border border-zinc-200 rounded-2xl shadow-xl shadow-zinc-200/50 p-8 md:p-10">
            <div className="mb-8">
              <h3 className="text-xl font-bold text-zinc-900">Payment Details</h3>
              <p className="text-sm text-zinc-500 mt-1">Enter your card methodology</p>
            </div>
            <PaymentForm plan={plan} />
          </div>

        </div>
      </main>
    </div>
  );
}
