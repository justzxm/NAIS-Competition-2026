import time
import warnings
import cv2

warnings.filterwarnings("ignore", message=".*SimilarityTransform.*")

import config
import attendance
import alarm
import notifikasi
from camera import Kamera
from detect import Detektor, potong_wajah, ketajaman, hadap_depan
from liveness import Kedipan
from recognize import Pengenal, Pelacak

HIJAU = (0, 255, 0)
MERAH = (0, 0, 255)
KUNING = (0, 255, 255)
PUTIH = (255, 255, 255)


def nilai_hidup(kedipan, kotak, jalur, t):
    """Mengembalikan (hidup, info, curiga). Jika fitur nonaktif, semua dianggap hidup."""
    if not kedipan.aktif:
        return True, "", False
    hidup, jk = kedipan.hidup(kotak, t)
    info = ""
    if config.TAMPIL_LIVENESS:
        info = " k=?" if jk is None else f" k={jk['jumlah']}"
    if hidup:
        jalur.pop("mulai_tanpa_kedip", None)
        return True, info, False
    jalur.setdefault("mulai_tanpa_kedip", t)
    curiga = t - jalur["mulai_tanpa_kedip"] >= config.SPOOF_DETIK
    return False, info, curiga


def main():
    kamera = Kamera()
    detektor = Detektor()
    pengenal = Pengenal()
    pelacak = Pelacak()
    kedipan = Kedipan()
    print("Anti-spoofing (kedipan):",
          "AKTIF" if kedipan.aktif else f"NONAKTIF ({kedipan.alasan})")
    if not pengenal.db:
        print("Database kosong. Daftarkan wajah dulu: python src\\register.py")

    hitung_nama = {}          # nama -> berapa kali berturut-turut dikenali
    unknown_sejak = None      # kapan Unknown mulai terlihat terus-menerus
    unknown_terakhir = 0.0    # kapan Unknown terakhir terlihat
    tampilan = []             # hasil proses terakhir: (kotak, teks, warna)
    pesan, waktu_pesan = "", 0.0
    nomor = 0
    fps, t_lalu = 0.0, time.time()

    try:
        while True:
            frame = kamera.baca()
            if frame is None:
                break

            # kedipan diamati di (hampir) setiap frame, karena kedipan sangat singkat
            if nomor % config.LIVENESS_SETIAP == 0:
                kedipan.perbarui(frame, time.time())

            if nomor % config.PROSES_SETIAP == 0:
                t_proses = time.time()
                tampilan = []
                dikenali = set()
                ada_unknown = False
                curiga_nama = None

                for d in detektor.deteksi_penuh(frame):
                    kotak = d["kotak"]
                    x1, y1, x2, y2 = kotak

                    # saringan 1: wajah terlalu kecil
                    if min(x2 - x1, y2 - y1) < config.UKURAN_WAJAH_MIN:
                        tampilan.append((kotak, "Mendekat", KUNING))
                        continue

                    emb = d["emb"]
                    wajah = potong_wajah(frame, kotak)
                    if emb is None or wajah is None:
                        continue

                    jalur = pelacak.cari(kotak, t_proses)
                    stabil = Pelacak.nama_stabil(jalur)
                    catatan = ""
                    skor = None

                    # saringan 2 dan 3: buram atau menoleh, jangan ambil keputusan baru
                    tajam = ketajaman(wajah)
                    ditahan = None
                    if tajam < config.TAJAM_MIN:
                        ditahan = f"buram {tajam:.0f}"
                    elif not hadap_depan(d["kps"]):
                        ditahan = "menoleh"

                    if ditahan:
                        if stabil and stabil != "Unknown":
                            catatan = ditahan          # orang yang sudah dikenali tetap diakui
                        else:
                            tampilan.append((kotak, ditahan.capitalize(), KUNING))
                            continue
                    else:
                        # pengenalan
                        nama, skor = pengenal.cocokkan(emb)
                        if nama == "Unknown" and jalur["nama"] not in (None, "Unknown"):
                            skor_tahan = pengenal.skor_untuk(emb, jalur["nama"])
                            if skor_tahan >= config.THRESHOLD_TAHAN:
                                nama, skor = jalur["nama"], skor_tahan
                        jalur["riwayat"].append(nama)
                        stabil = Pelacak.nama_stabil(jalur)
                        if stabil is not None:
                            jalur["nama"] = stabil

                    skor_txt = f" {skor:.2f}" if skor is not None else ""

                    if stabil is None:
                        tampilan.append((kotak, "Memverifikasi", KUNING))
                    elif stabil == "Unknown":
                        ada_unknown = True
                        tampilan.append((kotak, f"Unknown{skor_txt}", MERAH))
                    else:
                        # dikenali: periksa kedipan (anti-spoofing)
                        hidup, info, curiga = nilai_hidup(kedipan, kotak, jalur, t_proses)
                        akhir = f" ({catatan})" if catatan else ""
                        if hidup:
                            dikenali.add(stabil)
                            tampilan.append((kotak, f"{stabil}{skor_txt}{akhir}{info}", HIJAU))
                        else:
                            tampilan.append((kotak, f"{stabil}: kedipkan mata{info}", KUNING))
                            if curiga and t_proses - jalur.get("spoof_terakhir", 0.0) >= config.JEDA_SPOOF:
                                jalur["spoof_terakhir"] = t_proses
                                curiga_nama = stabil

                pelacak.bersihkan(t_proses)

                # absensi: hanya wajah yang dikenali dan terbukti hidup
                for nama in list(hitung_nama):
                    if nama not in dikenali:
                        hitung_nama[nama] = 0
                for nama in dikenali:
                    hitung_nama[nama] = hitung_nama.get(nama, 0) + 1
                    if hitung_nama[nama] == config.FRAME_KONFIRMASI:
                        if attendance.catat(nama):
                            pesan, waktu_pesan = f"Absen tercatat: {nama}", time.time()
                            alarm.umumkan_absen(nama)
                            notifikasi.kirim_absen(nama)

                # dugaan pemalsuan: dikenali tetapi tidak berkedip selama SPOOF_DETIK
                if curiga_nama:
                    attendance.catat_asing(f"dugaan_spoofing:{curiga_nama}")
                    notifikasi.kirim_spoof(curiga_nama)
                    alarm.bunyikan()
                    pesan, waktu_pesan = "PERINGATAN: dugaan pemalsuan wajah!", time.time()

                # alarm orang asing: Unknown terlihat terus-menerus selama DURASI_UNKNOWN detik
                if ada_unknown:
                    if unknown_sejak is None:
                        unknown_sejak = t_proses
                    unknown_terakhir = t_proses
                elif unknown_sejak is not None and t_proses - unknown_terakhir > config.TOLERANSI_UNKNOWN:
                    unknown_sejak = None

                if unknown_sejak is not None and t_proses - unknown_sejak >= config.DURASI_UNKNOWN:
                    if alarm.bunyikan():
                        pesan, waktu_pesan = "PERINGATAN: orang tidak dikenal!", time.time()
                        attendance.catat_asing()
                        notifikasi.kirim_asing()

            nomor += 1

            for (x1, y1, x2, y2), teks, warna in tampilan:
                cv2.rectangle(frame, (x1, y1), (x2, y2), warna, 2)
                cv2.putText(frame, f"{teks} {x2 - x1}px", (x1, max(y1 - 8, 20)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, warna, 2)

            sekarang = time.time()
            fps = 0.9 * fps + 0.1 * (1 / max(sekarang - t_lalu, 1e-6))
            t_lalu = sekarang
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, PUTIH, 2)
            if pesan and sekarang - waktu_pesan < 4:
                cv2.putText(frame, pesan, (10, 65),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, KUNING, 2)

            cv2.imshow("Sistem Absensi Wajah", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
    finally:
        kamera.tutup()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()