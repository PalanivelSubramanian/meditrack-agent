const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export async function postChatMessage(params: {
  message: string;
  sessionId?: number | null;
  accessToken?: string | null;
}) {
  const response = await fetch(`${API_BASE_URL}/chat/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(params.accessToken
        ? { Authorization: `Bearer ${params.accessToken}` }
        : {}),
    },
    body: JSON.stringify({
      message: params.message,
      session_id: params.sessionId ?? null,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail || "Chat request failed");
  }

  return response.json();
}

export async function startAuth(employeeId: string) {
  const response = await fetch(`${API_BASE_URL}/auth/start`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      employee_id: employeeId,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail || "Authentication start failed");
  }

  return response.json();
}

export async function verifyTotp(params: {
  employeeId: string;
  totpCode: string;
}) {
  const response = await fetch(`${API_BASE_URL}/auth/verify-totp`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      employee_id: params.employeeId,
      totp_code: params.totpCode,
    }),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    throw new Error(errorBody?.detail || "TOTP verification failed");
  }

  return response.json();
}

export type AuditLogItem = {
  id: number;
  action_type: string;
  user_id: number | null;
  entity_type: string | null;
  entity_id: number | null;
  permission_checked: string | null;
  access_granted: boolean;
  details: string | null;
  created_at: string;
};

export async function fetchAuditLogs(accessToken?: string): Promise<AuditLogItem[]> {
  if (!accessToken) {
    throw new Error("Login required to view audit logs.");
  }

  const response = await fetch(`${API_BASE_URL}/audit/logs`, {
    method: "GET",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(errorText || "Failed to fetch audit logs.");
  }

  return response.json();
}