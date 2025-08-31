
import os
from typing import Optional
from openai import OpenAI

DEFAULT_STT_MODEL = os.getenv("STT_MODEL", "whisper-1")

_client: Optional[OpenAI] = None
def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client

def transcribe_file(file_path: str, *, model: Optional[str] = None) -> str:
    """
    Transcribe an audio file from disk (wav/mp3/webm/ogg/etc).
    Returns plain text (response_format='text').
    Raises an exception if the API call fails.
    """
    mdl = model or DEFAULT_STT_MODEL
    client = _get_client()
    with open(file_path, "rb") as f:
        resp = client.audio.transcriptions.create(
            model=mdl,
            file=f,
            response_format="text",
        )
    return str(resp)

def transcribe_bytes(data: bytes, filename: str = "audio.webm", *, model: Optional[str] = None) -> str:
    """
    Transcribe audio directly from raw bytes (without writing to disk).
    Useful for in-memory recordings or uploaded blobs.
    """
    import io
    mdl = model or DEFAULT_STT_MODEL
    client = _get_client()
    buf = io.BytesIO(data)
    buf.name = filename
    resp = client.audio.transcriptions.create(
        model=mdl,
        file=buf,
        response_format="text",
    )
    return str(resp)
