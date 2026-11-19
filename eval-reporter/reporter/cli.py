import argparse
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .aggregate import load_results
from .client import post_run
from .metrics import render


def cmd_sync(args) -> int:
    runs = load_results(args.results)
    if not runs:
        print(f"no runs found under {args.results}", file=sys.stderr)
        return 1
    if args.dry_run:
        for r in runs:
            print(f'{r["run_key"]}  {r["model"]}  {r["defense"]}  trials={r["total_cases"]}  asr={r["attack_success_rate"]}')
        return 0
    token = os.environ.get("CONSOLE_SERVICE_TOKEN", "")
    if not token:
        print("CONSOLE_SERVICE_TOKEN is not set", file=sys.stderr)
        return 2
    failures = 0
    for r in runs:
        try:
            print(f'{post_run(args.api, token, r)}: {r["run_key"]} {r["model"]} {r["defense"]}')
        except RuntimeError as e:
            failures += 1
            print(f"FAILED: {e}", file=sys.stderr)
    return 1 if failures else 0


def make_handler(results: Path):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path == "/health":
                body, ctype = b'{"status":"ok","service":"eval-reporter"}', "application/json"
            elif self.path == "/metrics":
                body, ctype = render(load_results(results)).encode(), "text/plain; version=0.0.4"
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("content-type", ctype)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *a):  # keep stdout quiet
            pass

    return Handler


def cmd_serve(args) -> int:
    ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(args.results)).serve_forever()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="reporter")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync", help="post run summaries to the console API (token from CONSOLE_SERVICE_TOKEN)")
    s.add_argument("--results", type=Path, default=Path("eval/results"))
    s.add_argument("--api", default=os.environ.get("CONSOLE_API_URL", "http://localhost:8000"))
    s.add_argument("--dry-run", action="store_true", help="print summaries, send nothing")
    s.set_defaults(fn=cmd_sync)
    v = sub.add_parser("serve", help="expose /health and /metrics (internal port; never publish it)")
    v.add_argument("--results", type=Path, default=Path("eval/results"))
    v.add_argument("--port", type=int, default=9200)
    v.set_defaults(fn=cmd_serve)
    args = p.parse_args(argv)
    return args.fn(args)
