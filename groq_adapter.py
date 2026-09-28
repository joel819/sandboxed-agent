"""Groq-shaped replacement for agent.call_model(). agent.py itself is never edited -
demo.sh monkey-patches this in so the sandbox demo can reach a real hosted model
without touching the original support-agent code."""
import os

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"  # check console.groq.com/docs/models - Groq's free lineup changes


def call_model(messages):
    """Same input/output contract as agent.call_model, translated to OpenAI's shape."""
    resp = requests.post(
        GROQ_URL,
        headers={"Authorization": f"Bearer {os.environ['GROQ_API_KEY']}"},
        json={"model": GROQ_MODEL, "messages": messages, "tools": TOOLS_FOR_GROQ, "stream": False},
    )
    resp.raise_for_status()
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


def _parse_args(raw):
    import json
    return json.loads(raw) if isinstance(raw, str) else raw


# OpenAI/Groq tool schema is identical to Ollama's - imported lazily to avoid a
# circular import with tools.py at module load time.
from tools import TOOLS as TOOLS_FOR_GROQ
