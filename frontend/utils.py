import os
from datetime import datetime, timezone

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

# ── Color palette (greens) ──────────────────────────────────
#  #04140E deepest   #092219 very dark   #0D2E22 background
#  #153D2E card base #1B4B38 borders     #246142 accent line
#  #2E7E56 primary   #3C9C6E secondary   #4FB489 muted text
#  #6ECDA0 hover     #8FE0B8 light       #C6EFDA body text
#  #D9F7E6 chips     #ECFCF3 headings
# ────────────────────────────────────────────────────────────

BASE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=Inter:wght@400;500;600;700&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

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
    max-width: 820px !important;
    padding-top: 2.2rem !important;
    padding-bottom: 7rem !important;
    padding-left: 2rem !important;
    padding-right: 2rem !important;
}

#MainMenu, footer,
[data-testid="stToolbar"],
[data-testid="baseButton-headerNoPadding"] { display: none !important; }

[data-testid="stHeader"] {
    background: transparent !important;
    box-shadow: none !important;
}
[data-testid="stHeader"] * { color: #8FE0B8 !important; }

/* ── Sidebar ─────────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background: #0A241B !important;
    border-right: 1px solid #153D2E !important;
    min-width: 250px !important;
}
[data-testid="stSidebar"] * { color: #8FE0B8 !important; }
[data-testid="stSidebarCollapseButton"],
[data-testid="stExpandSidebarButton"] { display: none !important; }

[data-testid="stSidebar"] a {
    border-radius: 9px !important;
    padding: 0.5rem 0.9rem !important;
    margin: 2px 0 !important;
    transition: background 0.15s !important;
    text-decoration: none !important;
    font-size: 0.9rem !important;
}
[data-testid="stSidebar"] a:hover {
    background: rgba(110,205,160,0.10) !important;
    color: #ECFCF3 !important;
}
[data-testid="stSidebar"] [aria-current="page"] {
    background: rgba(60,156,110,0.18) !important;
    color: #D9F7E6 !important;
    font-weight: 600 !important;
    box-shadow: inset 3px 0 0 #3C9C6E !important;
}

/* ── Landing hero (logged-out) ───────────────────────────── */
.landing-hero {
    position: relative;
    text-align: center;
    padding: 2.6rem 0 1.8rem 0;
}
.landing-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(60,156,110,0.12);
    border: 1px solid rgba(60,156,110,0.35);
    color: #6ECDA0 !important;
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    padding: 5px 12px;
    border-radius: 999px;
    margin-bottom: 1.1rem;
}
.landing-title {
    font-family: 'Sora', sans-serif;
    font-size: 2.7rem;
    font-weight: 800;
    line-height: 1.12;
    letter-spacing: -0.8px;
    color: #ECFCF3;
    max-width: 620px;
    margin: 0 auto;
}
.landing-title em {
    font-style: normal;
    color: #6ECDA0;
}
.landing-subtitle {
    max-width: 540px;
    margin: 0.9rem auto 0 auto;
    font-family: 'Inter', sans-serif;
    font-size: 1rem;
    color: #8FE0B8;
    line-height: 1.65;
}
.landing-stats {
    display: flex;
    justify-content: center;
    gap: 2.4rem;
    margin-top: 1.8rem;
    flex-wrap: wrap;
}
.landing-stat-num {
    font-family: 'Sora', sans-serif;
    font-size: 1.3rem;
    font-weight: 700;
    color: #ECFCF3;
}
.landing-stat-label {
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    color: #4FB489;
    letter-spacing: 0.04em;
    margin-top: 2px;
    text-transform: uppercase;
}

/* ── Page header (centered) ──────────────────────────────── */
.page-hero {
    text-align: center;
    padding: 0.3rem 0 1.6rem 0;
    border-bottom: 1px solid #153D2E;
    margin-bottom: 1.4rem;
}
.page-kicker {
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #3C9C6E;
    margin-bottom: 0.45rem;
}
.page-title {
    font-family: 'Sora', sans-serif;
    font-size: 1.75rem;
    font-weight: 700;
    color: #ECFCF3;
    letter-spacing: -0.4px;
    line-height: 1.15;
}
.page-title-accent { display: none; }
.page-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 0.92rem;
    color: #4FB489;
    line-height: 1.6;
    margin: 0.4rem auto 0 auto;
    max-width: 560px;
}

/* ── Info banner ─────────────────────────────────────────── */
.info-banner {
    background: rgba(21,61,46,0.45);
    border: 1px solid #1B4B38;
    border-left: 3px solid #3C9C6E;
    border-radius: 12px;
    padding: 0.9rem 1.2rem;
    margin-bottom: 1.4rem;
}
.info-banner p {
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    color: #8FE0B8;
    margin: 0.25rem 0;
    line-height: 1.6;
}
.info-banner em { color: #C6EFDA; font-style: italic; }
.info-banner strong { color: #D9F7E6; font-weight: 600; }

/* ── Section headings ────────────────────────────────────── */
.section-label {
    display: flex;
    align-items: center;
    gap: 10px;
    font-family: 'Inter', sans-serif;
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #3C9C6E;
    margin: 1.5rem 0 0.8rem 0;
}
.section-label::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #153D2E;
}

/* ── Avatars ─────────────────────────────────────────────── */
.avatar {
    width: 44px;
    height: 44px;
    border-radius: 50%;
    background: linear-gradient(135deg, #246142 0%, #4FB489 100%);
    color: #ECFCF3;
    font-family: 'Sora', sans-serif;
    font-size: 0.85rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    letter-spacing: 0.5px;
}
.avatar-img {
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
    border: 2px solid #246142;
    display: block;
}

/* ── Cards (unified dark style) ──────────────────────────── */
.match-card {
    background: rgba(21,61,46,0.38);
    border: 1px solid #1B4B38;
    border-radius: 14px;
    padding: 1.1rem 1.25rem 1rem 1.25rem;
    margin-bottom: 0.75rem;
    transition: border-color 0.15s, background 0.15s;
}
.match-card:hover {
    border-color: #2E7E56;
    background: rgba(21,61,46,0.55);
}
.match-card-header {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-bottom: 0.5rem;
}
.match-card-name {
    font-family: 'Inter', sans-serif;
    font-size: 0.98rem;
    font-weight: 700;
    color: #ECFCF3;
    line-height: 1.3;
}
.match-card-meta {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    font-weight: 500;
    color: #4FB489;
    margin-top: 3px;
    line-height: 1.4;
}
.match-card-research {
    font-family: 'Inter', sans-serif;
    font-size: 0.84rem;
    color: #8FE0B8;
    line-height: 1.65;
    margin-bottom: 0.3rem;
}
.match-card-email {
    font-family: 'Inter', sans-serif;
    font-size: 0.76rem;
    color: #6ECDA0;
}

.dark-card {
    background: rgba(21,61,46,0.38);
    border: 1px solid #1B4B38;
    border-radius: 12px;
    padding: 0.85rem 1.05rem;
    margin-bottom: 6px;
    transition: border-color 0.15s;
}
.dark-card:hover { border-color: #2E7E56; }
.dark-card-name {
    font-family: 'Inter', sans-serif;
    font-size: 0.94rem;
    font-weight: 700;
    color: #ECFCF3;
    line-height: 1.3;
}
.dark-card-meta {
    font-family: 'Inter', sans-serif;
    font-size: 0.76rem;
    color: #4FB489;
    margin-top: 3px;
}
.dark-card-research {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    color: #8FE0B8;
    margin-top: 6px;
    line-height: 1.6;
}

/* ── Feed cards (home page) ──────────────────────────────── */
.feed-card {
    background: rgba(21,61,46,0.38);
    border: 1px solid #1B4B38;
    border-radius: 14px;
    padding: 1rem 1.2rem 0.9rem 1.2rem;
    margin-bottom: 0.8rem;
    transition: border-color 0.15s, background 0.15s;
}
.feed-card:hover {
    border-color: #2E7E56;
    background: rgba(21,61,46,0.55);
}
.feed-top {
    display: flex;
    align-items: center;
    gap: 11px;
}
.feed-who { flex: 1; min-width: 0; }
.feed-name {
    font-family: 'Inter', sans-serif;
    font-size: 0.92rem;
    font-weight: 700;
    color: #ECFCF3;
    line-height: 1.25;
}
.feed-meta {
    font-family: 'Inter', sans-serif;
    font-size: 0.74rem;
    color: #4FB489;
    margin-top: 2px;
}
.feed-time {
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    color: #3C9C6E;
    white-space: nowrap;
    align-self: flex-start;
    padding-top: 3px;
}
.feed-title {
    font-family: 'Inter', sans-serif;
    font-size: 0.96rem;
    font-weight: 600;
    color: #D9F7E6;
    margin-top: 0.7rem;
    line-height: 1.45;
}
.feed-body {
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    color: #8FE0B8;
    line-height: 1.65;
    margin-top: 0.35rem;
}
.feed-foot {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 0.65rem;
}
.type-pill {
    font-family: 'Inter', sans-serif;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #6ECDA0;
    background: rgba(60,156,110,0.14);
    border: 1px solid rgba(60,156,110,0.35);
    border-radius: 5px;
    padding: 2px 8px;
}
.match-pill {
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    font-weight: 600;
    color: #0D2E22;
    background: #8FE0B8;
    border-radius: 999px;
    padding: 2px 10px;
}

/* ── Tag chips ───────────────────────────────────────────── */
.tag-row { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 7px; }
.tag-chip, .tag-chip-dark {
    display: inline-block;
    background: rgba(60,156,110,0.16);
    border: 1px solid rgba(60,156,110,0.4);
    color: #8FE0B8 !important;
    font-family: 'Inter', sans-serif;
    font-size: 0.71rem;
    font-weight: 600;
    padding: 3px 11px;
    border-radius: 999px;
    white-space: nowrap;
}

/* ── Post cards ──────────────────────────────────────────── */
.post-card {
    background: rgba(21,61,46,0.38);
    border: 1px solid #1B4B38;
    border-radius: 12px;
    padding: 0.95rem 1.15rem;
    margin-bottom: 0.7rem;
}
.post-type-badge {
    display: inline-block;
    font-family: 'Inter', sans-serif;
    font-size: 0.66rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: #6ECDA0;
    background: rgba(60,156,110,0.14);
    border: 1px solid rgba(60,156,110,0.35);
    border-radius: 5px;
    padding: 2px 8px;
    margin-bottom: 0.5rem;
}
.post-title {
    font-family: 'Inter', sans-serif;
    font-size: 0.95rem;
    font-weight: 700;
    color: #ECFCF3;
    margin-bottom: 0.3rem;
    line-height: 1.4;
}
.post-content {
    font-family: 'Inter', sans-serif;
    font-size: 0.85rem;
    color: #8FE0B8;
    line-height: 1.65;
}
.post-date {
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    color: #3C9C6E;
    margin-top: 0.45rem;
}

/* ── Document rows ───────────────────────────────────────── */
.doc-row {
    display: flex;
    align-items: center;
    gap: 12px;
    background: rgba(21,61,46,0.38);
    border: 1px solid #1B4B38;
    border-radius: 12px;
    padding: 0.7rem 1rem;
    margin-bottom: 6px;
}
.doc-icon {
    width: 38px;
    height: 38px;
    border-radius: 9px;
    background: rgba(60,156,110,0.15);
    border: 1px solid rgba(60,156,110,0.35);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Inter', sans-serif;
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: #6ECDA0;
    text-transform: uppercase;
    flex-shrink: 0;
}

/* ── Post images ─────────────────────────────────────────── */
.post-img {
    display: block;
    max-width: 100%;
    max-height: 340px;
    border-radius: 10px;
    border: 1px solid #1B4B38;
    margin-top: 0.6rem;
    object-fit: cover;
}
.doc-name {
    font-family: 'Inter', sans-serif;
    font-size: 0.87rem;
    font-weight: 600;
    color: #ECFCF3;
    line-height: 1.3;
    word-break: break-all;
}
.doc-meta {
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    color: #4FB489;
    margin-top: 2px;
}

/* ── Profile hero ────────────────────────────────────────── */
.profile-hero {
    background: rgba(21,61,46,0.38);
    border: 1px solid #1B4B38;
    border-radius: 16px;
    padding: 1.6rem 1.8rem;
    margin-bottom: 1.4rem;
    display: flex;
    align-items: flex-start;
    gap: 18px;
    text-align: left;
}
.profile-hero-center {
    background: rgba(21,61,46,0.38);
    border: 1px solid #1B4B38;
    border-radius: 16px;
    padding: 2rem;
    margin-bottom: 1.4rem;
    text-align: center;
}
.profile-avatar-lg {
    width: 74px;
    height: 74px;
    border-radius: 50%;
    background: linear-gradient(135deg, #246142 0%, #4FB489 100%);
    color: #ECFCF3;
    font-family: 'Sora', sans-serif;
    font-size: 1.5rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    box-shadow: 0 0 0 3px rgba(60,156,110,0.25);
}
.profile-name {
    font-family: 'Sora', sans-serif;
    font-size: 1.45rem;
    font-weight: 700;
    color: #ECFCF3;
    margin-bottom: 0.2rem;
}
.profile-meta {
    font-family: 'Inter', sans-serif;
    font-size: 0.86rem;
    color: #6ECDA0;
    line-height: 1.55;
}

/* ── Auth card ───────────────────────────────────────────── */
.auth-panel {
    background: rgba(21,61,46,0.38);
    border: 1px solid #1B4B38;
    border-radius: 16px;
    padding: 1.8rem 2rem;
    max-width: 460px;
    margin: 0 auto;
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
[data-testid="stFileUploader"] label,
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
[data-testid="stFileUploader"] section {
    background-color: #092219 !important;
    border: 1.5px dashed #1B4B38 !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploader"] section * { color: #4FB489 !important; }
[data-testid="stFileUploader"] small { color: #3C9C6E !important; }

/* Buttons */
[data-testid="stButton"] > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button,
[data-testid="stDownloadButton"] > button {
    background: #2E7E56 !important;
    color: #ECFCF3 !important;
    border: none !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.5rem 1.1rem !important;
    transition: background 0.15s !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover,
[data-testid="stFormSubmitButton"] > button:hover,
[data-testid="stDownloadButton"] > button:hover {
    background: #3C9C6E !important;
}
[data-testid="stButton"] > button[kind="secondary"] {
    background: transparent !important;
    color: #6ECDA0 !important;
    border: 1.5px solid #246142 !important;
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover {
    background: rgba(36,97,66,0.22) !important;
    color: #8FE0B8 !important;
}
[data-testid="stButton"] > button {
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
    font-weight: 600 !important;
}

/* Tabs */
[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: transparent !important;
    gap: 2px !important;
    border-bottom: 1px solid #153D2E !important;
}
[data-testid="stTabs"] [data-baseweb="tab"] {
    color: #4FB489 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
    background: transparent !important;
    border-radius: 8px 8px 0 0 !important;
    padding: 0.5rem 1rem !important;
}
[data-testid="stTabs"] [aria-selected="true"] {
    color: #ECFCF3 !important;
    font-weight: 600 !important;
    border-bottom: 2px solid #3C9C6E !important;
}
[data-testid="stTabPanel"] { padding-top: 1.1rem !important; }

/* Radio */
[data-testid="stRadio"] > div { flex-direction: row !important; gap: 0.9rem !important; flex-wrap: wrap !important; }
[data-testid="stRadio"] label { color: #8FE0B8 !important; }

/* Alerts / spinner / caption */
[data-testid="stAlert"] {
    border-radius: 10px !important;
    font-family: 'Inter', sans-serif !important;
}
[data-testid="stSpinner"] p {
    font-family: 'Inter', sans-serif !important;
    color: #4FB489 !important;
    font-size: 0.88rem !important;
}
[data-testid="stCaptionContainer"] p {
    color: #3C9C6E !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.74rem !important;
}

/* ── Chat UI ─────────────────────────────────────────────── */
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
    background: #1B4B38 !important;
    color: #ECFCF3 !important;
    border-radius: 16px 16px 4px 16px !important;
    padding: 0.65rem 1.05rem !important;
    max-width: 82% !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
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
    line-height: 1.75 !important;
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
}
[data-testid="stChatInput"] textarea {
    background-color: #092219 !important;
    color: #C6EFDA !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.93rem !important;
}
[data-testid="stChatInput"] textarea::placeholder { color: #246142 !important; }
[data-testid="stChatInput"] button {
    background: #2E7E56 !important;
    border-radius: 10px !important;
}

/* ── Scrollbar / divider ─────────────────────────────────── */
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #153D2E; border-radius: 8px; }
::-webkit-scrollbar-thumb:hover { background: #246142; }

.thin-divider {
    border: none;
    border-top: 1px solid #153D2E;
    margin: 1.2rem 0;
}

@media (max-width: 700px) {
    .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
    .landing-title { font-size: 2rem; }
    .page-title { font-size: 1.4rem; }
    .profile-hero { flex-direction: column; }
}
</style>
"""


def get_initials(name: str) -> str:
    parts = name.strip().split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper() if name else "?"


def avatar_html(name: str, photo_b64=None, mime="image/jpeg",
                size=44, font_size="0.85rem") -> str:
    """Round avatar — photo if available, otherwise colored initials."""
    if photo_b64:
        return (f'<img class="avatar-img" src="data:{mime};base64,{photo_b64}" '
                f'style="width:{size}px;height:{size}px;" alt=""/>')
    return (f'<div class="avatar" style="width:{size}px;height:{size}px;'
            f'font-size:{font_size};">{get_initials(name)}</div>')


def time_ago(iso_str: str) -> str:
    """'2026-07-06 14:20:00' → '2d ago' (SQLite datetime('now') is UTC)."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("T", " ")[:19])
        delta = datetime.now(timezone.utc).replace(tzinfo=None) - dt
        s = int(delta.total_seconds())
        if s < 3600:        return f"{max(s // 60, 1)}m ago"
        if s < 86400:       return f"{s // 3600}h ago"
        if s < 86400 * 30:  return f"{s // 86400}d ago"
        return iso_str[:10]
    except (ValueError, AttributeError):
        return (iso_str or "")[:10]


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


def page_header(title: str, subtitle: str = "", kicker: str = ""):
    st.markdown(
        f'<div class="page-hero">'
        + (f'<div class="page-kicker">{kicker}</div>' if kicker else "")
        + f'<div class="page-title">{title}</div>'
        + (f'<div class="page-subtitle">{subtitle}</div>' if subtitle else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def section_label(text: str):
    st.markdown(f'<div class="section-label">{text}</div>', unsafe_allow_html=True)


def divider():
    st.markdown('<hr class="thin-divider"/>', unsafe_allow_html=True)
