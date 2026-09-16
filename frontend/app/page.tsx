import { SystemStatus } from "@/components/SystemStatus";
import Link from "next/link";

export default function HomePage() {
  return (
    <div className="space-y-8">
      <section className="rounded-lg border border-slate-200 bg-white p-6">
        <h2 className="text-xl font-semibold">Early warning, not just detection</h2>
        <p className="mt-2 max-w-3xl text-sm text-slate-600">
          The system groups recent traffic into short windows, extracts behavioural features, and forecasts the
          risk of an attack in the next 1–5 minutes. Every alert comes with ranked, human-readable reasons and a
          recommended next step for the analyst.
        </p>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        <SystemStatus />
        <Link href="/upload" className="rounded-lg border border-indigo-100 bg-indigo-50 p-6 text-sm text-indigo-900">
          <p className="font-semibold">1. Upload traffic</p><p className="mt-2 text-indigo-700">Build the live, 37-feature window sequence from a CSV replay.</p>
        </Link>
        <Link href="/dashboard" className="rounded-lg border border-indigo-100 bg-indigo-50 p-6 text-sm text-indigo-900">
          <p className="font-semibold">2. Forecast and investigate</p><p className="mt-2 text-indigo-700">View the risk timeline, MITRE stage, and feature-level explanation.</p>
        </Link>
      </section>
    </div>
  );
}
