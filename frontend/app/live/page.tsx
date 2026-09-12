"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { TrafficSource, getSession, listTrafficSources } from "@/lib/api";

export default function LiveSensorPage() {
  const [sources, setSources] = useState<TrafficSource[]>([]);
  const [error, setError] = useState<string | null>(null);
  const session = getSession();

  function refreshSources() {
    if (!session) return;
    setError(null);
    listTrafficSources(session.access_token)
      .then((items) => setSources(items.filter((item) => item.source_type === "zeek_live")))
      .catch((reason) => setError(reason instanceof Error ? reason.message : "Could not load live sensors"));
  }

  useEffect(() => { refreshSources(); }, [session?.access_token]);

  function openSource(source: TrafficSource) {
    localStorage.setItem("wth_source_id", source.id);
    window.location.href = "/dashboard";
  }

  if (!session) return <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center"><h2 className="text-2xl font-semibold text-slate-900">Sign in to connect a live sensor</h2><Link href="/login" className="mt-6 inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">Sign in</Link></section>;

  return <div className="mx-auto max-w-3xl space-y-6">
    <section className="rounded-2xl bg-slate-950 p-7 text-white"><p className="text-xs font-semibold uppercase tracking-[.18em] text-indigo-300">Permitted local telemetry</p><h2 className="mt-2 text-3xl font-semibold">Live Zeek connection sensor</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">Zeek observes connection metadata on a network you are authorised to monitor. The local adapter sends timestamps, addresses, ports, protocol, packets, bytes and connection state—never packet payloads—to the same 60-second feature pipeline used by CSV replay.</p></section>
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><h3 className="font-semibold text-slate-900">Start the local bridge</h3><ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-6 text-slate-600"><li>Start the Docker application stack.</li><li>Start Zeek on an interface you are permitted to monitor.</li><li>Run <code className="rounded bg-slate-100 px-1.5 py-0.5">python3 -m ai.ingestion.zeek_live_adapter</code> from the project root.</li><li>Click Refresh, then open the detected source below.</li></ol><p className="mt-4 text-xs text-slate-500">Exact commands and safety notes: <code>docs/demo/live-zeek-ingestion.md</code>.</p></section>
    <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><div className="flex items-center justify-between gap-3"><div><h3 className="font-semibold text-slate-900">Detected live sources</h3><p className="text-sm text-slate-500">Refresh after the adapter prints its first successful batch.</p></div><button onClick={refreshSources} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-semibold text-slate-700">Refresh</button></div>{error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}{!error && sources.length === 0 && <p className="mt-5 rounded-lg bg-slate-50 p-4 text-sm text-slate-500">No live source yet. Start Zeek and the adapter, then refresh this page.</p>}<div className="mt-4 space-y-3">{sources.map((source) => <div key={source.id} className="flex flex-col justify-between gap-3 rounded-xl border border-indigo-100 bg-indigo-50 p-4 sm:flex-row sm:items-center"><div><p className="font-semibold text-slate-900">{source.name}</p><p className="text-xs text-slate-600">Created {new Date(source.created_at).toLocaleString()}</p></div><button onClick={() => openSource(source)} className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white">Open dashboard</button></div>)}</div></section>
  </div>;
}
