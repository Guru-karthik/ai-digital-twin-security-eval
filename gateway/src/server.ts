import { buildApp } from "./app.js";
import { loadConfig } from "./config.js";

const cfg = loadConfig();
const app = await buildApp(cfg);
await app.listen({ port: cfg.port, host: "0.0.0.0" });
