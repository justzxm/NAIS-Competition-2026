import os
from collections import deque

import cv2

import config

try:
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision
    _ADA_MEDIAPIPE = True
except Exception:
    _ADA_MEDIAPIPE = False


def _iou(a, b):
    x1, y1 = max(a[0], b[0]), max(a[1], b[1])
    x2, y2 = min(a[2], b[2]), min(a[3], b[3])
    irisan = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    luas = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - irisan
    return irisan / luas if luas > 0 else 0.0


class Kedipan:
    """Mengamati kedipan mata tiap wajah dari MediaPipe Face Landmarker."""

    def __init__(self):
        self.aktif = False
        self.alasan = ""
        self.jalur = []
        self._ts_terakhir = 0

        if not config.LIVENESS_AKTIF:
            self.alasan = "dimatikan di config.py"
            return
        if not _ADA_MEDIAPIPE:
            self.alasan = "library mediapipe belum terpasang"
            return
        if not os.path.exists(config.PATH_LANDMARKER):
            self.alasan = "models/face_landmarker.task tidak ditemukan"
            return
        try:
            with open(config.PATH_LANDMARKER, "rb") as f:
                data = f.read()
            opsi = vision.FaceLandmarkerOptions(
                base_options=mp_python.BaseOptions(model_asset_buffer=data),
                running_mode=vision.RunningMode.VIDEO,
                num_faces=config.LIVENESS_MAKS_WAJAH,
                output_face_blendshapes=True,
            )
            self.landmarker = vision.FaceLandmarker.create_from_options(opsi)
            self.aktif = True
        except Exception as e:
            self.alasan = f"gagal memuat model ({type(e).__name__})"

    # ---- dipanggil setiap frame ----
    def perbarui(self, frame, t):
        if not self.aktif:
            return
        h, w = frame.shape[:2]
        kecil = frame
        if w > config.LIVENESS_LEBAR:
            kecil = cv2.resize(frame, (config.LIVENESS_LEBAR, int(h * config.LIVENESS_LEBAR / w)))
        rgb = cv2.cvtColor(kecil, cv2.COLOR_BGR2RGB)
        citra = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

        ts = int(t * 1000)
        if ts <= self._ts_terakhir:          # MediaPipe mewajibkan waktu yang selalu naik
            ts = self._ts_terakhir + 1
        self._ts_terakhir = ts
        try:
            hasil = self.landmarker.detect_for_video(citra, ts)
        except Exception:
            return

        for i, titik in enumerate(hasil.face_landmarks):
            xs = [p.x * w for p in titik]
            ys = [p.y * h for p in titik]
            kotak = (min(xs), min(ys), max(xs), max(ys))
            jalur = self._jalur_untuk(kotak, t)
            self._perbarui_status(jalur, self._nilai_kedip(hasil, i), t)

        self.jalur = [j for j in self.jalur if t - j["terakhir"] <= config.TRACK_HILANG]

    @staticmethod
    def _nilai_kedip(hasil, i):
        """Skor mata tertutup 0..1. Memakai nilai terkecil dari dua mata (kedipan menutup keduanya)."""
        if not hasil.face_blendshapes or i >= len(hasil.face_blendshapes):
            return None
        skor = {c.category_name: c.score for c in hasil.face_blendshapes[i]}
        kiri, kanan = skor.get("eyeBlinkLeft"), skor.get("eyeBlinkRight")
        if kiri is None or kanan is None:
            return None
        return min(kiri, kanan)

    def _jalur_untuk(self, kotak, t):
        terbaik, nilai = None, config.LIVENESS_IOU
        for j in self.jalur:
            n = _iou(kotak, j["kotak"])
            if n > nilai:
                terbaik, nilai = j, n
        if terbaik is None:
            terbaik = {"tutup": False, "sejak": 0.0, "blink": None,
                       "waktu_kedip": deque(maxlen=10), "jumlah": 0}
            self.jalur.append(terbaik)
        terbaik["kotak"] = kotak
        terbaik["terakhir"] = t
        return terbaik

    @staticmethod
    def _perbarui_status(j, blink, t):
        j["blink"] = blink
        if blink is None:
            return
        if not j["tutup"] and blink >= config.KEDIP_TUTUP:
            j["tutup"] = True
            j["sejak"] = t
        elif j["tutup"] and blink <= config.KEDIP_BUKA:
            j["tutup"] = False
            if t - j["sejak"] <= config.KEDIP_MAKS_DETIK:      # kedipan sungguhan, bukan mata terpejam
                j["waktu_kedip"].append(t)
                j["jumlah"] += 1

    # ---- dipakai main.py ----
    def hidup(self, kotak_scrfd, t):
        """(hidup, jalur_kedipan). hidup = ada cukup kedipan dalam LIVENESS_JENDELA detik terakhir."""
        cx = cy = None
        terbaik, nilai = None, config.LIVENESS_IOU
        for j in self.jalur:
            x1, y1, x2, y2 = j["kotak"]
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            if not (kotak_scrfd[0] <= cx <= kotak_scrfd[2] and kotak_scrfd[1] <= cy <= kotak_scrfd[3]):
                continue
            n = _iou(kotak_scrfd, j["kotak"])
            if n > nilai:
                terbaik, nilai = j, n
        if terbaik is None:
            return False, None
        baru = [x for x in terbaik["waktu_kedip"] if t - x <= config.LIVENESS_JENDELA]
        return len(baru) >= config.LIVENESS_KEDIP_MIN, terbaik