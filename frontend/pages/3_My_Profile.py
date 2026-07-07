import streamlit as st
import requests
from utils import (BASE_CSS, BACKEND_URL, auth_headers, is_logged_in,
                   api_get, api_post, api_delete, get_initials,
                   render_tag_chips, section_label, divider, SUGGESTED_TAGS)

st.markdown(BASE_CSS, unsafe_allow_html=True)

for key, default in [("token",""),("student_id",None),("student_name","")]:
    if key not in st.session_state:
        st.session_state[key] = default

if not is_logged_in():
    st.markdown(
        '<div class="profile-hero">'
        '<div style="font-size:2rem;margin-bottom:0.8rem;">🔒</div>'
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

initials     = get_initials(profile["name"])
existing_tags = profile.get("tags", [])
tag_texts    = [t["tag"] for t in existing_tags]

# ── Profile hero ───────────────────────────────────────────────────────────
meta_parts = [x for x in [profile.get("department",""), profile.get("university","")] if x]
if profile.get("year"):
    meta_parts.append(profile["year"])

st.markdown(
    f'<div class="profile-hero">'
    f'<div class="profile-avatar-lg">{initials}</div>'
    f'<div class="profile-name">{profile["name"]}</div>'
    f'<div class="profile-meta">{" · ".join(meta_parts)}</div>'
    + (f'<div style="margin-top:0.8rem;">{render_tag_chips(tag_texts, dark=True)}</div>' if tag_texts else "")
    + '</div>',
    unsafe_allow_html=True,
)

# ── Tabs ───────────────────────────────────────────────────────────────────
tab_edit, tab_posts, tab_tags, tab_saved = st.tabs(
    ["  ✏️  Edit Profile  ", "  📝  Posts  ", "  🏷️  Tags  ", "  🔖  Saved  "]
)

# ═══════════════════════ TAB 1 — EDIT ═══════════════════════════════════════
with tab_edit:
    section_label("Update your profile")
    with st.form("edit_profile"):
        bio        = st.text_area("Bio / About me", value=profile.get("bio") or "",
                                   height=120,
                                   placeholder="Describe your research interests, background, and collaboration goals…")
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
                      "department": department, "year": year},
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
    with st.form("add_post"):
        post_type = st.radio("Type", ["Work / Project", "Research Interest"], horizontal=True)
        title     = st.text_input("Title", placeholder="e.g. Paper on Bangla NLP tokenisation")
        content   = st.text_area("Details (optional)", height=90,
                                  placeholder="Describe what you did, what methods you used, what you found…")
        if st.form_submit_button("Publish post", use_container_width=True, type="primary"):
            if not title.strip():
                st.error("Title is required.")
            else:
                ptype = "work" if "Work" in post_type else "interest"
                _, err = api_post(f"/student/{sid}/posts",
                                  {"title": title.strip(), "content": content.strip(),
                                   "post_type": ptype})
                if err:
                    st.error(err)
                else:
                    st.success("Post published!")
                    st.rerun()

    divider()
    posts = profile.get("posts", [])
    if not posts:
        st.markdown(
            '<div style="text-align:center;padding:2rem;color:#5A7042;font-family:Inter,sans-serif;font-size:0.9rem;">'
            'No posts yet. Share your work or research interests above.</div>',
            unsafe_allow_html=True,
        )
    for post in posts:
        type_label = "Work / Project" if post["post_type"] == "work" else "Research Interest"
        col_post, col_del = st.columns([9, 1])
        with col_post:
            st.markdown(
                f'<div class="post-card">'
                f'<div class="post-type-badge">{type_label}</div>'
                f'<div class="post-title">{post["title"]}</div>'
                + (f'<div class="post-content">{post["content"]}</div>' if post.get("content") else "")
                + f'<div class="post-date">{post["created_at"][:10]}</div>'
                + '</div>',
                unsafe_allow_html=True,
            )
        with col_del:
            st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
            if st.button("✕", key=f"del_post_{post['id']}", help="Delete post"):
                api_delete(f"/student/{sid}/posts/{post['id']}")
                st.rerun()

# ═══════════════════════ TAB 3 — TAGS ═══════════════════════════════════════
with tab_tags:
    st.markdown(
        '<div class="info-banner" style="margin-top:0.5rem;">'
        '<p>Tags appear as colored chips behind your name when others search for PhD students and researchers. '
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

# ═══════════════════════ TAB 4 — SAVED ══════════════════════════════════════
with tab_saved:
    # ── Saved Faculty ──────────────────────────────────────────────────────
    section_label("Saved Professors")
    fac_data, _ = api_get(f"/student/{sid}/saved-faculty")
    saved_faculty = fac_data or []

    if not saved_faculty:
        st.markdown(
            '<div style="text-align:center;padding:1.5rem;color:#5A7042;font-family:Inter,sans-serif;font-size:0.88rem;">'
            'No saved professors yet. Use Search Faculty and click + Save.</div>',
            unsafe_allow_html=True,
        )
    for f in saved_faculty:
        initials_f = get_initials(f["name"])
        dept  = f.get("department", "")
        desig = f.get("designation", "")
        email = f.get("email", "")
        url   = f.get("profile_url", "")
        meta  = " · ".join(filter(None, [desig, dept]))

        col_f, col_rm = st.columns([9, 1])
        with col_f:
            st.markdown(
                f'<div class="match-card" style="padding:0.85rem 1.2rem;">'
                f'<div class="match-card-header">'
                f'<div class="avatar" style="width:38px;height:38px;font-size:0.75rem;">{initials_f}</div>'
                f'<div>'
                f'<div class="match-card-name">{f["name"]}</div>'
                f'<div class="match-card-meta">{meta}</div>'
                f'</div></div>'
                + (f'<div style="margin-top:4px;">'
                   + (f'<span class="match-card-email">{email}</span>')
                   + '</div>' if email else "")
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
            '<div style="text-align:center;padding:1.5rem;color:#5A7042;font-family:Inter,sans-serif;font-size:0.88rem;">'
            'No saved PhD researchers yet. Use Search PhD Students and click + Save.</div>',
            unsafe_allow_html=True,
        )
    for p in saved_phd:
        initials_p  = get_initials(p["name"])
        meta_parts  = [x for x in [p.get("department",""), p.get("university","SUST")] if x]
        if p.get("supervisor"): meta_parts.append(f"Sup: {p['supervisor']}")

        col_p, col_rm = st.columns([9, 1])
        with col_p:
            st.markdown(
                f'<div class="match-card" style="padding:0.85rem 1.2rem;">'
                f'<div class="match-card-header">'
                f'<div class="avatar" style="width:38px;height:38px;font-size:0.75rem;">{initials_p}</div>'
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
            '<div style="text-align:center;padding:1.5rem;color:#5A7042;font-family:Inter,sans-serif;font-size:0.88rem;">'
            'No saved students yet.</div>',
            unsafe_allow_html=True,
        )
    for s in saved_students:
        initials_s = get_initials(s["name"])
        meta_parts = [x for x in [s.get("department",""), s.get("university","")] if x]
        tags_html  = render_tag_chips(s.get("tags", []))

        col_s, col_rm = st.columns([9, 1])
        with col_s:
            st.markdown(
                f'<div class="match-card" style="padding:0.85rem 1.2rem;">'
                f'<div class="match-card-header">'
                f'<div class="avatar" style="width:38px;height:38px;font-size:0.75rem;">{initials_s}</div>'
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
