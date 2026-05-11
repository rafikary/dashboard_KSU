from flask import Blueprint, jsonify, request, current_app
from datetime import datetime, timedelta
import pandas as pd  
# import json

customers_bp = Blueprint("customers", __name__)


def _format_date_range(start_dt, end_dt):
    if start_dt is None or end_dt is None:
        return "", ""
    if pd.isna(start_dt) or pd.isna(end_dt):
        return "", ""
    return start_dt.strftime("%d %b %Y"), end_dt.strftime("%d %b %Y")


def _month_range_bounds(start_period, end_period):
    start_dt = pd.Period(start_period, freq="M").to_timestamp()
    end_dt = pd.Period(end_period, freq="M").to_timestamp(how="end")
    return start_dt, end_dt


def _format_input_date(date_str):
    if not date_str:
        return ""
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%d %b %Y")


def _last_complete_period(df):
    current_period = pd.Timestamp(datetime.now()).to_period("M")
    last_complete = current_period - 1
    data_max = df["aritemdate"].max().to_period("M") if not df.empty else last_complete
    return data_max if data_max < last_complete else last_complete


@customers_bp.route("/list")
def list_customers():
    """Return list semua customer names dari data"""
    df = current_app.config["DF_PENJUALAN"].copy()
    customers = sorted(df["custname"].unique().tolist())
    return jsonify({"customers": customers})


@customers_bp.route("/inactive")
def inactive():
    df = current_app.config["DF_PENJUALAN"].copy()
    days = int(request.args.get("days", 90))

    # Pakai tanggal max di data sebagai "sekarang"
    now = df["aritemdate"].max()
    cutoff = now - timedelta(days=days)

    # Transaksi terakhir per customer
    last_order = (
        df.groupby("custname")["aritemdate"]
        .max()
        .reset_index()
        .rename(columns={"aritemdate": "last_order_date"})
    )

    # Filter yang sudah tidak beli sejak cutoff
    inactive_df = last_order[last_order["last_order_date"] < cutoff].copy()
    inactive_df["days_inactive"] = (now - inactive_df["last_order_date"]).dt.days
    inactive_df["last_order_date"] = inactive_df["last_order_date"].dt.strftime("%Y-%m-%d")
    inactive_df = inactive_df.sort_values("days_inactive", ascending=False)

    return jsonify(inactive_df.rename(columns={"custname": "customer_name"}).to_dict(orient="records"))


@customers_bp.route("/loyalty")
def loyalty():
    df = current_app.config["DF_PENJUALAN"].copy()
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")

    if date_from:
        df = df[df["aritemdate"] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df["aritemdate"] <= pd.to_datetime(date_to)]

    # Get period parameter (default: all_time)
    period = request.args.get("period", "all_time")  # all_time, 3_months, 6_months, 12_months

    # Filter by period if not all_time (month-based for accuracy)
    if period != "all_time" and not date_from and not date_to:
        df["month_period"] = df["aritemdate"].dt.to_period("M")
        max_period = _last_complete_period(df)

        if period == "3_months":
            start_period = max_period - 2  # Last 3 complete months
        elif period == "6_months":
            start_period = max_period - 5  # Last 6 complete months
        elif period == "12_months":
            start_period = max_period - 11  # Last 12 complete months
        else:
            start_period = max_period - 2  # default to 3 months

        df = df[(df["month_period"] >= start_period) & (df["month_period"] <= max_period)]

    loyalty_df = (
        df.groupby("custname")
        .agg(
            total_orders=("aritemdate", "count"),
            total_spend=("aritemdtlamt", "sum"),
            first_order=("aritemdate", "min"),
            last_order=("aritemdate", "max"),
        )
        .reset_index()
        .sort_values("total_spend", ascending=False)
    )

    loyalty_df["first_order"] = loyalty_df["first_order"].dt.strftime("%Y-%m-%d")
    loyalty_df["last_order"]  = loyalty_df["last_order"].dt.strftime("%Y-%m-%d")
    loyalty_df["total_spend"] = loyalty_df["total_spend"].round(0)

    if date_from or date_to:
        period_start = _format_input_date(date_from) or _format_date_range(
            df["aritemdate"].min() if not df.empty else None,
            df["aritemdate"].min() if not df.empty else None,
        )[0]
        period_end = _format_input_date(date_to) or _format_date_range(
            df["aritemdate"].max() if not df.empty else None,
            df["aritemdate"].max() if not df.empty else None,
        )[1]
    elif period != "all_time" and not df.empty:
        period_start, period_end = _format_date_range(*_month_range_bounds(start_period, max_period))
    else:
        period_start, period_end = _format_date_range(
            df["aritemdate"].min() if not df.empty else None,
            df["aritemdate"].max() if not df.empty else None,
        )

    return jsonify({
        "customers": loyalty_df.rename(columns={"custname": "customer_name"}).to_dict(orient="records"),
        "period_start": period_start,
        "period_end": period_end,
    })


@customers_bp.route("/top-spending")
def top_spending():
    df = current_app.config["DF_PENJUALAN"].copy()
    month = request.args.get("month")  # format: "2019-10"

    if month:
        df = df[df["aritemdate"].dt.to_period("M").astype(str) == month]

    result = (
        df.groupby("custname")["aritemdtlamt"]
        .sum()
        .reset_index()
        .rename(columns={"custname": "customer_name", "aritemdtlamt": "total_spend"})
        .sort_values("total_spend", ascending=False)
    )
    result["total_spend"] = result["total_spend"].round(0)

    return jsonify(result.to_dict(orient="records"))


@customers_bp.route("/declining")
def declining():
    """Deteksi customer dengan tren pembelian menurun ≥3 bulan berturut-turut"""
    df = current_app.config["DF_PENJUALAN"].copy()

    # Revenue per customer per bulan
    df["month"] = df["aritemdate"].dt.to_period("M")
    monthly = (
        df.groupby(["custname", "month"])["aritemdtlamt"]
        .sum()
        .reset_index()
        .sort_values(["custname", "month"])
    )

    declining_customers = []
    for custname, group in monthly.groupby("custname"):
        revenues = group["aritemdtlamt"].tolist()
        months   = group["month"].tolist()

        # Cek ≥3 bulan berturut-turut menurun
        streak = 1
        max_streak = 1
        for i in range(1, len(revenues)):
            if revenues[i] < revenues[i - 1]:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 1

        if max_streak >= 3:
            last_rev  = revenues[-1]
            peak_rev  = max(revenues)
            pct_drop  = round((peak_rev - last_rev) / peak_rev * 100, 1) if peak_rev > 0 else 0
            declining_customers.append({
                "customer_name":   custname,
                "declining_months": max_streak,
                "peak_revenue":    round(peak_rev, 0),
                "last_revenue":    round(last_rev, 0),
                "pct_drop":        pct_drop,
                "last_active":     str(months[-1]),
            })

    declining_customers.sort(key=lambda x: -x["pct_drop"])
    return jsonify(declining_customers)


@customers_bp.route("/summary")
def summary():
    """Summary untuk card di dashboard (PRE-CALCULATED)"""
    # base_dir = os.path.dirname(os.path.dirname(__file__))
    # json_path = os.path.join(base_dir, 'data', 'report_summary.json')
    
    # # Coba baca JSON hasil pre-calc
    # if os.path.exists(json_path):
    #     with open(json_path, 'r') as f:
    #         return jsonify(json.load(f))
            
    # Fallback aman jika JSON tiba-tiba hilang/terhapus
    df_raw = current_app.config["DF_PENJUALAN"].copy()
    
    # 🌟 2. FILTER KONSISTENSI (Sama seperti logika AI)
    # Buang data masa depan & data kosong sebelum dihitung
    sekarang = pd.Timestamp(datetime.now())
    df = df_raw[df_raw["aritemdate"] <= sekarang].copy()
    
    now = df["aritemdate"].max()
    cutoff_inactive = now - timedelta(days=90)

    total_customers = df["custname"].nunique()
    total_revenue   = round(df["aritemdtlamt"].sum(), 0)
    total_orders    = len(df)

    last_order = df.groupby("custname")["aritemdate"].max()
    declining_count = (last_order < cutoff_inactive).sum()

    return jsonify({
        "totalCustomers":  int(total_customers),
        "totalOrders":     int(total_orders),
        "totalRevenue":    float(total_revenue),
        "decliningCount":  int(declining_count),
    })



@customers_bp.route("/top-loyalty")
def top_loyalty():
    """Get top loyal customers for dashboard chart"""
    df = current_app.config["DF_PENJUALAN"].copy()
    limit = int(request.args.get("limit", 10))
    period = request.args.get("period", "all_time")
    date_from = request.args.get("date_from")
    date_to   = request.args.get("date_to")
    if date_from:
        df = df[df["aritemdate"] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df["aritemdate"] <= pd.to_datetime(date_to)]

    # Store original date range for metadata
    period_start, period_end = _format_date_range(
        df["aritemdate"].min() if not df.empty else None,
        df["aritemdate"].max() if not df.empty else None,
    )
    
    # Filter by period if not all_time (month-based for accuracy)
    if period != "all_time" and not date_from and not date_to:
        df["month_period"] = df["aritemdate"].dt.to_period("M")
        max_period = _last_complete_period(df)

        if period == "3_months":
            start_period = max_period - 2  # Last 3 complete months
        elif period == "6_months":
            start_period = max_period - 5  # Last 6 complete months
        elif period == "12_months":
            start_period = max_period - 11  # Last 12 complete months
        else:
            start_period = max_period - 2  # default to 3 months

        df = df[(df["month_period"] >= start_period) & (df["month_period"] <= max_period)]
        period_start, period_end = _format_date_range(*_month_range_bounds(start_period, max_period))

    if date_from or date_to:
        period_start = _format_input_date(date_from) or period_start
        period_end = _format_input_date(date_to) or period_end
    
    loyalty_df = (
        df.groupby("custname")
        .agg(
            total_orders=("aritemdate", "count"),
            total_spend=("aritemdtlamt", "sum"),
        )
        .reset_index()
        .sort_values("total_spend", ascending=False)
        .head(limit)
    )
    
    loyalty_df["total_spend"] = loyalty_df["total_spend"].round(0)
    
    return jsonify({
        "customers": loyalty_df.rename(columns={"custname": "customer_name"}).to_dict(orient="records"),
        "period_start": period_start,
        "period_end": period_end
    })


@customers_bp.route("/growth")
def customer_growth():
    """Customer acquisition trend over time"""
    df = current_app.config["DF_PENJUALAN"].copy()
    period = request.args.get("period", "all_time")
    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    
    # Get first order date for each customer
    first_orders = df.groupby("custname")["aritemdate"].min().reset_index()
    first_orders["month"] = first_orders["aritemdate"].dt.to_period("M").astype(str)
    
    if date_from:
        first_orders = first_orders[first_orders["aritemdate"] >= pd.to_datetime(date_from)]
    if date_to:
        first_orders = first_orders[first_orders["aritemdate"] <= pd.to_datetime(date_to)]

    # Count new customers per month
    growth = (
        first_orders.groupby("month")
        .size()
        .reset_index(name="new_customers")
    )
    
    # Store period range
    period_start = growth['month'].min()
    period_end = growth['month'].max()
    
    # Filter by period if not all_time (month-based for accuracy)
    if period != "all_time" and not date_from and not date_to:
        growth["month_period"] = pd.PeriodIndex(growth["month"], freq="M")
        last_complete = _last_complete_period(df)
        max_period = growth["month_period"].max()
        if max_period > last_complete:
            max_period = last_complete

        if period == "3_months":
            start_period = max_period - 2  # Last 3 complete months
        elif period == "6_months":
            start_period = max_period - 5  # Last 6 complete months
        elif period == "12_months":
            start_period = max_period - 11  # Last 12 complete months
        else:
            start_period = max_period - 2  # default to 3 months

        growth = growth[(growth["month_period"] >= start_period) & (growth["month_period"] <= max_period)]
        growth = growth.drop(columns=["month_period"])
        period_start = growth["month"].min()
        period_end = growth["month"].max()
    
    # Calculate cumulative total
    growth["total_customers"] = growth["new_customers"].cumsum()
    
    if date_from or date_to:
        df_range = df.copy()
        if date_from:
            df_range = df_range[df_range["aritemdate"] >= pd.to_datetime(date_from)]
        if date_to:
            df_range = df_range[df_range["aritemdate"] <= pd.to_datetime(date_to)]
        period_start_formatted = _format_input_date(date_from) or _format_date_range(
            df_range["aritemdate"].min() if not df_range.empty else None,
            df_range["aritemdate"].min() if not df_range.empty else None,
        )[0]
        period_end_formatted = _format_input_date(date_to) or _format_date_range(
            df_range["aritemdate"].max() if not df_range.empty else None,
            df_range["aritemdate"].max() if not df_range.empty else None,
        )[1]
    elif period != "all_time" and not growth.empty:
        period_start_formatted, period_end_formatted = _format_date_range(
            *_month_range_bounds(start_period, max_period)
        )
    else:
        period_start_formatted, period_end_formatted = _format_date_range(
            df["aritemdate"].min() if not df.empty else None,
            df["aritemdate"].max() if not df.empty else None,
        )
    
    return jsonify({
        "growth": growth.to_dict(orient="records"),
        "period_start": period_start_formatted,
        "period_end": period_end_formatted
    })


@customers_bp.route("/cutoff")
def cutoff_customers():
    """Customer yang tidak bertransaksi lebih dari 2 tahun — dianggap cut-off / non-aktif permanen."""
    df = current_app.config["DF_PENJUALAN"].copy()

    # Pakai tanggal max di data sebagai acuan "sekarang"
    now = df["aritemdate"].max()
    threshold = now - timedelta(days=730)  # 2 tahun = 730 hari

    last_order = (
        df.groupby("custname")
        .agg(
            last_order_date=("aritemdate", "max"),
            total_orders=("aritemdate", "count"),
            total_spend=("aritemdtlamt", "sum"),
            first_order_date=("aritemdate", "min"),
        )
        .reset_index()
    )

    cutoff_df = last_order[last_order["last_order_date"] <= threshold].copy()
    cutoff_df["days_inactive"] = (now - cutoff_df["last_order_date"]).dt.days
    cutoff_df["years_inactive"] = (cutoff_df["days_inactive"] / 365).round(1)
    cutoff_df["last_order_date"] = cutoff_df["last_order_date"].dt.strftime("%Y-%m-%d")
    cutoff_df["first_order_date"] = cutoff_df["first_order_date"].dt.strftime("%Y-%m-%d")
    cutoff_df["total_spend"] = cutoff_df["total_spend"].round(0)
    cutoff_df = cutoff_df.sort_values("days_inactive", ascending=False)

    return jsonify({
        "count": len(cutoff_df),
        "cutoff_date": threshold.strftime("%Y-%m-%d"),
        "reference_date": now.strftime("%Y-%m-%d"),
        "customers": cutoff_df.rename(columns={"custname": "customer_name"}).to_dict(orient="records")
    })