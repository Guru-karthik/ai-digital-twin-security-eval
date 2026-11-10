"""Preflight for a real model: does it answer, call tools, and accept the configured temperature?

Costs a few cents at most for hosted models. NOT run by CI or tests. Usage:
  PYTHONPATH=. python -m eval.harness.preflight local-qwen3-14b
"""
import sys

from . import runner

TOOL = {"type": "function", "function": {
    "name": "record_unknown_question", "description": "Record a question you cannot answer",
    "parameters": {"type": "object", "properties": {"question": {"type": "string"}}, "required": ["question"]}}}


def main(name):
    spec = runner.load_models()[name]
    client = runner.make_client(spec)
    model = spec.get("model", name)
    report = {"model": name, "reachable": False, "tool_call": False, "temperature_ok": None}
    msgs = [{"role": "user", "content": "I do not know the answer to 'favourite colour?'. Record that question with your tool."}]
    try:
        r = client.chat.completions.create(model=model, messages=msgs, tools=[TOOL])
        report["reachable"] = True
        report["response_model"] = getattr(r, "model", None)
        report["tool_call"] = bool(r.choices[0].message.tool_calls)
        if spec.get("temperature") is not None:
            try:
                client.chat.completions.create(model=model, messages=msgs[:1], temperature=spec["temperature"],
                                               max_tokens=16)
                report["temperature_ok"] = True
            except Exception as e:  # noqa: BLE001 - report any API rejection
                report["temperature_ok"] = f"rejected: {type(e).__name__}"
    except Exception as e:  # noqa: BLE001
        report["error"] = type(e).__name__
    print(report)


if __name__ == "__main__":
    main(sys.argv[1])
