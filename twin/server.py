"""HTTP API around the unchanged `run_chat` loop: POST /chat and GET /health.

This is what the gateway talks to (contract: docs/openapi.yaml and gateway/README.md). It adds no behaviour to the agent:
it builds the same client, defenses and dispatcher as app.py and calls `run_chat`. The agent does not stream, so the
reply is returned whole; the gateway replays it as SSE.
`tool_calls` lists only calls that were executed; calls a defense blocked appear in `decisions`.

Run:  uvicorn server:app --host 0.0.0.0 --port 7861   (from the twin/ directory)
"""
import threading
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from agent import run_chat
from backends import make_backend
from config import load_config
from context import build_system_prompt
from defenses import Defenses
from dispatcher import Dispatcher
from runlog import RunLogger


class Turn(BaseModel):
    """History turns are user/assistant only. A `system` or `tool` role here would let a caller inject instructions."""
    model_config = ConfigDict(extra="forbid")
    role: Literal["user", "assistant"]
    content: str = Field(max_length=8000)


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message: str = Field(min_length=1, max_length=4000)
    history: list[Turn] = Field(default_factory=list, max_length=50)


class ToolCallOut(BaseModel):
    name: str
    arguments: dict


class ChatOut(BaseModel):
    reply: str
    tool_calls: list[ToolCallOut]
    decisions: list[dict]
    defense: str
    model: str


class _Recorder:
    """Wraps the backend for one request and records the calls that actually reach it.

    `dispatcher.tool_calls` also lists calls a defense blocked. Reporting those as tool calls would let the gateway
    store a lead for a blocked injection attempt, so only executed calls are reported; blocked attempts appear in
    `decisions` instead."""

    def __init__(self, inner):
        self.inner, self.executed = inner, []

    def tool_map(self):
        def wrap(name, fn):
            def call(**kwargs):
                self.executed.append(ToolCallOut(name=name, arguments=kwargs))
                return fn(**kwargs)
            return call
        return {name: wrap(name, fn) for name, fn in self.inner.tool_map().items()}


def create_app(config=None, client=None, backend=None, system_prompt=None, base_prompt=None) -> FastAPI:
    """Everything is injectable so tests need no network, API key or personal documents."""
    config = config or load_config()
    if client is None:
        from openai import OpenAI

        client = OpenAI()
    base_prompt = base_prompt or system_prompt or build_system_prompt()
    defenses = Defenses.from_config(config, canaries=config.extra.get("canaries", ()))  # None at D0
    system_prompt = system_prompt or (defenses.prompt(base_prompt) if defenses else base_prompt)
    backend = backend or make_backend(config)
    logger = RunLogger(path=config.log_path, config=config)
    # Defenses keep per-request state on a shared object, so requests are served one at a time.
    lock = threading.Lock()

    app = FastAPI(title="twin-api", docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "twin-api"}

    @app.post("/chat", response_model=ChatOut)
    def chat(body: ChatIn):
        history = [t.model_dump() for t in body.history]
        recorder = _Recorder(backend)
        dispatcher = Dispatcher.with_defenses(recorder, config, defenses)  # per request
        try:
            with lock:
                reply = run_chat(client, config, system_prompt, dispatcher, body.message, history, logger,
                                 defenses=defenses, base_prompt=base_prompt)
                calls = list(recorder.executed)
                decisions = list(dispatcher.decisions)
        except Exception as exc:  # model/provider failure: do not leak details to the caller
            print(f"chat failed: {type(exc).__name__}", flush=True)
            raise HTTPException(status_code=502, detail="The model is unavailable.") from None
        return ChatOut(reply=reply or "", tool_calls=calls, decisions=decisions, defense=config.defense,
                       model=config.model)

    return app


def _lazy_app():
    # `uvicorn server:app` builds the app on first import; tests call create_app() directly instead.
    from dotenv import load_dotenv

    load_dotenv(override=True)
    return create_app()


def __getattr__(name):
    if name == "app":
        globals()["app"] = _lazy_app()
        return globals()["app"]
    raise AttributeError(name)
