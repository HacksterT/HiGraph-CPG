"""Evidence chain display components."""

import os

import streamlit as st

from utils.api_client import get_evidence_chain, get_studies_for_recommendation

API_URL = os.getenv("API_URL", "http://localhost:8100")


def get_quality_color(quality: str) -> str:
    """Get color for quality rating badge."""
    quality_lower = (quality or "").lower()
    if "high" in quality_lower:
        return "green"
    elif "moderate" in quality_lower:
        return "orange"
    elif "low" in quality_lower or "very low" in quality_lower:
        return "red"
    return "gray"


def render_quality_badge(quality: str):
    """Render a quality rating badge."""
    if not quality:
        st.caption("Quality: Not rated")
        return

    quality_lower = quality.lower()
    if "high" in quality_lower:
        st.success(f"⬆️ {quality}")
    elif "moderate" in quality_lower:
        st.warning(f"➡️ {quality}")
    elif "low" in quality_lower:
        st.error(f"⬇️ {quality}")
    else:
        st.info(quality)


def render_evidence_chain(rec_id: str, rec_text: str):
    """
    Render the full evidence chain for a recommendation.

    Shows: Key Question → Evidence Body → Studies
    """
    st.subheader(f"Evidence Chain for {rec_id}")

    # Show recommendation text
    with st.container():
        st.markdown("**Recommendation:**")
        st.markdown(f"> {rec_text[:500]}{'...' if len(rec_text) > 500 else ''}")

    st.divider()

    # Fetch evidence chain
    with st.spinner("Loading evidence chain..."):
        result = get_evidence_chain(API_URL, rec_id)

    if result.get("error"):
        st.error(f"Could not load evidence: {result['error']}")
        return

    data = result.get("data", {})

    # Key Question section
    key_question = data.get("key_question", {})
    if key_question:
        st.markdown("### 🔬 Key Question")
        kq_id = key_question.get("kq_id", "Unknown")
        kq_num = key_question.get("kq_number", "")
        kq_text = key_question.get("question_text", "No question text")

        st.markdown(f"**{kq_id}** (Question {kq_num})")
        st.info(kq_text)

    st.divider()

    # Evidence Body section
    evidence = data.get("evidence", {})
    if evidence:
        st.markdown("### 📊 Evidence Body")

        col1, col2 = st.columns([1, 3])
        with col1:
            quality = evidence.get("quality_rating", "Not rated")
            render_quality_badge(quality)

            num_studies = evidence.get("num_studies", 0)
            st.metric("Studies", num_studies)

        with col2:
            findings = evidence.get("key_findings", "No key findings recorded")
            st.markdown("**Key Findings:**")
            st.markdown(findings)

    st.divider()

    # Studies section
    studies = data.get("studies", [])
    # Filter out None values
    studies = [s for s in studies if s is not None]

    st.markdown(f"### 📚 Supporting Studies ({len(studies)})")

    if not studies:
        st.caption("No studies linked to this evidence body.")
        return

    # Fetch full study details (with abstracts)
    with st.spinner("Loading study details..."):
        studies_result = get_studies_for_recommendation(API_URL, rec_id)

    if studies_result.get("error"):
        # Fall back to basic study list
        full_studies = studies
    else:
        full_studies = studies_result.get("studies", studies)

    for i, study in enumerate(full_studies):
        if study is None:
            continue

        pmid = study.get("pmid")
        title = study.get("title", "Untitled")
        journal = study.get("journal", "")
        year = study.get("year", "")
        study_type = study.get("study_type", "")
        authors = study.get("authors", "")
        abstract = study.get("abstract", "")

        # Study header with PubMed link
        if pmid:
            pubmed_url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}"
            st.markdown(f"**{i+1}. [{title}]({pubmed_url})**")
        else:
            st.markdown(f"**{i+1}. {title}**")

        # Metadata row
        meta_parts = []
        if journal:
            meta_parts.append(f"📰 {journal}")
        if year:
            meta_parts.append(f"📅 {year}")
        if study_type:
            meta_parts.append(f"📋 {study_type}")
        if pmid:
            meta_parts.append(f"PMID: {pmid}")

        if meta_parts:
            st.caption(" · ".join(meta_parts))

        # Authors (truncated)
        if authors:
            if len(authors) > 100:
                st.caption(f"👥 {authors[:100]}...")
            else:
                st.caption(f"👥 {authors}")

        # Abstract in expander
        if abstract:
            with st.expander("View Abstract", expanded=False):
                st.markdown(abstract)

        if i < len(full_studies) - 1:
            st.markdown("---")


def render_evidence_button(rec_id: str, rec_text: str):
    """
    Render a "View Evidence" button that shows evidence chain in a dialog.

    Args:
        rec_id: Recommendation ID
        rec_text: Recommendation text (for context)
    """
    button_key = f"evidence_btn_{rec_id}"

    if st.button("🔍 View Evidence", key=button_key, use_container_width=True):
        st.session_state[f"show_evidence_{rec_id}"] = True
        st.rerun()


def render_evidence_modal(rec_id: str, rec_text: str):
    """
    Render evidence chain in a modal/dialog style container.
    """
    state_key = f"show_evidence_{rec_id}"

    if st.session_state.get(state_key, False):
        with st.container():
            col1, col2 = st.columns([6, 1])
            with col2:
                if st.button("✕ Close", key=f"close_{rec_id}"):
                    st.session_state[state_key] = False
                    st.rerun()

            render_evidence_chain(rec_id, rec_text)
