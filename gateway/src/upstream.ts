import type { ChatMessage, TwinResponse } from "./types.js";

export type Fetch = typeof fetch;

export class UpstreamError extends Error {}

export async function callTwin(
  f: Fetch,
  baseUrl: string,
  message: string,
  history: ChatMessage[],
  timeoutMs: number,
): Promise<TwinResponse> {
  let res: Response;
  try {
    res = await f(`${baseUrl}/chat`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ message, history }),
      signal: AbortSignal.timeout(timeoutMs),
    });
  } catch (err) {
    throw new UpstreamError(`twin-api unreachable: ${(err as Error).name}`);
  }
  if (!res.ok) throw new UpstreamError(`twin-api returned ${res.status}`);
  const body = (await res.json().catch(() => null)) as TwinResponse | null;
  if (!body || typeof body.reply !== "string") throw new UpstreamError("twin-api returned an invalid body");
  return body;
}
