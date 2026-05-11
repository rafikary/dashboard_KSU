from flask import Blueprint, jsonify, request, current_app
import numpy as np
import pandas as pd

trend_bp = Blueprint("trend", __name__)


@trend_bp.route("/decline")
def detect_decline():
    df = current_app.config["DF_PENJUALAN"].copy()
    df["month"] = df["aritemdate"].dt.to_period("M").astype(str)

    monthly = (
        df.groupby(["custname", "month"])
        .agg(total=("aritemdtlamt", "sum"), orders=("aritemdate", "count"))
        .reset_index()
        .sort_values(["custname", "month"])
    )

    result = []
    for custname, group in monthly.groupby("custname"):
        if len(group) < 3:
            continue
        totals     = group["total"].tolist()
        months_lst = group["month"].tolist()
        orders_lst = group["orders"].tolist()

        declines   = sum(1 for i in range(len(totals) - 1) if totals[i] > totals[i + 1])
        pct_change = round(((totals[-1] - totals[-2]) / totals[-2]) * 100, 1) if totals[-2] else 0
        status     = "declining" if declines >= 3 else "warning" if declines >= 2 else "stable"

        trend_data = [
            {"month": m, "total": round(t, 0), "orders": o}
            for m, t, o in zip(months_lst, totals, orders_lst)
        ]

        result.append({
            "customer_name":    custname,
            "trend_data":       trend_data,
            "pct_change":       pct_change,
            "status":           status,
            "total_months":     len(totals),
            "declining_months": declines,
        })

    result.sort(key=lambda x: x["pct_change"])
    return jsonify(result)


@trend_bp.route("/monthly-revenue")
def monthly_revenue():
    df   = current_app.config["DF_PENJUALAN"].copy()
    area = request.args.get("area")

    if area:
        df = df[df["area"].str.upper() == area.upper()]

    period_start = df["aritemdate"].min() if not df.empty else None
    period_end = df["aritemdate"].max() if not df.empty else None

    monthly = (
        df.groupby(df["aritemdate"].dt.to_period("M"))
        .agg(total_revenue=("aritemdtlamt", "sum"), total_orders=("aritemdate", "count"))
        .reset_index()
    )
    monthly["month"]         = monthly["aritemdate"].astype(str)
    monthly["total_revenue"] = monthly["total_revenue"].round(0)
    
    # Filter out months with zero revenue (cleaner dashboard view)
    monthly = monthly[monthly["total_revenue"] > 0]

    return jsonify({
        "monthly": monthly[["month", "total_revenue", "total_orders"]].to_dict(orient="records"),
        "period_start": period_start.strftime("%d %b %Y") if period_start is not None else "",
        "period_end": period_end.strftime("%d %b %Y") if period_end is not None else "",
    })

@trend_bp.route("/activity-per-customer")
def activity_per_customer():
    df    = current_app.config["DF_PENJUALAN"].copy()
    limit = int(request.args.get("limit", 10))
    from_date = request.args.get("from")
    to_date   = request.args.get("to")

    if from_date:
        df = df[df["aritemdate"] >= pd.to_datetime(from_date)]
    if to_date:
        df = df[df["aritemdate"] <= pd.to_datetime(to_date)]

    # Top N by total revenue dalam range
    cust_totals = (
        df.groupby("custname")["aritemdtlamt"]
        .sum()
        .nlargest(limit)
        .reset_index()
    )
    top_custs_ordered = cust_totals["custname"].tolist()  # urutan rank 1..N

    df_top          = df[df["custname"].isin(top_custs_ordered)].copy()
    df_top["month"] = df_top["aritemdate"].dt.to_period("M").astype(str)

    activity = (
        df_top.groupby(["custname", "month"])
        .agg(
            order_count=("aritemdate", "count"),
            total_revenue=("aritemdtlamt", "sum"),
        )
        .reset_index()
        .rename(columns={"custname": "customer_name"})
    )
    activity["total_revenue"] = activity["total_revenue"].round(0)

    # Sort: urutan customer = rank revenue, lalu per bulan
    rank_map = {name: i for i, name in enumerate(top_custs_ordered)}
    activity["_rank"] = activity["customer_name"].map(rank_map)
    activity = activity.sort_values(["_rank", "month"]).drop(columns=["_rank"])

    return jsonify({"activity": activity.to_dict(orient="records")})
    

@trend_bp.route("/top-products")
def top_products():
    """Get top 10 products by revenue"""
    df = current_app.config["DF_PENJUALAN"].copy()
    limit = int(request.args.get("limit", 10))
    
    top_products = (
        df.groupby("itemshortdesc")
        .agg(
            total_revenue=("aritemdtlamt", "sum"),
            total_qty=("aritemqty", "sum"),
            total_orders=("aritemdate", "count")
        )
        .reset_index()
        .sort_values("total_revenue", ascending=False)
        .head(limit)
    )
    
    top_products["total_revenue"] = top_products["total_revenue"].round(0)
    top_products["total_qty"] = top_products["total_qty"].round(0)
    
    return jsonify({
        "products": top_products.to_dict(orient="records")
    })


@trend_bp.route("/sales-performance")
def sales_performance():
    """Get sales performance with period filter - FIXED: Filter AFTER aggregation"""
    from datetime import datetime, timedelta
    
    df = current_app.config["DF_PENJUALAN"].copy()
    period = request.args.get("period", "all_time")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    
    # Monthly sales aggregation FIRST (before filtering)
    # This ensures each month has COMPLETE data
    monthly = (
        df.groupby(df["aritemdate"].dt.to_period("M"))
        .agg(
            total_sales=("aritemdtlamt", "sum"),
            total_orders=("aritemdate", "count"),
            unique_customers=("custname", "nunique")
        )
        .reset_index()
    )
    monthly["month"] = monthly["aritemdate"].astype(str)
    monthly["total_sales"] = monthly["total_sales"].round(0)
    
    # Filter out months with zero revenue (better UX for dashboard)
    monthly = monthly[monthly["total_sales"] > 0]
    
    # Store period range for metadata
    period_start = monthly["month"].min()
    period_end = monthly["month"].max()
    
    # Apply date filter (priority over period)
    if date_from or date_to:
        start_period = pd.Period(date_from, freq="M") if date_from else monthly["aritemdate"].min()
        end_period = pd.Period(date_to, freq="M") if date_to else monthly["aritemdate"].max()
        monthly = monthly[(monthly["aritemdate"] >= start_period) & (monthly["aritemdate"] <= end_period)]
        period_start = monthly["month"].min()
        period_end = monthly["month"].max()
    # Apply period filter AFTER aggregation (filter complete months only)
    elif period != "all_time":
        current_period = pd.Timestamp(datetime.now()).to_period("M")
        last_complete = current_period - 1
        data_max = monthly["aritemdate"].max()
        max_period = data_max if data_max < last_complete else last_complete
        if period == "3_months":
            start_period = max_period - 2  # Last 3 complete months
        elif period == "6_months":
            start_period = max_period - 5  # Last 6 complete months
        elif period == "12_months":
            start_period = max_period - 11  # Last 12 complete months
        else:
            start_period = monthly["aritemdate"].min()
        monthly = monthly[(monthly["aritemdate"] >= start_period) & (monthly["aritemdate"] <= max_period)]
        period_start = monthly["month"].min()
        period_end = monthly["month"].max()
    
    # Calculate growth rate
    if len(monthly) > 1:
        monthly["growth_rate"] = monthly["total_sales"].pct_change() * 100
        monthly["growth_rate"] = monthly["growth_rate"].fillna(0).replace([np.inf, -np.inf], 0).round(2)
    else:
        monthly["growth_rate"] = 0
    
    result = monthly[["month", "total_sales", "total_orders", "unique_customers", "growth_rate"]].to_dict(orient="records")
    
    if date_from or date_to:
        df_range = df.copy()
        if date_from:
            df_range = df_range[df_range["aritemdate"] >= pd.to_datetime(date_from)]
        if date_to:
            df_range = df_range[df_range["aritemdate"] <= pd.to_datetime(date_to)]
        period_start_formatted = datetime.strptime(date_from, "%Y-%m-%d").strftime("%d %b %Y") if date_from else (
            df_range["aritemdate"].min().strftime("%d %b %Y") if not df_range.empty else ""
        )
        period_end_formatted = datetime.strptime(date_to, "%Y-%m-%d").strftime("%d %b %Y") if date_to else (
            df_range["aritemdate"].max().strftime("%d %b %Y") if not df_range.empty else ""
        )
    elif period != "all_time" and not monthly.empty:
        period_start_formatted = pd.Period(period_start, freq="M").to_timestamp().strftime("%d %b %Y")
        period_end_formatted = pd.Period(period_end, freq="M").to_timestamp(how="end").strftime("%d %b %Y")
    else:
        period_start_formatted = df["aritemdate"].min().strftime("%d %b %Y") if not df.empty else ""
        period_end_formatted = df["aritemdate"].max().strftime("%d %b %Y") if not df.empty else ""
    
    return jsonify({
        "performance": result,
        "period_start": period_start_formatted,
        "period_end": period_end_formatted,
        "summary": {
            "total_revenue": float(monthly["total_sales"].sum()),
            "avg_monthly": float(monthly["total_sales"].mean()),
            "avg_growth": float(monthly["growth_rate"].mean()) if len(monthly) > 1 else 0
        }
    })


# ── BARU: QoQ (Diperbaiki - Mengatasi Kuartal Bolong) ───────────────────
@trend_bp.route("/decline/qoq")
def decline_qoq():
    df = current_app.config["DF_PENJUALAN"].copy()
    df["quarter"] = df["aritemdate"].dt.to_period("Q").astype(str)

    # 1. Buat Matrix Pivot (Customer sebagai Baris, Kuartal sebagai Kolom)
    # Ini memastikan semua kuartal muncul. Jika ada yang bolong, diisi 0 (fill_value=0)
    qoq_matrix = (
        df.groupby(["custname", "quarter"])["aritemdtlamt"]
        .sum()
        .unstack(fill_value=0)
    )

    # Ambil list semua nama kuartal yang berurutan dari nama kolom
    all_quarters = qoq_matrix.columns.tolist()

    result = []
    # 2. Looping per baris customer dari matriks yang sudah rapi
    for cust, row in qoq_matrix.iterrows():
        totals = row.tolist()
        
        # Abaikan customer jika total mereka aktif belanja (belanja > 0) kurang dari 2 kuartal 
        # (Sepanjang sejarah mereka)
        if sum(1 for t in totals if t > 0) < 2:
            continue

        last  = totals[-1] # Kuartal terakhir di dataset
        prev  = totals[-2] # Satu kuartal sebelumnya
        
        # Hitung Persentase.
        if prev > 0:
            pct = round(((last - prev) / prev) * 100, 1)
        else:
            pct = 100.0 if last > 0 else 0.0

        declines = sum(1 for i in range(len(totals)-1) if totals[i] > totals[i+1])
        
        if declines >= 3:
            status = "declining"
        elif declines >= 2:
            status = "warning"
        else:
            status = "stable"

        result.append({
            "customer_name":      cust,
            "last_quarter":       all_quarters[-1],
            "prev_quarter":       all_quarters[-2],
            "last_total":         round(last),
            "prev_total":         round(prev),
            "pct_change_qoq":     pct,
            "status":             status,
            "total_quarters":     len(totals), # Ini adalah total seluruh kuartal di data (misal 4)
            "declining_quarters": declines,
            "trend_data":         [{"quarter": q, "total": round(t)} for q, t in zip(all_quarters, totals)]
        })

    result.sort(key=lambda x: x["pct_change_qoq"])
    return jsonify(result)

# ── BARU: Purchase Cycle ───────────────────────────────
@trend_bp.route("/decline/cycle")
def decline_cycle():
    df = current_app.config["DF_PENJUALAN"].copy()

    order_dates = (
        df.groupby(["custname", "aritemdate"])
        .size()
        .reset_index()[["custname", "aritemdate"]]
        .drop_duplicates()
        .sort_values(["custname", "aritemdate"])
    )

    now = df["aritemdate"].max()

    result = []
    for cust, grp in order_dates.groupby("custname"):
        dates = sorted(grp["aritemdate"].tolist())
        if len(dates) < 3:
            continue

        gaps      = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
        avg_cycle = round(float(np.mean(gaps)), 1)
        std_cycle = round(float(np.std(gaps)), 1)

        # ← FIX 2: minimal std 14 hari biar ga false alarm
        adjusted_std = max(std_cycle, 14.0)
        threshold    = avg_cycle + adjusted_std

        last_order        = dates[-1]
        current_idle_days = (now - last_order).days

        if current_idle_days > threshold * 2:
            status = "kritis"
        elif current_idle_days > threshold:
            status = "waspada"
        else:
            status = "normal"

        result.append({
            "customer_name":     cust,
            "avg_cycle_days":    avg_cycle,
            "std_days":          std_cycle,
            "last_order":        str(last_order.date()),
            "current_idle_days": current_idle_days,
            "threshold_days":    round(threshold, 1),
            "status":            status,
            "total_orders":      len(dates)
        })

    result.sort(key=lambda x: x["current_idle_days"], reverse=True)
    return jsonify(result)

# ── BARU: Diagnostic Analytics (Matriks Riwayat per Item) ──
@trend_bp.route("/decline-detail")
def decline_detail():
    df = current_app.config["DF_PENJUALAN"].copy()
    cust = request.args.get("customer")
    q_from = request.args.get("from")
    q_to = request.args.get("to")

    df_cust = df[df["custname"] == cust].copy()
    df_cust["quarter"] = df_cust["aritemdate"].dt.to_period("Q").astype(str)
    
    # Ambil tanggal transaksi terakhir
    last_dates = df_cust.groupby("itemshortdesc")["aritemdate"].max().dt.strftime("%Y-%m-%d").to_dict()

    # Buat daftar semua kuartal unik di rentang yang dipilih (agar kolom rapi)
    all_q = sorted(df["aritemdate"].dt.to_period("Q").astype(str).unique())
    try:
        start_idx = all_q.index(q_from)
        end_idx = all_q.index(q_to)
        # Ambil semua list kuartal di antara from dan to
        all_q_in_range = all_q[start_idx:end_idx+1]
    except:
        all_q_in_range = [q_from, q_to] # Fallback jika error
        
    df_q = df_cust[df_cust["quarter"].isin(all_q_in_range)]

    if df_q.empty:
        return jsonify({"quarters": all_q_in_range, "items": []})

    # PIVOT MATRIX: Kolom = Kuartal, Baris = Item
    pivot_qty = df_q.pivot_table(index="itemshortdesc", columns="quarter", values="aritemqty", aggfunc="sum").fillna(0)
    pivot_amt = df_q.pivot_table(index="itemshortdesc", columns="quarter", values="aritemdtlamt", aggfunc="sum").fillna(0)

    # Pastikan semua kuartal muncul di kolom tabel meskipun 0
    for q in all_q_in_range:
        if q not in pivot_qty.columns: pivot_qty[q] = 0
        if q not in pivot_amt.columns: pivot_amt[q] = 0

    details = []
    for item in pivot_qty.index:
        # Dictionary kuantitas untuk dirender Vue { "2024Q1": 10, "2024Q2": 0, "2024Q3": 5 }
        history_qty = {q: float(pivot_qty.at[item, q]) for q in all_q_in_range}
        history_amt = {q: float(pivot_amt.at[item, q]) for q in all_q_in_range}
        
        qty_last = history_qty[all_q_in_range[-1]]
        amt_last = history_amt[all_q_in_range[-1]]
        
        # Pisahkan histori masa lalu dan kuartal tujuan akhir
        past_qty = [history_qty[q] for q in all_q_in_range[:-1]]
        past_amt = [history_amt[q] for q in all_q_in_range[:-1]]
        
        max_past_qty = max(past_qty) if past_qty else 0
        max_past_amt = max(past_amt) if past_amt else 0
        sum_past_qty = sum(past_qty) if past_qty else 0
        
        # LOGIKA CERDAS BOS:
        if sum_past_qty > 0 and qty_last == 0:
            status = "Lost Item"
            diff_amt = 0 - max_past_amt # Hitung kerugian dari puncak belanjanya
        elif sum_past_qty > 0 and qty_last < max_past_qty:
            status = "Turun"
            diff_amt = amt_last - max_past_amt
        elif sum_past_qty == 0 and qty_last > 0:
            status = "Item Baru"
            diff_amt = amt_last
        else:
            status = "Stabil/Naik"
            diff_amt = amt_last - (sum(past_amt)/len(past_amt) if past_amt else 0)

        details.append({
            "item_name": item,
            "history_qty": history_qty,
            "qty_last": round(qty_last),
            "diff_amt": round(diff_amt),
            "status": status,
            "last_order": last_dates.get(item, "-")
        })

    return jsonify({
        "quarters": all_q_in_range,
        "items": details
    })


@trend_bp.route("/item-buyers")
def item_buyers():
    """Untuk menjawab: Barang ini biasanya dibeli oleh siapa saja?"""
    df = current_app.config["DF_PENJUALAN"].copy()
    item_name = request.args.get("item")
    
    # PERBAIKAN: Gunakan itemshortdesc
    df_item = df[df["itemshortdesc"] == item_name]
    
    buyers = (
        df_item.groupby("custname")
        .agg(total_qty=("aritemqty", "sum"), last_order=("aritemdate", "max"))
        .reset_index()
        .sort_values("total_qty", ascending=False)
        .head(10)
    )
    buyers["last_order"] = buyers["last_order"].dt.strftime("%Y-%m-%d")
    
    return jsonify(buyers.rename(columns={"custname": "customer_name"}).to_dict(orient="records"))