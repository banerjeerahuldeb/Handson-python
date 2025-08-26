# ask_ai.py
import streamlit as st
from typing import List, Tuple, Optional

st.set_page_config(page_title="Ask AI", page_icon="🤖", layout="wide")

# --------------------------------------------------------------------------------------
# ⛳ Replace this with your actual RAG/chat function
# It must return: (reply_text: str, citations: Optional[List[str]])
def answer_with_rag(user_text: str) -> Tuple[str, Optional[List[str]]]:
    # TODO: Hook up to your backend. This is only a placeholder.
    demo_reply = f"You said: {user_text}\n\n(Replace answer_with_rag() with your real function.)"
    return demo_reply, None
# --------------------------------------------------------------------------------------

# Initialize session state
if "messages" not in st.session_state:
    # Each message: {"id": int, "role": "user"|"assistant", "content": str, "citations": Optional[List[str]]}
    st.session_state.messages = [
        {"id": 0, "role": "assistant", "content": "Hello! Ask me anything about your documents.", "citations": None}
    ]

if "feedback" not in st.session_state:
    # Map message_id -> "up" | "down"
    st.session_state.feedback = {}

# Utility to generate next message id
def next_msg_id() -> int:
    if not st.session_state.messages:
        return 0
    return max(m.get("id", -1) for m in st.session_state.messages) + 1

# ==============================  STYLE  ==============================================
st.markdown(
    """
    <style>
    /* Optional: tighten default spacing a bit */
    [data-testid="stChatMessage"] { padding: 0.2rem 0; }

    /* Shared bubble look */
    .bubble {
        display: block;               /* enables auto margins */
        max-width: 75%;
        padding: 10px 14px;
        border-radius: 16px;
        line-height: 1.4;
        word-wrap: break-word;
        box-shadow: 0 1px 2px rgba(0,0,0,.06);
        font-size: 16px;
        white-space: pre-wrap;        /* keep newlines */
    }

    /* Assistant (left) */
    .bubble.assistant {
        background: #E8EAF6;          /* light indigo-ish */
        color: #111;
        margin-right: auto;           /* left align */
        border-top-left-radius: 6px;  /* “speechy” corner */
    }

    /* User / self (right) */
    .bubble.user {
        background: #DCF8C6;          /* WhatsApp-like green */
        color: #111;
        margin-left: auto;            /* right align */
        border-top-right-radius: 6px;
        text-align: left;             /* keep text left inside bubble */
    }

    /* Small muted line for metadata (e.g., citations) */
    .bubble .meta {
        margin-top: 6px;
        font-size: 12px;
        opacity: .75;
    }

    /* Feedback row beneath assistant bubbles */
    .feedback-row {
        display: flex;
        gap: 8px;
        align-items: center;
        margin: 6px 4px 0 4px;
        font-size: 18px;
    }

    .feedback-pill {
        padding: 2px 10px;
        border-radius: 12px;
        background: #f4f4f4;
        font-size: 12px;
        opacity: .8;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🤖 Ask AI")

# =========================  RENDER HISTORY  ==========================================
def render_message(msg: dict):
    """Render a single message with bubble + optional feedback controls."""
    role = msg.get("role", "assistant")
    content = msg.get("content", "")
    citations = msg.get("citations")
    msg_id = msg.get("id")

    with st.chat_message(role, avatar=("🤖" if role == "assistant" else "🧑")):
        # Main bubble
        meta_html = ""
        if citations:
            meta_html = f'<div class="meta">Sources: {", ".join(citations)}</div>'
        st.markdown(
            f'<div class="bubble {role}">{content}{meta_html}</div>',
            unsafe_allow_html=True
        )

        # Feedback UI only for assistant messages
        if role == "assistant":
            existing = st.session_state.feedback.get(msg_id)
            if existing:
                # Show what the user chose; no buttons
                icon = "👍" if existing == "up" else "👎"
                st.markdown(
                    f'<div class="feedback-row"><div class="feedback-pill">Feedback recorded {icon}</div></div>',
                    unsafe_allow_html=True
                )
            else:
                # Buttons appear only if we don't have feedback yet
                c1, c2 = st.columns([1,1])
                with c1:
                    up = st.button("👍", key=f"fb_up_{msg_id}", help="This answer was helpful")
                with c2:
                    down = st.button("👎", key=f"fb_down_{msg_id}", help="This answer was not helpful")

                if up:
                    st.session_state.feedback[msg_id] = "up"
                    st.toast("Thanks for your feedback! 👍")
                    st.rerun()
                if down:
                    st.session_state.feedback[msg_id] = "down"
                    st.toast("Thanks for your feedback! 👎")
                    st.rerun()

# Render entire history (past chats automatically won’t show buttons if feedback exists)
for m in st.session_state.messages:
    # Backfill id if missing (for older saves)
    if "id" not in m:
        m["id"] = next_msg_id()
    render_message(m)

# =========================  INPUT / RESPONSE  ========================================
user_text = st.chat_input("Type your message…")

if user_text:
    # Add & render user message (right-aligned bubble)
    user_id = next_msg_id()
    user_msg = {"id": user_id, "role": "user", "content": user_text, "citations": None}
    st.session_state.messages.append(user_msg)

    with st.chat_message("user", avatar="🧑"):
        st.markdown(f'<div class="bubble user">{user_text}</div>', unsafe_allow_html=True)

    # Get assistant reply
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking…"):
            reply_text, citations = answer_with_rag(user_text)

        # Store assistant message with its own id
        asst_id = next_msg_id()
        asst_msg = {"id": asst_id, "role": "assistant", "content": reply_text, "citations": citations}
        st.session_state.messages.append(asst_msg)

        # Render assistant bubble
        meta_html = f'<div class="meta">Sources: {", ".join(citations)}</div>' if citations else ""
        st.markdown(f'<div class="bubble assistant">{reply_text}{meta_html}</div>', unsafe_allow_html=True)

        # Render feedback buttons (visible only once until clicked)
        c1, c2 = st.columns([1,1])
        with c1:
            up_new = st.button("👍", key=f"fb_up_{asst_id}", help="This answer was helpful")
        with c2:
            down_new = st.button("👎", key=f"fb_down_{asst_id}", help="This answer was not helpful")

        if up_new:
            st.session_state.feedback[asst_id] = "up"
            st.toast("Thanks for your feedback! 👍")
            st.rerun()
        if down_new:
            st.session_state.feedback[asst_id] = "down"
            st.toast("Thanks for your feedback! 👎")
            st.rerun()

# =============================  AUTO-SCROLL  =========================================
st.markdown(
    """
    <script>
    const msgs = window.parent.document.querySelectorAll('[data-testid="stChatMessage"]');
    if (msgs && msgs.length) {
        msgs[msgs.length - 1].scrollIntoView({ behavior: "smooth", block: "end" });
    }
    </script>
    """,
    unsafe_allow_html=True
)
