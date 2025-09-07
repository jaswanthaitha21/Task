# utils.py
import pytesseract
import cv2
import numpy as np
import re
import spacy
import os
import fitz  # PyMuPDF
from PIL import Image
import io

# Configure Tesseract path (Windows example — adjust if needed)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Damage to cost mapping
DAMAGE_COST = {
    "dent": 300,
    "scratch": 150,
    "lamp broken": 400,
    "glass shatter": 500,
    "bumper damage": 600,
    "door damage": 700
}

SEVERITY_RULES = {
    "glass shatter": "Moderately Damaged",
    "lamp broken": "Slightly Damaged",
    "dent": "Slightly Damaged",
    "deep dent": "Moderately Damaged",
    "cracked windshield": "Moderately Damaged",
    "broken headlight": "Slightly Damaged",
}

def extract_text_from_image(image_path):
    """Extract text from image using Tesseract OCR"""
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    text = pytesseract.image_to_string(thresh)
    return text


def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF using PyMuPDF (fitz).
    - First tries direct text extraction (for digital/native PDFs).
    - If little/no text found, falls back to rendering pages as images + OCR.
    """
    full_text = ""
    doc = None

    try:
        doc = fitz.open(pdf_path)

        # First pass: try direct text extraction
        for page in doc:
            text = page.get_text().strip()
            if text:
                full_text += text + "\n"

        # Heuristic: if we got meaningful text, return it
        if len(full_text.strip()) > 50:  # Adjust threshold as needed
            return full_text.strip()

        # Fallback: render each page as image and OCR it
        full_text = ""
        for i, page in enumerate(doc):
            # Render page to image (increase DPI for better OCR)
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_bytes))

            # Save temp image for OCR
            temp_img_path = f"./temp_page_{i}.png"
            img.save(temp_img_path)

            # Use your existing OCR function
            page_text = extract_text_from_image(temp_img_path)
            full_text += page_text + "\n"

            # Cleanup
            if os.path.exists(temp_img_path):
                os.remove(temp_img_path)

        return full_text.strip()

    except Exception as e:
        raise Exception(f"Error extracting text from PDF: {e}")
    finally:
        if doc:
            doc.close()


def parse_policy_text(text):
    """Parse policy text to extract covered items"""
    text = text.lower()
    covered = []

    keywords = ["headlight", "windshield", "tire", "lamp", "glass", "bumper", "door", "dent"]
    for word in keywords:
        if word in text:
            if word in ["headlight", "lamp"]:
                covered.append("lamp broken")
            elif word in ["windshield", "glass"]:
                covered.append("glass shatter")
            elif word == "tire":
                covered.append("tire damage")
            elif word == "dent":
                covered.append("dent")
            elif word == "bumper":
                covered.append("bumper damage")
            elif word == "door":
                covered.append("door damage")
    return list(set(covered))


def estimate_cost(damage_list):
    """Estimate repair cost for detected damages"""
    total = 0
    details = []
    for d in damage_list:
        cost = DAMAGE_COST.get(d, 200)  # Default $200 if not found
        covered = True  # Will be validated against policy later
        details.append({"damage": d, "cost": cost, "covered": covered})
        total += cost
    return details, total


def get_severity(damage_type):
    """Get severity level based on damage type"""
    for key in SEVERITY_RULES:
        if key in damage_type:
            return SEVERITY_RULES[key]
    return "Slightly Damaged"