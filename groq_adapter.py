"""Groq-shaped replacement for agent.call_model(). agent.py itself is never edited -
demo.sh monkey-patches this in so the sandbox demo can reach a real hosted model
without touching the original support-agent code."""
import json
import os

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
# Groq retires models over time (llama-3.1-8b-instant and llama-3.3-70b-versatile are gone), so
# this is overridable: GROQ_MODEL=<id>. Current list: console.groq.com/docs/models
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")


def call_model(messages):
    """Same input/output contract as agent.call_model, translated to OpenAI's shape."""
    # OpenAI/Groq tool schema is identical to Ollama's. Imported here, not at module load, because
    # importing tools.py opens the vector store (which needs the seeded chroma_db).
    from tools import TOOLS as TOOLS_FOR_GROQ

    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={"model": GROQ_MODEL, "messages": _to_openai(messages), "tools": TOOLS_FOR_GROQ, "stream": False},
        timeout=30,
    )
    if not resp.ok:  # include the API's own message (e.g. model_not_found) instead of a bare status code
        raise RuntimeError(f"Groq API error {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    choice = data["choices"][0]["message"]

    # normalize back to the {message, prompt_eval_count, eval_count} shape agent.run() expects
    tool_calls = None
    if choice.get("tool_calls"):
        tool_calls = [
            {"function": {"name": c["function"]["name"], "arguments": _parse_args(c["function"]["arguments"])}}
            for c in choice["tool_calls"]
        ]
    message = {"role": "assistant", "content": choice.get("content") or ""}
    if tool_calls:
        message["tool_calls"] = tool_calls

    usage = data.get("usage", {})
    return {
        "message": message,
        "prompt_eval_count": usage.get("prompt_tokens", 0),
        "eval_count": usage.get("completion_tokens", 0),
    }


def _to_openai(messages):
    """agent.py keeps its history in Ollama's shape: tool-call arguments are dicts and tool results
    carry no id. OpenAI-compatible APIs need arguments as a JSON string, an id on every tool call,
    and a matching tool_call_id on every tool result. Translate on the way out; agent.py is untouched."""
    out, pending = [], []
    for m in messages:
        m = dict(m)
        if m.get("role") == "assistant" and m.get("tool_calls"):
            calls = []
            for i, c in enumerate(m["tool_calls"]):
                args = c["function"]["arguments"]
                call_id = c.get("id") or f"call_{len(out)}_{i}"
                calls.append({"id": call_id, "type": "function", "function": {
                    "name": c["function"]["name"], "arguments": args if isinstance(args, str) else json.dumps(args)}})
            pending = [c["id"] for c in calls]
            m["tool_calls"] = calls
        elif m.get("role") == "tool" and "tool_call_id" not in m and pending:
            m["tool_call_id"] = pending.pop(0)
        out.append(m)
    return out


def _parse_args(raw):
    return json.loads(raw) if isinstance(raw, str) else raw
