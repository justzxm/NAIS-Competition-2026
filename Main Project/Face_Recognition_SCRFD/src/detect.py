import cv2
import numpy as np
from insightface.app import FaceAnalysis
import config


class Detektor:
    def __init__(self):
        self.app = FaceAnalysis(
            name=config.NAMA_PAKET,
            root=config.BASE,
            allowed_modules=["detection", "recognition"],
            providers=["CPUExecutionProvider"],
        )
        self.app.prepare(ctx_id=-1, det_size=config.DET_SIZE)

    def deteksi_penuh(self, frame):
        """Daftar dict: kotak, skor deteksi, 5 titik wajah (kps), dan embedding ArcFace (emb)."""
        hasil = []
        for f in self.app.get(frame):
            if f.det_score < config.SKOR_DETEKSI_MIN:
                continue
            x1, y1, x2, y2 = [int(v) for v in f.bbox]
            emb = getattr(f, "embedding", None)
            if emb is not None:
                emb = emb / np.linalg.norm(emb)      # dinormalisasi agar np.dot = cosine
            hasil.append({
                "kotak": (x1, y1, x2, y2),
                "skor": float(f.det_score),
                "kps": getattr(f, "kps", None),
                "emb": emb,
            })
        return hasil

    def deteksi(self, frame):
        """Bentuk lama: daftar (x1, y1, x2, y2, skor)."""
        return [(*d["kotak"], d["skor"]) for d in self.deteksi_penuh(frame)]


def potong_wajah(frame, kotak):
    """Memotong wajah dari frame, dengan sedikit margin. None jika hasilnya kosong."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = kotak[:4]
    mx = int((x2 - x1) * config.MARGIN)
    my = int((y2 - y1) * config.MARGIN)
    x1, y1 = max(x1 - mx, 0), max(y1 - my, 0)
    x2, y2 = min(x2 + mx, w), min(y2 + my, h)
    wajah = frame[y1:y2, x1:x2]
    return wajah if wajah.size > 0 else None


def ketajaman(wajah):
    """Ukuran ketajaman wajah. Potongan diseragamkan ukurannya agar angkanya sebanding."""
    abu = cv2.cvtColor(cv2.resize(wajah, (112, 112)), cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(abu, cv2.CV_64F).var())


def hadap_depan(kps):
    """True jika wajah cukup menghadap kamera, dihitung dari posisi mata dan hidung."""
    if kps is None:
        return True
    mata_kiri, mata_kanan, hidung = kps[0], kps[1], kps[2]
    if mata_kanan[0] - mata_kiri[0] <= 1:
        return False
    rasio = (hidung[0] - mata_kiri[0]) / max(mata_kanan[0] - hidung[0], 1e-6)
    return config.YAW_MIN <= rasio <= config.YAW_MAX