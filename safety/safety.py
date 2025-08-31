import os, re, json
from typing import Optional

DEFAULT_PATTERNS = [

    r"\b(?:fuck|f\*?uck|f0ck)\b",
    r"\b(?:shit|s\*?hit)\b",
    r"\b(?:bitch|b1tch|bi?tc?h)\b",
    r"\b(?:asshole|a\*?shole)\b",
    r"\b(?:cunt)\b",
    r"\b(?:retard(?:ed)?)\b",
    r"\b(?:nigg(?:er|a))\b",

]


EXTRA = os.getenv("SAFETY_WORDLIST", "")
PATTERNS = [re.compile(p, re.IGNORECASE) for p in DEFAULT_PATTERNS]
if EXTRA and os.path.exists(EXTRA):
    try:
        data = json.load(open(EXTRA, "r", encoding="utf-8"))
        PATTERNS += [re.compile(p, re.IGNORECASE) for p in data.get("patterns", [])]
    except Exception:
        pass


ENABLE_SAFETY = os.getenv("ENABLE_SAFETY", "1") == "1"
SAFE_REPLY = os.getenv(
    "SAFETY_REPLY",
    "I can’t assist with messages that contain offensive language. "
    "Please rephrase your request—I’m happy to help with book recommendations from our database."
)


def is_inappropriate(text: str) -> Optional[str]:

    if not isinstance(text, str) or not text.strip():
        return None
    for pat in PATTERNS:
        if pat.search(text):
            return pat.pattern
    return None