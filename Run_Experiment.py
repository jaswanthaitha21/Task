# pages/1_🧪_Run_Experiment.py

import streamlit as st
import pandas as pd
import google.generativeai as genai
from openai import OpenAI
from PIL import Image
import os
import json
from difflib import SequenceMatcher
import Levenshtein

# --- Try importing DeepEval safely ---
DEEPEVAL_AVAILABLE = False
try:
    from deepeval.models.gpt_model import GPTModel
    from deepeval.models.gemini_model import GeminiModel
    from deepeval.metrics import AnswerRelevancyMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    DEEPEVAL_AVAILABLE = True
except Exception as e:
    st.warning(f"⚠️ DeepEval not available: {e}. Only basic metrics will be computed.")

# --- Custom KV Alignment ---
def parse_kv(text):
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

def kv_alignment_score(expected, actual):
    exp_dict = parse_kv(expected)
    act_dict = parse_kv(actual)
    if not exp_dict: return 0.0
    matched_keys = [k for k in exp_dict if k in act_dict]
    key_score = len(matched_keys) / len(exp_dict)
    value_scores = [
        SequenceMatcher(None, str(exp_dict[k]), str(act_dict[k])).ratio()
        for k in matched_keys
    ]
    value_score = sum(value_scores) / len(value_scores) if value_scores else 0.0
    return round(0.5 * key_score + 0.5 * value_score, 2)


def run_experiment_page():
    st.title("🧪 Run LLM Experiment")

    # --- Session State ---
    if 'evaluated_df' not in st.session_state:
        st.session_state.evaluated_df = None

    # --- Sidebar: Model Settings ---
    st.sidebar.header("⚙️ Inference & Evaluation")
    provider = st.sidebar.selectbox("Provider", ["gemini", "openai"], key="inf_provider")
    api_key = st.sidebar.text_input(f"{provider.capitalize()} API Key", type="password", key=f"{provider}_key")
    model_name = st.sidebar.selectbox(
        "Model",
        ["gemini-1.5-pro", "gemini-1.5-flash"] if provider == "gemini" else ["gpt-4o", "gpt-3.5-turbo"],
        key=f"{provider}_model"
    )

    # --- Judge LLM Selection ---
    st.sidebar.subheader("⚖️ Judge LLM (for evaluation)")
    judge_provider = st.sidebar.selectbox("Judge Provider", ["gemini", "openai"], key="judge_prov")
    judge_api_key = st.sidebar.text_input(f"Judge API Key", type="password", key="judge_key")
    judge_model_name = st.sidebar.selectbox(
        "Judge Model",
        ["gemini-1.5-pro", "gemini-1.5-flash"] if judge_provider == "gemini" else ["gpt-4o", "gpt-3.5-turbo"],
        key="judge_model"
    )

    # --- Master Prompt ---
    st.write("### 🧩 Master Prompt (use `{input}`)")
    master_prompt = st.text_area(
        "Edit prompt:",
        "Answer the question:\n\n{input}",
        height=180,
        key="master_prompt_edit"
    )

    # --- Upload Dataset ---
    uploaded_file = st.file_uploader("Upload CSV with `input`, `expected_output`", type="csv", key="run_upload")

    if not uploaded_file:
        st.info("📤 Upload a dataset to begin.")
        return

    try:
        df = pd.read_csv(uploaded_file)
        required = {"input", "expected_output"}
        if not required.issubset(df.columns):
            st.error(f"CSV must have: {required}")
            st.dataframe(df.head())
            return
    except Exception as e:
        st.error(f"Failed to read file: {e}")
        return

    # Show preview
    with st.expander("🔍 Input Data Preview"):
        st.dataframe(df)

    # --- Run Experiment Button ---
    if st.button("🚀 Run Experiment & Evaluate", key="run_btn"):
        if not api_key.strip():
            st.warning("🔑 Enter inference API key.")
            return
        if not judge_api_key.strip():
            st.warning("🔑 Enter judge API key.")
            return

        with st.spinner("Running inference and LLM-based evaluation..."):
            results = []

            # Initialize inference model
            try:
                if provider == "gemini":
                    genai.configure(api_key=api_key)
                    inf_model = genai.GenerativeModel(model_name)
                else:
                    inf_client = OpenAI(api_key=api_key)
            except Exception as e:
                st.error(f"❌ Failed to initialize inference model: {e}")
                return

            # Initialize judge model for evaluation
            judge_model = None
            if DEEPEVAL_AVAILABLE:
                try:
                    if judge_provider == "gemini":
                        judge_model = GeminiModel(model_name=judge_model_name, api_key=judge_api_key)
                    else:
                        judge_model = GPTModel(model_name=judge_model_name, api_key=judge_api_key)
                except Exception as e:
                    st.warning(f"Could not load judge model: {e}")

            if judge_model is None:
                st.warning("LLM-as-a-judge metrics will be skipped.")

            for _, row in df.iterrows():
                inp = str(row["input"]).strip()
                expected = str(row["expected_output"]).strip()

                # Render prompt
                try:
                    prompt = master_prompt.format(input=inp)
                except:
                    prompt = master_prompt + "\n\n" + inp

                # --- Step 1: Generate actual_output ---
                actual = "[ERROR]"
                try:
                    if inp.lower().endswith(('.png', '.jpg', '.jpeg')) and os.path.exists(inp):
                        if provider == "gemini":
                            with open(inp, "rb") as f:
                                response = inf_model.generate_content([prompt, {"mime_type": "image/jpeg", "data": f.read()}])
                                actual = response.text
                        else:
                            actual = "Image input not supported."
                    else:
                        if provider == "gemini":
                            response = inf_model.generate_content(prompt)
                            actual = response.text
                        else:
                            resp = inf_client.chat.completions.create(
                                model=model_name,
                                messages=[{"role": "user", "content": prompt}],
                                max_tokens=1024
                            )
                            actual = resp.choices[0].message.content
                except Exception as e:
                    actual = f"[ERROR] {str(e)[:200]}"

                # --- Step 2: Evaluate using LLM-as-a-judge ---
                test_case = LLMTestCase(
                    input=inp,
                    actual_output=actual,
                    expected_output=expected,
                    retrieval_context=[expected]  # For contextual metrics
                )

                result = {
                    "input": inp,
                    "expected_output": expected,
                    "actual_output": actual,
                    "Levenshtein Similarity": round(Levenshtein.ratio(expected.lower(), actual.lower()), 2),
                    "Key-Value Alignment": kv_alignment_score(expected, actual)
                }

                # Answer Relevance
                if judge_model:
                    try:
                        metric = AnswerRelevancyMetric(model=judge_model)
                        metric.measure(test_case)
                        result["Answer Relevance"] = round(metric.score, 2)
                    except Exception as e:
                        result["Answer Relevance"] = None
                else:
                    result["Answer Relevance"] = None

                # G-Eval: Correctness
                if judge_model:
                    try:
                        correctness = GEval(
                            name="Correctness",
                            model=judge_model,
                            criteria="Is the actual output factually consistent with the expected output?",
                            evaluation_params=[LLMTestCaseParams.EXPECTED_OUTPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
                        )
                        correctness.measure(test_case)
                        result["G-Eval"] = round(correctness.score, 2)
                    except Exception as e:
                        result["G-Eval"] = None
                else:
                    result["G-Eval"] = None

                results.append(result)

            # Save evaluated results
            result_df = pd.DataFrame(results)
            st.session_state.evaluated_df = result_df

            st.success("✅ Experiment & LLM-Based Evaluation Complete!")
            st.balloons()

    # --- Display Evaluated Results ---
    if st.session_state.evaluated_df is not None:
        result_df = st.session_state.evaluated_df
        st.subheader("📋 Evaluated Results (With LLM-as-a-Judge Metrics)")
        st.dataframe(result_df, use_container_width=True)

        # Download button
        csv_data = result_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Evaluated Results (Ready for Comparison)",
            csv_data,
            "evaluated_model_results.csv",
            "text/csv"
        )