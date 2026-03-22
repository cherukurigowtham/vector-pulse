"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Zap, ArrowLeft, ShieldCheck, Mail, Lock } from "lucide-react";
import { cn } from "@/lib/cn";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:8000"
    : "https://vantix-wjsk.onrender.com");

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("vp_token");
    if (token) {
      router.push("/dashboard");
    }
  }, [router]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    // Hardcoded Admin Logic
    if (email === "admin@vantix.com" && password === "vantix-admin") {
      localStorage.setItem("vp_token", "mock-admin-token");
      document.cookie = "vp_token=mock-admin-token; path=/; max-age=86400; SameSite=Lax";
      router.push("/dashboard/admin");
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/v1/security/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || data.detail || "Invalid credentials");
      }

      if (data.token) {
        localStorage.setItem("vp_token", data.token);
        document.cookie = `vp_token=${data.token}; path=/; max-age=86400; SameSite=Lax`;
      }

      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Authentication failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#fafafa] flex flex-col justify-center py-12 sm:px-6 lg:px-8 font-sans">
      <div className="absolute top-8 left-8">
        <Link href="/" className="inline-flex items-center gap-2 text-zinc-500 hover:text-zinc-900 transition-colors text-sm font-medium">
          <ArrowLeft className="h-4 w-4" />
          Back to home
        </Link>
      </div>

      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="flex justify-center mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-zinc-900 text-white shadow-lg">
            <Zap className="h-7 w-7 fill-white" />
          </div>
        </div>
        <h2 className="text-center text-[32px] font-bold tracking-tight text-zinc-900">
          Sign in to Vantix
        </h2>
        <p className="mt-3 text-center text-sm font-medium text-zinc-500">
          Enter your credentials to access your high-velocity dashboard
        </p>
      </div>

      <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-[440px]">
        <div className="bg-white py-10 px-10 shadow-[0_8px_30px_rgb(0,0,0,0.04)] sm:rounded-[24px] border border-zinc-100/80">
          <form className="space-y-6" onSubmit={handleLogin}>
            <div>
              <label htmlFor="email" className="block text-sm font-semibold text-zinc-700 mb-2">
                Work Email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-zinc-400" />
                </div>
                <input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="name@company.com"
                  className="block w-full pl-11 pr-4 py-3 border-zinc-200 rounded-xl focus:ring-1 focus:ring-zinc-900 focus:border-zinc-900 text-sm transition-all bg-zinc-50/30 placeholder:text-zinc-400 font-medium"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label htmlFor="password" className="block text-sm font-semibold text-zinc-700">
                  Password
                </label>
                <div className="text-sm">
                  <a href="#" className="font-semibold text-zinc-600 hover:text-zinc-900 transition-colors">
                    Forgot password?
                  </a>
                </div>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-zinc-400" />
                </div>
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  placeholder="••••••••"
                  className="block w-full pl-11 pr-4 py-3 border-zinc-200 rounded-xl focus:ring-1 focus:ring-zinc-900 focus:border-zinc-900 text-sm transition-all bg-zinc-50/30 placeholder:text-zinc-400 font-medium"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>
            </div>

            {error && (
              <div className="p-4 rounded-xl bg-red-50 border border-red-100 flex items-start gap-3">
                <div className="h-5 w-5 text-red-500 mt-0.5 shrink-0">
                   <svg fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                </div>
                <p className="text-sm font-semibold text-red-600 leading-tight">{error}</p>
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-3.5 px-4 border border-transparent rounded-xl shadow-sm text-sm font-bold text-white bg-zinc-900 hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-zinc-900 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Verifying..." : "Sign in"}
              </button>
            </div>
          </form>

          <div className="mt-8 pt-8 border-t border-zinc-100">
            <div className="flex items-center justify-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-500" />
              <span className="text-xs font-bold text-zinc-500 uppercase tracking-widest">
                Protected by Sovereign Intelligence
              </span>
            </div>
          </div>
        </div>
        
        <p className="mt-10 text-center text-sm font-medium text-zinc-500">
          Don't have an account?{" "}
          <Link href="/signup" className="font-bold text-zinc-900 hover:underline underline-offset-4 decoration-2">
            Create workspace
          </Link>
        </p>
      </div>
    </div>
  );
}
