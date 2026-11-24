import csv
import io
import os
import pickle
import sys
import tempfile
import threading
import time
import warnings
from datetime import date

warnings.filterwarnings("ignore", message=".*SimilarityTransform.*")

import cv2
import numpy as np
from flask import Flask, Response, jsonify, render_template_string, request

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(ROOT_DIR, "src")
WEB_DIR = os.path.join(ROOT_DIR, "web")

if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import alarm
import attendance
import config
import notifikasi
from camera import Kamera
from detect import Detektor, hadap_depan, ketajaman, potong_wajah
from liveness import Kedipan
from recognize import Pelacak, Pengenal

HIJAU = (0, 255, 0)
MERAH = (0, 0, 255)
KUNING = (0, 255, 255)
PUTIH = (255, 255, 255)

app = Flask(__name__)

_lock = threading.Lock()
_mode = "idle"  # "idle" | "absensi" | "daftar"
_kamera = None
_detektor = None
_latest_jpeg = None
_pesan_sistem = "Siap"
_status_daftar = {"aktif": False, "pesan": "Belum ada pendaftaran berjalan.", "ok": False}
_worker_thread = None


def _buat_frame_placeholder(teks="Menyiapkan kamera..."):
    kanvas = np.zeros((360, 640, 3), dtype=np.uint8)
    kanvas[:] = (24, 24, 27)
    cv2.putText(
        kanvas,
        teks,
        (30, 185),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        (229, 231, 235),
        2,
    )
    ok, buf = cv2.imencode(".jpg", kanvas, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    return buf.tobytes() if ok else b""


_PLACEHOLDER_JPEG = _buat_frame_placeholder()


def _set_pesan(teks):
    global _pesan_sistem
    with _lock:
        _pesan_sistem = teks


def _get_detektor():
    global _detektor
    if _detektor is None:
        _set_pesan("Memuat model deteksi & pengenalan wajah...")
        _detektor = Detektor()
    return _detektor


def _buka_kamera():
    global _kamera
    if _kamera is None:
        _set_pesan(f"Membuka kamera ID {config.KAMERA_ID}...")
        _kamera = Kamera()
    return _kamera


def _tutup_kamera():
    global _kamera
    if _kamera is not None:
        try:
            _kamera.tutup()
        except Exception:
            pass
        _kamera = None


def _simpan_jpeg(frame):
    global _latest_jpeg
    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
    if ok:
        with _lock:
            _latest_jpeg = buf.tobytes()


def _nilai_hidup(kedipan, kotak, jalur, t):
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


def _loop_absensi():
    global _mode
    try:
        kamera = _buka_kamera()
        detektor = _get_detektor()
        pengenal = Pengenal()
        pelacak = Pelacak()
        kedipan = Kedipan()

        status_live = "AKTIF" if kedipan.aktif else f"NONAKTIF ({kedipan.alasan})"
        _set_pesan(f"Mode absensi aktif | Anti-spoofing: {status_live}")

        hitung_nama = {}
        unknown_sejak = None
        unknown_terakhir = 0.0
        tampilan = []
        pesan, waktu_pesan = "", 0.0
        nomor = 0
        fps, t_lalu = 0.0, time.time()

        while True:
            with _lock:
                if _mode != "absensi":
                    break

            frame = kamera.baca()
            if frame is None:
                _set_pesan("Gagal membaca frame dari kamera.")
                time.sleep(0.05)
                continue

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

                    tajam = ketajaman(wajah)
                    ditahan = None
                    if tajam < config.TAJAM_MIN:
                        ditahan = f"buram {tajam:.0f}"
                    elif not hadap_depan(d["kps"]):
                        ditahan = "menoleh"

                    if ditahan:
                        if stabil and stabil != "Unknown":
                            catatan = ditahan
                        else:
                            tampilan.append((kotak, ditahan.capitalize(), KUNING))
                            continue
                    else:
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
                        hidup, info, curiga = _nilai_hidup(kedipan, kotak, jalur, t_proses)
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

                if curiga_nama:
                    attendance.catat_asing(f"dugaan_spoofing:{curiga_nama}")
                    notifikasi.kirim_spoof(curiga_nama)
                    alarm.bunyikan()
                    pesan, waktu_pesan = "PERINGATAN: dugaan pemalsuan wajah!", time.time()

                if ada_unknown:
                    if unknown_sejak is None:
                        unknown_sejak = t_proses
                    unknown_terakhir = t_proses
                elif (
                    unknown_sejak is not None
                    and t_proses - unknown_terakhir > config.TOLERANSI_UNKNOWN
                ):
                    unknown_sejak = None

                if (
                    unknown_sejak is not None
                    and t_proses - unknown_sejak >= config.DURASI_UNKNOWN
                ):
                    if alarm.bunyikan():
                        pesan, waktu_pesan = (
                            "PERINGATAN: orang tidak dikenal!",
                            time.time(),
                        )
                        attendance.catat_asing()
                        notifikasi.kirim_asing()

            nomor += 1

            for (x1, y1, x2, y2), teks, warna in tampilan:
                cv2.rectangle(frame, (x1, y1), (x2, y2), warna, 2)
                cv2.putText(
                    frame,
                    f"{teks} {x2 - x1}px",
                    (x1, max(y1 - 8, 20)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    warna,
                    2,
                )

            sekarang = time.time()
            fps = 0.9 * fps + 0.1 * (1 / max(sekarang - t_lalu, 1e-6))
            t_lalu = sekarang
            cv2.putText(
                frame,
                f"FPS: {fps:.1f}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                PUTIH,
                2,
            )
            if pesan and sekarang - waktu_pesan < 4:
                cv2.putText(
                    frame,
                    pesan,
                    (10, 65),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.8,
                    KUNING,
                    2,
                )

            _simpan_jpeg(frame)
            time.sleep(0.01)

    except Exception as e:
        _set_pesan(f"Error kamera/model: {e}")
        with _lock:
            _mode = "idle"
            _latest_jpeg = _buat_frame_placeholder(f"Error: {str(e)[:45]}")
    finally:
        _tutup_kamera()


def _proses_pendaftaran(nama, target_sampel=7, batas_detik=15):
    global _mode, _status_daftar
    sampel = []
    mulai = time.time()

    try:
        kamera = _buka_kamera()
        detektor = _get_detektor()

        while len(sampel) < target_sampel and (time.time() - mulai) < batas_detik:
            frame = kamera.baca()
            if frame is None:
                time.sleep(0.05)
                continue

            deteksi = detektor.deteksi_penuh(frame)
            pesan_layar = f"Daftar {nama}: {len(sampel)}/{target_sampel}"

            if len(deteksi) == 1:
                d = deteksi[0]
                x1, y1, x2, y2 = d["kotak"]
                wajah = potong_wajah(frame, d["kotak"])
                layak = (
                    min(x2 - x1, y2 - y1) >= config.UKURAN_WAJAH_MIN
                    and wajah is not None
                    and ketajaman(wajah) >= config.TAJAM_MIN
                    and hadap_depan(d["kps"])
                    and d["emb"] is not None
                )
                if layak:
                    sampel.append(d["emb"])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), HIJAU, 2)
                    pesan_layar = f"Tersimpan {len(sampel)}/{target_sampel} ({nama})"
                else:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), KUNING, 2)
                    pesan_layar = "Hadap depan, cukup dekat & tidak buram"
            elif len(deteksi) > 1:
                pesan_layar = "Pastikan hanya 1 wajah di kamera"

            cv2.putText(
                frame,
                pesan_layar,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                PUTIH,
                2,
            )
            _simpan_jpeg(frame)
            time.sleep(0.08)

        if len(sampel) >= 3:
            db = {}
            if os.path.exists(config.PATH_DATABASE):
                with open(config.PATH_DATABASE, "rb") as f:
                    db = pickle.load(f)
            db.setdefault(nama, [])
            db[nama].extend(sampel)
            with open(config.PATH_DATABASE, "wb") as f:
                pickle.dump(db, f)

            with _lock:
                _status_daftar = {
                    "aktif": False,
                    "ok": True,
                    "pesan": f"Berhasil mendaftarkan {len(sampel)} sampel wajah untuk '{nama}'.",
                }
            _set_pesan(f"Wajah '{nama}' berhasil didaftarkan.")
        else:
            with _lock:
                _status_daftar = {
                    "aktif": False,
                    "ok": False,
                    "pesan": f"Gagal: baru mendapat {len(sampel)}/{target_sampel} sampel. Coba lagi.",
                }
            _set_pesan("Pendaftaran belum cukup sampel.")
    except Exception as e:
        with _lock:
            _status_daftar = {
                "aktif": False,
                "ok": False,
                "pesan": f"Kesalahan saat pendaftaran: {e}",
            }
        _set_pesan(f"Error pendaftaran: {e}")
    finally:
        with _lock:
            _mode = "idle"
        _tutup_kamera()


@app.route("/")
def beranda():
    html_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(html_path):
        with open(html_path, encoding="utf-8") as f:
            return f.read()
    return render_template_string("<h1>web/index.html belum ditemukan</h1>")


@app.route("/api/frame")
def api_frame():
    with _lock:
        data = _latest_jpeg or _PLACEHOLDER_JPEG
    return Response(
        io.BytesIO(data).getvalue(),
        mimetype="image/jpeg",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


@app.route("/api/status")
def api_status():
    with _lock:
        return jsonify({"mode": _mode, "message": _pesan_sistem})


@app.route("/api/mode", methods=["POST"])
def api_mode():
    global _mode, _worker_thread, _latest_jpeg
    payload = request.get_json(silent=True) or {}
    mode_baru = payload.get("mode", "idle")

    if mode_baru not in ("idle", "absensi"):
        return jsonify({"ok": False, "message": "Mode tidak dikenal."}), 400

    with _lock:
        if _mode == "daftar":
            return jsonify({"ok": False, "message": "Tunggu pendaftaran wajah selesai dulu."}), 409
        _mode = mode_baru
        if mode_baru == "absensi":
            _latest_jpeg = _buat_frame_placeholder("Memulai kamera & model wajah...")

    if mode_baru == "idle":
        _tutup_kamera()
        with _lock:
            _latest_jpeg = None
        _set_pesan("Kamera dihentikan.")
        return jsonify({"ok": True, "message": "Kamera dihentikan."})

    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=_loop_absensi, daemon=True)
        _worker_thread.start()

    return jsonify({"ok": True, "message": "Memulai mode absensi & keamanan..."})


@app.route("/api/register", methods=["POST"])
def api_register():
    global _mode, _status_daftar, _latest_jpeg
    payload = request.get_json(silent=True) or {}
    nama = (payload.get("nama") or "").strip()
    if not nama:
        return jsonify({"ok": False, "message": "Nama wajib diisi."}), 400

    with _lock:
        if _mode == "daftar":
            return jsonify({"ok": False, "message": "Pendaftaran sedang berjalan."}), 409
        _mode = "daftar"
        _latest_jpeg = _buat_frame_placeholder(f"Menyiapkan daftar: {nama}...")
        _status_daftar = {
            "aktif": True,
            "ok": False,
            "pesan": f"Mengambil sampel wajah untuk '{nama}'...",
        }

    threading.Thread(target=_proses_pendaftaran, args=(nama,), daemon=True).start()
    return jsonify({"ok": True, "message": f"Pendaftaran '{nama}' dimulai."})


@app.route("/api/register-status")
def api_register_status():
    with _lock:
        return jsonify(_status_daftar)


def _baca_csv(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


@app.route("/api/absensi")
def api_absensi():
    return jsonify({"rows": _baca_csv(config.PATH_ABSENSI)})


@app.route("/api/peringatan")
def api_peringatan():
    return jsonify({"rows": _baca_csv(config.PATH_PERINGATAN)})


def _saring_hari_ini(path, tanggal):
    nama = os.path.splitext(os.path.basename(path))[0]
    sementara = os.path.join(tempfile.gettempdir(), f"{nama}_{tanggal}.csv")
    jumlah = 0
    with open(path, encoding="utf-8", newline="") as sumber, \
            open(sementara, "w", encoding="utf-8", newline="") as tujuan:
        baca, tulis = csv.reader(sumber), csv.writer(tujuan)
        kepala = next(baca, None)
        if kepala:
            tulis.writerow(kepala)
        for baris in baca:
            if any(sel.startswith(tanggal) for sel in baris):
                tulis.writerow(baris)
                jumlah += 1
    return sementara, jumlah


@app.route("/api/kirim-csv", methods=["POST"])
def api_kirim_csv():
    if not notifikasi.aktif():
        return jsonify({"ok": False, "message": "Telegram belum aktif atau .env belum lengkap."}), 400

    payload = request.get_json(silent=True) or {}
    hari_ini = bool(payload.get("hari_ini", False))
    tanggal = date.today().isoformat()

    daftar = (
        (config.PATH_ABSENSI, "Rekap absensi"),
        (config.PATH_PERINGATAN, "Catatan peringatan orang asing"),
    )
    hasil = []

    for path, ket in daftar:
        if not os.path.exists(path):
            hasil.append(f"{ket}: file belum ada")
            continue

        kirim_path, sementara = path, None
        if hari_ini:
            kirim_path, jumlah = _saring_hari_ini(path, tanggal)
            sementara = kirim_path
            if jumlah == 0:
                os.remove(sementara)
                hasil.append(f"{ket}: tidak ada data hari ini")
                continue
            ket = f"{ket} {tanggal} ({jumlah} baris)"

        ok = notifikasi.kirim_file(kirim_path, ket)
        hasil.append(f"{ket}: {'terkirim' if ok else 'gagal'}")
        if sementara and os.path.exists(sementara):
            os.remove(sementara)

    return jsonify({"ok": True, "message": " | ".join(hasil)})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
