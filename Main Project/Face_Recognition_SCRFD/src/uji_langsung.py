import csv
import os
from datetime import datetime

import cv2
import numpy as np

import config
from camera import Kamera
from detect import Detektor, potong_wajah, hadap_depan
from recognize import Pengenal

PATH_HASIL = os.path.join(config.DIR_DATA, "hasil_uji.csv")
HIJAU = (0, 255, 0)
MERAH = (0, 0, 255)
KUNING = (0, 255, 255)
PUTIH = (255, 255, 255)


def sesi(kamera, detektor, pengenal, label, terdaftar):
    """Mengukur skor wajah terbesar di layar sampai Q ditekan. Mengembalikan daftar skor."""
    skor_list = []
    nomor = 0
    teks, warna = "Menunggu wajah...", KUNING
    kotak_terakhir = None

    while True:
        frame = kamera.baca()
        if frame is None:
            break

        if nomor % config.PROSES_SETIAP == 0:
            kotak_terakhir = None
            hasil = detektor.deteksi_penuh(frame)
            if not hasil:
                teks, warna = "Tidak ada wajah", KUNING
            else:
                d = max(hasil, key=lambda h: (h["kotak"][2] - h["kotak"][0]) *
                                              (h["kotak"][3] - h["kotak"][1]))
                kotak_terakhir = d["kotak"]
                x1, y1, x2, y2 = kotak_terakhir
                ukuran = min(x2 - x1, y2 - y1)

                if ukuran < config.UKURAN_WAJAH_MIN:
                    teks, warna = f"Terlalu kecil ({ukuran}px), mendekat", KUNING
                elif not hadap_depan(d["kps"]):
                    teks, warna = "Menoleh, tidak dihitung", KUNING
                else:
                    if d["emb"] is not None:
                        emb = d["emb"]
                        if terdaftar:
                            nama, skor = label, pengenal.skor_untuk(emb, label)
                        else:
                            semua = {n: pengenal._skor_nama(emb, dd)
                                     for n, dd in pengenal.db.items()}
                            nama = max(semua, key=semua.get)
                            skor = semua[nama]
                        skor_list.append(skor)
                        if terdaftar and skor < 0.45:
                            os.makedirs(os.path.join(config.DIR_DATA, "skor_rendah"), exist_ok=True)
                            cv2.imwrite(os.path.join(config.DIR_DATA, "skor_rendah",
                                f"{label}_{skor:.2f}_{nomor}.jpg"), frame)

                        lolos = skor >= config.THRESHOLD
                        teks = f"{nama}: {skor:.2f}  ({'LOLOS' if lolos else 'ditolak'})"
                        # terdaftar: lolos itu baik. Orang asing: lolos itu buruk.
                        baik = lolos if terdaftar else not lolos
                        warna = HIJAU if baik else MERAH

        nomor += 1

        if kotak_terakhir is not None:
            x1, y1, x2, y2 = kotak_terakhir
            cv2.rectangle(frame, (x1, y1), (x2, y2), warna, 2)
        cv2.putText(frame, teks, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, warna, 2)

        if skor_list:
            a = np.array(skor_list)
            info = f"{label} | n={len(a)} min={a.min():.2f} maks={a.max():.2f}"
        else:
            info = f"{label} | n=0"
        cv2.putText(frame, info, (10, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.7, PUTIH, 2)
        cv2.putText(frame, f"THRESHOLD={config.THRESHOLD}  Q=selesai", (10, 95),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, PUTIH, 2)

        cv2.imshow("Uji langsung", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cv2.destroyAllWindows()
    return skor_list


def ringkas(label, terdaftar, skor_list):
    if not skor_list:
        print("Tidak ada data. Pastikan wajah besar, jelas, dan menghadap kamera.")
        return

    a = np.array(skor_list)
    jenis = "terdaftar" if terdaftar else "asing"
    persen_lolos = float((a >= config.THRESHOLD).mean() * 100)
    p5, p95 = np.percentile(a, 5), np.percentile(a, 95)

    print(f"\n=== Hasil: {label} ({jenis}) ===")
    print(f"Jumlah pengukuran : {len(a)}")
    print(f"Skor minimum      : {a.min():.2f}")
    print(f"Skor persentil 5  : {p5:.2f}")
    print(f"Skor rata-rata    : {a.mean():.2f}")
    print(f"Skor persentil 95 : {p95:.2f}")
    print(f"Skor maksimum     : {a.max():.2f}")
    print(f"THRESHOLD         : {config.THRESHOLD}")
    print(f"Di atas threshold : {persen_lolos:.0f}% dari pengukuran")
    if terdaftar:   
        print("Baca: orang terdaftar sebaiknya hampir selalu di atas threshold.")
    else:
        print("Baca: orang asing sebaiknya hampir tidak pernah di atas threshold.")
        print("      Skor maksimum ini (B) menentukan batas bawah THRESHOLD yang aman.")

    baru = not os.path.exists(PATH_HASIL)
    with open(PATH_HASIL, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if baru:
            w.writerow(["waktu", "label", "jenis", "jumlah", "min", "p5", "rata2",
                        "p95", "maks", "threshold", "persen_lolos"])
        w.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), label, jenis, len(a),
                    f"{a.min():.3f}", f"{p5:.3f}", f"{a.mean():.3f}",
                    f"{p95:.3f}", f"{a.max():.3f}", config.THRESHOLD, f"{persen_lolos:.0f}"])
    print(f"(tersimpan ke {PATH_HASIL})")


def main():
    pengenal = Pengenal()
    if not pengenal.db:
        print("Database kosong. Daftarkan wajah dulu: python src\\register.py")
        return

    print("Terdaftar :", {k: len(v) for k, v in pengenal.db.items()})
    print("THRESHOLD :", config.THRESHOLD)
    print("Gunakan nama sandi untuk orang asing (misalnya Penguji A), bukan nama asli.")

    kamera = Kamera()
    detektor = Detektor()
    try:
        while True:
            label = input("\nNama penguji (kosongkan untuk selesai): ").strip()
            if not label:
                break
            terdaftar = label in pengenal.db
            print(f"Jenis uji: {'orang terdaftar' if terdaftar else 'orang asing'}")
            print("Hadap kamera, bergerak sedikit (dekat, jauh, menoleh ringan). "
                  "Tekan Q pada jendela video untuk mengakhiri.")
            ringkas(label, terdaftar, sesi(kamera, detektor, pengenal, label, terdaftar))
    finally:
        kamera.tutup()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()