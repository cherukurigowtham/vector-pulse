import Link from "next/link";
import { Zap } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-zinc-200 bg-white">
      <div className="container py-16 lg:py-24">
        <div className="grid gap-12 lg:grid-cols-5 lg:gap-8">
          <div className="lg:col-span-2 space-y-6">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="flex items-center justify-center text-zinc-900">
                <Zap className="h-6 w-6 stroke-[2.5px]" fill="currentColor" />
              </div>
              <span className="text-xl font-bold tracking-tight text-zinc-900">Vantix</span>
            </Link>
            <p className="text-sm leading-relaxed text-zinc-500 max-w-xs">
              Deterministic risk intelligence and structural governance for massive engineering teams. Built for high-volume scale.
            </p>
          </div>
          
          <div>
            <h3 className="text-sm font-semibold text-zinc-900 mb-6 tracking-tight">Product</h3>
            <ul className="space-y-4 text-sm text-zinc-500">
              <li><Link href="/#product" className="hover:text-zinc-900 transition-colors">Capabilities</Link></li>
              <li><Link href="/#docs" className="hover:text-zinc-900 transition-colors">Integration Guide</Link></li>
              <li><Link href="/#pricing" className="hover:text-zinc-900 transition-colors">Pricing Tiers</Link></li>
              <li><Link href="/dashboard" className="hover:text-zinc-900 transition-colors">Live Dashboard</Link></li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-zinc-900 mb-6 tracking-tight">Company</h3>
            <ul className="space-y-4 text-sm text-zinc-500">
              <li><a href="#" className="hover:text-zinc-900 transition-colors">About Us</a></li>
              <li><a href="#" className="hover:text-zinc-900 transition-colors">Customers</a></li>
              <li><a href="#" className="hover:text-zinc-900 transition-colors">Engineering Blog</a></li>
              <li><a href="#" className="hover:text-zinc-900 transition-colors">Careers</a></li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-zinc-900 mb-6 tracking-tight">Legal</h3>
            <ul className="space-y-4 text-sm text-zinc-500">
              <li><a href="#" className="hover:text-zinc-900 transition-colors">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-zinc-900 transition-colors">Terms of Service</a></li>
              <li><a href="#" className="hover:text-zinc-900 transition-colors">Cookie Policy</a></li>
              <li><a href="#" className="hover:text-zinc-900 transition-colors">Data Processing</a></li>
            </ul>
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-zinc-100 flex flex-col md:flex-row items-center justify-between gap-6">
          <p className="text-sm text-zinc-400">
            &copy; {new Date().getFullYear()} Vector Pulse Inc. All rights reserved.
          </p>
          <div className="flex items-center gap-4 text-sm font-medium text-zinc-400">
            <div className="flex items-center gap-2 bg-zinc-50 px-3 py-1.5 rounded-full border border-zinc-100 shadow-sm">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-[12px] font-semibold text-zinc-600">All systems nominal</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
