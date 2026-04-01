import cv2
from ultralytics import YOLO

MODEL_PATH = "./firedetect-11s.pt"
CAMERA_INDEX = 0

IMG_SIZE = 640
CONFIDENCE_THRESHOLD = 0.40
IOU_THRESHOLD = 0.45

MIN_CONSECUTIVE_DETECTIONS = 3
MAX_MISSED_FRAMES = 5
MAX_BOX_AREA_RATIO = 0.70

WINDOW_NAME = "Live Fire/Smoke Detection"


def main():
    model = YOLO(MODEL_PATH)

    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    consecutive_detections = 0
    missed_frames = 0
    alert_active = False

    print("Press q to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to read frame.")
            break

        frame_h, frame_w = frame.shape[:2]
        frame_area = frame_w * frame_h

        results = model.predict(
            source=frame,
            conf=CONFIDENCE_THRESHOLD,
            iou=IOU_THRESHOLD,
            imgsz=IMG_SIZE,
            verbose=False
        )

        result = results[0]
        boxes = result.boxes

        valid_detections = []

        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                cls = int(box.cls[0])
                label = model.names[cls]
                conf = float(box.conf[0])

                x1, y1, x2, y2 = box.xyxy[0].tolist()
                x1 = int(x1)
                y1 = int(y1)
                x2 = int(x2)
                y2 = int(y2)

                box_w = max(0, x2 - x1)
                box_h = max(0, y2 - y1)
                box_area = box_w * box_h
                area_ratio = box_area / frame_area

                # Reject detections that cover most of the image
                if area_ratio > MAX_BOX_AREA_RATIO:
                    continue

                valid_detections.append({
                    "label": label,
                    "conf": conf,
                    "x1": x1,
                    "y1": y1,
                    "x2": x2,
                    "y2": y2,
                    "area_ratio": area_ratio
                })

        if len(valid_detections) > 0:
            consecutive_detections += 1
            missed_frames = 0
        else:
            missed_frames += 1
            consecutive_detections = 0

        if consecutive_detections >= MIN_CONSECUTIVE_DETECTIONS:
            alert_active = True

        if missed_frames >= MAX_MISSED_FRAMES:
            alert_active = False

        annotated = frame.copy()

        for det in valid_detections:
            label_text = f"{det['label']} {det['conf']:.2f}"

            cv2.rectangle(
                annotated,
                (det["x1"], det["y1"]),
                (det["x2"], det["y2"]),
                (0, 0, 255),
                2
            )

            cv2.putText(
                annotated,
                label_text,
                (det["x1"], max(20, det["y1"] - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

        status_text = "ALERT ACTIVE" if alert_active else "Monitoring"
        status_color = (0, 0, 255) if alert_active else (0, 255, 0)

        cv2.putText(
            annotated,
            status_text,
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.0,
            status_color,
            2
        )

        cv2.putText(
            annotated,
            f"Consecutive detections: {consecutive_detections}",
            (10, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2
        )

        cv2.imshow(WINDOW_NAME, annotated)

        if len(valid_detections) > 0:
            print("-" * 50)
            for det in valid_detections:
                print(
                    f"Detected {det['label']} | "
                    f"confidence={det['conf']:.2f} | "
                    f"area_ratio={det['area_ratio']:.2f}"
                )

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()