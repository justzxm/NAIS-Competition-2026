import threading
import time
import config

try:
    import winsound
except ImportError:      # bukan Windows
    winsound = None

_terakhir = 0.0
_sedang_bunyi = False


def _bunyi():
    global _sedang_bunyi
    try:
        for _ in range(3):
            if winsound:
                winsound.Beep(1000, 300)
                winsound.Beep(1500, 300)
            else:
                print("\a", end="", flush=True)
                time.sleep(0.6)
    finally:
        _sedang_bunyi = False


def bunyikan():
    """Membunyikan alarm di thread terpisah agar video tidak membeku."""
    global _terakhir, _sedang_bunyi
    sekarang = time.time()
    if _sedang_bunyi or sekarang - _terakhir < config.JEDA_ALARM:
        return False
    _terakhir = sekarang
    _sedang_bunyi = True
    threading.Thread(target=_bunyi, daemon=True).start()
    return True