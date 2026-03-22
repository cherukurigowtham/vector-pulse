import Link from "next/link";
import { Zap } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-zinc-800 bg-black">
      <div className="container py-16 lg:py-24">
        <div className="grid gap-12 lg:grid-cols-5 lg:gap-8">
          <div className="lg:col-span-2 space-y-6">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="flex items-center justify-center text-white">
                <Zap className="h-6 w-6 stroke-[2.5px]" fill="currentColor" />
              </div>
              <span className="text-xl font-bold bg-gradient-to-r from-white to-zinc-500 bg-clip-text text-transparent">
              Vantix
            </span>
            </Link>
            <p className="text-zinc-500 text-sm mb-6 max-w-xs">
            The autonomous risk intelligence layer for the $10 trillion global ledger.
            </p>
          </div>
          
          <div>
            <h3 className="text-sm font-semibold text-white mb-6 tracking-tight">Product</h3>
            <ul className="space-y-4 text-sm text-zinc-400">
              <li><Link href="/#product" className="hover:text-white transition-colors">Capabilities</Link></li>
              <li><Link href="/#docs" className="hover:text-white transition-colors">Integration Guide</Link></li>
              <li><Link href="/#pricing" className="hover:text-white transition-colors">Pricing Tiers</Link></li>
              <li><Link href="/dashboard" className="hover:text-white transition-colors">Live Dashboard</Link></li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-white mb-6 tracking-tight">Company</h3>
            <ul className="space-y-4 text-sm text-zinc-400">
              <li><a href="#" className="hover:text-white transition-colors">About Us</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Customers</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Engineering Blog</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Careers</a></li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-white mb-6 tracking-tight">Legal</h3>
            <ul className="space-y-4 text-sm text-zinc-400">
              <li><a href="#" className="hover:text-white transition-colors">Privacy Policy</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Terms of Service</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Cookie Policy</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Data Processing</a></li>
            </ul>
          </div>
        </div>

        <div className="mt-16 pt-8 border-t border-zinc-800 flex flex-col md:flex-row items-center justify-between gap-6">
          <p className="text-sm text-zinc-500">
            &copy; {new Date().getFullYear()} Vantix Inc. All rights reserved.
          </p>
          <div className="flex items-center gap-4 text-sm font-medium text-zinc-500">
            <div className="flex items-center gap-2 bg-zinc-900 px-3 py-1.5 rounded-full border border-zinc-800 shadow-sm">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-[12px] font-semibold text-zinc-300">All systems nominal</span>
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
