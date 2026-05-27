# frontend/app.py
import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="SUST Faculty Finder", page_icon="🎓", layout="centered")
st.title("🎓 SUST Faculty Finder")
st.caption("Find the right supervisor for your research topic.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

query = st.chat_input("Ask e.g. 'Find a PhD supervisor for machine learning and NLP'")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Searching faculty profiles..."):
            try:
                resp = requests.post(f"{BACKEND_URL}/ask", json={"query": query}, timeout=120)
                answer = resp.json().get("answer", "No answer returned.")
            except Exception as e:
                answer = f"Error connecting to backend: {e}"
        st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})