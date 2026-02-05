"""Citation display components."""

import streamlit as st

from components.evidence import render_evidence_chain


def render_citations(citations: list[dict], show_evidence_buttons: bool = True):
    """
    Render citations as expandable sections.

    Args:
        citations: List of citation dicts with rec_id, rec_text, strength, direction, topic
    """
    if not citations:
        return

    with st.expander(f"📚 Citations ({len(citations)} recommendations)", expanded=False):
        for i, citation in enumerate(citations):
            rec_id = citation.get("rec_id", f"Unknown-{i}")
            rec_text = citation.get("rec_text", "No text available")
            strength = citation.get("strength", "N/A")
            direction = citation.get("direction", "N/A")
            topic = citation.get("topic")

            st.markdown(f"**{rec_id}**")

            # Strength and direction badges
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if strength == "Strong":
                    st.success(f"⬆️ {strength}")
                else:
                    st.warning(f"↔️ {strength}")
            with col2:
                if direction == "For":
                    st.info(f"✓ {direction}")
                elif direction == "Against":
                    st.error(f"✗ {direction}")
                else:
                    st.caption(direction)
            with col3:
                if topic:
                    st.caption(f"📁 {topic}")

            # Recommendation text
            st.markdown(f"> {rec_text}")

            # View Evidence button
            if show_evidence_buttons:
                evidence_key = f"show_evidence_{rec_id}"
                if st.button(
                    "🔍 View Evidence Chain",
                    key=f"evidence_btn_{rec_id}_{i}",
                    use_container_width=False,
                ):
                    st.session_state[evidence_key] = True
                    st.session_state["current_evidence_rec"] = {
                        "rec_id": rec_id,
                        "rec_text": rec_text,
                    }

            if i < len(citations) - 1:
                st.divider()


def render_study_citations(studies: list[dict]):
    """
    Render study citations with PubMed links.

    Args:
        studies: List of study dicts with pmid, title, journal, year
    """
    if not studies:
        return

    with st.expander(f"📖 Supporting Studies ({len(studies)})", expanded=False):
        for study in studies:
            pmid = study.get("pmid")
            title = study.get("title", "Untitled")
            journal = study.get("journal", "")
            year = study.get("year", "")

            # Title with PubMed link if PMID available
            if pmid:
                pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"
                st.markdown(f"**[{title}]({pubmed_url})**")
            else:
                st.markdown(f"**{title}**")

            # Journal and year
            meta_parts = []
            if journal:
                meta_parts.append(journal)
            if year:
                meta_parts.append(str(year))
            if pmid:
                meta_parts.append(f"PMID: {pmid}")

            if meta_parts:
                st.caption(" · ".join(meta_parts))
