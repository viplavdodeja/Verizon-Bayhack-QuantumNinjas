from ultralytics import YOLO
import os

MODEL_PATH = "./firedetect-11s.pt"
IMAGE_FOLDER = "./images"

model = YOLO(MODEL_PATH)

results = model.predict(
    source=IMAGE_FOLDER,
    conf=0.40,
    iou=0.45,
    imgsz=640,
    verbose=False,
    save=True,
    project=".",
    name="output",
    exist_ok=True
)

for result in results:
    print(f"\nFile: {result.path}")
    boxes = result.boxes

    if boxes is not None and len(boxes) > 0:
        for box in boxes:
            cls = int(box.cls[0])
            label = model.names[cls]
            conf = float(box.conf[0])
            print(f"Detected {label} with confidence {conf:.2f}")
    else:
        print("No detections found.")