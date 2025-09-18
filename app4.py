# app.py
import streamlit as st

# Simple navigation
page = st.sidebar.radio("🧭 Navigate", ["🧪 Run LLM Experiment", "📊 Compare LLM Results"])

if page == "🧪 Run LLM Experiment":
    from pages.Run_Experiment import run_experiment_page
    run_experiment_page()
else:
    from pages.Compare_Results import compare_results_page
    compare_results_page()