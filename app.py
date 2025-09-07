# app.py
import streamlit as st
from PIL import Image
import os
import uuid
import pandas as pd
import time
import google.generativeai as genai
from fpdf import FPDF
from io import BytesIO
import datetime

# Import your modules
from models import load_car_detector, load_damage_model, detect_car, classify_damage, detect_and_annotate_car
from utils import extract_text_from_image, extract_text_from_pdf, parse_policy_text, estimate_cost, get_severity

# -------------------------------
# 🔐 HARD CODED GEMINI API KEY (For local testing only)
GEMINI_API_KEY = "AIzaSyDUvKi1lkLKUPrqZd9Xe1YhKgXs2o3qGOY"

# -------------------------------
# Setup directories
UPLOAD_FOLDER_IMAGES = "uploads/images"
UPLOAD_FOLDER_POLICIES = "uploads/policies"
os.makedirs(UPLOAD_FOLDER_IMAGES, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_POLICIES, exist_ok=True)

# -------------------------------
# ✅ PDF REPORT GENERATION FUNCTION (Updated for Multi-Damage)
def generate_pdf_report(claim_data, chat_history=None):
    from fpdf import FPDF
    import os
    from PIL import Image as PILImage

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.set_fill_color(0, 120, 212)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, "AutoClaim: Insurance Claim Report", ln=True, align="C", fill=True)
    pdf.ln(10)

    # Claim ID & Timestamp
    claim_id = claim_data.get('claim_id', 'N/A')
    submitted_at = claim_data.get('submitted_at', 'N/A')
    pdf.set_font("Arial", size=10)
    pdf.cell(0, 8, f"Claim ID: {claim_id} | Submitted: {submitted_at}", ln=True)
    pdf.ln(5)

    # Claim Summary
    pdf.set_font("Arial", size=12)
    detected_damages = claim_data.get('detected_damages', [])
    confidences = claim_data.get('confidences', [])

    for i, damage in enumerate(detected_damages):
        conf = confidences[i] if i < len(confidences) else 0.0
        pdf.cell(0, 10, f"Damage {i+1}: {damage.title()} (Confidence: {conf:.2f})", ln=True)

    if claim_data.get('covered_items'):
        covered = ", ".join([c.title() for c in claim_data['covered_items']])
        pdf.cell(0, 10, f"Policy Covers: {covered}", ln=True)
    pdf.ln(5)

    # Claim Decision
    detected_damages = claim_data.get('detected_damages', [])
    covered_items = claim_data.get('covered_items', [])
    covered_items_set = set(covered_items)
    is_any_covered = any(d in covered_items_set for d in detected_damages)

    pdf.set_font("Arial", 'B', 12)
    status_color = (0, 150, 0) if is_any_covered else (180, 0, 0)
    pdf.set_text_color(*status_color)
    pdf.cell(0, 10, f"Claim Status: {'APPROVED' if is_any_covered else 'PARTIALLY APPROVED/REJECTED'}", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(10)

    # Itemized Bill
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(0, 10, "Itemized Repair Bill", ln=True)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(90, 8, "Damage Type", border=1)
    pdf.cell(30, 8, "Covered", border=1)
    pdf.cell(40, 8, "Estimated Cost", border=1)
    pdf.ln(8)

    # Estimate cost for all detected damages
    detected_damages = claim_data.get('detected_damages', [])
    if not detected_damages and claim_data.get('detected_damage'):
        detected_damages = [claim_data['detected_damage']]

    items, _ = estimate_cost(detected_damages)

    # Recalculate covered status
    covered_items_set = set(covered_items)
    covered_amount = 0
    for item in items:
        item['covered'] = item['damage'] in covered_items_set
        if item['covered']:
            covered_amount += item['cost']

    pdf.set_font("Arial", size=11)
    for item in items:
        pdf.cell(90, 8, item['damage'].title(), border=1)
        covered_status = "Yes" if item['covered'] else "No"
        pdf.cell(30, 8, covered_status, border=1)
        pdf.cell(40, 8, f"${item['cost']}", border=1)
        pdf.ln(8)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(120, 10, "Approved Claim Amount:", border=0)
    pdf.cell(40, 10, f"${covered_amount}", border=0, ln=True)
    pdf.ln(10)

    # Car Image (annotated if available)
    image_path = claim_data.get('annotated_image_path') or claim_data.get('image_path')
    if image_path and os.path.exists(image_path):
        try:
            img = PILImage.open(image_path)
            temp_img = "temp_report_image.jpg"
            img.save(temp_img, "JPEG", quality=85)
            pdf.image(temp_img, x=10, w=180)
            os.remove(temp_img)
            pdf.ln(85)
        except Exception as e:
            pdf.cell(0, 10, "Car image could not be embedded.", ln=True)

    # Chat Transcript (Optional)
    if chat_history and len(chat_history) > 0:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 13)
        pdf.cell(0, 10, "AI Assistant Chat Transcript", ln=True)
        pdf.ln(5)
        pdf.set_font("Arial", size=10)
        for msg in chat_history:
            role = "You" if msg["role"] == "user" else "AI Assistant"
            text = msg["parts"][0]
            pdf.multi_cell(0, 6, txt=f"{role}: {text}", align="L")
            pdf.ln(2)

    # Output
    pdf_file = "AutoClaim_Report.pdf"
    pdf.output(pdf_file)
    return pdf_file

# -------------------------------
# Custom CSS
st.markdown("""
<style>
    .main { background-color: #f8f9fa; font-family: 'Segoe UI', sans-serif; }
    .step-header {
        background-color: #0078d4; color: white; padding: 12px 16px; border-radius: 10px;
        font-size: 1.2em; font-weight: bold; margin: 20px 0; box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
    .metric-card {
        background: white; padding: 15px; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        text-align: center; margin-bottom: 15px;
    }
    .metric-value { font-size: 1.5em; font-weight: bold; color: #0078d4; }
    .metric-label { font-size: 0.9em; color: #555; }
    .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); margin: 15px 0; }
    .success-box { background-color: #d4edda; color: #155724; padding: 12px; border-radius: 8px; border-left: 5px solid #28a745; margin: 10px 0; }
    .error-box { background-color: #f8d7da; color: #721c24; padding: 12px; border-radius: 8px; border-left: 5px solid #dc3545; margin: 10px 0; }
    .info-box { background-color: #d1ecf1; color: #0c5460; padding: 12px; border-radius: 8px; border-left: 5px solid #007bff; margin: 10px 0; }
    .stChatMessage { border-radius: 12px !important; padding: 10px 15px; }
    [data-testid="stButton"] button { background-color: #0078d4; color: white; }
</style>
""", unsafe_allow_html=True)

# -------------------------------
# Load models
@st.cache_resource
def get_models():
    car_model = load_car_detector()
    damage_processor, damage_model = load_damage_model()
    return car_model, damage_processor, damage_model

try:
    car_detector, damage_processor, damage_classifier = get_models()
except Exception as e:
    st.markdown(f'<div class="error-box">❌ Failed to load models: {e}</div>', unsafe_allow_html=True)
    st.stop()

# -------------------------------
# Session state initialization
if 'claim_data' not in st.session_state:
    st.session_state.claim_data = {}
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'is_speaking' not in st.session_state:
    st.session_state.is_speaking = False

# -------------------------------
# Header
st.markdown("<h1 style='text-align:center; color:#0078d4;'>🚗 AutoClaim Pro</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#555;'>Smart Insurance Claim Assistant with AI Insights</p>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# -------------------------------
# Step 1: Upload Car Image
st.markdown('<div class="step-header">📷 Upload Car Damage Photo</div>', unsafe_allow_html=True)
uploaded_image = st.file_uploader("Drag & drop your car image", type=["jpg", "jpeg", "png"], key="img_up")

if uploaded_image:
    image = Image.open(uploaded_image).convert("RGB")
    img_path = os.path.join(UPLOAD_FOLDER_IMAGES, f"{uuid.uuid4()}.jpg")
    image.save(img_path)
    st.session_state.claim_data['image_path'] = img_path
    st.session_state.claim_data['claim_id'] = f"CLAIM-{uuid.uuid4().hex[:8].upper()}"
    st.session_state.claim_data['submitted_at'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    st.markdown('<div class="card">', unsafe_allow_html=True)
    # Display annotated image if available, else original
    display_img_path = st.session_state.claim_data.get('annotated_image_path', img_path)
    display_image = Image.open(display_img_path)
    st.image(display_image, caption="Detected Car & Damage Area", use_column_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    with st.spinner("🔍 Detecting car..."):
        if detect_car(img_path, car_detector):
            st.markdown('<div class="success-box">✅ Car detected!</div>', unsafe_allow_html=True)
            st.session_state.claim_data['car_detected'] = True
        else:
            st.markdown('<div class="error-box">❌ No car detected.</div>', unsafe_allow_html=True)
            st.session_state.claim_data['car_detected'] = False

    if st.session_state.claim_data.get('car_detected'):
        with st.spinner("🔬 Analyzing damage..."):
            try:
                # Get multiple damages
                damage_labels, confidences = classify_damage(img_path, damage_processor, damage_classifier)
                st.session_state.claim_data['detected_damages'] = damage_labels
                st.session_state.claim_data['confidences'] = confidences
                st.session_state.claim_data['detected_damage'] = damage_labels[0] if damage_labels else "unknown"
                st.session_state.claim_data['confidence'] = confidences[0] if confidences else 0.0

                # Annotate image
                annotated_img_path = detect_and_annotate_car(img_path, car_detector)
                st.session_state.claim_data['annotated_image_path'] = annotated_img_path

                # Display damages
                st.markdown('<div class="card">', unsafe_allow_html=True)
                for i, (label, conf) in enumerate(zip(damage_labels, confidences)):
                    color = "#28a745" if i == 0 else "#6c757d"
                    st.markdown(f"<h4 style='color:{color}; margin:0;'>🔧 {label.title()} <small>({conf:.2f})</small></h4>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

            except Exception as e:
                st.markdown(f'<div class="error-box">❌ Error: {e}</div>', unsafe_allow_html=True)

# -------------------------------
# Severity (Max Severity from all damages)
if st.session_state.claim_data.get('detected_damages'):
    detected_damages = st.session_state.claim_data['detected_damages']
    severities = [get_severity(d) for d in detected_damages]
    # Define severity order for comparison
    severity_order = ["Slightly Damaged", "Moderately Damaged", "Severely Damaged"]
    max_severity = max(severities, key=lambda x: severity_order.index(x) if x in severity_order else 0)

    st.markdown(f"""
    <div class='metric-card' style='background:#fff3cd; border:1px solid #ffeaa7;'>
        <div class='metric-label'>⚠️ Max Severity</div>
        <div class='metric-value' style='color:#d39e00;'>{max_severity}</div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------
# Step 2: Upload Policy
st.markdown('<div class="step-header">📄 Upload Insurance Policy</div>', unsafe_allow_html=True)
uploaded_policy = st.file_uploader("PDF or Image", type=["pdf", "jpg", "jpeg", "png"], key="pol_up")

if uploaded_policy and st.session_state.claim_data.get('detected_damages'):
    ext = uploaded_policy.name.split(".")[-1].lower()
    path = os.path.join(UPLOAD_FOLDER_POLICIES, f"{uuid.uuid4()}.{ext}")
    with open(path, "wb") as f:
        f.write(uploaded_policy.read())
    st.session_state.claim_data['policy_path'] = path

    with st.spinner("📄 Extracting policy text..."):
        try:
            if ext == "pdf":
                raw = extract_text_from_pdf(path)
            else:
                raw = extract_text_from_image(path)

            covered = parse_policy_text(raw)
            st.session_state.claim_data['covered_items'] = covered

            st.markdown(f"""
            <div class='card'>
                <h4>🛡️ Policy Covers</h4>
                <p>{', '.join(covered) if covered else 'None detected'}</p>
            </div>
            """, unsafe_allow_html=True)
        except Exception as e:
            st.markdown(f'<div class="error-box">📄 Error: {e}</div>', unsafe_allow_html=True)

# -------------------------------
# Step 3: Claim Assessment
if uploaded_policy and st.session_state.claim_data.get('detected_damages'):
    st.markdown('<div class="step-header">💰 Claim Assessment</div>', unsafe_allow_html=True)

    detected_damages = st.session_state.claim_data.get('detected_damages', [])
    covered_items = st.session_state.claim_data.get('covered_items', [])
    covered_items_set = set(covered_items)

    # Calculate covered amount
    items, _ = estimate_cost(detected_damages)
    covered_amount = sum(i['cost'] for i in items if i['damage'] in covered_items_set)
    is_any_covered = any(d in covered_items_set for d in detected_damages)

    # Metrics
    col1, col2, col3 = st.columns(3)
    primary_damage = detected_damages[0] if detected_damages else "N/A"
    col1.markdown(f"<div class='metric-card'><div class='metric-label'>Primary Damage</div><div class='metric-value'>{primary_damage.title()}</div></div>", unsafe_allow_html=True)
    col2.markdown(f"<div class='metric-card'><div class='metric-label'>Any Covered?</div><div class='metric-value' style='color:{'green' if is_any_covered else 'red'};'>{'✅' if is_any_covered else '❌'}</div></div>", unsafe_allow_html=True)
    col3.markdown(f"<div class='metric-card'><div class='metric-label'>Approved</div><div class='metric-value'>${covered_amount}</div></div>", unsafe_allow_html=True)

    # Dataframe
    df = pd.DataFrame([
        {
            "Type": i['damage'].title(),
            "Covered": "✅ Yes" if i['damage'] in covered_items_set else "❌ No",
            "Cost": f"${i['cost']}"
        }
        for i in items
    ])
    st.dataframe(df.style.applymap(
        lambda v: 'color: green;' if v == "✅ Yes" else ('color: red;' if v == "❌ No" else ''),
        subset=['Covered']
    ))

    if not is_any_covered:
        st.markdown(f'<div class="info-box">ℹ️ <b>Reason:</b> None of the detected damages are covered.</div>', unsafe_allow_html=True)

    with st.expander("🧾 Itemized Bill"):
        for i in items:
            status = "Covered ✅" if i['damage'] in covered_items_set else "Not Covered ❌"
            st.markdown(f"- **{i['damage'].title()}**: ${i['cost']} → {status}")

# -------------------------------
# Step 4: AI Assistant with Voice
if st.session_state.claim_data.get('image_path') or st.session_state.claim_data.get('policy_path'):
    st.markdown('<div class="step-header">🧠 Ask AI Assistant (हिंदी/English)</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class='info-box'>
        💬 Type or click 🎙️ to speak. Click 🛑 to stop speaking.
    </div>
    """, unsafe_allow_html=True)

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # Chat display
        chat_container = st.container()
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.write(msg["parts"][0])

        # Unified input
        txt_col, voice_col = st.columns([12, 1], vertical_alignment="bottom", gap="small")
        with voice_col:
            voice_clicked = st.button("🎙️", key="voice", help="Speak your question")
        with txt_col:
            user_input = st.chat_input("Type or click 🎙️ to speak...")

        # Handle voice
        if voice_clicked:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                with st.spinner("🎙️ Listening..."):
                    try:
                        r.adjust_for_ambient_noise(source, duration=0.5)
                        audio = r.listen(source, timeout=3, phrase_time_limit=5)
                        text = r.recognize_google(audio, language="en-US,hi-IN")
                        user_input = text.strip()
                        st.session_state.last_input_mode = "voice"
                        st.session_state.temp_voice_input = user_input
                        st.success(f"✅: {user_input}")
                    except Exception as e:
                        st.warning(f"🎙️: {e}")

        if user_input or st.session_state.get("temp_voice_input"):
            if st.session_state.get("temp_voice_input"):
                user_input = st.session_state.pop("temp_voice_input")

            def detect_lang(t): return 'hi' if any('\u0900' <= c <= '\u097f' for c in t) else 'en'
            lang = detect_lang(user_input)

            with st.chat_message("user"): st.write(user_input)
            st.session_state.chat_history.append({"role": "user", "parts": [user_input]})

            with st.spinner("🧠 Thinking..."):
                try:
                    context_parts = [
                        f"- Claim ID: {st.session_state.claim_data.get('claim_id', 'N/A')}",
                        f"- Submitted: {st.session_state.claim_data.get('submitted_at', 'N/A')}",
                    ]

                    detected_damages = st.session_state.claim_data.get('detected_damages', [])
                    confidences = st.session_state.claim_data.get('confidences', [])
                    for i, d in enumerate(detected_damages):
                        conf = confidences[i] if i < len(confidences) else 0.0
                        context_parts.append(f"- Damage {i+1}: {d} (Conf: {conf:.2f})")

                    context_parts.append(f"- Covered Items: {', '.join(st.session_state.claim_data.get('covered_items', []))}")

                    # Add policy text snippet if available
                    if st.session_state.claim_data.get('policy_path'):
                        try:
                            policy_text = extract_text_from_pdf(st.session_state.claim_data['policy_path']) if st.session_state.claim_data['policy_path'].endswith('.pdf') else extract_text_from_image(st.session_state.claim_data['policy_path'])
                            context_parts.append(f"- Policy Text Snippet: {policy_text[:2000]}...")
                        except:
                            context_parts.append("- Policy Text: Not available")

                    context = "\n".join(context_parts)

                    img_path = st.session_state.claim_data.get('annotated_image_path') or st.session_state.claim_data.get('image_path')
                    img = Image.open(img_path) if img_path else None
                    prompt = f"{context}\n\nUser: {user_input}\n\nRespond in {'Hindi' if lang=='hi' else 'English'}. Be accurate and helpful."

                    if img:
                        response = model.generate_content([prompt, img])
                    else:
                        response = model.generate_content([prompt])

                    answer = response.text or ("मैं नहीं बता सकता।" if lang == 'hi' else "I can't answer that.")

                    with st.chat_message("assistant"): st.write(answer)
                    st.session_state.chat_history.append({"role": "model", "parts": [answer]})

                    # TTS if voice input
                    if st.session_state.get("last_input_mode") == "voice":
                        from gtts import gTTS
                        import pygame
                        import tempfile
                        import os
                        try:
                            tts = gTTS(text=answer, lang=lang, slow=False)
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                                tts.save(temp_file.name)
                                temp_file_path = temp_file.name

                            st.session_state.is_speaking = True
                            pygame.mixer.init()
                            pygame.mixer.music.load(temp_file_path)
                            pygame.mixer.music.play()

                            with st.container():
                                c1, c2 = st.columns([10, 1])
                                with c1: st.info("🔊 AI is speaking...")
                                with c2:
                                    if st.button("🛑", help="Stop"):
                                        pygame.mixer.music.stop()
                                        st.session_state.is_speaking = False
                                        st.rerun()

                            while st.session_state.is_speaking and pygame.mixer.music.get_busy():
                                time.sleep(0.1)
                            st.session_state.is_speaking = False
                            if os.path.exists(temp_file_path):
                                os.unlink(temp_file_path)
                        except Exception as e:
                            st.warning(f"🔊 TTS error: {e}")

                    st.session_state.last_input_mode = "text"

                except Exception as e:
                    st.error(f"❌ Gemini: {e}")

    except Exception as e:
        st.error(f"❌ AI Assistant: {e}")

# -------------------------------
# PDF Export Only
if uploaded_policy and st.session_state.claim_data.get('detected_damages'):
    st.markdown("---")
    st.markdown("### 📎 Export Report")

    if st.button("📥 Generate PDF Report"):
        with st.spinner("📄 Generating..."):
            try:
                pdf_path = generate_pdf_report(st.session_state.claim_data, st.session_state.chat_history)
                with open(pdf_path, "rb") as f:
                    st.download_button("⬇️ Download Report", f, "AutoClaim_Report.pdf", "application/pdf")
            except Exception as e:
                st.error(f"❌ PDF Generation Failed: {e}")

# Footer
st.markdown("<hr>", unsafe_allow_html=True)
st.markdown("<p style='text-align:center; color:#888;'>💡 Powered by YOLOv8, Transformers & Gemini AI</p>", unsafe_allow_html=True)