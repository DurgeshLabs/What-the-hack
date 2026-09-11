// app/upload/page.tsx
"use client";

import { useState } from "react";
import { getJobStatus, getSession, startReplay } from "@/lib/api";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobStatus, setJobStatus] = useState<string>("idle");
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState("");

  async function handleUpload() {
    if (!file) return;
    const session = getSession();
    if (!session) { setMessage("Log in first so the replay can be securely uploaded."); return; }
    try {
      setJobStatus("running"); setProgress(20); setMessage("");
      const job = await startReplay(file, session.access_token);
      localStorage.setItem("wth_source_id", job.traffic_source_id);
      setProgress(65); const completed = await getJobStatus(job.id, session.access_token);
      setJobStatus(completed.status); setProgress(completed.status === "completed" ? 100 : 70);
      setMessage(completed.status === "completed" ? `${completed.accepted_rows.toLocaleString()} flows accepted. Feature windows are building in the background.` : "Replay is still processing; refresh in a moment.");
    } catch (error) { setJobStatus("failed"); setProgress(0); setMessage(error instanceof Error ? error.message : "Upload failed."); }
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <h1 className="mb-6 text-2xl font-bold text-gray-800">
        Upload / Replay Traffic
      </h1>

      <div className="max-w-xl rounded-2xl border border-slate-200 bg-white p-7 shadow-sm">
        <p className="mb-5 text-sm text-slate-600">Upload a normalized flow CSV. The system validates it, groups it into 60-second windows, and calculates the 37 forecasting features.</p>
        <input
          type="file"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="mb-4 block w-full text-sm text-gray-600"
        />

        <button
          onClick={handleUpload}
          disabled={!file || jobStatus === "running"}
          className="w-full rounded bg-blue-600 py-2 text-white hover:bg-blue-700 disabled:bg-gray-300"
        >
          Upload &amp; run replay
        </button>

        {jobStatus !== "idle" && (
          <div className="mt-4">
            <p className="mb-1 text-sm text-gray-600">
              Status: <span className="font-medium">{jobStatus}</span>
            </p>
            <div className="h-2 w-full rounded bg-gray-200">
              <div
                className="h-2 rounded bg-blue-600 transition-all"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
        {message && <p className={`mt-4 rounded-lg p-3 text-sm ${jobStatus === "failed" ? "bg-red-50 text-red-700" : "bg-cyan-50 text-cyan-800"}`}>{message}</p>}
      </div>
    </div>
  );
}
