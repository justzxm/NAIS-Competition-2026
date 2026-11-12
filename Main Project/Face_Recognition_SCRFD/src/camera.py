import cv2
import config


class Kamera:
    def __init__(self):
        self.cap = cv2.VideoCapture(config.KAMERA_ID)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.LEBAR)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.TINGGI)
        if not self.cap.isOpened():
            raise RuntimeError("Kamera tidak bisa dibuka. Cek KAMERA_ID di config.py")

    def baca(self):
        ok, frame = self.cap.read()
        return frame if ok else None

    def tutup(self):
        self.cap.release()