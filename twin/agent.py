"""The tool-calling loop, extracted from app.py so a harness can drive it without Gradio."""
import time


def run_chat(client, config, system_prompt, dispatcher, message, history, logger=None):
    """Same loop as v0 `chat()`. Extra behaviour (iteration cap, hooks) is off unless configured."""
    t0 = time.time()
    dispatcher.reset()
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": message}]
    kwargs = {"model": config.model, "messages": messages}
    if config.temperature is not None:
        kwargs["temperature"] = config.temperature
    from tools import tools  # schemas

    kwargs["tools"] = tools
    tokens = {"prompt": 0, "completion": 0}

    def call():
        r = client.chat.completions.create(**kwargs)
        usage = getattr(r, "usage", None)
        if usage:
            tokens["prompt"] += getattr(usage, "prompt_tokens", 0) or 0
            tokens["completion"] += getattr(usage, "completion_tokens", 0) or 0
        return r

    response = call()
    iterations = 0
    while response.choices[0].finish_reason == "tool_calls":
        iterations += 1
        if config.max_iterations is not None and iterations > config.max_iterations:
            dispatcher.decisions.append({"decision": "stop", "reason": "ITERATION_CAP"})
            reply = "Sorry, I could not complete that request."
            break
        msg = response.choices[0].message
        results = dispatcher.dispatch(msg.tool_calls)
        messages.append(msg)
        messages.extend(results)
        response = call()
    else:
        reply = response.choices[0].message.content
    if logger:
        logger.write(messages=messages, reply=reply, tool_calls=dispatcher.tool_calls,
                     decisions=dispatcher.decisions, tokens=tokens,
                     latency_s=round(time.time() - t0, 4))
    return reply
