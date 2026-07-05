"use client";

import { useState } from "react";
import { fetchAuditLogs, type AuditLogItem } from "@/lib/api";
import type { AuthUser } from "@/types/chat";

type Props = {
  user: AuthUser | null;
};

export function AuditLogPanel({ user }: Props) {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const isAdmin = user?.role === "admin";

    if (!user) {
    return (
      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold text-slate-800">
          Audit viewer
        </div>
        <div className="mt-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
          Login as an admin to view audit logs.
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold text-slate-800">
          Audit viewer
        </div>
        <div className="mt-2 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-600">
          Admin only. Your actions are still audited, but only admins can review audit logs.
        </div>
      </div>
    );
  }

  async function loadAuditLogs() {
    setIsLoading(true);
    setError(null);

    try {
      const result = await fetchAuditLogs(user?.accessToken);
      setLogs(result);
    } catch (err: any) {
      setError(err.message || "Failed to load audit logs.");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-sm font-semibold text-slate-800">
            Audit viewer
          </div>
          <div className="text-xs text-slate-500">
            Admin review of recent protected actions.
          </div>
        </div>

        <button
          type="button"
          onClick={loadAuditLogs}
          disabled={isLoading}
          className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white disabled:opacity-50"
        >
          {isLoading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="mt-3 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-900">
          {error}
        </div>
      )}

      {logs.length > 0 && (
        <div className="mt-3 max-h-80 space-y-2 overflow-y-auto">
          {logs.map((log) => (
            <div
              key={log.id}
              className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700"
            >
              <div className="flex items-center justify-between gap-3">
                <div className="font-semibold text-slate-900">
                  {log.action_type}
                </div>

                <div
                  className={
                    log.access_granted
                      ? "rounded-full bg-green-100 px-2 py-0.5 font-semibold text-green-700"
                      : "rounded-full bg-red-100 px-2 py-0.5 font-semibold text-red-700"
                  }
                >
                  {log.access_granted ? "granted" : "blocked"}
                </div>
              </div>

              <div className="mt-2 grid gap-1">
                <div>
                  <span className="font-semibold">Permission:</span>{" "}
                  {log.permission_checked ?? "none"}
                </div>

                <div>
                  <span className="font-semibold">Entity:</span>{" "}
                  {log.entity_type ?? "none"}{" "}
                  {log.entity_id ? `#${log.entity_id}` : ""}
                </div>

                <div>
                  <span className="font-semibold">User ID:</span>{" "}
                  {log.user_id ?? "anonymous"}
                </div>

                <div>
                  <span className="font-semibold">Time:</span>{" "}
                  {new Date(log.created_at).toLocaleString()}
                </div>

                {log.details && (
                  <div className="mt-1 text-slate-600">
                    <span className="font-semibold">Details:</span>{" "}
                    {log.details}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {user && logs.length === 0 && !isLoading && !error && (
        <div className="mt-3 text-xs text-slate-500">
          Click Refresh to load recent audit logs.
        </div>
      )}
    </div>
  );
}