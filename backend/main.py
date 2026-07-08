from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
from contextlib import asynccontextmanager
from typing import Optional
import base64
import binascii
import json
import re
import rag
import student_db

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
# Letters (incl. accented), spaces, dots, hyphens, apostrophes — no digits/symbols.
NAME_RE  = re.compile(r"^(?=.*[^\W\d_])(?:[^\W\d_]|[ .'\-])+$", re.UNICODE)


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

class CvUploadRequest(BaseModel):
    filename: str
    data_b64: str

class PhotoUploadRequest(BaseModel):
    data_b64: str
    mime: str = "image/jpeg"

class DocumentUploadRequest(BaseModel):
    filename: str
    label: str = ""
    data_b64: str

class PostRequest(BaseModel):
    title: str
    content: str = ""
    post_type: str = "work"
    image_b64: Optional[str] = None
    image_mime: str = "image/jpeg"

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
        "profile_url": c.get("profile_url", ""),
    } for c in candidates[:15]]

    return {
        "answer": answer or "LLM did not return a response. Please retry.",
        "candidates": top,
    }


# ── Auth ──────────────────────────────────────────────────────────────────

@app.post("/auth/signup")
def signup(req: SignupRequest):
    name  = req.name.strip()
    email = req.email.strip().lower()
    if not name or not NAME_RE.fullmatch(name):
        raise HTTPException(status_code=400,
                            detail="Full name can only contain letters, spaces, dots, hyphens and apostrophes — no numbers.")
    if not EMAIL_RE.fullmatch(email):
        raise HTTPException(status_code=400,
                            detail="Please enter a valid email address (e.g. you@sust.edu).")
    if len(req.password) < 6:
        raise HTTPException(status_code=400,
                            detail="Password must be at least 6 characters.")
    result = student_db.signup(name, email, req.password,
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
    student_db.update_student(student_id, req.bio, req.university, req.department, req.year,
                              req.research_interests, req.research_summary)
    return {"message": "Profile updated"}


# ── CV upload / download ───────────────────────────────────────────────────

_CV_ALLOWED_EXT = {".pdf", ".doc", ".docx"}
_CV_MAX_BYTES   = 5 * 1024 * 1024  # 5 MB


@app.post("/student/{student_id}/cv")
def upload_cv(student_id: int, req: CvUploadRequest,
              x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    fname = req.filename.strip().replace("\\", "/").split("/")[-1]
    ext = ("." + fname.rsplit(".", 1)[-1].lower()) if "." in fname else ""
    if ext not in _CV_ALLOWED_EXT:
        raise HTTPException(status_code=400, detail="CV must be a PDF, DOC or DOCX file.")
    try:
        data = base64.b64decode(req.data_b64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Invalid file data.")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > _CV_MAX_BYTES:
        raise HTTPException(status_code=400, detail="CV file must be under 5 MB.")
    student_db.save_cv(student_id, fname, data)
    return {"message": "CV uploaded"}


@app.get("/student/{student_id}/cv")
def download_cv(student_id: int):
    cv = student_db.get_cv(student_id)
    if not cv:
        raise HTTPException(status_code=404, detail="No CV uploaded")
    filename, data = cv
    media = "application/pdf" if filename.lower().endswith(".pdf") else "application/octet-stream"
    return Response(content=data, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@app.delete("/student/{student_id}/cv")
def remove_cv(student_id: int, x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.delete_cv(student_id)
    return {"message": "CV removed"}


# ── Profile photo ──────────────────────────────────────────────────────────

_PHOTO_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
_PHOTO_MAX_BYTES    = 2 * 1024 * 1024  # 2 MB (frontend resizes before upload)


@app.post("/student/{student_id}/photo")
def upload_photo(student_id: int, req: PhotoUploadRequest,
                 x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if req.mime not in _PHOTO_ALLOWED_MIME:
        raise HTTPException(status_code=400, detail="Photo must be JPEG, PNG or WebP.")
    try:
        data = base64.b64decode(req.data_b64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Invalid image data.")
    if not data:
        raise HTTPException(status_code=400, detail="Empty image.")
    if len(data) > _PHOTO_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Photo must be under 2 MB.")
    student_db.save_photo(student_id, data, req.mime)
    return {"message": "Photo updated"}


@app.get("/student/{student_id}/photo")
def get_photo(student_id: int):
    photo = student_db.get_photo(student_id)
    if not photo:
        raise HTTPException(status_code=404, detail="No photo")
    data, mime = photo
    return Response(content=data, media_type=mime)


@app.delete("/student/{student_id}/photo")
def remove_photo(student_id: int, x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.delete_photo(student_id)
    return {"message": "Photo removed"}


# ── Documents ──────────────────────────────────────────────────────────────

_DOC_ALLOWED_EXT = {".pdf", ".doc", ".docx", ".ppt", ".pptx", ".txt",
                    ".png", ".jpg", ".jpeg"}
_DOC_MAX_BYTES   = 10 * 1024 * 1024  # 10 MB
_DOC_MIME = {
    ".pdf": "application/pdf", ".txt": "text/plain",
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
}


@app.post("/student/{student_id}/documents")
def upload_document(student_id: int, req: DocumentUploadRequest,
                    x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    fname = req.filename.strip().replace("\\", "/").split("/")[-1]
    ext = ("." + fname.rsplit(".", 1)[-1].lower()) if "." in fname else ""
    if ext not in _DOC_ALLOWED_EXT:
        raise HTTPException(status_code=400,
                            detail="Allowed types: PDF, DOC, DOCX, PPT, PPTX, TXT, PNG, JPG.")
    try:
        data = base64.b64decode(req.data_b64, validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail="Invalid file data.")
    if not data:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(data) > _DOC_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Documents must be under 10 MB.")
    mime = _DOC_MIME.get(ext, "application/octet-stream")
    student_db.add_document(student_id, fname, req.label.strip(), mime, data)
    return {"message": "Document uploaded"}


@app.get("/student/{student_id}/documents/{doc_id}")
def download_document(student_id: int, doc_id: int):
    doc = student_db.get_document(doc_id)
    if not doc or doc["student_id"] != student_id:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(content=doc["data"], media_type=doc["mime"],
                    headers={"Content-Disposition": f'attachment; filename="{doc["filename"]}"'})


@app.delete("/student/{student_id}/documents/{doc_id}")
def remove_document(student_id: int, doc_id: int,
                    x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    student_db.delete_document(doc_id, student_id)
    return {"message": "Document removed"}


# ── Home feed ──────────────────────────────────────────────────────────────

@app.get("/student/{student_id}/feed")
def student_feed(student_id: int, x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return student_db.get_feed(student_id)


# ── Posts ──────────────────────────────────────────────────────────────────

_POST_IMG_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
_POST_IMG_MAX_BYTES    = 3 * 1024 * 1024  # 3 MB (frontend resizes before upload)


@app.post("/student/{student_id}/posts")
def add_post(student_id: int, req: PostRequest, x_token: Optional[str] = Header(None)):
    auth_id = _require_auth(x_token)
    if auth_id != student_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    image_data = None
    if req.image_b64:
        if req.image_mime not in _POST_IMG_ALLOWED_MIME:
            raise HTTPException(status_code=400, detail="Image must be JPEG, PNG or WebP.")
        try:
            image_data = base64.b64decode(req.image_b64, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(status_code=400, detail="Invalid image data.")
        if len(image_data) > _POST_IMG_MAX_BYTES:
            raise HTTPException(status_code=400, detail="Post image must be under 3 MB.")
    student_db.add_post(student_id, req.title, req.content, req.post_type,
                        image_data, req.image_mime if image_data else "")
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
