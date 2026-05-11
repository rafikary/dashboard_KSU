from flask import Blueprint, request, jsonify
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import urllib
import os

load_dotenv()

auth_bp = Blueprint('auth', __name__)


def _get_engine():
    driver   = os.getenv("DB_DRIVER")
    server   = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    username = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    # print(f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={username};PWD={password}")
    params = urllib.parse.quote_plus(
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
    )
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")
    return engine



@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "Data tidak valid"}), 400

    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"success": False, "message": "Username dan password wajib diisi"}), 400

    try:
        engine = _get_engine()
        with engine.connect() as conn:
            row = conn.execute(
                text("SELECT uspassword, usflag FROM ql_m01us WHERE usoid = :u"),
                {"u": username}
            ).fetchone()
    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": "Tidak dapat terhubung ke database"}), 503

    if row is None:
        return jsonify({"success": False, "message": "Username atau password salah"}), 401

    password_hash, is_active = row

    if is_active == 'INACTIVE':
        return jsonify({"success": False, "message": "Akun tidak aktif"}), 403

    if password_hash != password:
        return jsonify({"success": False, "message": "Username atau password salah"}), 401

    return jsonify({
        "success": True,
        "message": "Login berhasil",
        "username": username
    })


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    return jsonify({"success": True, "message": "Logout berhasil"})

