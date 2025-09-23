# pages/Compare_Results.py

import streamlit as st
import pandas as pd
import plotly.express as px
import json
import Levenshtein
from io import StringIO
from difflib import SequenceMatcher
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
import nest_asyncio

# Allow nested event loops so asyncio works inside Streamlit
nest_asyncio.apply()

# --- Thread-Safe Debug Logging ---
# We avoid st.session_state in threads because it's not thread-safe
# Instead, we create a shared list outside session state
if 'safe_debug_logs' not in st.session_state:
    st.session_state.safe_debug_logs = []
debug_logs = st.session_state.safe_debug_logs  # Reference the same list everywhere

def log_debug(msg):
    debug_logs.append(f"{threading.current_thread().name}: {msg}")


# --- Custom Metric: Key-Value Alignment ---
class KeyValueAlignmentScore:
    def __init__(self):
        self.name = "Key-Value Alignment"
        self.score = 0.0

    def _similarity(self, a: str, b: str) -> float:
        """Case-insensitive string similarity using SequenceMatcher"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, a.strip().lower(), b.strip().lower()).ratio()

    def _clean_key(self, key: str) -> str:
        """Normalize keys by removing punctuation and spaces"""
        return key.strip().strip('"\'{}[]():').lower().replace(" ", "").replace("_", "")

    def _parse(self, text):
        """
        Parse text into dictionary using multiple strategies:
        1. Try JSON parsing
        2. Extract key-value pairs like "Status: Active"
        3. Fallback: treat entire output as single value
        """
        if not isinstance(text, str) or not text.strip():
            return {}

        raw = str(text).strip()

        # Strategy 1: Try JSON
        try:
            import json
            data = json.loads(raw)
            if isinstance(data, dict):
                return {k: str(v) for k, v in data.items()}
            elif isinstance(data, list):
                return {f"item_{i}": str(x) for i, x in enumerate(data)}
        except Exception:
            pass

        # Strategy 2: Extract key-value patterns like "Status: Active"
        import re
        kv_pairs = {}
        pattern = r'([a-zA-Z_][\w\s]*)\s*[:\-–>]\s*(.+?)(?:\n|$)'
        matches = re.findall(pattern, raw, re.IGNORECASE | re.MULTILINE)
        for key, value in matches:
            clean_key = self._clean_key(key)
            if clean_key:
                kv_pairs[clean_key] = value.strip()
        if kv_pairs:
            return kv_pairs

        # Strategy 3: If no structure, treat as single value
        return {"value": raw}

    def measure(self, test_case) -> float:
        """
        Measure alignment between expected and actual outputs
        Handles both structured (JSON/KV) and unstructured (free-text) cases
        """
        expected_dict = self._parse(test_case.expected_output)
        actual_dict = self._parse(test_case.actual_output)

        if not expected_dict or not actual_dict:
            self.score = 0.0
            return self.score

        # Normalize keys for matching
        exp_keys = {self._clean_key(k): k for k in expected_dict.keys()}
        act_keys = {self._clean_key(k): k for k in actual_dict.keys()}

        matched_keys = [k for k in exp_keys if k in act_keys]
        key_score = len(matched_keys) / len(exp_keys) if exp_keys else 0.0

        # Value similarity for matched keys
        value_scores = []
        for norm_key in matched_keys:
            orig_exp = exp_keys[norm_key]
            orig_act = act_keys[norm_key]
            sim = self._similarity(expected_dict[orig_exp], actual_dict[orig_act])
            value_scores.append(sim)

        value_score = sum(value_scores) / len(value_scores) if value_scores else 0.0

        # Special case: direct string match when both are flat values
        if (len(expected_dict) == 1 and "value" in exp_keys and
            len(actual_dict) == 1 and "value" in act_keys):
            direct_sim = self._similarity(
                expected_dict[exp_keys["value"]],
                actual_dict[act_keys["value"]]
            )
            self.score = round(direct_sim, 2)
            return self.score

        # Final score: weighted average of key match rate and value accuracy
        self.score = round(0.5 * key_score + 0.5 * value_score, 2)
        return self.score


# --- Safe Import DeepEval ---
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
    # These are high-level evaluation metrics powered by LLM-as-a-judge
    from deepeval.models import GeminiModel
    from deepeval.models import GPTModel
    from deepeval.metrics import AnswerRelevancyMetric, ContextualPrecisionMetric, ContextualRecallMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    DEEPEVAL_AVAILABLE = True
except Exception as e:
    st.warning(f"⚠️ Failed to load DeepEval: {e}")


def compare_results_page():
    st.set_page_config(page_title="LLM Output Evaluator", layout="wide")
    st.title("🔍 LLM Output Evaluator (Multi-Model Comparison)")

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
        except Exception as e:
            st.error(f"🔑 Missing API key: {e}")
            return

        show_debug = st.checkbox("Show Debug Logs")

        model_options = {
            "gemini": ["gemini-1.5-flash", "gemini-1.5-pro"],
            "openai": ["gpt-4o", "gpt-3.5-turbo"]
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

    # Initialize judge model
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

    # File uploader
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
    total_questions = 0

    # Pre-count questions and validate
    for file in uploaded_files:
        try:
            content = file.getvalue().decode("utf-8")
            df = pd.read_csv(StringIO(content))
        except UnicodeDecodeError:
            content = file.getvalue().decode("ISO-8859-1")
            df = pd.read_csv(StringIO(content))

        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            st.warning(f"⚠️ Skipping {file.name}: missing columns {missing}")
            continue

        total_questions += len(df)

    if total_questions == 0:
        st.error("🚫 No valid data found.")
        return

    # Progress bar
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Async worker for one row
    async def evaluate_row(row, model_name_display):
        question = str(row["question"]).strip() if pd.notna(row["question"]) else ""
        expected = str(row["expected_output"]).strip() if pd.notna(row["expected_output"]) else ""
        actual = str(row["actual_output"]).strip() if pd.notna(row["actual_output"]) else ""

        lev_similarity = round(Levenshtein.ratio(expected.lower(), actual.lower()), 2) if expected and actual else 0.0

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

        # Run metrics concurrently using ThreadPoolExecutor
        def run_metric(name, metric_class, **kwargs):
            try:
                metric = metric_class(model=judge_model, **kwargs)
                metric.measure(test_case)
                score = round(metric.score, 2)
                log_debug(f"[{name}] Score: {score}")
                return score
            except Exception as e:
                log_debug(f"[{name}] Failed: {type(e).__name__}: {e}")
                return None

        # For G-Eval (custom criteria)
        def run_geval():
            try:
                correctness = GEval(
                    name="Correctness",
                    model=judge_model,
                    criteria="Is the actual output factually consistent with the expected output?",
                    evaluation_params=[LLMTestCaseParams.EXPECTED_OUTPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
                )
                correctness.measure(test_case)
                score = round(correctness.score, 2)
                log_debug(f"[G-Eval] Score: {score}")
                return score
            except Exception as e:
                log_debug(f"[G-Eval] Failed: {type(e).__name__}: {e}")
                return None

        # For KV Alignment
        def run_kv():
            try:
                kv = KeyValueAlignmentScore()
                score = kv.measure(expected, actual)
                log_debug(f"[KV Alignment] Score: {score}")
                return score
            except Exception as e:
                log_debug(f"[KV Alignment] Failed: {type(e).__name__}: {e}")
                return None

        # Execute all in thread pool
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, run_metric, "AnswerRelevancy", AnswerRelevancyMetric),
                loop.run_in_executor(executor, run_metric, "ContextPrecision", ContextualPrecisionMetric),
                loop.run_in_executor(executor, run_metric, "ContextRecall", ContextualRecallMetric),
                loop.run_in_executor(executor, run_geval),
                loop.run_in_executor(executor, run_kv),
            ]
            scores = await asyncio.gather(*tasks)

        keys = ["Answer Relevance", "Context Precision", "Context Recall", "G-Eval", "Key-Value Alignment"]
        for k, v in zip(keys, scores):
            result[k] = v

        return result

    # Main async runner
    async def evaluate_all():
        tasks = []
        for file in uploaded_files:
            try:
                try:
                    content = file.getvalue().decode("utf-8")
                except UnicodeDecodeError:
                    content = file.getvalue().decode("ISO-8859-1")
                df = pd.read_csv(StringIO(content))

                if not required_cols.issubset(df.columns):
                    continue

                model_name_display = file.name.replace(".csv", "").replace("_", " ").replace("-", " ").title()

                for _, row in df.iterrows():
                    tasks.append(evaluate_row(row, model_name_display))
            except Exception as e:
                log_debug(f"[File] Read failed: {e}")

        results = await asyncio.gather(*tasks)
        return results

    # Run evaluation
    with st.spinner("Running concurrent evaluations..."):
        try:
            all_data = asyncio.run(evaluate_all())
            st.success("✅ Evaluation completed!")
        except Exception as e:
            st.error(f"Evaluation failed: {e}")
            return

    # Convert to DataFrame
    result_df = pd.DataFrame(all_data)
    numeric_metrics = [
        "Levenshtein Similarity", "Answer Relevance", "Context Precision",
        "Context Recall", "G-Eval", "Key-Value Alignment"
    ]

    for col in numeric_metrics:
        if col in result_df.columns:
            result_df[col] = pd.to_numeric(result_df[col], errors='coerce')

    leaderboard_df = result_df.groupby("Model")[numeric_metrics].mean().round(2).reset_index()
    for col in numeric_metrics:
        if col in leaderboard_df.columns:
            leaderboard_df[col] = pd.to_numeric(leaderboard_df[col], errors='coerce')
    leaderboard_df.fillna(0.0, inplace=True)

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🏆 Leaderboard", "📋 Per-Model Results", "📊 Charts", "🔍 Compare Per Question"])

    with tab1:
        st.subheader("🏅 Model Rankings")
        styled = leaderboard_df.style.format("{:.2f}", subset=numeric_metrics)
        for col in numeric_metrics:
            if col in leaderboard_df.columns and leaderboard_df[col].sum() > 0:
                styled = styled.background_gradient(cmap='Blues', subset=[col])
        st.dataframe(styled, width='stretch')

    with tab2:
        st.subheader("📋 Detailed Results by Model")
        for model in result_df["Model"].unique():
            st.markdown(f"#### 🤖 {model}")
            model_data = result_df[result_df["Model"] == model][[
                "Question", "Expected Output", "Actual Output"
            ] + numeric_metrics]
            st.dataframe(model_data, height=300, width='stretch')

    with tab3:
        st.subheader("📊 Performance Comparison Across Models")
        melted = leaderboard_df.melt(id_vars=["Model"], var_name="Metric", value_name="Score")
        fig = px.bar(melted, x="Model", y="Score", color="Metric", barmode="group", title="Scores by Metric")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📈 Distribution of Scores")
        cols = st.columns(2)
        for i, metric in enumerate(numeric_metrics):
            if metric in result_df.columns:
                fig_hist = px.histogram(result_df, x=metric, color="Model", nbins=10, title=metric)
                fig_hist.update_layout(height=300)
                cols[i % 2].plotly_chart(fig_hist, use_container_width=True)

    with tab4:
        st.subheader("🔎 Per-Question Winner Analysis")
        for metric in numeric_metrics:
            if metric not in result_df.columns:
                continue
            pivot = result_df.pivot_table(index="Question", columns="Model", values=metric)
            winner_counts = pivot.idxmax(axis=1).value_counts()

            col1, col2 = st.columns([2, 1])
            with col1:
                fig = px.bar(pivot.reset_index(), x="Question", y=pivot.columns, barmode="group", title=f"{metric}")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                st.markdown("**🏆 Winners**")
                st.write(winner_counts)

    # Downloads
    st.download_button(
        "⬇️ Download Full Results (CSV)",
        result_df.to_csv(index=False),
        "llm_evaluation_results.csv",
        "text/csv"
    )
    st.download_button(
        "⬇️ Download Leaderboard (CSV)",
        leaderboard_df.to_csv(index=False),
        "llm_leaderboard.csv",
        "text/csv"
    )

    # Debug panel
    if show_debug:
        with st.expander("🐞 Debug Logs"):
            for msg in debug_logs:
                st.text(msg)