// app/upload/page.tsx
"use client";

import { useState } from "react";
import { startReplay, getJobStatus } from "@/lib/api";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [jobStatus, setJobStatus] = useState<string>("idle");
  const [progress, setProgress] = useState(0);

  async function handleUpload() {
    if (!file) return;
    setJobStatus("pending");
    const job = await startReplay(file.name);
    setJobStatus(job.status);

    // Fake polling loop just to show progress moving
    let fakeProgress = 0;
    const interval = setInterval(async () => {
      fakeProgress += 20;
      setProgress(fakeProgress);
      if (fakeProgress >= 100) {
        clearInterval(interval);
        setJobStatus("completed");
      } else {
        const status = await getJobStatus(job.jobId);
        setJobStatus(status.status);
      }
    }, 800);
  }

  return (
    <div className="min-h-screen bg-gray-100 p-8">
      <h1 className="mb-6 text-2xl font-bold text-gray-800">
        Upload / Replay Traffic
      </h1>

      <div className="max-w-md rounded-lg bg-white p-6 shadow">
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
          Start Replay
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
      </div>
    </div>
  );
}