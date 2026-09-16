"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { SeverityBadge, StatusBadge, TrustBadges } from "@/components/AlertBadges";
import { AlertCard, AlertStatus, RiskLevel, getSession, isUnauthorized, listAlerts } from "@/lib/api";

const STATUSES: AlertStatus[] = ["open", "acknowledged", "investigating", "resolved"];
const SEVERITIES: RiskLevel[] = ["critical", "high", "medium", "low"];
const PAGE_SIZE = 20;

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<AlertCard[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [status, setStatus] = useState<AlertStatus | "">("");
  const [severity, setSeverity] = useState<RiskLevel | "">("");
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);

  const session = getSession();
  const token = session?.access_token;

  const load = useCallback(
    async (before?: string | null) => {
      if (!token) return;
      try {
        const page = await listAlerts(token, {
          status: status || undefined,
          severity: severity || undefined,
          limit: PAGE_SIZE,
          before: before ?? undefined,
        });
        setAlerts((current) => (before ? [...current, ...page.items] : page.items));
        setCursor(page.next_cursor);
        setState("ready");
      } catch (caught) {
        setError(isUnauthorized(caught) ? "Your session expired. Sign in again." : (caught as Error).message);
        setState("error");
      }
    },
    [token, status, severity],
  );

  useEffect(() => {
    setState("loading");
    load(null);
  }, [load]);

  if (!session) return <p className="text-slate-500">Sign in to view saved alerts.</p>;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[.18em] text-indigo-600">Investigation queue</p>
          <h2 className="mt-1 text-3xl font-semibold text-slate-900">Forecast alerts</h2>
        </div>
        <Link href="/dashboard" className="text-sm font-semibold text-indigo-600">
          Open dashboard
        </Link>
      </header>

      <div className="flex flex-wrap gap-3 rounded-xl border border-slate-200 bg-white p-4">
        <label className="text-sm">
          <span className="mr-2 text-slate-500">Status</span>
          <select value={status} onChange={(event) => setStatus(event.target.value as AlertStatus | "")} className="rounded border border-slate-300 px-2 py-1">
            <option value="">All</option>
            {STATUSES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          <span className="mr-2 text-slate-500">Severity</span>
          <select value={severity} onChange={(event) => setSeverity(event.target.value as RiskLevel | "")} className="rounded border border-slate-300 px-2 py-1">
            <option value="">All</option>
            {SEVERITIES.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        {(status || severity) && (
          <button
            type="button"
            onClick={() => {
              setStatus("");
              setSeverity("");
            }}
            className="text-sm font-semibold text-indigo-600"
          >
            Clear filters
          </button>
        )}
      </div>

      {state === "error" && <p className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</p>}
      {state === "loading" && <p className="text-sm text-slate-500">Loading alerts…</p>}

      {state === "ready" && alerts.length === 0 && (
        <section className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
          <h3 className="text-xl font-semibold">No alerts match</h3>
          <p className="mt-2 text-sm text-slate-500">
            {status || severity ? "Try clearing the filters." : "Run a forecast from the dashboard and save it here for investigation."}
          </p>
        </section>
      )}

      {alerts.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-4">Severity</th>
                <th className="px-5 py-4">Status</th>
                <th className="px-5 py-4">Forecast</th>
                <th className="px-5 py-4">Risk</th>
                <th className="px-5 py-4">Created</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr key={alert.id} className="border-t border-slate-100">
                  <td className="px-5 py-4">
                    <SeverityBadge severity={alert.severity} />
                  </td>
                  <td className="px-5 py-4">
                    <StatusBadge status={alert.status} />
                  </td>
                  <td className="px-5 py-4">
                    <p className="font-medium text-slate-900">{alert.title}</p>
                    <p className="mt-1 text-slate-500">
                      {alert.predicted_stage ?? "Stage unavailable"}
                      {alert.target_host ? ` · ${alert.target_host.ip_address}` : ""}
                    </p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      <TrustBadges alert={alert} />
                    </div>
                  </td>
                  <td className="px-5 py-4 font-semibold text-slate-800">{Math.round(alert.risk_score)}/100</td>
                  <td className="px-5 py-4 text-slate-500">{new Date(alert.created_at).toLocaleString()}</td>
                  <td className="px-5 py-4">
                    <Link href={`/alerts/${alert.id}`} className="font-semibold text-indigo-600">
                      Inspect
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {cursor && (
        <button type="button" onClick={() => load(cursor)} className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700">
          Load more
        </button>
      )}
    </div>
  );
}
