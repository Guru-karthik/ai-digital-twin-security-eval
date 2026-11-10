"""Single choke point between a model tool call and its execution.

In D0 this is a pass-through that matches the v0 behaviour exactly. Later defenses
register pre-execution hooks here; a hook returns None to allow or a (reason_code,
message) tuple to block.
"""
import json


class Dispatcher:
    def __init__(self, backend, config, hooks=None):
        self.backend = backend
        self.config = config
        self.hooks = list(hooks or [])
        self.decisions: list[dict] = []  # defense decisions for the current request
        self.tool_calls: list[dict] = []  # executed or attempted calls for the current request

    def reset(self):
        self.decisions, self.tool_calls = [], []

    def dispatch(self, tool_calls):
        results = []
        tool_map = self.backend.tool_map()
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)
            print(f"Tool called: {tool_name}", flush=True)
            self.tool_calls.append({"tool": tool_name, "arguments": arguments})
            blocked = None
            for hook in self.hooks:
                verdict = hook(tool_name, arguments)
                if verdict is not None:
                    blocked = verdict
                    self.decisions.append({"tool": tool_name, "decision": "block", "reason": verdict[0]})
                    break
            if blocked is not None:
                result = blocked[1]
            else:
                tool = tool_map.get(tool_name)
                result = tool(**arguments) if tool else "Unknown tool: " + tool_name
            results.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id})
        return results
