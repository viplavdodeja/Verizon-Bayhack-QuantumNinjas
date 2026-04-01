from ultralytics import YOLO

# Load the model
model = YOLO("./firedetect-11s.pt")

# Perform detection on an image
results = model("fire_forest_1.jpg")

# Display or process the results
results[0].show()  # This will display the image with detected objects

