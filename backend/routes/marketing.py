from flask import Blueprint, request, current_app
import pandas as pd

marketing_bp = Blueprint('marketing', __name__)

def get_df_with_marketing():
    """Dapatkan dataframe dengan kolom marketing_person dari salesname (DATA REAL)"""
    df = current_app.config['DF_PENJUALAN'].copy()

    df['custname'] = df['custname'].str.strip()
    df['area']     = df['area'].str.strip()

    # GUNAKAN KOLOM SALESNAME DARI DATA REAL
    df['marketing_person'] = df['salesname'].str.strip()
    df['marketing_name'] = df['salesname'].str.strip()

    return df

def filter_df_by_period(df, months=None, date_from=None, date_to=None):
    """Helper filter DataFrame by date_from/date_to atau fallback ke months"""
    from datetime import timedelta, datetime
    if date_from and date_to:
        df_r = df[(df['aritemdate'] >= date_from) & (df['aritemdate'] <= date_to)]
        def fmt(s): return datetime.strptime(s, '%Y-%m-%d').strftime('%d %b %Y')
        label = f'{fmt(date_from)} – {fmt(date_to)}'
    elif months and int(months) > 0:
        cutoff = df['aritemdate'].max() - timedelta(days=30 * int(months))
        df_r = df[df['aritemdate'] >= cutoff]
        label = f'{months} bulan terakhir'
    else:
        df_r = df
        label = 'All Time'
    return df_r, label


# ─── 1. LIST MARKETING PERSONS ─────────────────────────────────────
@marketing_bp.route('/api/marketing/persons')
def list_persons():
    """Ambil daftar marketing dari data real (salesname)"""
    df = current_app.config['DF_PENJUALAN'].copy()
    
    # Unique sales persons dari data
    persons_df = df.groupby('salesname').agg(
        total_transactions=('salesname', 'count'),
        total_omzet=('aritemdtlamt', 'sum')
    ).reset_index().sort_values('total_omzet', ascending=False)
    
    persons = [
        {
            'id': row['salesname'],
            'name': row['salesname'],
            'total_transactions': int(row['total_transactions']),
            'total_omzet': float(row['total_omzet'])
        }
        for _, row in persons_df.iterrows()
    ]
    
    return { 'status': 'success', 'data': persons }


# ─── 2. PERFORMANCE PER MARKETING ──────────────────────────────────
@marketing_bp.route('/api/marketing/performance')
def performance():
    """
    Performance ringkasan semua marketing persons (DATA REAL dari salesname)
    Params: date_from, date_to (opsional)
    """
    from datetime import timedelta, datetime
    date_from = request.args.get('date_from')
    date_to   = request.args.get('date_to')
    df = get_df_with_marketing()

    if date_from and date_to:
        df_r = df[(df['aritemdate'] >= date_from) & (df['aritemdate'] <= date_to)]
        def fmt(s): return datetime.strptime(s, '%Y-%m-%d').strftime('%d %b %Y')
        period_label = f'{fmt(date_from)} – {fmt(date_to)}'
    else:
        df_r = df
        period_label = 'All Time'

    result = []
    # Ambil unique sales persons dari data
    unique_persons = df_r['marketing_person'].unique()

    # Pre-compute dirty masks untuk seluruh df_r
    dup_mask_r = df_r.duplicated(keep=False)
    neg_mask_r = df_r['aritemqty'] < 0

    for person_name in unique_persons:
        df_p     = df_r[df_r['marketing_person'] == person_name]
        df_p_dup = df_r[dup_mask_r & (df_r['marketing_person'] == person_name)]
        df_p_neg = df_r[neg_mask_r & (df_r['marketing_person'] == person_name)]

        total_omzet   = float(df_p['aritemdtlamt'].sum())
        total_cust    = int(df_p['custname'].nunique())
        total_tx      = int(len(df_p))
        dup_omzet     = float(df_p_dup['aritemdtlamt'].sum())
        void_omzet    = float(df_p_neg['aritemdtlamt'].sum())
        dirty_tx      = int(len(df_p_dup)) + int(len(df_p_neg))
        integrity_rate= round((total_tx - dirty_tx) / total_tx * 100, 1) if total_tx > 0 else 100.0
        clean_omzet   = total_omzet - dup_omzet - abs(void_omzet)
        
        # Get last transaction date from ALL data (not filtered)
        df_person_all = df[df['marketing_person'] == person_name]
        last_tx_date = df_person_all['aritemdate'].max().strftime('%Y-%m-%d') if not df_person_all.empty else None

        result.append({
            'id':            person_name,
            'name':          person_name,
            'role':          'Sales Person',
            'total_omzet':   total_omzet,
            'clean_omzet':   clean_omzet,
            'dup_omzet':     dup_omzet,
            'void_omzet':    abs(void_omzet),
            'integrity_rate': integrity_rate,
            'total_customers': total_cust,
            'total_transactions': total_tx,
            'avg_per_customer':  round(total_omzet / total_cust, 0) if total_cust > 0 else 0,
            'last_transaction_date': last_tx_date
        })

    result.sort(key=lambda x: x['total_omzet'], reverse=True)

    return {
        'status':  'success',
        'period':  period_label,
        'data':    result
    }


# ─── 3. DETAIL SATU MARKETING ───────────────────────────────────────
@marketing_bp.route('/api/marketing/detail/<marketing_id>')
def detail(marketing_id):
    """
    Detail performance: top customers, omzet per bulan, breakdown kategori (DATA REAL)
    Params: date_from, date_to (opsional)
    """
    from datetime import timedelta, datetime
    date_from = request.args.get('date_from')
    date_to   = request.args.get('date_to')
    df = get_df_with_marketing()

    if date_from and date_to:
        df_p = df[(df['aritemdate'] >= date_from) & (df['aritemdate'] <= date_to) & (df['marketing_person'] == marketing_id)]
        def fmt(s): return datetime.strptime(s, '%Y-%m-%d').strftime('%d %b %Y')
        period_label = f'{fmt(date_from)} – {fmt(date_to)}'
    else:
        df_p = df[df['marketing_person'] == marketing_id]
        period_label = 'All Time'

    if df_p.empty:
        return { 'status': 'success', 'data': {
            'top_customers': [], 'category_breakdown': [], 'monthly_trend': []
        }}

    # Top customers
    top_custs = df_p.groupby('custname')['aritemdtlamt'].sum().reset_index()
    top_custs.columns = ['customer', 'omzet'] 
    top_custs = top_custs.sort_values('omzet', ascending=False)

    # Kategori breakdown
    cat_break = df_p.groupby('cat1shortdesc')['aritemdtlamt'].sum().reset_index()
    cat_break.columns = ['category', 'omzet']
    total = float(cat_break['omzet'].sum())
    cat_break['percentage'] = (cat_break['omzet'] / total * 100).round(1)
    cat_break = cat_break.sort_values('omzet', ascending=False)

    # Monthly trend
    df_p = df_p.copy()
    df_p['month'] = df_p['aritemdate'].dt.to_period('M').astype(str)
    monthly = df_p.groupby('month')['aritemdtlamt'].sum().reset_index()
    monthly.columns = ['month', 'omzet']
    monthly = monthly.sort_values('month')

    return {
        'status': 'success',
        'marketing_name': marketing_id,
        'period': period_label,
        'data': {
            'top_customers':      top_custs.to_dict('records'),
            'category_breakdown': cat_break.to_dict('records'),
            'monthly_trend':      monthly.to_dict('records')
        }
    }


# ─── 4. KOMISI ──────────────────────────────────────────────────────
@marketing_bp.route('/api/marketing/commission')
def commission():
    """
    Hitung komisi semua marketing untuk periode tertentu (DATA REAL).
    Params: date_from, date_to (opsional)
    """
    from datetime import timedelta, datetime
    date_from = request.args.get('date_from')
    date_to   = request.args.get('date_to')
    df = get_df_with_marketing()

    if date_from and date_to:
        df_now = df[(df['aritemdate'] >= date_from) & (df['aritemdate'] <= date_to)]
        def fmt(s): return datetime.strptime(s, '%Y-%m-%d').strftime('%d %b %Y')
        period_now_label = f'{fmt(date_from)} – {fmt(date_to)}'
        # Periode sebelumnya: rentang waktu yang sama sebelum date_from
        delta = pd.to_datetime(date_to) - pd.to_datetime(date_from)
        prev_to   = (pd.to_datetime(date_from) - timedelta(days=1)).strftime('%Y-%m-%d')
        prev_from = (pd.to_datetime(date_from) - delta - timedelta(days=1)).strftime('%Y-%m-%d')
        df_prev = df[(df['aritemdate'] >= prev_from) & (df['aritemdate'] <= prev_to)]
        period_prev_label = f'{fmt(prev_from)} – {fmt(prev_to)}'
    else:
        df_now = df
        df_prev = df[df['aritemdate'] < df['aritemdate'].min()]  # Empty
        period_now_label = 'All Time'
        period_prev_label = 'N/A'

    result = []
    unique_persons = df['marketing_person'].unique()

    for person_name in unique_persons:
        omzet_now  = float(df_now[df_now['marketing_person'] == person_name]['aritemdtlamt'].sum())
        omzet_prev = float(df_prev[df_prev['marketing_person'] == person_name]['aritemdtlamt'].sum())
        growth = ((omzet_now - omzet_prev) / omzet_prev * 100) if omzet_prev > 0 else 0
        cust_now  = int(df_now[df_now['marketing_person'] == person_name]['custname'].nunique())
        cust_prev = int(df_prev[df_prev['marketing_person'] == person_name]['custname'].nunique())

        result.append({
            'id':           person_name,
            'name':         person_name,
            'role':         'Sales Person',
            'omzet_now':    omzet_now,
            'omzet_prev':   omzet_prev,
            'growth_pct':   round(growth, 1),
            'growth_amount': omzet_now - omzet_prev,
            'customers_now':  cust_now,
            'customers_prev': cust_prev,
        })

    result.sort(key=lambda x: x['omzet_now'], reverse=True)

    return {
        'status':       'success',
        'period_now':   period_now_label,
        'period_prev':  period_prev_label,
        'data':         result
    }


# ─── 5. TOP 10 ITEMS PER MARKETING ──────────────────────────────────
@marketing_bp.route('/api/marketing/top-items/<marketing_id>')
def top_items(marketing_id):
    """
    Top 10 barang paling menguntungkan (omzet tertinggi) untuk satu sales person.
    Params: date_from, date_to (opsional)
    """
    date_from = request.args.get('date_from')
    date_to   = request.args.get('date_to')
    df = get_df_with_marketing()

    df_p, period_label = filter_df_by_period(df, None, date_from, date_to)
    df_p = df_p[df_p['marketing_person'] == marketing_id]

    if df_p.empty:
        return {'status': 'success', 'data': [], 'period': period_label}

    top = (
        df_p.groupby('itemshortdesc')
        .agg(total_omzet=('aritemdtlamt', 'sum'), total_qty=('aritemqty', 'sum'), total_tx=('aritemqty', 'count'))
        .reset_index()
        .sort_values('total_omzet', ascending=False)
        .head(10)
    )
    top['rank'] = range(1, len(top) + 1)
    top['total_omzet'] = top['total_omzet'].round(0)

    return {
        'status':  'success',
        'period':  period_label,
        'data':    top.rename(columns={'itemshortdesc': 'item_name'}).to_dict('records')
    }

