import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "eval-reporter"))

from reporter.aggregate import MAX_FAILED_CHECKS, load_results, summarise  # noqa: E402
from reporter.cli import main  # noqa: E402
from reporter.client import post_run  # noqa: E402
from reporter.metrics import render  # noqa: E402


def rec(case, success, model="m", defense="D2", ctype="attack", lat=1.0, cost=0.0, error=None):
    return {"case_id": case, "case_type": ctype, "model": model, "defense": defense, "success": success,
            "latency_s": lat, "cost_usd": cost, "error": error}


def test_attack_success_rate_and_passed_cases():
    rows = [rec("A1", True), rec("A1", False), rec("A2", False), rec("A2", False)]
    [run] = summarise("folder", rows)
    assert (run["total_cases"], run["passed_cases"], run["attack_success_rate"]) == (4, 3, 0.25)
    assert run["run_key"] == "folder" and run["failed_checks"] == ["A1 (1/2)"]


def test_groups_by_model_and_defense_and_failed_checks_worst_first():
    rows = [rec("A1", True, defense="D1"), rec("A2", True, defense="D1"), rec("A2", True, defense="D1"),
            rec("A1", False, defense="D3"), rec("A1", False, model="other", defense="D1")]
    runs = {(r["model"], r["defense"]): r for r in summarise("f", rows)}
    assert set(runs) == {("m", "D1"), ("m", "D3"), ("other", "D1")}
    assert runs[("m", "D1")]["failed_checks"] == ["A2 (2/2)", "A1 (1/1)"]
    assert runs[("m", "D3")]["attack_success_rate"] == 0.0 and runs[("m", "D3")]["failed_checks"] == []


def test_benign_and_error_and_unscored_records_do_not_count_as_attack_trials():
    rows = [rec("A1", True), rec("B1", None, ctype="benign"), rec("A2", None), rec("A3", True, error="timeout")]
    [run] = summarise("f", rows)
    assert run["total_cases"] == 1 and run["attack_success_rate"] == 1.0


def test_benign_only_group_is_skipped():
    assert summarise("f", [rec("B1", None, ctype="benign")]) == []


def test_latency_and_cost_cover_attack_and_benign_records():
    rows = [rec("A1", False, lat=2.0, cost=0.5), rec("B1", None, ctype="benign", lat=4.0, cost=0.25)]
    [run] = summarise("f", rows)
    assert run["mean_latency_s"] == 3.0 and run["cost_usd"] == 0.75


def test_failed_checks_are_capped():
    rows = [rec(f"A{i:03}", True) for i in range(MAX_FAILED_CHECKS + 20)]
    [run] = summarise("f", rows)
    assert len(run["failed_checks"]) == MAX_FAILED_CHECKS


def test_malformed_lines_are_skipped(tmp_path):
    d = tmp_path / "folder"
    d.mkdir()
    (d / "runs.jsonl").write_text(json.dumps(rec("A1", True)) + "\nnot json\n\n" + json.dumps(rec("A2", False)) + "\n")
    [run] = load_results(tmp_path)
    assert run["total_cases"] == 2


def test_real_results_payloads_match_the_openapi_contract():
    """Every summary built from the repo's real eval/results must be accepted by EvaluationRunCreate."""
    runs = load_results(ROOT / "eval" / "results")
    assert len(runs) >= 8
    schema = yaml.safe_load((ROOT / "docs" / "openapi.yaml").read_text())["components"]["schemas"]["EvaluationRunCreate"]
    for run in runs:
        assert set(run) <= set(schema["properties"]), "extra field would be rejected (additionalProperties: false)"
        assert set(schema["required"]) <= set(run)
        assert 0 <= run["attack_success_rate"] <= 1 and run["passed_cases"] <= run["total_cases"]
        assert len(run["defense"]) <= 32 and len(run["model"]) <= 100
        assert all(len(c) <= 500 for c in run["failed_checks"])


class Api(BaseHTTPRequestHandler):
    seen: list = []
    status = 201

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        Api.seen.append((self.path, self.headers.get("authorization"), body))
        self.send_response(Api.status)
        self.send_header("content-length", "2")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *a):
        pass


@pytest.fixture
def api():
    Api.seen, Api.status = [], 201
    srv = HTTPServer(("127.0.0.1", 0), Api)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


RUN = {"run_key": "r", "defense": "D2", "model": "m", "total_cases": 1, "passed_cases": 1}


def test_post_run_sends_bearer_token_and_reports_created_vs_updated(api):
    assert post_run(api, "tok-123", RUN) == "created"
    Api.status = 200
    assert post_run(api, "tok-123", RUN) == "updated"
    path, auth, body = Api.seen[0]
    assert path == "/api/v1/evaluation-runs" and auth == "Bearer tok-123" and body == RUN


def test_errors_never_contain_the_token(api):
    Api.status = 401
    with pytest.raises(RuntimeError) as e:
        post_run(api, "tok-SECRET", RUN)
    assert "401" in str(e.value) and "SECRET" not in str(e.value)
    with pytest.raises(RuntimeError) as e:
        post_run("http://127.0.0.1:9", "tok-SECRET", RUN, timeout=1)
    assert "SECRET" not in str(e.value)


def test_metrics_text_format_and_label_escaping():
    text = render([{"run_key": 'a"b', "model": "m", "defense": "D2", "attack_success_rate": 0.5, "total_cases": 4,
                    "passed_cases": 2, "mean_latency_s": None, "cost_usd": 0.0}])
    assert 'eval_attack_success_rate{run_key="a\\"b",model="m",defense="D2"} 0.5' in text
    assert "# TYPE eval_attack_success_rate gauge" in text
    assert "eval_mean_latency_seconds{" not in text  # None values are omitted


def test_cli_dry_run_sends_nothing(capsys):
    assert main(["sync", "--results", str(ROOT / "eval" / "results"), "--dry-run"]) == 0
    assert "defenses-dev-qwen3-8b" in capsys.readouterr().out


def test_cli_sync_posts_everything_and_exits_zero(api, monkeypatch):
    monkeypatch.setenv("CONSOLE_SERVICE_TOKEN", "tok")
    assert main(["sync", "--results", str(ROOT / "eval" / "results"), "--api", api]) == 0
    assert len(Api.seen) == len(load_results(ROOT / "eval" / "results"))


def test_cli_exit_codes(api, monkeypatch, tmp_path):
    monkeypatch.delenv("CONSOLE_SERVICE_TOKEN", raising=False)
    assert main(["sync", "--results", str(ROOT / "eval" / "results"), "--api", api]) == 2  # no token
    monkeypatch.setenv("CONSOLE_SERVICE_TOKEN", "tok")
    assert main(["sync", "--results", str(tmp_path), "--api", api]) == 1  # nothing to report
    Api.status = 500
    assert main(["sync", "--results", str(ROOT / "eval" / "results"), "--api", api]) == 1  # API failing


@pytest.mark.parametrize("folder", ["d0-dev-qwen3-8b", "defenses-dev-qwen3-8b", "stub-dev"])
def test_counts_match_the_projects_own_asr_table(folder):
    """The reporter must agree with eval.harness.stats.asr_table (the harness's own source of truth)."""
    sys.path.insert(0, str(ROOT))
    from eval.harness import stats

    rows = [json.loads(line) for line in (ROOT / "eval" / "results" / folder / "runs.jsonl").read_text().splitlines() if line.strip()]
    expected = {}
    for r in stats.asr_table(rows):
        a = expected.setdefault((r["model"], r["defense"]), [0, 0])
        a[0] += r["successes"]
        a[1] += r["n"]
    mine = {(r["model"], r["defense"]): [round(r["attack_success_rate"] * r["total_cases"]), r["total_cases"]]
            for r in load_results(ROOT / "eval" / "results") if r["run_key"] == folder}
    assert mine == expected
