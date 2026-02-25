"""Chat message components."""

import streamlit as st

from components.citations import render_citations


def render_user_message(content: str):
    """Render a user message in the chat."""
    with st.chat_message("user"):
        st.markdown(content)


def render_chat_message(
    content: str,
    citations: list[dict],
    reasoning: dict,
    message_index: int = 0,
):
    """
    Render an assistant message with citations and reasoning.

    Args:
        content: The answer text (markdown supported)
        citations: List of citation dicts with rec_id, rec_text, strength, direction
        reasoning: Reasoning metadata dict
        message_index: Index of this message in the chat history (used to make widget keys unique)
    """
    with st.chat_message("assistant"):
        # Main answer
        st.markdown(content)

        # Citations section
        if citations:
            render_citations(citations, message_index=message_index)

        # Reasoning/metadata (collapsed by default, or expanded if debug mode)
        if reasoning:
            show_debug = st.session_state.get("show_debug", False)
            with st.expander("🔍 Query Details", expanded=show_debug):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric(
                        "Routing",
                        reasoning.get("query_routing", "N/A"),
                    )

                with col2:
                    st.metric(
                        "Results Used",
                        reasoning.get("results_used", 0),
                    )

                with col3:
                    total_time = reasoning.get("total_time_ms", 0)
                    st.metric(
                        "Response Time",
                        f"{total_time}ms",
                    )

                # Token usage
                tokens = reasoning.get("tokens_used", {})
                if tokens:
                    st.caption(
                        f"Tokens: {tokens.get('prompt', 0)} prompt + "
                        f"{tokens.get('completion', 0)} completion"
                    )

                # Context usage (conversation history)
                context_usage = reasoning.get("context_usage", {})
                if context_usage and context_usage.get("history_turns_received", 0) > 0:
                    st.divider()
                    st.caption("**Conversation Context**")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text(f"History turns: {context_usage.get('history_turns_used', 0)}/{context_usage.get('history_turns_received', 0)}")
                    with col2:
                        st.text(f"Context tokens: ~{context_usage.get('estimated_context_tokens', 0)}")
                    if context_usage.get("history_summarized"):
                        st.info("Older conversation was summarized to fit context window")
