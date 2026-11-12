# Sistem Absensi dan Peringatan Orang Asing Berbasis Pengenalan Wajah

Sistem real-time untuk gedung kerja: wajah pekerja yang sudah terdaftar dikenali dan
absensinya tercatat otomatis, sedangkan orang tidak dikenal memicu alarm suara.

## Alur sistem
Kamera → deteksi wajah (SCRFD) → embedding wajah (ArcFace, wajah diluruskan otomatis)
→ pencocokan dengan database → dikenali: absensi tercatat | Unknown: alarm

Fitur pendukung: pelacakan wajah antar frame, pemungutan suara dari beberapa frame terakhir,
saringan wajah kecil/buram/menoleh, jeda waktu sebelum alarm dan absensi.

## Struktur folder
- `src/` : kode program
- `models/` : model InsightFace `buffalo_sc` (tidak ikut repo)
- `data/` : database wajah dan catatan absensi (tidak ikut repo)

## Cara memasang
1. Pasang library (urutan ini penting):
   ```
   pip install numpy opencv-contrib-python onnx onnxruntime scikit-image scipy
   pip install --no-deps insightface
   ```
   Jangan memasang `opencv-python`, karena bentrok dengan `opencv-contrib-python`.
2. Unduh model dari
   https://github.com/deepinsight/insightface/releases/download/model-zoo/buffalo_sc.zip
   lalu ekstrak sehingga file `.onnx` berada di `models/buffalo_sc/`
   (`det_500m.onnx` dan `w600k_mbf.onnx`).

## Cara memakai
1. Daftarkan wajah: `python src/register.py` (tekan `S` untuk menyimpan, `Q` untuk selesai)
2. Jalankan sistem: `python src/main.py` (tekan `Q` untuk keluar)

Semua pengaturan (threshold, ukuran wajah minimum, durasi alarm, dll.) ada di `src/config.py`.

## Hasil pengujian

| Jarak | Terdeteksi? | Lebar kotak (px) | Dikenali? | Skor | FPS |
|---|---|---|---|---|---|
| 1 m | ... | ... | ... | ... | ... |
| 3 m | ... | ... | ... | ... | ... |
| 5 m | ... | ... | ... | ... | ... |

| Pengujian | Jumlah orang | Hasil |
|---|---|---|
| Penolakan orang asing | ... | skor maksimum ..., THRESHOLD = ... |
| Pengenalan orang terdaftar | ... | skor persentil 5 = ... |

Jumlah penguji kecil, jadi hasil bersifat indikatif, bukan angka akurasi statistik.

## Batasan
- Belum ada anti-spoofing: foto atau video wajah di layar bisa dianggap orang terdaftar.
- Akurasi dipengaruhi cahaya, jarak, dan kualitas kamera.
- Pengenalan hanya dilakukan pada wajah yang cukup besar; wajah jauh hanya ditandai "Mendekat".

## Privasi
Hanya embedding (deretan angka) yang disimpan, bukan foto wajah. Semua orang yang terdaftar
dan diuji sudah memberi izin. Folder `data/` tidak diunggah ke repo.

## Komponen pihak ketiga dan lisensi
| Komponen | Fungsi | Lisensi (cek ulang di sumbernya) |
|---|---|---|
| InsightFace `buffalo_sc`: SCRFD (`det_500m`) dan ArcFace-MBF (`w600k_mbf`) | Deteksi dan pengenalan wajah | Kode MIT; model hanya untuk riset non-komersial |
| OpenCV, NumPy, ONNX Runtime | Pendukung | Lisensi terbuka |

Pemakaian model pihak ketiga dalam lomba ini sudah disetujui pembina. Model non-komersial
tidak boleh dipakai untuk produk komersial tanpa lisensi tambahan.