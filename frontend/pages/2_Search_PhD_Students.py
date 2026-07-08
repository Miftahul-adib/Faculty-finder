import streamlit as st
import requests
import json
from utils import (BASE_CSS, BACKEND_URL, auth_headers, is_logged_in,
                   api_post, api_delete, get_initials, render_tag_chips,
                   page_header, section_label, divider)

st.markdown(BASE_CSS, unsafe_allow_html=True)

for key, default in [("token",""),("student_id",None),("student_name",""),
                      ("phd_messages",[]),("phd_candidates",[]),
                      ("saved_phd_ids",set()),("saved_student_ids",set())]:
    if key not in st.session_state:
        st.session_state[key] = default

page_header("Search PhD Students",
            "Describe your research interest or collaboration goal — we'll find the right researchers",
            kicker="Find collaborators")

st.markdown(
    '<div class="info-banner">'
    '<p>— Ask in natural language, just like the faculty search. The AI understands context.</p>'
    '<p>— Try: <em>"Find a research partner working on NLP or Bangla text processing"</em></p>'
    '<p>— Results include PhD researchers and registered students with matching collaboration tags.</p>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Load saved IDs ─────────────────────────────────────────────────────────
if is_logged_in():
    sid = st.session_state.student_id
    if not st.session_state.saved_phd_ids:
        try:
            r = requests.get(f"{BACKEND_URL}/student/{sid}/saved-phd",
                             headers=auth_headers(), timeout=10)
            st.session_state.saved_phd_ids = {p["id"] for p in r.json()}
        except Exception:
            pass
    if not st.session_state.saved_student_ids:
        try:
            r = requests.get(f"{BACKEND_URL}/student/{sid}/saved-students",
                             headers=auth_headers(), timeout=10)
            st.session_state.saved_student_ids = {p["id"] for p in r.json()}
        except Exception:
            pass


def render_candidate_cards(candidates):
    if not candidates:
        return
    section_label(f"{len(candidates)} top matches — save to your list")
    for c in candidates:
        cid       = c["id"]
        tags      = c.get("tags", [])
        tags_txt  = [t["tag"] if isinstance(t, dict) else t for t in tags]
        dept      = c.get("department", "")
        super_    = c.get("supervisor", "")
        research  = c.get("research_area", "")
        email     = c.get("email", "")
        initials  = get_initials(c["name"])
        tags_html = render_tag_chips(tags_txt, dark=True)
        meta_parts = [p for p in [dept, f"Sup: {super_}" if super_ else ""] if p]
        meta      = " · ".join(meta_parts)
        email_html = (f'<span style="font-family:Inter,sans-serif;font-size:0.73rem;'
                      f'color:#6ECDA0;">{email}</span>') if email else ""

        # Source determines which save endpoint to use
        source = c.get("source", "phd")
        saved  = (cid in st.session_state.saved_phd_ids if source == "phd"
                  else cid in st.session_state.saved_student_ids)

        col_card, col_btn = st.columns([7, 1.3], gap="small")
        with col_card:
            st.markdown(
                f'<div class="dark-card">'
                f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">'
                f'<div class="avatar" style="width:36px;height:36px;font-size:0.75rem;">{initials}</div>'
                f'<div>'
                f'<div class="dark-card-name">{c["name"]}</div>'
                f'<div class="dark-card-meta">{meta}</div>'
                f'</div></div>'
                + (f'<div class="dark-card-research">'
                   f'{research[:220]}{"…" if len(research)>220 else ""}</div>'
                   if research else "")
                + (f'<div style="margin-top:5px;">{email_html}</div>' if email_html else "")
                + (tags_html if tags_html else "")
                + '</div>',
                unsafe_allow_html=True,
            )
        with col_btn:
            st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
            if is_logged_in():
                if saved:
                    btn_label = "✓ Saved"
                    if st.button(btn_label, key=f"unsave_phdc_{cid}_{source}",
                                 type="secondary", help="Remove", use_container_width=True):
                        if source == "phd":
                            api_delete(f"/student/{st.session_state.student_id}/save-phd/{cid}")
                            st.session_state.saved_phd_ids.discard(cid)
                        else:
                            api_delete(f"/student/{st.session_state.student_id}/save-student/{cid}")
                            st.session_state.saved_student_ids.discard(cid)
                        st.rerun()
                else:
                    if st.button("+ Save", key=f"save_phdc_{cid}_{source}",
                                 type="primary", use_container_width=True):
                        if source == "phd":
                            _, err = api_post(f"/student/{st.session_state.student_id}/save-phd",
                                              {"phd_student_id": cid})
                            if not err:
                                st.session_state.saved_phd_ids.add(cid)
                        else:
                            _, err = api_post(f"/student/{st.session_state.student_id}/save-student",
                                              {"target_student_id": cid})
                            if not err:
                                st.session_state.saved_student_ids.add(cid)
                        st.rerun()
            else:
                st.caption("Log in\nto save")


# ── Streaming generator ────────────────────────────────────────────────────
def _stream_phd(query):
    try:
        with requests.post(
            f"{BACKEND_URL}/ask-phd-stream",
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
                        st.session_state.phd_candidates = data.get("candidates", [])
                        return
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        yield f"\n\n**Connection error:** {e}"
        st.session_state.phd_candidates = []


# ── Chat history ───────────────────────────────────────────────────────────
for msg in st.session_state.phd_messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.phd_candidates and not st.session_state.get("_phd_just_streamed"):
    render_candidate_cards(st.session_state.phd_candidates)

# ── Chat input ─────────────────────────────────────────────────────────────
query = st.chat_input("e.g. Find a research partner working on medical image analysis")

if query and query.strip():
    query = query.strip()
    st.session_state["_phd_just_streamed"] = True
    st.session_state.phd_messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Searching PhD & student records…"):
            full_text = st.write_stream(_stream_phd(query))

    st.session_state.phd_messages.append({"role": "assistant", "content": full_text or ""})
    render_candidate_cards(st.session_state.get("phd_candidates", []))
else:
    st.session_state["_phd_just_streamed"] = False
