import re
import streamlit as st
from utils import (api_get, api_post, is_logged_in, divider, get_initials,
                   avatar_html, time_ago, render_tag_chips, section_label,
                   APP_NAME)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
# Letters only (spaces, dots, hyphens, apostrophes allowed) — no numbers.
NAME_RE  = re.compile(r"^(?=.*[^\W\d_])(?:[^\W\d_]|[ .'\-])+$", re.UNICODE)

_TYPE_LABELS = {
    "work":          "Work",
    "project":       "Project",
    "interest":      "Research Interest",
    "certification": "Certification",
}

for key, default in [("token", ""), ("student_id", None), ("student_name", "")]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Logged in: personal feed ────────────────────────────────────────────────
if is_logged_in():
    sid = st.session_state.student_id
    profile, _ = api_get(f"/student/{sid}")
    profile = profile or {}

    name       = profile.get("name") or st.session_state.student_name
    first_name = name.split()[0] if name else "there"
    meta_parts = [x for x in [profile.get("department", ""),
                              profile.get("university", ""),
                              profile.get("year", "")] if x]

    col_id, col_out = st.columns([8, 2])
    with col_id:
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:14px;padding:0.4rem 0 1.1rem 0;">'
            f'{avatar_html(name, profile.get("photo_b64"), size=52, font_size="1rem")}'
            f'<div>'
            f'<div style="font-family:Sora,sans-serif;font-size:1.25rem;font-weight:700;color:#ECFCF3;">'
            f'Hi, {first_name}</div>'
            f'<div style="font-family:Inter,sans-serif;font-size:0.8rem;color:#4FB489;">'
            f'{" · ".join(meta_parts) if meta_parts else "Welcome back"}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
    with col_out:
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("Log out", type="secondary", use_container_width=True):
            api_post("/auth/logout")
            for k in ["token", "student_id", "student_name"]:
                st.session_state[k] = "" if k == "token" else None
            st.rerun()

    # Nudge to set interests if the feed can't be personalized yet
    if not (profile.get("research_interests") or "").strip():
        st.markdown(
            '<div class="info-banner"><p>Your feed gets smarter when you add '
            '<strong>research interests</strong> to your profile — go to '
            '<em>My Profile → Edit Profile</em>. For now you\'re seeing the latest posts.</p></div>',
            unsafe_allow_html=True,
        )

    section_label("Your feed — students who share your interests")

    feed, feed_err = api_get(f"/student/{sid}/feed")
    if feed_err:
        st.error("Could not load your feed. Is the backend running?")
        feed = []

    if not feed:
        st.markdown(
            '<div style="text-align:center;padding:2.5rem 1rem;color:#4FB489;'
            'font-family:Inter,sans-serif;font-size:0.9rem;">'
            'Nothing here yet — when other students post their work and interests, '
            'you\'ll see it here.</div>',
            unsafe_allow_html=True,
        )

    for item in feed:
        a       = item["author"]
        matched = item.get("matched", [])
        content = item.get("content", "")
        if len(content) > 380:
            content = content[:380].rsplit(" ", 1)[0] + "…"

        meta = " · ".join(filter(None, [a.get("department", ""), a.get("year", "")]))
        pills = f'<span class="type-pill">{_TYPE_LABELS.get(item["post_type"], "Post")}</span>'
        if item.get("match_score", 0) > 0 and matched:
            shared = " · ".join(matched[:3])
            pills += f'<span class="match-pill">Shared: {shared}</span>'

        st.markdown(
            f'<div class="feed-card">'
            f'<div class="feed-top">'
            f'{avatar_html(a["name"], a.get("photo_b64"), a.get("photo_mime", "image/jpeg"), size=42, font_size="0.78rem")}'
            f'<div class="feed-who">'
            f'<div class="feed-name">{a["name"]}</div>'
            f'<div class="feed-meta">{meta}</div>'
            f'</div>'
            f'<div class="feed-time">{time_ago(item["created_at"])}</div>'
            f'</div>'
            f'<div class="feed-title">{item["title"]}</div>'
            + (f'<div class="feed-body">{content}</div>' if content else "")
            + (f'<img class="post-img" src="data:{item.get("image_mime") or "image/jpeg"};'
               f'base64,{item["image_b64"]}" alt=""/>' if item.get("image_b64") else "")
            + f'<div class="feed-foot">{pills}</div>'
            + '</div>',
            unsafe_allow_html=True,
        )

    st.stop()

# ── Landing / Auth (logged out) ─────────────────────────────────────────────
st.markdown(
    '<div class="landing-hero">'
    '<div class="landing-badge">AI research matchmaking · SUST</div>'
    '<div class="landing-title">Find the people behind<br/>your <em>next research idea</em></div>'
    '<div class="landing-subtitle">'
    f'{APP_NAME} matches you with professors, PhD researchers and fellow students '
    'who work on what you care about — just describe it in plain language.'
    '</div>'
    '<div class="landing-stats">'
    '<div><div class="landing-stat-num">611+</div><div class="landing-stat-label">Faculty profiles</div></div>'
    '<div><div class="landing-stat-num">33</div><div class="landing-stat-label">PhD researchers</div></div>'
    '<div><div class="landing-stat-num">1</div><div class="landing-stat-label">Campus network</div></div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)

col_auth, col_feat = st.columns([11, 9], gap="large")

with col_auth:
    st.markdown('<div class="auth-panel">', unsafe_allow_html=True)
    tab_login, tab_signup = st.tabs(["  Log in  ", "  Sign up  "])

    with tab_login:
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        with st.form("login_form"):
            email    = st.text_input("Email address", placeholder="you@example.com")
            password = st.text_input("Password", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Log in", use_container_width=True, type="primary")
        if submitted:
            if not email or not password:
                st.error("Please fill in both fields.")
            else:
                data, err = api_post("/auth/login", {"email": email, "password": password})
                if err:
                    st.error(err)
                else:
                    st.session_state.token        = data["token"]
                    st.session_state.student_id   = data["student_id"]
                    st.session_state.student_name = data["name"]
                    st.rerun()

    with tab_signup:
        st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
        with st.form("signup_form"):
            name       = st.text_input("Full name", placeholder="e.g. Rafiul Islam")
            email_s    = st.text_input("Email address", placeholder="you@sust.edu", key="su_email")
            password_s = st.text_input("Password", type="password",
                                       placeholder="Minimum 6 characters", key="su_pw")
            col_u, col_d = st.columns(2)
            with col_u:
                university = st.text_input("University", value="SUST")
            with col_d:
                department = st.text_input("Department", placeholder="e.g. CSE")
            year = st.selectbox("Year / Status",
                                ["", "1st Year", "2nd Year", "3rd Year", "4th Year",
                                 "Masters", "PhD Student", "Graduate"])
            submitted_s = st.form_submit_button("Create account", use_container_width=True, type="primary")
        if submitted_s:
            if not name or not email_s or not password_s:
                st.error("Name, email and password are required.")
            elif not NAME_RE.fullmatch(name.strip()):
                st.error("Full name can only contain letters (spaces, dots, hyphens allowed) — no numbers or symbols.")
            elif not EMAIL_RE.fullmatch(email_s.strip()):
                st.error("Please enter a valid email address, e.g. you@sust.edu.")
            elif len(password_s) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                _, err = api_post("/auth/signup", {
                    "name": name, "email": email_s, "password": password_s,
                    "university": university, "department": department, "year": year,
                })
                if err:
                    st.error(err)
                else:
                    st.success("Account created! Switch to the Log in tab.")
    st.markdown("</div>", unsafe_allow_html=True)

with col_feat:
    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)
    features = [
        ("Ask in plain language",
         "No filters or dropdowns — describe the research area you're interested in and let the AI do the matching."),
        ("A feed that knows your field",
         "See what students with overlapping interests are building, publishing and looking for."),
        ("A profile that works for you",
         "Photo, CV, documents, projects and certifications — everything a potential collaborator needs to say yes."),
    ]
    for title, desc in features:
        st.markdown(
            f'<div class="match-card">'
            f'<div class="match-card-name" style="font-size:0.92rem;">{title}</div>'
            f'<div class="match-card-research" style="margin-top:0.35rem;font-size:0.82rem;">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
