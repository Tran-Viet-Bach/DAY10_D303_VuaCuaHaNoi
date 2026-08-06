import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import plotly.graph_objects as go
import streamlit as st
from loaders import get_data_paths, load_dataframe, load_metrics, load_quality
from components import quality_strip

st.set_page_config(page_title="Repair", page_icon="3️⃣", layout="wide")
st.title("3️⃣ Repair Process")

paths = get_data_paths()
baseline_df = load_dataframe(str(paths["clean_csv"]))
repaired_df = load_dataframe(str(paths["repaired_csv"]))
baseline_metrics = load_metrics(str(paths["baseline_metrics"]))
corrupted_metrics = load_metrics(str(paths["corrupted_metrics"]))
repaired_metrics = load_metrics(str(paths["repaired_metrics"]))
repaired_quality = load_quality(str(paths["repaired_quality"]))

st.markdown(
    """
    ## Repair Flow

    ```
    Raw Snapshot (untouched) ──▶ build_clean_dataframe() ──▶ Repaired Data
    ```

    Repair **never** reads the corrupted copy — it re-derives clean data from the original
    raw API snapshot, guaranteeing a deterministic, independent recovery path.
    """
)

st.divider()
st.subheader("🔗 Lineage Verification")

baseline_ids = set(baseline_df["paper_id"])
repaired_ids = set(repaired_df["paper_id"])
lineage_match = baseline_ids == repaired_ids

cols = st.columns(3)
with cols[0]:
    st.metric("Baseline rows", len(baseline_df))
with cols[1]:
    st.metric("Repaired rows", len(repaired_df))
with cols[2]:
    st.metric("Lineage match", "✅ True" if lineage_match else "❌ False")

if not lineage_match:
    st.error(f"Missing from repaired: {baseline_ids - repaired_ids}")
    st.error(f"Unexpected in repaired: {repaired_ids - baseline_ids}")

st.divider()
st.subheader("📊 Recovery Rate (retrieval_hit_rate)")

base_val = baseline_metrics["retrieval_hit_rate"]
corrupt_val = corrupted_metrics["retrieval_hit_rate"]
repair_val = repaired_metrics["retrieval_hit_rate"]
recovery_pct = 100.0 if corrupt_val == base_val else min(100.0, max(0.0, (repair_val - corrupt_val) / (base_val - corrupt_val) * 100)) if base_val != corrupt_val else 100.0

fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=recovery_pct,
    title={"text": "Recovery Rate (%)"},
    gauge={"axis": {"range": [0, 100]}, "bar": {"color": "green"}},
))
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("⏱️ Timeline: Baseline → Corrupted → Repaired")
timeline_cols = st.columns(3)
metric_keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
for col, label, m in zip(timeline_cols, ["Baseline", "Corrupted", "Repaired"], [baseline_metrics, corrupted_metrics, repaired_metrics]):
    with col:
        st.markdown(f"**{label}**")
        for key in metric_keys:
            st.caption(f"{key}: {m.get(key):.3f}")

st.divider()
st.subheader("✅ Data Quality After Repair")
st.markdown(f"Overall status: **{repaired_quality.get('overall_status', 'N/A')}**")
quality_strip(repaired_quality)
