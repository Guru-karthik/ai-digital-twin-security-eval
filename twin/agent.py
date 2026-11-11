"""The tool-calling loop, extracted from app.py so a harness can drive it without Gradio."""
import time


def run_chat(client, config, system_prompt, dispatcher, message, history, logger=None, defenses=None,
             base_prompt=None):
    """Same loop as v0 `chat()`. Extra behaviour (iteration cap, hooks, defenses) is off unless configured.

    `defenses` is None for plain D0, which keeps the v0 code path. `system_prompt` is what the model sees (already
    hardened by `defenses.prompt`); `base_prompt` is the unhardened prompt that output checks compare against."""
    t0 = time.time()
    dispatcher.reset()
    if defenses is not None:
        defenses.begin_request(message, history)
        ok, safe = defenses.check_input(message)
        if not ok:
            dispatcher.decisions.extend(defenses.drain_events())
            if logger:
                logger.write(messages=[{"role": "user", "content": message[:200]}], reply=safe, tool_calls=[],
                             decisions=defenses.drain_events(), tokens={"prompt": 0, "completion": 0}, latency_s=0.0)
            return safe
        history = defenses.clean_history(history)
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
        cap = config.max_iterations if config.max_iterations is not None else (
            defenses.max_iterations if defenses is not None else None)
        if cap is not None and iterations > cap:
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
        if defenses is not None:
            reply, decs, regen = defenses.check_output(reply, base_prompt or system_prompt)
            dispatcher.decisions.extend(decs)
            if regen and defenses.policy.regenerate_once:
                kwargs["messages"] = messages + [{"role": "system", "content": defenses.regenerate_note}]
                retry = call().choices[0]
                reply2, decs2, regen2 = defenses.check_output(retry.message.content or "", base_prompt or system_prompt)
                dispatcher.decisions.extend(decs2)
                if regen2:
                    reply, final = defenses.final_block(decs[0]["reason"] if decs else "LEAK")
                    dispatcher.decisions.extend(final)
                else:
                    reply = reply2
            elif regen:
                reply, final = defenses.final_block(decs[0]["reason"] if decs else "LEAK")
                dispatcher.decisions.extend(final)
    if defenses is not None:
        dispatcher.decisions.extend(defenses.drain_events())
    if logger:
        logger.write(messages=messages, reply=reply, tool_calls=dispatcher.tool_calls,
                     decisions=dispatcher.decisions, tokens=tokens,
                     latency_s=round(time.time() - t0, 4))
    return reply
