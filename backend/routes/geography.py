from flask import Blueprint, request, current_app
import pandas as pd
from datetime import datetime, timedelta
import re

geography = Blueprint('geography', __name__)

def extract_city_from_customer_name(custname):
    """
    Extract kota dari nama customer untuk fix data entry yang salah.
    Contoh: 'GRAND MERCURE MALANG' -> 'MALANG'
    """
    if pd.isna(custname):
        return None
    
    custname_upper = str(custname).upper()
    
    # Daftar kota-kota besar yang sering muncul di nama customer
    # Urutkan dari yang lebih spesifik ke umum (YOGYAKARTA sebelum JAKARTA)
    cities = [
        'YOGYAKARTA', 'BALIKPAPAN', 'BANJARMASIN', 'BANYUWANGI', 'TANJUNGPINANG',
        'PALANGKARAYA', 'PANGKALPINANG', 'PONTIANAK', 'SAMARINDA', 'BANDAR LAMPUNG',
        'PEKANBARU', 'PALEMBANG', 'JAKARTA', 'BANDUNG', 'SURABAYA', 'SEMARANG', 
        'MALANG', 'MEDAN', 'MAKASSAR', 'DENPASAR', 'BALI', 'MANADO', 'BATAM',
        'BOGOR', 'TANGERANG', 'BEKASI', 'DEPOK', 'SOLO', 'SURAKARTA', 
        'MAGELANG', 'KEDIRI', 'BLITAR', 'PROBOLINGGO', 'JEMBER', 'BANYUWANGI',
        'MADIUN', 'PONOROGO', 'TULUNGAGUNG', 'SIDOARJO', 'GRESIK', 'MOJOKERTO',
        'PASURUAN', 'LUMAJANG', 'SITUBONDO', 'BONDOWOSO', 'BATU', 'KUPANG',
        'LOMBOK', 'MATARAM', 'UBUD', 'KUTA', 'SEMINYAK', 'NUSA DUA', 'CIREBON',
        'TASIKMALAYA', 'PURWOKERTO', 'CILACAP', 'PEKALONGAN', 'TEGAL',
        'PADANG', 'BUKITTINGGI', 'JAMBI', 'BENGKULU', 'LAMPUNG', 'AMBON',
        'JAYAPURA', 'SORONG', 'MANOKWARI', 'PALU', 'KENDARI', 'GORONTALO'
    ]
    
    # Cari kota yang ada di nama customer
    for city in cities:
        if city in custname_upper:
            return city
    
    return None

def get_geography_data():
    """Ambil data dari RAM dengan kolom tambahan untuk geography analysis"""
    df = current_app.config['DF_PENJUALAN'].copy()
    
    # Tambahkan kolom yang dibutuhkan untuk analisis geography
    if 'quarter' not in df.columns:
        df['quarter'] = df['aritemdate'].dt.to_period('Q')
    if 'month_str' not in df.columns:
        df['month_str'] = df['aritemdate'].dt.to_period('M').astype(str)
    
    return df


@geography.route('/api/geography/area-performance')
def area_performance():
    """Get top areas by revenue with growth trends"""
    df = get_geography_data()
    limit = int(request.args.get('limit', 10))
    
    # Calculate total revenue per area
    area_revenue = (
        df.groupby('area')
        .agg(
            total_revenue=('aritemdtlamt', 'sum'),
            total_orders=('aritemdate', 'count'),
            unique_customers=('custname', 'nunique')
        )
        .reset_index()
        .sort_values('total_revenue', ascending=False)
        .head(limit)
    )
    
    area_revenue['total_revenue'] = area_revenue['total_revenue'].round(0)
    
    return {
        'areas': area_revenue.to_dict(orient='records')
    }
    if 'year' not in df.columns:
        df['year'] = df['aritemdate'].dt.year
    if 'month' not in df.columns:
        df['month'] = df['aritemdate'].dt.month
    
    return df

def filter_by_month_range(df, month_from, month_to):
    """Helper untuk memfilter data berdasarkan parameter 'from' dan 'to'"""
    if month_from: 
        df = df[df['month_str'] >= month_from]
    if month_to: 
        df = df[df['month_str'] <= month_to]
    return df

def filter_by_date_range(df, date_from, date_to):
    """Helper filter berdasarkan tanggal penuh (YYYY-MM-DD)"""
    if date_from:
        df = df[df['aritemdate'] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df['aritemdate'] < pd.to_datetime(date_to) + pd.Timedelta(days=1)]
    return df

@geography.route('/api/geography/ranking-by-area', methods=['GET'])
def ranking_by_area():
    df = get_geography_data()
    area_filter = request.args.get('area')
    limit = int(request.args.get('limit', 10))
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    df = filter_by_date_range(df, date_from, date_to)
    if area_filter: df = df[df['area'] == area_filter]
    
    ranking = df.groupby(['area', 'custname'])['aritemdtlamt'].sum().reset_index()
    ranking.columns = ['area', 'customer', 'total_omzet']
    ranking = ranking.sort_values(['area', 'total_omzet'], ascending=[True, False])
    
    result = []
    for area in ranking['area'].unique():
        area_data = ranking[ranking['area'] == area].head(limit)
        result.append({
            'area': area,
            'top_customers': area_data[['customer', 'total_omzet']].to_dict('records')
        })
    
    return {'status': 'success', 'data': result, 'total_areas': len(result)}


@geography.route('/api/geography/ranking-by-city', methods=['GET'])
def ranking_by_city():
    """Ranking customer per kota (city), dengan auto-fix dari nama customer"""
    df = get_geography_data()
    city_filter = request.args.get('city')
    limit = int(request.args.get('limit', 10))
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    min_omzet = float(request.args.get('min_omzet', 100000000))  # Filter kota dengan min omzet 100jt
    
    df = filter_by_date_range(df, date_from, date_to)
    
    # SMART FIX: Extract city dari customer name, gunakan sebagai prioritas
    df['extracted_city'] = df['custname'].apply(extract_city_from_customer_name)
    
    # Gunakan extracted_city jika ada, jika tidak pakai kolom kota original
    df['corrected_city'] = df['extracted_city'].fillna(df['kota'])
    
    if city_filter: 
        df = df[df['corrected_city'] == city_filter]
    
    # Group by corrected city and customer
    ranking = df.groupby(['corrected_city', 'custname'])['aritemdtlamt'].sum().reset_index()
    ranking.columns = ['city', 'customer', 'total_omzet']
    ranking = ranking.sort_values(['city', 'total_omzet'], ascending=[True, False])
    
    # Filter only cities with total omzet >= min_omzet to avoid too many small cities
    city_totals = df.groupby('corrected_city')['aritemdtlamt'].sum()
    significant_cities = city_totals[city_totals >= min_omzet].index.tolist()
    
    result = []
    for city in sorted(significant_cities):
        city_data = ranking[ranking['city'] == city].head(limit)
        if not city_data.empty:
            result.append({
                'city': city,
                'total_city_omzet': float(city_totals[city]),
                'top_customers': city_data[['customer', 'total_omzet']].to_dict('records')
            })
    
    # Sort by total city omzet descending
    result = sorted(result, key=lambda x: x['total_city_omzet'], reverse=True)
    
    return {'status': 'success', 'data': result, 'total_cities': len(result)}


@geography.route('/api/geography/priority-areas', methods=['GET'])
def priority_areas():
    df = get_geography_data()
    # Support both explicit p1/p2 params and legacy date_from/date_to (auto-split)
    p1_from = request.args.get('p1_from')
    p1_to = request.args.get('p1_to')
    p2_from = request.args.get('p2_from')
    p2_to = request.args.get('p2_to')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if p1_from and p1_to and p2_from and p2_to:
        # Explicit period mode
        df_period1 = filter_by_date_range(df.copy(), p1_from, p1_to)
        df_period2 = filter_by_date_range(df.copy(), p2_from, p2_to)
        from datetime import datetime
        def fmt(s): return datetime.strptime(s, '%Y-%m-%d').strftime('%d %b %Y')
        p1_label = f"{fmt(p1_from)} – {fmt(p1_to)}"
        p2_label = f"{fmt(p2_from)} – {fmt(p2_to)}"
    else:
        # Legacy: auto-split single range at midpoint
        df_recent = filter_by_date_range(df, date_from, date_to)
        if not df_recent.empty:
            min_date = df_recent['aritemdate'].min()
            max_date = df_recent['aritemdate'].max()
            mid_date = min_date + (max_date - min_date) / 2
            p1_label = f"{min_date.strftime('%d %b %Y')} – {(mid_date - pd.Timedelta(days=1)).strftime('%d %b %Y')}"
            p2_label = f"{mid_date.strftime('%d %b %Y')} – {max_date.strftime('%d %b %Y')}"
            df_period1 = df_recent[df_recent['aritemdate'] < mid_date]
            df_period2 = df_recent[df_recent['aritemdate'] >= mid_date]
        else:
            df_period1 = df_period2 = df.iloc[0:0]
            p1_label = p2_label = '-'

    omzet_p1 = df_period1.groupby('area')['aritemdtlamt'].sum()
    omzet_p2 = df_period2.groupby('area')['aritemdtlamt'].sum()
    
    comparison = pd.DataFrame({'period1_omzet': omzet_p1, 'period2_omzet': omzet_p2}).fillna(0)
    comparison['growth_pct'] = ((comparison['period2_omzet'] - comparison['period1_omzet']) / 
                                 comparison['period1_omzet'] * 100).replace([float('inf'), -float('inf')], 0).fillna(0)
    comparison['growth_amount'] = comparison['period2_omzet'] - comparison['period1_omzet']
    comparison = comparison.sort_values('growth_pct')
    
    result = []
    for area, row in comparison.iterrows():
        if row['growth_pct'] < -10:
            priority, reason = 'HIGH', f"Omzet turun {abs(row['growth_pct']):.1f}%, perlu kunjungan segera"
        elif row['growth_pct'] < 0:
            priority, reason = 'MEDIUM', f"Ada penurunan {abs(row['growth_pct']):.1f}%, perlu monitoring"
        elif row['growth_pct'] < 10:
            priority, reason = 'LOW', "Performa stabil, kunjungan rutin"
        else:
            priority, reason = 'MAINTAIN', f"Performa bagus (+{row['growth_pct']:.1f}%), pertahankan momentum"
        
        result.append({
            'area': area, 'priority': priority, 'reason': reason,
            'period1_omzet': float(row['period1_omzet']), 'period2_omzet': float(row['period2_omzet']),
            'growth_pct': float(row['growth_pct']), 'growth_amount': float(row['growth_amount'])
        })
    
    return {
        'status': 'success',
        'data': result,
        'period1_label': p1_label,
        'period2_label': p2_label
    }


@geography.route('/api/geography/area-trends', methods=['GET'])
def area_trends():
    df = get_geography_data()
    period = request.args.get('period', 'quarterly')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    year_filter = request.args.get('year')
    
    df_recent = filter_by_date_range(df, date_from, date_to)
    if year_filter:
        df_recent = df_recent[df_recent['aritemdate'].dt.year == int(year_filter)]
    
    if period == 'monthly':
        df_recent['period'] = df_recent['aritemdate'].dt.to_period('M')
    else:
        df_recent['period'] = df_recent['aritemdate'].dt.to_period('Q')
    
    trends = df_recent.groupby(['area', 'period'])['aritemdtlamt'].sum().reset_index()
    trends['period'] = trends['period'].astype(str)
    trends.columns = ['area', 'period', 'omzet']
    
    result = []
    for area in trends['area'].unique():
        area_data = trends[trends['area'] == area].sort_values('period')
        result.append({'area': area, 'periods': area_data['period'].tolist(), 'omzet': area_data['omzet'].tolist()})
    
    return {'status': 'success', 'data': result}


@geography.route('/api/geography/period-comparison', methods=['GET'])
def period_comparison():
    """Bandingkan omzet antar dua periode bebas (untuk perhitungan komisi)"""
    from datetime import datetime
    df = get_geography_data()
    p1_from = request.args.get('p1_from')
    p1_to = request.args.get('p1_to')
    p2_from = request.args.get('p2_from')
    p2_to = request.args.get('p2_to')

    df_p1 = filter_by_date_range(df.copy(), p1_from, p1_to)
    df_p2 = filter_by_date_range(df.copy(), p2_from, p2_to)

    # Format period labels
    def fmt(s): return datetime.strptime(s, '%Y-%m-%d').strftime('%d %b %Y') if s else '-'
    period1_label = f"{fmt(p1_from)} – {fmt(p1_to)}" if p1_from and p1_to else 'Periode 1'
    period2_label = f"{fmt(p2_from)} – {fmt(p2_to)}" if p2_from and p2_to else 'Periode 2'

    omzet_p1 = df_p1.groupby('area')['aritemdtlamt'].sum()
    omzet_p2 = df_p2.groupby('area')['aritemdtlamt'].sum()

    all_areas = omzet_p1.index.union(omzet_p2.index)
    comparison = pd.DataFrame({
        'period1_omzet': omzet_p1.reindex(all_areas, fill_value=0),
        'period2_omzet': omzet_p2.reindex(all_areas, fill_value=0)
    })
    comparison['growth_amount'] = comparison['period2_omzet'] - comparison['period1_omzet']
    comparison['growth_pct'] = comparison.apply(
        lambda r: ((r['period2_omzet'] - r['period1_omzet']) / r['period1_omzet'] * 100)
                  if r['period1_omzet'] > 0 else 0, axis=1
    )
    comparison = comparison.sort_values('growth_pct')

    result = []
    for area, row in comparison.iterrows():
        result.append({
            'area': area,
            'period1_omzet': float(row['period1_omzet']),
            'period2_omzet': float(row['period2_omzet']),
            'growth_amount': float(row['growth_amount']),
            'growth_pct': float(row['growth_pct'])
        })

    return {
        'status': 'success',
        'period1_label': period1_label,
        'period2_label': period2_label,
        'data': result
    }


# 4. SUMMARY GEOGRAFIS - Overview semua area
@geography.route('/api/geography/summary', methods=['GET'])
def geography_summary():
    """
    Summary overview semua area: total omzet, jumlah customer, avg transaction
    """
    df = get_geography_data()
    
    summary = df.groupby('area').agg({
        'custname': 'nunique',
        'aritemdtlamt': ['sum', 'count', 'mean']
    }).reset_index()
    
    summary.columns = ['area', 'total_customers', 'total_omzet', 'total_transactions', 'avg_transaction']
    summary = summary.sort_values('total_omzet', ascending=False)
    
    result = summary.to_dict('records')
    
    return {
        'status': 'success',
        'total_areas': len(result),
        'data': result
    }
