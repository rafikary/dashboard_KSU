from flask import Blueprint, jsonify, request, current_app
import pandas as pd
from datetime import datetime
import re

aireport_bp = Blueprint('aireport', __name__)

def smart_filter_dataframe(df, column, search_term):
    """
    Smart filtering with multiple fallback strategies:
    1. Exact match (case-insensitive)
    2. Partial match with escaped special characters
    3. Fuzzy multi-word match
    """
    # Clean the column
    df[column] = df[column].astype(str).str.strip()
    
    # Strategy 1: Exact match
    exact_mask = df[column].str.upper() == search_term.upper()
    if exact_mask.any():
        return df[exact_mask].copy()
    
    # Strategy 2: Partial match (escape special regex chars)
    try:
        safe_term = re.escape(search_term)
        contains_mask = df[column].str.contains(safe_term, case=False, na=False, regex=True)
        if contains_mask.any():
            return df[contains_mask].copy()
    except Exception as e:
        print(f"[Filter] Regex error: {e}")
    
    # Strategy 3: Fuzzy multi-word match
    words = search_term.split()
    if len(words) > 1:
        fuzzy_mask = pd.Series(True, index=df.index)
        for word in words:
            if len(word) > 2:  # Only consider words longer than 2 chars
                safe_word = re.escape(word)
                fuzzy_mask = fuzzy_mask & df[column].str.contains(safe_word, case=False, na=False, regex=True)
        
        if fuzzy_mask.any():
            return df[fuzzy_mask].copy()
    
    # Nothing found
    return pd.DataFrame()

@aireport_bp.route("/api/aireport")
def generate_ai_report():
    """Generate AI report based ONLY on secure SQL token from Chatbot."""
    try:
        # Hanya menerima parameter ID (yang sekarang berisi Token UUID)
        token_id = request.args.get("id", "")
        
        if not token_id:
            return jsonify({"error": True, "message": "Token laporan tidak ditemukan."}), 400
            
        print(f"[AI Report] Mengambil data SQL dari token: {token_id}")
        
        # Langsung ambil data dari memori chatbot
        from chatbot_ai import get_data_for_report_by_token
        filtered_df = get_data_for_report_by_token(token_id)
        
        if filtered_df.empty:
            return jsonify({"error": True, "message": "Tidak ada data untuk laporan ini."}), 404
            
        # [SAFE MODE] Cek ketersediaan kolom untuk merender grafik/widget
        cols = [c.lower() for c in filtered_df.columns]
        
        summary_metrics = generate_summary_metrics(filtered_df) if 'aritemdtlamt' in cols and 'aritemqty' in cols else []
        ai_insights = generate_ai_insights(filtered_df) if 'aritemdate' in cols and 'aritemdtlamt' in cols else []
        trend_data = generate_trend_data(filtered_df) if 'aritemdate' in cols and 'aritemdtlamt' in cols else []
        category_data = generate_category_data(filtered_df) if 'cat1shortdesc' in cols and 'aritemdtlamt' in cols else []
        
        # [TABEL DINAMIS] Ubah dataframe mentah menjadi JSON untuk tabel
        df_safe = filtered_df.copy()
        for col in df_safe.columns:
            if pd.api.types.is_datetime64_any_dtype(df_safe[col]):
                df_safe[col] = df_safe[col].dt.strftime('%Y-%m-%d')
        recent_transactions = df_safe.fillna('-').to_dict('records')
        
        return jsonify({
            "summary": summary_metrics,
            "insights": ai_insights,
            "trend": trend_data,
            "categories": category_data,
            "transactions": recent_transactions,
            "entity_name": "Laporan Analitik AI",
            "generated_at": datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"[AI Report ERROR] {str(e)}")
        return jsonify({"error": True, "message": str(e)}), 500

def generate_summary_metrics(df, report_type):
    """Generate executive summary metrics"""
    total_revenue = df['aritemdtlamt'].sum()
    total_quantity = df['aritemqty'].sum()
    total_transactions = len(df)
    
    # Calculate growth (compare last 3 months vs previous 3 months)
    latest_date = df['aritemdate'].max()
    df['month'] = df['aritemdate'].dt.to_period('M')
    
    # Last 3 months
    last_3_months = df['month'].unique()[-3:] if len(df['month'].unique()) >= 3 else df['month'].unique()
    prev_3_months = df['month'].unique()[-6:-3] if len(df['month'].unique()) >= 6 else []
    
    last_revenue = df[df['month'].isin(last_3_months)]['aritemdtlamt'].sum()
    prev_revenue = df[df['month'].isin(prev_3_months)]['aritemdtlamt'].sum() if len(prev_3_months) > 0 else last_revenue
    
    revenue_growth = ((last_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0
    
    # Average order value
    avg_order_value = total_revenue / total_transactions if total_transactions > 0 else 0
    
    # Unique customers or products
    if report_type == "customer":
        unique_count = df['itemshortdesc'].nunique()
        unique_label = "Produk Dibeli"
        unique_icon = "ri-shopping-bag-3-line"
    elif report_type == "product":
        unique_count = df['custname'].nunique()
        unique_label = "Customer Unik"
        unique_icon = "ri-group-line"
    else:
        unique_count = df['custname'].nunique()
        unique_label = "Customer Unik"
        unique_icon = "ri-group-line"
    
    metrics = [
        {
            "label": "Total Pendapatan",
            "value": f"Rp {total_revenue:,.0f}",
            "change": f"{revenue_growth:+.1f}% vs periode sebelumnya",
            "trendClass": "positive" if revenue_growth > 0 else "negative" if revenue_growth < 0 else "neutral",
            "trendIcon": "ri-arrow-up-line" if revenue_growth > 0 else "ri-arrow-down-line" if revenue_growth < 0 else "ri-subtract-line",
            "icon": "ri-money-dollar-circle-line",
            "iconBg": "rgba(16, 185, 129, 0.2)",
            "iconColor": "#10b981"
        },
        {
            "label": "Total Kuantitas",
            "value": f"{total_quantity:,.0f} pcs",
            "change": f"{total_transactions:,} transaksi",
            "trendClass": "neutral",
            "trendIcon": "ri-shopping-cart-line",
            "icon": "ri-stack-line",
            "iconBg": "rgba(59, 130, 246, 0.2)",
            "iconColor": "#3b82f6"
        },
        {
            "label": unique_label,
            "value": f"{unique_count:,}",
            "change": "Entitas unik",
            "trendClass": "neutral",
            "trendIcon": "ri-checkbox-circle-line",
            "icon": unique_icon,
            "iconBg": "rgba(245, 158, 11, 0.2)",
            "iconColor": "#f59e0b"
        },
        {
            "label": "Rata-rata Nilai Order",
            "value": f"Rp {avg_order_value:,.0f}",
            "change": "Per transaksi",
            "trendClass": "neutral",
            "trendIcon": "ri-line-chart-line",
            "icon": "ri-calculator-line",
            "iconBg": "rgba(139, 92, 246, 0.2)",
            "iconColor": "#8b5cf6"
        }
    ]
    
    return metrics


def generate_ai_insights(df, report_type, entity_id):
    """Generate AI-powered insights with recommendations"""
    insights = []
    
    # Insight 1: Performance trend
    df['month'] = df['aritemdate'].dt.to_period('M')
    monthly_revenue = df.groupby('month')['aritemdtlamt'].sum().sort_index()
    
    if len(monthly_revenue) >= 2:
        recent_trend = monthly_revenue.iloc[-1] - monthly_revenue.iloc[-2]
        if recent_trend > 0:
            insights.append({
                "type": "success",
                "icon": "ri-arrow-up-circle-line",
                "badge": "Pertumbuhan Terdeteksi",
                "title": "Tren Pendapatan Positif",
                "description": f"Pendapatan meningkat Rp {recent_trend:,.0f} dibanding periode sebelumnya. Pertahankan strategi saat ini dan eksplorasi peluang ekspansi."
            })
        elif recent_trend < 0:
            insights.append({
                "type": "warning",
                "icon": "ri-alert-line",
                "badge": "Perlu Tindakan",
                "title": "Penurunan Pendapatan Terdeteksi",
                "description": f"Pendapatan menurun Rp {abs(recent_trend):,.0f}. Pertimbangkan untuk merevisi strategi marketing atau menawarkan promosi untuk meningkatkan penjualan."
            })
    
    # Insight 2: Top category opportunity
    if 'cat1shortdesc' in df.columns:
        top_category = df.groupby('cat1shortdesc')['aritemdtlamt'].sum().sort_values(ascending=False).head(1)
        if len(top_category) > 0:
            cat_name = top_category.index[0]
            cat_revenue = top_category.iloc[0]
            insights.append({
                "type": "info",
                "icon": "ri-pie-chart-2-line",
                "badge": "Terbaik",
                "title": f"Kategori Terdepan: {cat_name}",
                "description": f"Kategori ini menghasilkan Rp {cat_revenue:,.0f} pendapatan. Fokuskan upaya marketing di sini untuk ROI maksimal."
            })
    
    # Insight 3: Customer/Product diversity
    if report_type == "customer":
        product_count = df['itemshortdesc'].nunique()
        if product_count < 5:
            insights.append({
                "type": "warning",
                "icon": "ri-lightbulb-line",
                "badge": "Peluang Upsell",
                "title": "Portofolio Produk Terbatas",
                "description": f"Hanya {product_count} produk dibeli. Pertimbangkan cross-selling produk komplementer untuk meningkatkan nilai order."
            })
        else:
            insights.append({
                "type": "success",
                "icon": "ri-star-smile-line",
                "badge": "Pelanggan Aktif",
                "title": "Minat Produk Beragam",
                "description": f"{product_count} produk berbeda dibeli. Customer ini menunjukkan engagement dan loyalitas tinggi."
            })
    
    elif report_type == "product":
        customer_count = df['custname'].nunique()
        if customer_count < 5:
            insights.append({
                "type": "danger",
                "icon": "ri-error-warning-line",
                "badge": "Peringatan Risiko",
                "title": "Basis Pelanggan Terbatas",
                "description": f"Hanya {customer_count} pelanggan membeli produk ini. Perluas jangkauan marketing untuk mendapat lebih banyak pembeli."
            })
        else:
            insights.append({
                "type": "success",
                "icon": "ri-medal-line",
                "badge": "Produk Populer",
                "title": "Permintaan Pasar Kuat",
                "description": f"{customer_count} pelanggan unik membeli produk ini. Pertimbangkan untuk menambah stok."
            })
    
    # Insight 4: Seasonality pattern
    df['month_name'] = df['aritemdate'].dt.month_name()
    monthly_sales = df.groupby('month_name')['aritemdtlamt'].sum().sort_values(ascending=False)
    if len(monthly_sales) > 0:
        peak_month = monthly_sales.index[0]
        # Translate month names to Indonesian
        month_translation = {
            'January': 'Januari', 'February': 'Februari', 'March': 'Maret',
            'April': 'April', 'May': 'Mei', 'June': 'Juni',
            'July': 'Juli', 'August': 'Agustus', 'September': 'September',
            'October': 'Oktober', 'November': 'November', 'December': 'Desember'
        }
        peak_month_id = month_translation.get(peak_month, peak_month)
        insights.append({
            "type": "info",
            "icon": "ri-calendar-check-line",
            "badge": "Wawasan Musiman",
            "title": f"Performa Puncak: {peak_month_id}",
            "description": f"Penjualan biasanya mencapai puncak di bulan {peak_month_id}. Rencanakan inventori dan promosi dengan sesuai untuk hasil optimal."
        })
    
    return insights


def generate_trend_data(df):
    """Generate monthly trend data for line chart"""
    df['month_year'] = df['aritemdate'].dt.to_period('M').astype(str)
    
    monthly_trend = df.groupby('month_year').agg({
        'aritemdtlamt': 'sum'
    }).reset_index()
    
    monthly_trend = monthly_trend.sort_values('month_year')
    
    trend_data = []
    for _, row in monthly_trend.iterrows():
        trend_data.append({
            "month": row['month_year'],
            "value": float(row['aritemdtlamt'])
        })
    
    return trend_data


def generate_category_data(df):
    """Generate category distribution for pie chart"""
    if 'cat1shortdesc' not in df.columns:
        return []
    
    category_sales = df.groupby('cat1shortdesc')['aritemdtlamt'].sum().sort_values(ascending=False).head(6)
    
    category_data = []
    for cat, value in category_sales.items():
        category_data.append({
            "category": cat,
            "value": float(value)
        })
    
    return category_data


def generate_recent_transactions(df, report_type):
    """Generate all transactions sorted by date"""
    # JIKA CUSTOM: Kembalikan dictionary mentah apa adanya
    if report_type == "custom":
        df_safe = df.copy()
        # Konversi datetime agar bisa dikirim sebagai JSON
        for col in df_safe.columns:
            if pd.api.types.is_datetime64_any_dtype(df_safe[col]):
                df_safe[col] = df_safe[col].dt.strftime('%Y-%m-%d')
        # Format angka agar tidak ada NaN/Inf
        return df_safe.fillna('-').to_dict('records')

    df_sorted = df.sort_values('aritemdate', ascending=False)
    
    transactions = []
    for _, row in df_sorted.iterrows():
        if report_type == "customer":
            entity_field = row.get('itemshortdesc', 'N/A')
        else:
            entity_field = row.get('custname', 'N/A')
        
        transactions.append({
            "date": row['aritemdate'].strftime('%Y-%m-%d'),
            "entity": entity_field,
            "category": row.get('cat1shortdesc', 'N/A'),
            "quantity": float(row['aritemqty']),
            "amount": float(row['aritemdtlamt'])
        })
    
    return transactions
