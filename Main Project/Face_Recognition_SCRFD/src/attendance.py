import csv
import os
import time
from datetime import datetime
import config

_terakhir = {}   # nama -> waktu terakhir tercatat


def _tulis(path, kepala, baris):
    baru = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        penulis = csv.writer(f)
        if baru:
            penulis.writerow(kepala)
        penulis.writerow(baris)


def _sekarang():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def catat(nama):
    """Mencatat absensi ke CSV. Mengembalikan True jika benar-benar tercatat."""
    sekarang = time.time()
    if nama in _terakhir and sekarang - _terakhir[nama] < config.JEDA_ABSEN:
        return False
    _terakhir[nama] = sekarang
    _tulis(config.PATH_ABSENSI, ["nama", "waktu"], [nama, _sekarang()])
    return True


def catat_asing():
    """Mencatat satu kejadian orang tidak dikenal ke data/peringatan.csv."""
    _tulis(config.PATH_PERINGATAN, ["waktu", "kejadian"],
           [_sekarang(), "orang_tidak_dikenal"])