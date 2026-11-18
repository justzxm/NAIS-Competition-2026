import json
import os
import queue
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime

import config

_antrean = queue.Queue(maxsize=20)
_jalan = False
_kunci = threading.Lock()
_kredensial = None
_asing_terakhir = 0.0


def _baca_env():
    nilai = {}
    if os.path.exists(config.PATH_ENV):
        with open(config.PATH_ENV, encoding="utf-8") as f:
            for baris in f:
                baris = baris.strip()
                if not baris or baris.startswith("#") or "=" not in baris:
                    continue
                k, v = baris.split("=", 1)
                nilai[k.strip()] = v.strip().strip('"').strip("'")
    return nilai


def _ambil_kredensial():
    global _kredensial
    if _kredensial is None:
        env = _baca_env()
        token = os.environ.get("TELEGRAM_TOKEN") or env.get("TELEGRAM_TOKEN", "")
        chat = os.environ.get("TELEGRAM_CHAT_ID") or env.get("TELEGRAM_CHAT_ID", "")
        _kredensial = (token, chat)
    return _kredensial


def aktif():
    token, chat = _ambil_kredensial()
    return config.TELEGRAM_AKTIF and bool(token) and bool(chat)


def _waktu():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def kirim_sekarang(teks):
    """Mengirim pesan teks saat ini juga. True jika berhasil. Token tidak pernah dicetak."""
    token, chat = _ambil_kredensial()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat, "text": teks}).encode("utf-8")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=data),
                                    timeout=config.TELEGRAM_TIMEOUT) as r:
            return r.status == 200
    except Exception as e:
        print("Telegram gagal:", type(e).__name__, getattr(e, "code", ""))
        return False


def kirim_file(path, keterangan=""):
    """Mengirim sebuah file (misalnya CSV) sebagai dokumen. True jika berhasil."""
    if not aktif() or not os.path.exists(path):
        return False
    token, chat = _ambil_kredensial()
    batas = "----BatasForm7d3fa9"
    with open(path, "rb") as f:
        isi = f.read()
    badan = b""
    for nama, nilai in (("chat_id", chat), ("caption", keterangan)):
        badan += (f'--{batas}\r\nContent-Disposition: form-data; name="{nama}"'
                  f"\r\n\r\n{nilai}\r\n").encode("utf-8")
    badan += (f'--{batas}\r\nContent-Disposition: form-data; name="document"; '
              f'filename="{os.path.basename(path)}"\r\nContent-Type: text/csv\r\n\r\n'
              ).encode("utf-8") + isi + f"\r\n--{batas}--\r\n".encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendDocument", data=badan,
        headers={"Content-Type": f"multipart/form-data; boundary={batas}"})
    try:
        with urllib.request.urlopen(req, timeout=config.TELEGRAM_TIMEOUT * 3) as r:
            return r.status == 200
    except Exception as e:
        print("Telegram gagal:", type(e).__name__, getattr(e, "code", ""))
        return False


def _pekerja():
    while True:
        teks = _antrean.get()
        try:
            kirim_sekarang(teks)
            time.sleep(1.1)            # Telegram membatasi laju pesan per chat
        finally:
            _antrean.task_done()


def kirim(teks):
    """Mengantrekan pesan agar video tidak tersendat. Tidak melakukan apa pun jika belum aktif."""
    global _jalan
    if not aktif():
        return False
    with _kunci:
        if not _jalan:
            threading.Thread(target=_pekerja, daemon=True).start()
            _jalan = True
    try:
        _antrean.put_nowait(teks)
        return True
    except queue.Full:
        return False


def kirim_absen(nama):
    if not config.TELEGRAM_KIRIM_ABSEN:
        return False
    return kirim(f"✅ {nama} hadir ({_waktu()})")


def kirim_asing():
    global _asing_terakhir
    if not config.TELEGRAM_KIRIM_ASING:
        return False
    sekarang = time.time()
    if sekarang - _asing_terakhir < config.JEDA_NOTIF_ASING:
        return False
    if kirim(f"⚠️ Orang tidak dikenal terdeteksi ({_waktu()})"):
        _asing_terakhir = sekarang
        return True
    return False