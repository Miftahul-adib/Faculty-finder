import streamlit as st
import re
from utils import (api_post, is_logged_in, divider, get_initials, APP_NAME)

for key, default in [("token", ""), ("student_id", None), ("student_name", "")]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Logged in ──────────────────────────────────────────────────────────────
if is_logged_in():
    initials = get_initials(st.session_state.student_name)
    st.markdown(
        f'<div class="profile-hero">'
        f'<div class="profile-avatar-lg">{initials}</div>'
        f'<div class="profile-name">{st.session_state.student_name}</div>'
        f'<div class="profile-meta">Welcome back — use the sidebar to navigate</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)
    cards = [
        ("🔍", "Search Faculty", "Ask in natural language — AI matches you with the right professors for supervision or collaboration."),
        ("👥", "Search PhD Students", "Find PhD researchers by topic, method, or collaboration tag. Connect with peers."),
        ("👤", "My Profile", "Manage saved professors and researchers, post your works, and set collaboration tags."),
    ]
    for col, (icon, title, desc) in zip([c1, c2, c3], cards):
        with col:
            st.markdown(
                f'<div class="match-card" style="border-left-color:#3C9C6E;">'
                f'<div style="font-size:1.5rem;margin-bottom:0.5rem;">{icon}</div>'
                f'<div class="match-card-name" style="font-size:0.95rem;">{title}</div>'
                f'<div class="match-card-research" style="margin-top:0.4rem;font-size:0.82rem;">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    divider()
    if st.button("Log out", type="secondary"):
        api_post("/auth/logout")
        for k in ["token", "student_id", "student_name"]:
            st.session_state[k] = "" if k == "token" else None
        st.rerun()
    st.stop()

# ── Landing / Auth ───────────────────────────────────────────────────────────
st.markdown(
    '<div class="landing-hero">'
    '<div class="landing-glow"></div>'
    '<div class="landing-badge">🔬 AI-powered research matchmaking</div>'
    f'<div class="landing-title">Find your next<br/>research connection</div>'
    '<div class="landing-subtitle">'
    f'{APP_NAME} pairs you with the professors, PhD researchers, and collaborators '
    'who match your interests — described in plain language, not keyword search.'
    '</div>'
    '<div class="landing-stats">'
    '<div><div class="landing-stat-num">611+</div><div class="landing-stat-label">FACULTY PROFILES</div></div>'
    '<div><div class="landing-stat-num">AI</div><div class="landing-stat-label">SEMANTIC MATCHING</div></div>'
    '<div><div class="landing-stat-num">SUST</div><div class="landing-stat-label">CAMPUS NETWORK</div></div>'
    '</div>'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown("<div style='height:1.4rem'></div>", unsafe_allow_html=True)

_, mid, _ = st.columns([1, 10, 1])
with mid:
    st.markdown('<div class="auth-panel">', unsafe_allow_html=True)
    tab_login, tab_signup = st.tabs(["  Log in  ", "  Sign up  "])

    with tab_login:
        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
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
        st.markdown("<div style='height:0.8rem'></div>", unsafe_allow_html=True)
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
                                ["","1st Year","2nd Year","3rd Year","4th Year",
                                 "Masters","PhD Student","Graduate"])
            submitted_s = st.form_submit_button("Create account", use_container_width=True, type="primary")
        if submitted_s:
            # Frontend validation
            if not name or not email_s or not password_s:
                st.error("Name, email and password are required.")
            elif not re.match(r'^[a-zA-Z\s]{2,50}$', name.strip()):
                st.error("Full name can only contain letters and spaces (2-50 characters).")
            elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email_s.strip()):
                st.error("Please enter a valid email address (e.g. name@sust.edu).")
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

divider()

f1, f2, f3 = st.columns(3)
features = [
    ("💬", "Ask in plain language", "No filters or dropdowns — just describe the research area you're interested in."),
    ("🎯", "AI-ranked matches", "Semantic search surfaces the professors and peers most relevant to your query."),
    ("🔖", "Save & organize", "Bookmark professors and researchers, tag your own interests, and build your network."),
]
for col, (icon, title, desc) in zip([f1, f2, f3], features):
    with col:
        st.markdown(
            f'<div class="match-card" style="border-left-color:#3C9C6E;">'
            f'<div style="font-size:1.4rem;margin-bottom:0.5rem;">{icon}</div>'
            f'<div class="match-card-name" style="font-size:0.92rem;">{title}</div>'
            f'<div class="match-card-research" style="margin-top:0.4rem;font-size:0.8rem;">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )