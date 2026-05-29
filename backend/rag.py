# backend/rag.py
"""
SUST Faculty Finder — RAG core
Converted from v12 notebook (Gemma 4 via HuggingFace Inference API).
Config is read from .env — HF_TOKEN is never hardcoded here.
Embeddings now use HF Inference API — no sentence-transformers / torch needed.
"""

import os, sqlite3, struct, gc, time
from collections import defaultdict
from dotenv import load_dotenv
import numpy as np
from huggingface_hub import InferenceClient, login as hf_login

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════
#  SETTINGS  (mirrors Cell 0)
# ══════════════════════════════════════════════════════════════════════════
HF_TOKEN           = os.environ["HF_TOKEN"]
HF_PROVIDER        = os.getenv("HF_PROVIDER", "auto")
LLM_MODEL          = os.getenv("LLM_MODEL", "google/gemma-4-26B-A4B-it")
# ── CHANGED: full HF model ID required for Inference API ──────────────────
EMBED_MODEL_NAME   = os.getenv("EMBED_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
DB_PATH            = os.getenv("DB_PATH", "/app/data/Faculty_database.db")
TOP_K              = 25
DEBUG              = os.getenv("DEBUG", "false").lower() == "true"
MAX_RETRIES        = 2
_MAX_TOKENS_ROUTER = 20
_MAX_TOKENS_ANSWER = 2500

# ══════════════════════════════════════════════════════════════════════════
#  CELL 1 — HF LOGIN + CLIENT
#  REMOVED: SentenceTransformer — no torch/sentence-transformers needed
# ══════════════════════════════════════════════════════════════════════════
hf_login(token=HF_TOKEN, add_to_git_credential=False)
hf_client = InferenceClient(token=HF_TOKEN, provider=HF_PROVIDER)
print(f"HF client ready | model: {LLM_MODEL}")
print(f"Embedding model : {EMBED_MODEL_NAME} (via HF Inference API)")

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

        # ── CHANGED: hf_embed() instead of embed_model.encode() ───────────
        vecs = hf_embed(texts)

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
    # ── CHANGED: hf_embed() instead of embed_model.encode() ───────────────
    q_vec = hf_embed([query])[0]

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
You are an academic advisor helping students identify suitable SUST \
(Shahjalal University of Science and Technology) faculty members for \
research collaboration or graduate supervision.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INPUTS YOU WILL RECEIVE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. The student's research interest or query.
2. A set of SUST faculty profiles.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
YOUR TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1 — Silent analysis: Read EVERY faculty profile in full before \
writing anything. Do not start your response until you have assessed all profiles.
Step 2 — Relevance filtering: Identify every faculty member whose \
explicitly stated research areas overlap with the student's query. \
If no profile is relevant, say so clearly in the Overview.
Step 3 — Ranked output: Write the structured response below, listing \
ALL relevant faculty from most to least relevant.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED OUTPUT FORMAT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---
## Overview
<4–8 sentences. Name the strongest matches and explain why. If no profiles \
are relevant, state this clearly here and stop — do not fabricate matches.>

---
## Top Faculty Matches
<Repeat the block below for EVERY relevant faculty member, ranked best-first. \
Omit faculty with no relevant overlap entirely — no placeholder entries.>

### [Rank]. [Full Name] — [Designation], [Department]

**Why they match:** <1–5 sentences linking their EXPLICITLY STATED research \
areas or projects to the student's query. Do not infer, extend, or bridge gaps.>

**Research focus:** <Copy the research topics, methods, or project titles \
verbatim or near-verbatim from the profile. Do not paraphrase into broader fields.>

**Availability note:** <Include ONLY if the profile explicitly states the \
faculty member is on study leave, pursuing a degree abroad, or affiliated with \
another institution. Otherwise omit this field entirely.>

**Profile:** <URL only if explicitly provided in the profile data. Omit this \
line if no URL is present — do not construct or guess URLs.>

---
## Summary & Recommendation
<3–5 sentences of practical advice: who to contact first, useful cross-department \
pairings if applicable, and any honest gaps in the available expertise.>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT RULES — VIOLATIONS BREAK THE TOOL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

COMPLETENESS
- Analyse ALL profiles before writing. Never stop early.
- List EVERY faculty member with even partial relevance.

FACTUAL ACCURACY
- Use ONLY facts explicitly stated in the provided profiles.
- Never hallucinate, infer, or expand research areas beyond what is written.
  Forbidden expansions (this list is illustrative, not exhaustive):
    "health data science"      → NOT "machine learning"
    "molecular immunology"     → NOT "deep learning"
    "cryptography"             → NOT "cybersecurity"
    "compiler design"          → NOT "programming languages"
    "database management"      → NOT "big data"
    "signal processing"        → NOT "neural networks"
    "translation studies"      → NOT "correspondence research"
    "computational biology"    → NOT "bioinformatics" or "deep learning"
  Rule: if the profile does not use the term, you do not use the term.

DEPTH OF ENGAGEMENT
- Do not present a single co-authored paper, anthology inclusion, or conference \
  abstract as a primary or sustained research focus. Reflect depth accurately.


CONTACT DETAILS & URLS
- Never fabricate, reconstruct, or guess emails, URLs, or publication titles.
- Only include a Profile URL if it appears verbatim in the provided profile data.
- Do not construct URLs from email addresses, names, or department codes.

ACADEMIC RANK
- Use the exact designation from the profile.
- Do not upgrade rank (e.g. do not write "Professor" if the profile says \
  "Associate Professor" or "Lecturer").

AVAILABILITY FLAGS
- If a profile states the faculty member is on study leave, pursuing a degree \
  abroad, or is affiliated with another institution, flag this clearly so the \
  student understands they may be unavailable for supervision.
- Do not assume availability or unavailability beyond what is stated.
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
