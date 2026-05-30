import API from "./config";

export interface ApiResult<T = unknown> {
  code?: number;
  msg?: string;
  data?: T;
  success?: boolean;
  error?: string;
}

async function request<T>(url: string, body: unknown): Promise<T> {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export async function simpleChat(message: string): Promise<ReadableStream<Uint8Array> | null> {
  const res = await fetch(API.simpleChat, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ func: "chat", message }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.body;
}

export interface AgentChatParams {
  message: string;
  session_id?: string;
  openid?: string;
  image_base64?: string;
}

export interface AgentChatEvent {
  type: "meta" | "reply" | "done" | "error";
  content?: string;
  intent?: string;
  tools_used?: string[];
  session_id?: string;
  has_vision?: boolean;
}

/**
 * Agent chat with SSE streaming
 * Returns an AsyncGenerator yielding parsed events
 */
export async function* agentChatStream(params: AgentChatParams): AsyncGenerator<AgentChatEvent> {
  const res = await fetch(API.agentChat, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });

  if (!res.ok) {
    yield { type: "error", content: `HTTP ${res.status}: ${await res.text()}` };
    return;
  }

  const reader = res.body?.getReader();
  if (!reader) {
    yield { type: "error", content: "No response body" };
    return;
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const parsed = JSON.parse(trimmed);
          yield parsed as AgentChatEvent;
        } catch {
          // skip malformed lines
        }
      }
    }
    // process remaining
    if (buffer.trim()) {
      try {
        yield JSON.parse(buffer.trim()) as AgentChatEvent;
      } catch { /* skip */ }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function visionDetect(
  model_name: string,
  image_base64: string,
  params: Record<string, unknown> = {}
): Promise<ApiResult> {
  return request(API.visionDetect, { model_name, image_base64, params });
}

export function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      // strip data:image/xxx;base64, prefix
      const base64 = result.split(",")[1] || result;
      resolve(base64);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}
