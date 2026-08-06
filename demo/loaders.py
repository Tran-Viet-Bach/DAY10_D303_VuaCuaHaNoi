import json
from pathlib import Path

import pandas as pd
import streamlit as st


@st.cache_data
def load_metrics(metrics_path: str) -> dict:
    with open(metrics_path) as f:
        return json.load(f)


@st.cache_data
def load_quality(quality_path: str) -> dict:
    with open(quality_path) as f:
        return json.load(f)


@st.cache_data
def load_freshness(freshness_path: str) -> dict:
    with open(freshness_path) as f:
        return json.load(f)


@st.cache_data
def load_corruption_log(log_path: str) -> dict:
    with open(log_path) as f:
        return json.load(f)


@st.cache_data
def load_answers(answers_path: str) -> list[dict]:
    with open(answers_path) as f:
        data = json.load(f)
        return data if isinstance(data, list) else []


@st.cache_data
def load_dataframe(csv_path: str) -> pd.DataFrame:
    return pd.read_csv(csv_path, dtype={"age_days": int}, keep_default_na=False)


def get_data_paths() -> dict:
    base = Path("data")
    return {
        "baseline_metrics": base / "results" / "baseline_metrics.json",
        "corrupted_metrics": base / "results" / "corrupted_metrics.json",
        "repaired_metrics": base / "results" / "repaired_metrics.json",
        "baseline_quality": base / "quality" / "baseline_quality.json",
        "corrupted_quality": base / "quality" / "corrupted_quality.json",
        "repaired_quality": base / "quality" / "repaired_quality.json",
        "freshness": base / "quality" / "freshness_report.json",
        "corrupted_freshness": base / "quality" / "corrupted_freshness_report.json",
        "repaired_freshness": base / "quality" / "repaired_freshness_report.json",
        "corruption_log": base / "results" / "corruption_log.json",
        "baseline_answers": base / "results" / "baseline_answers.json",
        "corrupted_answers": base / "results" / "corrupted_answers.json",
        "repaired_answers": base / "results" / "repaired_answers.json",
        "demo_answers": base / "results" / "agent_demo_answers.json",
        "clean_csv": base / "clean" / "papers_clean.csv",
        "corrupted_csv": base / "clean" / "papers_clean_corrupted.csv",
        "repaired_csv": base / "clean" / "papers_clean_repaired.csv",
        "corruption_report": base / "reports" / "corruption_report.md",
        "phase1_report": base / "reports" / "phase1_report.md",
        "test_set": base / "eval" / "test_set.json",
    }
