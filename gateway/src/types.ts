export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ToolCall {
  name: string;
  arguments: Record<string, unknown>;
}

export interface Decision {
  decision?: string;
  reason?: string;
  [k: string]: unknown;
}

/**
 * What the gateway expects from twin-api POST /chat.
 * `reply` is required. `tool_calls` and `decisions` are optional extras the wrapper may expose
 * (the agent's record_user_details calls and its D2/D3 decisions); the gateway forwards them to the console.
 */
export interface TwinResponse {
  reply: string;
  tool_calls?: ToolCall[];
  decisions?: Decision[];
  defense?: string;
  model?: string;
}
