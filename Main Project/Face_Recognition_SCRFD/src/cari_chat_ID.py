import json
import urllib.request
import notifikasi

token, _ = notifikasi._ambil_kredensial()
if not token:
    print("TELEGRAM_TOKEN belum diisi di file .env")
    raise SystemExit

try:
    with urllib.request.urlopen(
            f"https://api.telegram.org/bot{token}/getUpdates", timeout=10) as r:
        data = json.load(r)
except Exception as e:
    print("Gagal:", type(e).__name__)
    raise SystemExit

ditemukan = {}
for u in data.get("result", []):
    pesan = u.get("message") or u.get("channel_post") or {}
    chat = pesan.get("chat")
    if chat:
        ditemukan[chat["id"]] = (chat.get("type"), chat.get("title") or chat.get("first_name", ""))

if not ditemukan:
    print("Belum ada pesan. Kirim pesan ke bot (atau di grup) lalu jalankan ulang.")
for cid, (tipe, nama) in ditemukan.items():
    print(cid, tipe, nama)