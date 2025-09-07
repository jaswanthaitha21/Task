# models.py
from ultralytics import YOLO
from transformers import AutoImageProcessor, AutoModelForImageClassification
import torch
from PIL import Image

# Load YOLOv8 for car detection
def load_car_detector():
    return YOLO('yolov8n.pt')  # Pretrained on COCO (includes 'car')

# Load damage classifier from local directory
def load_damage_model():
    """
    Load damage classification model from local directory.
    Assumes model is saved in './car_damage_model'
    """
    local_model_path = "./car_damage_model"
    from transformers import AutoImageProcessor, AutoModelForImageClassification
    processor = AutoImageProcessor.from_pretrained(local_model_path)
    model = AutoModelForImageClassification.from_pretrained(local_model_path)
    return processor, model

# Detect if image contains a car
def detect_car(image_path, model):
    results = model(image_path)
    names = model.names
    for r in results:
        for c in r.boxes.cls:
            class_name = names[int(c)]
            if class_name in ['car', 'truck', 'bus']:
                return True
    return False

# Classify damage type
def classify_damage(image_path, processor, model):
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        predicted_class_idx = logits.argmax(-1).item()
        label = model.config.id2label[predicted_class_idx]
        confidence = torch.softmax(logits, dim=1)[0][predicted_class_idx].item()

    return label.lower(), confidence