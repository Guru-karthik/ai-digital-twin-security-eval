import type { Config } from "./config.js";
import type { ChatMessage, Decision, ToolCall, TwinResponse } from "./types.js";
import type { Fetch } from "./upstream.js";

type Log = { warn: (obj: object, msg: string) => void };

async function post(f: Fetch, cfg: Config, path: string, payload: unknown, log: Log): Promise<void> {
  if (!cfg.consoleApiUrl || !cfg.consoleServiceToken) return;
  try {
    const res = await f(`${cfg.consoleApiUrl}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json", accept: "application/json", authorization: `Bearer ${cfg.consoleServiceToken}` },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) log.warn({ path, status: res.status }, "console webhook rejected");
  } catch (err) {
    log.warn({ path, err: (err as Error).name }, "console webhook failed");
  }
}

const str = (v: unknown, max: number): string | undefined => (typeof v === "string" && v ? v.slice(0, max) : undefined);

/** Leads come from the agent's record_user_details tool calls. Values are clamped to the API's limits. */
export function leadsFrom(calls: ToolCall[] | undefined, conversationId: string) {
  return (calls ?? [])
    .filter((c) => c.name === "record_user_details" && typeof c.arguments?.email === "string")
    .map((c) => ({
      email: String(c.arguments.email).slice(0, 254),
      name: str(c.arguments.name, 200),
      notes: str(c.arguments.notes, 2000),
      conversation_id: conversationId,
    }));
}

/** Best effort and never throws: a console outage must not break chat. */
export async function reportToConsole(
  f: Fetch,
  cfg: Config,
  log: Log,
  conversationId: string,
  messages: ChatMessage[],
  twin: TwinResponse,
): Promise<void> {
  const tasks: Promise<void>[] = [
    post(f, cfg, "/api/v1/conversations", {
      external_id: `${conversationId}:${messages.length}`,
      defense: twin.defense,
      model: twin.model,
      messages,
    }, log),
  ];
  for (const lead of leadsFrom(twin.tool_calls, conversationId)) tasks.push(post(f, cfg, "/api/v1/leads", lead, log));
  for (const c of twin.tool_calls ?? []) {
    tasks.push(post(f, cfg, "/api/v1/audit-events", { type: "tool_call", actor: "agent", subject: conversationId, detail: { name: c.name } }, log));
  }
  for (const d of (twin.decisions ?? []) as Decision[]) {
    tasks.push(post(f, cfg, "/api/v1/audit-events", { type: "policy_decision", actor: "agent", subject: conversationId, detail: d }, log));
  }
  await Promise.all(tasks);
}
