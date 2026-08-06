import streamlit as st

st.set_page_config(
    page_title="Day 10 — Data Pipeline & Observability Lab",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Day 10 — Data Pipeline & Observability Lab")
st.markdown(
    """
    RAG pipeline demo: Crossref ingestion → cleaning → embedding → retrieval,
    with data quality checks, corruption simulation, and repair verification.

    **Navigate using the sidebar** to explore each stage of the pipeline.
    """
)

st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("1️⃣ Baseline")
    st.write("Clean data pipeline with quality gates and retrieval evaluation.")
with col2:
    st.subheader("2️⃣ Corruption")
    st.write("6 controlled corruption scenarios injected into the clean dataset.")
with col3:
    st.subheader("3️⃣ Repair")
    st.write("Recovery from raw snapshot, verified against baseline lineage.")

st.info("👈 Use the page navigation in the sidebar to explore Overview, Baseline, Corruption, Repair, and the Comparison Dashboard.")
