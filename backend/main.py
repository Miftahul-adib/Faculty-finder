# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from contextlib import asynccontextmanager
import rag

@asynccontextmanager
async def lifespan(app: FastAPI):
    rag.setup_db()
    rag.ensure_embeddings()
    rag.load_faculty_index()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.get("/health")
def health():
    return {"status": "ok", "faculty_count": len(rag.FAC_IDS)}

@app.post("/ask")
def ask_endpoint(req: QueryRequest):
    answer = rag.ask(req.query)
    return {"answer": answer}