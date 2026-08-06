import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from loaders import get_data_paths, load_answers, load_metrics, load_quality

st.set_page_config(page_title="Comparison Dashboard", page_icon="📈", layout="wide")
st.title("📈 Comparison Dashboard")

paths = get_data_paths()
baseline_metrics = load_metrics(str(paths["baseline_metrics"]))
corrupted_metrics = load_metrics(str(paths["corrupted_metrics"]))
repaired_metrics = load_metrics(str(paths["repaired_metrics"]))
baseline_quality = load_quality(str(paths["baseline_quality"]))
corrupted_quality = load_quality(str(paths["corrupted_quality"]))
repaired_quality = load_quality(str(paths["repaired_quality"]))

metric_keys = ["retrieval_hit_rate", "mean_token_f1", "judge_accuracy", "mean_judge_score"]
metric_labels = {
    "retrieval_hit_rate": "Retrieval Hit Rate",
    "mean_token_f1": "Mean Token F1",
    "judge_accuracy": "Judge Accuracy",
    "mean_judge_score": "Mean Judge Score (/5, normalized)",
}

st.subheader("🧱 State Blocks")
cols = st.columns(3)
for col, label, m in zip(cols, ["Baseline", "Corrupted", "Repaired"], [baseline_metrics, corrupted_metrics, repaired_metrics]):
    with col:
        with st.container(border=True):
            st.markdown(f"### {label}")
            for key in metric_keys:
                st.metric(metric_labels[key], f"{m.get(key):.3f}")

st.divider()
st.subheader("📋 Master Comparison Table")
rows = []
for key in metric_keys:
    base = baseline_metrics.get(key)
    corrupt = corrupted_metrics.get(key)
    repair = repaired_metrics.get(key)
    d_corrupt = corrupt - base
    d_repair = repair - corrupt
    rows.append({
        "Metric": metric_labels[key],
        "Baseline": round(base, 4),
        "Corrupted": round(corrupt, 4),
        "Repaired": round(repair, 4),
        "Δ Corruption": round(d_corrupt, 4),
        "Δ Recovery": round(d_repair, 4),
    })
master_df = pd.DataFrame(rows)


def highlight_delta(v):
    if isinstance(v, (int, float)):
        if v < 0:
            return "background-color: #ffcccc"
        if v > 0:
            return "background-color: #ccffcc"
    return ""


st.dataframe(
    master_df.style.map(highlight_delta, subset=["Δ Corruption", "Δ Recovery"]),
    use_container_width=True,
    hide_index=True,
)

st.divider()
st.subheader("📊 Grouped Bar Chart")
long_rows = []
for state, m in zip(["Baseline", "Corrupted", "Repaired"], [baseline_metrics, corrupted_metrics, repaired_metrics]):
    for key in metric_keys:
        long_rows.append({"State": state, "Metric": metric_labels[key], "Value": m.get(key)})
long_df = pd.DataFrame(long_rows)
fig_bar = px.bar(long_df, x="Metric", y="Value", color="State", barmode="group")
st.plotly_chart(fig_bar, use_container_width=True)

st.divider()
st.subheader("🕸️ Radar Chart")
radar_metric_keys = metric_keys
fig_radar = go.Figure()
for state, m, color in zip(
    ["Baseline", "Corrupted", "Repaired"],
    [baseline_metrics, corrupted_metrics, repaired_metrics],
    ["#1f77b4", "#d62728", "#2ca02c"],
):
    values = [m.get(k) / 5 if k == "mean_judge_score" else m.get(k) for k in radar_metric_keys]
    values.append(values[0])
    fig_radar.add_trace(go.Scatterpolar(
        r=values,
        theta=[metric_labels[k] for k in radar_metric_keys] + [metric_labels[radar_metric_keys[0]]],
        fill="toself",
        name=state,
        line_color=color,
    ))
fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])))
st.plotly_chart(fig_radar, use_container_width=True)

st.divider()
st.subheader("📉 Slope Chart (Corrupted → Repaired)")
fig_slope = go.Figure()
for key in metric_keys:
    normalized = lambda v: v / 5 if key == "mean_judge_score" else v
    fig_slope.add_trace(go.Scatter(
        x=["Corrupted", "Repaired"],
        y=[normalized(corrupted_metrics.get(key)), normalized(repaired_metrics.get(key))],
        mode="lines+markers",
        name=metric_labels[key],
    ))
st.plotly_chart(fig_slope, use_container_width=True)

st.divider()
st.subheader("🔥 Quality Signal Heatmap")
check_names = [c["name"] for c in baseline_quality.get("checks", [])]
heat_rows = []
for state, q in zip(["Baseline", "Corrupted", "Repaired"], [baseline_quality, corrupted_quality, repaired_quality]):
    status_map = {c["name"]: (1 if c["status"] == "PASS" else 0) for c in q.get("checks", [])}
    heat_rows.append([status_map.get(name, 0) for name in check_names])
fig_heat = px.imshow(
    heat_rows,
    x=check_names,
    y=["Baseline", "Corrupted", "Repaired"],
    color_continuous_scale=["red", "green"],
    labels=dict(color="PASS=1"),
    aspect="auto",
)
st.plotly_chart(fig_heat, use_container_width=True)

st.divider()
st.subheader("❓ Per-Question Comparison")
baseline_answers = load_answers(str(paths["baseline_answers"]))
corrupted_answers = load_answers(str(paths["corrupted_answers"]))
repaired_answers = load_answers(str(paths["repaired_answers"]))
if baseline_answers and corrupted_answers and repaired_answers:
    per_q_rows = []
    for b, c, r in zip(baseline_answers, corrupted_answers, repaired_answers):
        per_q_rows.append({
            "question": b["question"][:60] + "…",
            "baseline_hit": b.get("retrieval_hit"),
            "corrupted_hit": c.get("retrieval_hit"),
            "repaired_hit": r.get("retrieval_hit"),
            "baseline_f1": round(b.get("token_f1", 0), 3),
            "corrupted_f1": round(c.get("token_f1", 0), 3),
            "repaired_f1": round(r.get("token_f1", 0), 3),
        })
    st.dataframe(pd.DataFrame(per_q_rows), use_container_width=True, hide_index=True)

st.divider()
st.subheader("📝 Causal Narrative")
d_hit = corrupted_metrics["retrieval_hit_rate"] - baseline_metrics["retrieval_hit_rate"]
d_f1 = corrupted_metrics["mean_token_f1"] - baseline_metrics["mean_token_f1"]
recovered_hit = repaired_metrics["retrieval_hit_rate"] == baseline_metrics["retrieval_hit_rate"]
recovered_f1 = repaired_metrics["mean_token_f1"] == baseline_metrics["mean_token_f1"]

narrative = f"""
Corruption injected 6 controlled defects (drop, blank, noise, truncate, stale-date, duplicate),
which reduced **retrieval_hit_rate by {abs(d_hit):.3f}** and **mean_token_f1 by {abs(d_f1):.3f}**,
and flipped the data quality gate from **{baseline_quality['overall_status']}** to **{corrupted_quality['overall_status']}**
({sum(1 for c in corrupted_quality['checks'] if c['status'] == 'FAIL')} check(s) failing:
{', '.join(c['name'] for c in corrupted_quality['checks'] if c['status'] == 'FAIL')}).

Repair re-derived clean data directly from the untouched raw snapshot (never from the corrupted copy),
which {'fully restored' if recovered_hit and recovered_f1 else 'partially restored'} baseline performance
(retrieval_hit_rate: {'✅ recovered' if recovered_hit else '⚠️ not fully recovered'},
mean_token_f1: {'✅ recovered' if recovered_f1 else '⚠️ not fully recovered'}),
and quality gate returned to **{repaired_quality['overall_status']}**.
"""
st.markdown(narrative)

st.divider()
st.subheader("⬇️ Export")
col1, col2 = st.columns(2)
with col1:
    st.download_button(
        "Download Master Comparison (CSV)",
        master_df.to_csv(index=False),
        file_name="master_comparison.csv",
        mime="text/csv",
    )
with col2:
    if paths["corruption_report"].exists():
        st.download_button(
            "Download Corruption Report (MD)",
            paths["corruption_report"].read_text(encoding="utf-8"),
            file_name="corruption_report.md",
            mime="text/markdown",
        )
