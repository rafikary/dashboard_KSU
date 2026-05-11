import os
import pandas as pd
import requests
from sqlalchemy import create_engine
from dotenv import load_dotenv
from datetime import timedelta
import urllib 
import json       
import numpy as np

load_dotenv()

def get_db_connection():
    """Fungsi helper untuk membuat koneksi database agar tidak ditulis berulang-ulang"""
    driver = os.getenv("DB_DRIVER")
    server = os.getenv("DB_SERVER")
    database = os.getenv("DB_NAME")
    username = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    
    params = urllib.parse.quote_plus(
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};UID={username};PWD={password}"
    )
    return create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

def tarik_data():
    """VERSI DISESUAIKAN: Menarik data Nominatif KSU"""
    print("\n[1] Memulai sinkronisasi data NOMINATIF KSU...")
    # Sesuaikan nama file parquet
    parquet_path = 'data/ksu.parquet' 
    os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
    
    # 1. Tentukan Scope Window
    if os.path.exists(parquet_path):
        df_lama = pd.read_parquet(parquet_path)
        if 'tglnominatif' in df_lama.columns:
            last_date_max = pd.to_datetime(df_lama['tglnominatif']).max()
            # Gunakan buffer 7-14 hari untuk memastikan data nominatif akhir bulan/minggu terupdate
            tanggal_mulai = (last_date_max - timedelta(days=14)).strftime('%Y-%m-%d')
            print(f"    -> Incremental Mode: Menarik data sejak {tanggal_mulai}")
        else:
            print(f"    -> ⚠️ Struktur lama terdeteksi. Melakukan FULL RESET...")
            df_lama = pd.DataFrame()
            tanggal_mulai = '2021-01-01'
    else:
        df_lama = pd.DataFrame()
        tanggal_mulai = '2021-01-01'
        print("    -> Full Load Mode: Menarik semua data.")
    
    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # 2. Query Baru (Disesuaikan dengan parameter tanggal_mulai)
            query = f"""
            SELECT 
                tglNominatif, 
                gencode AS kode, 
                gendesc AS nama, 
                CASE WHEN flag = 1 THEN 'A' ELSE 'B' END AS flag, 
                pinjaman, 
                sisaPinjaman, 
                jasaTtg1, 
                jasaTtg2, 
                jasaTtg3, 
                jasaTtgNP, 
                totalJasaTtg, 
                sisaPinjamanNP, 
                saldoKas, 
                saldoBank 
            FROM QL_NominatifSum s 
            INNER JOIN QL_mstgen g ON g.gencode = s.cmpcode AND g.gengroup = 'BRANCHCODE' 
            WHERE tglNominatif >= '{tanggal_mulai}'
            ORDER BY tglNominatif
            """
            
            print(f"    -> Executing query...")
            df_baru = pd.read_sql(query, conn)
            
            if df_baru.empty:
                print("    -> Tidak ada data baru yang ditemukan.")
                return 

            df_baru.columns = df_baru.columns.str.lower()
            
            # Buat 'unique_id' gabungan karena data nominatif biasanya harian per cabang
            # Ini untuk mencegah duplikasi saat concat
            df_baru['uid'] = df_baru['tglnominatif'].astype(str) + "_" + df_baru['kode'].astype(str)
            
            print(f"    -> Query selesai! Rows ditarik: {len(df_baru):,}")
            
        # 3. UPSERT STRATEGY
        if not df_lama.empty:
            # Pastikan df_lama juga punya 'uid'
            if 'uid' not in df_lama.columns:
                 df_lama['uid'] = df_lama['tglnominatif'].astype(str) + "_" + df_lama['kode'].astype(str)
            
            # Buang data lama yang kuncinya (UID) ada di data baru
            df_lama_clean = df_lama[~df_lama['uid'].isin(df_baru['uid'])]
            df_final = pd.concat([df_lama_clean, df_baru], ignore_index=True)
            
            print(f"    -> Memperbarui: {len(df_baru):,} rows")
        else:
            df_final = df_baru
        
        # Simpan ke Parquet
        df_final.to_parquet(parquet_path, index=False)
        print(f"    -> Sukses! Total baris KSU: {len(df_final):,}")
            
    except Exception as e:
        print(f"    -> Gagal sinkronisasi KSU: {e}")


def trigger_flask_reload():
    """Memanggil Flask API setelah SEMUA proses sync selesai"""
    print("\n[3] Memberitahu backend Flask untuk me-refresh RAM...")
    try:
        response = requests.post("http://localhost:5000/api/internal/reload-data")
        print("    -> Status Refresh RAM Flask:", response.json())
    except Exception as e:
        print("    -> Flask sedang mati, RAM akan di-load otomatis saat Flask dinyalakan nanti.")

def full_reset_sync():
    """Tarik ulang semua data dari awal. Kalau gagal, rollback ke data lama."""
    print("\n[FULL RESET] Menarik ulang semua data dari DB...")
    parquet_files = {
        'data/ksu.parquet': tarik_data,
    }

    # Backup semua file lama dulu sebelum dihapus
    for parquet_file in parquet_files:
        backup = parquet_file + '.bak'
        if os.path.exists(parquet_file):
            os.replace(parquet_file, backup)
            print(f"    -> Backup: {parquet_file} -> {backup}")

    try:
        for parquet_file, tarik_fn in parquet_files.items():
            tarik_fn()
            if not os.path.exists(parquet_file):
                raise Exception(f"Sync gagal: {parquet_file} tidak terbuat setelah sync.")

        # Sukses — hapus backup
        for parquet_file in parquet_files:
            backup = parquet_file + '.bak'
            if os.path.exists(backup):
                os.remove(backup)
        print("\n[FULL RESET] Selesai! Backup dihapus.")

    except Exception as e:
        # Gagal — rollback dari backup
        print(f"\n[FULL RESET] Gagal: {e}. Rollback ke data lama...")
        for parquet_file in parquet_files:
            backup = parquet_file + '.bak'
            if os.path.exists(backup):
                os.replace(backup, parquet_file)
                print(f"    -> Rollback: {backup} -> {parquet_file}")
        raise  # lempar error supaya app.py catat status error


if __name__ == "__main__":
    import sys
    if '--full-reset' in sys.argv:
        full_reset_sync()
    else:
        tarik_data()
        trigger_flask_reload()