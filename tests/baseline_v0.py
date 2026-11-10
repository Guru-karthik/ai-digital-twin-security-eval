"""Frozen copy of the v0-baseline loop (twin/app.py and twin/tools.py at tag v0-baseline).

Only change: the OpenAI client and `requests.post` are injected/patched so it can run offline.
Do not edit; it is the reference for the D0-equivalence test.
"""
import json
import os

import requests

pushover_url = "https://api.pushover.net/1/messages.json"


def push(text):
    requests.post(
        pushover_url,
        data={"token": os.getenv("PUSHOVER_TOKEN"), "user": os.getenv("PUSHOVER_USER"), "message": text},
    )


def record_user_details(email, name="Name not provided", notes="not provided"):
    push(f"Recording interest from {name} with email {email} and notes {notes}")
    return "OK"


def record_unknown_question(question):
    push(f"Recording {question} asked that I couldn't answer")
    return "OK"


tool_map = {"record_user_details": record_user_details, "record_unknown_question": record_unknown_question}


def handle_tool_calls(tool_calls):
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        print(f"Tool called: {tool_name}", flush=True)
        tool = tool_map.get(tool_name)
        result = tool(**arguments) if tool else "Unknown tool: " + tool_name
        results.append({"role": "tool", "content": json.dumps(result), "tool_call_id": tool_call.id})
    return results


def chat(client, model_name, system, tools, message, history):
    messages = system + history + [{"role": "user", "content": message}]
    response = client.chat.completions.create(model=model_name, messages=messages, tools=tools)
    while response.choices[0].finish_reason == "tool_calls":
        message = response.choices[0].message
        tool_calls = message.tool_calls
        results = handle_tool_calls(tool_calls)
        messages.append(message)
        messages.extend(results)
        response = client.chat.completions.create(model=model_name, messages=messages, tools=tools)
    return response.choices[0].message.content
