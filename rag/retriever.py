
import os
from functools import lru_cache
from typing import List, Dict
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

DB_PATH = os.getenv("CHROMA_DB_PATH", "../chroma_db2")
COLLECTION = os.getenv("CHROMA_COLLECTION", "books_json")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set.")

@lru_cache(maxsize=1)
def _collection():
    """
    Create and cache a ChromaDB collection object with the embedding function.
    Cached so it is instantiated only once per process.
    """
    client = chromadb.PersistentClient(path=DB_PATH)
    ef = OpenAIEmbeddingFunction(api_key=OPENAI_API_KEY, model_name=EMBED_MODEL)
    return client.get_collection(COLLECTION, embedding_function=ef)

def retrieve(query: str, k: int = 5) -> List[Dict]:
    """
    Perform a semantic search in ChromaDB and return a list of blocks
    containing {title, summary, distance}, which will be used in the RAG_CONTEXT
    section of the prompt.
    """
    if not isinstance(query, str) or not query.strip():
        return []
    q = _collection().query(
        query_texts=[query],
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    docs = (q.get("documents") or [[]])[0]
    metas = (q.get("metadatas") or [[]])[0]
    dists = (q.get("distances") or [[]])[0]

    blocks: List[Dict] = []
    for doc, meta, dist in zip(docs, metas, dists):
        title = (meta.get("title") or "").strip()
        summary = (doc or "").strip()
        if title and summary:
            blocks.append({"title": title, "summary": summary, "distance": float(dist)})
    return blocks
