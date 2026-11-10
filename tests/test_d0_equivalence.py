"""D0 must keep the v0 behaviour: same model requests, same tool calls, same push payloads, same reply."""
import copy

import pytest
import requests

import baseline_v0
from agent import run_chat
from backends import RealBackend
from config import Config
from conftest import StubClient, make_response, tool_call
from dispatcher import Dispatcher
from tools import tools

SYSTEM = "SYSTEM PROMPT CANARY"

CONVERSATIONS = {
    "plain_answer": ([make_response("Hello, I am an AI twin.")], "hi", []),
    "lead_capture": ([
        make_response(tool_calls=[tool_call("record_user_details",
                                            {"email": "a@example.com", "name": "Ann", "notes": "wants call"})]),
        make_response("Thanks, recorded."),
    ], "My email is a@example.com", [{"role": "user", "content": "earlier"},
                                      {"role": "assistant", "content": "reply"}]),
    "unknown_question": ([
        make_response(tool_calls=[tool_call("record_unknown_question", {"question": "Favourite colour?"})]),
        make_response("I don't know."),
    ], "Favourite colour?", []),
    "two_tools_then_unknown": ([
        make_response(tool_calls=[tool_call("record_user_details", {"email": "b@example.com"}, "c1"),
                                  tool_call("no_such_tool", {}, "c2")]),
        make_response(tool_calls=[tool_call("record_unknown_question", {"question": "q"}, "c3")]),
        make_response("Done."),
    ], "go", []),
}


class Posts:
    def __init__(self):
        self.calls = []

    def __call__(self, url, data=None, **kw):
        self.calls.append((url, dict(data)))


def normalise(reqs):
    out = []
    for req in reqs:
        msgs = []
        for m in req["messages"]:
            if isinstance(m, dict):
                msgs.append(m)
            else:
                msgs.append({"assistant_tool_calls": [(t.id, t.function.name, t.function.arguments)
                                                      for t in m.tool_calls]})
        out.append({**req, "messages": msgs})
    return out


@pytest.mark.parametrize("name", CONVERSATIONS)
def test_d0_matches_v0(name, monkeypatch):
    script, message, history = CONVERSATIONS[name]
    posts_old, posts_new = Posts(), Posts()

    monkeypatch.setattr(requests, "post", posts_old)
    old_client = StubClient(copy.deepcopy(script))
    old_reply = baseline_v0.chat(old_client, "gpt-5.4-mini", [{"role": "system", "content": SYSTEM}],
                                 tools, message, list(history))

    monkeypatch.setattr(requests, "post", posts_new)
    new_client = StubClient(copy.deepcopy(script))
    cfg = Config()
    new_reply = run_chat(new_client, cfg, SYSTEM, Dispatcher(RealBackend(), cfg), message, list(history))

    assert new_reply == old_reply
    assert normalise(new_client.requests) == normalise(old_client.requests)
    assert posts_new.calls == posts_old.calls
    assert posts_new.calls or name == "plain_answer"
