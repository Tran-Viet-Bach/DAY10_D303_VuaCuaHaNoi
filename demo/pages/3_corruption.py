import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import streamlit as st
from loaders import get_data_paths, load_corruption_log, load_metrics, load_quality
from components import quality_strip

st.set_page_config(page_title="Corruption", page_icon="2️⃣", layout="wide")
st.title("2️⃣ Corruption Simulation")

paths = get_data_paths()
log = load_corruption_log(str(paths["corruption_log"]))
baseline_metrics = load_metrics(str(paths["baseline_metrics"]))
corrupted_metrics = load_metrics(str(paths["corrupted_metrics"]))
corrupted_quality = load_quality(str(paths["corrupted_quality"]))

st.markdown(
    f"Original rows: **{log['original_row_count']}** → Corrupted rows: **{log['corrupted_row_count']}** "
    f"(generated at {log['generated_at']})"
)

st.divider()
st.subheader("🧪 6 Corruption Scenarios")

scenario_desc = {
    "drop_latest_record": "Remove a ground-truth document entirely → breaks retrieval",
    "blank_summary": "Empty the summary field → breaks quality & F1",
    "add_noise": "Inject noise text into a non-GT document",
    "truncate_title": "Truncate title → breaks exact-lookup path",
    "stale_date": "Set publication date to year 2000 → breaks freshness",
    "duplicate_row": "Duplicate a row → breaks uniqueness check",
}

cols = st.columns(3)
for i, entry in enumerate(log["entries"]):
    with cols[i % 3]:
        gt_badge = "📌 Ground Truth" if entry["in_ground_truth"] else "◽ Non-GT"
        with st.container(border=True):
            st.markdown(f"**{entry['type']}**")
            st.caption(scenario_desc.get(entry["type"], ""))
            st.caption(f"paper_id: `{entry['paper_id'][:30]}`")
            st.caption(gt_badge)

st.divider()
st.subheader("🔍 Corruption Log Detail")
df = pd.DataFrame(log["entries"])
st.dataframe(df, use_container_width=True, hide_index=True)

st.divider()
st.subheader("📉 Metric Impact")
metric_keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
rows = []
for key in metric_keys:
    base = baseline_metrics.get(key)
    corrupt = corrupted_metrics.get(key)
    delta = corrupt - base if isinstance(base, (int, float)) and isinstance(corrupt, (int, float)) else None
    rows.append({"Metric": key, "Baseline": base, "Corrupted": corrupt, "Δ": delta})
delta_df = pd.DataFrame(rows)
st.dataframe(
    delta_df.style.map(lambda v: "color: red" if isinstance(v, (int, float)) and v < 0 else "", subset=["Δ"]),
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("❌ Data Quality After Corruption")
st.markdown(f"Overall status: **{corrupted_quality.get('overall_status', 'N/A')}**")
quality_strip(corrupted_quality)
