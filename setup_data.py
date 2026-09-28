"""One-time setup: seed SQLite orders + Chroma docs. Run once before agent.py."""
import sqlite3
import chromadb

# --- structured data: SQLite ---
conn = sqlite3.connect("orders.db")
conn.execute("DROP TABLE IF EXISTS orders")
conn.execute("CREATE TABLE orders (id TEXT PRIMARY KEY, status TEXT, item TEXT, total REAL)")
conn.executemany(
    "INSERT INTO orders VALUES (?, ?, ?, ?)",
    [
        ("A100", "shipped", "GPU node - 4x A100", 1200.00),
        ("A101", "processing", "GPU node - 1x A6000", 300.00),
        ("A102", "delivered", "CPU node - 32 core", 80.00),
    ],
)
conn.commit()
conn.close()

# --- unstructured data: Chroma (default embedding fn = all-MiniLM-L6-v2 via ONNX) ---
client = chromadb.PersistentClient(path="./chroma_db")
client.delete_collection("docs") if "docs" in [c.name for c in client.list_collections()] else None
coll = client.create_collection("docs")
coll.add(
    ids=["doc1", "doc2", "doc3"],
    documents=[
        "SoverGrid routes compute jobs to the cheapest available node meeting the job's latency and hardware requirements.",
        "Refunds are issued within 5 business days after a node fails a job's health check and the job is retried elsewhere.",
        "Node providers are paid out weekly in USDC once their uptime for the week is verified against the monitoring log.",
    ],
)
print("Seeded orders.db and chroma_db/")
