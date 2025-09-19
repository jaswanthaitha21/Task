# pages/2_📊_Compare_Results.py

import streamlit as st
import pandas as pd
import plotly.express as px
import json
import Levenshtein
from io import StringIO
from difflib import SequenceMatcher


# --- Custom Metric: Key-Value Alignment ---
class KeyValueAlignmentScore:
    def __init__(self):
        self.name = "Key-Value Alignment"
        self.score = 0.0

    def _similarity(self, a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _parse(self, text):
        """Parse text into key-value pairs: tries JSON first, then line-by-line 'key: value'"""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pairs = {}
            for line in text.strip().splitlines():
                if ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if key:
                        pairs[key] = value
            return pairs if pairs else {}

    def measure(self, test_case) -> float:
        expected_dict = self._parse(test_case.expected_output)
        actual_dict = self._parse(test_case.actual_output)

        if not expected_dict or not actual_dict:
            self.score = 0.0
            return self.score

        matched_keys = [k for k in expected_dict if k in actual_dict]
        key_score = len(matched_keys) / len(expected_dict) if expected_dict else 0.0

        value_scores = [
            self._similarity(expected_dict[k], actual_dict[k])
            for k in matched_keys
        ]
        value_score = sum(value_scores) / len(value_scores) if value_scores else 0.0

        self.score = round(0.5 * key_score + 0.5 * value_score, 2)
        return self.score


# --- Try Import DeepEval Components Safely ---
DEEPEVAL_AVAILABLE = False
GeminiModel = None
GPTModel = None
AnswerRelevancyMetric = None
ContextualPrecisionMetric = None
ContextualRecallMetric = None
GEval = None
LLMTestCase = None
LLMTestCaseParams = None

try:
    from deepeval.models import GeminiModel
    from deepeval.models import GPTModel
    from deepeval.metrics import AnswerRelevancyMetric, ContextualRecallMetric, ContextualPrecisionMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    DEEPEVAL_AVAILABLE = True
except Exception as e:
    pass


def compare_results_page():
    st.set_page_config(page_title="LLM Output Evaluator", layout="wide")
    st.title("🔍 LLM Output Evaluator (Multi-Model Comparison)")

    # --- Debug Logging ---
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []

    def log_debug(msg):
        st.session_state.debug_logs.append(msg)

    # --- Sidebar: Provider, Model Selection ---
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Provider selection
        provider = st.selectbox(
            "Select Judge Provider",
            options=["gemini", "openai"],
            format_func=lambda x: x.capitalize()
        )

        # Load API key from secrets
        try:
            api_key = st.secrets["gemini_api_key"] if provider == "gemini" else st.secrets["openai_api_key"]
        except Exception as e:
            st.error(f"Missing API key: {e}")
            return

        show_debug = st.checkbox("Show Debug Logs")

        # Model selection
        model_options = {
            "gemini": ["gemini-1.5-flash", "gemini-1.5-pro"],
            "openai": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
        }
        model_name = st.selectbox(f"{provider.capitalize()} Model", model_options[provider])

        st.markdown("---")
        st.info("Upload one CSV per model. Must have: `question`, `expected_output`, `actual_output`.")

    if not DEEPEVAL_AVAILABLE:
        st.error("""
        Required package `deepeval` not installed.

        Install with:
        ```bash
        pip install "deepeval[all]" google-generativeai openai
        ```
        """)
        return

    # --- Initialize Judge Model ---
    judge_model = None
    try:
        if provider == "gemini":
            judge_model = GeminiModel(model_name=model_name, api_key=api_key)
        elif provider == "openai":
            judge_model = GPTModel(model_name=model_name, api_key=api_key)
        else:
            st.error("Unsupported provider.")
            return
    except Exception as e:
        st.error(f"Failed to initialize judge model: {e}")
        return

    # --- File Uploader ---
    st.write("### 📤 Upload LLM Outputs (One CSV per Model)")
    uploaded_files = st.file_uploader(
        "Upload CSV files (one per model)",
        type="csv",
        accept_multiple_files=True,
        help="Each must have: 'question', 'expected_output', 'actual_output'"
    )

    if not uploaded_files:
        st.info("📤 Please upload one or more model output CSVs to begin evaluation.")
        return

    required_cols = {"question", "expected_output", "actual_output"}
    all_data = []
    total_files = len(uploaded_files)
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, file in enumerate(uploaded_files):
        try:
            df = pd.read_csv(StringIO(file.getvalue().decode("utf-8")))
        except Exception as e:
            st.error(f"❌ Failed to read {file.name}: {e}")
            continue

        model_name_display = file.name.replace(".csv", "").replace("_", " ").replace("-", " ").title()

        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            st.error(f"⚠️ {model_name_display}: Missing columns: {missing}")
            continue

        st.write(f"**🧠 Evaluating:** `{model_name_display}` ({len(df)} questions)")

        for _, row in df.iterrows():
            question = str(row["question"]).strip()
            expected = str(row["expected_output"]).strip()
            actual = str(row["actual_output"]).strip()

            lev_similarity = round(Levenshtein.ratio(expected.lower(), actual.lower()), 2)

            retrieval_context = [f"In relation to '{question}', it's important to know that {expected}."]

            test_case = LLMTestCase(
                input=question,
                actual_output=actual,
                expected_output=expected,
                retrieval_context=retrieval_context
            )

            result = {
                "Model": model_name_display,
                "Question": question,
                "Expected Output": expected,
                "Actual Output": actual,
                "Levenshtein Similarity": lev_similarity,
            }

            def evaluate_with_log(name, metric_class, **kwargs):
                try:
                    metric = metric_class(model=judge_model, **kwargs)
                    metric.measure(test_case)
                    score = round(metric.score, 2)
                    log_debug(f"[{name}] Score: {score}")
                    return score
                except Exception as e:
                    log_debug(f"[{name}] Failed: {e}")
                    return None

            result["Answer Relevance"] = evaluate_with_log("AnswerRelevancy", AnswerRelevancyMetric)
            result["Context Precision"] = evaluate_with_log("ContextPrecision", ContextualPrecisionMetric)
            result["Context Recall"] = evaluate_with_log("ContextRecall", ContextualRecallMetric)

            try:
                correctness = GEval(
                    name="Correctness",
                    model=judge_model,
                    criteria="Is the actual output factually consistent with the expected output?",
                    evaluation_params=[LLMTestCaseParams.EXPECTED_OUTPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
                )
                correctness.measure(test_case)
                result["G-Eval"] = round(correctness.score, 2)
                log_debug(f"[G-Eval] Score: {result['G-Eval']}")
            except Exception as e:
                log_debug(f"[G-Eval] Failed: {e}")
                result["G-Eval"] = None

            try:
                kv_metric = KeyValueAlignmentScore()
                result["Key-Value Alignment"] = kv_metric.measure(test_case)
                log_debug(f"[Key-Value Alignment] Score: {result['Key-Value Alignment']}")
            except Exception as e:
                log_debug(f"[Key-Value Alignment] Failed: {e}")
                result["Key-Value Alignment"] = None

            all_data.append(result)

        progress = (idx + 1) / total_files
        progress_bar.progress(progress)
        status_text.text(f"✅ Processed {idx + 1}/{total_files} files...")

    progress_bar.empty()
    status_text.empty()

    if not all_data:
        st.error("🚫 No valid data found.")
        return

    result_df = pd.DataFrame(all_data)
    numeric_metrics = [
        "Levenshtein Similarity", "Answer Relevance", "Context Precision",
        "Context Recall", "G-Eval", "Key-Value Alignment"
    ]

    for col in numeric_metrics:
        result_df[col] = pd.to_numeric(result_df[col], errors='coerce')

    leaderboard_df = result_df.groupby("Model")[numeric_metrics].mean().round(2).reset_index()
    for col in numeric_metrics:
        leaderboard_df[col] = pd.to_numeric(leaderboard_df[col], errors='coerce')
    leaderboard_df.fillna(0.0, inplace=True)

    tab1, tab2, tab3, tab4 = st.tabs(["🏆 Leaderboard", "📋 Per-Model Results", "📊 Charts", "🔍 Compare Per Question"])

    with tab1:
        st.subheader("🏅 Model Rankings")
        styled = leaderboard_df.style.format("{:.2f}", subset=numeric_metrics)
        for col in numeric_metrics:
            if leaderboard_df[col].sum() > 0:
                styled = styled.background_gradient(cmap='Blues', subset=[col])
        st.dataframe(styled, width='stretch')

    with tab2:
        st.subheader("📋 Detailed Results by Model")
        for model in result_df["Model"].unique():
            st.markdown(f"#### 🤖 {model}")
            st.dataframe(result_df[result_df["Model"] == model].drop(columns=["Model"]), height=300)

    with tab3:
        st.subheader("📊 Performance Comparison")
        melted_df = leaderboard_df.melt(id_vars=["Model"], value_vars=numeric_metrics, var_name="Metric",
                                        value_name="Score")
        fig = px.bar(melted_df, x="Model", y="Score", color="Metric", barmode="group", title="Scores by Metric")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📈 Distributions")
        cols = st.columns(2)
        for i, metric in enumerate(numeric_metrics):
            fig_hist = px.histogram(result_df, x=metric, color="Model", nbins=10, title=metric)
            fig_hist.update_layout(height=300)
            cols[i % 2].plotly_chart(fig_hist, use_container_width=True)

    with tab4:
        st.subheader("🔎 Per-Question Analysis")
        for metric in numeric_metrics:
            st.markdown(f"#### {metric}")
            pivot = result_df.pivot_table(index="Question", columns="Model", values=metric)
            winner_counts = pivot.idxmax(axis=1).value_counts()
            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.bar(pivot.reset_index(), x="Question", y=pivot.columns, barmode="group", title=metric)
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.markdown("**🏆 Winners**")
                st.write(winner_counts)

    st.download_button("⬇️ Download Full Results", result_df.to_csv(index=False), "results.csv", "text/csv")
    st.download_button("⬇️ Download Leaderboard", leaderboard_df.to_csv(index=False), "leaderboard.csv", "text/csv")

    if show_debug:
        with st.expander("🐞 Debug Logs"):
            for msg in st.session_state.debug_logs:
                st.text(msg)