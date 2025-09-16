import streamlit as st
import pandas as pd
import plotly.express as px
import json
import Levenshtein
from io import StringIO

# DeepEval
from deepeval.models import GeminiModel
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRecallMetric,
    ContextualPrecisionMetric,
    GEval,
)
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from deepeval.metrics.base_metric import BaseMetric


# Page config
st.set_page_config(page_title="LLM Output Evaluator", layout="wide")
st.title("🔍 LLM Output Evaluator (Multi-Model Comparison)")

# --- Debug State Initialization ---
if 'debug_logs' not in st.session_state:
    st.session_state.debug_logs = []

def log_debug(msg):
    st.session_state.debug_logs.append(msg)


# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    GEMINI_API_KEY = st.text_input("Enter Google API Key", type="password")
    judge_model_name = st.selectbox(
        "Select Judge Model",
        ["gemini-1.5-flash", "gemini-2.5-flash"]
    )
    show_debug = st.checkbox("Show Debug Logs")

if not GEMINI_API_KEY:
    st.warning("Please enter your Google API key to proceed.")
    st.stop()

try:
    judge_model = GeminiModel(model_name=judge_model_name, api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"Failed to initialize Gemini model: {e}")
    st.stop()


# --- Custom Usefulness Metric (Now Works!) ---
class UsefulnessMetric(BaseMetric):
    def __init__(self, model):
        self.model = model
        self.name = "Usefulness"

    def measure(self, test_case: LLMTestCase) -> float:
        try:
            prompt = f"""
            Evaluate how useful this response is on a scale from 0 to 1.
            Consider correctness, clarity, relevance, and completeness.

            User Question: {test_case.input}
            Expected Answer: {test_case.expected_output}
            LLM Response: {test_case.actual_output}

            Respond ONLY with:
            {{ "score": 0.75 }}
            Do NOT include any other text.
            """
            raw_response = self.model.generate(prompt).strip()
            log_debug(f"[Usefulness] Raw → {raw_response}")

            # Extract JSON safely
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            if start == -1 or end <= start:
                log_debug("❌ No JSON found")
                return 0.0
            parsed = json.loads(raw_response[start:end])
            score = float(parsed.get("score", 0.0))
            return max(0.0, min(1.0, score))
        except Exception as e:
            log_debug(f"❌ Usefulness error: {str(e)}")
            return 0.0

    def is_successful(self):
        return self.score >= 0.5


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
else:
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

        model_name = file.name.replace(".csv", "").replace("_", " ").replace("-", " ").title()

        if not required_cols.issubset(df.columns):
            missing = required_cols - set(df.columns)
            st.error(f"⚠️ {model_name}: Missing columns: {missing}")
            continue

        st.write(f"**🧠 Evaluating:** `{model_name}` ({len(df)} questions)")

        for _, row in df.iterrows():
            question = str(row["question"]).strip()
            expected = str(row["expected_output"]).strip()
            actual = str(row["actual_output"]).strip()

            lev_score = round(Levenshtein.ratio(expected.lower(), actual.lower()), 2)

            # ✅ Realistic retrieval context (simulate RAG)
            retrieval_context = [
                f"In relation to '{question}', it's important to know that {expected}. "
                "This fact helps provide accurate answers in knowledge-intensive tasks."
            ]

            test_case = LLMTestCase(
                input=question,
                actual_output=actual,
                expected_output=expected,
                retrieval_context=retrieval_context
            )

            result = {
                "Model": model_name,
                "Question": question,
                "Expected Output": expected,
                "Actual Output": actual,
                "Levenshtein Similarity": lev_score,
            }

            # Generic safe evaluator with logging
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

            # ✅ Answer Relevancy
            result["Answer Relevance"] = evaluate_with_log("AnswerRelevancy", AnswerRelevancyMetric)

            # ✅ Usefulness (Custom)
            try:
                usefulness = UsefulnessMetric(model=judge_model)
                result["Usefulness"] = usefulness.measure(test_case)
                log_debug(f"[Usefulness] Final: {result['Usefulness']}")
            except Exception as e:
                log_debug(f"[Usefulness] Exception: {e}")
                result["Usefulness"] = None

            # ✅ Contextual Precision
            result["Context Precision"] = evaluate_with_log("ContextPrecision", ContextualPrecisionMetric)

            # ✅ Contextual Recall
            result["Context Recall"] = evaluate_with_log("ContextRecall", ContextualRecallMetric)

            # ✅ G-Eval: Correctness
            try:
                correctness = GEval(
                    name="Correctness",
                    model=judge_model,
                    criteria="Is the actual output factually consistent with the expected output?",
                    evaluation_params=[
                        LLMTestCaseParams.EXPECTED_OUTPUT,
                        LLMTestCaseParams.ACTUAL_OUTPUT
                    ],
                )
                correctness.measure(test_case)
                result["G-Eval"] = round(correctness.score, 2)
                log_debug(f"[G-Eval] Score: {result['G-Eval']}")
            except Exception as e:
                log_debug(f"[G-Eval] Failed: {e}")
                result["G-Eval"] = None

            all_data.append(result)

        # Update progress
        progress = (idx + 1) / total_files
        progress_bar.progress(progress)
        status_text.text(f"✅ Processed {idx + 1}/{total_files} files...")

    progress_bar.empty()
    status_text.empty()

    if not all_data:
        st.error("🚫 No valid data found. Check your CSV formats.")
    else:
        # Create DataFrame
        result_df = pd.DataFrame(all_data)
        numeric_metrics = [
            "Levenshtein Similarity",
            "Answer Relevance",
            "Usefulness",
            "Context Precision",
            "Context Recall",
            "G-Eval"
        ]

        # Ensure numeric types
        for col in numeric_metrics:
            result_df[col] = pd.to_numeric(result_df[col], errors='coerce')

        # Compute leaderboard
        leaderboard_df = result_df.groupby("Model")[numeric_metrics].mean().round(2).reset_index()
        for col in numeric_metrics:
            leaderboard_df[col] = pd.to_numeric(leaderboard_df[col], errors='coerce')
        leaderboard_df.fillna(0.0, inplace=True)

        # Tabs
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
                model_data = result_df[result_df["Model"] == model].drop(columns=["Model"])
                st.dataframe(model_data, height=300)

        with tab3:
            st.subheader("📊 Performance Comparison")

            melted_df = leaderboard_df.melt(id_vars=["Model"], value_vars=numeric_metrics, var_name="Metric", value_name="Score")
            fig = px.bar(
                melted_df,
                x="Model",
                y="Score",
                color="Metric",
                barmode="group",
                title="Model Scores by Metric",
                text="Score",
                height=500,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
            fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
            st.plotly_chart(fig, use_container_width=True)

            st.markdown("### 📈 Metric Distributions")
            cols = st.columns(2)
            for i, metric in enumerate(numeric_metrics):
                fig_hist = px.histogram(result_df, x=metric, color="Model", nbins=10, title=f"{metric}")
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
                    fig = px.bar(pivot.reset_index(), x="Question", y=pivot.columns, barmode="group", title=f"{metric}")
                    fig.update_layout(height=400, legend_title="Model")
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.markdown("**🏆 Winners**")
                    st.write(winner_counts)

        # Download buttons
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

        # 🔍 Debug Panel
        if show_debug:
            with st.expander("🐞 Debug Logs"):
                for msg in st.session_state.debug_logs:
                    st.text(msg)