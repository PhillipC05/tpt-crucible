"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ErrorBoundary } from "@/components/ErrorBoundary";

interface Job {
  id: string;
  model_name: string;
  target: string;
  status: "pending" | "running" | "complete" | "failed";
  created_at: string;
  completed_at?: string;
  error?: string;
  result?: string;
}

const statusColor: Record<string, string> = {
  complete: "text-accent-green",
  running: "text-accent-cyan",
  pending: "text-text-secondary",
  failed: "text-accent-red",
};

const statusDot: Record<string, string> = {
  complete: "bg-accent-green",
  running: "bg-accent-cyan animate-pulse",
  pending: "bg-text-secondary",
  failed: "bg-accent-red",
};

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-US", { hour12: false });
  } catch {
    return iso;
  }
}

const PAGE_SIZE = 20;

function JobSkeleton() {
  return (
    <div className="flex items-start gap-3 p-3 rounded bg-bg-tertiary animate-pulse">
      <div className="w-2.5 h-2.5 rounded-full mt-1 flex-shrink-0 bg-bg-primary" />
      <div className="flex-1 space-y-1.5">
        <div className="h-3 bg-bg-primary rounded w-48" />
        <div className="h-2.5 bg-bg-primary rounded w-72" />
      </div>
    </div>
  );
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

  useEffect(() => {
    const load = () => {
      fetch(`${apiUrl}/api/jobs`)
        .then((r) => r.json())
        .then((data: Job[]) => {
          setJobs(data.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()));
          setLoading(false);
        })
        .catch(() => setLoading(false));
    };
    load();
    const interval = setInterval(load, 5000);
    return () => clearInterval(interval);
  }, [apiUrl]);

  const totalPages = Math.max(1, Math.ceil(jobs.length / PAGE_SIZE));
  const pageJobs = jobs.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-bg-primary grid-bg p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-accent-cyan">Job History</h1>
              <p className="text-sm text-text-secondary mt-1">
                {loading ? "Loading..." : `${jobs.length} total compilation jobs`}
              </p>
            </div>
            <Link
              href="/cloud"
              className="px-4 py-2 rounded bg-accent-cyan/20 text-accent-cyan text-sm border border-accent-cyan/50 hover:bg-accent-cyan/30"
            >
              + New Job
            </Link>
          </div>

          <div className="stat-card">
            {loading && (
              <div className="space-y-2">
                {Array.from({ length: 5 }).map((_, i) => <JobSkeleton key={i} />)}
              </div>
            )}
            {!loading && jobs.length === 0 && (
              <p className="text-xs text-text-secondary text-center py-8">
                No jobs yet.{" "}
                <Link href="/cloud" className="text-accent-cyan hover:underline">
                  Start a compilation
                </Link>
              </p>
            )}
            {!loading && jobs.length > 0 && (
              <>
                <div className="space-y-2">
                  {pageJobs.map((job) => (
                    <div key={job.id} className="flex items-start gap-3 p-3 rounded bg-bg-tertiary">
                      <div className={`w-2.5 h-2.5 rounded-full mt-1 flex-shrink-0 ${statusDot[job.status] ?? "bg-text-secondary"}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-sm font-mono text-text-primary">{job.model_name}</span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-bg-primary text-text-secondary">{job.target}</span>
                          <span className={`text-[10px] font-bold ${statusColor[job.status] ?? "text-text-secondary"}`}>
                            {job.status.toUpperCase()}
                          </span>
                        </div>
                        <div className="text-[10px] text-text-secondary mt-0.5 space-x-2">
                          <span>Started: {formatDate(job.created_at)}</span>
                          {job.completed_at && <span>Finished: {formatDate(job.completed_at)}</span>}
                          <span className="font-mono text-text-secondary/60">{job.id}</span>
                        </div>
                        {job.error && <p className="text-[10px] text-accent-red mt-1 truncate">{job.error}</p>}
                      </div>
                      {job.status === "complete" && (
                        <a
                          href={`${apiUrl}/api/jobs/${job.id}/download`}
                          className="flex-shrink-0 px-3 py-1 rounded bg-accent-green/20 text-accent-green text-xs hover:bg-accent-green/30"
                        >
                          Download
                        </a>
                      )}
                    </div>
                  ))}
                </div>

                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4 pt-4 border-t border-border">
                    <span className="text-xs text-text-secondary">
                      Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, jobs.length)} of {jobs.length}
                    </span>
                    <div className="flex gap-2">
                      <button
                        onClick={() => setPage((p) => Math.max(0, p - 1))}
                        disabled={page === 0}
                        className="px-3 py-1 rounded bg-bg-tertiary text-text-secondary text-xs border border-border disabled:opacity-30 hover:text-text-primary"
                      >
                        Prev
                      </button>
                      <span className="px-3 py-1 text-xs text-text-secondary">
                        {page + 1} / {totalPages}
                      </span>
                      <button
                        onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                        disabled={page >= totalPages - 1}
                        className="px-3 py-1 rounded bg-bg-tertiary text-text-secondary text-xs border border-border disabled:opacity-30 hover:text-text-primary"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>
    </ErrorBoundary>
  );
}
