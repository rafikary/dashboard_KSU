from flask import Blueprint, request, current_app
import pandas as pd
from datetime import datetime, timedelta

category = Blueprint('category', __name__)

# Helper untuk load data dari RAM
def get_category_data():
    """Dapatkan data dari RAM (sudah di-load di app.py)"""
    df = current_app.config['DF_PENJUALAN'].copy()
    
    # Ensure date columns exist
    if 'quarter' not in df.columns:
        df['quarter'] = df['aritemdate'].dt.to_period('Q')
    if 'year' not in df.columns:
        df['year'] = df['aritemdate'].dt.year
    if 'month' not in df.columns:
        df['month'] = df['aritemdate'].dt.month
    
    return df


# 1. BREAKDOWN KATEGORI - Persentase omzet per kategori
@category.route('/api/category/breakdown', methods=['GET'])
def category_breakdown():
    """
    Menampilkan breakdown omzet per kategori produk
    Query params:
    - customer: filter spesifik customer (optional)
    - area: filter spesifik area (optional)
    - months: periode analisis dalam bulan (default: 12)
    - level: diabaikan (selalu kategori utama)
    """
    df = get_category_data()
    
    # Apply filters
    customer_filter = request.args.get('customer')
    area_filter = request.args.get('area')
    months = int(request.args.get('months', 12))
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    # Filter by date — prioritaskan date_from/date_to, lalu months
    if date_from or date_to:
        if date_from:
            df = df[df['aritemdate'] >= pd.to_datetime(date_from)]
        if date_to:
            df = df[df['aritemdate'] <= pd.to_datetime(date_to)]
    else:
        latest_date = df['aritemdate'].max()
        cutoff_date = latest_date - timedelta(days=30 * months)
        df = df[df['aritemdate'] >= cutoff_date]
    
    if customer_filter:
        df = df[df['custname'] == customer_filter]
    
    if area_filter:
        df = df[df['area'] == area_filter]
    
    # Group by kategori utama
    cat_column = 'cat1shortdesc'
    breakdown = df.groupby(cat_column)['aritemdtlamt'].sum().reset_index()
    breakdown.columns = ['category', 'total_omzet']
    
    # Hitung persentase
    total_omzet = breakdown['total_omzet'].sum()
    breakdown['percentage'] = (breakdown['total_omzet'] / total_omzet * 100).replace([float('inf'), -float('inf')], 0).round(2)
    breakdown = breakdown.sort_values('total_omzet', ascending=False)
    
    result = breakdown.to_dict('records')
    
    return {
        'status': 'success',
        'period': f'{months} bulan terakhir',
        'total_omzet': float(total_omzet),
        'category_level': 'Kategori Utama',
        'data': result
    }


# 2. TREN KATEGORI - Growth per kategori
@category.route('/api/category/trends', methods=['GET'])
def category_trends():
    """
    Menampilkan tren omzet per kategori dari waktu ke waktu
    Query params:
    - period: 'monthly' atau 'quarterly' (default: quarterly)
    - months: jumlah bulan history (default: 12)
    - level: diabaikan (selalu kategori utama)
    """
    df = get_category_data()
    
    period = request.args.get('period', 'quarterly')
    months = int(request.args.get('months', 12))
    year = request.args.get('year')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    # Filter date — prioritaskan date_from/date_to, lalu year, lalu months
    if date_from or date_to:
        if date_from:
            df = df[df['aritemdate'] >= pd.to_datetime(date_from)].copy()
        if date_to:
            df = df[df['aritemdate'] <= pd.to_datetime(date_to)].copy()
    elif year:
        df = df[df['aritemdate'].dt.year == int(year)].copy()
    else:
        latest_date = df['aritemdate'].max()
        cutoff_date = latest_date - timedelta(days=30 * months)
        df = df[df['aritemdate'] >= cutoff_date].copy()
    
    # Create period column
    if period == 'monthly':
        df['period'] = df['aritemdate'].dt.to_period('M')
    else:
        df['period'] = df['aritemdate'].dt.to_period('Q')
    
    # Group by category and period
    cat_column = 'cat1shortdesc'
    trends = df.groupby([cat_column, 'period'])['aritemdtlamt'].sum().reset_index()
    trends['period'] = trends['period'].astype(str)
    trends.columns = ['category', 'period', 'omzet']
    
    # Format untuk chart (series per category)
    result = []
    for category in trends['category'].unique():
        cat_data = trends[trends['category'] == category].sort_values('period')
        result.append({
            'category': category,
            'periods': cat_data['period'].tolist(),
            'omzet': cat_data['omzet'].tolist()
        })
    
    return {
        'status': 'success',
        'period_type': period,
        'category_level': 'cat1',
        'data': result
    }


# 3. TOP ITEMS PER KATEGORI
@category.route('/api/category/top-items', methods=['GET'])
def top_items_by_category():
    """
    Menampilkan top items dalam setiap kategori
    Query params:
    - category: spesifik kategori (optional)
    - limit: jumlah top items per kategori (default: 5)
    - months: periode analisis (default: 12)
    """
    df = get_category_data()
    
    category_filter = request.args.get('category')
    limit = int(request.args.get('limit', 5))
    months = int(request.args.get('months', 12))
    
    # Filter date
    latest_date = df['aritemdate'].max()
    cutoff_date = latest_date - timedelta(days=30 * months)
    df = df[df['aritemdate'] >= cutoff_date]
    
    if category_filter:
        df = df[df['cat1shortdesc'] == category_filter]
    
    # Group by category and item
    top_items = df.groupby(['cat1shortdesc', 'itemshortdesc']).agg({
        'aritemdtlamt': 'sum',
        'aritemqty': 'sum'
    }).reset_index()
    
    top_items.columns = ['category', 'item', 'total_omzet', 'total_qty']
    top_items = top_items.sort_values(['category', 'total_omzet'], ascending=[True, False])
    
    # Get top N per category
    result = []
    for category in top_items['category'].unique():
        cat_data = top_items[top_items['category'] == category].head(limit)
        result.append({
            'category': category,
            'top_items': cat_data[['item', 'total_omzet', 'total_qty']].to_dict('records')
        })
    
    return {
        'status': 'success',
        'period': f'{months} bulan terakhir',
        'data': result
    }


# 4. COMPARISON KATEGORI - Periode vs Periode
@category.route('/api/category/comparison', methods=['GET'])
def category_comparison():
    """
    Membandingkan performa kategori antara 2 periode
    Useful untuk analisis 6 bulanan vs 6 bulanan sebelumnya (untuk komisi)
    
    Query params:
    - months: jumlah bulan untuk setiap periode (default: 6)
    - level: diabaikan (selalu kategori utama)
    """
    df = get_category_data()
    
    months = int(request.args.get('months', 6))
    p1_from = request.args.get('p1_from')
    p1_to   = request.args.get('p1_to')
    p2_from = request.args.get('p2_from')
    p2_to   = request.args.get('p2_to')

    if p1_from and p1_to and p2_from and p2_to:
        df_period1 = df[(df['aritemdate'] >= pd.to_datetime(p1_from)) &
                        (df['aritemdate'] < pd.to_datetime(p1_to) + timedelta(days=1))]
        df_period2 = df[(df['aritemdate'] >= pd.to_datetime(p2_from)) &
                        (df['aritemdate'] < pd.to_datetime(p2_to) + timedelta(days=1))]
        def fmt(s): return datetime.strptime(s, '%Y-%m-%d').strftime('%d %b %Y')
        period1_label = f"{fmt(p1_from)} – {fmt(p1_to)}"
        period2_label = f"{fmt(p2_from)} – {fmt(p2_to)}"
    else:
        # Bagi jadi 2 periode berdasarkan months
        latest_date = df['aritemdate'].max()
        period2_start = latest_date - timedelta(days=30 * months)
        period1_start = period2_start - timedelta(days=30 * months)
        df_period1 = df[(df['aritemdate'] >= period1_start) & (df['aritemdate'] < period2_start)]
        df_period2 = df[df['aritemdate'] >= period2_start]
        period1_label = f'{months} bulan sebelumnya'
        period2_label = f'{months} bulan terakhir'
    
    # Aggregate per kategori utama
    cat_column = 'cat1shortdesc'
    
    omzet_p1 = df_period1.groupby(cat_column)['aritemdtlamt'].sum()
    omzet_p2 = df_period2.groupby(cat_column)['aritemdtlamt'].sum()
    
    # Combine
    comparison = pd.DataFrame({
        'period1_omzet': omzet_p1,
        'period2_omzet': omzet_p2
    }).fillna(0)
    
    comparison['growth_amount'] = comparison['period2_omzet'] - comparison['period1_omzet']
    comparison['growth_pct'] = ((comparison['period2_omzet'] - comparison['period1_omzet']) / 
                                 comparison['period1_omzet'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
    
    # Calculate percentage of total
    total_p1 = comparison['period1_omzet'].sum()
    total_p2 = comparison['period2_omzet'].sum()
    
    comparison['period1_pct'] = (comparison['period1_omzet'] / total_p1 * 100).replace([float('inf'), -float('inf')], 0).round(2)
    comparison['period2_pct'] = (comparison['period2_omzet'] / total_p2 * 100).replace([float('inf'), -float('inf')], 0).round(2)
    
    # Sort by period2 omzet
    comparison = comparison.sort_values('period2_omzet', ascending=False)
    
    result = []
    for category, row in comparison.iterrows():
        result.append({
            'category': category,
            'period1_omzet': float(row['period1_omzet']),
            'period2_omzet': float(row['period2_omzet']),
            'period1_pct': float(row['period1_pct']),
            'period2_pct': float(row['period2_pct']),
            'growth_amount': float(row['growth_amount']),
            'growth_pct': float(row['growth_pct'])
        })
    
    return {
        'status': 'success',
        'period1': period1_label,
        'period2': period2_label,
        'period1_total': float(total_p1),
        'period2_total': float(total_p2),
        'overall_growth_pct': float((total_p2 - total_p1) / total_p1 * 100) if total_p1 > 0 else 0,
        'data': result
    }

