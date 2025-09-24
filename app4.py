# app7.py

# 1. Run Experiment: Generate outputs from LLMs
# 2. Compare Results: Evaluate and compare multiple models using semantic metrics

import streamlit as st

# Sets page title and layout
st.set_page_config(page_title="LLM Evaluator", layout="wide")

# Sidebar navigation to switch between experiment and comparison
page = st.sidebar.radio(" Navigate", [" Run Experiment", " Compare Results"])

# Loads and run the appropriate page based on selection
if page == " Run Experiment":
    from pages.Run_Experiment import run_experiment_page
    run_experiment_page()  # Runs inference on inputs
else:
    from pages.Compare_Results import compare_results_page
    compare_results_page()  # Compares model performance