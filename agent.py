"""Mini harness: agent loop + tool calling + trimming + hard limits, on a local model."""
import json
import sys

import requests

from tools import TOOLS, run_tool

MODEL = "llama3.2"          # <- swap model here, nothing else changes
OLLAMA_URL = "http://localhost:11434/api/chat"
MAX_STEPS = 5                # harness part: hard cap on loop iterations
MAX_TOKENS = 4000            # harness part: spend limit, enforced in code, not the prompt

SYSTEM = (
    "You are SoverGrid's support agent. Use tools to answer questions about "
    "orders and docs. Don't guess — call a tool if you're not sure."
)


def call_model(messages):
    resp = requests.post(
        OLLAMA_URL,
        json={"model": MODEL, "messages": messages, "tools": TOOLS, "stream": False},
    )
    resp.raise_for_status()
    return resp.json()


def run(user_input: str) -> str:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_input}]
    tokens_spent = 0

    for step in range(1, MAX_STEPS + 1):
        data = call_model(messages)
        tokens_spent += data.get("prompt_eval_count", 0) + data.get("eval_count", 0)

        if tokens_spent > MAX_TOKENS:
            return f"[stopped: token budget exceeded at step {step}]"

        msg = data["message"]
        messages.append(msg)

        tool_calls = msg.get("tool_calls")
        if not tool_calls:
            return msg["content"]  # model gave a final answer, no tool needed

        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            result = run_tool(name, args)
            print(f"  [step {step}] {name}({args}) -> {result}", file=sys.stderr)
            messages.append({"role": "tool", "content": result})

    return "[stopped: max steps reached without a final answer]"


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "What's the status of order A101?"
    print(run(question))
