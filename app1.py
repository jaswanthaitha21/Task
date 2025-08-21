import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import matplotlib.pyplot as plt
import google.generativeai as genai
import re
import json
from typing import Dict, Optional, Tuple

# ---------------------------
# Configure Gemini API
# ---------------------------
genai.configure(api_key="Give_your_own_api_key")
model = genai.GenerativeModel("gemini-2.5-flash")

# ---------------------------
# Helper Functions
# ---------------------------
def extract_text_from_pdf(uploaded_file):
    text = ""
    pdf = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    for page in pdf:
        text += page.get_text()
    return text

def gemini_generate(prompt):
    response = model.generate_content(prompt)
    return response.text

def safe_float(num_str: str) -> Optional[float]:
    if num_str is None:
        return None
    s = num_str.replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        return None

def normalize_policy_name(text: str, fallback: str) -> str:
    if not text:
        return fallback
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()][:20]
    for ln in lines:
        if len(ln) > 8 and re.search(r"(policy|plan|insurance|health|mediclaim)", ln, re.I):
            if not re.search(r"table of contents|index|disclaimer", ln, re.I):
                return ln[:120]
    if lines:
        return lines[0][:120]
    return fallback

# ---------------------------
# Metric Extraction
# ---------------------------
SUM_INSURED_PATTERNS = [
    r"(sum\s*insured|insured\s*sum|coverage\s*amount|cover\s*amount|insured\s*amount)\s*[:\-]?\s*₹?\s*([0-9][0-9,\.]*)\s*(lakh|lac|crore|cr)?",
    r"₹\s*([0-9][0-9,\.]*)\s*(lakh|lac|crore|cr)?\s*(sum\s*insured|coverage|cover)"
]

WAITING_PERIOD_PATTERNS = [
    r"(waiting\s*period|initial\s*waiting\s*period)\s*[:\-]?\s*([0-9]{1,3})\s*(days?|months?)",
    r"([0-9]{1,3})\s*(days?|months?)\s*(?:of)?\s*(?:initial\s*)?waiting\s*period"
]

CLAIM_RATIO_PATTERNS = [
    r"(claim\s*settlement\s*ratio|claim\s*ratio|incurred\s*claim\s*ratio)\s*[:\-]?\s*([0-9]{1,3}(?:\.[0-9]+)?)\s*%",
    r"([0-9]{1,3}(?:\.[0-9]+)?)\s*%\s*(claim\s*settlement\s*ratio|claim\s*ratio)"
]

def _extract_by_patterns(text: str, patterns) -> Optional[Tuple[str, str]]:
    for pat in patterns:
        m = re.search(pat, text, flags=re.I)
        if m:
            groups = [g for g in m.groups() if g is not None]
            if len(groups) >= 2:
                return (groups[-2], groups[-1])
            elif len(groups) == 1:
                return (groups[0], "")
    return None

def extract_sum_insured(text: str) -> Optional[str]:
    hit = _extract_by_patterns(text, SUM_INSURED_PATTERNS)
    if not hit:
        return None
    val, unit = hit
    num = safe_float(val)
    if num is None:
        return None
    unit = unit.lower() if unit else ""
    if re.search(r"(lakh|lac)", unit):
        return f"{num:.2f} Lakh"
    if re.search(r"(crore|cr)", unit):
        return f"{num * 100:.2f} Lakh"
    if num >= 100000:
        return f"{num/100000:.2f} Lakh"
    return f"{num:.0f}"

def extract_waiting_period(text: str) -> Optional[str]:
    hit = _extract_by_patterns(text, WAITING_PERIOD_PATTERNS)
    if not hit:
        return None
    val, unit = hit
    num = safe_float(val)
    if num is None:
        return None
    unit = unit.lower() if unit else "days"
    if "month" in unit:
        return f"{int(num*30)} Days"
    return f"{int(num)} Days"

def extract_claim_ratio(text: str) -> Optional[str]:
    hit = _extract_by_patterns(text, CLAIM_RATIO_PATTERNS)
    if not hit:
        return None
    val = hit[0] if hit[0] and re.search(r"\d", hit[0]) else hit[1]
    num = safe_float(val)
    if num is None:
        return None
    if num <= 1.2:
        num *= 100
    return f"{num:.2f}%"

def ask_gemini_for_metric(policy_name: str, policy_text: str, metric: str) -> Optional[str]:
    prompt = f"""
You are given an insurance policy description. Extract the value for the metric exactly and ONLY as a JSON object.

Policy Name: "{policy_name}"
Metric: "{metric}"

Rules:
- If found, return exact value with units/%.
- If NOT found, use reliable knowledge to provide a typical/recent value.
- Output MUST be valid JSON: {{ "metric": "...", "value": "..." }}

Policy Text:
\"\"\"{policy_text[:15000]}\"\"\"
"""
    try:
        raw = gemini_generate(prompt)
        try:
            js = json.loads(raw)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                js = json.loads(m.group(0))
            else:
                return None
        return str(js.get("value")).strip()
    except Exception:
        return None

def get_three_metrics(policy_name: str, text: str) -> Dict[str, Optional[str]]:
    metrics = {
        "Sum Insured": extract_sum_insured(text),
        "Waiting Period": extract_waiting_period(text),
        "Claim Settlement Ratio": extract_claim_ratio(text),
    }
    for k, v in metrics.items():
        if not v:
            ai_val = ask_gemini_for_metric(policy_name, text, k)
            if ai_val:
                metrics[k] = ai_val
    return metrics

def to_number_for_plot(value: Optional[str], metric: str) -> Optional[float]:
    if not value:
        return None
    v = value.strip()
    if metric == "Sum Insured":
        m = re.search(r"([0-9][0-9,\.]*)\s*(lakh|lac)?", v, re.I)
        if m:
            num = safe_float(m.group(1))
            if num is None:
                return None
            unit = (m.group(2) or "").lower()
            if unit in ["lakh", "lac"]:
                return float(num)
            if num >= 100000:
                return num / 100000.0
            return num
    elif metric == "Waiting Period":
        m = re.search(r"([0-9]{1,4})\s*days?", v, re.I)
        if m:
            return float(m.group(1))
        m = re.search(r"([0-9]{1,3})\s*months?", v, re.I)
        if m:
            return float(m.group(1)) * 30.0
    elif metric == "Claim Settlement Ratio":
        m = re.search(r"([0-9]{1,3}(?:\.[0-9]+)?)\s*%", v)
        if m:
            return float(m.group(1))
        m = re.search(r"([01](?:\.[0-9]+)?)$", v)
        if m:
            return float(m.group(1)) * 100.0
    return None

# ---------------------------
# Streamlit UI
# ---------------------------
st.set_page_config(page_title="Policy Comparator", layout="wide")
st.title("📄 Insurance Policy Comparator")
st.markdown("Upload two policy documents (PDFs) to generate summaries, comparisons, visual insights, and ask questions.")

# Initialize session state
for key in ["text1", "text2", "summary1", "summary2", "comparison",
            "policy1_name", "policy2_name", "metrics_df", "show_qa"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "show_qa" else False

# Upload PDFs
col1, col2 = st.columns(2)
with col1:
    pdf1 = st.file_uploader("Upload Policy Document 1", type="pdf")
with col2:
    pdf2 = st.file_uploader("Upload Policy Document 2", type="pdf")

if pdf1 and pdf2:
    if st.button("Generate Summaries"):
        st.session_state.text1 = extract_text_from_pdf(pdf1)
        st.session_state.text2 = extract_text_from_pdf(pdf2)

        st.session_state.summary1 = gemini_generate(
            f"Summarize this insurance policy in structured **paragraph** style: {st.session_state.text1}"
        )
        st.session_state.summary2 = gemini_generate(
            f"Summarize this insurance policy in structured **paragraph** style: {st.session_state.text2}"
        )

        st.session_state.policy1_name = normalize_policy_name(st.session_state.text1, "Policy 1")
        st.session_state.policy2_name = normalize_policy_name(st.session_state.text2, "Policy 2")

    if st.session_state.summary1 and st.session_state.summary2:
        st.subheader("📌 Policy Summaries")
        st.markdown(f"### {st.session_state.policy1_name}")
        st.write(st.session_state.summary1)
        st.markdown(f"### {st.session_state.policy2_name}")
        st.write(st.session_state.summary2)

        # ----------- Comparison Table -----------
        if st.button("Compare Policies"):
            m1 = get_three_metrics(st.session_state.policy1_name, st.session_state.text1)
            m2 = get_three_metrics(st.session_state.policy2_name, st.session_state.text2)
            rows = []
            for attr in ["Sum Insured", "Waiting Period", "Claim Settlement Ratio"]:
                rows.append({
                    "Attribute": attr,
                    st.session_state.policy1_name: m1.get(attr, ""),
                    st.session_state.policy2_name: m2.get(attr, "")
                })
            st.session_state.comparison = pd.DataFrame(rows)
            st.session_state.metrics_df = pd.DataFrame([{"Policy": st.session_state.policy1_name, **m1},
                                                        {"Policy": st.session_state.policy2_name, **m2}])

        if isinstance(st.session_state.comparison, pd.DataFrame):
            st.subheader("📊 Policy Comparison Table")
            st.table(st.session_state.comparison)

            st.subheader("📈 Metrics Visualization")
            metric_choice = st.selectbox(
                "Select a metric to visualize",
                options=["Sum Insured", "Waiting Period", "Claim Settlement Ratio"]
            )
            plot_df = st.session_state.metrics_df.copy()
            plot_df["Value"] = plot_df[metric_choice].apply(lambda v: to_number_for_plot(v, metric_choice))
            st.dataframe(st.session_state.metrics_df)

            if plot_df["Value"].isna().all():
                st.warning("Could not prepare numeric values for the selected metric.")
            else:
                fig, ax = plt.subplots()
                ax.bar(plot_df["Policy"], plot_df["Value"], color=["#4CAF50", "#2196F3"])
                ax.set_ylabel(metric_choice)
                ax.set_title(f"{metric_choice} Comparison")
                st.pyplot(fig)

        # ----------- Simple Q&A -----------
        if st.button("Ask Q&A"):
            st.session_state.show_qa = True

        if st.session_state.show_qa:
            user_question = st.text_input("Enter your question about these policies:")
            if user_question:
                qa_prompt = f"Answer the following question based on the two insurance documents: {user_question}"
                ga_context = f"Policy A:\n{st.session_state.text1}\n\nPolicy B:\n{st.session_state.text2}"
                ga_response = gemini_generate(f"{qa_prompt}\n\nContext:\n{ga_context}")
                st.markdown("**Answer:**")
                st.write(ga_response)
