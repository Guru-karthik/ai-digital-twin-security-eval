// STUB twin-api for the Compose stack. It is NOT the agent: no model, no tools, no defenses.
// It exists so gateway -> console can be exercised end to end before twin/server.py (T1) lands.
// Contract (see gateway/README.md): POST /chat {message, history} -> {reply, tool_calls?, decisions?}
import { createServer } from "node:http";

const EMAIL = /[^\s@]+@[^\s@]+\.[^\s@]+/;

createServer((req, res) => {
  if (req.method === "GET" && req.url === "/health") { res.writeHead(200).end('{"status":"ok","service":"twin-stub"}'); return; }
  if (req.method !== "POST" || req.url !== "/chat") { res.writeHead(404).end(); return; }
  let raw = "";
  req.on("data", (c) => { raw += c; if (raw.length > 200_000) req.destroy(); });
  req.on("end", () => {
    let body;
    try { body = JSON.parse(raw); } catch { res.writeHead(400).end(); return; }
    const email = typeof body.message === "string" ? body.message.match(EMAIL)?.[0] : undefined;
    const out = {
      reply: email ? "[stub] Thanks, I have noted your email." : "[stub] This is a placeholder reply, not the real agent.",
      defense: "stub",
      model: "stub",
      decisions: [{ decision: "allow", reason: "stub" }],
      tool_calls: email ? [{ name: "record_user_details", arguments: { email, notes: "captured by stub" } }] : [],
    };
    res.writeHead(200, { "content-type": "application/json" }).end(JSON.stringify(out));
  });
}).listen(7861, "0.0.0.0");
