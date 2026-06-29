export type ChatUI = {
  type: string;
  data: Record<string, any>;
};

export type ChatResponse = {
  session_id: number;
  message: string;
  intent: string;
  requires_auth: boolean;
  ui: ChatUI;
};

export type ChatMessage = {
  id: string;
  sender: "user" | "assistant";
  text: string;
  response?: ChatResponse;
};

export type AuthUser = {
  accessToken: string;
  userId: number;
  employeeId: string;
  fullName: string;
  role: string;
  permissions: string[];
};