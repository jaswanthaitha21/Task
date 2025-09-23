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
        "gemini": ["gemini-1.5-pro", "gemini-1.5-flash"],
        "openai": ["gpt-4o", "gpt-3.5-turbo"]
    }
    model_name = st.selectbox("Model", model_options[provider])
    api_key = GEMINI_API_KEY if provider == "gemini" else OPENAI_API_KEY

    # --- Step 2: Master Prompt with Placeholders ---
    st.write("### 2. Enter Master Prompt")
    st.info("Use `{col_name}` to reference any column from your CSV.")
    master_prompt = st.text_area(
        "Prompt Template",
        "Classify the sentiment of this text as POSITIVE, NEUTRAL, or NEGATIVE:\n\n{input}",
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

    cols = list(df.columns)
    st.info(f"Available columns: {', '.join([f'`{c}`' for c in cols])}")

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
                result_row = row.to_dict()

                # Render prompt using all available columns
                try:
                    rendered_prompt = master_prompt.format(**row.astype(str))
                except KeyError as e:
                    st.warning(f"⚠️ Column {e} not found in data. Using fallback prompt.")
                    rendered_prompt = master_prompt + "\n\n" + str(row.iloc[0])
                except Exception:
                    rendered_prompt = master_prompt + "\n\n" + str(row.iloc[0])

                actual = "[ERROR]"
                try:
                    # Check if any cell looks like an image path and exists
                    image_path = None
                    for col_val in row.astype(str):
                        val = col_val.strip()
                        if val.lower().endswith(('.png', '.jpg', '.jpeg', '.webp', '.bmp')) and os.path.exists(val):
                            image_path = val
                            break

                    if image_path and provider == "gemini":
                        # Multimodal: image + prompt
                        with open(image_path, "rb") as img_file:
                            image_data = img_file.read()
                        response = model.generate_content([
                            rendered_prompt,
                            {"mime_type": "image/jpeg", "data": image_data}
                        ])
                        actual = response.text
                    else:
                        # Text-only input
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

                result_row["actual_output"] = actual
                results.append(result_row)

            result_df = pd.DataFrame(results)
            st.session_state.experiment_result = result_df

            st.success("✅ Generation Complete!")
            st.balloons()

    # --- Display & Download Results ---
    if "experiment_result" in st.session_state:
        result_df = st.session_state.experiment_result
        st.write("### ✅ Generated Output with `actual_output`")
        st.dataframe(result_df, use_container_width=True)

        csv = result_df.to_csv(index=False).encode("utf-8")
        original_name = os.path.splitext(uploaded_file.name)[0]
        dynamic_filename = f"{model_name}_{original_name}.csv"

        st.download_button(
            "⬇️ Download Results (CSV)",
            csv,
            dynamic_filename,
            "text/csv"
        )