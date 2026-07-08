from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional
import json
import rag
import student_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    rag.setup_db()
    rag.ensure_embeddings()
    rag.load_faculty_index()
    student_db.setup_student_db()
    rag.setup_phd_db()
    rag.ensure_phd_embeddings()
    rag.load_phd_index()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Pydantic models ───────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    university: str = "SUST"
    department: str = ""
    year: str = ""

class LoginRequest(BaseModel):
    email: str
    password: str

class UpdateProfileRequest(BaseModel):
    bio: Optional[str] = None
    university: Optional[str] = None
    department: Optional[str] = None
    year: Optional[str] = None
    research_interests: Optional[str] = None
    research_summary: Optional[str] = None
    certifications: Optional[str] = None
    cv_path: Optional[str] = None

class PostRequest(BaseModel):
    title: str
    content: str = ""
    post_type: str = "work"

class TagRequest(BaseModel):
    tag: str

class SaveFacultyRequest(BaseModel):
    faculty_id: int

class SavePhdRequest(BaseModel):
    phd_student_id: int

class SaveStudentRequest(BaseModel):
    target_student_id: int


# ── Auth helper ───────────────────────────────────────────────────────────

def _require_auth(token: Optional[str]) -> int:
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    student_id = student_db.verify_token(token)
    if not student_id:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return student_id


# ── Health ────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "faculty_count": len(rag.FAC_IDS)}


# ── Faculty RAG search ────────────────────────────────────────────────────

@app.post("/ask")
def ask_endpoint(req: QueryRequest):
    route = rag.classify_query(req.query)
    if route == "out_of_scope":
        return {"answer": rag.OUT_OF_SCOPE_MSG, "candidates": []}

    candidates = rag.retrieve_top_faculty(req.query, k=15)
    answer = rag.generate_answer(req.query, candidates)

    top = [{
        "id":          c["id"],
        "name":        c["name"],
        "designation": c.get("designation", ""),
        "department":  c.get("department", ""),
        "email":       c.get("email", ""),
        "profile_url": c.get("profile_url", ""),
    } for c in candidates[:15]]

    return {
        "answer": answer or "LLM did not return a response. Please retry.",
        "candidates": top,
    }


# ── Auth ──────────────────────────────────────────────────────────────────

@app.post("/auth/signup")
def signup(req: SignupRequest):
    result = student_db.signup(req.name, req.email, req.password,
                               req.university, req.department, req.year)
    if not result["ok"]:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"message": "Account created successfully"}


@app.post("/auth/login")
def login(req: LoginRequest):
    result = student_db.login(req.email, req.password)
    if not result["ok"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result


@app.post("/auth/logout")
def logout(x_token: Optional[str] = Header(None)):
    if x_token:
        student_db.logout(x_token)
    return {"message": "Logged out"}


# ── Student profile ───────────────────────────────────────────────────────

@app.get("/student/{student_id}")
def get_student(student_id: int):
    s = student_db.get_student(student_id)
    if not s:
        raise HTTPException(status_code=404, detail="Student not found")
    return s


@app.put("/student/{student_id}")
def update_student(student_id: int, req: UpdateProfileRequest,
                   x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Cannot edit another student's profile")
    student_db.update_student(
        student_id, 
        bio=req.bio, 
        university=req.university, 
        department=req.department, 
        year=req.year,
        research_interests=req.research_interests,
        research_summary=req.research_summary,
        certifications=req.certifications,
        cv_path=req.cv_path
    )
    return {"message": "Profile updated"}


# ── Posts ──────────────────────────────────────────────────────────────────

@app.post("/student/{student_id}/posts")
def add_post(student_id: int, req: PostRequest, x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.add_post(student_id, req.title, req.content, req.post_type)
    return {"message": "Post added"}


@app.delete("/student/{student_id}/posts/{post_id}")
def delete_post(student_id: int, post_id: int, x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.delete_post(post_id, student_id)
    return {"message": "Post deleted"}


# ── Tags ───────────────────────────────────────────────────────────────────

@app.post("/student/{student_id}/tags")
def add_tag(student_id: int, req: TagRequest, x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.add_tag(student_id, req.tag)
    return {"message": "Tag added"}


@app.delete("/student/{student_id}/tags/{tag_id}")
def delete_tag(student_id: int, tag_id: int, x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.delete_tag(tag_id, student_id)
    return {"message": "Tag deleted"}


# ── Save faculty ───────────────────────────────────────────────────────────

@app.post("/student/{student_id}/save-faculty")
def save_faculty(student_id: int, req: SaveFacultyRequest,
                 x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.save_faculty(student_id, req.faculty_id)
    return {"message": "Faculty saved"}


@app.delete("/student/{student_id}/save-faculty/{faculty_id}")
def unsave_faculty(student_id: int, faculty_id: int,
                   x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.unsave_faculty(student_id, faculty_id)
    return {"message": "Removed"}


@app.get("/student/{student_id}/saved-faculty")
def get_saved_faculty(student_id: int):
    return student_db.get_saved_faculty(student_id)


# ── Save PhD student ───────────────────────────────────────────────────────

@app.post("/student/{student_id}/save-phd")
def save_phd(student_id: int, req: SavePhdRequest,
             x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.save_phd(student_id, req.phd_student_id)
    return {"message": "PhD student saved"}


@app.delete("/student/{student_id}/save-phd/{phd_student_id}")
def unsave_phd(student_id: int, phd_student_id: int,
               x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.unsave_phd(student_id, phd_student_id)
    return {"message": "Removed"}


@app.get("/student/{student_id}/saved-phd")
def get_saved_phd(student_id: int):
    return student_db.get_saved_phd(student_id)


# ── Save registered student ────────────────────────────────────────────────

@app.post("/student/{student_id}/save-student")
def save_student_contact(student_id: int, req: SaveStudentRequest,
                         x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.save_student_contact(student_id, req.target_student_id)
    return {"message": "Student saved"}


@app.delete("/student/{student_id}/save-student/{target_id}")
def unsave_student_contact(student_id: int, target_id: int,
                           x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.unsave_student_contact(student_id, target_id)
    return {"message": "Removed"}


@app.get("/student/{student_id}/saved-students")
def get_saved_students(student_id: int):
    return student_db.get_saved_student_contacts(student_id)


# ── Faculty RAG streaming search ──────────────────────────────────────────

@app.post("/ask-stream")
def ask_stream_endpoint(req: QueryRequest):
    def generate():
        route = rag.classify_query(req.query)
        if route == "out_of_scope":
            yield f"data: {json.dumps({'text': rag.OUT_OF_SCOPE_MSG})}\n\n"
            yield f"data: {json.dumps({'done': True, 'candidates': []})}\n\n"
            return

        candidates = rag.retrieve_top_faculty(req.query, k=15)
        if not candidates:
            yield f"data: {json.dumps({'text': 'No faculty found. Please check the database.'})}\n\n"
            yield f"data: {json.dumps({'done': True, 'candidates': []})}\n\n"
            return

        context  = rag.build_context(candidates)
        user_msg = (
            f"STUDENT QUERY:\n{req.query}\n\n"
            f"FACULTY PROFILES ({len(candidates)} candidates):\n\n{context}"
        )

        for token in rag.stream_llm(rag.ANSWER_SYSTEM, user_msg,
                                     max_tokens=rag._MAX_TOKENS_ANSWER, temperature=0.1):
            yield f"data: {json.dumps({'text': token})}\n\n"

        top = [{
            "id":          c["id"],
            "name":        c["name"],
            "designation": c.get("designation", ""),
            "department":  c.get("department", ""),
            "email":       c.get("email", ""),
            "profile_url": c.get("profile_url", ""),
        } for c in candidates[:15]]
        yield f"data: {json.dumps({'done': True, 'candidates': top})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── PhD student search ─────────────────────────────────────────────────────

@app.post("/ask-phd")
def ask_phd_endpoint(req: QueryRequest):
    return rag.ask_phd(req.query)


@app.post("/ask-phd-stream")
def ask_phd_stream_endpoint(req: QueryRequest):
    def generate():
        route = rag.classify_query_phd(req.query)
        if route == "out_of_scope":
            yield f"data: {json.dumps({'text': rag.PHD_OUT_OF_SCOPE_MSG})}\n\n"
            yield f"data: {json.dumps({'done': True, 'candidates': []})}\n\n"
            return

        candidates = rag.retrieve_top_phd(req.query, k=15)
        if not candidates:
            yield f"data: {json.dumps({'text': 'No PhD students found in the database.'})}\n\n"
            yield f"data: {json.dumps({'done': True, 'candidates': []})}\n\n"
            return

        context  = rag.build_phd_context(candidates)
        user_msg = (
            f"STUDENT QUERY:\n{req.query}\n\n"
            f"PHD STUDENT PROFILES ({len(candidates)} candidates):\n\n{context}"
        )

        for token in rag.stream_llm(rag.PHD_ANSWER_SYSTEM, user_msg,
                                     max_tokens=2000, temperature=0.1):
            yield f"data: {json.dumps({'text': token})}\n\n"

        top = [{
            "id":               c["id"],
            "name":             c["name"],
            "department":       c.get("department", ""),
            "research_area":    c.get("research_area", ""),
            "tags":             c.get("tags", []),
            "email":            c.get("email", ""),
            "supervisor":       c.get("supervisor", ""),
            "similarity_score": c.get("similarity_score", 0),
        } for c in candidates[:15]]
        yield f"data: {json.dumps({'done': True, 'candidates': top})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/phd-students/{phd_id}")
def get_phd_student(phd_id: int):
    s = student_db.get_phd_student(phd_id)
    if not s:
        raise HTTPException(status_code=404, detail="PhD student not found")
    return s


@app.get("/phd-students")
def phd_students(q: str = ""):
    if q.strip():
        return student_db.search_phd_students(q)
    return student_db.get_all_phd_students()
