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
):
    """
    Render an assistant message with citations and reasoning.

    Args:
        content: The answer text (markdown supported)
        citations: List of citation dicts with rec_id, rec_text, strength, direction
        reasoning: Reasoning metadata dict
    """
    with st.chat_message("assistant"):
        # Main answer
        st.markdown(content)

        # Citations section
        if citations:
            render_citations(citations)

        # Reasoning/metadata (collapsed by default)
        if reasoning:
            with st.expander("🔍 Query Details", expanded=False):
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
