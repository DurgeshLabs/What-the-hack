// app/alerts/page.tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getAlerts } from "@/lib/api";

const severityColor: Record<string, string> = {
  low: "bg-risk-low",
  medium: "bg-risk-medium",
  high: "bg-risk-high",
  critical: "bg-risk-critical",
};

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [sortBy, setSortBy] = useState<"score" | "time">("score");

  useEffect(() => {
    getAlerts().then(setAlerts);
  }, []);

  const sorted = [...alerts].sort((a, b) =>
    sortBy === "score" ? b.score - a.score : 0
  );

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">Alerts</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setSortBy("score")}
            className={`rounded px-3 py-1 text-sm ${
              sortBy === "score" ? "bg-blue-600 text-white" : "bg-white text-gray-600"
            }`}
          >
            Sort by risk
          </button>
          <button
            onClick={() => setSortBy("time")}
            className={`rounded px-3 py-1 text-sm ${
              sortBy === "time" ? "bg-blue-600 text-white" : "bg-white text-gray-600"
            }`}
          >
            Sort by recency
          </button>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg bg-white shadow">
        <table className="w-full text-left">
          <thead className="bg-gray-50 text-sm text-gray-500">
            <tr>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Host</th>
              <th className="px-4 py-3">Risk Score</th>
              <th className="px-4 py-3">Time</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((alert) => (
              <tr key={alert.id} className="border-t border-gray-100">
                <td className="px-4 py-3">
                  <span
                    className={`rounded px-2 py-1 text-xs font-medium text-white ${severityColor[alert.severity]}`}
                  >
                    {alert.severity}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-700">{alert.host}</td>
                <td className="px-4 py-3 font-semibold text-gray-800">{alert.score}</td>
                <td className="px-4 py-3 text-gray-500">{alert.time}</td>
                <td className="px-4 py-3">
                  <Link
                    href={`/alerts/${alert.id}`}
                    className="text-sm text-blue-600 hover:underline"
                  >
                    View →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// app/alerts/[id]/page.tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getAlertDetail } from "@/lib/api";

const severityColor: Record<string, string> = {
  low: "bg-risk-low",
  medium: "bg-risk-medium",
  high: "bg-risk-high",
  critical: "bg-risk-critical",
};

export default function AlertDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const [alert, setAlert] = useState<any>(null);

  useEffect(() => {
    getAlertDetail(id).then(setAlert);
  }, [id]);

  if (!alert) return <p className="p-8">Loading alert...</p>;

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <div className="mb-6 flex items-center gap-3">
        <span
          className={`rounded px-3 py-1 text-sm font-medium text-white ${severityColor[alert.severity]}`}
        >
          {alert.severity.toUpperCase()}
        </span>
        <h1 className="text-2xl font-bold text-gray-800">
          Alert — {alert.host}
        </h1>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Left: main details */}
        <div className="col-span-2 space-y-6">
          <div className="rounded-lg bg-white p-6 shadow">
            <h2 className="mb-3 text-lg font-semibold text-gray-700">
              Predicted Attack
            </h2>
            <p className="text-xl font-bold text-gray-900">{alert.predictedAttack}</p>
            <p className="mt-1 text-sm text-gray-500">
              Forecast horizon: {alert.forecastHorizon}
            </p>
            <p className="mt-1 text-sm text-gray-500">
              Confidence: {(alert.confidence * 100).toFixed(0)}%
            </p>
          </div>

          <div className="rounded-lg bg-white p-6 shadow">
            <h2 className="mb-3 text-lg font-semibold text-gray-700">
              Why this was flagged
            </h2>
            <ul className="list-disc space-y-1 pl-5 text-gray-700">
              {alert.contributingFactors.map((f: string, i: number) => (
                <li key={i}>{f}</li>
              ))}
            </ul>
          </div>

          <div className="rounded-lg bg-white p-6 shadow">
            <h2 className="mb-3 text-lg font-semibold text-gray-700">
              Recommended Actions
            </h2>
            <ul className="list-disc space-y-1 pl-5 text-gray-700">
              {alert.recommendedActions.map((a: string, i: number) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right: risk score + mini chart placeholder */}
        <div className="space-y-6">
          <div className="rounded-lg bg-white p-6 text-center shadow">
            <p className="text-sm text-gray-500">Risk Score</p>
            <p className="text-4xl font-bold text-gray-900">{alert.score}</p>
          </div>

          <div className="rounded-lg bg-white p-6 shadow">
            <p className="mb-2 text-sm font-medium text-gray-600">
              Traffic before → after
            </p>
            <p className="text-xs text-gray-400">
              Before: {alert.trafficBefore.join(", ")}
            </p>
            <p className="text-xs text-gray-400">
              After: {alert.trafficAfter.join(", ")}
            </p>
            <p className="mt-2 text-xs italic text-gray-400">
              (real mini-chart comes later — Recharts sparkline)
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
