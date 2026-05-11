from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
import pandas as pd
import os

from routes.trend import trend_bp
from routes.items import items_bp
from routes.customers import customers_bp
from routes.geography import geography
from routes.category import category
from routes.marketing import marketing_bp
from routes.dataquality import dataquality_bp
from routes.insights import insights_bp
from routes.export import export_bp
from routes.chatbot import chatbot_bp
from routes.aireport import aireport_bp
from routes.auth import auth_bp
from routes.piutang import piutang_bp
from routes.logs import logs_bp

app = Flask(__name__)
CORS(app)

# ── Setup Direktori ───────────────────────────────────────────────────
BASE_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(BASE_DIR, "data")
PARQUET_PATH = os.path.join(DATA_DIR, "penjualan.parquet")

# ── Fungsi Load Data ke RAM ───────────────────────────────────────────
def load_data_to_ram():
    """Fungsi ini dipanggil saat startup dan saat di-trigger oleh sync_data.py"""
    if os.path.exists(PARQUET_PATH):
        # Gunakan read_parquet! (Jauh lebih cepat dari CSV)
        df_penjualan = pd.read_parquet(PARQUET_PATH)
        
        # Parse tanggal (Biasanya Parquet sudah otomatis datetime, tapi untuk jaga-jaga)
        df_penjualan["aritemdate"] = pd.to_datetime(df_penjualan["aritemdate"])
        
        # Parse lastupdate jika ada (kolom baru untuk tracking return)
        if "lastupdate" in df_penjualan.columns:
            df_penjualan["lastupdate"] = pd.to_datetime(df_penjualan["lastupdate"])
        
        # Trim whitespace
        for col in ["custname", "kota", "area", "cat1shortdesc", "cat2shortdesc", "itemshortdesc", "satuan", "salesname"]:
            if col in df_penjualan.columns:
                df_penjualan[col] = df_penjualan[col].astype(str).str.strip()
        
        app.config["DF_PENJUALAN"] = df_penjualan
        print(f"[OK] Data Penjualan berhasil di-load ke RAM : {len(df_penjualan):,} rows")
    else:
        # Fallback jika file belum ditarik oleh sync_data.py
        app.config["DF_PENJUALAN"] = pd.DataFrame()
        print("[WARNING] File Parquet belum ada! Silakan jalankan 'python sync_data.py' terlebih dahulu.")

# Eksekusi load pertama kali saat server Flask baru menyala
load_data_to_ram()

# ── Init AI Chatbot (opsional, butuh Ollama) ──────────────────────────────────
try:
    from chatbot_ai import init_ai_chatbot
    init_ai_chatbot()
except Exception as _e:
    print(f"[AI Chatbot] Tidak diinisialisasi: {_e}")

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
        try:
            from chatbot_ai import build_sqlite_from_parquet
            build_sqlite_from_parquet()
            print("[OK] Database AI berhasil disinkronkan.")
        except Exception as e:
            print(f"[ERROR] Gagal sinkronisasi DB AI: {e}")
            
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
    df = app.config.get("DF_PENJUALAN")
    if df is not None and not df.empty:
        # Ambil tanggal terkecil dan terbesar
        min_date = df["aritemdate"].min()
        max_date = df["aritemdate"].max()
        
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
app.register_blueprint(trend_bp,     url_prefix="/api/trend")
app.register_blueprint(items_bp,     url_prefix="/api/items")
app.register_blueprint(customers_bp, url_prefix="/api/customers")
app.register_blueprint(geography)
app.register_blueprint(category)
app.register_blueprint(marketing_bp)
app.register_blueprint(dataquality_bp)
app.register_blueprint(insights_bp)
app.register_blueprint(export_bp,    url_prefix="/api/export")
app.register_blueprint(chatbot_bp)
app.register_blueprint(aireport_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(piutang_bp)
app.register_blueprint(logs_bp)

# ── AI Chatbot Logs Endpoints ─────────────────────────────────────────────────
try:
    from chatbot_ai import get_ai_logs
    
    @app.route('/api/chatbot/logs', methods=['GET'])
    def get_chatbot_logs_endpoint():
        """Endpoint untuk melihat AI reasoning logs - SQL queries, pikiran AI, dll."""
        try:
            limit = request.args.get('limit', 50, type=int)
            logs = get_ai_logs(limit=min(limit, 200))  # Max 200
            return jsonify({
                'success': True,
                'count': len(logs),
                'logs': logs
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/chatbot/logs/latest', methods=['GET'])
    def get_latest_log_endpoint():
        """Endpoint untuk melihat log terakhir (debugging real-time)."""
        try:
            logs = get_ai_logs(limit=1)
            if logs:
                return jsonify({
                    'success': True,
                    'log': logs[0]
                })
            return jsonify({
                'success': False,
                'error': 'No logs found'
            }), 404
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/logs', methods=['GET'])
    def view_logs_page():
        """HTML page untuk view chatbot logs di browser - akses dari mana aja."""
        try:
            limit = request.args.get('limit', 20, type=int)
            logs = get_ai_logs(limit=min(limit, 100))
            
            # Build HTML
            html = f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Chatbot AI Logs</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .controls {{
            margin: 20px 0;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 5px;
        }}
        .controls button {{
            background: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }}
        .controls button:hover {{
            background: #45a049;
        }}
        .log-entry {{
            border: 1px solid #ddd;
            margin: 15px 0;
            padding: 15px;
            border-radius: 5px;
            background: #fafafa;
        }}
        .log-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        .log-timestamp {{
            color: #666;
            font-size: 0.9em;
        }}
        .log-question {{
            font-weight: bold;
            color: #2196F3;
            margin: 8px 0;
        }}
        .log-section {{
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-left: 3px solid #2196F3;
        }}
        .log-section-title {{
            font-weight: bold;
            color: #555;
            margin-bottom: 5px;
        }}
        .sql-query {{
            background: #263238;
            color: #aed581;
            padding: 10px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            overflow-x: auto;
            white-space: pre-wrap;
        }}
        .answer {{
            background: #e8f5e9;
            padding: 10px;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
        }}
        .draft-answer {{
            background: #fff3e0;
            padding: 10px;
            border-radius: 4px;
            border-left: 4px solid #ff9800;
        }}
        .validation {{
            background: #e3f2fd;
            padding: 10px;
            border-radius: 4px;
            border-left: 4px solid #2196F3;
        }}
        .raw-data {{
            background: #f5f5f5;
            padding: 8px;
            border-radius: 3px;
            font-family: monospace;
            font-size: 0.85em;
            max-height: 200px;
            overflow-y: auto;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .badge-data {{
            background: #4CAF50;
            color: white;
        }}
        .badge-chat {{
            background: #2196F3;
            color: white;
        }}
        .badge-interceptor {{
            background: #ff9800;
            color: white;
        }}
        .badge-llm {{
            background: #9c27b0;
            color: white;
        }}
        .no-logs {{
            text-align: center;
            padding: 40px;
            color: #999;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Chatbot AI Reasoning Logs</h1>
        
        <div class="controls">
            <button onclick="location.reload()">🔄 Refresh</button>
            <button onclick="window.location.href='/logs?limit=50'">Show 50</button>
            <button onclick="window.location.href='/logs?limit=100'">Show 100</button>
            <button onclick="window.location.href='/api/chatbot/logs/latest'">JSON Latest</button>
            <span style="margin-left: 20px; color: #666;">Showing {len(logs)} log(s)</span>
        </div>
'''
            
            if not logs:
                html += '<div class="no-logs">📭 No logs yet. Try asking chatbot a question!</div>'
            else:
                for i, log in enumerate(reversed(logs), 1):
                    timestamp = log.get('timestamp', 'N/A')
                    question = log.get('question', 'N/A')
                    intent = log.get('intent', 'N/A')
                    sql_source = log.get('sql_source', 'N/A')
                    sql_query = log.get('sql_query', 'N/A')
                    raw_result = log.get('raw_sql_result', 'N/A')
                    draft = log.get('draft_answer', 'N/A')
                    validation = log.get('validation_notes', 'N/A')
                    final = log.get('final_answer', 'N/A')
                    
                    intent_badge = f'<span class="badge badge-data">DATA</span>' if intent == 'DATA' else f'<span class="badge badge-chat">CHAT</span>'
                    sql_badge = f'<span class="badge badge-interceptor">INTERCEPTOR</span>' if sql_source == 'INTERCEPTOR' else f'<span class="badge badge-llm">LLM</span>'
                    
                    html += f'''
        <div class="log-entry">
            <div class="log-header">
                <div>
                    <span style="font-weight: bold; color: #333;">#{i}</span>
                    <span class="log-timestamp">{timestamp}</span>
                </div>
                <div>
                    {intent_badge}
                    {sql_badge}
                </div>
            </div>
            
            <div class="log-question">❓ {question}</div>
            
            <div class="log-section">
                <div class="log-section-title">🔍 SQL Query:</div>
                <div class="sql-query">{sql_query}</div>
            </div>
            
            <div class="log-section">
                <div class="log-section-title">📊 Raw SQL Result:</div>
                <div class="raw-data">{raw_result}</div>
            </div>
            
            <div class="log-section">
                <div class="log-section-title">✏️ Draft Answer (LLM):</div>
                <div class="draft-answer">{draft}</div>
            </div>
            
            <div class="log-section">
                <div class="log-section-title">🔎 Validation Notes:</div>
                <div class="validation">{validation}</div>
            </div>
            
            <div class="log-section">
                <div class="log-section-title">✅ Final Answer:</div>
                <div class="answer">{final}</div>
            </div>
        </div>
'''
            
            html += '''
    </div>
</body>
</html>
'''
            return html
            
        except Exception as e:
            return f'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Error</title>
</head>
<body>
    <h1>Error Loading Logs</h1>
    <p>{str(e)}</p>
    <a href="/logs">Try Again</a>
</body>
</html>
''', 500

except ImportError:
    # Jika chatbot_ai tidak tersedia, skip endpoints
    pass

# ── Serve Frontend ────────────────────────────────────────────────────
@app.route("/")
def serve_frontend():
    return send_from_directory("../frontend", "index.html")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)