"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { Menu, X, Zap } from "lucide-react";
import Link from "next/link";
import AuthModal from "./AuthModal";
import { cn } from "@/lib/cn";

type AuthUser = {
  email?: string;
  team_id?: string;
  is_admin?: boolean;
};

export default function Navigation() {
  const [isScrolled, setIsScrolled] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "signup">("login");
  const [loggedIn, setLoggedIn] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const pathname = usePathname();
  const isLandingPage = pathname === "/";

  useEffect(() => {
    const onScroll = () => setIsScrolled(window.scrollY > 8);
    window.addEventListener("scroll", onScroll);
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    const checkSession = async () => {
      try {
        const token = localStorage.getItem("vp_token");
        if (!token) return;

        if (token === "mock-admin-token") {
          setUser({ email: "admin@vantix.com", is_admin: true });
          setLoggedIn(true);
          return;
        }

        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE || "https://vantix-wjsk.onrender.com"}/api/v1/security/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) return;
        const data = (await response.json()) as AuthUser;
        
        setUser(data);
        setLoggedIn(true);
      } catch {
        // noop
      }
    };

    checkSession();
  }, []);

  const openAuth = (mode: "login" | "signup") => {
    setAuthMode(mode);
    setAuthModalOpen(true);
    setDrawerOpen(false);
  };

  const handleLogout = async () => {
    try {
      const token = localStorage.getItem("vp_token");
      await fetch(`${process.env.NEXT_PUBLIC_API_BASE || "https://vantix-wjsk.onrender.com"}/api/v1/security/auth/logout`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
    } catch {
      // noop
    }
    localStorage.removeItem("vp_token");
    setUser(null);
    setLoggedIn(false);
  };

  return (
    <>
      <nav
        className={cn(
          "fixed inset-x-0 top-0 z-50 border-b transition-all duration-200",
          isScrolled || !isLandingPage ? "border-zinc-200 bg-[var(--card)]/95 backdrop-blur-xl shadow-sm" : "border-transparent bg-transparent",
        )}
      >
        <div className="container flex h-16 xl:h-20 items-center justify-between">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="flex items-center justify-center text-zinc-900">
              <Zap className="h-6 w-6 stroke-[2.5px]" fill="currentColor" />
            </div>
            <span className="text-xl font-bold tracking-tight text-zinc-900">Vantix</span>
          </Link>

          <div className="hidden items-center gap-8 text-sm font-medium text-zinc-500 lg:flex">
            <Link href="/#product" className="hover:text-zinc-900 transition-colors">Product</Link>
            <Link href="/#docs" className="hover:text-zinc-900 transition-colors">Docs</Link>
            <Link href="/#pricing" className="hover:text-zinc-900 transition-colors">Pricing</Link>
          </div>

          <div className="hidden items-center gap-4 lg:flex">
            {!loggedIn ? (
              <>
                <button onClick={() => openAuth("login")} className="px-4 py-2 text-sm font-semibold text-zinc-600 hover:text-zinc-900 transition-colors">
                  Log in
                </button>
                <button
                  onClick={() => openAuth("signup")}
                  className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold !text-white hover:bg-zinc-800 transition-colors shadow-sm"
                >
                  Get started
                </button>
              </>
            ) : (
              <>
                <a
                  href={user?.is_admin ? "/dashboard/admin" : "/dashboard"}
                  className="rounded-lg border border-zinc-200 bg-white px-4 py-2 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors shadow-sm"
                >
                  {user?.is_admin ? "Admin Console" : "Dashboard"}
                </a>
                <button onClick={handleLogout} className="px-4 py-2 text-sm font-semibold text-zinc-600 hover:text-zinc-900 transition-colors">
                  Logout
                </button>
              </>
            )}
          </div>

          <button onClick={() => setDrawerOpen(true)} className="lg:hidden p-2 -mr-2 text-zinc-600 hover:text-zinc-900">
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </nav>

      <div
        className={cn(
          "fixed inset-0 z-[60] bg-zinc-900/20 backdrop-blur-sm transition-all duration-300",
          drawerOpen ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
        )}
      >
        <div className={cn(
          "ml-auto h-full w-full max-w-sm bg-white p-6 shadow-2xl transition-transform duration-300",
          drawerOpen ? "translate-x-0" : "translate-x-full"
        )}>
          <div className="mb-8 flex items-center justify-between">
            <span className="text-base font-semibold text-zinc-900">Menu</span>
            <button onClick={() => setDrawerOpen(false)} className="p-2 -mr-2 text-zinc-500 hover:text-zinc-900 rounded-full hover:bg-zinc-100">
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="space-y-6 text-sm font-medium text-zinc-600">
            <Link href="/#product" onClick={() => setDrawerOpen(false)} className="block hover:text-zinc-900 transition-colors">Product</Link>
            <Link href="/#docs" onClick={() => setDrawerOpen(false)} className="block hover:text-zinc-900 transition-colors">Docs</Link>
            <Link href="/#pricing" onClick={() => setDrawerOpen(false)} className="block hover:text-zinc-900 transition-colors">Pricing</Link>
          </div>

          <div className="mt-8 pt-8 border-t border-zinc-100 space-y-4">
            {!loggedIn ? (
              <>
                <button onClick={() => openAuth("login")} className="w-full rounded-lg border border-zinc-200 px-4 py-2.5 text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors shadow-sm">
                  Log in
                </button>
                <button onClick={() => openAuth("signup")} className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium !text-white hover:bg-zinc-800 transition-colors shadow-sm">
                  Get started
                </button>
              </>
            ) : (
              <>
                <a href="/dashboard" className="block w-full rounded-lg border border-zinc-200 px-4 py-2.5 text-center text-sm font-medium text-zinc-700 hover:bg-zinc-50 transition-colors shadow-sm">
                  Open dashboard
                </a>
                <button onClick={handleLogout} className="w-full rounded-lg text-red-600 bg-red-50 hover:bg-red-100 px-4 py-2.5 text-sm font-medium transition-colors">
                  Logout
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      <AuthModal
        isOpen={authModalOpen}
        mode={authMode}
        onClose={() => setAuthModalOpen(false)}
        onAuthSuccess={(data) => {
          if (data.token) {
            localStorage.setItem("vp_token", data.token);
            document.cookie = `vp_token=${data.token}; path=/; max-age=86400; SameSite=Lax`;
          }
          setAuthModalOpen(false);
          setLoggedIn(true);

          const token = data.token || localStorage.getItem("vp_token");
          if (!token) return;

          if (token === "mock-admin-token") {
            setUser({ email: "admin@vantix.com", is_admin: true });
            return;
          }

          fetch(`${process.env.NEXT_PUBLIC_API_BASE || "https://vantix-wjsk.onrender.com"}/api/v1/security/auth/me`, {
            headers: { Authorization: `Bearer ${token}` },
          })
            .then((res) => res.json())
            .then((payload: AuthUser) => {
              setUser(payload);
            })
            .catch(() => {
              // noop
            });
        }}
      />
    </>
  );
}
