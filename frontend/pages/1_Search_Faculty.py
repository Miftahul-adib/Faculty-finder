import streamlit as st
import requests
import json
from utils import (BASE_CSS, BACKEND_URL, auth_headers, is_logged_in,
                   api_post, api_delete, get_initials,
                   page_header, section_label, divider)

st.markdown(BASE_CSS, unsafe_allow_html=True)

for key, default in [("token",""),("student_id",None),("student_name",""),
                      ("fac_messages",[]),("fac_candidates",[]),("saved_fac_ids",set())]:
    if key not in st.session_state:
        st.session_state[key] = default

page_header("Search Faculty",
            "Describe your research interest in plain language — our AI finds the right professors",
            kicker="Find a supervisor")

st.markdown(
    '<div class="info-banner">'
    '<p>— Ask one question at a time. Each query is answered independently.</p>'
    '<p>— Try: <em>"Find me a PhD supervisor for deep learning in medical imaging"</em> or '
    '<em>"Who works on flood prediction at SUST?"</em></p>'
    '<p>— <strong>Faculty database:</strong> SUST (611 faculty). More universities coming soon.</p>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Load saved IDs once ────────────────────────────────────────────────────
if is_logged_in() and not st.session_state.saved_fac_ids:
    try:
        r = requests.get(f"{BACKEND_URL}/student/{st.session_state.student_id}/saved-faculty",
                         headers=auth_headers(), timeout=10)
        st.session_state.saved_fac_ids = {f["id"] for f in r.json()}
    except Exception:
        pass


# ── Candidate cards ────────────────────────────────────────────────────────
def render_candidate_cards(candidates):
    if not candidates:
        return
    section_label(f"{len(candidates)} top matches — save to your list")
    for c in candidates:
        fid      = c["id"]
        saved    = fid in st.session_state.saved_fac_ids
        initials = get_initials(c["name"])
        dept     = c.get("department", "")
        desig    = c.get("designation", "")
        url      = c.get("profile_url", "")
        meta     = " · ".join(filter(None, [desig, dept]))
        link_html = (f'<a href="{url}" target="_blank" style="font-family:Inter,sans-serif;'
                     f'font-size:0.73rem;color:#6ECDA0;text-decoration:none;">'
                     f'View profile ↗</a>') if url else ""

        col_card, col_btn = st.columns([7, 1.3], gap="small")
        with col_card:
            st.markdown(
                f'<div class="dark-card">'
                f'<div style="display:flex;align-items:center;gap:10px;">'
                f'<div class="avatar" style="width:36px;height:36px;font-size:0.75rem;">{initials}</div>'
                f'<div>'
                f'<div class="dark-card-name">{c["name"]}</div>'
                f'<div class="dark-card-meta">{meta}</div>'
                f'</div></div>'
                + (f'<div style="margin-top:6px;">{link_html}</div>' if link_html else "")
                + '</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if is_logged_in():
                if saved:
                    if st.button("✓ Saved", key=f"unsave_f_{fid}", type="secondary",
                                 help="Remove from saved", use_container_width=True):
                        api_delete(f"/student/{st.session_state.student_id}/save-faculty/{fid}")
                        st.session_state.saved_fac_ids.discard(fid)
                        st.rerun()
                else:
                    if st.button("+ Save", key=f"save_f_{fid}", type="primary",
                                 use_container_width=True):
                        _, err = api_post(f"/student/{st.session_state.student_id}/save-faculty",
                                          {"faculty_id": fid})
                        if not err:
                            st.session_state.saved_fac_ids.add(fid)
                            st.rerun()
            else:
                st.caption("Log in\nto save")


# ── Streaming generator ────────────────────────────────────────────────────
def _stream_faculty(query):
    try:
        with requests.post(
            f"{BACKEND_URL}/ask-stream",
            json={"query": query},
            headers={**auth_headers(), "Accept": "text/event-stream"},
            stream=True,
            timeout=180,
        ) as resp:
            for raw in resp.iter_lines():
                if not raw:
                    continue
                line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                if not line.startswith("data: "):
                    continue
                try:
                    data = json.loads(line[6:])
                    if "text" in data:
                        yield data["text"]
                    if data.get("done"):
                        st.session_state.fac_candidates = data.get("candidates", [])
                        return
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        yield f"\n\n**Connection error:** {e}"
        st.session_state.fac_candidates = []


# ── Chat history ───────────────────────────────────────────────────────────
for msg in st.session_state.fac_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.fac_candidates and not st.session_state.get("_fac_just_streamed"):
    render_candidate_cards(st.session_state.fac_candidates)

# ── Chat input ─────────────────────────────────────────────────────────────
query = st.chat_input("e.g. Find a PhD supervisor for machine learning and NLP research")

if query and query.strip():
    query = query.strip()
    st.session_state["_fac_just_streamed"] = True
    st.session_state.fac_messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Searching faculty database…"):
            full_text = st.write_stream(_stream_faculty(query))

    st.session_state.fac_messages.append({"role": "assistant", "content": full_text or ""})
    render_candidate_cards(st.session_state.get("fac_candidates", []))
else:
    st.session_state["_fac_just_streamed"] = False
