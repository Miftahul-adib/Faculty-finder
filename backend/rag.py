# backend/rag.py
"""
SUST Faculty Finder — RAG core
Converted from v12 notebook (Gemma 4 via HuggingFace Inference API).
Config is read from .env — HF_TOKEN is never hardcoded here.
"""

import os, sqlite3, struct, gc, time
from collections import defaultdict
from dotenv import load_dotenv
import numpy as np
from huggingface_hub import InferenceClient, login as hf_login
from sentence_transformers import SentenceTransformer

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════
#  SETTINGS  (mirrors Cell 0)
# ══════════════════════════════════════════════════════════════════════════
HF_TOKEN           = os.environ["HF_TOKEN"]
HF_PROVIDER        = os.getenv("HF_PROVIDER", "auto")
LLM_MODEL          = os.getenv("LLM_MODEL", "google/gemma-4-26B-A4B-it")
DB_PATH            = os.getenv("DB_PATH", "/app/data/Faculty_database.db")
EMBED_MODEL_NAME   = "all-MiniLM-L6-v2"
TOP_K              = 25
DEBUG              = os.getenv("DEBUG", "false").lower() == "true"
MAX_RETRIES        = 2
_MAX_TOKENS_ROUTER = 20
_MAX_TOKENS_ANSWER = 2500

# ══════════════════════════════════════════════════════════════════════════
#  CELL 1 — HF LOGIN + CLIENT + EMBEDDING MODEL
# ══════════════════════════════════════════════════════════════════════════
hf_login(token=HF_TOKEN, add_to_git_credential=False)
hf_client = InferenceClient(token=HF_TOKEN, provider=HF_PROVIDER)
print(f"HF client ready | model: {LLM_MODEL}")

embed_model = SentenceTransformer(EMBED_MODEL_NAME)
print(f"Embedding model loaded: {EMBED_MODEL_NAME}")

# ══════════════════════════════════════════════════════════════════════════
#  CELL 2 — DB CONNECTION + SCHEMA SETUP
# ══════════════════════════════════════════════════════════════════════════
def get_conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con

def col_exists(con, table: str, col: str) -> bool:
    return col in [r[1] for r in con.execute(f"PRAGMA table_info('{table}')").fetchall()]

def setup_db():
    """Add embedding column if missing. Print quick stats. Mirrors Cell 2."""
    with get_conn() as con:
        if not col_exists(con, "faculty", "embedding"):
            con.execute("ALTER TABLE faculty ADD COLUMN embedding BLOB")
            con.commit()
            print("  + faculty.embedding column added")
        else:
            print("  faculty.embedding column already present")

        total   = con.execute("SELECT COUNT(*) FROM faculty").fetchone()[0]
        has_sum = con.execute(
            "SELECT COUNT(*) FROM faculty WHERE research_summary IS NOT NULL AND TRIM(research_summary) != ''"
        ).fetchone()[0]
        has_emb = con.execute(
            "SELECT COUNT(*) FROM faculty WHERE embedding IS NOT NULL"
        ).fetchone()[0]

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
        ph = ",".join("?" * len(batch_ids))

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
        vecs  = embed_model.encode(
            texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False
        )

        with get_conn() as con:
            for row, vec in zip(rows, vecs):
                con.execute(
                    "UPDATE faculty SET embedding=? WHERE id=?",
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
#  CELL 5 — LLM WRAPPER (Gemma 4 via HF API)
# ══════════════════════════════════════════════════════════════════════════
def llm_call(
    system_prompt: str,
    user_content:  str,
    max_tokens:    int   = 600,
    temperature:   float = 0.1,
    label:         str   = "",
) -> str:
    """
    Call Gemma 4 via HuggingFace Inference API.
    Gemma 4 natively supports the system role — no merging needed.
    """
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
    q_vec = embed_model.encode(
        [query], normalize_embeddings=True, show_progress_bar=False
    )[0]

    sims     = FAC_MATRIX @ q_vec
    top_idx  = np.argsort(-sims)[:k]
    top_ids  = [int(FAC_IDS[i]) for i in top_idx]
    top_sims = [float(sims[i]) for i in top_idx]

    if DEBUG:
        print(f"  [RETRIEVAL] top similarity scores: "
              f"{[round(s, 3) for s in top_sims[:5]]} ...")

    ph = ",".join("?" * len(top_ids))
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
You are an academic advisor helping students find suitable SUST \
(Shahjalal University of Science and Technology) faculty members for research \
collaboration or graduate supervision.
You will receive:
  1. The student's research interest or query.
  2. Research profiles of up to 25 SUST faculty members.
Your task: Analyse EVERY single faculty profile provided. For each one, decide \
if they are relevant to the student's query. Then write your full structured \
response listing ALL relevant faculty — do not stop after the first match.
FORMAT YOUR RESPONSE EXACTLY AS FOLLOWS:
---
## Overview
<4-8 sentences summarising who the strongest matches are and why.>
---
## Top Faculty Matches
For EACH relevant faculty member, ranked best-first, write ALL of these:
### [Rank]. [Full Name] — [Designation], [Department]
**Why they match:** <1-8 sentences linking their specific listed research areas or \
projects directly to the student's query. Use only what is explicitly stated in \
their profile — do not infer, extend, or reinterpret.>
**Research focus:** <Copy the research topics, methods, or project titles exactly \
as described in their profile. Do not paraphrase into broader fields.>
**Profile:** <URL, only if provided in the profile data. Omit this line otherwise.>
(Repeat the above block for every relevant faculty member.)
---
## Summary & Recommendation
<3-5 sentences of practical advice: who to contact first, any useful pairings \
across departments, and any notable gaps in coverage.>
---
STRICT RULES:
1. Analyse ALL profiles before writing your response. Do not stop early.
2. List EVERY faculty member who is even partially relevant.
3. Only use facts explicitly stated in the provided profiles. No hallucination.
4. Do not invent, infer, or expand on research areas beyond what is written.
   Examples of forbidden expansions:
   - "health data science" → NOT "machine learning"
   - "molecular immunology" → NOT "deep learning"
   - "statistical modelling" → NOT "predictive analytics"
   - "computer vision" → NOT "medical image analysis"
   - "natural language processing" → NOT "speech recognition"
   - "robotics" → NOT "autonomous systems"
   - "cryptography" → NOT "cybersecurity"
   - "compiler design" → NOT "programming languages"
   - "database management" → NOT "big data"
   - "signal processing" → NOT "neural networks"
   - "translation studies" → NOT "correspondence research"
   - "anthology contribution" → NOT "primary research focus"
   - "computational biology" → NOT "deep learning"
   Use the exact terms from the profile. Do not bridge gaps between a \
   faculty member's stated expertise and the student's topic.
5. Do not fabricate, guess, or reconstruct emails, URLs, or publication titles. \
   Only include a Profile URL if it is explicitly present in the provided profile data. \
   Do not construct URLs from email addresses or department names.
6. Do not upgrade or assume academic rank. Use only the designation explicitly \
   stated in the profile (e.g. do not write "Professor" if the profile says \
   "Associate Professor" or "Assistant Professor").
7. If a faculty member's profile states they are currently on study leave, \
   pursuing a degree abroad, or affiliated with another institution, note this \
   clearly in the "Why they match" field so the student is aware of their \
   likely unavailability for supervision.
8. Do not conflate a faculty member's PhD topic with their current research focus. \
   A PhD thesis completed years ago is not evidence of a current research area \
   unless the profile explicitly lists it as an ongoing interest or recent publication.
9. If a profile contains no relevant research areas, skip that faculty member silently.
10. Do not present a faculty member's peripheral or one-time contribution to a topic \
    (e.g. a single co-authored paper, an anthology inclusion, or a conference abstract) \
    as a primary or sustained research focus. Reflect the depth of engagement \
    accurately and proportionally.
"""
def build_context(candidates: list) -> str:
    blocks = []
    for i, p in enumerate(candidates, 1):
        header = (
            f"=== FACULTY {i}: {p.get('name', '-')} ===\n"
            f"Designation : {p.get('designation', '-')}\n"
            f"Department  : {p.get('department', '-')}\n"
            f"Profile URL : {p.get('profile_url') or 'N/A'}\n"
            f"Similarity  : {p.get('similarity_score', 0)}\n"
        )
        summary = (p.get("research_summary") or "").strip()
        if summary:
            body = f"Research Summary:\n{summary}"
        else:
            parts = []
            if p.get("interests"):
                parts.append("Research Interests: " + "; ".join(p["interests"]))
            bio = (p.get("biography") or "").strip()
            if bio:
                parts.append(f"Biography: {bio[:400]}")
            body = "\n".join(parts) if parts else "No profile data available."
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
    print(f"  → Route: {route.upper()}")

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
