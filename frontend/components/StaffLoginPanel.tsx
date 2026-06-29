"use client";

import { useState } from "react";
import { startAuth, verifyTotp } from "@/lib/api";
import type { AuthUser } from "@/types/chat";

type Props = {
  user: AuthUser | null;
  onLogin: (user: AuthUser) => void;
  onLogout: () => void;
};

export function StaffLoginPanel({ user, onLogin, onLogout }: Props) {
  const [employeeId, setEmployeeId] = useState("EMP1001");
  const [totpCode, setTotpCode] = useState("");
  const [step, setStep] = useState<"employee" | "totp">("employee");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  async function handleStartAuth() {
    setError(null);
    setIsLoading(true);

    try {
      await startAuth(employeeId);
      setStep("totp");
    } catch (err: any) {
      setError(err.message || "Could not start authentication");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleVerifyTotp() {
    setError(null);
    setIsLoading(true);

    try {
      const result = await verifyTotp({
        employeeId,
        totpCode,
      });

      onLogin({
        accessToken: result.access_token,
        userId: result.user_id,
        employeeId: result.employee_id,
        fullName: result.full_name,
        role: result.role,
        permissions: result.permissions,
      });

      setTotpCode("");
      setStep("employee");
    } catch (err: any) {
      setError(err.message || "Could not verify authenticator code");
    } finally {
      setIsLoading(false);
    }
  }

  if (user) {
    return (
      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold text-slate-800">
          Verified staff
        </div>
        <div className="mt-2 text-sm text-slate-600">{user.fullName}</div>
        <div className="text-sm text-slate-600">
          {user.employeeId} / {user.role}
        </div>

        <button
          onClick={onLogout}
          className="mt-3 rounded-lg border px-3 py-2 text-sm hover:bg-slate-50"
        >
          Logout
        </button>
      </div>
    );
  }

  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="text-sm font-semibold text-slate-800">Staff Login</div>
      <p className="mt-1 text-xs text-slate-500">
        Employee ID is allowed here. Authenticator code is submitted to backend
        auth API, not to the chat agent.
      </p>

      {step === "employee" && (
        <div className="mt-3 space-y-2">
          <input
            value={employeeId}
            onChange={(event) => setEmployeeId(event.target.value)}
            placeholder="Employee ID"
            className="w-full rounded-lg border px-3 py-2 text-sm"
          />

          <button
            onClick={handleStartAuth}
            disabled={isLoading}
            className="w-full rounded-lg bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
          >
            {isLoading ? "Checking..." : "Start verification"}
          </button>
        </div>
      )}

      {step === "totp" && (
        <div className="mt-3 space-y-2">
          <input
            value={totpCode}
            onChange={(event) => setTotpCode(event.target.value)}
            placeholder="Authenticator code"
            className="w-full rounded-lg border px-3 py-2 text-sm"
          />

          <button
            onClick={handleVerifyTotp}
            disabled={isLoading}
            className="w-full rounded-lg bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
          >
            {isLoading ? "Verifying..." : "Verify"}
          </button>

          <button
            onClick={() => setStep("employee")}
            className="w-full rounded-lg border px-3 py-2 text-sm hover:bg-slate-50"
          >
            Back
          </button>
        </div>
      )}

      {error && <div className="mt-3 text-sm text-red-600">{error}</div>}
    </div>
  );
}