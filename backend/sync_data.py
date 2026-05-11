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

def tarik_data_penjualan():
    """VERSI BARU: Incremental Load dengan Upsert ID & Safety Buffer"""
    print("\n[1] Memulai sinkronisasi data PENJUALAN...")
    parquet_path = 'data/penjualan.parquet'
    os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
    
    # 1. Tentukan Scope Window (Safety Buffer)
    if os.path.exists(parquet_path):
        df_lama = pd.read_parquet(parquet_path)
        # Cari tanggal mutasi terakhir di data lokal
        # Backward compatibility: gunakan 'aritemdate' jika 'lastupdate' belum ada
        if 'lastupdate' in df_lama.columns:
            last_update_max = pd.to_datetime(df_lama['lastupdate']).max()
        else:
            print(f"    -> ⚠️  Struktur lama terdeteksi. Melakukan FULL RESET...")
            df_lama = pd.DataFrame()  # Force full reset karena struktur berbeda
            tanggal_mulai = '2021-01-01'
            print(f"    -> Full Load Mode: Menarik semua data dari awal.")
            
        if not df_lama.empty:
            # GUNAKAN BUFFER 14 HARI (bukan 365 hari). 
            # Cukup untuk menangkap data telat input atau backdating.
            tanggal_mulai = (last_update_max - timedelta(days=14)).strftime('%Y-%m-%d')
            print(f"    -> Incremental Mode: Menarik mutasi sejak {tanggal_mulai}")
    else:
        df_lama = pd.DataFrame()
        tanggal_mulai = '2021-01-01' # Full load pertama kali
        print("    -> Full Load Mode: Menarik semua data.")
    
    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # 2. Query Data dengan ID & Return Handling
            query = f"""
            select d.aritemdtloid, h.area, ct.gndesc kota, c.custname, 
                   h.aritemdate, 
                   ISNULL(arretitemdate, aritemdate) lastupdate,
                   aritemno, c1.cat1shortdesc, c2.cat2shortdesc, m.itemshortdesc, 
                   d.aritemqty - ISNULL(arretitemqty,0) aritemqty, 
                   u.gndesc satuan, d.aritemprice, 
                   (d.aritemqty - ISNULL(arretitemqty,0)) * d.aritemprice aritemdtlamt, 
                   ISNULL(sl.usname,'-') salesname
            from QL_trnaritemmst h 
            inner join ql_mstcust c on c.custoid=h.custoid 
            inner join QL_m05GN ct on ct.gnoid=c.custcityoid 
            inner join ql_trnaritemdtl d on h.aritemmstoid=d.aritemmstoid 
            inner join QL_mstitem m on m.itemoid=d.itemoid 
            left join QL_mstcat1 c1 on c1.cat1oid=m.cat1oid 
            left join QL_mstcat2 c2 on c2.cat2oid=m.cat2oid 
            inner join QL_m05GN u on u.gnoid = d.aritemunitoid 
            inner join QL_trnshipmentitemdtl sj on sj.shipmentitemdtloid = d.shipmentitemdtloid
            inner join QL_trndoitemdtl dod on dod.doitemdtloid = sj.doitemdtloid
            inner join QL_trnsoitemmst som on som.soitemmstoid = dod.soitemmstoid
            outer apply (
                select SUM(arretitemqty) arretitemqty, max(xh.arretitemdate) arretitemdate 
                from QL_trnarretitemdtl xd 
                inner join QL_trnarretitemmst xh on xh.arretitemmstoid=xd.arretitemmstoid 
                where xd.aritemdtloid=d.aritemdtloid 
                and arretitemmststatus in ('Post','Closed')
            ) dr
            left join QL_m01us sl on sl.usoid = c.salesoid
            WHERE h.aritemmststatus in ('Post','Closed','Cancel')
              AND ISNULL(arretitemdate, h.aritemdate) >= '{tanggal_mulai}'
            """
            
            print(f"    -> Executing query... (ini bisa 3-10 menit untuk 5 tahun data)")
            df_baru = pd.read_sql(query, conn)
            
            if df_baru.empty:
                print("    -> Tidak ada data mutasi baru.")
                return # Keluar dari fungsi, tidak perlu simpan ulang parquet

            df_baru.columns = df_baru.columns.str.lower()
            print(f"    -> Query selesai! Total rows ditarik: {len(df_baru):,}")
            
            # [PENTING] Pastikan tipe data ID sama agar .isin() Pandas tidak error
            df_baru['aritemdtloid'] = df_baru['aritemdtloid'].astype(str)
            
        # 3. UPSERT STRATEGY (Update by ID)
        if not df_lama.empty:
            df_lama['aritemdtloid'] = df_lama['aritemdtloid'].astype(str)
            
            # Buang data lama yang ID-nya ikut ketarik di data baru
            df_lama_clean = df_lama[~df_lama['aritemdtloid'].isin(df_baru['aritemdtloid'])]
            
            # Gabungkan data lama yang sudah bersih dengan data mutasi baru
            df_final = pd.concat([df_lama_clean, df_baru], ignore_index=True)
            
            print(f"    -> Memperbarui/Menambah: {len(df_baru):,} rows")
            print(f"    -> Total final: {len(df_final):,} rows")
        else:
            df_final = df_baru
            print(f"    -> Total data diunduh: {len(df_final):,} rows")
        
        # Simpan ke Parquet
        df_final.to_parquet(parquet_path, index=False)
        print("    -> Parquet berhasil disimpan.")
        print(f"    -> Sukses! Total baris Penjualan: {len(df_final):,} baris.")
            
    except Exception as e:
        print(f"    -> Gagal sinkronisasi Penjualan: {e}")

def tarik_data_piutang():
    print("\n[2] Memulai sinkronisasi data PIUTANG & PELUNASAN...")
    parquet_path = 'data/piutang.parquet' # Disimpan di file berbeda
    os.makedirs(os.path.dirname(parquet_path), exist_ok=True)
    
    # 1. CEK DATA LOKAL
    if os.path.exists(parquet_path):
        df_lama = pd.read_parquet(parquet_path)
        # BUFFER 1 TAHUN UNTUK PIUTANG (karena ada customer return hampir 1 tahun)
        tanggal_maksimal = pd.to_datetime(df_lama['aritemdate']).max()
        tanggal_mulai_tarik = (tanggal_maksimal - timedelta(days=365)).strftime('%Y-%m-%d')
        print(f"    -> Menarik data Piutang sejak (buffer 1 tahun): {tanggal_mulai_tarik}")
    else:
        df_lama = pd.DataFrame()
        tanggal_mulai_tarik = '2021-01-01'
        print("    -> FULL LOAD Piutang dari awal...")

    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # Catatan: TOP 10000 saya hapus agar tidak ada data yang terpotong.
            # WHERE t.aritemdate ditambahkan untuk fungsi incremental.
            query = f"""
            select t.area, custname, ISNULL(sl.usname,'-') salesname, t.aritemno, aritemdate, 
            aritemduedate, datediff(day, aritemdate, aritemduedate) dueday, aritemgrandtotal, 
            ISNULL(cashbankno, con.payrefno )payrefno, paymentdate, amtbayar, max(paymentdate) over(partition by aritemno) 
            maxpaymentdate, SUM(amtbayar) over(partition by aritemno) sumbayar, aritemgrandtotal - ISNULL(SUM(amtbayar) 
            over(partition by aritemno),0) arbalance, case when aritemgrandtotal - ISNULL(SUM(amtbayar) over(partition by aritemno),0) > 0 then datediff(day, aritemdate, getdate()) else datediff(day,aritemdate, max(paymentdate) over(partition by aritemno)) end umurpiutang 
            from QL_trnaritemmst t inner join QL_mstcust c on c.custoid=t.custoid left join QL_conar con on con.reftype in ('QL_trnaritemmst','QL_trnarretitemmst') 
            and con.refoid=t.aritemmstoid and con.amtbayar != 0 left join QL_trnpayar par on par.payaroid = con.payrefoid and con.trnartype='PAYAR' 
            left join QL_trnarretitemmst ret on ret.arretitemmstoid = con.payrefoid and con.trnartype='APRETFG' left join QL_trncashbankmst cb on cb.cashbankoid = par.cashbankoid 
            left join QL_m01us sl on sl.usoid = c.salesoid 
            WHERE t.aritemdate >= '{tanggal_mulai_tarik}'
            order by aritemdate desc
            """
            print(f"    -> Executing query... (ini bisa 2-5 menit untuk 5 tahun data)")
            df_baru = pd.read_sql(query, conn)
            df_baru.columns = df_baru.columns.str.lower()
            print(f"    -> Query selesai! Total rows ditarik: {len(df_baru):,}")
            
            if df_baru.empty and df_lama.empty:
                print("    -> Tabel kosong. Skip.")
                return

        # 3. GABUNGKAN DATA (Custom Deduplication Strategy)
        # Strategy: Preserve df_lama duplicates, remove only overlapping rows, clean df_baru
        if not df_lama.empty and not df_baru.empty:
            if set(df_lama.columns) != set(df_baru.columns):
                df_lama = pd.DataFrame()
                df_final = df_baru
            else:
                df_baru = df_baru[df_lama.columns]
                for col in df_lama.columns:
                    try: df_lama[col] = df_lama[col].astype(df_baru[col].dtype)
                    except: pass
                
                # Custom dedup: Remove overlapping rows from df_lama, preserve existing duplicates
                key_cols = ['aritemno']  # Business key (1 invoice = 1 row, window function aggregated)
                df_lama_keys = df_lama[key_cols].apply(tuple, axis=1)
                df_baru_keys = df_baru[key_cols].apply(tuple, axis=1)
                
                # Keep only non-overlapping rows from df_lama (preserves historical duplicates)
                df_lama_clean = df_lama[~df_lama_keys.isin(df_baru_keys)]
                
                # Safety net: Deduplicate df_baru only (in case database returns duplicates)
                df_baru_clean = df_baru.drop_duplicates(subset=key_cols, keep='last')
                
                # Concat: old (minus overlap) + new (clean)
                df_final = pd.concat([df_lama_clean, df_baru_clean], ignore_index=True)
                print(f"    -> df_lama: {len(df_lama):,} rows → {len(df_lama_clean):,} rows (removed {len(df_lama)-len(df_lama_clean):,} overlapping)")
                print(f"    -> df_baru: {len(df_baru):,} rows → {len(df_baru_clean):,} rows (removed {len(df_baru)-len(df_baru_clean):,} duplicates)")
        elif not df_baru.empty:
            # Safety net: Clean df_baru jika df_lama kosong
            df_final = df_baru.drop_duplicates(subset=['aritemno'], keep='last')
        else:
            df_final = df_lama 
            
        print(f"    -> Menyimpan {len(df_final):,} rows ke parquet...")
        df_final.to_parquet(parquet_path, index=False)
        print(f"    -> Sukses! Total baris Piutang: {len(df_final):,} baris.")
            
    except Exception as e:
        print(f"    -> Gagal sinkronisasi Piutang: {e}")

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
        'data/penjualan.parquet': tarik_data_penjualan,
        'data/piutang.parquet': tarik_data_piutang,
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

def generate_precalculated_reports():
    """Menghitung analitik berat dan menyimpannya ke JSON agar API Flask secepat kilat."""
    print("\n[3] Memulai Pre-Calculation (Generate JSON Reports)...")
    
    parquet_path = 'data/penjualan.parquet'
    if not os.path.exists(parquet_path):
        print("    -> Skip Pre-calc: Data parquet belum ada.")
        return

    df = pd.read_parquet(parquet_path)
    now = df["aritemdate"].max()

    # ---------------------------------------------------------
    # REPORT 1: SUMMARY DASHBOARD (api/customers/summary)
    # ---------------------------------------------------------
    print("    -> Menghitung Summary KPI Dashboard...")
    cutoff_inactive = now - timedelta(days=90)
    last_order = df.groupby("custname")["aritemdate"].max()
    
    summary_data = {
        "totalCustomers":  int(df["custname"].nunique()),
        "totalOrders":     int(len(df)),
        "totalRevenue":    float(round(df["aritemdtlamt"].sum(), 0)),
        "decliningCount":  int((last_order < cutoff_inactive).sum()),
    }
    
    with open('data/report_summary.json', 'w') as f:
        json.dump(summary_data, f)


    # ---------------------------------------------------------
    # REPORT 2: PURCHASE CYCLE / CHURN (api/trend/decline/cycle)
    # ---------------------------------------------------------
    print("    -> Menghitung Purchase Cycle (Churn)...")
    order_dates = (
        df.groupby(["custname", "aritemdate"]).size()
        .reset_index()[["custname", "aritemdate"]]
        .drop_duplicates().sort_values(["custname", "aritemdate"])
    )

    cycle_result = []
    for cust, grp in order_dates.groupby("custname"):
        dates = sorted(grp["aritemdate"].tolist())
        if len(dates) < 3:
            continue

        gaps      = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        avg_cycle = round(float(np.mean(gaps)), 1)
        std_cycle = round(float(np.std(gaps)), 1)
        adjusted_std = max(std_cycle, 14.0)
        threshold    = avg_cycle + adjusted_std

        last_order_date   = dates[-1]
        current_idle_days = (now - last_order_date).days

        if current_idle_days > threshold * 2:
            status = "kritis"
        elif current_idle_days > threshold:
            status = "waspada"
        else:
            status = "normal"

        cycle_result.append({
            "customer_name":     cust,
            "avg_cycle_days":    avg_cycle,
            "std_days":          std_cycle,
            "last_order":        str(last_order_date.date()),
            "current_idle_days": int(current_idle_days),
            "threshold_days":    round(threshold, 1),
            "status":            status,
            "total_orders":      len(dates)
        })

    cycle_result.sort(key=lambda x: x["current_idle_days"], reverse=True)
    with open('data/report_decline_cycle.json', 'w') as f:
        json.dump(cycle_result, f)

    print("    -> Pre-Calculation Selesai!")

if __name__ == "__main__":
    import sys
    if '--full-reset' in sys.argv:
        full_reset_sync()
        # generate_precalculated_reports()
    else:
        tarik_data_penjualan()
        tarik_data_piutang()
        # generate_precalculated_reports()
        trigger_flask_reload()