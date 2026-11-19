export interface Config {
  port: number;
  apiKey: string;
  twinApiUrl: string;
  consoleApiUrl: string | null;
  consoleServiceToken: string | null;
  rateLimitMax: number;
  rateLimitWindow: string;
  upstreamTimeoutMs: number;
}

/** Fails closed: the gateway refuses to start without an API key. */
export function loadConfig(env: NodeJS.ProcessEnv = process.env): Config {
  const apiKey = env.GATEWAY_API_KEY ?? "";
  if (apiKey.length < 16) {
    throw new Error("GATEWAY_API_KEY must be set (at least 16 characters)");
  }
  const consoleApiUrl = env.CONSOLE_API_URL ? env.CONSOLE_API_URL.replace(/\/+$/, "") : null;
  return {
    port: Number(env.PORT ?? 8080),
    apiKey,
    twinApiUrl: (env.TWIN_API_URL ?? "http://localhost:7861").replace(/\/+$/, ""),
    consoleApiUrl,
    consoleServiceToken: env.CONSOLE_SERVICE_TOKEN || null,
    rateLimitMax: Number(env.RATE_LIMIT_MAX ?? 30),
    rateLimitWindow: env.RATE_LIMIT_WINDOW ?? "1 minute",
    upstreamTimeoutMs: Number(env.UPSTREAM_TIMEOUT_MS ?? 60_000),
  };
}
