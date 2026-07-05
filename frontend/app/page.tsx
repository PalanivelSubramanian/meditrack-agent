"use client";

import { useState } from "react";
import { postChatMessage } from "@/lib/api";
import type { AuthUser, ChatMessage, ChatResponse } from "@/types/chat";

import { DynamicAgentCard } from "@/components/DynamicAgentCard";
import { StaffLoginPanel } from "@/components/StaffLoginPanel";
import { AuditLogPanel } from "@/components/AuditLogPanel";


function createId() {
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: createId(),
      sender: "assistant",
      text: "Hello, I am MediTrack Agent. I can help with public health questions or verified clinic workflows like patient search, appointment booking, doctor availability, and patient history.",
    },
  ]);

  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [selectedPatient, setSelectedPatient] = useState<{
  patientId: number;
  patientNumber: string;
  fullName: string;
} | null>(null);

  async function sendMessage(messageText?: string) {
    const text = (messageText ?? input).trim();

    if (!text || isSending) {
      return;
    }

    setInput("");
    setIsSending(true);

    const userMessage: ChatMessage = {
      id: createId(),
      sender: "user",
      text,
    };

    setMessages((current) => [...current, userMessage]);

    try {
      const response: ChatResponse = await postChatMessage({
        message: text,
        sessionId,
        accessToken: user?.accessToken,
      });

      setSessionId(response.session_id);

      const responsePatient = response.ui?.data?.patient;

      if (
        responsePatient?.patient_id &&
        responsePatient?.patient_number &&
        responsePatient?.full_name
      ) {
        setSelectedPatient({
          patientId: responsePatient.patient_id,
          patientNumber: responsePatient.patient_number,
          fullName: responsePatient.full_name,
        });
      }

      const assistantMessage: ChatMessage = {
        id: createId(),
        sender: "assistant",
        text: response.message,
        response,
      };

      setMessages((current) => [...current, assistantMessage]);
    } catch (err: any) {
      const assistantMessage: ChatMessage = {
        id: createId(),
        sender: "assistant",
        text: err.message || "Something went wrong.",
      };

      setMessages((current) => [...current, assistantMessage]);
    } finally {
      setIsSending(false);
    }
  }

  async function clearPatientContext() {
  console.log("Clear patient clicked");

  setSelectedPatient(null);

  if (!sessionId) {
    console.warn("No sessionId available to clear patient context");
    return;
  }

  if (!user?.accessToken) {
    console.warn("No access token available to clear patient context");
    return;
  }

  const clearUrl = `${API_BASE_URL}/chat/clear-patient-context`;
  console.log("Calling clear patient endpoint:", clearUrl, "sessionId:", sessionId);

  try {
    const response = await fetch(clearUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${user.accessToken}`,
      },
      body: JSON.stringify({
        session_id: sessionId,
      }),
    });

    const result = await response.json();
    console.log("Clear patient context result:", result);
  } catch (error) {
    console.error("Failed to clear patient context", error);
  }
}

  return (
    <main className="min-h-screen bg-slate-100 p-6">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="space-y-4">
          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <h1 className="text-lg font-bold text-slate-900">
              MediTrack Agent
            </h1>

            <p className="mt-1 text-sm text-slate-500">
              Agentic healthcare coordination assistant.
            </p>
          </div>

          <StaffLoginPanel
            user={user}
            onLogin={setUser}
            onLogout={() => {
              setUser(null);
              setSelectedPatient(null);
              setSessionId(null);
            }}
          />

          <AuditLogPanel user={user} />

          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold text-slate-800">
              Demo script
            </div>

            <div className="mt-1 text-xs text-slate-500">
              Recommended final project walkthrough.
            </div>

            <ol className="mt-3 list-decimal space-y-2 pl-4 text-xs text-slate-700">
              <li>Login as receptionist using Employee ID + TOTP.</li>
              <li>Search ambiguous patient: John Smith.</li>
              <li>Select P10001 and view patient history.</li>
              <li>Ask: What medications is he taking?</li>
              <li>Ask: Summarize current patient history.</li>
              <li>Click Clear patient, then ask medication follow-up again.</li>
              <li>Show Aisha Rahman upcoming appointments.</li>
              <li>Cancel appointment if a demo appointment exists.</li>
              <li>Login as admin and refresh Audit viewer.</li>
              <li>Show Agent trace and audit logs together.</li>
            </ol>
          </div>

          <div className="rounded-xl border bg-white p-4 shadow-sm">
            <div className="text-sm font-semibold text-slate-800">
              Try workflows
            </div>

            <div className="mt-3 space-y-2">
              {[
                "What causes headache?",
                "Search patient John Smith",
                "Find patient Aisha Rahman",
                "Which cardiologists are available tomorrow?",
                "Show dermatology slots tomorrow",
                "Book appointment for Aisha Rahman with cardiology tomorrow at 09:30",
                "Show Aisha Rahman history",
                "Show John Smith history",
              ].map((example) => (
                <button
                  key={example}
                  type="button"
                  onClick={() => sendMessage(example)}
                  disabled={isSending}
                  className="w-full rounded-lg border px-3 py-2 text-left text-xs hover:bg-slate-50 disabled:opacity-50"
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <section className="flex h-[calc(100vh-3rem)] flex-col rounded-xl border bg-white shadow-sm">
          <div className="border-b p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="font-semibold text-slate-900">Chat Workspace</div>

                <div className="text-sm text-slate-500">
                  {user
                    ? `Verified as ${user.fullName} (${user.role})`
                    : "Public mode"}
                </div>
              </div>

              {selectedPatient && (
                <div className="rounded-xl border border-blue-200 bg-blue-50 px-3 py-2 text-right text-xs text-blue-900">
                  <div className="font-semibold">Current patient</div>

                  <div>
                    {selectedPatient.fullName} · {selectedPatient.patientNumber}
                  </div>

                  <button
                      type="button"
                      onClick={clearPatientContext}
                      className="mt-2 rounded-lg border border-blue-300 bg-white px-2 py-1 text-[11px] font-semibold text-blue-700 hover:bg-blue-100">
                      Clear patient
                    </button>
                </div>
              )}
            </div>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto p-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={
                  message.sender === "user"
                    ? "ml-auto max-w-2xl"
                    : "mr-auto max-w-3xl"
                }
              >
                <div
                  className={
                    message.sender === "user"
                      ? "rounded-xl bg-slate-900 px-4 py-3 text-sm text-white"
                      : "rounded-xl bg-slate-100 px-4 py-3 text-sm text-slate-800"
                  }
                >
                  {message.text}
                </div>

                {message.sender === "assistant" && message.response?.ui && (
                  <div className="mt-2">
                    <DynamicAgentCard
                      ui={message.response.ui}
                      onSendMessage={sendMessage}
                      onFillInput={setInput}
                      accessToken={user?.accessToken}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="border-t p-4">
            <form
              className="flex gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                sendMessage();
              }}
            >
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Ask MediTrack Agent..."
                className="flex-1 rounded-lg border px-4 py-3 text-sm"
              />

              <button
                type="submit"
                disabled={isSending}
                className="rounded-lg bg-slate-900 px-5 py-3 text-sm font-medium text-white disabled:opacity-50"
              >
                {isSending ? "Sending..." : "Send"}
              </button>
            </form>
          </div>
        </section>
      </div>
    </main>
  );
}