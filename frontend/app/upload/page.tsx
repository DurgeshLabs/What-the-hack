"use client";

import Link from "next/link";
import { useState } from "react";
import { IngestionJob, getJobStatus, getSession, startReplay } from "@/lib/api";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<IngestionJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const session = getSession();

  async function upload() {
    if (!file || !session) return;
    setError(null);
    try {
      let current = await startReplay(session.access_token, file);
      setJob(current);
      const timer = window.setInterval(async () => {
        try {
          current = await getJobStatus(session.access_token, current.id);
          setJob(current);
          if (["completed", "failed"].includes(current.status)) {
            window.clearInterval(timer);
            if (current.status === "completed") localStorage.setItem("wth_source_id", current.traffic_source_id);
          }
        } catch (reason) {
          window.clearInterval(timer);
          setError(reason instanceof Error ? reason.message : "Unable to check upload status");
        }
      }, 1000);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Upload failed");
    }
  }

  if (!session) return <p className="text-slate-500">Sign in before adding traffic.</p>;
  const finished = job?.status === "completed";
  const processing = !!job && !["completed", "failed"].includes(job.status);

  return <div className="mx-auto max-w-4xl space-y-6">
    <div><p className="text-xs font-semibold uppercase tracking-[.18em] text-indigo-600">Data intake</p><h2 className="mt-1 text-3xl font-semibold text-slate-900">Choose a traffic source</h2><p className="mt-2 text-sm text-slate-500">Upload a historical CSV replay or connect an authorised local Zeek sensor. Both build the same 60-second feature windows and use the same forecasting model.</p></div>
    <div className="grid gap-6 md:grid-cols-2">
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"><p className="text-xs font-semibold uppercase tracking-[.14em] text-indigo-600">Option 1</p><h3 className="mt-2 text-xl font-semibold text-slate-900">Upload CSV replay</h3><p className="mt-2 text-sm leading-6 text-slate-500">Use timestamp, source/destination, protocol, packets and bytes. The service groups records into one window per minute.</p><input type="file" accept=".csv,text/csv" onChange={(event) => setFile(event.target.files?.[0] ?? null)} className="mt-5 block w-full rounded-lg border border-slate-200 p-3 text-sm"/><button onClick={upload} disabled={!file || processing} className="mt-4 w-full rounded-lg bg-indigo-600 py-3 text-sm font-semibold text-white disabled:opacity-50">{processing ? "Processing traffic…" : "Upload and build feature windows"}</button>{error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}{job && <div className="mt-5 rounded-lg bg-slate-50 p-4 text-sm"><p className="font-semibold capitalize text-slate-800">{job.status}</p><p className="mt-1 text-slate-600">Accepted {job.accepted_rows.toLocaleString()} of {job.total_rows.toLocaleString()} rows · skipped {job.skipped_rows.toLocaleString()}</p>{job.error_message && <p className="mt-2 text-red-700">{job.error_message}</p>}</div>}{finished && <Link href="/dashboard" className="mt-5 block rounded-lg border border-indigo-200 bg-indigo-50 p-3 text-center text-sm font-semibold text-indigo-700">Open CSV dashboard →</Link>}</section>
      <section className="rounded-2xl border border-indigo-200 bg-indigo-50/50 p-6 shadow-sm"><p className="text-xs font-semibold uppercase tracking-[.14em] text-indigo-600">Option 2</p><h3 className="mt-2 text-xl font-semibold text-slate-900">Live Zeek sensor</h3><p className="mt-2 text-sm leading-6 text-slate-600">For a network you own or are authorised to monitor, Zeek emits connection metadata locally and Docker forwards it to the protected live-ingestion API. No packet payload is sent.</p><ul className="mt-5 space-y-2 text-sm text-slate-600"><li>• One command starts the application and bridge.</li><li>• Zeek records connections from your permitted interface.</li><li>• Select the detected source and view its forecast.</li></ul><Link href="/live" className="mt-6 block rounded-lg bg-slate-950 p-3 text-center text-sm font-semibold text-white">Set up live sensor →</Link></section>
    </div>
  </div>;
}
