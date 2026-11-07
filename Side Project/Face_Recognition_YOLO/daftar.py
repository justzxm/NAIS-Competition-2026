import cv2
import pickle
import os
from ultralytics import YOLO
from embedding import get_embedding

nama = input("Nama orang yang didaftarkan: ").strip()

yolo = YOLO("model_wajah.pt")
cap = cv2.VideoCapture(0)

# Muat database lama jika ada
if os.path.exists("database.pkl"):
    with open("database.pkl", "rb") as f:
        db = pickle.load(f)
else:
    db = {}
db.setdefault(nama, [])

while True:
    ok, frame = cap.read()
    if not ok:
        break

    hasil = yolo(frame, verbose=False)[0]
    boxes = hasil.boxes.xyxy.cpu().numpy().astype(int)

    for (x1, y1, x2, y2) in boxes:
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

    info = f"{nama}: {len(db[nama])} foto | S=simpan  Q=selesai"
    cv2.putText(frame, info, (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    cv2.imshow("Daftar Wajah", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("s"):
        if len(boxes) == 1:                      # simpan hanya jika ada 1 wajah
            x1, y1, x2, y2 = boxes[0]
            wajah = frame[max(y1, 0):y2, max(x1, 0):x2]
            db[nama].append(get_embedding(wajah))
            print(f"Tersimpan ({len(db[nama])} foto)")
        else:
            print("Harus ada tepat 1 wajah di layar")
    elif key == ord("q"):
        break

with open("database.pkl", "wb") as f:
    pickle.dump(db, f)

cap.release()
cv2.destroyAllWindows()
print("Database disimpan:", {k: len(v) for k, v in db.items()})