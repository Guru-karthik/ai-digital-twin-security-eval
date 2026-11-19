import { randomUUID, timingSafeEqual, createHash } from "node:crypto";
import Fastify, { type FastifyInstance } from "fastify";
import rateLimit from "@fastify/rate-limit";
import { Counter, Histogram, Registry, collectDefaultMetrics } from "prom-client";
import type { Config } from "./config.js";
import { reportToConsole } from "./console.js";
import type { ChatMessage } from "./types.js";
import { callTwin, UpstreamError, type Fetch } from "./upstream.js";

const chatSchema = {
  body: {
    type: "object",
    required: ["message"],
    additionalProperties: false,
    properties: {
      message: { type: "string", minLength: 1, maxLength: 4000 },
      history: {
        type: "array",
        maxItems: 50,
        items: {
          type: "object",
          required: ["role", "content"],
          additionalProperties: false,
          properties: { role: { enum: ["user", "assistant"] }, content: { type: "string", maxLength: 8000 } },
        },
      },
      conversation_id: { type: "string", minLength: 1, maxLength: 64, pattern: "^[A-Za-z0-9_-]+$" },
    },
  },
} as const;

function keyMatches(given: string | undefined, expected: string): boolean {
  if (!given) return false;
  // hash both sides so lengths are equal and the comparison is constant-time
  const a = createHash("sha256").update(given).digest();
  const b = createHash("sha256").update(expected).digest();
  return timingSafeEqual(a, b);
}

/** Splits a reply into small chunks. The agent is not streaming, so this replays a finished reply. */
export function chunk(text: string, size = 24): string[] {
  const out: string[] = [];
  for (let i = 0; i < text.length; i += size) out.push(text.slice(i, i + size));
  return out;
}

export type GatewayApp = FastifyInstance & { metrics: Registry };

export async function buildApp(cfg: Config, f: Fetch = fetch): Promise<GatewayApp> {
  // One registry per app so tests do not share counters. Labels are bounded (route pattern + status), never user input.
  const metrics = new Registry();
  collectDefaultMetrics({ register: metrics });
  const requests = new Counter({ name: "gateway_http_requests_total", help: "HTTP requests", labelNames: ["route", "status"], registers: [metrics] });
  const duration = new Histogram({ name: "gateway_http_request_duration_seconds", help: "HTTP latency", labelNames: ["route"], registers: [metrics] });
  const upstreamFailures = new Counter({ name: "gateway_upstream_failures_total", help: "twin-api failures", registers: [metrics] });

  const app = Fastify({
    // Request log without bodies. Credentials are redacted. Visitor messages are never logged.
    logger: process.env.NODE_ENV === "test" ? false : { redact: ["req.headers.x-api-key", "req.headers.authorization"] },
    bodyLimit: 128 * 1024,
    // Reject unknown fields (the contract says additionalProperties:false) instead of Fastify's default of silently stripping them.
    ajv: { customOptions: { removeAdditional: false } },
  });

  await app.register(rateLimit, { max: cfg.rateLimitMax, timeWindow: cfg.rateLimitWindow });

  app.addHook("onResponse", async (req, reply) => {
    const route = req.routeOptions?.url ?? "unmatched";
    requests.inc({ route, status: String(reply.statusCode) });
    duration.observe({ route }, reply.elapsedTime / 1000);
  });

  app.addHook("onSend", async (_req, reply) => {
    reply.header("x-content-type-options", "nosniff");
    reply.header("cache-control", "no-store");
  });

  app.get("/health", { config: { rateLimit: false } }, async () => ({ status: "ok", service: "gateway" }));

  // Auth runs before body validation so unauthenticated callers learn nothing about the schema.
  const requireKey = async (req: { headers: Record<string, unknown> }, reply: { code: (n: number) => { send: (b: object) => unknown } }) => {
    if (!keyMatches(req.headers["x-api-key"] as string | undefined, cfg.apiKey)) {
      return reply.code(401).send({ message: "Unauthenticated." });
    }
  };

  app.post("/chat", { schema: chatSchema, onRequest: requireKey }, async (req, reply) => {
    const body = req.body as { message: string; history?: ChatMessage[]; conversation_id?: string };
    const history = body.history ?? [];
    const conversationId = body.conversation_id ?? randomUUID();

    let twin;
    try {
      twin = await callTwin(f, cfg.twinApiUrl, body.message, history, cfg.upstreamTimeoutMs);
    } catch (err) {
      if (err instanceof UpstreamError) {
        upstreamFailures.inc();
        req.log.warn({ reason: err.message }, "upstream failure");
        return reply.code(502).send({ message: "The twin is unavailable." });
      }
      throw err;
    }

    const transcript: ChatMessage[] = [
      ...history,
      { role: "user", content: body.message },
      { role: "assistant", content: twin.reply },
    ];
    void reportToConsole(f, cfg, req.log, conversationId, transcript, twin);

    if ((req.headers.accept ?? "").includes("text/event-stream")) {
      reply.hijack();
      reply.raw.writeHead(200, { "content-type": "text/event-stream", "cache-control": "no-store", connection: "keep-alive", "x-content-type-options": "nosniff" });
      for (const part of chunk(twin.reply)) reply.raw.write(`event: delta\ndata: ${JSON.stringify({ text: part })}\n\n`);
      reply.raw.write(`event: done\ndata: ${JSON.stringify({ conversation_id: conversationId })}\n\n`);
      reply.raw.end();
      return reply;
    }
    return { reply: twin.reply, conversation_id: conversationId };
  });

  app.setErrorHandler((err: Error & { statusCode?: number; validation?: unknown }, req, reply) => {
    const status = err.statusCode ?? 500;
    if (status >= 500) req.log.error({ err: err.name }, "unhandled error");
    // Validation and rate-limit messages are safe to return; 5xx messages are not.
    reply.code(status).send({ message: status >= 500 ? "Internal error." : err.message });
  });

  return Object.assign(app, { metrics }) as unknown as GatewayApp;
}
