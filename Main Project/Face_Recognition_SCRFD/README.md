# Sistem Absensi dan Peringatan Orang Asing
# Berbasis Pengenalan Wajah dan Active Liveness Detection

Sistem real-time yang mengenali wajah orang yang sudah terdaftar,
mencatat kehadirannya secara otomatis, dan membunyikan peringatan
ketika ada orang yang tidak dikenal.

Sistem dilengkapi Active Liveness Detection menggunakan MediaPipe
Face Landmarker untuk memverifikasi respons gerakan wajah sebelum
proses absensi dilakukan.

Hasil pengenalan dan peringatan dikirim sebagai notifikasi
ke grup Telegram.

Dibuat untuk NAIS Competition 2026 oleh tim SMK Negeri 3 Singaraja.

## Contoh penggunaan
- **Sekolah dan kampus:** absensi siswa atau mahasiswa di pintu kelas atau gerbang, dan
  peringatan untuk orang luar yang masuk area sekolah.
- **Perkantoran dan pabrik:** kehadiran karyawan dan kontrol akses area kerja.
- **Asrama, kos, dan apartemen:** pengenalan penghuni di pintu masuk.
- **Laboratorium dan ruang terbatas:** pembatasan akses hanya untuk anggota terdaftar.
- **Acara dan komunitas:** pencatatan kehadiran peserta dan anggota.

## Fitur
- Deteksi dan pengenalan wajah real-time dari webcam atau kamera lain.
- Absensi otomatis ke `data/absensi.csv`, dengan jeda agar orang yang sama tidak tercatat berulang.
- Peringatan orang tidak dikenal: alarm berbunyi dan kejadian tercatat di `data/peringatan.csv`.
- Notifikasi Telegram untuk absensi dan peringatan, serta pengiriman rekap CSV sebagai lampiran.
- Pelacakan wajah antar frame dan pemungutan suara dari beberapa frame terakhir, sehingga satu frame
  yang meleset tidak langsung menjadi absensi atau alarm.
- Saringan wajah terlalu kecil, buram, dan menoleh.
- Active Liveness Detection menggunakan MediaPipe Face Landmarker
  dengan 478 titik landmark wajah.
- Verifikasi respons kedipan mata sebelum absensi dilakukan.
- Deteksi dugaan pemalsuan wajah: jika wajah tidak memberikan
  respons kedipan selama lebih dari 10 detik, sistem mencatat
  peringatan dan mengirim notifikasi.

## Alur sistem
```
Kamera
  |
  v
Deteksi wajah (SCRFD)
  |
  v
Active Liveness (MediaPipe)
  |
  +-- Wajah memberikan respons kedipan
  |       |
  |       v
  |   Lolos pemeriksaan Active Liveness
  |       |
  |       v
  |   ArcFace + pencocokan database
  |       |
  |       +-- Dikenali
  |       |     -> Absensi tercatat
  |       |     -> Nada berhasil
  |       |     -> Notifikasi Telegram
  |       |
  |       +-- Unknown
  |             -> Peringatan orang asing
  |             -> Alarm
  |             -> Notifikasi Telegram
  |
  +-- Belum memberikan respons kedipan
          |
          v
      Status memverifikasi
          |
          v
      Lebih dari 10 detik
          |
          v
      Dugaan pemalsuan wajah
          |
          +-- Catatan peringatan
          +-- Alarm
          +-- Notifikasi Telegram
```

## Struktur folder
```
Face_Recognition_SCRFD/
├── README.md
├── requirements.txt
├── .env_contoh
│
├── models/
│   ├── buffalo_sc/
│   │   ├── det_500m.onnx
│   │   └── w600k_mbf.onnx
│   │
│   └── face_landmarker.task
│
├── data/
│    
└── src/
    ├── config.py
    ├── camera.py
    ├── detect.py
    ├── recognize.py
    ├── register.py
    ├── attendance.py
    ├── alarm.py
    ├── notifikasi.py
    ├── liveness.py
    ├── main.py
    ├── uji_langsung.py
    ├── kirim_csv.py
    ├── cari_chat_id.py

## Cara memasang

Gunakan Python 3.14. Di Mac Intel, gunakan Python 3.12 atau 3.13, karena versi baru
`onnxruntime` tidak lagi menyediakan paket untuk Intel.

### Windows
```
git clone https://github.com/justzxm/NAIS-Competition-2026.git
cd "NAIS-Competition-2026\Main Project\Face_Recognition_SCRFD"
pip install -r requirements.txt
```

### macOS
```
git clone https://github.com/justzxm/NAIS-Competition-2026.git
cd "NAIS-Competition-2026/Main Project/Face_Recognition_SCRFD"
pip install -r requirements.txt
```
Jalankan juga `Install Certificates.command` (folder Applications, Python 3.x) sekali setelah
memasang Python dari python.org.

Unduh model dari `https://github.com/deepinsight/insightface/releases/download/model-zoo/buffalo_sc.zip`,
lalu taruh `det_500m.onnx` dan `w600k_mbf.onnx` langsung di `models/buffalo_sc/`.

### Model Active Liveness
```
Unduh model Face Landmarker dari Google:

https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task

Simpan file tersebut di:

models/face_landmarker.task

Model ini digunakan oleh MediaPipe Face Landmarker
untuk mendeteksi 478 titik landmark wajah.
```

## Cara memakai

1. Daftarkan wajah (tekan `S` untuk menyimpan, `Q` untuk selesai; ambil 6-8 foto dengan sudut
   dan cahaya sedikit berbeda):
   ```
   src\register.py        (Windows)
   src/register.py          (macOS)
   ```
2. Jalankan sistem (tekan `Q` untuk keluar):
   ```
   src\main.py            (Windows)
   src/main.py              (macOS)
   ```

Warna kotak di layar: hijau berarti dikenali, merah berarti Unknown, kuning berarti belum diproses
Kedip untuk mendaftarkan diri ke data absensi.csv, jika tidak berkedip selama 10 detik akan dianggap pemalsuan wajah
(terlalu kecil, buram, atau masih memverifikasi). Saat pertama dijalankan, izinkan akses kamera.

## Pengaturan penting (`src/config.py`)

| Pengaturan | Fungsi |
|---|---|
| `THRESHOLD` | Skor kemiripan minimum agar wajah dianggap orang terdaftar |
| `UKURAN_WAJAH_MIN` | Lebar wajah minimum (piksel) agar diproses; di bawahnya hanya ditandai "Mendekat" |
| `TAJAM_MIN` | Batas ketajaman; di bawahnya wajah dianggap buram |
| `YAW_MIN`, `YAW_MAX` | Batas sudut menoleh yang masih diproses |
| `FRAME_KONFIRMASI` | Berapa kali berturut-turut dikenali sebelum absensi dicatat |
| `JEDA_ABSEN` | Selang waktu (detik) sebelum orang yang sama boleh tercatat lagi |
| `DURASI_UNKNOWN` | Lama (detik) Unknown harus terlihat terus-menerus sebelum alarm berbunyi |
| `JEDA_ALARM` | Selang waktu (detik) antar alarm |
| `NADA_ABSEN`, `NADA_ALARM` | Pola nada (frekuensi Hz, durasi ms) di Windows |

## Notifikasi Telegram

1. Buat bot lewat **@BotFather** di Telegram (`/newbot`), lalu salin tokennya.
2. Buat grup, tambahkan bot ke grup, dan kirim satu pesan di grup.
3. Salin `.env.contoh` menjadi `.env` di folder project, lalu isi token dan chat ID:
   ```
   TELEGRAM_TOKEN=token_dari_BotFather
   TELEGRAM_CHAT_ID=id_grup
   ```
4. Cari chat ID dengan `python src/cari_chat_id.py`.
5. Kirim rekap CSV kapan saja dengan `python src/kirim_csv.py` (opsi `hari_ini` untuk data hari ini).

File `.env` sudah diabaikan Git. **Jangan pernah mengunggah token.** Kalau token bocor, kirim
`/revoke` ke @BotFather. Tanpa `.env`, program tetap berjalan, hanya tanpa notifikasi.

## Hasil pengujian

| Pengujian | Jumlah orang | Hasil |
|---|---|---|
| Pengenalan orang terdaftar | 1 | skor persentil 5 = 0.54 |
| Penolakan orang asing | 1 | rata-rata 0.19, persentil 95 = 0.36, maksimum 0.57 |

`THRESHOLD` yang dipakai: 0.4

| Jarak | Terdeteksi? | Lebar kotak (px) | Dikenali? | Skor | FPS |
|---|---|---|---|---|---|
| 1 m | Ya | 100+ | Ya | 65-70 | 16-20+ |
| 2 m | ... | ... | ... | ... | ... |
| 3 m | ... | ... | ... | ... | ... |

Jumlah penguji masih kecil, jadi hasil bersifat indikatif, bukan angka akurasi statistik.
Pada model FaceNet yang dipakai sebelumnya, skor orang terdaftar dan orang asing hampir
tumpang tindih; ArcFace memisahkan sebagian besar pengukuran dengan jelas.

## Batasan
- Belum ada anti-spoofing: foto atau video wajah di layar bisa dianggap orang terdaftar.
- Jarak pengenalan dibatasi resolusi kamera (sekitar 2 m dengan kamera saat ini). Wajah yang
  terlalu kecil tidak cukup rinci untuk dikenali, jadi hanya ditandai "Mendekat".
- Akurasi dipengaruhi cahaya dan sudut wajah.
- Penguji masih sedikit.

## Rencana pengembangan
- Kamera beresolusi tinggi atau lensa lebih sempit untuk jarak lebih jauh.
- Anti-spoofing dan enkripsi database.
- Persetujuan dan kebijakan privasi untuk pengguna di sekolah.

## Privasi dan etika
- Hanya embedding (deretan angka) yang disimpan, bukan foto wajah. Folder `data/` tidak diunggah ke repo.
- Pendaftaran wajah hanya dilakukan atas persetujuan orang yang bersangkutan.
- Notifikasi Telegram berisi nama dan waktu kehadiran, dan semua anggota grup dapat melihatnya.
  Tambahkan hanya orang yang berhak, dan beri tahu orang yang terdaftar. Foto wajah tidak dikirim.
- Pengguna sebaiknya diberi tahu bahwa sistem ini aktif di area tersebut, dan datanya  hanya
  dipakai untuk absensi dan keamanan.
- Sistem ini masih prototipe dan belum layak menjadi satu-satunya pengaman pada area sensitif.

## Komponen pihak ketiga dan lisensi

| Komponen | Fungsi | Lisensi (cek ulang di sumbernya) |
|---|---|---|
| InsightFace `buffalo_sc`: SCRFD (`det_500m`) dan ArcFace-MBF (`w600k_mbf`) | Deteksi dan pengenalan wajah | Kode MIT; model hanya untuk riset non-komersial |
| OpenCV, NumPy, ONNX Runtime | Pengolahan gambar dan menjalankan model | Lisensi terbuka |
| Telegram Bot API | Notifikasi | Ketentuan layanan Telegram |
| MediaPipe Face Landmarker (`face_landmarker.task`) | Deteksi 478 titik landmark wajah untuk Active Liveness Detection | Apache License 2.0 |


## Pemecahan masalah

| Gejala | Penyebab dan solusi |
|---|---|
| `pip install` gagal, tidak menemukan versi yang cocok | Versi Python tidak sesuai. Pakai Python 3.14 (Mac Intel: 3.12 atau 3.13) |
| `CERTIFICATE_VERIFY_FAILED` saat mengunduh model | macOS: jalankan `Install Certificates.command` |
| `Kamera tidak bisa dibuka` | Tutup aplikasi lain yang memakai kamera, izinkan akses kamera, atau ubah `KAMERA_ID` di `config.py` |
| `No module named 'config'` | Jalankan dari folder `Face_Recognition_SCRFD`, bukan dari folder lain |
| "Database kosong" | Daftarkan wajah dulu dengan `register.py` |
| Telegram gagal (HTTP 404, 400, atau 403) | Token atau chat ID salah, atau bot belum masuk grup. Jalankan `cari_chat_id.py` dan `uji_telegram.py` |
