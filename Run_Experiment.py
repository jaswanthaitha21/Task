# pages/1_🧪_Run_Experiment.py

import streamlit as st
import pandas as pd
import google.generativeai as genai
from openai import OpenAI
import os


def run_experiment_page():
    st.title("🧪 Run LLM Experiment")

    # --- Load Secrets ---
    try:
        GEMINI_API_KEY = st.secrets["gemini_api_key"]
        OPENAI_API_KEY = st.secrets["openai_api_key"]
    except Exception as e:
        st.error(f"❌ Missing API keys in `.streamlit/secrets.toml`: {e}")
        st.code('gemini_api_key = "your-key"\nopenai_api_key = "your-key"')
        return

    # --- Step 1: Select Provider & Model ---
    st.write("### 1. Select LLM Provider and Model")
    provider = st.selectbox("Provider", ["gemini", "openai"], format_func=str.capitalize)
    model_options = {
        "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.5-flash"],
        "openai": ["gpt-4o", "gpt-3.5-turbo"]
    }
    model_name = st.selectbox("Model", model_options[provider])

    api_key = GEMINI_API_KEY if provider == "gemini" else OPENAI_API_KEY

    # --- Step 2: Master Prompt with Dynamic Placeholders ---
    st.write("### 2. Enter Master Prompt")
    st.info("Use `{col_name}` to reference any column from your CSV.")
    master_prompt = st.text_area(
        "Prompt Template",
        "Answer the question:\n\n{input}",
        height=180
    )

    # --- Step 3: Upload CSV ---
    st.write("### 3. Upload Dataset CSV")
    uploaded_file = st.file_uploader("Upload CSV", type="csv", key="run_csv")

    if not uploaded_file:
        st.info("📤 Upload a CSV file to begin.")
        return

    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"❌ Failed to read CSV: {e}")
        return

    st.write("#### Input Data Preview")
    st.dataframe(df.head())

    # Extract column names for placeholder help
    cols = list(df.columns)
    st.info(f"Your columns: {', '.join([f'`{c}`' for c in cols])}. Use them like `{{input}}`, `{{{cols[0]}}}` etc.")

    # --- Step 4: Run Experiment ---
    if st.button("🚀 Run Experiment", key="run_exp"):
        with st.spinner("Generating responses..."):
            results = []

            # Initialize client
            try:
                if provider == "gemini":
                    genai.configure(api_key=api_key)
                    model = genai.GenerativeModel(model_name)
                else:
                    client = OpenAI(api_key=api_key)
            except Exception as e:
                st.error(f"❌ Failed to initialize {provider}: {e}")
                return

            for _, row in df.iterrows():
                # Render prompt using all available columns
                try:
                    rendered_prompt = master_prompt.format(**row.astype(str))
                except KeyError as e:
                    missing = str(e)
                    rendered_prompt = f"[ERROR: Missing column '{missing}' in prompt]"
                except Exception as e:
                    rendered_prompt = master_prompt + "\n\n" + str(row.iloc[0])

                # Call LLM
                actual = "[ERROR]"
                try:
                    if provider == "gemini":
                        response = model.generate_content(rendered_prompt)
                        actual = response.text
                    else:
                        resp = client.chat.completions.create(
                            model=model_name,
                            messages=[{"role": "user", "content": rendered_prompt}],
                            max_tokens=1024
                        )
                        actual = resp.choices[0].message.content
                except Exception as e:
                    actual = f"[ERROR] {str(e)[:200]}"

                # Build result row
                result_row = row.to_dict()
                result_row["actual_output"] = actual
                results.append(result_row)

            # Save to session
            result_df = pd.DataFrame(results)
            st.session_state.experiment_result = result_df

            st.success("✅ Generation Complete!")

    # --- Display & Download Results ---
    if "experiment_result" in st.session_state:
        result_df = st.session_state.experiment_result
        st.write("### ✅ Generated Output with `actual_output`")
        st.dataframe(result_df, use_container_width=True)

        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Download Results (CSV)",
            csv,
            "experiment_results_with_actuals.csv",
            "text/csv"
        )