"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { SeverityBadge, StatusBadge, TrustBadges } from "@/components/AlertBadges";
import {
  ALLOWED_TRANSITIONS,
  AlertDetail,
  AlertStatus,
  addAlertNote,
  getAlertDetail,
  getSession,
  isUnauthorized,
  updateAlertStatus,
} from "@/lib/api";

const ACTION_LABEL: Record<AlertStatus, string> = {
  open: "Reopen",
  acknowledged: "Acknowledge",
  investigating: "Start investigating",
  resolved: "Resolve",
};

export default function AlertDetailPage({ params }: { params: { id: string } }) {
  const [alert, setAlert] = useState<AlertDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");

  const session = getSession();
  const token = session?.access_token;
  const canTriage = session?.user.role === "admin" || session?.user.role === "analyst";

  const refresh = useCallback(async () => {
    if (!token) return;
    try {
      setAlert(await getAlertDetail(token, params.id));
      setError(null);
    } catch (caught) {
      setError(isUnauthorized(caught) ? "Your session expired. Sign in again." : (caught as Error).message);
    }
  }, [token, params.id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function move(next: AlertStatus) {
    if (!token) return;
    setBusy(true);
    try {
      setAlert(await updateAlertStatus(token, params.id, next, note.trim() || undefined));
      setNote("");
      setError(null);
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function comment() {
    if (!token || !note.trim()) return;
    setBusy(true);
    try {
      await addAlertNote(token, params.id, note.trim());
      setNote("");
      await refresh();
    } catch (caught) {
      setError((caught as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!session) return <p className="text-slate-500">Sign in to inspect this alert.</p>;
  if (error && !alert) return <p className="rounded-lg bg-red-50 p-4 text-red-700">{error}</p>;
  if (!alert) return <p className="text-slate-500">Loading saved forecast…</p>;

  const horizonMinutes = Math.max(
    1,
    Math.round((new Date(alert.forecast_window_end).getTime() - new Date(alert.forecast_window_start).getTime()) / 60000),
  );

  return (
    <div className="space-y-6">
      <Link href="/alerts" className="text-sm font-semibold text-indigo-600">
        Back to alerts
      </Link>

      {error && <p className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</p>}

      <section className="rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
        <div className="flex flex-wrap items-center gap-2">
          <SeverityBadge severity={alert.severity} />
          <StatusBadge status={alert.status} />
          <TrustBadges alert={alert} />
          <span className="text-sm text-slate-500">Saved {new Date(alert.created_at).toLocaleString()}</span>
        </div>
        <h2 className="mt-4 text-3xl font-semibold text-slate-900">{alert.title}</h2>
        <p className="mt-2 text-slate-600">{alert.summary}</p>

        <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Stat label="Peak risk" value={`${Math.round(alert.risk_score)}/100`} />
          <Stat label="Attack stage" value={alert.predicted_stage ?? "Unknown"} />
          <Stat label="Attack type" value={alert.predicted_attack_type ?? "Unknown"} />
          <Stat label="Confidence" value={`${Math.round(alert.confidence_score * 100)}%`} />
        </div>
        <p className="mt-4 text-sm text-slate-500">
          Forecast horizon: {horizonMinutes} minutes from {new Date(alert.forecast_window_start).toLocaleTimeString()}
          {alert.target_host ? ` · Busiest destination ${alert.target_host.ip_address}` : ""}
          {alert.resolved_at ? ` · Resolved ${new Date(alert.resolved_at).toLocaleString()}` : ""}
        </p>
      </section>

      {canTriage && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-900">Triage</h3>
          <p className="mt-1 text-sm text-slate-500">Every change is recorded in the timeline and the audit log.</p>
          <textarea
            value={note}
            onChange={(event) => setNote(event.target.value)}
            placeholder="Optional note, attached to whichever action you take next"
            rows={2}
            maxLength={2000}
            className="mt-4 w-full rounded-lg border border-slate-300 p-3 text-sm"
          />
          <div className="mt-3 flex flex-wrap gap-2">
            {ALLOWED_TRANSITIONS[alert.status].map((next) => (
              <button
                key={next}
                type="button"
                disabled={busy}
                onClick={() => move(next)}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
              >
                {ACTION_LABEL[next]}
              </button>
            ))}
            <button
              type="button"
              disabled={busy || !note.trim()}
              onClick={comment}
              className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50"
            >
              Add note only
            </button>
          </div>
        </section>
      )}

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-900">Why it was flagged</h3>
          <div className="mt-4 space-y-3">
            {alert.top_feature_contributors.length ? (
              alert.top_feature_contributors.map((item) => (
                <div key={item.feature}>
                  <div className="flex justify-between text-sm">
                    <span>{item.feature.replaceAll("_", " ")}</span>
                    <span className="text-slate-500">{Math.round(item.contribution * 100)}%</span>
                  </div>
                  <div className="mt-1 h-2 rounded-full bg-slate-100">
                    <div className="h-2 rounded-full bg-indigo-500" style={{ width: `${Math.max(3, item.contribution * 100)}%` }} />
                  </div>
                  {item.description && <p className="mt-1 text-xs text-slate-500">{item.description}</p>}
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No feature attribution was stored for this alert.</p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-900">Recommended next actions</h3>
          <ol className="mt-4 space-y-3 text-sm text-slate-700">
            {alert.recommended_actions.map((action, index) => (
              <li key={action} className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-xs font-semibold text-indigo-700">
                  {index + 1}
                </span>
                {action}
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="font-semibold text-slate-900">Investigation timeline</h3>
        {alert.events.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">Nothing recorded yet. Acknowledging this alert starts the trail.</p>
        ) : (
          <ol className="mt-4 space-y-4">
            {alert.events.map((event) => (
              <li key={event.id} className="flex gap-3 border-l-2 border-indigo-200 pl-4">
                <div>
                  <p className="text-sm font-medium text-slate-800">
                    {event.event_type === "comment"
                      ? "Note added"
                      : `Status changed${event.from_status ? ` from ${event.from_status}` : ""} to ${event.to_status}`}
                  </p>
                  <p className="text-xs text-slate-500">{new Date(event.created_at).toLocaleString()}</p>
                  {event.note && <p className="mt-1 text-sm text-slate-600">{event.note}</p>}
                </div>
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 font-semibold text-slate-900">{value}</p>
    </div>
  );
}
