"use client";

import { useEffect, useState } from "react";
import {
  AuditEntry,
  SystemOverview,
  getAuditTrail,
  getSession,
  getSystemOverview,
  isUnauthorized,
} from "@/lib/api";

const COUNT_LABELS: Record<string, string> = {
  users: "Users",
  traffic_sources: "Traffic sources",
  ingestion_jobs: "Ingestion jobs",
  raw_flows: "Raw flows",
  traffic_windows: "Traffic windows",
  predictions: "Predictions",
  alerts: "Alerts",
};

export default function AdminPage() {
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  const session = getSession();
  const token = session?.access_token;
  const isAdmin = session?.user.role === "admin";

  useEffect(() => {
    if (!token || !isAdmin) return;
    Promise.all([getSystemOverview(token), getAuditTrail(token, 25)])
      .then(([system, trail]) => {
        setOverview(system);
        setAudit(trail.items);
        setError(null);
      })
      .catch((caught) =>
        setError(isUnauthorized(caught) ? "Your session expired. Sign in again." : (caught as Error).message),
      );
  }, [token, isAdmin]);

  if (!session) return <p className="text-slate-500">Sign in to view the admin panel.</p>;
  if (!isAdmin) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-8">
        <h2 className="text-xl font-semibold text-slate-900">Admin access required</h2>
        <p className="mt-2 text-sm text-slate-600">
          You are signed in as <span className="font-semibold">{session.user.role}</span>. Model and user
          administration is restricted to the admin role.
        </p>
      </div>
    );
  }
  if (error) return <p className="rounded-lg bg-red-50 p-4 text-sm text-red-700">{error}</p>;
  if (!overview) return <p className="text-slate-500">Loading system state…</p>;

  const config = overview.configuration;
  const warnings: string[] = [];
  if (config.uses_default_jwt_secret) warnings.push("JWT_SECRET_KEY is the built-in development default. Set a random secret before any shared deployment.");
  if (!config.checkpoint_present) warnings.push("No trained model artifact is mounted, so forecasts are coming from the rule-based fallback.");
  if (!config.rate_limit_enabled) warnings.push("Rate limiting is disabled.");

  return (
    <div className="space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[.18em] text-indigo-600">Administration</p>
        <h2 className="mt-1 text-3xl font-semibold text-slate-900">System</h2>
      </header>

      {warnings.length > 0 && (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <h3 className="font-semibold text-amber-900">Attention</h3>
          <ul className="mt-2 space-y-1 text-sm text-amber-900">
            {warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </section>
      )}

      <section className="grid gap-3 sm:grid-cols-3 lg:grid-cols-4">
        {Object.entries(overview.counts).map(([key, value]) => (
          <div key={key} className="rounded-xl border border-slate-200 bg-white p-4">
            <p className="text-xs uppercase tracking-wide text-slate-500">{COUNT_LABELS[key] ?? key}</p>
            <p className="mt-1 text-2xl font-semibold text-slate-900">{value.toLocaleString()}</p>
          </div>
        ))}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-900">Registered models</h3>
          {overview.models.length === 0 ? (
            <p className="mt-3 text-sm text-slate-500">No model has produced a prediction yet.</p>
          ) : (
            <table className="mt-4 w-full text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="pb-2">Name</th>
                  <th className="pb-2">Version</th>
                  <th className="pb-2">Schema</th>
                  <th className="pb-2">Active</th>
                </tr>
              </thead>
              <tbody>
                {overview.models.map((model) => (
                  <tr key={`${model.name}@${model.version}`} className="border-t border-slate-100">
                    <td className="py-2 font-medium text-slate-800">{model.name}</td>
                    <td className="py-2 font-mono text-xs text-slate-600">{model.version}</td>
                    <td className="py-2 text-slate-600">{model.feature_schema_version}</td>
                    <td className="py-2">{model.is_active ? "yes" : "no"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p className="mt-4 text-xs text-slate-500">
            {overview.fallback_predictions} of {overview.counts.predictions ?? 0} predictions came from the rule-based
            fallback.
          </p>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-900">Accounts</h3>
          <table className="mt-4 w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="pb-2">Email</th>
                <th className="pb-2">Role</th>
                <th className="pb-2">Last login</th>
              </tr>
            </thead>
            <tbody>
              {overview.users.map((account) => (
                <tr key={account.email} className="border-t border-slate-100">
                  <td className="py-2 text-slate-800">{account.email}</td>
                  <td className="py-2 capitalize text-slate-600">{account.role}</td>
                  <td className="py-2 text-slate-500">
                    {account.last_login_at ? new Date(account.last_login_at).toLocaleString() : "never"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-900">Configuration</h3>
          <dl className="mt-4 space-y-2 text-sm">
            {Object.entries(config).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-4 border-b border-slate-100 pb-1">
                <dt className="text-slate-500">{key.replaceAll("_", " ")}</dt>
                <dd className="font-medium text-slate-800">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </div>

        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <h3 className="font-semibold text-slate-900">Alerts by status</h3>
          <dl className="mt-4 space-y-2 text-sm">
            {Object.entries(overview.alerts_by_status).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-4 border-b border-slate-100 pb-1">
                <dt className="capitalize text-slate-500">{key}</dt>
                <dd className="font-medium text-slate-800">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <h3 className="font-semibold text-slate-900">Audit trail</h3>
        {audit.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">Nothing recorded yet.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="pb-2">When</th>
                  <th className="pb-2">Actor</th>
                  <th className="pb-2">Action</th>
                  <th className="pb-2">Resource</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((entry) => (
                  <tr key={entry.id} className="border-t border-slate-100">
                    <td className="py-2 text-slate-500">{new Date(entry.created_at).toLocaleString()}</td>
                    <td className="py-2 text-slate-700">{entry.actor_email ?? "system"}</td>
                    <td className="py-2 font-mono text-xs text-slate-800">{entry.action}</td>
                    <td className="py-2 text-slate-500">{entry.resource_type ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
