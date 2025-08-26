import streamlit as st
import fitz  # PyMuPDF for PDF reading
import google.generativeai as genai
import re
import pandas as pd
import matplotlib.pyplot as plt
import json
from typing import Dict, Optional, Tuple

# ---------------------------
# Configure Gemini API
# ---------------------------
genai.configure(api_key="AIzaSyDUvKi1lkLKUPrqZd9Xe1YhKgXs2o3qGOY")
model = genai.GenerativeModel("gemini-1.5-flash")

# ---------------------------
# Comprehensive Policy Attributes
# ---------------------------
POLICY_ATTRIBUTES = [
    "Sum Insured",
    "Premium Amount",
    "Waiting Period",
    "Pre-Hospitalization Coverage",
    "Post-Hospitalization Coverage",
    "Room Rent Coverage",
    "ICU Charges Coverage",
    "Co-Pay Clause",
    "Sub-Limits on Treatments",
    "Claim Settlement Ratio",
    "Network Hospitals",
    "Cashless Claim Process",
    "Exclusions",
    "Maternity Coverage",
    "AYUSH Treatment Coverage",
    "Daycare Procedures Covered",
    "No Claim Bonus",
    "Restoration of Sum Insured",
    "Critical Illness Coverage",
    "Health Checkup Coverage"
]

# ---------------------------
# Helper Functions
# ---------------------------
def extract_text_from_pdf(uploaded_file):
    """Extract text from uploaded PDF using PyMuPDF"""
    text = ""
    pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in pdf:
        text += page.get_text()
    return text

def gemini_generate(prompt):
    """Call Gemini API and return response text"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def safe_float(num_str: str) -> Optional[float]:
    """Safely convert string to float"""
    if not num_str:
        return None
    s = re.sub(r"[^\d.-]", "", num_str.split()[0]) if num_str else ""
    try:
        return float(s)
    except ValueError:
        return None

def normalize_policy_name(text: str, fallback: str) -> str:
    """Extract likely policy name from first few lines"""
    if not text:
        return fallback
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:20]
    for ln in lines:
        if len(ln) > 8 and re.search(r"(policy|plan|insurance|health|mediclaim)", ln, re.I):
            if not re.search(r"table of contents|index|disclaimer", ln, re.I):
                return ln[:120]
    return lines[0][:120] if lines else fallback

def extract_attribute_regex(text: str, attr: str) -> Optional[str]:
    """Extract attribute using predefined regex patterns"""
    patterns = {
        "Sum Insured": [
            r"sum\s*insured[:\-]?\s*₹?\s*([0-9][0-9,\.]*)\s*(lakh|lac|crore|cr)?",
            r"cover\s*amount[:\-]?\s*₹?\s*([0-9][0-9,\.]*)"
        ],
        "Premium Amount": [
            r"premium[:\-]?\s*₹?\s*([0-9][0-9,\.]+)",
            r"annual\s*cost[:\-]?\s*₹?\s*([0-9][0-9,\.]+)"
        ],
        "Waiting Period": [
            r"waiting\s*period[:\-]?\s*([0-9]+)\s*(days?|months?)",
            r"initial\s*exclusion\s*period[:\-]?\s*([0-9]+)\s*(days?|months?)"
        ],
        "Pre-Hospitalization Coverage": [
            r"pre[-\s]*hospitalization[:\-]?\s*([0-9]+)\s*days?",
        ],
        "Post-Hospitalization Coverage": [
            r"post[-\s]*hospitalization[:\-]?\s*([0-9]+)\s*days?",
        ],
        "Room Rent Coverage": [
            r"room\s*rent[:\-]?\s*(up to [0-9]+%|capped at|no restriction|as per actual|unlimited)",
        ],
        "ICU Charges Coverage": [
            r"icu\s*charges?[:\-]?\s*(covered|up to [0-9]+%|included|subject to limit)",
        ],
        "Co-Pay Clause": [
            r"co[-\s]*pay[:\-]?\s*([0-9]+%|applicable|mandatory|yes|no)",
            r"copayment[:\-]?\s*(yes|no|[0-9]+%)"
        ],
        "Sub-Limits on Treatments": [
            r"sub[-\s]*limit[:\-]?\s*(yes|no|applicable|subject to cap)",
        ],
        "Claim Settlement Ratio": [
            r"claim\s*settlement\s*ratio[:\-]?\s*([0-9]{1,3}(?:\.[0-9]+)?)%",
            r"incurred\s*claim\s*ratio[:\-]?\s*([0-9]{1,3}(?:\.[0-9]+)?)%"
        ],
        "Network Hospitals": [
            r"network\s*hospitals?[:\-]?\s*([0-9,]+)",
            r"cashless\s*hospitals?[:\-]?\s*([0-9,]+)"
        ],
        "Maternity Coverage": [
            r"maternity[:\-]?\s*(covered|yes|up to [0-9]+ days|not covered|excluded)",
        ],
        "AYUSH Treatment Coverage": [
            r"ayush[:\-]?\s*(covered|yes|included|not covered)",
        ],
        "Daycare Procedures Covered": [
            r"daycare\s*procedures?[:\-]?\s*(yes|covered|[0-9]+ listed)",
        ],
        "No Claim Bonus": [
            r"no\s*claim\s*bonus[:\-]?\s*(yes|up to [0-9]+%|available)",
        ],
        "Restoration of Sum Insured": [
            r"restoration\s*of\s*sum\s*insured[:\-]?\s*(yes|once|multiple times|not available)",
        ],
        "Critical Illness Coverage": [
            r"critical\s*illness[:\-]?\s*(covered|yes|sum insured|not covered)",
        ],
        "Health Checkup Coverage": [
            r"health\s*checkup[:\-]?\s*(covered|yes|annual|once a year)",
        ],
        "Cashless Claim Process": [
            r"cashless\s*claim[:\-]?\s*(reimbursement|TPA|process.*details)",
        ],
        "Exclusions": [
            r"exclusions[:\-]?\s*(\w.*){10,50}",
        ],
    }

    if attr not in patterns:
        return None

    for pat in patterns[attr]:
        m = re.search(pat, text, re.I)
        if m:
            return " ".join(filter(None, m.groups())).strip()
    return None

def get_all_policy_metrics(policy_name: str, text: str) -> Dict[str, Optional[str]]:
    """Extract all policy attributes using regex + Gemini fallback"""
    results = {}
    for attr in POLICY_ATTRIBUTES:
        val = extract_attribute_regex(text, attr)
        if not val or len(val) < 3 or "error" in val.lower():
            # Fallback to Gemini
            prompt = f"""
            From this insurance policy document, extract the value for: '{attr}'.
            If not found, say 'Not specified'. Keep it short and clear.
            Answer in one line.

            Policy Text (excerpt):
            {text[:8000]}
            """
            try:
                val = gemini_generate(prompt)
                if len(val) > 150 or "sorry" in val.lower() or "cannot" in val.lower():
                    val = "Not specified"
            except:
                val = "Not specified"
        results[attr] = val if val else "Not specified"
    return results

def to_number_for_plot(value: Optional[str], metric: str) -> Optional[float]:
    """Convert text value to number for plotting"""
    if not value or value == "Not specified":
        return None
    v = str(value).strip()

    if metric == "Sum Insured":
        m = re.search(r"([0-9][0-9,\.]*)\s*(lakh|lac)?", v, re.I)
        if m:
            num = safe_float(m.group(1))
            if num is None:
                return None
            unit = (m.group(2) or "").lower()
            if unit in ["lakh", "lac"]:
                return float(num)
            return num / 100000.0  # Convert ₹ to Lakh
    elif metric == "Waiting Period":
        m = re.search(r"([0-9]{1,4})\s*days?", v, re.I)
        if m:
            return float(m.group(1))
        m = re.search(r"([0-9]{1,3})\s*months?", v, re.I)
        if m:
            return float(m.group(1)) * 30.0
    elif metric in ["Pre-Hospitalization Coverage", "Post-Hospitalization Coverage"]:
        m = re.search(r"([0-9]{1,3})", v)
        if m:
            return float(m.group(1))
    elif metric == "Claim Settlement Ratio":
        m = re.search(r"([0-9]{1,3}(?:\.[0-9]+)?)\s*%", v)
        if m:
            return float(m.group(1))
    elif metric == "Network Hospitals":
        m = re.search(r"([0-9,]+)", v)
        if m:
            return float(m.group(1).replace(",", ""))
    elif metric == "No Claim Bonus":
        m = re.search(r"([0-9]{1,3})%", v)
        if m:
            return float(m.group(1))
    elif metric == "Premium Amount":
        m = re.search(r"₹?\s*([0-9,\.]+)", v)
        if m:
            return safe_float(m.group(1))
    return None

# ---------------------------
# Streamlit UI Setup
# ---------------------------
st.set_page_config(page_title="Insurance Policy Comparator", layout="wide")
st.title("📄 Insurance Policy Comparator")
st.markdown("Upload two insurance policy PDFs to compare coverage, benefits, and key terms.")

# Initialize session state
session_keys = [
    "text1", "text2", "summary1", "summary2",
    "policy1_name", "policy2_name",
    "full_comparison", "metrics_df",
    "qa_mode", "qa_history"
]
for key in session_keys:
    if key not in st.session_state:
        st.session_state[key] = None if key not in ["qa_mode", "qa_history"] else (False if key == "qa_mode" else [])

# File Upload
col1, col2 = st.columns(2)
with col1:
    pdf1 = st.file_uploader("Upload Policy Document 1", type="pdf", key="pdf1")
with col2:
    pdf2 = st.file_uploader("Upload Policy Document 2", type="pdf", key="pdf2")

if pdf1 and pdf2:
    if st.button("🔍 Generate Summaries"):
        with st.spinner("Extracting text and generating summaries..."):
            st.session_state.text1 = extract_text_from_pdf(pdf1)
            st.session_state.text2 = extract_text_from_pdf(pdf2)

            st.session_state.policy1_name = normalize_policy_name(st.session_state.text1, "Policy 1")
            st.session_state.policy2_name = normalize_policy_name(st.session_state.text2, "Policy 2")

            st.session_state.summary1 = gemini_generate(
                f"Summarize this insurance policy in a structured paragraph style: {st.session_state.text1[:15000]}"
            )
            st.session_state.summary2 = gemini_generate(
                f"Summarize this insurance policy in a structured paragraph style: {st.session_state.text2[:15000]}"
            )

            # Reset comparison and QA
            st.session_state.full_comparison = None
            st.session_state.metrics_df = None
            st.session_state.qa_history = []

    if st.session_state.summary1 and st.session_state.summary2:
        st.subheader("📌 Policy Summaries")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"### {st.session_state.policy1_name}")
            st.write(st.session_state.summary1)
        with col2:
            st.markdown(f"### {st.session_state.policy2_name}")
            st.write(st.session_state.summary2)

        # ---------------------------
        # Full Policy Comparison Table
        # ---------------------------
        if st.button("📊 Compare All Attributes") or st.session_state.full_comparison is not None:
            if st.session_state.full_comparison is None:
                with st.spinner("Extracting all policy details using AI..."):
                    m1 = get_all_policy_metrics(st.session_state.policy1_name, st.session_state.text1)
                    m2 = get_all_policy_metrics(st.session_state.policy2_name, st.session_state.text2)

                    comparison_data = []
                    for attr in POLICY_ATTRIBUTES:
                        comparison_data.append({
                            "Attribute": attr,
                            st.session_state.policy1_name: m1.get(attr, "Not specified"),
                            st.session_state.policy2_name: m2.get(attr, "Not specified")
                        })
                    st.session_state.full_comparison = pd.DataFrame(comparison_data)
                    st.session_state.metrics_df = pd.DataFrame([
                        {"Policy": st.session_state.policy1_name, **m1},
                        {"Policy": st.session_state.policy2_name, **m2}
                    ])

            st.subheader("📋 Full Policy Comparison")
            st.dataframe(st.session_state.full_comparison, use_container_width=True)

            # Export Button
            @st.cache_data
            def convert_df_to_csv(df):
                return df.to_csv(index=False).encode('utf-8')

            csv = convert_df_to_csv(st.session_state.full_comparison)
            st.download_button("📥 Download Comparison as CSV", csv, "policy_comparison.csv", "text/csv")

            # ---------------------------
            # Visualizations
            # ---------------------------
            st.subheader("📈 Visual Comparison of Key Metrics")

            NUMERIC_ATTRIBUTES = [
                "Sum Insured",
                "Waiting Period",
                "Pre-Hospitalization Coverage",
                "Post-Hospitalization Coverage",
                "Claim Settlement Ratio",
                "Network Hospitals",
                "No Claim Bonus",
                "Premium Amount"
            ]

            available_attrs = [a for a in NUMERIC_ATTRIBUTES if a in st.session_state.metrics_df.columns]
            if not available_attrs:
                st.info("No numeric attributes available for visualization.")
            else:
                selected_attr = st.selectbox("Select a metric to visualize:", options=available_attrs)

                df = st.session_state.metrics_df[["Policy", selected_attr]].copy()
                df["Value"] = df[selected_attr].apply(lambda x: to_number_for_plot(x, selected_attr))

                if df["Value"].isna().all():
                    st.warning(f"Could not extract numeric data for '{selected_attr}'.")
                else:
                    fig, ax = plt.subplots(figsize=(6, 4))
                    bars = ax.bar(df["Policy"], df["Value"], color=['#4CAF50', '#2196F3'], alpha=0.8)

                    for bar, val in zip(bars, df["Value"]):
                        if not pd.isna(val):
                            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + bar.get_height() * 0.02,
                                    f"{val:g}", ha='center', va='bottom', fontweight='bold')

                    ylabel_map = {
                        "Sum Insured": "Sum Insured (in Lakh ₹)",
                        "Waiting Period": "Waiting Period (Days)",
                        "Pre-Hospitalization Coverage": "Days",
                        "Post-Hospitalization Coverage": "Days",
                        "Claim Settlement Ratio": "Ratio (%)",
                        "Network Hospitals": "Number",
                        "No Claim Bonus": "Bonus (%)",
                        "Premium Amount": "Amount (₹)"
                    }
                    ax.set_ylabel(ylabel_map.get(selected_attr, "Value"))
                    ax.set_title(f"{selected_attr} Comparison")
                    ax.grid(axis='y', linestyle='--', alpha=0.5)
                    st.pyplot(fig)

        # ---------------------------
        # Q&A with Gemini
        # ---------------------------
        st.subheader("💬 Ask About These Policies")
        if st.button("🗨️ Start Q&A with AI"):
            st.session_state.qa_mode = True

        if st.session_state.qa_mode:
            with st.form("qa_form", clear_on_submit=True):
                user_q = st.text_input(
                    "Ask a question about the policies:",
                    placeholder="E.g., Which policy has better maternity coverage?"
                )
                submitted = st.form_submit_button("Ask Gemini")

            if submitted and user_q.strip():
                with st.spinner("Getting AI response..."):
                    prompt = f"""
                    You are an expert in health insurance. Compare or analyze based on the following.

                    Policy 1 ({st.session_state.policy1_name}):
                    {st.session_state.text1[:8000]}

                    Policy 2 ({st.session_state.policy2_name}):
                    {st.session_state.text2[:8000]}

                    Question:
                    {user_q}

                    Answer clearly and concisely.
                    """
                    ans = gemini_generate(prompt)
                    st.session_state.qa_history.append((user_q, ans))

            # Display Q&A history
            for i, (q, a) in enumerate(reversed(st.session_state.qa_history), 1):
                st.markdown(f"**Q{i}: {q}**")
                st.markdown(f"> **A:** {a}")
                st.divider()