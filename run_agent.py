"""Demo entrypoint. Wraps agent.py without editing it: swaps in the Groq adapter
when a key is available, otherwise replays a canned trace so the demo still runs
on the free tier with zero setup."""
import os
import sys

import agent

CANNED = {
    "where is order a101?": (
        [("get_order", {"order_id": "A101"},
          "order A101: status=processing, item=GPU node - 1x A6000, total=$300.00")],
        "Order A101 is currently processing — a GPU node (1x A6000), total $300.00.",
    ),
}


def run_canned(question: str) -> str:
    key = question.strip().lower()
    if key not in CANNED:
        return "[canned mode: no recorded response for this question - set GROQ_API_KEY for a live answer]"
    steps, answer = CANNED[key]
    for name, args, result in steps:
        print(f"  [canned step] {name}({args}) -> {result}", file=sys.stderr)
    return answer


if __name__ == "__main__":
    question = sys.argv[1] if len(sys.argv) > 1 else "where is order A101?"

    if os.environ.get("GROQ_API_KEY"):
        import groq_adapter
        agent.call_model = groq_adapter.call_model
        print(agent.run(question))
    else:
        print("[no GROQ_API_KEY set - replaying canned trace]", file=sys.stderr)
        print(run_canned(question))
