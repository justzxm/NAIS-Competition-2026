import csv
import os
import sys
import tempfile
from datetime import date

import config
import notifikasi

# Pemakaian:
#   python src/kirim_csv.py             -> kirim seluruh isi CSV
#   python src/kirim_csv.py hari_ini    -> kirim hanya baris hari ini

if not notifikasi.aktif():
    raise SystemExit("Telegram belum aktif: cek file .env dan TELEGRAM_AKTIF di config.py")

hari_ini = len(sys.argv) > 1 and sys.argv[1] == "hari_ini"
tanggal = date.today().isoformat()


def saring_hari_ini(path):
    """Membuat salinan sementara berisi baris hari ini saja. Mengembalikan (jalur, jumlah baris)."""
    nama = os.path.splitext(os.path.basename(path))[0]
    sementara = os.path.join(tempfile.gettempdir(), f"{nama}_{tanggal}.csv")
    jumlah = 0
    with open(path, encoding="utf-8", newline="") as sumber, \
            open(sementara, "w", encoding="utf-8", newline="") as tujuan:
        baca, tulis = csv.reader(sumber), csv.writer(tujuan)
        kepala = next(baca, None)
        if kepala:
            tulis.writerow(kepala)
        for baris in baca:
            if any(sel.startswith(tanggal) for sel in baris):
                tulis.writerow(baris)
                jumlah += 1
    return sementara, jumlah


DAFTAR = (
    (config.PATH_ABSENSI, "Rekap absensi"),
    (config.PATH_PERINGATAN, "Catatan peringatan orang asing"),
)

for path, ket in DAFTAR:
    if not os.path.exists(path):
        print(f"{ket}: belum ada ({os.path.basename(path)})")
        continue

    kirim_path, sementara = path, None
    if hari_ini:
        kirim_path, jumlah = saring_hari_ini(path)
        sementara = kirim_path
        if jumlah == 0:
            print(f"{ket}: tidak ada data hari ini ({tanggal})")
            os.remove(sementara)
            continue
        ket = f"{ket} {tanggal} ({jumlah} baris)"

    ok = notifikasi.kirim_file(kirim_path, ket)
    print(f"{ket}: {'terkirim' if ok else 'GAGAL'}")
    if sementara and os.path.exists(sementara):
        os.remove(sementara)