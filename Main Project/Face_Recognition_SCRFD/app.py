import csv
import os
import sys
import tempfile
import threading
import time
from collections import deque
from datetime import date
import pickle

import cv2
from flask import Flask, jsonify, render_template_string, request, send_file

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
_status_daftar = {"aktif": False, "pesan": "Belum ada pendaftaran berjalan.", "ok": False}
_worker_thread = None
_stop_worker = threading.Event()


def _get_detektor():
    global _detektor
    if _detektor is None:
        _detektor = Detektor()
    return _detektor


def _buka_kamera():
    global _kamera
    if _kamera is None:
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


def _loop_absensi():
    kamera = _buka_kamera()
    detektor = _get_detektor()
    pengenal = Pengenal()
    pelacak = Pelacak()

    hitung_nama = {}
    unknown_sejak = None
    unknown_terakhir = 0.0
    tampilan = []
    pesan, waktu_pesan = "", 0.0
    nomor = 0
    fps, t_lalu = 0.0, time.time()

    while not _stop_worker.is_set():
        with _lock:
            if _mode != "absensi":
                break

        frame = kamera.baca()
        if frame is None:
            time.sleep(0.05)
            continue

        if nomor % config.PROSES_SETIAP == 0:
            t_proses = time.time()
            tampilan = []
            dikenali = set()
            ada_unknown = False

            for d in detektor.deteksi_penuh(frame):
                kotak = d["kotak"]
                x1, y1, x2, y2 = kotak

                if min(x2 - x1, y2 - y1) < config.UKURAN_WAJAH_MIN:
                    tampilan.append((kotak, "Mendekat", KUNING))
                    continue

                wajah = potong_wajah(frame, kotak)
                if wajah is None:
                    continue

                jalur = pelacak.cari(kotak, t_proses)
                stabil = Pelacak.nama_stabil(jalur)

                tajam = ketajaman(wajah)
                if tajam < config.TAJAM_MIN:
                    tampilan.append((kotak, f"Buram {tajam:.0f}", KUNING))
                    continue

                if not hadap_depan(d["kps"]):
                    if stabil and stabil != "Unknown":
                        dikenali.add(stabil)
                        tampilan.append((kotak, f"{stabil} (menoleh)", HIJAU))
                    else:
                        tampilan.append((kotak, "Menoleh", KUNING))
                    continue

                emb = d["emb"]
                if emb is None:
                    continue
                nama, skor = pengenal.cocokkan(emb)

                if nama == "Unknown" and jalur["nama"] not in (None, "Unknown"):
                    skor_tahan = pengenal.skor_untuk(emb, jalur["nama"])
                    if skor_tahan >= config.THRESHOLD_TAHAN:
                        nama, skor = jalur["nama"], skor_tahan

                jalur["riwayat"].append(nama)
                stabil = Pelacak.nama_stabil(jalur)
                if stabil is not None:
                    jalur["nama"] = stabil

                if stabil is None:
                    tampilan.append((kotak, "Memverifikasi", KUNING))
                elif stabil == "Unknown":
                    ada_unknown = True
                    tampilan.append((kotak, f"Unknown {skor:.2f}", MERAH))
                else:
                    dikenali.add(stabil)
                    tampilan.append((kotak, f"{stabil} {skor:.2f}", HIJAU))

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

        _simpan_jpeg(frame)
        time.sleep(0.01)


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

            cv2.putText(frame, pesan_layar, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, PUTIH, 2)
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
        else:
            with _lock:
                _status_daftar = {
                    "aktif": False,
                    "ok": False,
                    "pesan": f"Gagal: baru mendapat {len(sampel)}/{target_sampel} sampel. Coba lagi dengan pencahayaan cukup.",
                }
    except Exception as e:
        with _lock:
            _status_daftar = {
                "aktif": False,
                "ok": False,
                "pesan": f"Kesalahan saat pendaftaran: {e}",
            }
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
        data = _latest_jpeg
    if not data:
        return ("", 204)
    return send_file(
        io.BytesIO(data) if "io" in sys.modules else __import__("io").BytesIO(data),
        mimetype="image/jpeg",
    )


@app.route("/api/mode", methods=["POST"])
def api_mode():
    global _mode, _worker_thread
    payload = request.get_json(silent=True) or {}
    mode_baru = payload.get("mode", "idle")

    if mode_baru not in ("idle", "absensi"):
        return jsonify({"ok": False, "message": "Mode tidak dikenal."}), 400

    with _lock:
        if _mode == "daftar":
            return jsonify({"ok": False, "message": "Tunggu pendaftaran wajah selesai dulu."}), 409
        _mode = mode_baru

    if mode_baru == "idle":
        _tutup_kamera()
        return jsonify({"ok": True, "message": "Kamera dihentikan."})

    if _worker_thread is None or not _worker_thread.is_alive():
        _worker_thread = threading.Thread(target=_loop_absensi, daemon=True)
        _worker_thread.start()

    return jsonify({"ok": True, "message": "Mode absensi & keamanan aktif."})


@app.route("/api/register", methods=["POST"])
def api_register():
    global _mode, _status_daftar
    payload = request.get_json(silent=True) or {}
    nama = (payload.get("nama") or "").strip()
    if not nama:
        return jsonify({"ok": False, "message": "Nama wajib diisi."}), 400

    with _lock:
        if _mode == "daftar":
            return jsonify({"ok": False, "message": "Pendaftaran sedang berjalan."}), 409
        _mode = "daftar"
        _status_daftar = {
            "aktif": True,
            "ok": False,
            "pesan": f"Mengambil sampel wajah untuk '{nama}'...",
        }

    threading.Thread(target=_proses_pendaftaran, args=(nama,), daemon=True).start()
    return jsonify({"ok": True, "message": f"Pendaftaran '{nama}' dimulai. Arahkan wajah ke kamera."})


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
