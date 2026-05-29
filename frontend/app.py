import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

st.set_page_config(
    page_title="Find Your Supervisor",
    page_icon="🎓",
    layout="centered",
    initial_sidebar_state="collapsed"
)

CUSTOM_CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=Inter:wght@300;400;500;600&display=swap');

* {
    box-sizing: border-box;
}

html,
body,
.stApp,
[data-testid="stApp"],
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
[data-testid="stMainBlockContainer"],
[data-testid="stVerticalBlock"],
.main,
.block-container {
    background-color: #2C3A1E !important;
    color: #E8E4D9 !important;
}

/* Allow sticky to work inside Streamlit's scroll container */
[data-testid="stAppViewContainer"] > section:first-child {
    overflow: visible !important;
}

.block-container {
    max-width: 760px !important;
    padding-top: 2rem !important;
    padding-bottom: 8rem !important;
}

#MainMenu,
header,
footer,
[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="baseButton-headerNoPadding"] {
    display: none !important;
}

.page-title {
    font-family: 'Sora', sans-serif;
    font-size: 2.4rem;
    font-weight: 800;
    color: #F0EAD2;
    text-align: center;
    letter-spacing: -0.6px;
    line-height: 1.08;
    margin-bottom: 0.3rem;
}

.page-subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 0.97rem;
    font-weight: 400;
    color: #B7C7AA;
    text-align: center;
    margin-bottom: 1.2rem;
}

.info-card {
    width: 100%;
    background-color: #F7F5F0;
    border: 1px solid #D8E0CC;
    border-radius: 12px;
    padding: 1rem 1.4rem 0.9rem 1.4rem;
    margin-bottom: 1rem;
}

.info-heading {
    font-family: 'Inter', sans-serif;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #6B8F52;
    text-align: center;
    margin-bottom: 0.7rem;
}

.info-card p {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 400 !important;
    color: #3A3A2E !important;
    margin: 0.45rem 0 !important;
    line-height: 1.65 !important;
}

.sticky-header {
    position: sticky;
    top: 0;
    z-index: 999;
    background-color: #2C3A1E;
    padding: 1rem 0 0.5rem 0;
    text-align: center;
}

.info-card strong {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 600 !important;
    color: #2C3A1E !important;
}

.info-card em {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 500 !important;
    color: #2C3A1E !important;
    font-style: italic !important;
}

.coming-soon-text {
    font-family: 'Inter', sans-serif !important;
    font-size: 0.875rem !important;
    font-weight: 400 !important;
    color: #7A9A62 !important;
}

.thin-divider {
    border: none;
    border-top: 1px solid #3D5229;
    margin: 0.8rem 0 1rem 0;
}

/* ─── Claude-like chat messages ─── */

[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
}

[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"],
[data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"],
[data-testid="stChatMessage"] .stChatMessageAvatarUser,
[data-testid="stChatMessage"] .stChatMessageAvatarAssistant,
[data-testid="stChatMessage"] > div:first-child {
    display: none !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    display: flex !important;
    flex-direction: column !important;
    align-items: flex-end !important;
    padding: 0.15rem 0 !important;
    gap: 0 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"] {
    background-color: #3D5229 !important;
    color: #F0EAD2 !important;
    border-radius: 18px 18px 4px 18px !important;
    padding: 0.6rem 1rem !important;
    max-width: 80% !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
    line-height: 1.6 !important;
    display: inline-block !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stMarkdownContainer"] p {
    color: #F0EAD2 !important;
    margin: 0 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.92rem !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) .stChatMessageActionBar,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) [data-testid="stChatMessageActionBar"] {
    justify-content: flex-end !important;
    margin-top: 2px !important;
    margin-right: 2px !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    display: block !important;
    padding: 0.2rem 0 0.8rem 0 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] {
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    max-width: 100% !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] p,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] li,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] span {
    font-family: 'Inter', sans-serif !important;
    color: #E8E4D9 !important;
    font-size: 0.93rem !important;
    line-height: 1.75 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] h1,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] h2,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] h3,
[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] h4 {
    font-family: 'Inter', sans-serif !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: #C8D8B0 !important;
    margin: 1rem 0 0.3rem 0 !important;
    line-height: 1.4 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] a {
    color: #A8D08D !important;
    text-decoration: underline !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] hr {
    border-color: #3D5229 !important;
    margin: 0.6rem 0 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) [data-testid="stMarkdownContainer"] strong {
    color: #D0DCB8 !important;
    font-weight: 600 !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]) {
    margin-top: 1.2rem !important;
}

[data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]) {
    margin-top: 0.4rem !important;
    padding-bottom: 1.2rem !important;
    border-bottom: 1px solid rgba(61, 82, 41, 0.3) !important;
}

[data-testid="stChatMessage"]:last-of-type:has([data-testid="chatAvatarIcon-assistant"]) {
    border-bottom: none !important;
}

/* ─── Input area ─── */

[data-testid="stChatFloatingInputContainer"],
[data-testid="stBottomBlockContainer"],
[data-testid="stBottomBlockContainer"] > div,
[data-testid="stBottomBlockContainer"] section,
[data-testid="stBottomBlockContainer"] form,
div:has([data-testid="stChatInput"]),
div:has([data-testid="stChatInput"]) > div {
    background-color: #2C3A1E !important;
    border: none !important;
    box-shadow: none !important;
}

[data-testid="stBottomBlockContainer"] {
    background-color: #2C3A1E !important;
    padding: 1rem 1rem 1.1rem 1rem !important;
}

[data-testid="stChatFloatingInputContainer"] {
    background-color: #2C3A1E !important;
    border-top: none !important;
    box-shadow: none !important;
}

[data-testid="stChatFloatingInputContainer"] > div,
[data-testid="stBottomBlockContainer"] > div {
    max-width: 760px !important;
    margin: 0 auto !important;
    background-color: #2C3A1E !important;
}

[data-testid="stChatInput"] {
    max-width: 760px !important;
    margin: 0 auto !important;
    background-color: #2C3A1E !important;
}

[data-testid="stChatInput"] > div,
[data-testid="stChatInputContainer"] {
    background-color: #2B2D38 !important;
    border: 1.5px solid #4A6434 !important;
    border-radius: 12px !important;
    box-shadow: none !important;
}

[data-testid="stChatInput"] textarea,
[data-testid="stChatInputContainer"] textarea {
    background-color: #2B2D38 !important;
    color: #E8E4D9 !important;
    font-family: 'Inter', sans-serif !important;
    font-size: 0.95rem !important;
}

[data-testid="stChatInput"] textarea::placeholder,
[data-testid="stChatInputContainer"] textarea::placeholder {
    color: #A9ABB8 !important;
}

[data-testid="stChatInput"] button,
[data-testid="stChatInputContainer"] button {
    background-color: #505263 !important;
    border-radius: 10px !important;
    color: #F0EAD2 !important;
}

[data-testid="stChatInput"] button:hover,
[data-testid="stChatInputContainer"] button:hover {
    background-color: #6B6E82 !important;
}

[data-testid="stSpinner"] p {
    font-family: 'Inter', sans-serif !important;
    color: #B7C7AA !important;
    font-size: 0.9rem !important;
}

::-webkit-scrollbar {
    width: 7px;
}

::-webkit-scrollbar-track {
    background: #2C3A1E;
}

::-webkit-scrollbar-thumb {
    background: #5C7744;
    border-radius: 8px;
}

@media screen and (max-width: 700px) {
    .block-container {
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        padding-top: 1.5rem !important;
    }

    .page-title {
        font-size: 2rem;
    }

    .page-subtitle {
        font-size: 0.9rem;
    }

    .info-card {
        padding: 0.9rem 1rem;
    }
}
</style>
"""

COPY_BUTTON_JS = """
<script>
(function injectCopyButtons() {
    function addCopyButtons() {
        const userMessages = document.querySelectorAll('[data-testid="stChatMessage"]');
        userMessages.forEach(function(msg) {
            const avatarIcon = msg.querySelector('[data-testid="chatAvatarIcon-user"]');
            if (!avatarIcon) return;
            if (msg.querySelector('.copy-btn-row')) return;

            const mdContainer = msg.querySelector('[data-testid="stMarkdownContainer"]');
            if (!mdContainer) return;

            const text = mdContainer.innerText || '';

            const row = document.createElement('div');
            row.className = 'copy-btn-row';
            row.style.cssText = 'display:flex;justify-content:flex-end;margin-top:4px;';

            const btn = document.createElement('button');
            btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2 2v1"></path></svg> Copy';
            btn.style.cssText = [
                'background:transparent',
                'border:none',
                'color:#8AA875',
                'font-family:Inter,sans-serif',
                'font-size:0.72rem',
                'cursor:pointer',
                'display:flex',
                'align-items:center',
                'gap:4px',
                'padding:2px 4px',
                'border-radius:5px',
                'transition:color 0.15s'
            ].join(';');

            btn.addEventListener('mouseenter', function() { btn.style.color = '#C8D8B0'; });
            btn.addEventListener('mouseleave', function() { btn.style.color = '#8AA875'; });

            btn.addEventListener('click', function() {
                navigator.clipboard.writeText(text).then(function() {
                    btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> Copied';
                    btn.style.color = '#A8D08D';
                    setTimeout(function() {
                        btn.innerHTML = '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2 2v1"></path></svg> Copy';
                        btn.style.color = '#8AA875';
                    }, 1500);
                });
            });

            row.appendChild(btn);
            msg.appendChild(row);
        });
    }

    const observer = new MutationObserver(function() { addCopyButtons(); });
    observer.observe(document.body, { childList: true, subtree: true });
    addCopyButtons();
})();
</script>
"""

INFO_CARD_HTML = """
<div class="info-card">
<div class="info-heading">Before you start</div>

<p>— <strong> Please keep it to one query at a time.</strong> Running on a free API with limited credits, multiple quick queries can drain it for everyone.</p>

<p>— Each question is answered independently. This system does not remember previous messages. Reloading or refreshing the page will clear all messages.</p>

<p>— Describe your interest in plain language, e.g. <em>"Find me a professor in deep learning for medical imaging"</em>.The system will find the most relevant faculty matches.</p>

<p>— <strong>Faculty database included: </strong>SUST. <span class="coming-soon-text">More universities coming soon.</span></p>

<p>— <strong>Prototype:</strong> This is an early stage build. It can make mistakes, miss relevant faculty, or respond slowly. Please bear with it.</p>
</div>

<hr class="thin-divider"/>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    '''<div class="sticky-header">
        <div class="page-title">Find Your Professor</div>
        <div class="page-subtitle">Describe your research interest — we\'ll match you with the right faculty</div>
    </div>''',
    unsafe_allow_html=True
)

st.markdown(INFO_CARD_HTML, unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

query = st.chat_input("e.g. Find a PhD supervisor for machine learning and NLP")

if query and query.strip():
    query = query.strip()

    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Searching faculty profiles..."):
            try:
                response = requests.post(
                    f"{BACKEND_URL}/ask",
                    json={"query": query},
                    timeout=120
                )

                response.raise_for_status()

                try:
                    data = response.json()
                    answer = data.get("answer") or "No answer returned."
                except ValueError:
                    answer = response.text.strip() or "No answer returned."

            except requests.exceptions.Timeout:
                answer = (
                    "⏳ **The server is taking too long to respond.**\n\n"
                    "This usually happens when the backend is waking up from sleep "
                    "(it's hosted on a free tier). Please wait a moment and try again — "
                    "a second attempt usually works.\n\n"
                    "*If the issue keeps happening, the server may be temporarily unavailable.*"
                )
            except requests.exceptions.RequestException as error:
                answer = f"Error connecting to backend: {error}"

        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

st.markdown(COPY_BUTTON_JS, unsafe_allow_html=True)
