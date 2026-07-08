"""
SUST Faculty Finder — RAG core
Converted from v12 notebook (Gemma 4 via HuggingFace Inference API).
Config is read from .env — HF_TOKEN is never hardcoded here.
Embeddings now use HF Inference API — no sentence-transformers / torch needed.
"""
# backend/rag.py

import os, struct, gc, time
from collections import defaultdict
from dotenv import load_dotenv
import numpy as np
from huggingface_hub import InferenceClient, login as hf_login
import requests
import json
from db import get_conn, col_exists

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════
#  SETTINGS
# ══════════════════════════════════════════════════════════════════════════
HF_TOKEN           = os.environ.get("HF_TOKEN", "")
DEEPSEEK_API_KEY   = os.environ.get("DEEPSEEK_API_KEY", "")
USE_DEEPSEEK       = os.getenv("USE_DEEPSEEK", "true").lower() == "true"
DEEPSEEK_MODEL     = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
LLM_MODEL          = os.getenv("LLM_MODEL", "deepseek-chat")
EMBED_MODEL_NAME   = os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
TOP_K              = 25
DEBUG              = os.getenv("DEBUG", "false").lower() == "true"
MAX_RETRIES        = 2
_MAX_TOKENS_ROUTER = 20
_MAX_TOKENS_ANSWER = 5000

# ══════════════════════════════════════════════════════════════════════════
#  CLIENT INITIALIZATION
# ══════════════════════════════════════════════════════════════════════════
hf_login(token=HF_TOKEN, add_to_git_credential=False)
hf_client = InferenceClient(token=HF_TOKEN)  # used for embeddings regardless of LLM backend

if USE_DEEPSEEK:
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY environment variable is required")
    print(f"[OK] Using DeepSeek API | model: {DEEPSEEK_MODEL}")
    deepseek_client = None  # Will use requests directly
else:
    print(f"[OK] Using HuggingFace | model: {LLM_MODEL}")

print(f"Embedding model : {EMBED_MODEL_NAME} (via HF Inference API)")


# ══════════════════════════════════════════════════════════════════════════
#  DEEPSEEK LLM CALL HELPER
# ══════════════════════════════════════════════════════════════════════════
def deepseek_call(system_prompt: str, user_content: str, max_tokens: int = 5000, temperature: float = 0.1) -> str:
    """Call DeepSeek API."""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "max_tokens": max_tokens,
        "temperature": max(temperature, 0.01),
        "stream": False
    }
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        if DEBUG:
            print(f"DeepSeek error: {e}")
        raise


def deepseek_stream(system_prompt: str, user_content: str, max_tokens: int = 5000, temperature: float = 0.1):
    """Stream from DeepSeek API."""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "max_tokens": max_tokens,
        "temperature": max(temperature, 0.01),
        "stream": True
    }
    try:
        resp = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload,
            timeout=60,
            stream=True
        )
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            line = line.decode("utf-8") if isinstance(line, bytes) else line
            if line.startswith("data: "):
                try:
                    chunk = json.loads(line[6:])
                    token = chunk["choices"][0]["delta"].get("content", "")
                    if token:
                        yield token
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        if DEBUG:
            print(f"DeepSeek stream error: {e}")
        raise

# ══════════════════════════════════════════════════════════════════════════
#  EMBEDDING HELPER  (replaces SentenceTransformer)
# ══════════════════════════════════════════════════════════════════════════
def hf_embed(texts: list) -> np.ndarray:
    """
    Embed a list of texts via HF Inference API.
    Returns an L2-normalised float32 array of shape (len(texts), hidden_dim).

    Handles both return shapes from the API:
      - 2-D (batch, hidden)       → sentence-level, use directly
      - 3-D (batch, seq, hidden)  → token-level, mean-pool first
    """
    result = hf_client.feature_extraction(texts, model=EMBED_MODEL_NAME)
    arr = np.array(result, dtype=np.float32)

    # Mean-pool token dimension if the API returns token-level embeddings
    if arr.ndim == 3:
        arr = arr.mean(axis=1)

    # L2 normalise (mirrors normalize_embeddings=True in SentenceTransformer)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    arr = arr / np.where(norms == 0, 1.0, norms)
    return arr

# ══════════════════════════════════════════════════════════════════════════
#  CELL 2 — DB SCHEMA SETUP  (connection comes from db.get_conn — MySQL)
# ══════════════════════════════════════════════════════════════════════════
def setup_db():
    """Add embedding column if missing. Print quick stats. Mirrors Cell 2."""
    with get_conn() as con:
        if not col_exists(con, "faculty", "embedding"):
            con.execute("ALTER TABLE faculty ADD COLUMN embedding LONGBLOB")
            con.commit()
            print("  + faculty.embedding column added")
        else:
            print("  faculty.embedding column already present")

        total   = con.execute("SELECT COUNT(*) AS n FROM faculty").fetchone()["n"]
        has_sum = con.execute(
            "SELECT COUNT(*) AS n FROM faculty WHERE research_summary IS NOT NULL AND TRIM(research_summary) != ''"
        ).fetchone()["n"]
        has_emb = con.execute(
            "SELECT COUNT(*) AS n FROM faculty WHERE embedding IS NOT NULL"
        ).fetchone()["n"]

    print(f"\nFaculty total          : {total}")
    print(f"With research_summary  : {has_sum}  ({100*has_sum//max(total,1)}%)")
    print(f"With embedding         : {has_emb}  ({100*has_emb//max(total,1)}%)")
    print("DB setup OK")

# ══════════════════════════════════════════════════════════════════════════
#  CELL 3 — COMPUTE FACULTY EMBEDDINGS
# ══════════════════════════════════════════════════════════════════════════
def vec_to_blob(vec) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec.tolist())

def blob_to_vec(blob: bytes) -> np.ndarray:
    n = len(blob) // 4
    return np.array(struct.unpack(f"{n}f", blob), dtype=np.float32)

def build_embed_text(row, interests: list) -> str:
    """
    Build the text to embed for a faculty member.
    Priority: research_summary → interests + bio fallback.
    """
    summary = (row["research_summary"] or "").strip()
    if summary:
        return summary[:1000]
    parts = []
    if row["name"]:        parts.append(row["name"])
    if row["designation"]: parts.append(row["designation"])
    if interests:          parts.append("Research: " + "; ".join(interests))
    bio = (row["biography"] or "").strip()
    if bio:                parts.append(bio[:300])
    return " | ".join(parts)

def ensure_embeddings():
    """Compute embeddings for any faculty that are missing them. Mirrors Cell 3."""
    with get_conn() as con:
        pending = [r["id"] for r in con.execute(
            "SELECT id FROM faculty WHERE embedding IS NULL"
        ).fetchall()]

    print(f"Faculty needing embeddings: {len(pending)}")
    if not pending:
        print("All faculty already have embeddings — skipping.")
        return

    total_p = len(pending)
    done    = 0
    t0      = time.time()

    for start in range(0, total_p, 64):
        batch_ids = pending[start:start+64]
        ph = ",".join(["%s"] * len(batch_ids))

        with get_conn() as con:
            rows = con.execute(
                f"SELECT id, name, designation, biography, research_summary FROM faculty WHERE id IN ({ph})",
                batch_ids
            ).fetchall()
            interests_map = defaultdict(list)
            for ir in con.execute(
                f"SELECT faculty_id, interest FROM research_interests WHERE faculty_id IN ({ph})",
                batch_ids
            ).fetchall():
                interests_map[ir["faculty_id"]].append(ir["interest"])

        texts = [build_embed_text(r, interests_map[r["id"]]) for r in rows]

        # ── CHANGED: hf_embed() instead of embed_model.encode() ───────────
        vecs = hf_embed(texts)

        with get_conn() as con:
            for row, vec in zip(rows, vecs):
                con.execute(
                    "UPDATE faculty SET embedding=%s WHERE id=%s",
                    (vec_to_blob(vec), row["id"])
                )
            con.commit()

        done += len(batch_ids)
        print(f"  Embedded {done}/{total_p} ...", end="\r")

    print(f"\nAll {total_p} embeddings computed in {time.time()-t0:.1f}s")

# ══════════════════════════════════════════════════════════════════════════
#  CELL 4 — LOAD FACULTY INDEX INTO MEMORY (module-level globals)
# ══════════════════════════════════════════════════════════════════════════
FAC_IDS    = []
FAC_MATRIX = None

def load_faculty_index():
    """Load all faculty embeddings into RAM. Mirrors Cell 4."""
    global FAC_IDS, FAC_MATRIX
    with get_conn() as con:
        rows = con.execute(
            "SELECT id, embedding FROM faculty WHERE embedding IS NOT NULL"
        ).fetchall()
    FAC_IDS    = [r["id"] for r in rows]
    FAC_MATRIX = np.stack([blob_to_vec(r["embedding"]) for r in rows])
    print(f"Faculty index loaded: {len(FAC_IDS)} faculty vectors ({FAC_MATRIX.shape})")

# ══════════════════════════════════════════════════════════════════════════
#  CELL 5 — LLM WRAPPER (Gemma 4 via HF API + DeepSeek)
# ══════════════════════════════════════════════════════════════════════════
def llm_call(
    system_prompt: str,
    user_content:  str,
    max_tokens:    int   = 600,
    temperature:   float = 0.1,
    label:         str   = "",
) -> str:
    """
    Call LLM (DeepSeek or HuggingFace).
    Supports both APIs transparently based on USE_DEEPSEEK flag.
    """
    if USE_DEEPSEEK:
        try:
            return deepseek_call(system_prompt, user_content, max_tokens, temperature)
        except Exception as e:
            print(f"  [LLM] {label} DeepSeek error: {e}")
            raise
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_content},
        ]
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = hf_client.chat.completions.create(
                    model=LLM_MODEL,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=max(temperature, 0.01),
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                print(f"  [LLM attempt {attempt}/{MAX_RETRIES}] {label} error: {e}")
                gc.collect()
                if attempt < MAX_RETRIES:
                    time.sleep(2 * attempt)
        return ""


def stream_llm(
    system_prompt: str,
    user_content:  str,
    max_tokens:    int   = 5000,
    temperature:   float = 0.1,
):
    """Generator — streams LLM response token by token."""
    if USE_DEEPSEEK:
        yield from deepseek_stream(system_prompt, user_content, max_tokens, temperature)
    else:
        try:
            stream = hf_client.chat.completions.create(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_content},
                ],
                max_tokens=max_tokens,
                temperature=max(temperature, 0.01),
                stream=True,
            )
            for chunk in stream:
                token = chunk.choices[0].delta.content or ""
                if token:
                    yield token
        except Exception as e:
            yield f"\n\n[Error: {e}]"

# ══════════════════════════════════════════════════════════════════════════
#  CELL 6 — ROUTER
# ══════════════════════════════════════════════════════════════════════════
ROUTER_SYSTEM = """\
You are a query classifier for a SUST (Shahjalal University of Science and Technology) \
faculty search system.

This system ONLY helps users find SUST faculty/researchers based on research interests, \
expertise, or academic topics.

Classify the user query into exactly one of these two categories:

  faculty_search  — user wants to find faculty, researchers, supervisors, or professors \
based on a research topic, field, or academic interest.
  out_of_scope    — anything else (general questions, unrelated topics, too vague, \
non-research queries).

Examples:
  "Find me a PhD supervisor for machine learning" -> faculty_search
  "Who works on flood prediction at SUST?" -> faculty_search
  "Find researchers in Bangla NLP" -> faculty_search
  "What is machine learning?" -> out_of_scope
  "Tell me about SUST" -> out_of_scope
  "research" -> out_of_scope

OUTPUT: Reply with ONLY one word — either `faculty_search` or `out_of_scope`. \
No explanation. No punctuation. Just the label.
"""

def classify_query(query: str) -> str:
    raw = llm_call(
        ROUTER_SYSTEM,
        f"Query: {query}",
        max_tokens=_MAX_TOKENS_ROUTER,
        temperature=0.0,
        label="router",
    ).lower().strip()
    if "out_of_scope" in raw:
        return "out_of_scope"
    if "faculty_search" in raw:
        return "faculty_search"
    print(f"  [ROUTER] unexpected: '{raw}' — defaulting to faculty_search")
    return "faculty_search"

# ══════════════════════════════════════════════════════════════════════════
#  CELL 7 — SEMANTIC RETRIEVAL
# ══════════════════════════════════════════════════════════════════════════
def retrieve_top_faculty(query: str, k: int = TOP_K) -> list:
    """
    Embed the query, compute cosine similarity against all faculty embeddings,
    return the top-k faculty dicts with their research_summary.
    Uses module-level FAC_IDS and FAC_MATRIX — mirrors Cell 7 exactly.
    """
    # ── CHANGED: hf_embed() instead of embed_model.encode() ───────────────
    q_vec = hf_embed([query])[0]

    sims     = FAC_MATRIX @ q_vec
    top_idx  = np.argsort(-sims)[:k]
    top_ids  = [int(FAC_IDS[i]) for i in top_idx]
    top_sims = [float(sims[i]) for i in top_idx]

    if DEBUG:
        print(f"  [RETRIEVAL] top similarity scores: "
              f"{[round(s, 3) for s in top_sims[:5]]} ...")

    ph = ",".join(["%s"] * len(top_ids))
    with get_conn() as con:
        rows = con.execute(f"""
            SELECT
                f.id, f.name, f.designation, f.department,
                f.email, f.profile_url,
                f.research_summary, f.biography
            FROM faculty f
            WHERE f.id IN ({ph})
        """, top_ids).fetchall()

        interests_map = defaultdict(list)
        for ir in con.execute(
            f"SELECT faculty_id, interest FROM research_interests WHERE faculty_id IN ({ph})",
            top_ids
        ).fetchall():
            interests_map[ir["faculty_id"]].append(ir["interest"])

    id_to_row  = {r["id"]: dict(r) for r in rows}
    id_to_sim  = dict(zip(top_ids, top_sims))
    candidates = []
    for fid in top_ids:
        if fid not in id_to_row:
            continue
        p = id_to_row[fid]
        p["similarity_score"] = round(id_to_sim[fid], 4)
        p["interests"]        = interests_map.get(fid, [])
        candidates.append(p)

    print(f"  Retrieved {len(candidates)} candidates for query.")
    return candidates

# ══════════════════════════════════════════════════════════════════════════
#  CELL 8 — BUILD CONTEXT & GENERATE ANSWER
# ══════════════════════════════════════════════════════════════════════════
ANSWER_SYSTEM = """\
You are an academic advisor helping students identify suitable SUST \
(Shahjalal University of Science and Technology) faculty members for \
research collaboration or graduate supervision.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. The student's research interest or query.
2. A ranked list of SUST faculty profiles (pre-selected by semantic similarity).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1 — Read EVERY faculty profile in full before writing anything.
Step 2 — List ALL provided faculty. These profiles were pre-selected by \
semantic similarity, so every one of them is relevant to some degree. \
NEVER skip or omit any profile. Rank from most to least relevant.
Step 3 — Write the structured response below.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---
## Overview
<5–8 sentences. Name the top 3–5 strongest matches and explain why. \
Briefly mention what the remaining faculty contribute.>

---
## Faculty Matches
<Repeat the block below for EVERY faculty member provided, ranked best-first. \
Include ALL of them — never omit any.>

### [Rank]. [Full Name] — [Designation], [Department]

**Why they match:** <5–7 sentences. Explain specifically how their stated \
research areas, methods, projects, and application domains align with the query. \
Discuss any techniques or tools they use that are directly relevant. \
Where multiple aspects of the query connect to their work, address each one. \
For lower-ranked entries 3–4 sentences covering partial overlap is acceptable.>

**Research focus:** <A thorough list of their research topics, methodologies, \
tools, frameworks, and application domains exactly as stated in the profile. \
Separate each distinct area with a bullet (•).>

**Email:** <Email if provided in the profile data, otherwise omit this line.>

**Profile:** <URL only if explicitly present in the profile data. Omit if absent — \
never construct or guess URLs.>

**Availability note:** <Include ONLY if the profile explicitly states the \
faculty member is on study leave or affiliated elsewhere. Otherwise omit.>

---
## Summary & Recommendation
<4–6 sentences of practical advice: who to contact first, useful cross-department \
pairings, and any honest gaps in the available expertise.>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- List ALL provided profiles — never skip one.
- Keep each entry concise (4–6 lines) so all 15 fit in the response.
- Only use facts explicitly stated in the profiles. Never infer or expand.
- Never fabricate emails, URLs, or publication titles.
- Use the exact designation — do not upgrade academic rank.
- Forbidden expansions: "health data" → NOT "machine learning", \
  "cryptography" → NOT "cybersecurity", "signal processing" → NOT "neural networks".
"""

def build_context(candidates: list) -> str:
    """
    Build faculty context for LLM.
    ISSUE #5 FIX: Do NOT include "No profile data available." fallback message.
    Instead, always construct something meaningful from available fields.
    """
    blocks = []
    for i, p in enumerate(candidates, 1):
        header = (
            f"=== FACULTY {i}: {p.get('name', '-')} ===\n"
            f"Designation : {p.get('designation', '-')}\n"
            f"Department  : {p.get('department', '-')}\n"
            f"Email       : {p.get('email') or 'N/A'}\n"
            f"Profile URL : {p.get('profile_url') or 'N/A'}\n"
            f"Similarity  : {p.get('similarity_score', 0)}\n"
        )
        
        # Build body from available data — prioritize research_summary, fall back to interests + bio
        summary = (p.get("research_summary") or "").strip()
        if summary:
            body = f"Research Summary:\n{summary}"
        else:
            body_parts = []
            if p.get("interests"):
                body_parts.append("Research Interests: " + "; ".join(p["interests"]))
            bio = (p.get("biography") or "").strip()
            if bio:
                body_parts.append(f"Biography: {bio[:400]}")
            
            # If we have interests or bio, use them. Otherwise, minimal fallback (not "No profile data available.")
            if body_parts:
                body = "\n".join(body_parts)
            else:
                # Minimal placeholder that won't generate a "Why they match" section
                body = "[Minimal profile information available — consider contacting directly for details]"
        
        blocks.append(header + body)
    return "\n\n".join(blocks)

def generate_answer(query: str, candidates: list) -> str:
    context  = build_context(candidates)
    user_msg = (
        f"STUDENT QUERY:\n{query}\n\n"
        f"FACULTY PROFILES ({len(candidates)} candidates):\n\n"
        f"{context}"
    )
    return llm_call(
        ANSWER_SYSTEM,
        user_msg,
        max_tokens=_MAX_TOKENS_ANSWER,
        temperature=0.1,
        label="answer",
    )

# ══════════════════════════════════════════════════════════════════════════
#  CELL 9 — MAIN ask() FUNCTION
# ══════════════════════════════════════════════════════════════════════════
OUT_OF_SCOPE_MSG = (
    "This system is designed only for finding SUST faculty based on research "
    "interests and academic expertise.\n\n"
    "Please ask something like:\n"
    "  • 'Find me a PhD supervisor for machine learning and NLP'\n"
    "  • 'Who works on flood prediction or climate change at SUST?'\n"
    "  • 'Find researchers in renewable energy or power systems'\n"
    "  • 'I need a supervisor for my thesis on deep learning for medical imaging'"
)

def ask(query: str) -> str:
    """
    Full pipeline — mirrors Cell 9 exactly:
      1. Router  → faculty_search or out_of_scope
      2a. If faculty_search: retrieve top-K → LLM structured answer
      2b. If out_of_scope:   return rejection message
    """
    t0 = time.time()
    W  = 80

    print("\n" + "═" * W)
    print(f"  QUERY: {query}")
    print("═" * W)

    # ── Step 0: Route ────────────────────────────────────────────────────
    print("\n  [STEP 0] Classifying query ...")
    route = classify_query(query)
    print(f"  -> Route: {route.upper()}")

    # ── Pipeline 2: Out of scope ─────────────────────────────────────────
    if route == "out_of_scope":
        print("\n  [OUT OF SCOPE]")
        print("═" * W)
        print(OUT_OF_SCOPE_MSG)
        print("═" * W)
        return OUT_OF_SCOPE_MSG

    # ── Pipeline 1: Faculty search ───────────────────────────────────────
    print(f"\n  [STEP 1] Semantic retrieval — top {TOP_K} faculty ...")
    candidates = retrieve_top_faculty(query, k=TOP_K)

    if not candidates:
        msg = "No faculty found in the database. Please check the DB setup."
        print(f"  [ERROR] {msg}")
        return msg

    print(f"\n  [STEP 2] Generating structured answer via LLM ...")
    answer = generate_answer(query, candidates)

    if not answer:
        answer = "LLM did not return a response. Please retry."

    elapsed = time.time() - t0
    print(f"\n  ⏱  Done in {elapsed:.1f}s")
    print("\n" + "═" * W)
    print(answer)
    print("═" * W)

    return answer


# ══════════════════════════════════════════════════════════════════════════
#  PhD STUDENT RAG — setup, embeddings, retrieval, answer
# ══════════════════════════════════════════════════════════════════════════

PHD_IDS    = []
PHD_MATRIX = None

PHD_OUT_OF_SCOPE_MSG = (
    "This search helps you find PhD students and researchers for collaboration.\n\n"
    "Try asking:\n"
    "  • 'Find someone working on NLP or Bangla language processing'\n"
    "  • 'Looking for a research partner in computer vision'\n"
    "  • 'Who is working on IoT and smart systems at SUST?'\n"
    "  • 'Find a co-author for a deep learning paper'"
)

PHD_ROUTER_SYSTEM = """\
You are a query classifier for a PhD student and researcher search system.

Classify the query into ONE of:
  researcher_search — user wants to find PhD students, researchers, or research collaborators/partners
  out_of_scope      — completely unrelated to research or collaboration (weather, cooking, jokes, etc.)

Reply with ONLY one word: researcher_search  OR  out_of_scope
"""

PHD_ANSWER_SYSTEM = """\
You are a research collaboration advisor helping students find PhD researchers \
at SUST (Shahjalal University of Science and Technology) for collaboration, \
co-authorship, or networking.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. The student's query (research interest or collaboration goal).
2. A ranked list of PhD student profiles (most semantically similar first).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1 — Read EVERY profile in full before writing anything.
Step 2 — Include ALL profiles as matches. These candidates were pre-selected \
by semantic similarity, so EVERY one of them is relevant to some degree. \
DO NOT skip or omit any profile — list all of them, ranked from most to least relevant.
Step 3 — Write the structured response below.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---
## Overview
<4-6 sentences. Name the strongest matches, explain why they fit, and briefly \
mention what complementary expertise the others bring.>

---
## Matches

### [Rank]. [Full Name] — [Department]

**Why they match:** <4–6 sentences. Explain how their research areas, thesis work, \
active projects, and collaboration tags connect to the query. Be specific about \
which methodologies or datasets they work with that are relevant. Where their \
tags signal openness to the type of collaboration the student is looking for, \
highlight this explicitly.>

**Research focus:** <Comprehensive list of their research areas, methods, tools, \
and domains verbatim or near-verbatim from the profile. Use bullets (•) for each distinct area.>

**Current work:** <2–3 sentences on their active thesis or project from the bio. \
Be specific — include any collaborators, datasets, or real-world deployment targets mentioned.>

**Collaboration tags:** <List every tag exactly as written. If none, write "None listed.">

**Supervisor:** <Supervisor name from the profile, or "Not specified".>

**Contact:** <Email if explicitly provided in the profile, otherwise omit this line.>

---
## Summary & Recommendation
<3-4 sentences of practical advice: who to contact first, useful cross-department \
pairings, and any honest gaps.>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- List ALL provided profiles — never skip one.
- Only use facts explicitly stated in the profiles.
- Never fabricate emails, supervisors, or research areas.
- Never expand or infer research areas beyond what is written.
- Keep each entry concise (3-6 lines) so the full list fits in the response.
"""


def classify_query_phd(query: str) -> str:
    raw = llm_call(
        PHD_ROUTER_SYSTEM,
        f"Query: {query}",
        max_tokens=10,
        temperature=0.0,
        label="phd_router",
    ).lower().strip()
    if "out_of_scope" in raw:
        return "out_of_scope"
    return "researcher_search"


def setup_phd_db():
    """Add embedding column to phd_students if missing."""
    with get_conn() as con:
        if not col_exists(con, "phd_students", "embedding"):
            con.execute("ALTER TABLE phd_students ADD COLUMN embedding LONGBLOB")
            con.commit()
            print("  + phd_students.embedding column added")
        else:
            print("  phd_students.embedding column already present")
        total = con.execute("SELECT COUNT(*) AS n FROM phd_students").fetchone()["n"]
        has_emb = con.execute(
            "SELECT COUNT(*) AS n FROM phd_students WHERE embedding IS NOT NULL"
        ).fetchone()["n"]
    print(f"PhD students: {total} total, {has_emb} with embeddings")


def _build_phd_embed_text(row, tags: list) -> str:
    parts = []
    if row["name"]:           parts.append(row["name"])
    if row["department"]:     parts.append(row["department"])
    if row["supervisor"]:     parts.append(f"Supervisor: {row['supervisor']}")
    if row["research_area"]:  parts.append(f"Research: {row['research_area']}")
    bio = (row["bio"] or "").strip()
    if bio:                   parts.append(bio[:400])
    if tags:                  parts.append("Collaboration tags: " + "; ".join(tags))
    return " | ".join(parts)


def ensure_phd_embeddings():
    """Compute embeddings for PhD students that are missing them."""
    with get_conn() as con:
        pending = [r["id"] for r in con.execute(
            "SELECT id FROM phd_students WHERE embedding IS NULL"
        ).fetchall()]

    print(f"PhD students needing embeddings: {len(pending)}")
    if not pending:
        print("All PhD students already have embeddings — skipping.")
        return

    for start in range(0, len(pending), 32):
        batch_ids = pending[start:start + 32]
        ph = ",".join(["%s"] * len(batch_ids))
        with get_conn() as con:
            rows = con.execute(
                f"SELECT id, name, department, supervisor, research_area, bio FROM phd_students WHERE id IN ({ph})",
                batch_ids
            ).fetchall()
            tags_map = defaultdict(list)
            for tr in con.execute(
                f"SELECT phd_student_id, tag FROM phd_student_tags WHERE phd_student_id IN ({ph})",
                batch_ids
            ).fetchall():
                tags_map[tr["phd_student_id"]].append(tr["tag"])

        texts = [_build_phd_embed_text(r, tags_map[r["id"]]) for r in rows]
        vecs  = hf_embed(texts)

        with get_conn() as con:
            for row, vec in zip(rows, vecs):
                con.execute("UPDATE phd_students SET embedding=%s WHERE id=%s",
                            (vec_to_blob(vec), row["id"]))
            con.commit()

    print(f"PhD student embeddings done ({len(pending)} computed)")


def load_phd_index():
    """Load PhD student embeddings into RAM."""
    global PHD_IDS, PHD_MATRIX
    with get_conn() as con:
        rows = con.execute(
            "SELECT id, embedding FROM phd_students WHERE embedding IS NOT NULL"
        ).fetchall()
    if not rows:
        print("No PhD student embeddings found — index empty.")
        return
    PHD_IDS    = [r["id"] for r in rows]
    PHD_MATRIX = np.stack([blob_to_vec(r["embedding"]) for r in rows])
    print(f"PhD student index loaded: {len(PHD_IDS)} vectors {PHD_MATRIX.shape}")


def retrieve_top_phd(query: str, k: int = 10) -> list:
    """Semantic retrieval for PhD students."""
    if not PHD_IDS or PHD_MATRIX is None:
        return []

    q_vec    = hf_embed([query])[0]
    sims     = PHD_MATRIX @ q_vec
    top_idx  = np.argsort(-sims)[:k]
    top_ids  = [int(PHD_IDS[i]) for i in top_idx]
    top_sims = [float(sims[i]) for i in top_idx]

    ph = ",".join(["%s"] * len(top_ids))
    with get_conn() as con:
        rows = con.execute(f"""
            SELECT id, name, department, supervisor, research_area, bio, email, year_enrolled
            FROM phd_students WHERE id IN ({ph})
        """, top_ids).fetchall()
        tags_map = defaultdict(list)
        for tr in con.execute(
            f"SELECT phd_student_id, tag FROM phd_student_tags WHERE phd_student_id IN ({ph})",
            top_ids
        ).fetchall():
            tags_map[tr["phd_student_id"]].append(tr["tag"])

    id_to_row = {r["id"]: dict(r) for r in rows}
    id_to_sim = dict(zip(top_ids, top_sims))

    candidates = []
    for fid in top_ids:
        if fid not in id_to_row:
            continue
        p = id_to_row[fid]
        p["similarity_score"] = round(id_to_sim[fid], 4)
        p["tags"] = tags_map.get(fid, [])
        candidates.append(p)

    print(f"  Retrieved {len(candidates)} PhD candidates for query.")
    return candidates


def build_phd_context(candidates: list) -> str:
    """
    Build PhD student context for LLM.
    ISSUE #5 FIX: Do NOT include "No profile data available." fallback message.
    """
    blocks = []
    for i, p in enumerate(candidates, 1):
        header = (
            f"=== PHD STUDENT {i}: {p.get('name', '-')} ===\n"
            f"Department    : {p.get('department', '-')}\n"
            f"Supervisor    : {p.get('supervisor') or 'N/A'}\n"
            f"Year Enrolled : {p.get('year_enrolled') or 'N/A'}\n"
            f"Email         : {p.get('email') or 'N/A'}\n"
            f"Similarity    : {p.get('similarity_score', 0)}\n"
        )
        research = (p.get("research_area") or "").strip()
        bio      = (p.get("bio") or "").strip()
        tags     = p.get("tags", [])

        body_parts = []
        if research:  body_parts.append(f"Research Areas:\n{research}")
        if bio:       body_parts.append(f"Bio:\n{bio}")
        if tags:      body_parts.append("Collaboration Tags:\n" + "\n".join(f"  - {t}" for t in tags))
        
        # If we have any data, use it. Otherwise, minimal placeholder.
        if body_parts:
            body = "\n\n".join(body_parts)
        else:
            body = "[Minimal profile information — reach out for more details]"

        blocks.append(header + body)
    return "\n\n".join(blocks)


def ask_phd(query: str) -> dict:
    """Full RAG pipeline for PhD student search."""
    W = 80
    print("\n" + "═" * W)
    print(f"  [PHD SEARCH] QUERY: {query}")
    print("═" * W)

    t0 = time.time()

    print("  [STEP 0] Routing query...")
    route = classify_query_phd(query)
    print(f"  -> Route: {route.upper()}")

    if route == "out_of_scope":
        return {"answer": PHD_OUT_OF_SCOPE_MSG, "candidates": []}

    print("  [STEP 1] Semantic retrieval...")
    candidates = retrieve_top_phd(query, k=15)
    if not candidates:
        return {"answer": "No PhD students found in the database.", "candidates": []}

    print("  [STEP 2] Generating LLM answer...")
    context  = build_phd_context(candidates)
    user_msg = (
        f"STUDENT QUERY:\n{query}\n\n"
        f"PHD STUDENT PROFILES ({len(candidates)} candidates):\n\n{context}"
    )
    answer = llm_call(PHD_ANSWER_SYSTEM, user_msg,
                      max_tokens=2000, temperature=0.1, label="phd_answer")

    elapsed = time.time() - t0
    print(f"  ⏱  Done in {elapsed:.1f}s")
    print("═" * W)

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

    return {
        "answer":     answer or "LLM did not return a response. Please retry.",
        "candidates": top,
    }