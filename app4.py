# app.py

# Streamlit is used for building interactive web apps in Python
# This file sets up navigation between two key pages:
# 1. Run Experiment: Generate outputs from LLMs
# 2. Compare Results: Evaluate and compare multiple models using semantic metrics

import streamlit as st

# Set page title and layout
st.set_page_config(page_title="Opik-like LLM Evaluator", layout="wide")

# Sidebar navigation to switch between experiment and comparison
page = st.sidebar.radio("🧭 Navigate", ["🧪 Run Experiment", "📊 Compare Results"])

# Load and run the appropriate page based on selection
if page == "🧪 Run Experiment":
    from pages.Run_Experiment import run_experiment_page
    run_experiment_page()  # Runs inference on inputs
else:
    from pages.Compare_Results import compare_results_page
    compare_results_page()  # Compares model performance