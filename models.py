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

# Classify damage type — NOW RETURNS MULTIPLE
def classify_damage(image_path, processor, model):
    image = Image.open(image_path).convert("RGB")
    inputs = processor(images=image, return_tensors="pt")

    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = torch.softmax(logits, dim=1)[0]  # Get probabilities

        # Get top 3 predictions
        topk = torch.topk(logits, k=3)
        labels = []
        confidences = []

        for i in range(topk.indices.size(1)):
            idx = topk.indices[0][i].item()
            conf = probs[idx].item()
            if conf > 0.3:  # Confidence threshold
                label = model.config.id2label[idx].lower()
                labels.append(label)
                confidences.append(conf)

        if not labels:  # Fallback to top-1 if none above threshold
            idx = logits.argmax(-1).item()
            label = model.config.id2label[idx].lower()
            conf = probs[idx].item()
            labels = [label]
            confidences = [conf]

    return labels, confidences  # Return lists now

# NEW: Annotate car with bounding box
def detect_and_annotate_car(image_path, model, save_annotated=True):
    """
    Detect car and return annotated image path with bounding box.
    Later, replace with damage-specific detector.
    """
    results = model(image_path)
    annotated_image = None

    for r in results:
        # Plot bounding boxes on image
        im_array = r.plot()  # returns numpy array (BGR)
        annotated_image = Image.fromarray(im_array[..., ::-1])  # Convert BGR to RGB

    if annotated_image and save_annotated:
        annotated_path = image_path.replace(".jpg", "_annotated.jpg")
        annotated_image.save(annotated_path)
        return annotated_path

    return image_path  # fallback