# Smart Librarian

Smart Librarian is a chatbot application that recommends and explains books from a local database.  
It uses LangChain, OpenAI models, and ChromaDB for retrieval-augmented generation (RAG).  
The project includes a web-based interface built with FastAPI (backend) and a simple HTML/JS frontend.

---

## Features

- Retrieval-augmented generation with ChromaDB
- LangChain prompt orchestration
- Tool for retrieving full summaries from `books.json`
- Memory across conversation turns (ConversationBufferMemory)
- Text-to-speech (TTS) and speech-to-text (STT) using OpenAI APIs
- Web interface for interaction with the chatbot

**Note:** Image generation was not implemented.

---

## Requirements

- Python 3.10 or higher
- An OpenAI API key

## How to run

- cd web
- python -m http.server 5500
- uvicorn smart_librarian.api.server:app --reload
- pip install -r requirements.txt
- set environment variables
- python -m indexing.embeddings

