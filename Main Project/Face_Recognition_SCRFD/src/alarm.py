import io
import math
import queue
import struct
import subprocess
import sys
import threading
import time
import wave

import config

try:
    import winsound
except ImportError:      # bukan Windows
    winsound = None

LAJU = 22050             # sampel per detik
_antrean = queue.Queue(maxsize=5)
_terakhir_alarm = 0.0
_pekerja_jalan = False
_kunci = threading.Lock()
_WAV = {}                # "absen" / "alarm" -> data WAV (byte)


def _bangun_wav(daftar_nada, ulang=1, awal_ms=0):
    """Mengubah daftar (frekuensi Hz, durasi ms) menjadi satu rekaman WAV di memori."""
    data = bytearray(b"\x00\x00" * int(LAJU * awal_ms / 1000))
    for _ in range(ulang):
        for frek, durasi in daftar_nada:
            n = int(LAJU * durasi / 1000)
            if frek <= 0:
                data += b"\x00\x00" * n                    # jeda diam
                continue
            frek = max(37, min(LAJU // 2 - 1, int(frek)))
            tepi = max(1, int(0.005 * LAJU))               # fade 5 ms agar tidak berbunyi "klik"
            for i in range(n):
                redam = min(1.0, i / tepi, (n - i) / tepi)
                nilai = int(32767 * 0.6 * redam * math.sin(2 * math.pi * frek * i / LAJU))
                data += struct.pack("<h", nilai)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(LAJU)
        w.writeframes(bytes(data))
    return buf.getvalue()


def _siapkan():
    if winsound is None:
        return
    try:
        _WAV["absen"] = _bangun_wav(config.NADA_ABSEN, awal_ms=config.JEDA_AWAL_MS)
        _WAV["alarm"] = _bangun_wav(config.NADA_ALARM, config.ULANG_ALARM,
                                    awal_ms=config.JEDA_AWAL_MS)
    except Exception:
        _WAV.clear()                                       # nanti jatuh ke Beep biasa


def _putar_beep(daftar_nada):
    """Cadangan: Beep satu per satu (lebih rentan tersendat)."""
    for frek, durasi in daftar_nada:
        if frek <= 0:
            time.sleep(durasi / 1000)
        else:
            winsound.Beep(max(37, min(32767, int(frek))), int(durasi))


def _putar_mac(nama_suara):
    subprocess.run(["afplay", f"/System/Library/Sounds/{nama_suara}.aiff"],
                   capture_output=True)


def _nada_alarm():
    if winsound:
        if "alarm" in _WAV:
            winsound.PlaySound(_WAV["alarm"], winsound.SND_MEMORY)
        else:
            for _ in range(config.ULANG_ALARM):
                _putar_beep(config.NADA_ALARM)
    elif sys.platform == "darwin":
        for _ in range(config.ULANG_ALARM):
            _putar_mac(config.SUARA_MAC_ALARM)
    else:
        for _ in range(config.ULANG_ALARM):
            print("\a", end="", flush=True)
            time.sleep(0.4)


def _nada_absen():
    if winsound:
        if "absen" in _WAV:
            winsound.PlaySound(_WAV["absen"], winsound.SND_MEMORY)
        else:
            _putar_beep(config.NADA_ABSEN)
    elif sys.platform == "darwin":
        _putar_mac(config.SUARA_MAC_ABSEN)
    else:
        print("\a", end="", flush=True)


def _pekerja():
    while True:
        jenis = _antrean.get()
        try:
            if jenis == "alarm":
                _nada_alarm()
            else:
                _nada_absen()
        except Exception:
            pass                       # gagal bersuara tidak boleh menghentikan program
        finally:
            _antrean.task_done()


def _antre(jenis):
    global _pekerja_jalan
    with _kunci:
        if not _pekerja_jalan:
            threading.Thread(target=_pekerja, daemon=True).start()
            _pekerja_jalan = True
    try:
        _antrean.put_nowait(jenis)
        return True
    except queue.Full:
        return False


def bunyikan():
    """Alarm orang asing. Dibatasi oleh JEDA_ALARM. True jika alarm benar-benar diantrekan."""
    global _terakhir_alarm
    sekarang = time.time()
    if sekarang - _terakhir_alarm < config.JEDA_ALARM:
        return False
    if _antre("alarm"):
        _terakhir_alarm = sekarang
        return True
    return False


def umumkan_absen(nama=None):
    """Nada tanda absensi tercatat."""
    if not config.SUARA_ABSEN:
        return False
    return _antre("absen")


def tunggu_selesai():
    """Menunggu semua suara selesai (dipakai untuk pengujian)."""
    _antrean.join()


_siapkan()