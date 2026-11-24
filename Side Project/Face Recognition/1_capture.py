import cv2
import os

# 1. Masukkan nama subjek yang akan direkam
nama = input("Masukkan nama Anda: ")

# 2. Buat folder khusus untuk orang tersebut di dalam folder dataset
path_folder = f"dataset/{nama}"
if not os.path.exists(path_folder):
    os.makedirs(path_folder)
    print(f"Folder untuk {nama} berhasil dibuat.")

# 3. Nyalakan kamera laptop (biasanya index 0)
cap = cv2.VideoCapture(0)

print("\n[INFO] Kamera menyala. Tekan tombol 's' untuk menyimpan gambar, atau 'q' untuk keluar.")

jumlah_gambar = 0

while True:
    ret, frame = cap.read()
    if not ret:
        print("[ERROR] Gagal membuka kamera.")
        break

    # Tampilkan jendela kamera
    cv2.imshow("Perekam Wajah - Tekan 's' untuk Capture", frame)

    key = cv2.waitKey(1) & 0xFF

    # Jika tombol 's' ditekan, simpan gambar ke folder
    if key == ord('s'):
        jumlah_gambar += 1
        file_path = f"{path_folder}/img_{jumlah_gambar}.jpg"
        cv2.imwrite(file_path, frame)
        print(f"[BERHASIL] Gambar {jumlah_gambar} tersimpan.")

    # Jika tombol 'q' ditekan, keluar dari program
    elif key == ord('q'):
        break

# 4. Lepaskan kamera dan tutup semua jendela
cap.release()
cv2.destroyAllWindows()
print(f"\n[SELESAI] Total {jumlah_gambar} gambar tersimpan untuk {nama}.")