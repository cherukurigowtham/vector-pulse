"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Zap, ArrowLeft, ShieldCheck, Mail, Lock, User, Building, Phone } from "lucide-react";
import { cn } from "@/lib/cn";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:8000"
    : "https://vantix-wjsk.onrender.com");

export default function SignupPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [mobileNumber, setMobileNumber] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [captchaStatus, setCaptchaStatus] = useState<"idle" | "verifying" | "success">("idle");
  const router = useRouter();

  const handleCaptcha = () => {
    if (captchaStatus === "success") return;
    setCaptchaStatus("verifying");
    setTimeout(() => setCaptchaStatus("success"), 1200);
  };

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (captchaStatus !== "success") {
      setError("Please complete the security verification.");
      return;
    }

    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API_BASE}/api/v1/security/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          email, 
          password, 
          full_name: fullName, 
          company: companyName,
          mobile_number: mobileNumber 
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.message || data.detail || "Signup failed");
      }

      // If signup is successful and returns a token
      if (data.token) {
        localStorage.setItem("vp_token", data.token);
        document.cookie = `vp_token=${data.token}; path=/; max-age=86400; SameSite=Lax`;
        router.push("/dashboard");
      } else {
        // Fallback: Redirect to login
        router.push("/login?signup_success=true");
      }
    } catch (err: any) {
      setError(err.message || "Signup failed. Please try again.");
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

      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="flex justify-center mb-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-zinc-900 text-white shadow-lg">
            <Zap className="h-7 w-7 fill-white" />
          </div>
        </div>
        <h2 className="text-[32px] font-bold tracking-tight text-zinc-900 leading-tight">
          Create your workspace
        </h2>
        <p className="mt-3 text-sm font-medium text-zinc-500">
          Deploy high-velocity risk intelligence in minutes
        </p>
      </div>

      <div className="mt-10 sm:mx-auto sm:w-full sm:max-w-[520px]">
        <div className="bg-white py-10 px-10 shadow-[0_8px_30px_rgb(0,0,0,0.04)] sm:rounded-[24px] border border-zinc-100/80">
          <form className="space-y-6" onSubmit={handleSignup}>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-zinc-700 mb-2">Full Name</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <User className="h-4 w-4 text-zinc-400" />
                  </div>
                  <input
                    type="text"
                    required
                    placeholder=""
                    className="block w-full pl-11 pr-4 py-3 border-zinc-200 rounded-xl focus:ring-1 focus:ring-zinc-900 focus:border-zinc-900 text-sm transition-all bg-zinc-50/30 font-medium"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-semibold text-zinc-700 mb-2">Company</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                    <Building className="h-4 w-4 text-zinc-400" />
                  </div>
                  <input
                    type="text"
                    required
                    placeholder=""
                    className="block w-full pl-11 pr-4 py-3 border-zinc-200 rounded-xl focus:ring-1 focus:ring-zinc-900 focus:border-zinc-900 text-sm transition-all bg-zinc-50/30 font-medium"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                  />
                </div>
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-zinc-700 mb-2">Work Email</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Mail className="h-4 w-4 text-zinc-400" />
                </div>
                <input
                  type="email"
                  required
                  placeholder=""
                  className="block w-full pl-11 pr-4 py-3 border-zinc-200 rounded-xl focus:ring-1 focus:ring-zinc-900 focus:border-zinc-900 text-sm transition-all bg-zinc-50/30 font-medium"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-zinc-700 mb-2">Mobile (for interactive ops)</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Phone className="h-4 w-4 text-zinc-400" />
                </div>
                  <input
                    type="tel"
                    required
                    placeholder="+91"
                    className="block w-full pl-11 pr-4 py-3 border-zinc-200 rounded-xl focus:ring-1 focus:ring-zinc-900 focus:border-zinc-900 text-sm transition-all bg-zinc-50/30 font-medium"
                    value={mobileNumber}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val.startsWith("+91") || val === "+" || val === "") {
                        setMobileNumber(val);
                      } else if (/^\d/.test(val)) {
                        setMobileNumber("+91" + val);
                      }
                    }}
                  />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-zinc-700 mb-2">Password</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                  <Lock className="h-4 w-4 text-zinc-400" />
                </div>
                  <input
                    type="password"
                    required
                    minLength={6}
                    placeholder=""
                    className="block w-full pl-11 pr-4 py-3 border-zinc-200 rounded-xl focus:ring-1 focus:ring-zinc-900 focus:border-zinc-900 text-sm transition-all bg-zinc-50/30 font-medium"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
              </div>
            </div>

            <div className="flex items-center justify-between rounded-xl border border-zinc-100 bg-zinc-50/80 p-4 shadow-sm">
                <div className="flex items-center gap-3">
                  <button type="button" onClick={handleCaptcha} className={cn("flex h-6 w-6 items-center justify-center rounded-lg border transition-all duration-300", captchaStatus === "success" ? "bg-zinc-900 border-zinc-900 text-white" : "border-zinc-200 bg-white hover:border-zinc-300 shadow-sm")}>
                    {captchaStatus === "success" && <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>}
                    {captchaStatus === "verifying" && <div className="h-3 w-3 rounded-full border-[2px] border-zinc-300 border-t-zinc-600 animate-spin" />}
                  </button>
                  <span className="text-[13px] font-bold text-zinc-700">Verify you are human</span>
                </div>
                <div className="flex items-center gap-1.5 opacity-40">
                  <ShieldCheck className="h-4 w-4 text-zinc-800" />
                  <span className="text-[9px] font-black uppercase tracking-widest text-zinc-800">Protected</span>
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

            <button
              type="submit"
              disabled={loading}
              className="w-full flex justify-center py-3.5 px-4 border border-transparent rounded-xl shadow-sm text-sm font-bold text-white bg-zinc-900 hover:bg-zinc-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-zinc-900 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Creating workspace..." : "Continue"}
            </button>
          </form>
        </div>
        
        <p className="mt-10 text-center text-sm font-medium text-zinc-500">
          Already have an account?{" "}
          <Link href="/login" className="font-bold text-zinc-900 hover:underline underline-offset-4 decoration-2">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
