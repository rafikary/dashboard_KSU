from flask import Blueprint, jsonify, request, current_app
from datetime import timedelta
import pandas as pd

items_bp = Blueprint("items", __name__)


@items_bp.route("/missing/<customer_name>")
def missing_items(customer_name):
    """
    Deteksi item yang dibeli rutin tapi tidak dibeli di kuartal sekarang.
    
    LOGIKA BISNIS BARU (Behavioral-Based):
    1. Item harus rutin: minimal 3x dalam 4 kuartal terakhir ATAU ada di Q-1 dan Q-2
    2. Item KOSONG di kuartal sekarang (berdasarkan current date sistem)
    3. Status BEHAVIORAL:
       - WARNING (🟡): Customer BELUM ORDER APAPUN di Q ini → Telat order / sepi
       - URGENT (🔴): Customer SUDAH ORDER barang lain, tapi item ini tidak dibeli → Pindah supplier!
    """
    from datetime import datetime

    df = current_app.config["DF_PENJUALAN"].copy()

    # Tambah kolom quarter
    df["quarter"] = df["aritemdate"].dt.to_period("Q")

    # Cek apakah customer exist
    all_customers = df["custname"].str.upper().unique()
    customer_upper = customer_name.upper()

    if customer_upper not in all_customers:
        return jsonify({
            "customer_name": customer_name,
            "customer_exists": False,
            "missing_items": [],
            "error": f"Customer '{customer_name}' tidak ditemukan dalam database"
        }), 404

    # Filter customer
    df_cust = df[df["custname"].str.upper() == customer_upper].copy()

    if df_cust.empty:
        return jsonify({
            "customer_name": customer_name,
            "customer_exists": True,
            "missing_items": []
        })

    # Gunakan CURRENT DATE SISTEM (bukan transaksi terakhir customer!)
    today = pd.Timestamp.now()
    current_quarter_actual = today.to_period("Q")

    # Identifikasi kuartal-kuartal yang ada di data customer
    all_quarters = sorted(df_cust["quarter"].unique())

    if len(all_quarters) < 2:
        return jsonify({
            "customer_name": customer_name,
            "missing_items": []
        })

    current_quarter = current_quarter_actual

    # Cari previous quarters
    past_quarters = [q for q in all_quarters if q < current_quarter]

    if len(past_quarters) < 2:
        return jsonify({
            "customer_name": customer_name,
            "missing_items": [],
            "current_quarter": str(current_quarter),
            "info": "Data historis tidak cukup untuk analisis"
        })

    # Ambil 4 kuartal terakhir untuk baseline (lebih ketat)
    if len(past_quarters) >= 4:
        baseline_quarters = past_quarters[-4:]  # Q-4, Q-3, Q-2, Q-1
    else:
        baseline_quarters = past_quarters

    prev_quarter_1 = past_quarters[-1]  # Q-1
    prev_quarter_2 = past_quarters[-2] if len(past_quarters) >= 2 else None  # Q-2

    # Hitung hari dalam kuartal sekarang
    quarter_start = current_quarter.to_timestamp()
    days_into_quarter = (today - quarter_start).days

    # CEK BEHAVIORAL: Apakah customer SUDAH ORDER barang lain di Q ini?
    has_any_transaction_in_current_q = current_quarter in all_quarters

    # Group by item dan quarter, sum qty
    item_quarter = (
        df_cust.groupby(["itemshortdesc", "quarter"])["aritemqty"]
        .sum()
        .reset_index()
    )

    # Pivot: item x quarter
    pivot = item_quarter.pivot(index="itemshortdesc", columns="quarter", values="aritemqty").fillna(0)

    missing = []

    for item in pivot.index:
        # Cari semua kuartal dimana item punya transaksi (qty > 0) di baseline period
        item_quarters_with_qty = [q for q in baseline_quarters if q in pivot.columns and pivot.loc[item, q] > 0]

        # DEFINISI RUTIN BARU (balance antara ketat dan praktis):
        # Opsi 1: Minimal 2x dalam 4 kuartal terakhir (item recurring)
        # Opsi 2: Ada di Q-1 (item yang dibeli quarter lalu pasti rutin)
        has_in_q1 = prev_quarter_1 in pivot.columns and pivot.loc[item, prev_quarter_1] > 0

        is_rutin = len(item_quarters_with_qty) >= 2 or has_in_q1

        if not is_rutin:
            # Item tidak cukup rutin, skip
            continue

        # Cek apakah item KOSONG di current quarter
        missing_in_current = current_quarter not in pivot.columns or pivot.loc[item, current_quarter] == 0

        if not missing_in_current:
            # Item masih ada di Q sekarang, skip
            continue

        # Kuartal terakhir item ini dibeli
        last_quarter_with_qty = item_quarters_with_qty[-1] if item_quarters_with_qty else None

        if not last_quarter_with_qty:
            continue

        # Hitung berapa kuartal sudah kosong
        quarters_after_last = []
        check_quarter = last_quarter_with_qty + 1
        while check_quarter <= current_quarter:
            quarters_after_last.append(check_quarter)
            check_quarter += 1

        quarters_empty_count = len(quarters_after_last)

        # ===== LOGIKA 3-TIER SEVERITY (Behavioral + Time-Based) =====
        # 🔴 URGENT (MERAH): 
        #    - Customer SUDAH order barang lain, tapi item ini tidak masuk (behavioral threat!)
        #    - ATAU item SUDAH KOSONG 3+ quarters (time-based severity extreme)
        # 🟠 CAUTION (ORANYE):
        #    - Customer BELUM order apapun DAN item KOSONG 2 quarters (concern, tapi bukan immediate)
        # 🟡 WARNING (KUNING):
        #    - Customer BELUM order apapun DAN item BARU KOSONG 1 quarter (grace period)

        if has_any_transaction_in_current_q:
            # Customer SUDAH BELI barang lain, tapi item ini tidak ada → URGENT!
            status = "urgent"
            reason = "Customer sudah order item lain, tapi tidak order item ini (kemungkinan pindah supplier)"
        elif quarters_empty_count >= 3:
            # Item sudah kosong 3+ quarters → URGENT! (terlalu lama hilang)
            status = "urgent"
            reason = f"Item sudah kosong {quarters_empty_count} kuartal berturut-turut (terlalu lama)"
        elif quarters_empty_count == 2:
            # Item kosong 2 quarters + customer belum order apapun → CAUTION
            status = "caution"
            reason = "Item sudah kosong 2 kuartal, perlu follow-up lebih serius"
        else:
            # Item baru kosong 1 quarter + customer belum order apapun → WARNING
            status = "warning"
            reason = "Customer belum ada transaksi apapun, item baru kosong 1 kuartal"

        # Hitung avg qty saat item masih aktif
        avg_qty = round(sum([pivot.loc[item, q] for q in item_quarters_with_qty]) / len(item_quarters_with_qty), 0) if item_quarters_with_qty else 0

        missing.append({
            "item_name": item,
            "avg_qty_previous": int(avg_qty),
            "last_quarter": str(last_quarter_with_qty),
            "current_quarter": str(current_quarter),
            "status": status,
            "quarters_empty": quarters_empty_count,
            "reason": reason
        })

    # Sort by status priority (urgent > caution > warning) then avg_qty descending
    status_priority = {"urgent": 0, "caution": 1, "warning": 2}
    missing.sort(key=lambda x: (status_priority.get(x["status"], 99), -x["avg_qty_previous"]))

    return jsonify({
        "customer_name": customer_name,
        "missing_items": missing,
        "current_quarter": str(current_quarter),
        "days_into_quarter": int(days_into_quarter),
        "has_transaction_in_current_q": has_any_transaction_in_current_q,
        "info": f"Hari ke-{days_into_quarter} dari ~90 hari di {current_quarter}"
    })


@items_bp.route("/top-by-customer/<customer_name>")
def top_by_customer(customer_name):
    df = current_app.config["DF_PENJUALAN"].copy()
    limit = int(request.args.get("limit", 10))
    sort_by = request.args.get("sort_by", "qty")  # Default qty

    df_cust = df[df["custname"].str.upper() == customer_name.upper()]

    # Tentukan kolom mana yang dipakai untuk sorting
    sort_col = "total_spend" if sort_by == "amount" else "total_qty"

    top = (
        df_cust.groupby("itemshortdesc")
        .agg(total_qty=("aritemqty", "sum"), total_spend=("aritemdtlamt", "sum"))
        .reset_index()
        .sort_values(sort_col, ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    top["rank"] = top.index + 1
    top["total_qty"] = top["total_qty"].round(0)
    top["total_spend"] = top["total_spend"].round(0)

    return jsonify({
        "customer_name": customer_name,
        "items": top.rename(columns={"itemshortdesc": "item_name"}).to_dict(orient="records")
    })


@items_bp.route("/top-overall")
def top_overall():
    df        = current_app.config["DF_PENJUALAN"].copy()
    limit     = int(request.args.get("limit", 10))
    date_from = request.args.get("from")   # format YYYY-MM-DD
    date_to   = request.args.get("to")
    sort_by   = request.args.get("sort_by", "qty")

    # ✅ Filter pakai date langsung — support YYYY-MM-DD dari date picker
    if date_from:
        df = df[df["aritemdate"] >= pd.to_datetime(date_from)]
    if date_to:
        # +1 hari agar tanggal akhir inclusive (konsisten dengan rule 17 chatbot)
        df = df[df["aritemdate"] < pd.to_datetime(date_to) + timedelta(days=1)]

    sort_col = "total_spend" if sort_by == "amount" else "total_qty"

    top = (
        df.groupby("itemshortdesc")
        .agg(
            freq       =("aritemdtlamt", "count"),   # ✅ tambah freq agar konsisten sama SQL chatbot
            total_qty  =("aritemqty",    "sum"),
            total_spend=("aritemdtlamt", "sum")
        )
        .reset_index()
        .sort_values(sort_col, ascending=False)
        .head(limit)
        .reset_index(drop=True)
    )
    top["rank"]        = top.index + 1
    top["total_qty"]   = top["total_qty"].round(0)
    top["total_spend"] = top["total_spend"].round(0)

    return jsonify({"items": top.rename(columns={"itemshortdesc": "item_name"}).to_dict(orient="records")})


@items_bp.route("/trending")
def trending_items():
    df = current_app.config["DF_PENJUALAN"].copy()
    limit   = int(request.args.get("limit", 10))
    sort_by = request.args.get("sort_by", "qty")

    from_month = request.args.get("from")  # "YYYY-MM"
    to_month   = request.args.get("to")    # "YYYY-MM"

    df["month"] = df["aritemdate"].dt.to_period("M")
    all_months  = sorted(df["month"].unique())

    # Tentukan rentang bulan
    if from_month and to_month:
        try:
            from_period  = pd.Period(from_month, freq="M")
            to_period    = pd.Period(to_month,   freq="M")
            range_months = [m for m in all_months if from_period <= m <= to_period]
        except Exception:
            range_months = all_months[-3:]
    else:
        # Default: 3 bulan terakhir
        max_date = df["aritemdate"].max()
        if max_date.day < 25 and len(all_months) >= 4:
            range_months = all_months[-4:-1]
        else:
            range_months = all_months[-3:]

    if not range_months:
        return jsonify({"trending": [], "months": []})

    months_str = [str(m) for m in range_months]
    df_range   = df[df["month"].isin(range_months)]

    metric_col = "aritemdtlamt" if sort_by == "amount" else "aritemqty"

    monthly_data = (
        df_range.groupby(["itemshortdesc", "month"])[metric_col]
        .sum()
        .unstack(fill_value=0)
    )
    monthly_data.columns = [str(c) for c in monthly_data.columns]

    # Pastikan semua kolom bulan ada (isi 0 kalau tidak ada di data)
    for m in months_str:
        if m not in monthly_data.columns:
            monthly_data[m] = 0
    monthly_data = monthly_data[months_str]  # urutan kolom sesuai months_str

    trends = []
    for item, row in monthly_data.iterrows():
        vals = [row[m] for m in months_str]

        # Minimal ada 2 bulan dengan transaksi
        if sum(1 for v in vals if v > 0) < 2:
            continue

        # Growth: bulan terakhir vs bulan pertama yang ada datanya (bukan selalu vals[0])
        first_nonzero = next((v for v in vals if v > 0), 0)
        growth = ((vals[-1] - first_nonzero) / first_nonzero * 100) if first_nonzero > 0 else 0

        if growth > 0:
            trends.append({
                "item_name":    item,
                "monthly_data": {m: round(v, 0) for m, v in zip(months_str, vals)},
                "growth_pct":   round(growth, 1)
            })

    trends.sort(key=lambda x: -x["growth_pct"])
    return jsonify({
        "trending": trends[:limit],
        "months":   months_str  # ← frontend pakai ini, bukan bikin sendiri
    })
@items_bp.route("/top5-category")
def top5_category():
    """Distribusi revenue per kategori — untuk pie chart dashboard"""
    df    = current_app.config["DF_PENJUALAN"].copy()
    month = request.args.get("month")

    if month:
        df = df[df["aritemdate"].dt.to_period("M").astype(str) == month]

    cat = (
        df.groupby("cat1shortdesc")["aritemdtlamt"]
        .sum()
        .reset_index()
        .sort_values("aritemdtlamt", ascending=False)
        .head(5)
    )
    cat["aritemdtlamt"] = cat["aritemdtlamt"].round(0)

    return jsonify({
        "categories": cat.rename(
            columns={"cat1shortdesc": "category", "aritemdtlamt": "total_revenue"}
        ).to_dict(orient="records")
    })


@items_bp.route("/search")
def search_items():
    """
    Search produk berdasarkan keyword - TANPA LIMIT untuk pencarian lengkap
    Query params:
    - q: keyword pencarian (required)
    - from: tanggal mulai (optional, format YYYY-MM-DD)
    - to: tanggal akhir (optional, format YYYY-MM-DD)
    - sort_by: 'amount' atau 'qty' (default: 'amount')
    """
    df = current_app.config["DF_PENJUALAN"].copy()
    keyword = request.args.get("q", "").strip()
    date_from = request.args.get("from")
    date_to = request.args.get("to")
    sort_by = request.args.get("sort_by", "amount")
    
    if not keyword:
        return jsonify({"items": [], "error": "Keyword pencarian tidak boleh kosong"}), 400
    
    # Filter tanggal jika ada
    if date_from:
        df = df[df["aritemdate"] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df["aritemdate"] < pd.to_datetime(date_to) + timedelta(days=1)]
    
    # Filter produk berdasarkan keyword (case-insensitive)
    df_filtered = df[df["itemshortdesc"].str.contains(keyword, case=False, na=False)]
    
    if df_filtered.empty:
        return jsonify({"items": [], "total": 0, "keyword": keyword})
    
    sort_col = "total_spend" if sort_by == "amount" else "total_qty"
    
    # Aggregate semua produk yang cocok (TANPA LIMIT)
    results = (
        df_filtered.groupby("itemshortdesc")
        .agg(
            freq=("aritemdtlamt", "count"),
            total_qty=("aritemqty", "sum"),
            total_spend=("aritemdtlamt", "sum")
        )
        .reset_index()
        .sort_values(sort_col, ascending=False)
        .reset_index(drop=True)
    )
    
    results["rank"] = results.index + 1
    results["total_qty"] = results["total_qty"].round(0)
    results["total_spend"] = results["total_spend"].round(0)
    
    return jsonify({
        "items": results.rename(columns={"itemshortdesc": "item_name"}).to_dict(orient="records"),
        "total": len(results),
        "keyword": keyword
    })