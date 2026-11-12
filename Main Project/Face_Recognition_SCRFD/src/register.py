import os
import pickle
import cv2
import config
from camera import Kamera
from detect import Detektor, hadap_depan


def muat_db():
    if os.path.exists(config.PATH_DATABASE):
        with open(config.PATH_DATABASE, "rb") as f:
            return pickle.load(f)
    return {}


def main():
    nama = input("Nama orang yang didaftarkan: ").strip()
    if not nama:
        print("Nama tidak boleh kosong")
        return

    db = muat_db()
    db.setdefault(nama, [])
    kamera = Kamera()
    detektor = Detektor()
    pesan = ""

    try:
        while True:
            frame = kamera.baca()
            if frame is None:
                break

            tampil = frame.copy()
            wajah = detektor.deteksi_penuh(frame)
            for d in wajah:
                x1, y1, x2, y2 = d["kotak"]
                cv2.rectangle(tampil, (x1, y1), (x2, y2), (0, 255, 0), 2)

            cv2.putText(tampil, f"{nama}: {len(db[nama])} foto | S=simpan  Q=selesai",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(tampil, pesan, (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.imshow("Daftar Wajah", tampil)

            tombol = cv2.waitKey(1) & 0xFF
            if tombol == ord("s"):
                if len(wajah) != 1:
                    pesan = "Harus tepat 1 wajah di layar"
                else:
                    d = wajah[0]
                    x1, y1, x2, y2 = d["kotak"]
                    if min(x2 - x1, y2 - y1) < config.UKURAN_WAJAH_MIN:
                        pesan = "Wajah terlalu kecil, mendekat"
                    elif not hadap_depan(d["kps"]):
                        pesan = "Terlalu menoleh, hadap lebih lurus"
                    elif d["emb"] is None:
                        pesan = "Embedding tidak tersedia"
                    else:
                        db[nama].append(d["emb"])
                        pesan = f"Tersimpan ({len(db[nama])} foto)"
            elif tombol == ord("q"):
                break
    finally:
        kamera.tutup()
        cv2.destroyAllWindows()

    with open(config.PATH_DATABASE, "wb") as f:
        pickle.dump(db, f)
    print("Database disimpan:", {k: len(v) for k, v in db.items()})


if __name__ == "__main__":
    main()