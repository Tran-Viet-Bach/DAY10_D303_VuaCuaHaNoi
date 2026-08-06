import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import plotly.express as px
import streamlit as st
from loaders import get_data_paths, load_answers, load_freshness, load_metrics, load_quality
from components import quality_strip, freshness_card

st.set_page_config(page_title="Baseline", page_icon="1️⃣", layout="wide")
st.title("1️⃣ Baseline Metrics")

paths = get_data_paths()
metrics = load_metrics(str(paths["baseline_metrics"]))
quality = load_quality(str(paths["baseline_quality"]))
freshness = load_freshness(str(paths["freshness"]))
answers = load_answers(str(paths["baseline_answers"]))

st.subheader("📊 Key Metrics")
cols = st.columns(4)
with cols[0]:
    st.metric("Retrieval Hit Rate", f"{metrics['retrieval_hit_rate']:.3f}")
with cols[1]:
    st.metric("Mean Token F1", f"{metrics['mean_token_f1']:.3f}")
with cols[2]:
    st.metric("Judge Accuracy", f"{metrics['judge_accuracy']:.3f}")
with cols[3]:
    st.metric("Mean Judge Score", f"{metrics['mean_judge_score']:.2f} / 5")

st.caption(f"Judge backend: `{metrics.get('judge_backend', 'N/A')}` · Samples: {metrics.get('samples', 'N/A')}")

st.divider()
st.subheader("✅ Data Quality Gates")
st.markdown(f"Overall status: **{quality.get('overall_status', 'N/A')}**")
quality_strip(quality)

st.divider()
st.subheader("🕐 Freshness")
freshness_card(freshness)

st.divider()
st.subheader("📈 Token F1 by Question Type")
if answers:
    df = pd.DataFrame(answers)
    if "question_type" in df.columns and "token_f1" in df.columns:
        agg = df.groupby("question_type")["token_f1"].mean().reset_index()
        fig = px.bar(agg, x="question_type", y="token_f1", color="question_type", range_y=[0, 1])
        st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("❓ Q&A Detail")
if answers:
    df = pd.DataFrame(answers)
    filter_choice = st.radio("Filter", ["All", "Hits only", "Misses only"], horizontal=True)
    if filter_choice == "Hits only" and "retrieval_hit" in df.columns:
        df = df[df["retrieval_hit"] == True]  # noqa: E712
    elif filter_choice == "Misses only" and "retrieval_hit" in df.columns:
        df = df[df["retrieval_hit"] == False]  # noqa: E712

    display_cols = [c for c in ["question", "question_type", "answer", "ground_truth", "retrieval_hit", "token_f1"] if c in df.columns]
    st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
else:
    st.warning("No baseline answers found.")
