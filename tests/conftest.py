import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "twin"))
sys.path.insert(0, str(ROOT / "tests"))

FAKE_SECRETS = {"OPENAI_API_KEY": "sk-FAKE0000000000000000test", "PUSHOVER_TOKEN": "FAKE-token-123456",
                "PUSHOVER_USER": "FAKE-user-123456"}


@pytest.fixture(autouse=True)
def fake_env(monkeypatch):
    for k, v in FAKE_SECRETS.items():
        monkeypatch.setenv(k, v)


def make_response(content=None, tool_calls=None, usage=(10, 5)):
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(
        choices=[SimpleNamespace(message=msg, finish_reason="tool_calls" if tool_calls else "stop")],
        usage=SimpleNamespace(prompt_tokens=usage[0], completion_tokens=usage[1]),
    )


def tool_call(name, args, id_="call_1"):
    return SimpleNamespace(id=id_, function=SimpleNamespace(name=name, arguments=json.dumps(args)))


class StubClient:
    """Scripted model: returns queued responses and records every create() call."""

    def __init__(self, responses):
        self.responses, self.requests = list(responses), []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append({k: (list(v) if k == "messages" else v) for k, v in kwargs.items()})
        return self.responses.pop(0)


@pytest.fixture
def fake_cv(tmp_path):
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(72, 750, "Fake Person - ML engineer. CANARY-CV-0001")
    c.save()
    pdf = tmp_path / "cv.pdf"
    pdf.write_bytes(buf.getvalue())
    txt = tmp_path / "summary.txt"
    txt.write_text("Fake summary. CANARY-SUM-0001", encoding="utf-8")
    return pdf, txt
