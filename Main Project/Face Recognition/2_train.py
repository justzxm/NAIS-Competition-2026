import cv2
import os
import numpy as np

# Tentukan direktori dataset
path_dataset = "dataset"

# 1. Inisialisasi face recognizer dan detektor wajah (menggunakan file XML di folder lokal)
recognizer = cv2.face.LBPHFaceRecognizer_create()
detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

def get_images_and_labels(path):
    # Cari semua file gambar di dalam folder dataset
    image_paths = []
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".jpg") or file.endswith(".png"):
                image_paths.append(os.path.join(root, file))

    face_samples = []
    ids = []
    names_dict = {}
    current_id = 0

    # Petakan nama folder ke ID angka
    for image_path in image_paths:
        # Ambil nama folder sebagai label nama
        nama_subjek = os.path.basename(os.path.dirname(image_path))
        
        if nama_subjek not in names_dict:
            names_dict[current_id] = nama_subjek
            current_id += 1
        
        # Cari ID untuk nama ini
        subjek_id = [k for k, v in names_dict.items() if v == nama_subjek][0]

        # Baca gambar dan ubah ke grayscale
        img = cv2.imread(image_path)
        if img is None:
            continue
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Deteksi wajah di dalam foto
        faces = detector.detectMultiScale(gray)

        for (x, y, w, h) in faces:
            face_samples.append(gray[y:y+h, x:x+w])
            ids.append(subjek_id)

    return face_samples, np.array(ids), names_dict

print("[INFO] Sedang memproses data wajah untuk training...")
faces, ids, names_dict = get_images_and_labels(path_dataset)

if len(faces) == 0:
    print("[ERROR] Tidak ada wajah yang terdeteksi pada dataset. Pastikan file 'haarcascade_frontalface_default.xml' sudah ada di folder ini dan foto Anda jelas.")
else:
    # Lakukan training model
    recognizer.train(faces, ids)

    # Simpan model ke file training.yml
    recognizer.save("training.yml")

    # Simpan kamus nama (mapping ID ke nama) menggunakan file teks sederhana
    with open("names.txt", "w") as f:
        for key, value in names_dict.items():
            f.write(f"{key},{value}\n")

    print(f"\n[SUKSES] Training selesai! Model disimpan sebagai 'training.yml'.")
    print(f"[INFO] Terdaftar {len(names_dict)} orang dalam model.")