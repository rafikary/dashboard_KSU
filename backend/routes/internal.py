from flask import Blueprint, current_app, jsonify
import json
import os
import subprocess
import sys
import threading

internal_bp = Blueprint("internal", __name__)


def write_reset_status(state, message):
    reset_status_file = current_app.config["RESET_STATUS_FILE"]
    os.makedirs(os.path.dirname(reset_status_file), exist_ok=True)
    with open(reset_status_file, "w") as f:
        json.dump({"state": state, "message": message}, f)


def read_reset_status():
    reset_status_file = current_app.config["RESET_STATUS_FILE"]
    if os.path.exists(reset_status_file):
        with open(reset_status_file, "r") as f:
            return json.load(f)
    return {"state": "idle", "message": ""}


@internal_bp.route("/api/internal/reload-data", methods=["POST"])
def reload_data():
    """Endpoint ini akan ditembak oleh sync_data.py setiap kali sinkronisasi selesai."""
    try:
        load_data_func = current_app.config.get("LOAD_DATA_TO_RAM")
        if not callable(load_data_func):
            raise RuntimeError("LOAD_DATA_TO_RAM belum dikonfigurasi")

        load_data_func()
        return jsonify(
            {
                "status": "success",
                "message": "RAM berhasil di-refresh dengan data Parquet terbaru!",
            }
        ), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@internal_bp.route("/api/internal/full-reset-sync", methods=["POST"])
def full_reset_sync():
    """Hapus semua parquet dan tarik ulang semua data dari awal (dipanggil manual via tombol)."""
    if read_reset_status()["state"] == "running":
        return jsonify({"status": "error", "message": "Reset sedang berjalan, harap tunggu..."}), 400

    app_obj = current_app._get_current_object()
    base_dir = app_obj.config["BASE_DIR"]

    def run():
        with app_obj.app_context():
            write_reset_status("running", "Menghapus data lama dan menarik ulang dari DB...")

        try:
            result = subprocess.run(
                [sys.executable, "sync_data.py", "--full-reset"],
                cwd=base_dir,
                capture_output=True,
                text=True,
            )

            with app_obj.app_context():
                if result.returncode == 0:
                    load_data_func = app_obj.config.get("LOAD_DATA_TO_RAM")
                    if callable(load_data_func):
                        load_data_func()
                    df = app_obj.config.get("DF_KSU")
                    rows = len(df) if df is not None else 0
                    write_reset_status("done", f"Berhasil! Data berhasil dimuat ulang ({rows:,} baris).")
                else:
                    error_message = result.stderr[-300:] if result.stderr else "unknown error"
                    write_reset_status("error", f"Sync gagal: {error_message}")
        except Exception as e:
            with app_obj.app_context():
                write_reset_status("error", f"Gagal: {str(e)}")

    threading.Thread(target=run, daemon=True).start()
    return jsonify({"status": "success", "message": "Reset dimulai..."}), 200


@internal_bp.route("/api/internal/sync-status", methods=["GET"])
def sync_status():
    return jsonify(read_reset_status())