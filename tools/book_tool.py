
import json
from typing import List, Dict, Optional
import chromadb

from langchain_core.tools import tool
import os


JSON_PATH = "../books.json"
DB_PATH = "../chroma_db2"
COLLECTION = "books_json"
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _load_books() -> List[Dict]:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _get_chroma_collection():
    """
    Use the same collection as for indexing.
    """
    client = chromadb.PersistentClient(path=DB_PATH)
    return client.get_collection(COLLECTION)

def _full_summary_from_chroma(title_exact: str) -> Optional[str]:
    """
    Look up the collection metadata by exact title and return full_summary if available.
    """
    col = _get_chroma_collection()
    res = col.get(where={"title": title_exact})
    if res and res.get("metadatas"):
        metas = res["metadatas"]
        if metas and isinstance(metas, list) and len(metas) > 0 and isinstance(metas[0], dict):
            fs = (metas[0].get("full_summary") or "").strip()
            return fs or None
    return None


def get_summary_by_title_fn(title: str) -> str:
    """
    Return the FULL summary for an EXACT title.
    1) Try to fetch from Chroma (metadata)
    2) Fallback to books.json (full_summary first, then summary)
    """
    title_exact = (title or "").strip()
    if not title_exact:
        return "Error: 'title' is empty."


    try:
        fs = _full_summary_from_chroma(title_exact)
        if fs:
            return fs
    except Exception as e:
        pass


    title_norm = title_exact.lower()
    for b in _load_books():
        if (b.get("title") or "").strip().lower() == title_norm:
            full = (b.get("full_summary") or "").strip()
            short = (b.get("summary") or "").strip()
            if full:
                return full
            return short or "No full summary found for this title."
    return "Title does not exist in the local database."


@tool("get_summary_by_title")
def get_summary_by_title(title: str) -> str:
    """Return the COMPLETE summary for an EXACT title (Chroma -> books.json)."""
    return get_summary_by_title_fn(title)


TOOLS = [get_summary_by_title]
