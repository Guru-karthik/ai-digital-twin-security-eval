"""Tool backends: the only place side effects happen.

RealBackend reproduces the v0 behaviour (Pushover push with the same message text).
MockBackend records every call and never touches the network.
"""
import os
import time
from abc import ABC, abstractmethod

PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


class ToolBackend(ABC):
    @abstractmethod
    def record_user_details(self, email, name="Name not provided", notes="not provided"): ...

    @abstractmethod
    def record_unknown_question(self, question): ...

    def tool_map(self) -> dict:
        return {
            "record_user_details": self.record_user_details,
            "record_unknown_question": self.record_unknown_question,
        }


class RealBackend(ToolBackend):
    def __init__(self):
        # Credentials are read from the environment at call time and never logged.
        pass

    def push(self, text):
        import requests

        requests.post(
            PUSHOVER_URL,
            data={
                "token": os.getenv("PUSHOVER_TOKEN"),
                "user": os.getenv("PUSHOVER_USER"),
                "message": text,
            },
        )

    def record_user_details(self, email, name="Name not provided", notes="not provided"):
        self.push(f"Recording interest from {name} with email {email} and notes {notes}")
        return "OK"

    def record_unknown_question(self, question):
        self.push(f"Recording {question} asked that I couldn't answer")
        return "OK"


class MockBackend(ToolBackend):
    """Records every call; results are configurable (including attacker-controlled strings for E5)."""

    def __init__(self, results=None, clock=time.time):
        self.results = dict(results or {})
        self.calls: list[dict] = []
        self.session = "default"
        self.turn = 0
        self._clock = clock

    def set_context(self, session, turn):
        self.session, self.turn = session, turn

    def _record(self, tool, **arguments):
        self.calls.append({"tool": tool, "arguments": arguments, "session": self.session,
                           "turn": self.turn, "timestamp": self._clock()})
        return self.results.get(tool, "OK")

    def record_user_details(self, email, name="Name not provided", notes="not provided"):
        return self._record("record_user_details", email=email, name=name, notes=notes)

    def record_unknown_question(self, question):
        return self._record("record_unknown_question", question=question)


def make_backend(config) -> ToolBackend:
    return MockBackend() if config.test_mode else RealBackend()
