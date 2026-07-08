import base64
import io

import streamlit as st
import requests
from PIL import Image, ImageOps
from utils import (BASE_CSS, BACKEND_URL, auth_headers, is_logged_in,
                   api_get, api_post, api_delete, get_initials, avatar_html,
                   render_tag_chips, section_label, divider, page_header,
                   SUGGESTED_TAGS)

st.markdown(BASE_CSS, unsafe_allow_html=True)

for key, default in [("token",""),("student_id",None),("student_name","")]:
    if key not in st.session_state:
        st.session_state[key] = default

if not is_logged_in():
    st.markdown(
        '<div class="profile-hero-center">'
        '<div class="profile-name">My Profile</div>'
        '<div class="profile-meta">Please log in to view your profile</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.info("Go to the Home page to log in or sign up.")
    st.stop()

sid = st.session_state.student_id
profile, err = api_get(f"/student/{sid}")
if err or not profile:
    st.error("Could not load your profile. Please try again.")
    st.stop()

existing_tags = profile.get("tags", [])
tag_texts     = [t["tag"] for t in existing_tags]

# ── Profile hero ───────────────────────────────────────────────────────────
meta_parts = [x for x in [profile.get("department",""), profile.get("university","")] if x]
if profile.get("year"):
    meta_parts.append(profile["year"])

interests = [x.strip() for x in (profile.get("research_interests") or "").split(",") if x.strip()]
summary   = (profile.get("research_summary") or "").strip()

st.markdown(
    f'<div class="profile-hero">'
    f'{avatar_html(profile["name"], profile.get("photo_b64"), size=74, font_size="1.5rem")}'
    f'<div style="flex:1;min-width:0;">'
    f'<div class="profile-name">{profile["name"]}</div>'
    f'<div class="profile-meta">{" · ".join(meta_parts)}</div>'
    + (f'<div style="margin-top:0.6rem;">{render_tag_chips(interests, dark=True)}</div>' if interests else "")
    + (f'<div class="profile-meta" style="margin-top:0.7rem;font-size:0.82rem;color:#8FE0B8;">{summary}</div>' if summary else "")
    + (f'<div style="margin-top:0.6rem;">{render_tag_chips(tag_texts, dark=True)}</div>' if tag_texts else "")
    + '</div></div>',
    unsafe_allow_html=True,
)

# ── Tabs ───────────────────────────────────────────────────────────────────
tab_edit, tab_posts, tab_docs, tab_tags, tab_saved = st.tabs(
    ["  Edit Profile  ", "  Posts  ", "  Documents  ", "  Tags  ", "  Saved  "]
)

# ═══════════════════════ TAB 1 — EDIT ═══════════════════════════════════════
with tab_edit:
    # ── Profile photo ───────────────────────────────────────────────────────
    section_label("Profile photo")
    col_ph, col_ctl = st.columns([1, 4])
    with col_ph:
        st.markdown(avatar_html(profile["name"], profile.get("photo_b64"),
                                size=84, font_size="1.6rem"),
                    unsafe_allow_html=True)
    with col_ctl:
        photo_file = st.file_uploader("Upload a photo (JPG, PNG or WebP)",
                                      type=["png", "jpg", "jpeg", "webp"],
                                      key="photo_upload")
        bcol1, bcol2 = st.columns(2)
        with bcol1:
            if photo_file is not None and st.button("Set as profile photo",
                                                    type="primary", key="photo_btn",
                                                    use_container_width=True):
                try:
                    img = Image.open(photo_file)
                    img = ImageOps.exif_transpose(img)
                    img.thumbnail((512, 512))
                    buf = io.BytesIO()
                    img.convert("RGB").save(buf, "JPEG", quality=88)
                    b64 = base64.b64encode(buf.getvalue()).decode()
                except Exception:
                    st.error("Could not read that image — try a different file.")
                else:
                    _, perr = api_post(f"/student/{sid}/photo",
                                       {"data_b64": b64, "mime": "image/jpeg"})
                    if perr:
                        st.error(perr)
                    else:
                        st.rerun()
        with bcol2:
            if profile.get("photo_b64") and st.button("Remove photo", type="secondary",
                                                      key="photo_rm",
                                                      use_container_width=True):
                api_delete(f"/student/{sid}/photo")
                st.rerun()

    divider()

    # ── Profile fields ──────────────────────────────────────────────────────
    section_label("About you")
    with st.form("edit_profile"):
        bio        = st.text_area("Bio / About me", value=profile.get("bio") or "",
                                   height=120,
                                   placeholder="Describe your background and collaboration goals…")
        research_interests = st.text_input(
            "Research interests (comma separated)",
            value=profile.get("research_interests") or "",
            placeholder="e.g. Machine Learning, Bangla NLP, Computer Vision")
        research_summary = st.text_area(
            "My research summary", value=profile.get("research_summary") or "",
            height=110,
            placeholder="Summarize your own research or thesis work — topics, methods, results…")
        c1, c2 = st.columns(2)
        with c1:
            university = st.text_input("University", value=profile.get("university") or "SUST")
            department = st.text_input("Department",  value=profile.get("department") or "")
        with c2:
            year = st.text_input("Year / Status", value=profile.get("year") or "")
        if st.form_submit_button("Save changes", use_container_width=True, type="primary"):
            r = requests.put(
                f"{BACKEND_URL}/student/{sid}",
                json={"bio": bio, "university": university,
                      "department": department, "year": year,
                      "research_interests": research_interests,
                      "research_summary": research_summary},
                headers=auth_headers(), timeout=15,
            )
            if r.ok:
                st.success("Profile updated successfully!")
                st.rerun()
            else:
                st.error(r.text)

# ═══════════════════════ TAB 2 — POSTS ══════════════════════════════════════
with tab_posts:
    section_label("Add a post")
    _POST_TYPES = {
        "Work / Project":     "work",
        "Completed Project":  "project",
        "Research Interest":  "interest",
        "Certification":      "certification",
    }
    _POST_LABELS = {v: k for k, v in _POST_TYPES.items()}
    with st.form("add_post", clear_on_submit=True):
        post_type = st.radio("Type", list(_POST_TYPES.keys()), horizontal=True)
        title     = st.text_input("Title", placeholder="e.g. Paper on Bangla NLP tokenisation, AWS ML certification…")
        content   = st.text_area("Details (optional)", height=90,
                                  placeholder="Describe what you did, what methods you used, what you found…")
        post_img  = st.file_uploader("Attach a picture (optional — JPG, PNG or WebP)",
                                     type=["png", "jpg", "jpeg", "webp"], key="post_img")
        if st.form_submit_button("Publish post", use_container_width=True, type="primary"):
            if not title.strip():
                st.error("Title is required.")
            else:
                payload = {"title": title.strip(), "content": content.strip(),
                           "post_type": _POST_TYPES[post_type]}
                img_err = None
                if post_img is not None:
                    try:
                        img = Image.open(post_img)
                        img = ImageOps.exif_transpose(img)
                        img.thumbnail((1024, 1024))
                        buf = io.BytesIO()
                        img.convert("RGB").save(buf, "JPEG", quality=85)
                        payload["image_b64"]  = base64.b64encode(buf.getvalue()).decode()
                        payload["image_mime"] = "image/jpeg"
                    except Exception:
                        img_err = "Could not read that image — try a different file."
                if img_err:
                    st.error(img_err)
                else:
                    _, err = api_post(f"/student/{sid}/posts", payload)
                    if err:
                        st.error(err)
                    else:
                        st.success("Post published!")
                        st.rerun()

    divider()
    posts = profile.get("posts", [])
    if not posts:
        st.markdown(
            '<div style="text-align:center;padding:2rem;color:#4FB489;font-family:Inter,sans-serif;font-size:0.9rem;">'
            'No posts yet. Share your work or research interests above.</div>',
            unsafe_allow_html=True,
        )
    for post in posts:
        type_label = _POST_LABELS.get(post["post_type"], "Work / Project")
        col_post, col_del = st.columns([9, 1])
        with col_post:
            st.markdown(
                f'<div class="post-card">'
                f'<div class="post-type-badge">{type_label}</div>'
                f'<div class="post-title">{post["title"]}</div>'
                + (f'<div class="post-content">{post["content"]}</div>' if post.get("content") else "")
                + (f'<img class="post-img" src="data:{post.get("image_mime") or "image/jpeg"};'
                   f'base64,{post["image_b64"]}" alt=""/>' if post.get("image_b64") else "")
                + f'<div class="post-date">{post["created_at"][:10]}</div>'
                + '</div>',
                unsafe_allow_html=True,
            )
        with col_del:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"del_post_{post['id']}", help="Delete post"):
                api_delete(f"/student/{sid}/posts/{post['id']}")
                st.rerun()

# ═══════════════════════ TAB 3 — DOCUMENTS ══════════════════════════════════
with tab_docs:
    # ── CV ──────────────────────────────────────────────────────────────────
    section_label("Curriculum Vitae (CV)")
    cv_name = profile.get("cv_filename") or ""
    if cv_name:
        col_dl, col_rm_cv = st.columns([4, 1])
        with col_dl:
            try:
                r = requests.get(f"{BACKEND_URL}/student/{sid}/cv",
                                 headers=auth_headers(), timeout=15)
                if r.ok:
                    st.download_button(f"Download {cv_name}", data=r.content,
                                       file_name=cv_name, use_container_width=True)
            except requests.exceptions.RequestException:
                st.caption("Could not load your CV right now.")
        with col_rm_cv:
            if st.button("Remove", key="rm_cv", type="secondary", use_container_width=True):
                api_delete(f"/student/{sid}/cv")
                st.rerun()
    else:
        st.caption("No CV uploaded yet.")

    cv_file = st.file_uploader("Upload your CV (PDF, DOC or DOCX — max 5 MB)",
                               type=["pdf", "doc", "docx"], key="cv_upload")
    if cv_file is not None:
        if cv_file.size > 5 * 1024 * 1024:
            st.error("File is larger than 5 MB. Please upload a smaller CV.")
        elif st.button("Upload CV", type="primary", key="cv_upload_btn"):
            b64 = base64.b64encode(cv_file.getvalue()).decode()
            _, err = api_post(f"/student/{sid}/cv",
                              {"filename": cv_file.name, "data_b64": b64})
            if err:
                st.error(err)
            else:
                st.success("CV uploaded!")
                st.rerun()

    divider()

    # ── Other documents ────────────────────────────────────────────────────
    section_label("Documents — papers, certificates, transcripts")
    docs = profile.get("documents", [])
    if not docs:
        st.caption("No documents yet. Attach papers, certificates or anything a collaborator should see.")
    for d in docs:
        size_kb = (d.get("size") or 0) // 1024
        label   = d.get("label") or ""
        ext     = d["filename"].rsplit(".", 1)[-1].upper() if "." in d["filename"] else "FILE"
        meta    = " · ".join(filter(None, [label, f"{size_kb} KB", (d.get("uploaded_at") or "")[:10]]))
        col_doc, col_get, col_del = st.columns([6, 2, 1])
        with col_doc:
            st.markdown(
                f'<div class="doc-row">'
                f'<div class="doc-icon">{ext[:4]}</div>'
                f'<div style="flex:1;min-width:0;">'
                f'<div class="doc-name">{d["filename"]}</div>'
                f'<div class="doc-meta">{meta}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        with col_get:
            try:
                r = requests.get(f"{BACKEND_URL}/student/{sid}/documents/{d['id']}",
                                 headers=auth_headers(), timeout=15)
                if r.ok:
                    st.download_button("Get", data=r.content, file_name=d["filename"],
                                       key=f"dl_doc_{d['id']}", help="Download",
                                       use_container_width=True)
            except requests.exceptions.RequestException:
                pass
        with col_del:
            if st.button("✕", key=f"del_doc_{d['id']}", help="Delete document"):
                api_delete(f"/student/{sid}/documents/{d['id']}")
                st.rerun()

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    doc_label = st.text_input("Label (optional)", key="doc_label",
                              placeholder="e.g. Conference paper, IELTS certificate, Transcript")
    doc_file  = st.file_uploader("Attach a document (PDF, DOC, DOCX, PPT, PPTX, TXT, PNG, JPG — max 10 MB)",
                                 type=["pdf", "doc", "docx", "ppt", "pptx", "txt", "png", "jpg", "jpeg"],
                                 key="doc_upload")
    if doc_file is not None:
        if doc_file.size > 10 * 1024 * 1024:
            st.error("File is larger than 10 MB.")
        elif st.button("Add document", type="primary", key="doc_upload_btn"):
            b64 = base64.b64encode(doc_file.getvalue()).decode()
            _, err = api_post(f"/student/{sid}/documents",
                              {"filename": doc_file.name,
                               "label": doc_label.strip(),
                               "data_b64": b64})
            if err:
                st.error(err)
            else:
                st.success("Document added!")
                st.rerun()

# ═══════════════════════ TAB 4 — TAGS ═══════════════════════════════════════
with tab_tags:
    st.markdown(
        '<div class="info-banner" style="margin-top:0.5rem;">'
        '<p>Tags appear as chips behind your name when others search for PhD students and researchers. '
        'They signal what kind of collaboration you are open to.</p>'
        '</div>',
        unsafe_allow_html=True,
    )

    section_label("Quick-add suggested tags")
    used = {t["tag"] for t in existing_tags}
    cols = st.columns(2)
    for i, tag in enumerate(SUGGESTED_TAGS):
        with cols[i % 2]:
            if tag in used:
                st.markdown(
                    f'<div style="padding:4px 0;">'
                    f'<span class="tag-chip" style="opacity:0.55;">{tag} ✓</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button(f"+ {tag}", key=f"sugg_{i}", use_container_width=True):
                    api_post(f"/student/{sid}/tags", {"tag": tag})
                    st.rerun()

    divider()
    section_label("Add a custom tag")
    with st.form("custom_tag"):
        custom = st.text_input("", placeholder="e.g. Looking for partner in quantum ML",
                                label_visibility="collapsed")
        if st.form_submit_button("Add tag", use_container_width=True, type="primary"):
            if not custom.strip():
                st.error("Tag cannot be empty.")
            elif custom.strip() in used:
                st.warning("You already have this tag.")
            else:
                api_post(f"/student/{sid}/tags", {"tag": custom.strip()})
                st.rerun()

    if existing_tags:
        divider()
        section_label("Your current tags")
        for t in existing_tags:
            col_t, col_rm = st.columns([8, 1])
            with col_t:
                st.markdown(
                    f'<div style="padding:4px 0;">'
                    f'<span class="tag-chip-dark">{t["tag"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            with col_rm:
                if st.button("✕", key=f"del_tag_{t['id']}", help="Remove tag"):
                    api_delete(f"/student/{sid}/tags/{t['id']}")
                    st.rerun()

# ═══════════════════════ TAB 5 — SAVED ══════════════════════════════════════
with tab_saved:
    # ── Saved Faculty ──────────────────────────────────────────────────────
    section_label("Saved Professors")
    fac_data, _ = api_get(f"/student/{sid}/saved-faculty")
    saved_faculty = fac_data or []

    if not saved_faculty:
        st.markdown(
            '<div style="text-align:center;padding:1.5rem;color:#4FB489;font-family:Inter,sans-serif;font-size:0.88rem;">'
            'No saved professors yet. Use Search Faculty and click + Save.</div>',
            unsafe_allow_html=True,
        )
    for f in saved_faculty:
        dept  = f.get("department", "")
        desig = f.get("designation", "")
        url   = f.get("profile_url", "")
        meta  = " · ".join(filter(None, [desig, dept]))

        col_f, col_rm = st.columns([9, 1])
        with col_f:
            st.markdown(
                f'<div class="match-card" style="padding:0.85rem 1.2rem;">'
                f'<div class="match-card-header">'
                f'{avatar_html(f["name"], size=38, font_size="0.75rem")}'
                f'<div>'
                f'<div class="match-card-name">{f["name"]}</div>'
                f'<div class="match-card-meta">{meta}</div>'
                f'</div></div>'
                + (f'<div style="margin-top:4px;">'
                   f'<a href="{url}" target="_blank" class="match-card-email" '
                   f'style="text-decoration:none;">View profile ↗</a>'
                   '</div>' if url else "")
                + '</div>',
                unsafe_allow_html=True,
            )
        with col_rm:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"rm_sf_{f['id']}", help="Remove"):
                api_delete(f"/student/{sid}/save-faculty/{f['id']}")
                st.rerun()

    divider()

    # ── Saved PhD Students ──────────────────────────────────────────────────
    section_label("Saved PhD Researchers")
    phd_data, _ = api_get(f"/student/{sid}/saved-phd")
    saved_phd = phd_data or []

    if not saved_phd:
        st.markdown(
            '<div style="text-align:center;padding:1.5rem;color:#4FB489;font-family:Inter,sans-serif;font-size:0.88rem;">'
            'No saved PhD researchers yet. Use Search PhD Students and click + Save.</div>',
            unsafe_allow_html=True,
        )
    for p in saved_phd:
        meta_parts  = [x for x in [p.get("department",""), p.get("university","SUST")] if x]
        if p.get("supervisor"): meta_parts.append(f"Sup: {p['supervisor']}")

        col_p, col_rm = st.columns([9, 1])
        with col_p:
            st.markdown(
                f'<div class="match-card" style="padding:0.85rem 1.2rem;">'
                f'<div class="match-card-header">'
                f'{avatar_html(p["name"], size=38, font_size="0.75rem")}'
                f'<div>'
                f'<div class="match-card-name">{p["name"]}</div>'
                f'<div class="match-card-meta">{" · ".join(meta_parts)}</div>'
                f'</div></div>'
                + (f'<div class="match-card-research" style="margin-top:4px;">{p.get("research_area","")[:160]}{"…" if len(p.get("research_area",""))>160 else ""}</div>'
                   if p.get("research_area") else "")
                + '</div>',
                unsafe_allow_html=True,
            )
        with col_rm:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"rm_phd_{p['id']}", help="Remove"):
                api_delete(f"/student/{sid}/save-phd/{p['id']}")
                st.rerun()

    divider()

    # ── Saved Students ──────────────────────────────────────────────────────
    section_label("Saved Students")
    st_data, _ = api_get(f"/student/{sid}/saved-students")
    saved_students = st_data or []

    if not saved_students:
        st.markdown(
            '<div style="text-align:center;padding:1.5rem;color:#4FB489;font-family:Inter,sans-serif;font-size:0.88rem;">'
            'No saved students yet.</div>',
            unsafe_allow_html=True,
        )
    for s in saved_students:
        meta_parts = [x for x in [s.get("department",""), s.get("university","")] if x]
        tags_html  = render_tag_chips(s.get("tags", []))

        col_s, col_rm = st.columns([9, 1])
        with col_s:
            st.markdown(
                f'<div class="match-card" style="padding:0.85rem 1.2rem;">'
                f'<div class="match-card-header">'
                f'{avatar_html(s["name"], size=38, font_size="0.75rem")}'
                f'<div>'
                f'<div class="match-card-name">{s["name"]}</div>'
                f'<div class="match-card-meta">{" · ".join(meta_parts)}</div>'
                f'</div></div>'
                + (f'<div class="match-card-research" style="margin-top:4px;">{s.get("bio","")[:120]}…</div>'
                   if s.get("bio") else "")
                + (tags_html if tags_html else "")
                + '</div>',
                unsafe_allow_html=True,
            )
        with col_rm:
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"rm_st_{s['id']}", help="Remove"):
                api_delete(f"/student/{sid}/save-student/{s['id']}")
                st.rerun()
