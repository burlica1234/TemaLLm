
import os, sys, re, subprocess
from pathlib import Path
from typing import Optional
from openai import OpenAI

TTS_MODEL  = os.getenv("OPENAI_TTS_MODEL", "gpt-4o-mini-tts")
TTS_VOICE  = os.getenv("OPENAI_TTS_VOICE", "alloy")

TTS_FORMAT = os.getenv("OPENAI_TTS_FORMAT", "mp3").lower()

_client: Optional[OpenAI] = None
def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client

def safe_filename(name: str, default: str = "speech") -> str:
    name = (name or "").strip()
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    return name or default

def _stream_to_file(kwargs: dict, out_path: Path) -> bool:
    """Attempt the streaming variant of the api"""
    client = _get_client()
    try:
        with client.audio.speech.with_streaming_response.create(**kwargs) as resp:
            resp.stream_to_file(out_path)
        return True
    except TypeError:

        return False
    except Exception:
        return False

def synthesize_to_file(text: str, out_path: str = "last_reply") -> str:
    if not text or not text.strip():
        raise ValueError("Empty text for TTS.")


    desired_ext = ".mp3" if TTS_FORMAT == "mp3" else ".wav"
    p = Path(out_path)
    if p.suffix.lower() not in {".mp3", ".wav"}:
        p = p.with_suffix(desired_ext)
    p.parent.mkdir(parents=True, exist_ok=True)

    base_kwargs = dict(model=TTS_MODEL, voice=TTS_VOICE, input=text)


    if _stream_to_file({**base_kwargs, "format": TTS_FORMAT}, p):
        return str(p)


    if _stream_to_file({**base_kwargs, "response_format": TTS_FORMAT}, p):
        return str(p)


    client = _get_client()

    try:
        resp = client.audio.speech.create(**base_kwargs)
        audio_bytes = getattr(resp, "content", None) or resp.to_bytes()

        if p.suffix.lower() == ".mp3":
            p = p.with_suffix(".wav")
        p.write_bytes(audio_bytes)
        return str(p)
    except TypeError:
        pass


    resp = client.audio.speech.create(**{**base_kwargs, "response_format": TTS_FORMAT})
    audio_bytes = getattr(resp, "content", None) or resp.to_bytes()
    p.write_bytes(audio_bytes)
    return str(p)


def play_in_app(path: str, block: bool = False) -> None:
    """ Play audio in the same process """
    if sys.platform.startswith("win"):
        import winsound
        flags = winsound.SND_FILENAME | (0 if block else winsound.SND_ASYNC)
        winsound.PlaySound(path, flags)
    else:
        try:
            import simpleaudio as sa
        except ImportError:
            raise RuntimeError("Install simpleaudio: pip install simpleaudio")
        wave_obj = sa.WaveObject.from_wave_file(path)
        play_obj = wave_obj.play()
        if block:
            play_obj.wait_done()


def play_file(path: str) -> None:
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
