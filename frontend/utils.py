import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

APP_NAME = "ScholarLink"
APP_ICON = "🔬"
APP_TAGLINE = "Research Matchmaking"

SUGGESTED_TAGS = [
    "Looking for research partner in ML",
    "Looking for research partner in NLP",
    "Looking for research partner in Computer Vision",
    "Looking for research partner in Bioinformatics",
    "Looking for research partner in IoT",
    "Open to research collaboration",
    "Looking for co-author",
    "Seeking PhD supervisor",
    "Available for project collaboration",
    "Looking for industry partner",
    "Open to internship opportunities",
    "Seeking thesis partner",
]

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

/* ── Color palette (7 shades of green) ─────────────────────
   #04140E  deepest dark
   #092219  very dark bg
   #0D2E22  main background
   #153D2E  sidebar / card base
   #1B4B38  elevated card
   #246142  accent borders
   #2E7E56  primary / buttons
   #3C9C6E  secondary accent
   #4FB489  links / meta text
   #6ECDA0  active / hover
   #8FE0B8  light accent
   #C6EFDA  body text
   #D9F7E6  tag chips / badges
   #ECFCF3  headings on dark
   #F1FAF6  light card bg
──────────────────────────────────────────────────────────── */

html, body, .stApp,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stVerticalBlock"],
.main, .block-container {
    background-color: #0D2E22 !important;
    color: #C6EFDA !important;
}

.block-container {
    max-width: 860px !important;
    padding-top: 2.5rem !important;
    padding-bottom: 7rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="baseButton-headerNoPadding"] { display: none !important; }

/* Keep the header bar itself (not display:none) so the sidebar
   collapse/expand arrow it contains stays visible and clickable —
   just make it blend into the background. */
[data-testid="stHeader"] {
    background: transparent !important;
    box-shadow: none !important;
}
[data-testid="stHeader"] * { color: #8FE0B8 !important; }

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #071B14 0%, #0C2A20 50%, #0D2E22 100%) !important;
    border-right: 1px solid #153D2E !important;
    min-width: 260px !important;
}
[data-testid="stSidebar"] * { color: #8FE0B8 !important; }

/* Sidebar is always open — hide the collapse control entirely so it
   can't be closed (and there's nothing to bring back). */
[data-testid="stSidebarCollapseButton"],
[data-testid="stExpandSidebarButton"] { display: none !important; }

[data-testid="stSidebar"] a {
    border-radius: 8px !important;
    padding: 0.45rem 0.9rem !important;
    margin: 3px 0 !important;
    transition: background 0.15s !important;
    text-decoration: none !important;
}
[data-testid="stSidebar"] a:hover {
    background: rgba(110,205,160,0.12) !important;
    color: #ECFCF3 !important;
}
[data-testid="stSidebar"] [aria-current="page"] {
    background: rgba(60,156,110,0.22) !important;
    color: #D9F7E6 !important;
    font-weight: 700 !important;
    border-left: 3px solid #3C9C6E !important;
}

/* ── Landing hero (logged-out intro) ────────────────────────── */
.landing-hero {
    position: relative;
    text-align: center;
    padding: 2.2rem 1rem 1.6rem 1rem;
    overflow: hidden;
}
.landing-glow {
    position: absolute;
    top: -140px;
    left: 50%;
    transform: translateX(-50%);
    width: 480px;
    height: 320px;
    background: radial-gradient(circle, rgba(60,156,110,0.35) 0%, rgba(60,156,110,0) 70%);
    pointer-events: none;
    z-index: 0;
}
.landing-badge {
    position: relative;
    z-index: 1;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(60,156,110,0.14);
    border: 1px solid rgba(60,156,110,0.4);
    color: #6ECDA0 !important;
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 5px 14px;
    border-radius: 999px;
    margin-bottom: 1.1rem;
}
.landing-title {
    position: relative;
    z-index: 1;
    font-family: 'Sora', sans-serif;
    font-size: 3rem;
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -1.2px;
    background: linear-gradient(135deg, #ECFCF3 15%, #6ECDA0 60%, #2E7E56 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}
.landing-subtitle {
    position: relative;
    z-index: 1;
    max-width: 480px;
    margin: 0.9rem auto 0 auto;
    font-family: 'Inter', sans-serif;
    font-size: 1rem;
    color: #8FE0B8;
    line-height: 1.65;
}
.landing-stats {
    position: relative;
    z-index: 1;
    display: flex;
    justify-content: center;
    gap: 2.2rem;
    margin-top: 1.8rem;
    flex-wrap: wrap;
}
.landing-stat-num {
    font-family: 'Sora', sans-serif;
    font-size: 1.4rem;
    font-weight: 800;
    color: #ECFCF3;
}
.landing-stat-label {
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    color: #4FB489;
    letter-spacing: 0.03em;
    margin-top: 2px;
}

/* ── Page header ──────────────────────────────────────────── */
.page-hero {
    text-align: center;
    padding: 0.5rem 0 2rem 0;
}
.page-title {
    font-family: 'Sora', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    color: #ECFCF3;
    letter-spacing: -0.8px;
    line-height: 1.08;
}
.page-title-accent {
    display: block;
    width: 52px;
    height: 3px;
    background: linear-gradient(90deg, #2E7E56, #6ECDA0, #8FE0B8);
    border-radius: 2px;
    margin: 0.55rem auto 0.9rem auto;
}
.page-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    font-weight: 400;
    color: #4FB489;
    line-height: 1.6;
}

/* ── Info banner ─────────────────────────────────────────── */
.info-banner {
    background: linear-gradient(135deg, #1E2D13 0%, #153D2E 100%);
    border: 1px solid #1B4B38;
    border-left: 4px solid #3C9C6E;
    border-radius: 12px;
    padding: 1rem 1.3rem;
    margin-bottom: 1.5rem;
}
.info-banner p {
    font-family: 'Inter', sans-serif;
    font-size: 0.86rem;
    color: #8FE0B8;
    margin: 0.3rem 0;
    line-height: 1.65;
}
.info-banner em { color: #C6EFDA; font-style: italic; }
.info-banner strong { color: #D9F7E6; font-weight: 600; }

/* ── Section headings ────────────────────────────────────── */
.section-label {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.15em;
    text-transform: uppercase;
    color: #3C9C6E;
    margin: 1.6rem 0 0.9rem 0;
}
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, #1B4B38, transparent);
}

/* ── Match cards (cream, for profile saved lists) ────────── */
.match-card {
    background: #F1FAF6;
    border-radius: 14px;
    border-left: 4px solid #3C9C6E;
    padding: 1.2rem 1.4rem 1.1rem 1.4rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.match-card-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 0.6rem;
}
.avatar {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: linear-gradient(135deg, #246142 0%, #4FB489 100%);
    color: #ECFCF3;
    font-family: 'Sora', sans-serif;
    font-size: 0.85rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    letter-spacing: 0.5px;
}
.match-card-name {
    font-family: 'Inter', sans-serif;
    font-size: 1.02rem;
    font-weight: 700;
    color: #0D2E22;
    line-height: 1.25;
}
.match-card-meta {
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem;
    font-weight: 500;
    color: #2E7E56;
    margin-top: 3px;
    line-height: 1.4;
}
.match-card-research {
    font-family: 'Inter', sans-serif;
    font-size: 0.84rem;
    color: #1B4B38;
    line-height: 1.65;
    margin-bottom: 0.5rem;
}
.match-card-email {
    font-family: 'Inter', sans-serif;
    font-size: 0.76rem;
    color: #3C9C6E;
    margin-top: 4px;
}

/* ── Dark candidate cards (below chat response) ──────────── */
.dark-card {
    background: linear-gradient(135deg, #162010 0%, #1E2D13 60%, #153D2E 100%);
    border: 1px solid #1B4B38;
    border-left: 3px solid #2E7E56;
    border-radius: 12px;
    padding: 0.9rem 1.1rem;
    margin-bottom: 6px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.3);
}
.dark-card-name {
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    color: #ECFCF3;
    line-height: 1.3;
}
.dark-card-meta {
    font-family: 'Inter', sans-serif;
    font-size: 0.76rem;
    color: #6ECDA0;
    margin-top: 3px;
}
.dark-card-research {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    color: #8FE0B8;
    margin-top: 6px;
    line-height: 1.6;
}

/* ── Tag chips ───────────────────────────────────────────── */
.tag-row { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 7px; }
.tag-chip {
    display: inline-block;
    background: #E8F5D8;
    border: 1.5px solid #8FE0B8;
    color: #153D2E !important;
    font-family: 'Inter', sans-serif;
    font-size: 0.71rem;
    font-weight: 700;
    padding: 3px 11px;
    border-radius: 20px;
    white-space: nowrap;
    letter-spacing: 0.01em;
}
.tag-chip-dark {
    display: inline-block;
    background: rgba(60,156,110,0.2);
    border: 1.5px solid #246142;
    color: #8FE0B8 !important;
    font-family: 'Inter', sans-serif;
    font-size: 0.71rem;
    font-weight: 700;
    padding: 3px 11px;
    border-radius: 20px;
    white-space: nowrap;
    letter-spacing: 0.01em;
}

/* ── Post cards ──────────────────────────────────────────── */
.post-card {
    background: linear-gradient(135deg, #162010 0%, #1E2D13 100%);
    border: 1px solid #1B4B38;
    border-radius: 12px;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
}
.post-type-badge {
    display: inline-block;
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6ECDA0;
    background: rgba(60,156,110,0.18);
    border: 1px solid #246142;
    border-radius: 4px;
    padding: 2px 8px;
    margin-bottom: 0.5rem;
}
.post-title {
    font-family: 'Inter', sans-serif;
    font-size: 0.97rem;
    font-weight: 700;
    color: #ECFCF3;
    margin-bottom: 0.35rem;
    line-height: 1.4;
}
.post-content {
    font-family: 'Inter', sans-serif;
    font-size: 0.86rem;
    color: #8FE0B8;
    line-height: 1.7;
}
.post-date {
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    color: #3C9C6E;
    margin-top: 0.5rem;
}

/* ── Profile hero ────────────────────────────────────────── */
.profile-hero {
    background: linear-gradient(135deg, #092219 0%, #1E2D13 50%, #153D2E 100%);
    border: 1px solid #1B4B38;
    border-radius: 16px;
    padding: 2rem 2rem;
    margin-bottom: 1.5rem;
    text-align: center;
}
.profile-avatar-lg {
    width: 76px;
    height: 76px;
    border-radius: 50%;
    background: linear-gradient(135deg, #246142 0%, #4FB489 100%);
    color: #ECFCF3;
    font-family: 'Sora', sans-serif;
    font-size: 1.55rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 1rem auto;
    box-shadow: 0 4px 20px rgba(0,0,0,0.35), 0 0 0 4px rgba(60,156,110,0.2);
}
.profile-name {
    font-family: 'Sora', sans-serif;
    font-size: 1.65rem;
    font-weight: 800;
    color: #ECFCF3;
    margin-bottom: 0.3rem;
}
.profile-meta {
    font-family: 'Inter', sans-serif;
    font-size: 0.88rem;
    color: #6ECDA0;
}

/* ── Auth card ───────────────────────────────────────────── */
.auth-panel {
    background: linear-gradient(135deg, #1E2D13 0%, #153D2E 100%);
    border: 1px solid #1B4B38;
    border-radius: 16px;
    padding: 2rem 2.2rem;
    max-width: 440px;
    margin: 0 auto;
    box-shadow: 0 8px 32px rgba(0,0,0,0.25);
}

/* ── Streamlit widget overrides ──────────────────────────── */
[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea {
    background-color: #092219 !important;
    color: #C6EFDA !important;
    border: 1.5px solid #1B4B38 !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.9rem !important;
    transition: border-color 0.2s !important;
}
[data-testid="stTextInput"] input:focus,
[data-testid="stTextArea"] textarea:focus {
    border-color: #3C9C6E !important;
    box-shadow: 0 0 0 3px rgba(60,156,110,0.15) !important;
}
[data-testid="stTextInput"] label,
[data-testid="stTextArea"] label,
[data-testid="stSelectbox"] label,
[data-testid="stRadio"] label {
    color: #4FB489 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.83rem !important;
    font-weight: 500 !important;
    margin-bottom: 4px !important;
}
[data-testid="stSelectbox"] > div > div {
    background-color: #092219 !important;
    border: 1.5px solid #1B4B38 !important;
    border-radius: 10px !important;
    color: #C6EFDA !important;
}

/* Buttons */
[data-testid="stButton"] > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button {
    background: linear-gradient(135deg, #246142, #2E7E56) !important;
    color: #ECFCF3 !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.5rem 1.1rem !important;
    transition: all 0.15s !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    background: linear-gradient(135deg, #2E7E56, #3C9C6E) !important;
    box-shadow: 0 2px 8px rgba(46,126,86,0.35) !important;
}
[data-testid="stButton"] > button[kind="secondary"] {
    background: rgba(36,97,66,0.15) !important;
    color: #6ECDA0 !important;
    border: 1.5px solid #246142 !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: rgba(36,97,66,0.28) !important;
    color: #8FE0B8 !important;
}
[data-testid="stButton"] > button {
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
}

/* Tabs */
[data-testid="stTabs"] {
    border-bottom: 1px solid #153D2E !important;
}
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 2px !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    color: #4FB489 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    background: transparent !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 0.5rem 1.1rem !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #ECFCF3 !important;
    font-weight: 700 !important;
    background: rgba(60,156,110,0.14) !important;
    border-bottom: 3px solid #3C9C6E !important;
}
[data-testid="stTabPanel"] {
    padding-top: 1.2rem !important;
}

/* Radio */
[data-testid="stRadio"] > div { flex-direction: row !important; gap: 1rem !important; }
[data-testid="stRadio"] label { color: #8FE0B8 !important; }

/* Alerts */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
}

/* Spinner */
[data-testid="stSpinner"] p {
    font-family: 'Inter', sans-serif !important;
    color: #4FB489 !important;
    font-size: 0.88rem !important;
}

/* Caption */
[data-testid="stCaptionContainer"] p {
    color: #3C9C6E !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.73rem !important;
}

/* ── Chat UI ──────────────────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
}
[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"],
[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"],
[data-testid="stChatMessage"] > div:first-child { display: none !important; }

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-end !important;
    padding: 0.25rem 0 !important;
    margin-top: 1.2rem !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"] {
    background: linear-gradient(135deg, #1B4B38, #246142) !important;
    color: #ECFCF3 !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 0.7rem 1.1rem !important;
    max-width: 82% !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.2) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"] p {
    color: #ECFCF3 !important;
    margin: 0 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    display: block !important;
    padding: 0.5rem 0 1.2rem 0 !important;
    border-bottom: 1px solid rgba(27,75,56,0.5) !important;
    margin-top: 0.5rem !important;
}
[data-testid="stChatMessage"]:last-of-type:has([data-testid="chatAvatarIcon-assistant"]) {
    border-bottom: none !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] {
    background: transparent !important;
    padding: 0 !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] p,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] li {
    font-family: 'Inter', sans-serif !important;
    color: #C6EFDA !important;
    font-size: 0.92rem !important;
    line-height: 1.8 !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] h2,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] h3 {
    font-family: 'Sora', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 700 !important;
    color: #8FE0B8 !important;
    margin: 1.2rem 0 0.45rem 0 !important;
    padding-bottom: 5px !important;
    border-bottom: 1px solid rgba(36,97,66,0.4) !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] strong {
    color: #D9F7E6 !important;
    font-weight: 700 !important;
}
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] hr {
    border-color: #153D2E !important;
    margin: 0.7rem 0 !important;
}

/* Chat input */
[data-testid="stChatFloatingInputContainer"],
[data-testid="stBottomBlockContainer"],
div:has([data-testid="stChatInput"]) {
    background-color: #0D2E22 !important;
    border: none !important;
}
[data-testid="stChatInput"] > div,
[data-testid="stChatInputContainer"] {
    background-color: #092219 !important;
    border: 1.5px solid #1B4B38 !important;
    border-radius: 14px !important;
    transition: border-color 0.2s !important;
}
[data-testid="stChatInput"] > div:focus-within,
[data-testid="stChatInputContainer"]:focus-within {
    border-color: #3C9C6E !important;
    box-shadow: 0 0 0 3px rgba(36,97,66,0.1) !important;
}
[data-testid="stChatInput"] textarea {
    background-color: #092219 !important;
    color: #C6EFDA !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.93rem !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #246142 !important; }
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #246142, #2E7E56) !important;
    border-radius: 10px !important;
}

/* ── Scrollbar ────────────────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #153D2E; border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: #246142; }

/* ── Divider ──────────────────────────────────────────────── */
.thin-divider {
    border: none;
    border-top: 1px solid #1E2D13;
    margin: 1.2rem 0;
}

/* ── Responsive ───────────────────────────────────────────── */
@media (max-width: 700px) {
    .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
    .page-title { font-size: 1.9rem; }
    .match-card { padding: 1rem 1.1rem; }
}
</style>
"""


def get_initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "?"


def auth_headers():
    token = st.session_state.get("token", "")
    return {"x-token": token} if token else {}


def is_logged_in():
    return bool(st.session_state.get("token"))


def api_get(path, params=None):
    try:
        r = requests.get(f"{BACKEND_URL}{path}", params=params,
                         headers=auth_headers(), timeout=30)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)


def api_post(path, json=None):
    try:
        r = requests.post(f"{BACKEND_URL}{path}", json=json,
                          headers=auth_headers(), timeout=120)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get("detail", str(e))
        except Exception:
            detail = str(e)
        return None, detail
    except requests.exceptions.RequestException as e:
        return None, str(e)


def api_delete(path):
    try:
        r = requests.delete(f"{BACKEND_URL}{path}",
                            headers=auth_headers(), timeout=15)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)


def render_tag_chips(tags, dark=False):
    if not tags:
        return ""
    cls = "tag-chip-dark" if dark else "tag-chip"
    chips = "".join(f'<span class="{cls}">{t}</span>' for t in tags)
    return f'<div class="tag-row">{chips}</div>'


def page_header(title: str, subtitle: str = ""):
    st.markdown(
        f'<div class="page-hero">'
        f'<div class="page-title">{title}</div>'
        f'<div class="page-title-accent"></div>'
        + (f'<div class="page-subtitle">{subtitle}</div>' if subtitle else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def section_label(text: str):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def divider():
    st.markdown('<hr class="thin-divider"/>', unsafe_allow_html=True)
