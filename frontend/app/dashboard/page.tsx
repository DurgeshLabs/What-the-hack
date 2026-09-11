"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Forecast,
  Overview,
  clearSession,
  getForecast,
  getOverview,
  getSession,
  isUnauthorized,
  saveForecast,
} from "@/lib/api";

const badge: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-800",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

const mitreStages = [
  { stage: "Reconnaissance", source: "PortScan / reconnaissance", color: "bg-sky-500" },
  { stage: "Initial Access", source: "FTP/SSH Patator, web brute force, Heartbleed", color: "bg-amber-500" },
  { stage: "Lateral Movement", source: "Infiltration", color: "bg-violet-500" },
  { stage: "Command & Control", source: "Botnet", color: "bg-fuchsia-500" },
  { stage: "Exfiltration / Impact", source: "DoS / DDoS harmful-impact bucket", color: "bg-rose-500" },
];

function Line({ values, color = "#6366f1" }: { values: number[]; color?: string }) {
  if (!values.length) return null;
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const span = Math.max(max - min, 1);
  const points = values
    .map((value, index) => `${(index / Math.max(values.length - 1, 1)) * 100},${90 - ((value - min) / span) * 76}`)
    .join(" ");

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-52 w-full overflow-visible">
      <path d="M0 90 H100" stroke="#e2e8f0" strokeWidth="1" />
      <polyline points={points} fill="none" stroke={color} strokeWidth="2.5" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default function DashboardPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const session = getSession();
  const sourceId = typeof window === "undefined" ? null : localStorage.getItem("wth_source_id");

  useEffect(() => {
    if (!session || !sourceId) return;
    getOverview(session.access_token, sourceId)
      .then(setOverview)
      .catch((requestError) => {
        if (isUnauthorized(requestError)) {
          clearSession();
          window.location.href = "/login";
          return;
        }
        setError(requestError.message);
      });
    getForecast(session.access_token, sourceId).then(setForecast).catch(() => undefined);
  }, [session?.access_token, sourceId]);

  async function saveAlert() {
    if (!session || !sourceId) return;
    setSaving(true);
    try {
      const saved = await saveForecast(session.access_token, sourceId);
      window.location.href = `/alerts/${saved.alert_id}`;
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Could not save forecast");
    } finally {
      setSaving(false);
    }
  }

  if (!session) return <Empty title="Sign in to view live traffic" detail="The dashboard uses your analyst session to read uploaded data." href="/login" action="Sign in" />;
  if (!sourceId) return <Empty title="No traffic source selected" detail="Upload a normalized traffic CSV to create a 60-second feature timeline." href="/upload" action="Upload traffic" />;
  if (error) return <div className="rounded-xl border border-red-200 bg-red-50 p-5 text-red-800">Dashboard unavailable: {error}</div>;
  if (!overview) return <p className="text-slate-500">Loading your traffic timeline…</p>;

  const traffic = overview.traffic.slice(-60);
  const peak = forecast?.risk_timeline.reduce((current, point) => current.risk_score > point.risk_score ? current : point);
  const stageTransitions = forecast?.risk_timeline.filter((point, index, timeline) => index === 0 || point.stage !== timeline[index - 1].stage) ?? [];
  const projectedStage = peak?.stage ?? forecast?.risk_timeline[0]?.stage ?? "Unknown";

  return (
    <div className="space-y-6">
      <section className="flex flex-col justify-between gap-4 rounded-2xl bg-slate-950 p-7 text-white md:flex-row md:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[.18em] text-indigo-300">Live forecasting workspace</p>
          <h2 className="mt-2 text-3xl font-semibold">Network risk, before it becomes an incident.</h2>
          <p className="mt-2 max-w-2xl text-sm text-slate-300">Source {sourceId.slice(0, 8)} · 60-second behavioural windows · next 5 minutes</p>
        </div>
        <Link href="/upload" className="rounded-lg bg-white px-4 py-2 text-sm font-semibold text-slate-900">Upload new traffic</Link>
      </section>

      <section className="grid gap-4 md:grid-cols-4">
        <Card label="Feature windows" value={String(overview.window_count)} hint="60-second snapshots" />
        <Card label="Flows observed" value={String(traffic.reduce((sum, point) => sum + point.flows, 0))} hint="in displayed timeline" />
        <Card label="Forecast status" value={forecast ? "Ready" : overview.model_ready ? "Need 10 windows" : "Artifact offline"} hint={forecast ? "world model running" : "upload more traffic or mount artifact"} />
        <Card label="Peak forecast risk" value={peak ? `${Math.round(peak.risk_score * 100)}%` : "—"} hint={peak?.stage ?? "no forecast yet"} accent={forecast?.peak_risk_level} />
      </section>

      <section className="grid gap-6 lg:grid-cols-5">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-3">
          <div className="flex justify-between">
            <div><h3 className="font-semibold text-slate-900">Observed traffic volume</h3><p className="text-sm text-slate-500">Packets per 60-second window</p></div>
            <span className="text-sm text-slate-500">{traffic.length} windows</span>
          </div>
          <Line values={traffic.map((point) => point.packets)} />
          <div className="flex justify-between text-xs text-slate-400"><span>{traffic[0] ? new Date(traffic[0].timestamp).toLocaleTimeString() : ""}</span><span>Now</span></div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm lg:col-span-2">
          <h3 className="font-semibold text-slate-900">Forecasted risk</h3><p className="mb-4 text-sm text-slate-500">Five-minute model projection</p>
          {forecast ? <><Line values={forecast.risk_timeline.map((point) => point.risk_score * 100)} color="#ef4444" /><div className="flex items-center justify-between"><span className={`rounded-full px-3 py-1 text-xs font-semibold ${badge[forecast.peak_risk_level]}`}>{forecast.peak_risk_level.toUpperCase()}</span><button onClick={saveAlert} disabled={saving} className="rounded-lg bg-indigo-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">{saving ? "Saving…" : "Save as alert"}</button></div></> : <p className="rounded-lg bg-slate-50 p-4 text-sm text-slate-500">A forecast appears once the model artifact is available and at least 10 windows are built.</p>}
        </div>
      </section>

      {forecast && <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-900">Forecasted attack stage</h3>
          <p className="mt-1 text-sm text-slate-500">A coarse, MITRE-aligned progression category—not exact technique attribution.</p>
          <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-[.14em] text-indigo-600">Five-minute verdict</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{projectedStage}</p>
            <p className="mt-1 text-sm text-slate-600">{stageTransitions.length === 1 ? "Sustained across all five forecast windows; no stage transition is predicted." : `${stageTransitions.length} stage changes are predicted across the five-minute projection.`}</p>
          </div>
          <div className="mt-4 space-y-3">{forecast.risk_timeline.map((point) => <div key={point.step} className="flex items-center gap-3 text-sm"><span className="w-14 text-slate-500">+{point.step} min</span><div className="h-2 flex-1 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-indigo-500" style={{ width: `${point.risk_score * 100}%` }} /></div><span className="w-12 text-right font-medium text-slate-700">{Math.round(point.risk_score * 100)}%</span></div>)}</div>
          {stageTransitions.length > 1 && <p className="mt-4 border-t border-slate-100 pt-4 text-sm text-slate-600">Stage changes: {stageTransitions.map((point) => `+${point.step} min ${point.stage ?? "Unknown"}`).join(" → ")}</p>}
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-900">What influenced this forecast</h3>
          <div className="mt-4 space-y-3">{forecast.top_feature_contributors.slice(0, 5).map((item) => <div key={item.feature}><div className="flex justify-between text-sm"><span className="text-slate-700">{item.feature.replaceAll("_", " ")}</span><span className="text-slate-500">{Math.round(item.contribution * 100)}%</span></div><div className="mt-1 h-2 rounded-full bg-slate-100"><div className="h-2 rounded-full bg-indigo-500" style={{ width: `${Math.max(3, item.contribution * 100)}%` }} /></div></div>)}</div>
        </div>
      </section>}

      <section className="rounded-2xl border border-indigo-100 bg-indigo-50/60 p-6 shadow-sm">
        <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-end"><div><p className="text-xs font-semibold uppercase tracking-[.16em] text-indigo-600">Model reference</p><h3 className="mt-1 text-xl font-semibold text-slate-900">MITRE-aligned stage mapping</h3></div><p className="max-w-xl text-sm text-slate-600">The model forecasts a coarse attack-progression category from flow behaviour. Analysts must validate it with endpoint, identity, and packet evidence; it does not assert an exact ATT&amp;CK technique.</p></div>
        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-5">{mitreStages.map((item) => <div key={item.stage} className="rounded-xl border border-white bg-white p-4"><span className={`mb-3 block h-1.5 w-10 rounded-full ${item.color}`} /><h4 className="font-semibold text-slate-900">{item.stage}</h4><p className="mt-1 text-xs leading-5 text-slate-500">Training label: {item.source}</p></div>)}</div>
        <p className="mt-4 text-xs text-slate-500">Benign traffic is the sixth model class. DoS/DDoS is displayed in a shared late-stage Impact bucket; it is not presented as proof of data exfiltration.</p>
      </section>
    </div>
  );
}

function Card({ label, value, hint, accent }: { label: string; value: string; hint: string; accent?: string }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><p className="text-sm text-slate-500">{label}</p><p className={`mt-2 text-2xl font-semibold ${accent === "critical" ? "text-red-600" : "text-slate-900"}`}>{value}</p><p className="mt-1 text-xs text-slate-400">{hint}</p></div>;
}

function Empty({ title, detail, href, action }: { title: string; detail: string; href: string; action: string }) {
  return <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center"><h2 className="text-2xl font-semibold text-slate-900">{title}</h2><p className="mx-auto mt-2 max-w-lg text-slate-500">{detail}</p><Link href={href} className="mt-6 inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white">{action}</Link></section>;
}
