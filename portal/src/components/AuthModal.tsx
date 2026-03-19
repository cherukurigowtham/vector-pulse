"use client";

import { useState, useEffect } from "react";

const API_BASE = typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ? 'http://localhost:8000'
  : 'https://vector-pulse-api.onrender.com';

export default function AuthModal({ isOpen, mode, onClose, onAuthSuccess }: { isOpen: boolean, mode: "login" | "signup", onClose: () => void, onAuthSuccess: (data: any) => void }) {
  const [currentMode, setCurrentMode] = useState(mode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setCurrentMode(mode);
  }, [mode]);

  if (!isOpen) return null;

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    const endpoint = currentMode === "signup" ? `${API_BASE}/api/v1/security/auth/signup` : `${API_BASE}/api/v1/security/auth/login`;

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password })
      });
      const text = await response.text();
      let data;
      try { data = JSON.parse(text); } catch(e) {}
      if (!response.ok) throw new Error(data?.message || data?.detail || text || "Authentication failed");
      
      onAuthSuccess(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay active" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="modal">
        <div style={{ display: 'flex', gap: '10px', marginBottom: '24px' }}>
          <button 
            type="button"
            className="btn" 
            onClick={() => setCurrentMode("signup")} 
            style={{ flex: 1, background: currentMode === "signup" ? "var(--text)" : "var(--card)", color: currentMode === "signup" ? "var(--bg)" : "var(--text)" }}>
            Sign up
          </button>
          <button 
            type="button"
            className="btn" 
            onClick={() => setCurrentMode("login")} 
            style={{ flex: 1, background: currentMode === "login" ? "var(--text)" : "var(--card)", color: currentMode === "login" ? "var(--bg)" : "var(--text)" }}>
            Log in
          </button>
        </div>
        <h3 style={{ marginBottom: '12px' }}>{currentMode === "signup" ? "Create your account" : "Log back in"}</h3>
        <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>
          {currentMode === "signup" ? "Get a test key and open your Signal Hub." : "View your key, usage, and account details."}
        </p>
        
        <form onSubmit={handleAuth}>
          <input type="email" className="field" placeholder="you@company.com" required value={email} onChange={e => setEmail(e.target.value)} />
          <input type="password" className="field" placeholder="Password" required minLength={6} value={password} onChange={e => setPassword(e.target.value)} />
          <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '10px' }} disabled={loading}>
            {loading ? (currentMode === "signup" ? "Creating..." : "Logging in...") : (currentMode === "signup" ? "Create account" : "Log in")}
          </button>
        </form>
        {error && <div className="error" style={{ display: 'block' }}>{error}</div>}
      </div>
    </div>
  );
}
