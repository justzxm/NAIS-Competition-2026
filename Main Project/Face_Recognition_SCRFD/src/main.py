import time
import cv2
import config
import attendance
import alarm
from camera import Kamera
from detect import Detektor, potong_wajah, ketajaman, hadap_depan
from recognize import Pengenal, Pelacak

HIJAU = (0, 255, 0)
MERAH = (0, 0, 255)
KUNING = (0, 255, 255)
PUTIH = (255, 255, 255)


def main():
    kamera = Kamera()
    detektor = Detektor()
    pengenal = Pengenal()
    pelacak = Pelacak()
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

            if nomor % config.PROSES_SETIAP == 0:
                t_proses = time.time()
                tampilan = []
                dikenali = set()
                ada_unknown = False

                for d in detektor.deteksi_penuh(frame):
                    kotak = d["kotak"]
                    x1, y1, x2, y2 = kotak

                    # saringan 1: wajah terlalu kecil
                    if min(x2 - x1, y2 - y1) < config.UKURAN_WAJAH_MIN:
                        tampilan.append((kotak, "Mendekat", KUNING))
                        continue

                    wajah = potong_wajah(frame, kotak)
                    if wajah is None:
                        continue

                    jalur = pelacak.cari(kotak, t_proses)
                    stabil = Pelacak.nama_stabil(jalur)

                    # saringan 2: gambar buram
                    tajam = ketajaman(wajah)
                    if tajam < config.TAJAM_MIN:
                        tampilan.append((kotak, f"Buram {tajam:.0f}", KUNING))
                        continue

                    # saringan 3: wajah menoleh, jangan ambil keputusan baru
                    if not hadap_depan(d["kps"]):
                        if stabil and stabil != "Unknown":
                            dikenali.add(stabil)
                            tampilan.append((kotak, f"{stabil} (menoleh)", HIJAU))
                        else:
                            tampilan.append((kotak, "Menoleh", KUNING))
                        continue

                    # pengenalan
                    emb = d["emb"]
                    if emb is None:
                        continue
                    nama, skor = pengenal.cocokkan(emb)

                    # batas lebih longgar untuk orang yang barusan dikenali
                    if nama == "Unknown" and jalur["nama"] not in (None, "Unknown"):
                        skor_tahan = pengenal.skor_untuk(emb, jalur["nama"])
                        if skor_tahan >= config.THRESHOLD_TAHAN:
                            nama, skor = jalur["nama"], skor_tahan

                    jalur["riwayat"].append(nama)
                    stabil = Pelacak.nama_stabil(jalur)
                    if stabil is not None:
                        jalur["nama"] = stabil

                    info = f" t={tajam:.0f}" if config.TAMPIL_TAJAM else ""
                    if stabil is None:
                        tampilan.append((kotak, "Memverifikasi", KUNING))
                    elif stabil == "Unknown":
                        ada_unknown = True
                        tampilan.append((kotak, f"Unknown {skor:.2f}{info}", MERAH))
                    else:
                        dikenali.add(stabil)
                        tampilan.append((kotak, f"{stabil} {skor:.2f}{info}", HIJAU))

                pelacak.bersihkan(t_proses)

                # absensi: nama harus dikenali beberapa kali berturut-turut
                for nama in list(hitung_nama):
                    if nama not in dikenali:
                        hitung_nama[nama] = 0
                for nama in dikenali:
                    hitung_nama[nama] = hitung_nama.get(nama, 0) + 1
                    if hitung_nama[nama] == config.FRAME_KONFIRMASI:
                        if attendance.catat(nama):
                            pesan, waktu_pesan = f"Absen tercatat: {nama}", time.time()

                # alarm: Unknown harus terlihat terus-menerus selama DURASI_UNKNOWN detik
                if ada_unknown:
                    if unknown_sejak is None:
                        unknown_sejak = t_proses
                    unknown_terakhir = t_proses
                elif unknown_sejak is not None and t_proses - unknown_terakhir > config.TOLERANSI_UNKNOWN:
                    unknown_sejak = None

                if unknown_sejak is not None and t_proses - unknown_sejak >= config.DURASI_UNKNOWN:
                    if alarm.bunyikan():
                        pesan, waktu_pesan = "PERINGATAN: orang tidak dikenal!", time.time()

            nomor += 1

            # gambar hasil terakhir di setiap frame
            for (x1, y1, x2, y2), teks, warna in tampilan:
                cv2.rectangle(frame, (x1, y1), (x2, y2), warna, 2)
                cv2.putText(frame, teks, (x1, max(y1 - 8, 20)),
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