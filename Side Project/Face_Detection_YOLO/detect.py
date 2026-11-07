from ultralytics import YOLO
import cv2
import os
import pickle
import numpy as np
from embedding import get_embedding

FOLDER = r"D:\Python\Project_AI\Face_Detection_YOLO"
THRESHOLD = 0.4

model = YOLO(os.path.join(FOLDER, "model_wajah.pt"))

with open(os.path.join(FOLDER, "database.pkl"), "rb") as f:
    db = pickle.load(f)

def cocokkan(emb):
    terbaik, skor_terbaik = "Unknown", -1.0
    for nama, daftar_emb in db.items():
        skor = max(float(np.dot(emb, e)) for e in daftar_emb)
        if skor > skor_terbaik:
            terbaik, skor_terbaik = nama, skor
    if skor_terbaik < THRESHOLD:
        terbaik = "Unknown"
    return terbaik, skor_terbaik

cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

while True:
    ret, frame = cap.read()

    if not ret:
        break

    results = model(
        frame,
        conf=0.4,              # dinaikkan agar tangan lebih jarang lolos
        iou=0.3,               # diturunkan agar kotak ganda dibuang
        max_det=10,
        agnostic_nms=True,     # NMS lintas kelas
        imgsz=960,
        verbose=False
        )

    # ---- bagian yang diganti: awal loop dan penyaringan ----
    boxes = results[0].boxes
    for (x1, y1, x2, y2), c in zip(boxes.xyxy.cpu().numpy().astype(int),
                                   boxes.conf.cpu().numpy()):
        w, h = x2 - x1, y2 - y1
        if w < 25 or h < 25:                 # terlalu kecil
            continue
        if not (0.6 <= w / h <= 1.3):        # bentuk bukan seperti wajah
            continue

        x1, y1 = max(x1, 0), max(y1, 0)
        wajah = frame[y1:y2, x1:x2]
        if wajah.size == 0:
            continue

        if w < 60 or h < 60:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 255), 2)
            cv2.putText(frame, "Terlalu jauh", (x1, max(y1 - 8, 20)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            continue
        # ---- sampai sini ----

        nama, skor = cocokkan(get_embedding(wajah))

        warna = (0, 255, 0) if nama != "Unknown" else (0, 0, 255)
        cv2.rectangle(frame, (x1, y1), (x2, y2), warna, 2)
        cv2.putText(frame, f"{nama} {skor:.2f}", (x1, max(y1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna, 2)

    cv2.imshow("Face Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()