import os
import pickle
from collections import Counter, deque
import numpy as np
import config


class Pengenal:
    def __init__(self):
        self.db = {}
        if os.path.exists(config.PATH_DATABASE):
            with open(config.PATH_DATABASE, "rb") as f:
                self.db = pickle.load(f)

    def _skor_nama(self, emb, daftar_emb):
        """Rata-rata dari TOP_K skor tertinggi, supaya satu foto mirip saja tidak cukup."""
        skor = sorted((float(np.dot(emb, e)) for e in daftar_emb), reverse=True)
        teratas = skor[:config.TOP_K]
        return sum(teratas) / len(teratas)

    def skor_untuk(self, emb, nama):
        """Skor terhadap satu nama tertentu (untuk batas 'tahan')."""
        if nama not in self.db:
            return -1.0
        return self._skor_nama(emb, self.db[nama])

    def cocokkan(self, emb):
        """Mengembalikan (nama, skor). 'Unknown' jika skor rendah atau hasilnya ambigu."""
        if not self.db:
            return "Unknown", -1.0

        hasil = sorted(((self._skor_nama(emb, d), n) for n, d in self.db.items()),
                       reverse=True)
        skor_terbaik, nama_terbaik = hasil[0]

        if skor_terbaik < config.THRESHOLD:
            return "Unknown", skor_terbaik

        if len(hasil) > 1 and skor_terbaik - hasil[1][0] < config.SELISIH_MIN:
            return "Unknown", skor_terbaik

        return nama_terbaik, skor_terbaik


def _iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    irisan = max(0, x2 - x1) * max(0, y2 - y1)
    luas = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - irisan
    return irisan / luas if luas > 0 else 0.0


class Pelacak:
    """Mengikuti tiap wajah antar frame, lalu memilih nama dari beberapa hasil terakhir."""

    def __init__(self):
        self.daftar = []

    def cari(self, kotak, sekarang):
        terbaik, iou_terbaik = None, config.IOU_TRACK
        for jalur in self.daftar:
            nilai = _iou(kotak, jalur["kotak"])
            if nilai > iou_terbaik:
                terbaik, iou_terbaik = jalur, nilai
        if terbaik is None:
            terbaik = {"riwayat": deque(maxlen=config.RIWAYAT), "nama": None}
            self.daftar.append(terbaik)
        terbaik["kotak"] = kotak
        terbaik["terakhir"] = sekarang
        return terbaik

    def bersihkan(self, sekarang):
        self.daftar = [j for j in self.daftar
                       if sekarang - j["terakhir"] <= config.TRACK_HILANG]

    @staticmethod
    def nama_stabil(jalur):
        """Nama yang paling sering muncul di riwayat. None jika datanya belum cukup."""
        if len(jalur["riwayat"]) < config.RIWAYAT_MIN:
            return None
        return Counter(jalur["riwayat"]).most_common(1)[0][0]