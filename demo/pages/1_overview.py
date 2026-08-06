import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st
from loaders import get_data_paths

st.set_page_config(page_title="Overview", page_icon="🗺️", layout="wide")
st.title("🗺️ Pipeline Overview")

st.markdown(
    """
    ## Architecture

    ```
    Crossref API ──▶ Raw Snapshot ──▶ Clean Data ──▶ Embedding (MiniLM) ──▶ ChromaDB
                                                                                │
                                                                                ▼
                                                            Retrieval + Extraction Agent
                                                                                │
                                                                                ▼
                                                          Evaluation (hit_rate, F1, LLM judge)
    ```

    **Corruption & Repair loop:**

    ```
    Clean Data ──▶ [6 corruption scenarios] ──▶ Corrupted Data ──▶ Re-evaluate
         │                                                              │
         └────────────────── Raw Snapshot ──▶ Repair ──▶ Repaired Data ─┘
                                                                (re-evaluate, compare)
    ```
    """
)

st.divider()
st.subheader("📁 Artifact Inventory")

paths = get_data_paths()
cols = st.columns(3)
groups = {
    "Metrics": ["baseline_metrics", "corrupted_metrics", "repaired_metrics"],
    "Quality": ["baseline_quality", "corrupted_quality", "repaired_quality"],
    "Reports": ["phase1_report", "corruption_report"],
}
for i, (group_name, keys) in enumerate(groups.items()):
    with cols[i]:
        st.markdown(f"**{group_name}**")
        for key in keys:
            p = paths[key]
            status = "✅" if p.exists() else "❌"
            st.caption(f"{status} `{p}`")

st.divider()
st.subheader("⚙️ Configuration Summary")
st.markdown(
    """
    - **Source**: Crossref API (works-based search)
    - **Embedding model**: `sentence-transformers/all-MiniLM-L6-v2`
    - **Vector store**: ChromaDB (local, persistent)
    - **LLM (judge/agent)**: Ollama `llama3.1` (local, no API key)
    - **Freshness threshold**: 180 days
    - **Test set**: 8 frozen questions (4 types: summary, authors, date, categories)
    """
)
