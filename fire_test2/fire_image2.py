from ultralytics import YOLO
import cv2

MODEL_PATH = "./firedetect-11s.pt"
IMAGE_PATH = "fire_forest_1.jpg"

model = YOLO(MODEL_PATH)

results = model.predict(
    source=IMAGE_PATH,
    conf=0.30,
    iou=0.45,
    imgsz=640,
    verbose=False
)

result = results[0]

print("Detections:")
boxes = result.boxes
if boxes is not None and len(boxes) > 0:
    for i, box in enumerate(boxes):
        cls = int(box.cls[0])
        label = model.names[cls]
        conf = float(box.conf[0])
        x1, y1, x2, y2 = box.xyxy[0].tolist()

        print(f"{i+1}. {label} | confidence={conf:.2f} | box=({x1:.1f}, {y1:.1f}, {x2:.1f}, {y2:.1f})")
else:
    print("No detections found.")

annotated = result.plot()
cv2.imshow("Detection Result", annotated)
cv2.imwrite("fire_forest_1_detected.jpg", annotated)
cv2.waitKey(0)
cv2.destroyAllWindows()