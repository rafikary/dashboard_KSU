from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import pandas as pd
import os

from routes.ksu import ksu_bp
from routes.auth import auth_bp
from routes.export import export_bp
from routes.dataquality import dataquality_bp
from routes.logs import logs_bp
# Disabled routes (not relevant for KSU):
# from routes.trend import trend_bp
# from routes.items import items_bp
# from routes.customers import customers_bp
# from routes.geography import geography
# from routes.category import category
# from routes.marketing import marketing_bp
# from routes.insights import insights_bp
# from routes.chatbot import chatbot_bp
# from routes.aireport import aireport_bp
# from routes.piutang import piutang_bp

app = Flask(__name__)
CORS(app)

# ── Setup Direktori ───────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
KSU_PARQUET_PATH = os.path.join(DATA_DIR, "ksu.parquet")

# ── Fungsi Load Data ke RAM ───────────────────────────────────────────
def load_data_to_ram():
    """Fungsi ini dipanggil saat startup dan saat di-trigger oleh sync_data.py"""
    # Load KSU data
    if os.path.exists(KSU_PARQUET_PATH):
        df_ksu = pd.read_parquet(KSU_PARQUET_PATH)
        
        # Parse tanggal
        df_ksu["tglnominatif"] = pd.to_datetime(df_ksu["tglnominatif"])
        
        # Trim whitespace
        for col in ["kode", "nama", "flag"]:
            if col in df_ksu.columns:
                df_ksu[col] = df_ksu[col].astype(str).str.strip()
        
        app.config["DF_KSU"] = df_ksu
        print(f"[OK] Data KSU berhasil di-load ke RAM : {len(df_ksu):,} rows")
    else:
        app.config["DF_KSU"] = pd.DataFrame()
        print("[WARNING] File ksu.parquet belum ada! Silakan jalankan 'python sync_data.py' terlebih dahulu.")

# Eksekusi load pertama kali saat server Flask baru menyala
load_data_to_ram()

# ── Init AI Chatbot (opsional, butuh Ollama) ──────────────────────────────────
# Disabled for KSU dashboard
# try:
#     from chatbot_ai import init_ai_chatbot
#     init_ai_chatbot()
# except Exception as _e:
#     print(f"[AI Chatbot] Tidak diinisialisasi: {_e}")

# ── Helper status reset (pakai file agar multi-process Flask bisa baca) ──
import json

RESET_STATUS_FILE = os.path.join(BASE_DIR, 'data', 'reset_status.json')

def write_reset_status(state, message):
    os.makedirs(os.path.dirname(RESET_STATUS_FILE), exist_ok=True)
    with open(RESET_STATUS_FILE, 'w') as f:
        json.dump({'state': state, 'message': message}, f)

def read_reset_status():
    if os.path.exists(RESET_STATUS_FILE):
        with open(RESET_STATUS_FILE, 'r') as f:
            return json.load(f)
    return {'state': 'idle', 'message': ''}

# ── Endpoint Rahasia untuk Refresh RAM ────────────────────────────────
@app.route("/api/internal/reload-data", methods=["POST"])
def reload_data():
    """Endpoint ini akan ditembak oleh sync_data.py setiap kali sinkronisasi selesai"""
    try:
        load_data_to_ram()
        # Disabled AI chatbot sync for KSU
        # try:
        #     from chatbot_ai import build_sqlite_from_parquet
        #     build_sqlite_from_parquet()
        #     print("[OK] Database AI berhasil disinkronkan.")
        # except Exception as e:
        #     print(f"[ERROR] Gagal sinkronisasi DB AI: {e}")
            
        return jsonify({
            "status": "success", 
            "message": "RAM berhasil di-refresh dengan data Parquet terbaru!"
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/internal/full-reset-sync", methods=["POST"])
def full_reset_sync():
    """Hapus semua parquet dan tarik ulang semua data dari awal (dipanggil manual via tombol)"""
    if read_reset_status()['state'] == 'running':
        return jsonify({"status": "error", "message": "Reset sedang berjalan, harap tunggu..."}), 400
    import threading, subprocess, sys
    def run():
        write_reset_status('running', 'Menghapus data lama dan menarik ulang dari DB...')
        try:
            result = subprocess.run(
                [sys.executable, 'sync_data.py', '--full-reset'],
                cwd=BASE_DIR,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                load_data_to_ram()
                df = app.config.get('DF_PENJUALAN')
                rows = len(df) if df is not None else 0
                write_reset_status('done', f'Berhasil! Data berhasil dimuat ulang ({rows:,} baris).')
            else:
                write_reset_status('error', f'Sync gagal: {result.stderr[-300:] if result.stderr else "unknown error"}')
        except Exception as e:
            write_reset_status('error', f'Gagal: {str(e)}')
    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "success", "message": "Reset dimulai..."}), 200

@app.route("/api/internal/sync-status", methods=["GET"])
def sync_status():
    return jsonify(read_reset_status())

# ── Endpoint Metadata (Untuk Tahun & Tanggal Terakhir) ────────────────
@app.route("/api/metadata")
def get_metadata():
    df = app.config.get("DF_KSU")
    if df is not None and not df.empty:
        # Ambil tanggal terkecil dan terbesar
        min_date = df["tglnominatif"].min()
        max_date = df["tglnominatif"].max()
        
        # Array untuk translate bulan ke Bahasa Indonesia
        bulan_indo = ['', 'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni', 
                      'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember']
        
        # Format menjadi "1 Februari 2026"
        tgl_terakhir = f"{max_date.day} {bulan_indo[max_date.month]} {max_date.year}"
        
        return jsonify({
            "start_year": int(min_date.year),
            "end_year": int(max_date.year),
            "last_import": tgl_terakhir
        })
        
    return jsonify({"start_year": 2021, "end_year": 2026, "last_import": "Belum ada data"})

# ── Register Blueprints ───────────────────────────────────────────────
app.register_blueprint(ksu_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(export_bp, url_prefix="/api/export")
app.register_blueprint(dataquality_bp)
app.register_blueprint(logs_bp)

# Disabled blueprints (not relevant for KSU):
# app.register_blueprint(trend_bp, url_prefix="/api/trend")
# app.register_blueprint(items_bp, url_prefix="/api/items")
# app.register_blueprint(customers_bp, url_prefix="/api/customers")
# app.register_blueprint(geography)
# app.register_blueprint(category)
# app.register_blueprint(marketing_bp)
# app.register_blueprint(insights_bp)
# app.register_blueprint(chatbot_bp)
# app.register_blueprint(aireport_bp)
# app.register_blueprint(piutang_bp)

# ── AI Chatbot Logs Endpoints ─────────────────────────────────────────────────
# ── Serve Frontend ────────────────────────────────────────────────────
@app.route("/")
def serve_frontend():
    return send_from_directory("../frontend", "index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)