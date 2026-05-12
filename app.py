"""Powerbot — Streamlit chat app for sample-size planning conversations."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import streamlit as st
from supabase import create_client

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096
SYSTEM_PROMPT_PATH = Path(__file__).parent / "system_prompt.md"
CONVERSATIONS_DIR = Path(__file__).parent / "conversations"

TOOLS = [{"type": "web_search_20260209", "name": "web_search"}]

st.set_page_config(page_title="Powerbot", page_icon="📊")


def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.title("Powerbot")
    st.caption("Your sample size therapist")
    with st.form("login"):
        pw = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter")
    if submitted:
        if pw == st.secrets.get("APP_PASSWORD"):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    return False


if not check_password():
    st.stop()


@st.cache_resource
def get_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def load_messages(session_id: str) -> list:
    try:
        resp = (
            get_supabase().table("conversations")
            .select("role,content")
            .eq("session_id", session_id)
            .order("timestamp")
            .execute()
        )
    except Exception:
        return []
    messages = []
    for row in resp.data:
        content = row["content"]
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, ValueError, TypeError):
            pass
        messages.append({"role": row["role"], "content": content})
    return messages


def init_session() -> None:
    if "session_id" not in st.session_state:
        url_session = st.query_params.get("session")
        if url_session:
            st.session_state.session_id = url_session
            st.session_state.messages = load_messages(url_session)
        else:
            st.session_state.session_id = (
                datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                + "-"
                + uuid.uuid4().hex[:6]
            )
            st.session_state.messages = []
            st.query_params["session"] = st.session_state.session_id
    if "log_path" not in st.session_state:
        CONVERSATIONS_DIR.mkdir(exist_ok=True)
        st.session_state.log_path = (
            CONVERSATIONS_DIR / f"{st.session_state.session_id}.jsonl"
        )


def log_event(role: str, content) -> None:
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "role": role,
        "content": content,
    }
    with st.session_state.log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    try:
        content_str = content if isinstance(content, str) else json.dumps(content)
        get_supabase().table("conversations").insert({
            "session_id": st.session_state.session_id,
            "timestamp": entry["timestamp"],
            "role": role,
            "content": content_str,
        }).execute()
    except Exception:
        pass


def block_field(block, name: str):
    return block.get(name) if isinstance(block, dict) else getattr(block, name, None)


def render_assistant_blocks(content) -> None:
    for block in content:
        btype = block_field(block, "type")
        if btype == "text":
            st.markdown(block_field(block, "text") or "")
        elif btype == "server_tool_use" and block_field(block, "name") == "web_search":
            inp = block_field(block, "input") or {}
            query = inp.get("query", "") if isinstance(inp, dict) else ""
            if query:
                st.caption(f"🔎 Searched the web: *{query}*")


def format_transcript() -> str:
    lines = []
    for msg in st.session_state.get("messages", []):
        role = msg["role"].upper()
        content = msg["content"]
        if isinstance(content, str):
            text = content
        else:
            text = "\n".join(
                b.get("text", "") for b in content if b.get("type") == "text"
            )
        lines.append(f"{role}:\n{text}")
    return "\n\n---\n\n".join(lines)


init_session()
system_prompt_text = SYSTEM_PROMPT_PATH.read_text()
client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

with st.sidebar:
    st.markdown("**Session**")
    st.code(st.session_state.session_id, language=None)
    st.caption("Bookmark this page to resume this conversation later.")
    if st.session_state.get("messages"):
        st.download_button(
            "⬇ Download transcript",
            data=format_transcript(),
            file_name=f"powerbot-{st.session_state.session_id}.txt",
            mime="text/plain",
        )
    if st.button("Start new conversation"):
        for key in ("messages", "session_id", "log_path"):
            st.session_state.pop(key, None)
        st.query_params.clear()
        st.rerun()

st.title("Powerbot")
st.caption("Your sample size therapist — a thinking partner for power analysis")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], str):
            st.markdown(msg["content"])
        else:
            render_assistant_blocks(msg["content"])

if prompt := st.chat_input("Tell me about the study you're planning..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    log_event("user", prompt)

    with st.chat_message("user"):
        st.markdown(prompt)

    _BLOCK_KEYS = {"type", "text", "id", "name", "input"}

    def _sanitize(content):
        if isinstance(content, list):
            return [{k: v for k, v in b.items() if k in _BLOCK_KEYS} for b in content]
        return content

    api_messages = [
        {"role": m["role"], "content": _sanitize(m["content"])}
        for m in st.session_state.messages
    ]

    with st.chat_message("assistant"):
        placeholder = st.empty()
        streamed_text = ""
        try:
            with client.messages.stream(
                model=MODEL,
                max_tokens=MAX_TOKENS,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt_text,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                tools=TOOLS,
                messages=api_messages,
            ) as stream:
                for text in stream.text_stream:
                    streamed_text += text
                    placeholder.markdown(streamed_text + "▌")
                placeholder.markdown(streamed_text or "_(no response)_")
                final = stream.get_final_message()

            for block in final.content:
                if (
                    getattr(block, "type", None) == "server_tool_use"
                    and getattr(block, "name", None) == "web_search"
                ):
                    inp = getattr(block, "input", {}) or {}
                    query = inp.get("query", "") if isinstance(inp, dict) else ""
                    if query:
                        st.caption(f"🔎 Searched the web: *{query}*")

            full_content = [block.model_dump() for block in final.content]
            st.session_state.messages.append(
                {"role": "assistant", "content": full_content}
            )
            log_event("assistant", full_content)

        except anthropic.APIError as e:
            st.error(f"API error: {e}")
            st.session_state.messages.pop()
