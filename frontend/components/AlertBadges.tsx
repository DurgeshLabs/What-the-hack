"use client";

import type { AlertStatus, RiskLevel } from "@/lib/api";

const SEVERITY: Record<RiskLevel, string> = {
  low: "bg-emerald-100 text-emerald-800",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
};

const STATUS: Record<AlertStatus, string> = {
  open: "bg-slate-200 text-slate-800",
  acknowledged: "bg-sky-100 text-sky-800",
  investigating: "bg-indigo-100 text-indigo-800",
  resolved: "bg-emerald-100 text-emerald-800",
};

export function SeverityBadge({ severity }: { severity: RiskLevel }) {
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${SEVERITY[severity] ?? SEVERITY.low}`}>{severity.toUpperCase()}</span>;
}

export function StatusBadge({ status }: { status: AlertStatus }) {
  return <span className={`rounded-full px-2.5 py-1 text-xs font-semibold capitalize ${STATUS[status] ?? STATUS.open}`}>{status}</span>;
}

/**
 * Honesty markers. A high score from the fallback, or on traffic unlike the training
 * baseline, must never read like a confirmed incident.
 */
export function TrustBadges({ alert }: { alert: { is_fallback: boolean; is_uncertain: boolean; is_ood: boolean } }) {
  const flags: { label: string; title: string; className: string }[] = [];
  if (alert.is_fallback) {
    flags.push({
      label: "Rule fallback",
      title: "Produced by the rule-based fallback, not the trained model.",
      className: "bg-violet-100 text-violet-800",
    });
  }
  if (alert.is_uncertain) {
    flags.push({
      label: "Low confidence",
      title: "The model is not confident. Corroborate before acting.",
      className: "bg-yellow-100 text-yellow-900",
    });
  }
  if (alert.is_ood) {
    flags.push({
      label: "Unseen pattern",
      title: "This traffic is unlike the model's training baseline, so a false positive is likely.",
      className: "bg-rose-100 text-rose-800",
    });
  }
  if (!flags.length) return null;
  return (
    <>
      {flags.map((flag) => (
        <span key={flag.label} title={flag.title} className={`rounded-full px-2.5 py-1 text-xs font-semibold ${flag.className}`}>
          {flag.label}
        </span>
      ))}
    </>
  );
}
