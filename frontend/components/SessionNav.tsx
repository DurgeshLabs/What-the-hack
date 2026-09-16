"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import { TokenResponse, clearSession, getSession, logout } from "@/lib/api";

export function SessionNav() {
  const pathname = usePathname();
  const [session, setSession] = useState<TokenResponse | null>(null);

  // Session storage is browser-only. Keeping it in state and listening for our
  // explicit event prevents a stale label after login, logout, or route changes.
  useEffect(() => {
    const syncSession = () => setSession(getSession());
    syncSession();
    window.addEventListener("wth-session-changed", syncSession);
    return () => window.removeEventListener("wth-session-changed", syncSession);
  }, [pathname]);

  async function signOut() {
    try {
      if (session) await logout(session.access_token);
    } finally {
      clearSession();
      localStorage.removeItem("wth_source_id");
      window.location.assign("/login");
    }
  }

  return (
    <nav className="flex items-center gap-4 text-sm text-slate-600">
      <Link href="/dashboard" className="hover:text-slate-900">Dashboard</Link>
      <Link href="/alerts" className="hover:text-slate-900">Alerts</Link>
      <Link href="/upload" className="hover:text-slate-900">Upload</Link>
      <Link href="/live" className="hover:text-slate-900">Live sensor</Link>
      {session ? <>
        <span className="hidden text-xs text-slate-400 md:inline">{session.user.email}</span>
        <button onClick={signOut} className="font-semibold text-indigo-600 hover:text-indigo-800">Sign out</button>
      </> : <Link href="/login" className="font-semibold text-indigo-600">Sign in</Link>}
    </nav>
  );
}
