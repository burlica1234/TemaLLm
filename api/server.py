
import os, re, secrets
from typing import Optional
from fastapi import FastAPI, Request, Response, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


from core.client import (
    PROMPT, RAG_INSTRUCTIONS,
    llm_with_tools, llm,
    format_rag_blocks,
    memory,
)
from rag.retriever import retrieve
from tools.book_tool import get_summary_by_title_fn
from safety.safety import is_inappropriate, SAFE_REPLY
from speech.tts import synthesize_to_file, safe_filename
from speech.stt import transcribe_file

from langchain_core.messages import AIMessage, ToolMessage
from openai import OpenAI

STATIC_DIR = os.getenv("STATIC_DIR", "../static")
AUDIO_DIR = os.path.join(STATIC_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

STT_MODEL = os.getenv("STT_MODEL", "whisper-1")
_openai = OpenAI()

app = FastAPI(title="Smart Librarian API ")
#apelam api ul din browser
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_ORIGIN", "http://localhost:5500")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    question: str
    with_audio: bool = False

class ChatResponse(BaseModel):
    text: str
    audio_url: Optional[str] = None

def _extract_title(text: str) -> Optional[str]:
    m = re.search(r"^Recommendation:\s*(.+)$", text, flags=re.IGNORECASE | re.MULTILINE)
    return (m.group(1).strip() if m else None)

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request, response: Response) -> ChatResponse:
    if not request.cookies.get("sid"):
        response.set_cookie("sid", secrets.token_hex(12), httponly=True, samesite="Lax")


    if is_inappropriate(req.question):
        return ChatResponse(text=SAFE_REPLY, audio_url=None)


    blocks = retrieve(req.question, k=5)
    rag_blocks = format_rag_blocks(blocks)


    history_vars = memory.load_memory_variables({})
    history_msgs = history_vars.get("history", [])
    messages = PROMPT.format_messages(
        history=history_msgs,
        user_question=req.question,
        rag_blocks=rag_blocks,
        rag_instructions=RAG_INSTRUCTIONS.strip()
    )


    ai: AIMessage = llm_with_tools.invoke(messages)
    if (not ai.tool_calls) and ("Recommendation:" in (ai.content or "")):
        ai = llm_with_tools.invoke(
            messages,
            tool_choice={"type": "function", "function": {"name": "get_summary_by_title"}}
        )

    if ai.tool_calls:
        tool_messages = []
        for call in ai.tool_calls:
            name = call["name"]; args = call.get("args", {}) or {}
            if name == "get_summary_by_title":
                try:
                    result = get_summary_by_title_fn(**args)
                except Exception as e:
                    result = f"Tool error {name}: {e}"
                tool_messages.append(ToolMessage(content=result, name=name, tool_call_id=call["id"]))
            else:
                tool_messages.append(ToolMessage(content=f"Unknown tool: {name}", name=name, tool_call_id=call["id"]))
        final_ai: AIMessage = llm.invoke(messages + [ai] + tool_messages)
        final_text = final_ai.content or ""
    else:
        final_text = ai.content or ""


    memory.chat_memory.add_user_message(req.question)
    memory.chat_memory.add_ai_message(final_text)


    audio_url = None
    if req.with_audio and final_text.strip().startswith("Recommendation:"):
        title = _extract_title(final_text) or "recommendation"
        filename = f"{safe_filename(title)}.mp3"
        out_path = os.path.join(AUDIO_DIR, filename)
        synthesize_to_file(final_text, out_path=out_path)
        audio_url = f"/static/audio/{filename}"

    return ChatResponse(text=final_text, audio_url=audio_url)


@app.post("/api/transcribe")
async def transcribe(file: UploadFile = File(...)):

    import tempfile, os
    suffix = os.path.splitext(file.filename or "")[1] or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        temp_path = tmp.name

    try:
        text = transcribe_file(temp_path)
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass

    return {"text": text}
