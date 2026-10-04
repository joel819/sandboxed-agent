"""Offline checks for the adapter that lets the Ollama-shaped agent.py talk to Groq."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from groq_adapter import _to_openai  # noqa: E402


def test_history_is_translated_to_the_openai_shape():
    history = [
        {"role": "system", "content": "s"},
        {"role": "user", "content": "where is order A101?"},
        # what agent.py appends after a model reply: Ollama-style, arguments are a dict
        {"role": "assistant", "content": "", "tool_calls": [
            {"function": {"name": "get_order", "arguments": {"order_id": "A101"}}},
            {"function": {"name": "search_docs", "arguments": {"query": "refunds"}}}]},
        {"role": "tool", "content": "order A101: status=processing"},
        {"role": "tool", "content": "refunds within 5 days"},
    ]
    out = _to_openai(history)
    calls = out[2]["tool_calls"]
    assert [c["type"] for c in calls] == ["function", "function"]
    assert json.loads(calls[0]["function"]["arguments"]) == {"order_id": "A101"}
    assert calls[0]["id"] != calls[1]["id"]
    # each tool result points at its own call, in order
    assert [out[3]["tool_call_id"], out[4]["tool_call_id"]] == [calls[0]["id"], calls[1]["id"]]
    # the caller's history is not mutated
    assert history[2]["tool_calls"][0]["function"]["arguments"] == {"order_id": "A101"}
    assert "tool_call_id" not in history[3]


def test_string_arguments_are_left_alone():
    history = [{"role": "assistant", "content": "", "tool_calls": [
        {"id": "x1", "function": {"name": "get_order", "arguments": '{"order_id": "A101"}'}}]}]
    assert _to_openai(history)[0]["tool_calls"][0]["function"]["arguments"] == '{"order_id": "A101"}'
    assert _to_openai(history)[0]["tool_calls"][0]["id"] == "x1"
