"""Tool schemas (what the model sees) + implementations (what actually runs)."""
import sqlite3
import chromadb

TRIM_CHARS = 300  # harness part: cap tool output before it re-enters context

_chroma = chromadb.PersistentClient(path="./chroma_db").get_collection("docs")

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Semantic search over SoverGrid FAQ/docs.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Look up one order by its exact ID.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"],
            },
        },
    },
]


def search_docs(query: str) -> str:
    res = _chroma.query(query_texts=[query], n_results=2)
    return " | ".join(res["documents"][0]) if res["documents"][0] else "no matches"


def get_order(order_id: str) -> str:
    conn = sqlite3.connect("orders.db")
    row = conn.execute(
        "SELECT id, status, item, total FROM orders WHERE id = ?", (order_id,)
    ).fetchone()
    conn.close()
    if not row:
        return f"no order found for id {order_id}"
    return f"order {row[0]}: status={row[1]}, item={row[2]}, total=${row[3]:.2f}"


DISPATCH = {"search_docs": search_docs, "get_order": get_order}


def run_tool(name: str, args: dict) -> str:
    if name not in DISPATCH:
        return f"error: unknown tool {name}"
    try:
        result = DISPATCH[name](**args)
    except Exception as e:
        # model-generated args are untrusted input - malformed calls must not crash the loop
        return f"error: bad arguments for {name}: {e}"
    return result[:TRIM_CHARS]  # trim before it goes back into the context window
