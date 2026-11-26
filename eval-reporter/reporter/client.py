"""POST run summaries to the console API with the service token (docs/openapi.yaml, POST /api/v1/evaluation-runs)."""
import json
import urllib.error
import urllib.request


def post_run(api_url: str, token: str, run: dict, timeout: float = 10.0) -> str:
    """Returns 'created', 'updated' or raises RuntimeError with a message that never contains the token."""
    req = urllib.request.Request(
        api_url.rstrip("/") + "/api/v1/evaluation-runs",
        data=json.dumps(run).encode(),
        headers={"content-type": "application/json", "accept": "application/json", "authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return "created" if res.status == 201 else "updated"
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"API rejected {run['run_key']}/{run['model']}/{run['defense']}: HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise RuntimeError(f"API unreachable: {type(e).__name__}") from None
