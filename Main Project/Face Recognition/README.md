# NAIS Competition 2026 - Face Recognition Module

Proyek ini merupakan bagian dari aplikasi **FaceRecApp** yang dikembangkan untuk ajang **NAIS Competition 2026**. Modul ini berfokus pada sistem pengenalan wajah (*Face Recognition*) berbasis Python dan OpenCV, yang dirancang untuk melakukan ekstraksi dataset, pelatihan model, dan deteksi wajah secara nyata (*real-time*).

---

## 📁 Struktur Direktori Proyek

Proyek ini diatur dengan struktur direktori hierarkis berikut:

```text
FaceRecApp/
│
├── .gitignore
├── README.md
│
└── Main Project/
    └── Face Recognition/
        ├── 1_capture.py                      # Skrip untuk pengambil/ekstraksi data wajah
        ├── 2_train.py                        # Skrip untuk melatih model pengenalan wajah
        ├── 3_recognize.py                    # Skrip utama untuk pengenalan wajah secara real-time
        └── haarcascade_frontalface_default.xml # Pre-trained Cascade Classifier untuk deteksi wajah
