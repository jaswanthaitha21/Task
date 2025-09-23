# pages/2_📊_Compare_Results.py

import streamlit as st
import pandas as pd
import plotly.express as px
import json
import Levenshtein
from io import StringIO
from difflib import SequenceMatcher
import asyncio
from concurrent.futures import ThreadPoolExecutor
import nest_asyncio

# Apply nest_asyncio only once
nest_asyncio.apply()

# --- Custom Metric: Key-Value Alignment ---
class KeyValueAlignmentScore:
    def __init__(self):
        self.name = "Key-Value Alignment"
        self.score = 0.0

    def _similarity(self, a, b):
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def _parse(self, text):
        if isinstance(text, dict): return text
        try:
            return json.loads(str(text))
        except Exception:
            pairs = {}
            for line in str(text).splitlines():
                if ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip().strip('"\'{}[]')
                    value = parts[1].strip().strip('"\'{}[]')
                    if key: pairs[key] = value
            return pairs

    def measure(self, test_case) -> float:
        exp = self._parse(test_case.expected_output)
        act = self._parse(test_case.actual_output)
        if not exp or not act: return 0.0

        matched = [k for k in exp if k in act]
        key_score = len(matched) / len(exp)
        val_scores = [self._similarity(str(exp[k]), str(act[k])) for k in matched]
        val_score = sum(val_scores) / len(val_scores) if val_scores else 0.0

        self.score = round(0.5 * key_score + 0.5 * val_score, 2)
        return self.score


# --- Safe DeepEval Import ---
DEEPEVAL_AVAILABLE = False
GeminiModel = None
GPTModel = None
try:
    from deepeval.models import GeminiModel
    from deepeval.models import GPTModel
    from deepeval.metrics import AnswerRelevancyMetric, ContextualPrecisionMetric, ContextualRecallMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    DEEPEVAL_AVAILABLE = True
except Exception as e:
    st.warning(f"⚠️ DeepEval not available: {e}")


def compare_results_page():
    st.title("🔍 LLM Output Evaluator (Multi-Model Comparison)")

    # Debug logs
    if 'debug_logs' not in st.session_state:
        st.session_state.debug_logs = []

    def log_debug(msg):
        st.session_state.debug_logs.append(msg)

    # --- Sidebar: Judge Config ---
    with st.sidebar:
        st.header("⚙️ Configuration")

        provider = st.selectbox(
            "Judge Provider",
            options=["gemini", "openai"],
            format_func=str.capitalize
        )

        try:
            api_key = st.secrets["gemini_api_key"] if provider == "gemini" else st.secrets["openai_api_key"]
        except Exception:
            st.error("🔑 API key missing in `.streamlit/secrets.toml`")
            return

        show_debug = st.checkbox("Show Debug Logs")

        model_options = {
            "gemini": ["gemini-1.5-pro", "gemini-1.5-flash"],
            "openai": ["gpt-4o", "gpt-3.5-turbo"]
        }
        model_name = st.selectbox("Judge Model", model_options[provider])

        st.markdown("---")
        st.info("Upload CSVs with: `question`, `expected_output`, `actual_output`")

    if not DEEPEVAL_AVAILABLE:
        st.error("""
        Install required packages:
        ```bash
        pip install "deepeval[all]" google-generativeai openai
        ```
        """)
        return

    # Initialize judge model
    judge_model = None
    try:
        if provider == "gemini":
            judge_model = GeminiModel(model_name=model_name, api_key=api_key)
        elif provider == "openai":
            judge_model = GPTModel(model_name=model_name, api_key=api_key)
    except Exception as e:
        st.error(f"Failed to initialize judge model: {e}")
        return

    if judge_model is None:
        st.error("Could not initialize judge model.")
        return

    # File uploader
    uploaded_files = st.file_uploader(
        "Upload CSV files (one per model)",
        type="csv",
        accept_multiple_files=True,
        help="Must have: 'question', 'expected_output', 'actual_output'"
    )

    if not uploaded_files:
        st.info("📤 Upload at least one file.")
        return

    required_cols = {"question", "expected_output", "actual_output"}
    all_data = []
    total_questions = 0

    # Pre-load data
    for file in uploaded_files:
        try:
            df = pd.read_csv(StringIO(file.getvalue().decode("utf-8")))
            if not required_cols.issubset(df.columns):
                st.warning(f"⚠️ Skipping {file.name}: missing columns")
                continue
            total_questions += len(df)
        except Exception as e:
            st.error(f"❌ Failed to read {file.name}: {e}")

    if total_questions == 0:
        st.error("No valid data found.")
        return

    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Define async worker for one row
    async def evaluate_row(row, model_name_display):
        question = str(row["question"]).strip()
        expected = str(row["expected_output"]).strip()
        actual = str(row["actual_output"]).strip()

        lev_sim = round(Levenshtein.ratio(expected.lower(), actual.lower()), 2)

        test_case = LLMTestCase(
            input=question,
            actual_output=actual,
            expected_output=expected,
            retrieval_context=[expected]
        )

        result = {
            "Model": model_name_display,
            "Question": question,
            "Expected Output": expected,
            "Actual Output": actual,
            "Levenshtein Similarity": lev_sim,
        }

        # Define sync wrapper for DeepEval metrics
        def run_metric(name, fn):
            try:
                return fn()
            except Exception as e:
                log_debug(f"[{name}] {e}")
                return None

        # Run all metrics concurrently
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, run_metric, "AnswerRelevancy", lambda: (
                    AnswerRelevancyMetric(model=judge_model).measure(test_case),
                    round(AnswerRelevancyMetric.score, 2)
                )[1]),
                loop.run_in_executor(executor, run_metric, "ContextPrecision", lambda: (
                    ContextualPrecisionMetric(model=judge_model).measure(test_case),
                    round(ContextualPrecisionMetric.score, 2)
                )[1]),
                loop.run_in_executor(executor, run_metric, "ContextRecall", lambda: (
                    ContextualRecallMetric(model=judge_model).measure(test_case),
                    round(ContextualRecallMetric.score, 2)
                )[1]),
                loop.run_in_executor(executor, run_metric, "GEval", lambda: (
                    GEval(
                        name="Correctness",
                        model=judge_model,
                        criteria="Is the actual output factually consistent with the expected output?",
                        evaluation_params=[LLMTestCaseParams.EXPECTED_OUTPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
                    ).measure(test_case),
                    round(GEval.score, 2)
                )[1]),
            ]

            results = await asyncio.gather(*tasks)

        keys = ["Answer Relevance", "Context Precision", "Context Recall", "G-Eval"]
        for k, v in zip(keys, results):
            result[k] = v

        try:
            kv_metric = KeyValueAlignmentScore()
            result["Key-Value Alignment"] = kv_metric.measure(test_case)
        except Exception as e:
            result["Key-Value Alignment"] = None
            log_debug(f"[KV Alignment] {e}")

        return result

    # Main async runner
    async def evaluate_all():
        tasks = []
        for file in uploaded_files:
            try:
                df = pd.read_csv(StringIO(file.getvalue().decode("utf-8")))
                if not required_cols.issubset(df.columns):
                    continue
                model_name_display = file.name.replace(".csv", "").title()
                for _, row in df.iterrows():
                    tasks.append(evaluate_row(row, model_name_display))
            except Exception as e:
                log_debug(f"Error reading {file.name}: {e}")

        results = await asyncio.gather(*tasks)
        return results

    # Run async evaluation
    with st.spinner("Running concurrent evaluations..."):
        start_time = time.time()
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            all_data = loop.run_until_complete(evaluate_all())
        except Exception as e:
            st.error(f"Evaluation failed: {e}")
            return
        finally:
            loop.close()

        elapsed = time.time() - start_time
        st.success(f"✅ Evaluation completed in {elapsed:.1f} seconds!")

    # Convert to DataFrame
    result_df = pd.DataFrame(all_data)
    numeric_metrics = [
        "Levenshtein Similarity", "Answer Relevance", "Context Precision",
        "Context Recall", "G-Eval", "Key-Value Alignment"
    ]

    for col in numeric_metrics:
        result_df[col] = pd.to_numeric(result_df[col], errors='coerce')

    leaderboard_df = result_df.groupby("Model")[numeric_metrics].mean().round(2).reset_index()

    # Tabs
    tab1, tab2, tab3 = st.tabs(["🏆 Leaderboard", "📋 Results", "📈 Charts"])

    with tab1:
        st.subheader("🏅 Rankings")
        styled = leaderboard_df.style.format("{:.2f}").background_gradient(cmap='Blues')
        st.dataframe(styled, use_container_width=True)

    with tab2:
        st.subheader("📋 Detailed Results")
        for model in result_df["Model"].unique():
            st.markdown(f"#### 🤖 {model}")
            st.dataframe(result_df[result_df["Model"] == model][[
                "Question", "Expected Output", "Actual Output"
            ] + numeric_metrics], height=300)

    with tab3:
        melted = leaderboard_df.melt("Model", var_name="Metric", value_name="Score")
        fig = px.bar(melted, x="Model", y="Score", color="Metric", barmode="group")
        st.plotly_chart(fig, use_container_width=True)

    # Downloads
    st.download_button("⬇️ Full Results", result_df.to_csv(index=False), "results.csv", "text/csv")
    st.download_button("⬇️ Leaderboard", leaderboard_df.to_csv(index=False), "leaderboard.csv", "text/csv")

    if show_debug:
        with st.expander("🐞 Logs"):
            for msg in st.session_state.debug_logs:
                st.text(msg)