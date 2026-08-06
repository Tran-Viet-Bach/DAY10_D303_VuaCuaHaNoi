import streamlit as st
from typing import Any


def metric_card(label: str, value: Any, delta: str = "", delta_color: str = "normal"):
    """Display a metric card with optional delta."""
    col1, col2 = st.columns([3, 1])
    with col1:
        st.metric(label, f"{value:.4f}" if isinstance(value, float) else value)
    if delta:
        with col2:
            st.caption(delta)


def quality_pill(check_name: str, status: str):
    """Display a quality check pill."""
    color = "🟢" if status == "PASS" else "🔴"
    st.caption(f"{color} {check_name}")


def quality_strip(quality: dict):
    """Display 6 quality check pills in a row."""
    cols = st.columns(6)
    checks = quality.get("checks", [])
    for i, check in enumerate(checks):
        if i < 6:
            with cols[i]:
                quality_pill(check["name"], check["status"])


def freshness_card(freshness: dict):
    """Display freshness summary."""
    cols = st.columns(3)
    with cols[0]:
        st.metric("Latest Published", freshness.get("latest_published", "N/A"))
    with cols[1]:
        st.metric("Oldest Published", freshness.get("oldest_published", "N/A"))
    with cols[2]:
        stale = freshness.get("stale_rows", 0)
        total = freshness.get("total_rows", 1)
        is_fresh = "✅ Fresh" if freshness.get("is_fresh") else f"⚠️ {stale} stale"
        st.metric("Status", is_fresh)


def corruption_entry_row(entry: dict):
    """Display a single corruption entry as a compact row."""
    cols = st.columns([1, 2, 1.5, 0.8])
    with cols[0]:
        st.caption(entry["type"])
    with cols[1]:
        st.caption(entry["paper_id"][:20])
    with cols[2]:
        gt_badge = "📌 GT" if entry["in_ground_truth"] else "–"
        st.caption(gt_badge)
    with cols[3]:
        st.caption(entry.get("param", "")[:15])


def comparison_table_header():
    """Display comparison table header."""
    cols = st.columns([2, 1, 1, 1, 1, 1])
    with cols[0]:
        st.write("**Metric**")
    with cols[1]:
        st.write("**Baseline**")
    with cols[2]:
        st.write("**Corrupted**")
    with cols[3]:
        st.write("**Repaired**")
    with cols[4]:
        st.write("**Δ Corrupt**")
    with cols[5]:
        st.write("**Δ Repair**")
