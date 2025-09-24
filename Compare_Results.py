# pages/Compare_Results.py

import ast
from collections.abc import Mapping
import plotly.express as px
import streamlit as st
import pandas as pd
import json
import Levenshtein
from io import StringIO
from difflib import SequenceMatcher
import threading
import asyncio
from concurrent.futures import ThreadPoolExecutor
import nest_asyncio

# Allowing nested event loops so asyncio works inside Streamlit
nest_asyncio.apply()

# --- Thread-Safe Debug Logging ---
# We avoid st.session_state in threads because it's not thread-safe
# and create a shared list outside session state
if 'safe_debug_logs' not in st.session_state:
    st.session_state.safe_debug_logs = []
debug_logs = st.session_state.safe_debug_logs  # References the same list everywhere


def log_debug(msg):
    debug_logs.append(f"{threading.current_thread().name}: {msg}")


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
    from deepeval.models import GeminiModel
    from deepeval.models import GPTModel
    from deepeval.metrics import AnswerRelevancyMetric, ContextualPrecisionMetric, ContextualRecallMetric, GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams
    DEEPEVAL_AVAILABLE = True
except Exception as e:
    st.warning(f" Failed to load DeepEval: {e}")


def compare_results_page():

    def fuzzy_value_similarity(expected, actual):
        exp = try_parse_json(expected)
        act = try_parse_json(actual)
        from difflib import SequenceMatcher

        if isinstance(exp, (dict, list)) and isinstance(act, (dict, list)):
            exp_flat = flatten_json(exp)
            act_flat = flatten_json(act)
            scores = []
            for k, v in exp_flat.items():
                if k in act_flat:
                    sim = SequenceMatcher(None, str(v), str(act_flat[k])).ratio()
                    scores.append(sim)
            return round(sum(scores) / len(scores), 2) if scores else 0.0

        # Fallback: treat as text, use string similarity
        if str(expected).strip() and str(actual).strip():
            return round(SequenceMatcher(None, str(expected).strip(), str(actual).strip()).ratio(), 2)
        return 0.0

    def try_parse_json(text):
        try:
            return json.loads(text)
        except Exception:
            try:
                return ast.literal_eval(text)
            except Exception:
                return None

    def flatten_json(y, parent_key='', sep='.'):
        items = {}
        if isinstance(y, Mapping):
            for k, v in y.items():
                new_key = f"{parent_key}{sep}{k}" if parent_key else k
                items.update(flatten_json(v, new_key, sep=sep))
        elif isinstance(y, list):
            for i, v in enumerate(y):
                new_key = f"{parent_key}{sep}{i}" if parent_key else str(i)
                items.update(flatten_json(v, new_key, sep=sep))
        else:
            items[parent_key] = str(y)
        return items

    st.set_page_config(page_title="LLM Output Evaluator", layout="wide")
    st.title(" LLM Output Evaluator (Multi-Model Comparison)")

    # --- Sidebar: Judge Config ---
    with st.sidebar:
        st.header("Configuration")

        provider = st.selectbox(
            "Judge Provider",
            options=["gemini", "openai"],
            format_func=str.capitalize
        )

        try:
            api_key = st.secrets["gemini_api_key"] if provider == "gemini" else st.secrets["openai_api_key"]
        except Exception as e:
            st.error(f" Missing API key: {e}")
            return

        show_debug = st.checkbox("Show Debug Logs")

        model_options = {
            "gemini": [
                "gemini-1.5-flash", "gemini-1.5-flash-8b", "gemini-1.5-pro",
                "gemini-2.0-flash", "gemini-2.0-flash-lite",
                "gemini-2.5-flash", " gemini-2.5-flash-lite", "gemini-2.5-pro"
            ],
            "openai": ["gpt-4", "gpt-4.5", "gpt-4.1", "gpt-40", "gpt-3.5-turbo"]
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

    # --- Judging Mode ---
    st.write("### Judging Mode")
    judge_mode = st.radio(
        "How do you want to compare outputs?",
        ["Automatic (expected output present)", "Pairwise (no expected_output, human or LLM judge)"],
        index=0,
        help="If your CSVs have 'expected_output', use automatic metrics. If not, do pairwise comparison."
    )

    # --- File uploader ---
    st.write("### Upload LLM Outputs")
    uploaded_files = st.file_uploader(
        "Upload CSV files (one per model)",
        type="csv",
        accept_multiple_files=True,
        help="Each must have: 'question', 'expected_output', 'actual_output' for automatic; or just 'question', 'actual_output' for pairwise."
    )

    if not uploaded_files:
        st.info(" Please upload one or more model output CSVs to begin evaluation.")
        return

    # === PAIRWISE COMPARISON MODE ===
    if judge_mode.startswith("Pairwise"):
        # Only allow if exactly 2 files, and both have 'question' and 'actual_output', but NOT 'expected_output'
        if len(uploaded_files) != 2:
            st.warning("Please upload exactly 2 CSV files (one per model) for pairwise comparison.")
            return

        dfs = []
        model_names = []
        for file in uploaded_files:
            try:
                content = file.getvalue().decode("utf-8")
                df = pd.read_csv(StringIO(content))
            except UnicodeDecodeError:
                content = file.getvalue().decode("ISO-8859-1")
                df = pd.read_csv(StringIO(content))

            if not {"question", "actual_output"}.issubset(df.columns):
                st.error(f"{file.name} missing required columns: 'question', 'actual_output'")
                return

            if "expected_output" in df.columns:
                st.error(f"{file.name} should NOT have 'expected_output' for pairwise mode.")
                return

            model_names.append(file.name.replace(".csv", "").replace("_", "").replace("-", " ").title())
            dfs.append(df)

        # Merge on question
        merged = pd.merge(dfs[0], dfs[1], on="question", suffixes=(f" ({model_names[0]})", f" ({model_names[1]})"))
        st.write(f"#### Comparing: {model_names[0]} vs {model_names[1]}")

        judge_type = st.radio("Who should judge?", ["Human", "LLM"], horizontal=True)
        results = []

        if judge_type == "Human":
            st.info("Go through each question and pick the better output. You can download your votes at the end.")
            votes = []
            for idx, row in merged.iterrows():
                st.markdown(
                    f"<div style='margin-top: 2em; margin-bottom:0.5em; font-weight:bold; font-size:1.1em;'>Q{idx+1}: {row['question']}</div>",
                    unsafe_allow_html=True
                )
                st.markdown(
                    "<div style='margin-bottom:0.2em; color: #888;'>Select the better output below:</div>",
                    unsafe_allow_html=True
                )
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"<div style='font-weight:bold; color: #1a4;'> {model_names[0]} </div>", unsafe_allow_html=True)
                    st.markdown(
                        f"<div style='background: #f7f7fa; border-radius: 6px; padding:0.7em 1em; min-height:3em;'>{row[f'actual_output ({model_names[0]})']}</div>",
                        unsafe_allow_html=True
                    )
                with col2:
                    st.markdown(f"<div style='font-weight:bold; color:#14a;'> {model_names[1]} </div>", unsafe_allow_html=True)
                    st.markdown(
                        f"<div style='background: #f7f7fa; border-radius: 6px; padding:0.7em 1em; min-height: 3em;'>{row[f'actual_output ({model_names[1]})']}</div>",
                        unsafe_allow_html=True
                    )
                vote = st.radio("", [model_names[0], model_names[1], "Tie"], key=f"vote_{idx}", horizontal=True)
                votes.append(vote)

            merged["Winner"] = votes
            st.write("#### Results Table")
            st.dataframe(merged[["question", f"actual_output ({model_names[0]})", f"actual_output ({model_names[1]})", "Winner"]])

            # --- Vote summary ---
            st.markdown("### Vote Summary")
            vote_counts = merged["Winner"].value_counts()
            for name in [model_names[0], model_names[1], "Tie"]:
                st.write(f"{name}: {vote_counts.get(name, 0)} votes")

            st.download_button(
                "Download Pairwise Judging Results (CSV)",
                merged.to_csv(index=False),
                "pairwise_human_judging.csv",
                "text/csv"
            )
            return

        else:  # LLM judge
            st.info("The judge LLM will compare both outputs and pick a winner for each question.")
            if st.button(" Run LLM Judging", key="llm_judge_btn"):
                with st.spinner("LLM judging in progress..."):
                    results = []
                    for idx, row in merged.iterrows():
                        prompt = f"""
        You are an expert evaluator. Given a question and two model outputs, select which output is better. If both are equally good, say 'Tie'.

        Question: {row['question']}
        Output 1 ({model_names[0]}): {row[f'actual_output ({model_names[0]})']}
        Output 2 ({model_names[1]}): {row[f'actual_output ({model_names[1]})']}

        Respond with only one of: '{model_names[0]}', '{model_names[1]}', or 'Tie'.
                        """

                        try:
                            if provider == "gemini":
                                # Use the judge_model's a_generate (async) properly
                                import asyncio

                                async def get_gemini_judgment():
                                    return await judge_model.a_generate(prompt)

                                try:
                                    loop = asyncio.get_event_loop()
                                except RuntimeError:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)

                                response = loop.run_until_complete(get_gemini_judgment())
                                winner = response.strip() if isinstance(response, str) else str(response).strip()

                            else:  # OpenAI
                                resp = judge_model.client.chat.completions.create(
                                    model=model_name,
                                    messages=[{"role": "user", "content": prompt}],
                                    max_tokens=20
                                )
                                winner = resp.choices[0].message.content.strip()

                        except Exception as e:
                            winner = f"[ERROR] {str(e)[:50]}"

                        # Normalize winner
                        if model_names[0].lower() in winner.lower():
                            winner = model_names[0]
                        elif model_names[1].lower() in winner.lower():
                            winner = model_names[1]
                        elif "tie" in winner.lower():
                            winner = "Tie"
                        else:
                            winner = "Tie"  # Default fallback

                        results.append(winner)

                    merged["Winner"] = results
                    st.success("LLM judging complete!")
                    st.dataframe(merged[["question", f"actual_output ({model_names[0]})", f"actual_output ({model_names[1]})", "Winner"]])

                    # --- Vote summary ---
                    st.markdown("### Vote Summary")
                    vote_counts = merged["Winner"].value_counts()
                    for name in [model_names[0], model_names[1], "Tie"]:
                        st.write(f"{name}: {vote_counts.get(name, 0)} votes")

                    st.download_button(
                        "Download Pairwise LLM Judging Results (CSV)",
                        merged.to_csv(index=False),
                        "pairwise_llm_judging.csv",
                        "text/csv"
                    )

    # === AUTOMATIC METRICS MODE (expected_output present) ===
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
            st.warning(f" Skipping {file.name}: missing columns {missing}")
            continue

        total_questions += len(df)

    if total_questions == 0:
        st.error(" No valid data found.")
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
            "Fuzzy Value Similarity": fuzzy_value_similarity(expected, actual),
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

        # Execute all in thread pool (without Key Value Alignment)
        with ThreadPoolExecutor() as executor:
            loop = asyncio.get_event_loop()
            tasks = [
                loop.run_in_executor(executor, run_metric, "AnswerRelevancy", AnswerRelevancyMetric),
                loop.run_in_executor(executor, run_metric, "ContextPrecision", ContextualPrecisionMetric),
                loop.run_in_executor(executor, run_metric, "ContextRecall", ContextualRecallMetric),
                loop.run_in_executor(executor, run_geval),
            ]
            scores = await asyncio.gather(*tasks)

        keys = ["Answer Relevance", "Context Precision", "Context Recall", "G-Eval"]
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

                model_name_display = file.name.replace(".csv", "").replace("_", "").replace("-", " ").title()

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
            st.success(" Evaluation completed!")
        except Exception as e:
            st.error(f"Evaluation failed: {e}")
            return

    # Convert to DataFrame
    result_df = pd.DataFrame(all_data)
    numeric_metrics = [
        "Levenshtein Similarity", "Answer Relevance", "Context Precision",
        "Context Recall", "G-Eval", "Fuzzy Value Similarity"
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
    tab1, tab2, tab3, tab4 = st.tabs([" Leaderboard", " Per-Model Results", " Charts", " Compare Per Question"])

    with tab1:
        st.subheader(" Model Rankings")
        styled = leaderboard_df.style.format("{:.2f}", subset=numeric_metrics)
        for col in numeric_metrics:
            if col in leaderboard_df.columns and leaderboard_df[col].sum() > 0:
                styled = styled.background_gradient(cmap='Blues', subset=[col])
        st.dataframe(styled, width='stretch')

    with tab2:
        st.subheader(" Detailed Results by Model")
        for model in result_df["Model"].unique():
            model_data = result_df[result_df["Model"] == model][
                ["Question", "Expected Output", "Actual Output"] + numeric_metrics
            ]
            st.markdown(f"#### {model}")
            st.dataframe(model_data, height=300, width='stretch')

    with tab3:
        st.subheader(" Performance Comparison Across Models")
        melted = leaderboard_df.melt(id_vars=["Model"], var_name="Metric", value_name="Score")
        fig = px.bar(melted, x="Model", y="Score", color="Metric", barmode="group", title="Scores by Metric")
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Distribution of Scores")
        cols = st.columns(2)
        for i, metric in enumerate(numeric_metrics):
            if metric in result_df.columns:
                fig_hist = px.histogram(result_df, x=metric, color="Model", nbins=10, title=metric)
                fig_hist.update_layout(height=300)
                cols[i % 2].plotly_chart(fig_hist, use_container_width=True)

    with tab4:
        st.subheader(" Per-Question Winner Analysis")
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
                st.markdown("** Winners**")
                st.write(winner_counts)

    # Downloads
    st.download_button(
        "Download Full Results (Csv)",
        result_df.to_csv(index=False),
        "llm_evaluation_results.csv",
        "text/csv"
    )
    st.download_button(
        "Download Leaderboard (CSV)",
        leaderboard_df.to_csv(index=False),
        "llm_leaderboard.csv",
        "text/csv"
    )

    # Debug panel
    if show_debug:
        with st.expander("Debug Logs"):
            for msg in debug_logs:
                st.text(msg)