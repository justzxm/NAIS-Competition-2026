import csv
import os
import time
from datetime import datetime
import config

_terakhir = {}   # nama -> waktu terakhir tercatat


def catat(nama):
    """Mencatat absensi ke CSV. Mengembalikan True jika benar-benar tercatat."""
    sekarang = time.time()
    if nama in _terakhir and sekarang - _terakhir[nama] < config.JEDA_ABSEN:
        return False
    _terakhir[nama] = sekarang

    file_baru = not os.path.exists(config.PATH_ABSENSI)
    with open(config.PATH_ABSENSI, "a", newline="", encoding="utf-8") as f:
        penulis = csv.writer(f)
        if file_baru:
            penulis.writerow(["nama", "waktu"])
        penulis.writerow([nama, datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    return True