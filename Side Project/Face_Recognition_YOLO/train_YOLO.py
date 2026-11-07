from ultralytics import YOLO


# Load model YOLOv8 Nano
model = YOLO("yolov8n.pt")

# Training model
model.train(
    data=r"D:\Python\Project_AI\Face_Detection_YOLO\faces.yaml",
    epochs=50,
    imgsz=640,
    batch=8,
    name="face_detection"
)