# app.py
import streamlit as st

# Page navigation
st.set_page_config(page_title="Opik-like LLM Evaluator", layout="wide")
page = st.sidebar.radio("🧭 Navigate", ["🧪 Run Experiment", "📊 Compare Results"])

if page == "🧪 Run Experiment":
    from pages.Run_Experiment import run_experiment_page
    run_experiment_page()
else:
    from pages.Compare_Results import compare_results_page
    compare_results_page()