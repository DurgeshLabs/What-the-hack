"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { clearSession, getSession, logout } from "@/lib/api";

export function SessionNav() {
  // Re-evaluate local session data whenever Next.js changes route. This keeps the
  // visible action correct immediately after the login page stores a new token.
  usePathname();
  const session = getSession();

  async function signOut() {
    try {
      if (session) await logout(session.access_token);
    } finally {
      clearSession();
      localStorage.removeItem("wth_source_id");
      window.location.href = "/login";
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
