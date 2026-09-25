"""FastAPI server: retrieval, chat, and graph-summary endpoints."""
import json
import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingest.embed import load_config
from server.rag_core import get_context, chat as rag_chat

app = FastAPI(title="immunolit-rag API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://jluthy.github.io"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

CFG = load_config()


class SearchRequest(BaseModel):
    query: str
    k: int | None = None


class ChatRequest(BaseModel):
    query: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/search")
def search(req: SearchRequest):
    k = req.k or CFG["rag"]["retrieval_k"]
    return {"results": get_context(req.query, CFG, k)}


@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    result = rag_chat(req.query, CFG)
    return {"answer": result["answer"], "citations": result["citations"]}


@app.get("/api/graph/summary")
def graph_summary():
    path = os.path.join(CFG["paths"]["graph_dir"], "graph_summary.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="graph summary not yet built")
    with open(path) as f:
        return json.load(f)
