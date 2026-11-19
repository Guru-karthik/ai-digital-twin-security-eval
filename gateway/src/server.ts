import { createServer } from "node:http";
import { buildApp } from "./app.js";
import { loadConfig } from "./config.js";

const cfg = loadConfig();
const app = await buildApp(cfg);
await app.listen({ port: cfg.port, host: "0.0.0.0" });

// Metrics live on a separate port so they are never reachable through the public /chat listener.
// Keep METRICS_PORT unpublished (Compose only exposes it to the Prometheus container).
if (cfg.metricsPort > 0) {
  createServer(async (req, res) => {
    if (req.url !== "/metrics") { res.writeHead(404).end(); return; }
    res.writeHead(200, { "content-type": app.metrics.contentType }).end(await app.metrics.metrics());
  }).listen(cfg.metricsPort, "0.0.0.0");
}
