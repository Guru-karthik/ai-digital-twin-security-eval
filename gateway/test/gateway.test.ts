import { afterEach, describe, expect, it } from "vitest";
import type { FastifyInstance } from "fastify";
import { buildApp, chunk } from "../src/app.js";
import { loadConfig, type Config } from "../src/config.js";
import { leadsFrom } from "../src/console.js";

process.env.NODE_ENV = "test";
const KEY = "test-gateway-key-123456";

interface Call { url: string; init: RequestInit }

function cfg(over: Partial<Config> = {}): Config {
  return {
    ...loadConfig({ GATEWAY_API_KEY: KEY, TWIN_API_URL: "http://twin", CONSOLE_API_URL: "http://console", CONSOLE_SERVICE_TOKEN: "svc" }),
    ...over,
  };
}

/** Fake fetch: twin returns `twinBody`, console accepts everything. Records every call. */
function fakeFetch(twinBody: object | (() => Response), calls: Call[], consoleStatus = 201): typeof fetch {
  return (async (url: string, init: RequestInit) => {
    calls.push({ url, init });
    if (url.startsWith("http://twin")) {
      return typeof twinBody === "function" ? twinBody() : new Response(JSON.stringify(twinBody), { status: 200 });
    }
    return new Response("{}", { status: consoleStatus });
  }) as unknown as typeof fetch;
}

let app: FastifyInstance;
afterEach(async () => { await app?.close(); });

const post = (payload: unknown, headers: Record<string, string> = { "x-api-key": KEY }) =>
  app.inject({ method: "POST", url: "/chat", payload: payload as object, headers });

describe("config", () => {
  it("refuses to start without a strong API key", () => {
    expect(() => loadConfig({})).toThrow(/GATEWAY_API_KEY/);
    expect(() => loadConfig({ GATEWAY_API_KEY: "short" })).toThrow(/GATEWAY_API_KEY/);
  });
});

describe("auth", () => {
  it("rejects missing and wrong keys with 401", async () => {
    app = await buildApp(cfg(), fakeFetch({ reply: "x" }, []));
    expect((await post({ message: "hi" }, {})).statusCode).toBe(401);
    expect((await post({ message: "hi" }, { "x-api-key": "wrong" })).statusCode).toBe(401);
  });

  it("checks the key before validating the body", async () => {
    app = await buildApp(cfg(), fakeFetch({ reply: "x" }, []));
    expect((await post({ nonsense: true }, {})).statusCode).toBe(401);
  });

  it("does not require a key for /health", async () => {
    app = await buildApp(cfg(), fakeFetch({ reply: "x" }, []));
    const res = await app.inject({ url: "/health" });
    expect(res.statusCode).toBe(200);
    expect(res.json()).toEqual({ status: "ok", service: "gateway" });
  });
});

describe("validation", () => {
  it.each([
    [{}],
    [{ message: "" }],
    [{ message: "x".repeat(4001) }],
    [{ message: "hi", extra: 1 }],
    [{ message: "hi", history: [{ role: "system", content: "x" }] }],
    [{ message: "hi", history: Array(51).fill({ role: "user", content: "x" }) }],
    [{ message: "hi", conversation_id: "../etc/passwd" }],
  ])("returns 400 for %j", async (payload) => {
    const calls: Call[] = [];
    app = await buildApp(cfg(), fakeFetch({ reply: "x" }, calls));
    expect((await post(payload)).statusCode).toBe(400);
    expect(calls).toHaveLength(0); // nothing reached the twin
  });
});

describe("chat proxy", () => {
  it("returns reply and a generated conversation_id, forwarding message and history only", async () => {
    const calls: Call[] = [];
    app = await buildApp(cfg(), fakeFetch({ reply: "hello" }, calls));
    const history = [{ role: "user", content: "a" }, { role: "assistant", content: "b" }];

    const res = await post({ message: "hi", history });
    expect(res.statusCode).toBe(200);
    expect(res.json().reply).toBe("hello");
    expect(res.json().conversation_id).toMatch(/^[0-9a-f-]{36}$/);

    const twinCall = calls.find((c) => c.url === "http://twin/chat")!;
    expect(JSON.parse(String(twinCall.init.body))).toEqual({ message: "hi", history });
  });

  it("keeps a supplied conversation_id", async () => {
    app = await buildApp(cfg(), fakeFetch({ reply: "hello" }, []));
    expect((await post({ message: "hi", conversation_id: "abc-1" })).json().conversation_id).toBe("abc-1");
  });

  it("sets nosniff and no-store", async () => {
    app = await buildApp(cfg(), fakeFetch({ reply: "hello" }, []));
    const res = await post({ message: "hi" });
    expect(res.headers["x-content-type-options"]).toBe("nosniff");
    expect(res.headers["cache-control"]).toBe("no-store");
  });

  it("returns 502 without leaking details when the twin fails", async () => {
    app = await buildApp(cfg(), fakeFetch(() => new Response("secret stack trace", { status: 500 }), []));
    const res = await post({ message: "hi" });
    expect(res.statusCode).toBe(502);
    expect(res.body).not.toContain("secret");
  });

  it("returns 502 on an invalid twin body", async () => {
    app = await buildApp(cfg(), fakeFetch({ nope: 1 }, []));
    expect((await post({ message: "hi" })).statusCode).toBe(502);
  });

  it("returns 502 when the twin is unreachable", async () => {
    const f = (async () => { throw new TypeError("connect ECONNREFUSED"); }) as unknown as typeof fetch;
    app = await buildApp(cfg(), f);
    expect((await post({ message: "hi" })).statusCode).toBe(502);
  });
});

describe("SSE", () => {
  it("replays the reply as delta events then done", async () => {
    const reply = "x".repeat(60);
    app = await buildApp(cfg(), fakeFetch({ reply }, []));
    const res = await post({ message: "hi", conversation_id: "c9" }, { "x-api-key": KEY, accept: "text/event-stream" });

    expect(res.headers["content-type"]).toBe("text/event-stream");
    const events = res.body.trim().split("\n\n");
    const deltas = events.filter((e) => e.startsWith("event: delta"));
    expect(deltas.length).toBe(3);
    const text = deltas.map((e) => JSON.parse(e.split("data: ")[1]!).text).join("");
    expect(text).toBe(reply);
    expect(events.at(-1)).toBe('event: done\ndata: {"conversation_id":"c9"}');
  });

  it("chunk() reassembles to the original text", () => {
    expect(chunk("héllo wörld, this is a longer reply!").join("")).toBe("héllo wörld, this is a longer reply!");
    expect(chunk("")).toEqual([]);
  });
});

describe("console webhooks", () => {
  const flush = () => new Promise((r) => setTimeout(r, 20));

  it("stores the conversation and forwards leads, tool calls and decisions with the service token", async () => {
    const calls: Call[] = [];
    const twin = {
      reply: "thanks",
      defense: "D2",
      model: "qwen3:8b",
      tool_calls: [{ name: "record_user_details", arguments: { email: "v@example.com", name: "V" } }],
      decisions: [{ decision: "allow", reason: "ok" }],
    };
    app = await buildApp(cfg(), fakeFetch(twin, calls));
    await post({ message: "my email is v@example.com", conversation_id: "c1" });
    await flush();

    const consoleCalls = calls.filter((c) => c.url.startsWith("http://console"));
    const paths = consoleCalls.map((c) => c.url.replace("http://console", "")).sort();
    expect(paths).toEqual(["/api/v1/audit-events", "/api/v1/audit-events", "/api/v1/conversations", "/api/v1/leads"]);
    for (const c of consoleCalls) {
      expect((c.init.headers as Record<string, string>).authorization).toBe("Bearer svc");
    }
    const lead = JSON.parse(String(consoleCalls.find((c) => c.url.endsWith("/leads"))!.init.body));
    expect(lead).toEqual({ email: "v@example.com", name: "V", conversation_id: "c1" });
  });

  it("still answers when the console is down or rejects", async () => {
    app = await buildApp(cfg(), fakeFetch({ reply: "ok" }, [], 500));
    expect((await post({ message: "hi" })).statusCode).toBe(200);
    await flush();
  });

  it("makes no console calls when the console is not configured", async () => {
    const calls: Call[] = [];
    app = await buildApp(cfg({ consoleApiUrl: null, consoleServiceToken: null }), fakeFetch({ reply: "ok" }, calls));
    await post({ message: "hi" });
    await flush();
    expect(calls.filter((c) => c.url.startsWith("http://console"))).toHaveLength(0);
  });

  it("clamps lead fields to the API limits and ignores other tools", () => {
    const leads = leadsFrom([
      { name: "record_user_details", arguments: { email: "a@b.co", notes: "n".repeat(5000) } },
      { name: "record_unknown_question", arguments: { question: "?" } },
      { name: "record_user_details", arguments: { name: "no email" } },
    ], "c");
    expect(leads).toHaveLength(1);
    expect(leads[0]!.notes).toHaveLength(2000);
  });
});

describe("rate limit", () => {
  it("returns 429 after the configured maximum", async () => {
    app = await buildApp(cfg({ rateLimitMax: 3 }), fakeFetch({ reply: "x" }, []));
    const codes: number[] = [];
    for (let i = 0; i < 5; i++) codes.push((await post({ message: "hi" })).statusCode);
    expect(codes).toEqual([200, 200, 200, 429, 429]);
  });
});
