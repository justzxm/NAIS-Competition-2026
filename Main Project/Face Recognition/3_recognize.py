import cv2
import csv
import os
from datetime import datetime

# 1. Muat kamus nama dari file names.txt
names_dict = {}
if os.path.exists("names.txt"):
    with open("names.txt", "r") as f:
        for line in f:
            if "," in line:
                key, value = line.strip().split(",")
                names_dict[int(key)] = value

# 2. Inisialisasi recognizer dan detektor wajah
recognizer = cv2.face.LBPHFaceRecognizer_create()
recognizer.read("training.yml")
detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

# 3. Siapkan file CSV untuk mencatat log deteksi (jika belum ada, buat file dan tulis header-nya)
csv_file = "deteksi_log.csv"
file_exists = os.path.exists(csv_file)

with open(csv_file, mode="a", newline="") as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow(["Tanggal_Waktu", "Nama", "Confidence"])

# 4. Nyalakan kamera
cap = cv2.VideoCapture(0)
print("\n[INFO] Kamera rekognisi aktif. Tekan tombol 'q' untuk keluar.")

# Variabel pembatas agar log CSV tidak menulis data yang sama terus-menerus dalam 1 detik
last_logged_name = ""
last_log_time = datetime.now()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5, minSize=(100, 100))

    for (x, y, w, h) in faces:
        # Prediksi wajah menggunakan model yang sudah dilatih
        id_prediksi, confidence = recognizer.predict(gray[y:y+h, x:x+w])

        # Atur ambang batas (confidence). Semakin kecil nilai confidence, semakin akurat.
        # Biasanya di bawah 70 atau 80 dianggap cocok.
        if confidence < 80:
            nama = names_dict.get(id_prediksi, "Tidak Dikenal")
            # Tampilkan tingkat akurasi (dibalik agar persentase keyakinan intuitif)
            akurasi_text = f"{round(100 - confidence)}%"
        else:
            nama = "Tidak Dikenal"
            akurasi_text = f"{round(100 - confidence)}%"

        # Kotak di sekitar wajah
        cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
        
        # Tulis nama dan akurasi di atas kotak
        teks_tampil = f"{nama} ({akurasi_text})"
        cv2.putText(frame, teks_tampil, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        # 5. Simpan ke CSV (Poin 7) dengan jeda waktu minimal 3 detik per orang agar log tidak menumpuk
        sekarang = datetime.now()
        if nama != "Tidak Dikenal":
            selisih_waktu = (sekarang - last_log_time).total_seconds()
            if nama != last_logged_name or selisih_waktu > 3:
                with open(csv_file, mode="a", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow([sekarang.strftime("%Y-%m-%d %H:%M:%S"), nama, f"{round(100 - confidence)}%"])
                print(f"[LOG TERSIMPAN] {nama} terdeteksi pada {sekarang.strftime('%H:%M:%S')}")
                last_logged_name = nama
                last_log_time = sekarang

    # Tampilkan jendela hasil rekognisi
    cv2.imshow("Uji Coba Rekognisi Wajah - Tekan 'q' untuk Keluar", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print("[SELESAI] Program rekognisi ditutup.")