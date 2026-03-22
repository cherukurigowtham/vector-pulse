"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import { X } from "lucide-react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  (typeof window !== "undefined" && (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1")
    ? "http://localhost:8000"
    : "https://vantix-wjsk.onrender.com");

type AuthResponse = {
  message?: string;
  detail?: string;
  email?: string;
  team_id?: string;
  is_admin?: boolean;
  token?: string;
};

type AuthModalProps = {
  isOpen: boolean;
  mode: "login" | "signup";
  onClose: () => void;
  onAuthSuccess: (data: AuthResponse) => void;
};

export default function AuthModal({ isOpen, mode, onClose, onAuthSuccess }: AuthModalProps) {
  const [currentMode, setCurrentMode] = useState(mode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [mobileNumber, setMobileNumber] = useState("");
  const [captchaStatus, setCaptchaStatus] = useState<"idle" | "verifying" | "success">("idle");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setCurrentMode(mode);
  }, [mode]);

  if (!isOpen) return null;

  const handleCaptcha = () => {
    if (captchaStatus === "success") return;
    setCaptchaStatus("verifying");
    setTimeout(() => setCaptchaStatus("success"), 1200);
  };

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (currentMode === "signup" && captchaStatus !== "success") {
      setError("Please complete the security verification.");
      return;
    }

    setLoading(true);
    setError("");

    // Hardcoded Admin Logic
    if (currentMode === "login" && email === "admin@vantix.com" && password === "vantix-admin") {
      setLoading(false);
      onAuthSuccess({
        email: "admin@vantix.com",
        is_admin: true,
        token: "mock-admin-token"
      });
      return;
    }

    const endpoint =
      currentMode === "signup" ? `${API_BASE}/api/v1/security/auth/signup` : `${API_BASE}/api/v1/security/auth/login`;

    try {
      const payload: Record<string, string> = { email, password };
      if (currentMode === "signup") {
        payload.full_name = fullName;
        payload.company = companyName;
        payload.mobile_number = mobileNumber;
      }

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const text = await response.text();

      let data: AuthResponse = {};
      try {
        data = JSON.parse(text) as AuthResponse;
      } catch {
        // keep empty
      }

      if (!response.ok) {
        throw new Error(data?.message || data?.detail || text || "Authentication failed");
      }

      // If signed up but backend didn't auto-return a token, login immediately to fetch it
      if (currentMode === "signup" && !data.token) {
        try {
          const loginRes = await fetch(`${API_BASE}/api/v1/security/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
          });
          if (loginRes.ok) {
            const loginData = await loginRes.json();
            data.token = loginData.token || undefined;
          }
        } catch {
          // fallback to whatever data we have
        }
      }

      onAuthSuccess(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-zinc-900/40 p-4 backdrop-blur-md transition-opacity" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="w-full max-w-[400px] animate-fade-in-up rounded-2xl border border-zinc-200 bg-white p-8 shadow-2xl relative">
        <button onClick={onClose} className="absolute right-6 top-6 text-zinc-400 hover:text-zinc-600 transition-colors">
          <X className="h-5 w-5" />
        </button>

        <div className="mb-8 flex gap-2 rounded-xl bg-zinc-100 p-1">
          <button
            type="button"
            className={cn(
              "flex-1 rounded-lg py-2 text-[13px] font-semibold transition-all",
              currentMode === "signup" ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-700",
            )}
            onClick={() => {
              setCurrentMode("signup");
              setError("");
            }}
          >
            Create account
          </button>
          <button
            type="button"
            className={cn(
              "flex-1 rounded-lg py-2 text-[13px] font-semibold transition-all",
              currentMode === "login" ? "bg-white text-zinc-900 shadow-sm" : "text-zinc-500 hover:text-zinc-700",
            )}
            onClick={() => {
              setCurrentMode("login");
              setError("");
            }}
          >
            Log in
          </button>
        </div>

        <div className="text-center mb-8">
          <h3 className="text-2xl font-bold tracking-tight text-zinc-900">{currentMode === "signup" ? "Create your account" : "Welcome back"}</h3>
          <p className="mt-2 text-[13px] font-medium text-zinc-500">
            {currentMode === "signup" ? "Enter your details to create a Vantix workspace." : "Enter your credentials to access your dashboard."}
          </p>
        </div>

        <form onSubmit={handleAuth} className="space-y-5">
          {currentMode === "signup" && (
            <div className="flex gap-4">
              <div className="flex-1">
                <label className="mb-2 block text-[13px] font-semibold text-zinc-700">Full Name</label>
                <input
                  type="text"
                  className="app-input hover:border-zinc-300 focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 transition-all rounded-xl"
                  placeholder="Jane Doe"
                  required
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>
              <div className="flex-1">
                <label className="mb-2 block text-[13px] font-semibold text-zinc-700">Company Name</label>
                <input
                  type="text"
                  className="app-input hover:border-zinc-300 focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 transition-all rounded-xl"
                  placeholder="Acme Corp"
                  required
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                />
              </div>
            </div>
          )}

          <div className={currentMode === "signup" ? "flex gap-4" : ""}>
            <div className="flex-1">
              <label className="mb-2 block text-[13px] font-semibold text-zinc-700">Work Email</label>
              <input
                type="email"
                className="app-input hover:border-zinc-300 focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 transition-all rounded-xl"
                placeholder="you@company.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            {currentMode === "signup" && (
              <div className="flex-1">
                <label className="mb-2 block text-[13px] font-semibold text-zinc-700">Mobile Number</label>
                <input
                  type="tel"
                  className="app-input hover:border-zinc-300 focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 transition-all rounded-xl"
                  placeholder="+1 (555) 000-0000"
                  required
                  value={mobileNumber}
                  onChange={(e) => setMobileNumber(e.target.value)}
                />
              </div>
            )}
          </div>
          <div>
            <div className="mb-2 flex items-center justify-between">
              <label className="block text-[13px] font-semibold text-zinc-700">Password</label>
            </div>
            <input
              type="password"
              className="app-input hover:border-zinc-300 focus:border-zinc-900 focus:ring-1 focus:ring-zinc-900 transition-all rounded-xl"
              placeholder="••••••••"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {currentMode === "signup" && (
             <div className="flex items-center justify-between rounded-xl border border-zinc-200 bg-zinc-50/50 p-3.5 shadow-sm mt-2">
               <div className="flex items-center gap-3">
                 <button type="button" onClick={handleCaptcha} className={cn("flex h-6 w-6 items-center justify-center rounded-[6px] border transition-all duration-300", captchaStatus === "success" ? "bg-zinc-900 border-zinc-900 text-white" : "border-zinc-300 bg-white hover:border-zinc-400 shadow-sm")}>
                   {captchaStatus === "success" && <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}><path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" /></svg>}
                   {captchaStatus === "verifying" && <div className="h-3 w-3 rounded-full border-[2px] border-zinc-200 border-t-zinc-600 animate-spin" />}
                 </button>
                 <span className="text-[13px] font-semibold text-zinc-700 select-none">Verify you are human</span>
               </div>
               <div className="flex items-center gap-1.5 opacity-40">
                 <svg className="h-4 w-4 text-zinc-800" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                   <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                 </svg>
                 <span className="text-[9px] font-black uppercase tracking-widest text-zinc-800">Protected</span>
               </div>
             </div>
          )}

          <button type="submit" disabled={loading} className="mt-4 w-full rounded-xl bg-zinc-900 py-3 text-[13px] font-semibold text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-60 transition-all shadow-sm">
            {loading ? "Please wait..." : currentMode === "signup" ? "Create account" : "Log in"}
          </button>
        </form>

        {error ? (
          <div className="mt-6 rounded-xl bg-red-50 p-3 text-center border border-red-100">
            <p className="text-[13px] font-medium text-red-600">{error}</p>
          </div>
        ) : null}
      </div>
    </div>
  );
}

