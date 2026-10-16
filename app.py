import streamlit as st
import requests
import os
import time
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key={API_KEY}"

HANDBOOK_PATH = "handbook/handbook.md"

@st.cache_data
def load_handbook():
    with open(HANDBOOK_PATH, "r", encoding="utf-8") as f:
        return f.read()

HANDBOOK = load_handbook()

SYSTEM_PROMPT = """You are an HR policy assistant for MediCore Bangladesh Ltd.
Your ONLY knowledge source is the HR Employee Handbook provided below.

RULES:
1. Answer ONLY from the handbook. Do not use outside knowledge.
2. Always cite the section number (e.g. "Section 3.2").
3. If the question cannot be answered from the handbook, say clearly:
   "This is outside the scope of the MediCore HR handbook. Please contact HR directly."
4. Reply in the same language as the question:
   - English question → English answer
   - Bangla question → Bangla answer
5. Be concise but complete. Always state the actual answer, not just the section number.

HANDBOOK:
{handbook}
"""

def ask_gemini(question: str, handbook: str, retries: int = 3) -> str:
    prompt = SYSTEM_PROMPT.format(handbook=handbook) + f"\n\nQuestion: {question}"
    body = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "maxOutputTokens": 512,
            "temperature": 0.1
        }
    }
    for attempt in range(retries):
        try:
            r = requests.post(API_URL, json=body, timeout=60)
            if r.status_code == 503:
                wait = 10 * (attempt + 1)
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return "No response received. Please try again."
            parts = candidates[0].get("content", {}).get("parts", [])
            if not parts:
                return "Empty response. Please try again."
            return parts[0].get("text", "No text in response.")
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(5)
                continue
            return "Request timed out. Please try again."
        except Exception as e:
            return f"Error: {e}"
    return "Service temporarily unavailable. Please wait a minute and try again."

# --- UI ---
st.set_page_config(page_title="MediCore HR Assistant", page_icon="💊")
st.title("💊 MediCore HR Policy Assistant")
st.caption("Ask any question about MediCore Bangladesh Ltd. HR policies — in English or Bangla.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question := st.chat_input("Ask a policy question..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Looking up policy..."):
            answer = ask_gemini(question, HANDBOOK)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})