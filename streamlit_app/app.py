"""HiGraph-CPG Clinical Guideline Chat Interface."""

import os

import streamlit as st
from components.chat import render_chat_message, render_user_message
from components.evidence import render_evidence_chain
from utils.api_client import check_api_health, get_answer

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8100")

# Page config
st.set_page_config(
    page_title="HiGraph-CPG | Clinical Guideline Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        max-width: 1200px;
        margin: 0 auto;
    }
    .chat-message {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    .user-message {
        background-color: #e3f2fd;
        border-left: 4px solid #1976d2;
    }
    .assistant-message {
        background-color: #f5f5f5;
        border-left: 4px solid #43a047;
    }
    .citation-box {
        background-color: #fff3e0;
        border: 1px solid #ff9800;
        border-radius: 0.25rem;
        padding: 0.75rem;
        margin-top: 0.5rem;
        font-size: 0.9rem;
    }
    .strength-strong {
        color: #2e7d32;
        font-weight: bold;
    }
    .strength-weak {
        color: #f57c00;
    }
    .header-container {
        padding: 1rem 0;
        border-bottom: 2px solid #1976d2;
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_healthy" not in st.session_state:
    st.session_state.api_healthy = None

if "current_evidence_rec" not in st.session_state:
    st.session_state.current_evidence_rec = None

if "show_debug" not in st.session_state:
    st.session_state.show_debug = False


def build_conversation_history(messages: list[dict], max_turns: int = 10) -> list[dict]:
    """
    Build conversation history for API request.

    Args:
        messages: List of message dicts from session state
        max_turns: Maximum number of turns to include (default 10 = 5 exchanges)

    Returns:
        List of conversation turns for API
    """
    # Convert to API format and limit to recent turns
    history = []
    for msg in messages[-max_turns:]:
        history.append({
            "role": msg["role"],
            "content": msg["content"],
        })
    return history


def main():
    """Main application entry point."""
    # Header
    st.markdown('<div class="header-container">', unsafe_allow_html=True)
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("VA/DoD Diabetes Clinical Guideline Assistant")
        st.caption("Powered by HiGraph-CPG Knowledge Graph")
    with col2:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Check API health on first load
    if st.session_state.api_healthy is None:
        with st.spinner("Connecting to knowledge base..."):
            st.session_state.api_healthy = check_api_health(API_URL)

    if not st.session_state.api_healthy:
        st.error("⚠️ Unable to connect to the API. Please ensure the service is running.")
        st.info(f"API URL: {API_URL}")
        if st.button("Retry Connection"):
            st.session_state.api_healthy = check_api_health(API_URL)
            st.rerun()
        return

    # Check if we should show evidence chain
    if st.session_state.current_evidence_rec:
        rec_data = st.session_state.current_evidence_rec
        with st.container():
            col1, col2 = st.columns([6, 1])
            with col2:
                if st.button("← Back to Chat", use_container_width=True):
                    st.session_state.current_evidence_rec = None
                    st.rerun()

            render_evidence_chain(rec_data["rec_id"], rec_data["rec_text"])
        return  # Don't show chat when viewing evidence

    # Display chat history
    for message in st.session_state.messages:
        if message["role"] == "user":
            render_user_message(message["content"])
        else:
            render_chat_message(
                message["content"],
                message.get("citations", []),
                message.get("reasoning", {}),
            )

    # Chat input
    if prompt := st.chat_input("Ask about diabetes clinical guidelines..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        render_user_message(prompt)

        # Build conversation history from previous messages (excluding current question)
        conversation_history = build_conversation_history(
            st.session_state.messages[:-1]  # Exclude the message we just added
        )

        # Get response with conversation context
        with st.spinner("Searching knowledge base and generating answer..."):
            response = get_answer(
                API_URL,
                prompt,
                conversation_history=conversation_history if conversation_history else None,
            )

        if response.get("error"):
            error_msg = f"Error: {response['error']}"
            st.session_state.messages.append({
                "role": "assistant",
                "content": error_msg,
                "citations": [],
                "reasoning": {},
            })
            st.error(error_msg)
        else:
            # Add assistant message
            st.session_state.messages.append({
                "role": "assistant",
                "content": response.get("answer", "No response generated."),
                "citations": response.get("citations", []),
                "reasoning": response.get("reasoning", {}),
            })
            render_chat_message(
                response.get("answer", ""),
                response.get("citations", []),
                response.get("reasoning", {}),
            )

        st.rerun()

    # Sidebar with info
    with st.sidebar:
        st.header("About")
        st.markdown("""
        This assistant helps you navigate the **VA/DoD Type 2 Diabetes
        Clinical Practice Guideline** (2023).

        **What you can ask:**
        - Treatment recommendations
        - Medication guidance
        - Evidence for specific therapies
        - Guidelines for comorbidities (CKD, CVD)

        **Data source:**
        - 26 clinical recommendations
        - 154 supporting studies
        - GRADE evidence ratings
        """)

        st.divider()

        st.header("Tips")
        st.markdown("""
        - Be specific about patient characteristics
        - Ask about drug classes (SGLT2, GLP-1, etc.)
        - Request evidence for recommendations
        - Ask follow-up questions like "tell me more" or "what about side effects?"
        """)

        st.divider()

        st.header("Settings")
        st.session_state.show_debug = st.toggle(
            "Show debug info",
            value=st.session_state.show_debug,
            help="Display context usage and timing information"
        )

        # Show conversation stats if debug is on
        if st.session_state.show_debug and st.session_state.messages:
            st.divider()
            st.subheader("Conversation Stats")
            num_exchanges = len([m for m in st.session_state.messages if m["role"] == "user"])
            st.metric("Exchanges", num_exchanges)

            # Show last response's context usage if available
            last_assistant = next(
                (m for m in reversed(st.session_state.messages) if m["role"] == "assistant"),
                None
            )
            if last_assistant and last_assistant.get("reasoning"):
                reasoning = last_assistant["reasoning"]
                context_usage = reasoning.get("context_usage", {})
                if context_usage:
                    st.caption("Last response context:")
                    st.text(f"History turns used: {context_usage.get('history_turns_used', 0)}")
                    st.text(f"Summarized: {context_usage.get('history_summarized', False)}")
                    st.text(f"Est. tokens: {context_usage.get('estimated_context_tokens', 0)}")


if __name__ == "__main__":
    main()
