# utils.py
import pytesseract

# Add this at the top of utils.py
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


import pytesseract
import cv2
import numpy as np
import re
import spacy
from pdf2image import convert_from_path
import os

# Damage to cost mapping (can be extended)
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
    img = cv2.imread(image_path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
    text = pytesseract.image_to_string(thresh)
    return text


def extract_text_from_pdf(pdf_path):
    # Try to auto-detect Poppler from PATH, else fallback to manual path
    default_poppler_path = r"C:\Program Files\poppler-24.08.0\bin"  # <-- update this

    poppler_path = None
    if os.environ.get("PATH"):
        for p in os.environ["PATH"].split(os.pathsep):
            if os.path.exists(os.path.join(p, "pdftoppm.exe")):
                poppler_path = p
                break

    if poppler_path is None:  # fallback if not found in PATH
        poppler_path = default_poppler_path
        if not os.path.exists(os.path.join(poppler_path, "pdftoppm.exe")):
            raise FileNotFoundError(
                f"Poppler not found! Please install it and set PATH, "
                f"or update poppler_path in utils.py (expected {default_poppler_path})"
            )

    images = convert_from_path(pdf_path, poppler_path=poppler_path)
    full_text = ""
    for img in images:
        temp_path = "./temp_img.jpg"
        img.save(temp_path)
        full_text += extract_text_from_image(temp_path) + "\n"
        os.remove(temp_path)  # Cleanup
    return full_text


def parse_policy_text(text):
    text = text.lower()
    covered = []

    # Simple keyword matching (can be improved with NER)
    keywords = ["headlight", "windshield", "tire", "lamp", "glass", "bumper", "door"]
    for word in keywords:
        if word in text:
            if word == "headlight" or "lamp" in word:
                covered.append("lamp broken")
            if word == "windshield" or "glass" in word:
                covered.append("glass shatter")
            if word == "tire":
                covered.append("tire damage")
            if word == "dent" in text:
                covered.append("dent")
            if word == "bumper":
                covered.append("bumper damage")
    return list(set(covered))

def estimate_cost(damage_list):
    total = 0
    details = []
    for d in damage_list:
        cost = DAMAGE_COST.get(d, 200)
        covered = True  # Will be checked later against policy
        details.append({"damage": d, "cost": cost, "covered": covered})
        total += cost
    return details, total

def get_severity(damage_type):
    for key in SEVERITY_RULES:
        if key in damage_type:
            return SEVERITY_RULES[key]
    return "Slightly Damaged"

