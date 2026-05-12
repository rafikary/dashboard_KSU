from flask import Flask, send_from_directory
from flask_cors import CORS
import pandas as pd
import os

from routes.ksu import ksu_bp
from routes.auth import auth_bp
from routes.export import export_bp
from routes.dataquality import dataquality_bp
from routes.logs import logs_bp
from routes.internal import internal_bp
from routes.metadata import metadata_bp
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

app.config["BASE_DIR"] = BASE_DIR
app.config["DATA_DIR"] = DATA_DIR
app.config["KSU_PARQUET_PATH"] = KSU_PARQUET_PATH
app.config["RESET_STATUS_FILE"] = os.path.join(DATA_DIR, "reset_status.json")

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


    app.config["LOAD_DATA_TO_RAM"] = load_data_to_ram

# Eksekusi load pertama kali saat server Flask baru menyala
load_data_to_ram()

# ── Init AI Chatbot (opsional, butuh Ollama) ──────────────────────────────────
# Disabled for KSU dashboard
# try:
#     from chatbot_ai import init_ai_chatbot
#     init_ai_chatbot()
# except Exception as _e:
#     print(f"[AI Chatbot] Tidak diinisialisasi: {_e}")

# ── Register Blueprints ───────────────────────────────────────────────
app.register_blueprint(ksu_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(export_bp, url_prefix="/api/export")
app.register_blueprint(dataquality_bp)
app.register_blueprint(logs_bp)
app.register_blueprint(internal_bp)
app.register_blueprint(metadata_bp)

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