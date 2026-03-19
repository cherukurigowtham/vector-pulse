"use client";

import { useState, useEffect } from "react";
import AuthModal from "./AuthModal";

export default function Navigation() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [loggedIn, setLoggedIn] = useState(false);
  const [dashboardOpen, setDashboardOpen] = useState(false);
  const [user, setUser] = useState<any>(null);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'}/api/v1/security/auth/me`);
        if (response.ok) {
          const data = await response.json();
          setUser(data);
          setLoggedIn(true);
        }
      } catch (err) {}
    };
    checkSession();
  }, []);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 40);
    };
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  const openAuth = (mode: "login" | "signup") => {
    setAuthMode(mode);
    setAuthModalOpen(true);
    setDrawerOpen(false);
  };

  const handleLogout = async () => {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'}/api/v1/security/auth/logout`, { method: "POST" });
    } catch (err) {}
    setLoggedIn(false);
    setUser(null);
    setDashboardOpen(false);
  };

  return (
    <>
      <nav style={{ background: isScrolled ? "rgba(5,5,5,0.95)" : "rgba(5,5,5,0.5)" }}>
        <div className="container">
          <a href="#" className="brand">
            <img src="/logo-mark.png" alt="" style={{ height: '32px', width: 'auto' }} />
            <span>Vantix</span>
          </a>
          <div className="nav-links">
            <a href="#product">Product</a>
            <a href="#how-it-works">How it Works</a>
            <a href="#pricing">Pricing</a>
            <a href="#results">Results</a>
          </div>
          <div className="nav-actions">
            {!loggedIn ? (
              <>
                <button onClick={() => openAuth('login')} className="btn btn-secondary">Log in</button>
                <button onClick={() => openAuth('signup')} className="btn btn-primary">Get Access</button>
              </>
            ) : (
                <>
                  <button className="btn btn-secondary" onClick={() => setDashboardOpen(true)}>
                    {user?.is_admin ? "Admin Hub" : "Hub"}
                  </button>
                  <button onClick={handleLogout} className="btn btn-primary">Log out</button>
                </>
            )}
          </div>
          <button className={`hamburger ${drawerOpen ? 'open' : ''}`} onClick={() => setDrawerOpen(!drawerOpen)}>
            <span></span><span></span><span></span>
          </button>
        </div>
      </nav>

      {/* Mobile Drawer */}
      <div className={`mobile-drawer ${drawerOpen ? 'open' : ''}`}>
        <a href="#product" onClick={() => setDrawerOpen(false)}>Product</a>
        <a href="#how-it-works" onClick={() => setDrawerOpen(false)}>How it Works</a>
        <a href="#pricing" onClick={() => setDrawerOpen(false)}>Pricing</a>
        <a href="#results" onClick={() => setDrawerOpen(false)}>Results</a>
        <div className="drawer-actions">
          {!loggedIn ? (
              <>
                <button onClick={() => openAuth('login')} className="btn btn-secondary">Log In</button>
                <button onClick={() => openAuth('signup')} className="btn btn-primary">Sign Up</button>
              </>
          ) : (
              <>
                <button onClick={() => { setDashboardOpen(true); setDrawerOpen(false); }} className="btn btn-secondary">
                  {user?.is_admin ? "Admin Hub" : "Hub"}
                </button>
                <button onClick={handleLogout} className="btn btn-primary">Log out</button>
              </>
          )}
        </div>
      </div>

      <AuthModal 
        isOpen={authModalOpen} 
        mode={authMode} 
        onClose={() => setAuthModalOpen(false)} 
        onAuthSuccess={() => { 
          setAuthModalOpen(false); 
          setLoggedIn(true); 
          // Re-fetch user on success
          fetch(`${process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'}/api/v1/security/auth/me`)
            .then(res => res.json())
            .then(data => setUser(data));
          setDashboardOpen(true);
        }} 
      />

      {dashboardOpen && (
        <div className="modal-overlay active" onClick={(e) => { if (e.target === e.currentTarget) setDashboardOpen(false); }}>
          <div className="modal">
             <div className="hub">
                <h3 style={{ marginBottom: '8px' }}>Signal Hub</h3>
                <p style={{ color: 'var(--text-muted)', marginBottom: '24px' }}>Monitor your real-time performance and savings.</p>
                
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '24px' }}>
                  <div style={{ background: 'var(--surface-bright)', padding: '16px', borderRadius: '12px', border: '1px solid var(--card-border)' }}>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-dim)' }}>Usage</div>
                    <div style={{ fontSize: '24px', fontWeight: 800 }}>0</div>
                  </div>
                  <div style={{ background: 'var(--surface-bright)', padding: '16px', borderRadius: '12px', border: '1px solid var(--card-border)' }}>
                    <div style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-dim)' }}>Savings</div>
                    <div style={{ fontSize: '24px', fontWeight: 800 }}>₹0</div>
                  </div>
                </div>

                <div style={{ background: 'var(--bg)', border: '1px solid var(--card-border)', padding: '16px', borderRadius: '12px', fontFamily: 'var(--font-mono)', fontSize: '13px', marginBottom: '24px', wordBreak: 'break-all' }}>
                  ********************
                </div>

                <div style={{ display: 'flex', gap: '12px' }}>
                  <button onClick={() => setDashboardOpen(false)} className="btn btn-secondary" style={{ flex: 1 }}>Close</button>
                  <button onClick={handleLogout} className="btn btn-secondary" style={{ flex: 1 }}>Logout</button>
                </div>
              </div>
          </div>
        </div>
      )}
    </>
  );
}
