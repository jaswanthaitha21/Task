import streamlit as st
import pandas as pd
import plotly.express as px
import json
import Levenshtein

# DeepEval
from deepeval.models import GeminiModel
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualRecallMetric,
    ContextualPrecisionMetric,
    GEval,
)
from deepeval.metrics.base_metric import BaseMetric
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

# Page config
st.set_page_config(page_title="LLM Output Evaluator", layout="wide")
st.title("🔍 LLM Output Evaluator")

# --- Configuration ---
with st.sidebar:
    st.header("⚙️ Config")
    GEMINI_API_KEY = st.text_input("Google API Key", type="password", value="")
    model_options = ["gemini-1.5-flash", "gemini-2.5-flash"]
    selected_model_name = st.selectbox("Judge Model", model_options)

if not GEMINI_API_KEY:
    st.warning("Please enter your Gemini API key.")
    st.stop()

try:
    model = GeminiModel(model_name=selected_model_name, api_key=GEMINI_API_KEY)
except Exception as e:
    st.error(f"Failed to load model: {e}")
    st.stop()


# --- Custom Usefulness Metric (Fixed!) ---
class UsefulnessMetric(BaseMetric):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.name = "Usefulness"

    def measure(self, test_case: LLMTestCase) -> float:
        try:
            # Include question (input), actual_output, and expected_output for richer judgment
            prompt = f"""
            On a scale of 0 to 1, evaluate how useful the LLM's response is for the given user question.
            Consider correctness, clarity, completeness, and relevance.

            User Question: {test_case.input}
            Expected Answer: {test_case.expected_output}
            LLM Response: {test_case.actual_output}

            Respond ONLY with valid JSON:
            {{ "score": <float between 0.0 and 1.0> }}

            Do NOT include explanations.
            """

            raw_response = self.model.generate(prompt).strip()
            st.session_state.debug_messages.append(f"🔧 [Usefulness] Raw LLM output: {raw_response}")

            # Robust JSON extraction
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            if start == -1 or end <= start:
                st.session_state.debug_messages.append("❌ No JSON found in response")
                return 0.0

            parsed = json.loads(raw_response[start:end])
            score = float(parsed.get("score", 0.0))

            return round(max(0.0, min(1.0, score)), 2)
        except Exception as e:
            st.session_state.debug_messages.append(f"❌ Usefulness error: {str(e)}")
            return 0.0

    def is_successful(self):
        return self.score >= 0.5


# Initialize debug log
if 'debug_messages' not in st.session_state:
    st.session_state.debug_messages = []


# --- File Upload ---
st.write("Upload a CSV with columns: `question`, `expected_output`, `actual_output`")
uploaded_file = st.file_uploader("Choose a file", type="csv")

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file, encoding='ISO-8859-1')
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

    required_cols = ["question", "expected_output", "actual_output"]
    if not all(col in df.columns for col in required_cols):
        st.error(f"Missing required columns. Found: {list(df.columns)}. Need: {required_cols}")
        st.dataframe(df.head())
    else:
        comparison_data = []

        for _, row in df.iterrows():
            question = str(row["question"]).strip()
            expected = str(row["expected_output"]).strip()
            actual = str(row["actual_output"]).strip()

            lev_score = round(Levenshtein.ratio(expected.lower(), actual.lower()), 2)

            # Create test case with retrieval context
            test_case = LLMTestCase(
                input=question,
                actual_output=actual,
                expected_output=expected,
                retrieval_context=[expected]  # Required for contextual metrics
            )

            result = {
                "Model": selected_model_name,
                "Question": question,
                "Expected Output": expected,
                "Actual Output": actual,
                "Levenshtein Similarity": lev_score,
                "Answer Relevance": None,
                "Usefulness": None,
                "Context Precision": None,
                "Context Recall": None,
                "G-Eval": None
            }

            # --- Evaluate Each Metric Safely ---
            # Answer Relevancy
            try:
                metric = AnswerRelevancyMetric(model=model)
                metric.measure(test_case)
                result["Answer Relevance"] = round(metric.score, 2)
            except Exception as e:
                st.session_state.debug_messages.append(f"❌ AnswerRelevancy failed: {e}")

            # Usefulness
            try:
                usefulness = UsefulnessMetric(model=model)
                result["Usefulness"] = usefulness.measure(test_case)
            except Exception as e:
                st.session_state.debug_messages.append(f"❌ Usefulness failed: {e}")

            # Contextual Precision
            try:
                metric = ContextualPrecisionMetric(model=model)
                metric.measure(test_case)
                result["Context Precision"] = round(metric.score, 2)
            except Exception as e:
                st.session_state.debug_messages.append(f"❌ ContextualPrecision failed: {e}")

            # Contextual Recall
            try:
                metric = ContextualRecallMetric(model=model)
                metric.measure(test_case)
                result["Context Recall"] = round(metric.score, 2)
            except Exception as e:
                st.session_state.debug_messages.append(f"❌ ContextualRecall failed: {e}")

            # G-Eval (Correctness)
            try:
                geval_metric = GEval(
                    name="Correctness",
                    model=model,
                    criteria="Is the actual output factually correct based on the expected output?",
                    evaluation_params=[
                        LLMTestCaseParams.EXPECTED_OUTPUT,
                        LLMTestCaseParams.ACTUAL_OUTPUT
                    ],
                )
                geval_metric.measure(test_case)
                result["G-Eval"] = round(geval_metric.score, 2)
            except Exception as e:
                st.session_state.debug_messages.append(f"❌ G-Eval failed: {e}")

            comparison_data.append(result)

        # Convert to DataFrame
        result_df = pd.DataFrame(comparison_data)

        # Leaderboard
        leaderboard_df = result_df.groupby("Model").agg({
            "Levenshtein Similarity": "mean",
            "Answer Relevance": "mean",
            "Usefulness": "mean",
            "Context Precision": "mean",
            "Context Recall": "mean",
            "G-Eval": "mean"
        }).round(2).reset_index()

        numeric_cols = leaderboard_df.select_dtypes(include='number').columns

        # --- Display Results ---
        st.subheader("🏆 Leaderboard")
        st.dataframe(
            leaderboard_df.style.format("{:.2f}", subset=numeric_cols),
            use_container_width=True
        )

        st.subheader("📋 Per-Case Results")
        st.dataframe(result_df, use_container_width=True)

        st.subheader("📈 Metric Distributions")
        metric_cols = ["Levenshtein Similarity", "Answer Relevance", "Usefulness", "Context Precision", "Context Recall", "G-Eval"]
        cols = st.columns(2)
        for i, metric in enumerate(metric_cols):
            if metric in result_df.columns:
                fig = px.histogram(result_df, x=metric, nbins=10, title=f"{metric} Distribution")
                fig.update_layout(height=300)
                cols[i % 2].plotly_chart(fig, use_container_width=True)

        # --- Debug Panel ---
        with st.expander("🐞 Debug Logs"):
            for msg in st.session_state.debug_messages:
                st.text(msg)

        # --- Downloads ---
        result_csv = result_df.to_csv(index=False).encode('utf-8')
        leaderboard_csv = leaderboard_df.to_csv(index=False).encode('utf-8')

        st.download_button("⬇️ Download Results CSV", data=result_csv, file_name="per_case_results.csv", mime="text/csv")
        st.download_button("⬇️ Download Leaderboard CSV", data=leaderboard_csv, file_name="leaderboard.csv", mime="text/csv")

else:
    st.info("Awaiting CSV upload...")