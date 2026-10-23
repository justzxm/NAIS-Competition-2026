import cv2

def periksa_webcam():
    # Mencoba membuka indeks kamera pertama (0)
    # cv2.CAP_DSHOW opsional untuk Windows agar loading kamera lebih cepat
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    
    # Memeriksa apakah kamera berhasil dibuka
    if cap.isOpened():
        print("✅ Webcam terdeteksi dan siap digunakan!")
        # Selalu lepaskan kamera setelah selesai diperiksa
        cap.release()
        return True
    else:
        print("❌ Tidak ada webcam yang terdeteksi pada perangkat ini.")
        return False

if __name__ == "__main__":
    periksa_webcam()

# kode dibuat oleh Gemini AI
