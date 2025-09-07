import streamlit as st
import fitz  # PyMuPDF
import google.generativeai as genai
import re
import pandas as pd
import matplotlib.pyplot as plt
from typing import Dict, Optional

# -------------------------------
# Configure Gemini API
# -------------------------------
GOOGLE_API_KEY = ""  # Replace with your key
try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")  # Efficient & higher free quota
except Exception as e:
    st.error(f"Failed to configure Gemini API: {e}")
    st.stop()

# -------------------------------
# Comprehensive Policy Attributes
# -------------------------------
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


# -------------------------------
# Helper Functions
# -------------------------------

def extract_text_from_pdf_type(data):
    """Extract text from bytes or file-like object (reusable)"""
    try:
        pdf = fitz.open(stream=data, filetype="pdf")
        text = ""
        for page in pdf:
            text += page.get_text()
        pdf.close()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""


def extract_text_from_pdf(uploaded_file):
    """Extract text from uploaded PDF using PyMuPDF (safe for Streamlit re-use)"""
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)
    data = uploaded_file.read()
    return extract_text_from_pdf_type(data)


def gemini_generate(prompt):
    """Call Gemini API with graceful 429 handling"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        if "429" in str(e):
            return "Not specified (quota exceeded - try later)"
        return "Not specified"


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
            r"sum\s*insured[:\-]?\s*₹?\s*([0-9,\.]+)\s*(lakh|lac|crore|cr)?",
            r"cover\s*amount[:\-]?\s*₹?\s*([0-9,\.]+)",
            r"sum\s*insured.*?([0-9,\.]+)\s*(lakh|crore|₹)",
            r"insured.*?₹?\s*([0-9,\.]+)"
        ],
        "Premium Amount": [
            r"premium[:\-]?\s*₹?\s*([0-9,\.]+)",
            r"annual\s*cost[:\-]?\s*₹?\s*([0-9,\.]+)",
            r"₹?\s*([0-9,\.]+)\s*per\s*year",
            r"cost.*?₹\s*([0-9,\.]+)"
        ],
        "Waiting Period": [
            r"waiting\s*period.*?([0-9]+)\s*days?",
            r"initial\s*waiting\s*period.*?([0-9]+)",
            r"waiting\s*period[:\-]?\s*([0-9]+)\s*days?",
            r"waiting period.*?([0-9]+)\s*year"
        ],
        "Pre-Hospitalization Coverage": [
            r"pre[-\s]hospitalization.*?([0-9]+)\s*days?",
            r"pre[-\s]hospitalization[:\-]?\s*([0-9]+)"
        ],
        "Post-Hospitalization Coverage": [
            r"post[-\s]hospitalization.*?([0-9]+)\s*days?",
            r"post[-\s]hospitalization[:\-]?\s*([0-9]+)"
        ],
        "Room Rent Coverage": [
            r"room\s*rent[:\-]?\s*(up to [0-9]+%|capped at|no restriction|as per actual|unlimited|covered fully)",
            r"room.*?([0-9]+%)"
        ],
        "ICU Charges Coverage": [
            r"icu\s*charges?[:\-]?\s*(covered|fully|included|no cap|without separate cap)",
            r"icu.*?covered"
        ],
        "Co-Pay Clause": [
            r"co[-\s]pay[:\-]?\s*([0-9]+%|applicable|mandatory|yes|no)",
            r"copayment[:\-]?\s*(yes|no|[0-9]+%)",
            r"co[-\s]payment.*?([0-9]+%)"
        ],
        "Sub-Limits on Treatments": [
            r"sub[-\s]limit[:\-]?\s*(yes|no|applicable|subject to cap)",
            r"sub[-\s]limit"
        ],
        "Claim Settlement Ratio": [
            r"claim\s*settlement\s*ratio[:\-]?\s*([0-9]{1,3}(?:\.[0-9]+)?)%",
            r"incurred\s*claim\s*ratio[:\-]?\s*([0-9]{1,3}(?:\.[0-9]+)?)%"
        ],
        "Network Hospitals": [
            r"network\s*hospitals?[:\-]?\s*([0-9,]+)",
            r"([0-9,]+)\s+network\s*hospitals",
            r"over\s*([0-9,]+)",
            r"([0-9,]+)\+?\s*(?:network|cashless)",
            r"cashless\s*hospitals?[:\-]?\s*([0-9,]+)"
        ],
        "Cashless Claim Process": [
            r"cashless\s*claim[:\-]?\s*(reimbursement|TPA process|details|within \d+ hours)",
            r"approval.*?within.*?(\d+)\s*hours"
        ],
        "Exclusions": [
            r"exclusions[:\-]?\s*(.*)"
        ],
        "Maternity Coverage": [
            r"maternity.*?waiting.*?([0-9]+)\s*years?",
            r"maternity[:\-]?\s*(covered|yes|up to [0-9]+ days|not covered|excluded|available as add-on)",
            r"waiting period.*?maternity.*?([0-9]+)\s*years?"
        ],
        "AYUSH Treatment Coverage": [
            r"ayush[:\-]?\s*(covered|yes|included|not covered)",
            r"ayush.*?(covered|approved centers)"
        ],
        "Daycare Procedures Covered": [
            r"daycare\s*procedures?[:\-]?\s*(yes|covered|[0-9]+ listed|[0-9]+\+)",
            r"([0-9]+)\+\s*daycare"
        ],
        "No Claim Bonus": [
            r"no\s*claim\s*bonus[:\-]?\s*(yes|up to [0-9]+%|available)",
            r"ncb.*?([0-9]+%)"
        ],
        "Restoration of Sum Insured": [
            r"restoration\s*of\s*sum\s*insured[:\-]?\s*(yes|once|multiple times|not available)",
            r"restoration.*?(once|yes)"
        ],
        "Critical Illness Coverage": [
            r"critical\s*illness[:\-]?\s*(covered|yes|sum insured|not covered)",
            r"critical.*?illness.*?(covered)"
        ],
        "Health Checkup Coverage": [
            r"health\s*checkup[:\-]?\s*(covered|yes|annual|once a year|up to ₹[0-9,]+)",
            r"checkup.*?(covered)"
        ]
    }

    if attr not in patterns:
        return None

    for pat in patterns[attr]:
        m = re.search(pat, text, re.I)
        if m:
            return "".join(m.groups()).strip()
    return None


def get_all_policy_metrics(policy_name: str, text: str) -> Dict[str, Optional[str]]:
    """Extract all attributes using regex first, then ONE Gemini fallback for missing ones"""
    results = {}

    # Step 1: Extract with regex
    for attr in POLICY_ATTRIBUTES:
        val = extract_attribute_regex(text, attr)
        if val and len(val.strip()) >= 3 and "error" not in val.lower():
            results[attr] = val.strip()
        else:
            results[attr] = "Not specified"

    # Step 2: Find missing fields
    missing_attrs = [attr for attr, val in results.items() if val == "Not specified"]
    if not missing_attrs:
        return results  # All done!

    # Step 3: Single Gemini call to fill missing values
    prompt = f"""
    You are an expert insurance analyst. Extract the following fields from the policy document:
    {', '.join(missing_attrs)}

    Return in this format:
    - Sum Insured: value
    - Premium Amount: value
    ... (one per line)

    If not found, write 'Not specified'.

    Policy Text (excerpt):
    {text[:12000]}

    Extracted values:
    """

    try:
        response = model.generate_content(prompt)
        gemini_text = response.text.strip()
    except Exception as e:
        st.warning(f"Gemini fallback failed: {str(e)}")
        return results  # Return regex-only results

    # Parse response
    for line in gemini_text.splitlines():
        for attr in missing_attrs:
            if attr.lower() in line.lower() or line.strip().startswith(f"{attr}:"):
                if ":" in line:
                    val = line.split(":", 1)[1].strip()
                    results[attr] = val if val else "Not specified"
                break

    return results


def to_number_for_plot(value: Optional[str], metric: str) -> Optional[float]:
    """Convert text value to number for plotting — robust version"""
    if not value or value == "Not specified" or "quota exceeded" in str(value).lower():
        return None
    v = str(value).strip()

    # Clean up for number extraction
    v_alpha = re.sub(r"[^\w\s.%]", "", v.lower())

    try:
        if metric == "Sum Insured":
            lakh_match = re.search(r"([0-9]+\.?[0-9]*)\s*lakh?", v_alpha)
            if lakh_match:
                return float(lakh_match.group(1))
            crore_match = re.search(r"([0-9]+\.?[0-9]*)\s*crore", v_alpha)
            if crore_match:
                return float(crore_match.group(1)) * 100
            num_match = re.search(r"([0-9,\.]+)", v.replace("₹", ""))
            if num_match:
                num = safe_float(num_match.group(1))
                return num / 100000.0 if num else None
            return None

        elif metric == "Premium Amount":
            num_match = re.search(r"₹?\s*([0-9,\.]+)", v)
            if num_match:
                return safe_float(num_match.group(1))
            return None

        elif metric == "Waiting Period":
            day_match = re.search(r"([0-9]+)\s*day", v_alpha)
            if day_match:
                return float(day_match.group(1))
            month_match = re.search(r"([0-9]+)\s*month", v_alpha)
            if month_match:
                return float(month_match.group(1)) * 30
            year_match = re.search(r"([0-9]+)\s*year", v_alpha)
            if year_match:
                return float(year_match.group(1)) * 365
            return None

        elif metric in ["Pre-Hospitalization Coverage", "Post-Hospitalization Coverage"]:
            day_match = re.search(r"([0-9]{1,3})", v)
            if day_match:
                return float(day_match.group(1))
            return None

        elif metric == "Claim Settlement Ratio":
            perc_match = re.search(r"([0-9]{1,3}(?:\.[0-9]+)?)\s*%", v)
            if perc_match:
                return float(perc_match.group(1))
            return None

        elif metric == "Network Hospitals":
            num_match = re.search(r"([0-9,]+)", v)
            if num_match:
                return float(num_match.group(1).replace(",", ""))
            return None

        elif metric == "No Claim Bonus":
            perc_match = re.search(r"([0-9]{1,3})%", v)
            if perc_match:
                return float(perc_match.group(1))
            return None

        else:
            # Generic number fallback
            num_match = re.search(r"([0-9]+\.?[0-9]*)", v)
            if num_match:
                return float(num_match.group(1))
            return None

    except Exception:
        return None


# -------------------------------
# Streamlit UI Setup
# -------------------------------
st.set_page_config(page_title="Insurance Policy Comparator", layout="wide")
st.title("🩺 Insurance Policy Comparator")
st.markdown("Upload two insurance policy PDFs to compare coverage, benefits, and key terms.")

# Initialize session state
session_keys = [
    "text1", "text2", "summary1", "summary2",
    "policy1_name", "policy2_name",
    "full_comparison", "metrics_df",
    "qa_mode", "qa_history",
    "pdf1_bytes", "pdf2_bytes"
]
for key in session_keys:
    if key not in st.session_state:
        st.session_state[key] = None
if "qa_mode" not in st.session_state:
    st.session_state.qa_mode = False
if "qa_history" not in st.session_state:
    st.session_state.qa_history = []

# File Upload
col1, col2 = st.columns(2)
with col1:
    pdf1 = st.file_uploader("Upload Policy Document 1", type="pdf", key="pdf1")
with col2:
    pdf2 = st.file_uploader("Upload Policy Document 2", type="pdf", key="pdf2")

# Extract and summarize
if pdf1 and pdf2:
    if st.button("🔍 Generate Summaries"):
        with st.spinner("Extracting text and generating summaries..."):
            # Store raw bytes
            pdf1.seek(0)
            st.session_state.pdf1_bytes = pdf1.read()
            pdf2.seek(0)
            st.session_state.pdf2_bytes = pdf2.read()

            # Extract text
            st.session_state.text1 = extract_text_from_pdf_type(st.session_state.pdf1_bytes)
            st.session_state.text2 = extract_text_from_pdf_type(st.session_state.pdf2_bytes)

            # Debug: Show lengths
            st.write(f"📄 Policy 1 Length: {len(st.session_state.text1):,} chars")
            st.write(f"📄 Policy 2 Length: {len(st.session_state.text2):,} chars")

            st.session_state.policy1_name = normalize_policy_name(st.session_state.text1, "Policy 1")
            st.session_state.policy2_name = normalize_policy_name(st.session_state.text2, "Policy 2")

            st.session_state.summary1 = gemini_generate(
                f"Summarize this insurance policy in a structured paragraph: {st.session_state.text1[:15000]}"
            )
            st.session_state.summary2 = gemini_generate(
                f"Summarize this insurance policy in a structured paragraph: {st.session_state.text2[:15000]}"
            )

            # Reset comparison
            st.session_state.full_comparison = None
            st.session_state.metrics_df = None
            st.session_state.qa_history = []

    # Show summaries
    if st.session_state.summary1 and st.session_state.summary2:
        st.subheader("📄 Policy Summaries")
        col1_summary, col2_summary = st.columns(2)
        with col1_summary:
            st.markdown(f"### {st.session_state.policy1_name}")
            st.write(st.session_state.summary1)
        with col2_summary:
            st.markdown(f"### {st.session_state.policy2_name}")
            st.write(st.session_state.summary2)

        # Full Comparison
        if st.button("📊 Compare All Attributes") or st.session_state.full_comparison is not None:
            if st.session_state.full_comparison is None:
                with st.spinner("Extracting policy details (smart mode)..."):
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


            # Export
            @st.cache_data
            def convert_df_to_csv(df):
                return df.to_csv(index=False).encode('utf-8')


            csv = convert_df_to_csv(st.session_state.full_comparison)
            st.download_button("📥 Download as CSV", csv, "policy_comparison.csv", "text/csv")

        # Visualizations
        st.subheader("📈 Visual Comparison of Key Metrics")
        if st.session_state.metrics_df is None:
            st.info("Click 'Compare All Attributes' to generate visualizations.")
        else:
            NUMERIC_ATTRIBUTES = [
                "Sum Insured", "Premium Amount", "Waiting Period",
                "Pre-Hospitalization Coverage", "Post-Hospitalization Coverage",
                "Claim Settlement Ratio", "Network Hospitals", "No Claim Bonus"
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

        # Q&A
        st.subheader("❓ Ask About These Policies")
        if st.button("💬 Start Q&A with AI"):
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