
import os, json
from uuid import uuid5, NAMESPACE_DNS

import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

JSON_PATH = "../books.json"
DB_PATH = "../chroma_db2"
COLLECTION = "books_json"
MODEL = "text-embedding-3-small"

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set.")


client = chromadb.PersistentClient(path=DB_PATH)
embedding_fct = OpenAIEmbeddingFunction(model_name=MODEL, api_key=API_KEY)


collection = client.get_or_create_collection(
    name=COLLECTION,
    embedding_function=embedding_fct,
    metadata={"hnsw:space" : "cosine"}
)


with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)


documents = []
metadatas = []
ids = []

for item in data:
    title = (item.get("title") or "").strip()
    summary = (item.get("summary") or "").strip()
    full_summary = (item.get("full_summary") or "").strip()
    if not title or not summary:
        continue

    stable_key = title.lower().strip()
    ids.append(str(uuid5(NAMESPACE_DNS, stable_key)))

    documents.append(summary)
    metadatas.append({"title": title, "full_summary": full_summary})



collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
print(f"Indexed {len(ids)} items into '{COLLECTION}' at '{DB_PATH}'.")