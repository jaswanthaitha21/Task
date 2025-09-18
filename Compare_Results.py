# pages/2_📊_Compare_Results.py

import streamlit as st
import pandas as pd
import plotly.express as px

def compare_results_page():
    st.title("📊 Compare LLM Models")

    st.write("### Upload evaluated CSVs from 'Run Experiment' (must include metrics)")

    uploaded_files = st.file_uploader(
        "Upload 2+ evaluated model outputs",
        type="csv",
        accept_multiple_files=True,
        key="compare_uploader"
    )

    if not uploaded_files or len(uploaded_files) < 2:
        st.info("📤 Upload at least two evaluated CSV files to compare.")
        return

    all_models = []
    metric_cols = [
        "Levenshtein Similarity",
        "Key-Value Alignment",
        "Answer Relevance",
        "G-Eval"
    ]

    for file in uploaded_files:
        try:
            df = pd.read_csv(file)
            required = {"input", "expected_output", "actual_output"}
            if not required.issubset(df.columns):
                st.warning(f"⚠️ Skipping {file.name}: missing required columns.")
                continue

            model_name = file.name.replace(".csv", "").replace("_", " ").title()

            # Compute average scores
            scores = {"Model": model_name}
            for col in metric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    scores[col] = df[col].mean()
                else:
                    scores[col] = None
            all_models.append(scores)

        except Exception as e:
            st.error(f"❌ Failed to process {file.name}: {e}")

    if not all_models:
        st.error("No valid model data found.")
        return

    # Leaderboard
    leaderboard = pd.DataFrame(all_models)
    st.subheader("🏆 Model Comparison Leaderboard")
    st.dataframe(
        leaderboard.style.format("{:.2f}")
                     .background_gradient(cmap='Blues', subset=[c for c in metric_cols if c in leaderboard.columns]),
        use_container_width=True
    )

    # Charts
    st.subheader("📈 Performance Charts")

    melted = leaderboard.melt("Model", var_name="Metric", value_name="Score").dropna()
    fig = px.bar(
        melted,
        x="Model",
        y="Score",
        color="Metric",
        barmode="group",
        title="Model Scores by Metric",
        text="Score"
    )
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

    # Per-model view
    st.subheader("📋 Detailed Results by Model")
    for file in uploaded_files:
        try:
            df = pd.read_csv(file)
            model_name = file.name.replace(".csv", "").title()
            with st.expander(f"📄 {model_name}"):
                st.dataframe(df[[c for c in df.columns if c != "expected_output"]])
        except:
            continue