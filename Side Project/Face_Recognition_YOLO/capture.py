import cv2
from pathlib import Path

# lokasi penyimpanan foto
folder = Path(__file__).resolve().parent/"dataset"/"images"/"train"
folder.mkdir(parents=True,exist_ok=True)

# mengaktifkan webcam
camera = cv2.VideoCapture(0)

if not camera.isOpened():
    raise RuntimeError ("Webcam tidak dapat di buka")

# Menentukan nomor foto berikutnya
nomor = 1

while (folder/f"face_{nomor}.jpg").exists():
    nomor += 1

while True:
    ret, frame = camera.read()

    if not ret:
        print("Gagal membaca kamera")
        break

    cv2.imshow("Face Capture",frame)

    key = cv2.waitKey(1) & 0xFF

# tekan S untuk menyimpan foto
    if key == ord("s"):
        lokasi = folder/f"face_{nomor}.jpg"

        if cv2.imwrite(str(lokasi), frame):
            print(f"Foto berhasil disimpan: {lokasi}")
            nomor += 1
        else:
            print("Gagal menyimpan foto")
# tekan Q untuk keluar
    elif key == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()