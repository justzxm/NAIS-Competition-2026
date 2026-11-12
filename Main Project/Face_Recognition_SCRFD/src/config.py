import os

# ---- lokasi ----
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR_DATA = os.path.join(BASE, "data")
os.makedirs(DIR_DATA, exist_ok=True)
PATH_DATABASE = os.path.join(DIR_DATA, "database.pkl")
PATH_ABSENSI = os.path.join(DIR_DATA, "absensi.csv")

# ---- kamera ----
KAMERA_ID = 0
LEBAR = 1280
TINGGI = 720

# ---- deteksi (SCRFD) ----
NAMA_PAKET = "buffalo_sc"
DET_SIZE = (640, 640)        # naikkan ke (960, 960) untuk wajah lebih jauh (lebih lambat)
SKOR_DETEKSI_MIN = 0.5
MARGIN = 0.1                 # tambahan ruang di sekitar wajah saat dipotong

# ---- pengenalan ----
THRESHOLD = 0.4              # skor kemiripan minimum
THRESHOLD_TAHAN = 0.3        # batas lebih rendah untuk orang yang barusan dikenali
TOP_K = 3                    # jumlah skor tertinggi yang dirata-ratakan per orang
SELISIH_MIN = 0.05           # selisih skor minimal antara orang terbaik dan kedua
UKURAN_WAJAH_MIN = 80        # lebar/tinggi kotak (px) minimum agar wajah dikenali
PROSES_SETIAP = 1            # pengenalan dijalankan tiap N frame (naikkan jika lambat)

# ---- kestabilan saat orang bergerak ----
YAW_MIN = 0.4                # rasio hidung terhadap mata; di luar YAW_MIN..YAW_MAX dianggap menoleh
YAW_MAX = 2.5
RIWAYAT = 7                  # jumlah hasil terakhir yang dipakai untuk memilih nama
RIWAYAT_MIN = 4              # minimal hasil terkumpul sebelum keputusan diambil
IOU_TRACK = 0.15             # kemiripan kotak antar frame agar dianggap wajah yang sama
TRACK_HILANG = 1.0           # detik; wajah yang tidak terlihat selama ini dilupakan

# ---- kualitas gambar ----
TAJAM_MIN = 90               # di bawah ini dianggap buram (0 = nonaktif)
TAMPIL_TAJAM = False         # True untuk menampilkan nilai ketajaman saat kalibrasi

# ---- absensi ----
FRAME_KONFIRMASI = 5         # berapa kali berturut-turut dikenali sebelum absen dicatat
JEDA_ABSEN = 60 * 60         # detik; orang yang sama tidak dicatat lagi selama jeda ini

# ---- alarm ----
DURASI_UNKNOWN = 4           # detik Unknown harus terlihat terus-menerus sebelum alarm
TOLERANSI_UNKNOWN = 1.0      # detik; Unknown boleh hilang sebentar tanpa mengulang hitungan
JEDA_ALARM = 10              # detik antar alarm