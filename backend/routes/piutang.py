from flask import Blueprint, request, current_app, jsonify
import pandas as pd
import os


piutang_bp = Blueprint('piutang', __name__)


def get_df():
    """Load piutang parquet lazily, enrich with kota from penjualan, cache in app config."""
    df = current_app.config.get('DF_PIUTANG')
    if df is None:
        base = os.path.dirname(os.path.dirname(__file__))
        path = os.path.join(base, 'data', 'piutang.parquet')
        if not os.path.exists(path):
            return pd.DataFrame()
        df = pd.read_parquet(path)
        df['aritemdate']    = pd.to_datetime(df['aritemdate'],    errors='coerce')
        df['aritemduedate'] = pd.to_datetime(df['aritemduedate'], errors='coerce')
        for col in ['area', 'custname', 'salesname', 'aritemno']:
            df[col] = df[col].astype(str).str.strip()

        # ── Deduplicate by aritemno — keep latest state per invoice ──
        df = (
            df.sort_values('aritemdate', ascending=True)
              .drop_duplicates(subset='aritemno', keep='last')
        )

        # ── Enrich with kota from penjualan ──────────────────────────
        df_s = current_app.config.get('DF_PENJUALAN')
        if df_s is not None and not df_s.empty and 'kota' in df_s.columns:
            kota_map = (
                df_s.assign(custname=df_s['custname'].astype(str).str.strip())
                .groupby('custname')['kota']
                .first()
            )
            df['kota'] = df['custname'].map(kota_map).astype(str).str.strip()
            df['kota'] = df['kota'].replace('nan', None)
        else:
            df['kota'] = None

        current_app.config['DF_PIUTANG'] = df
    return df


def unpaid(df):
    """Return only rows with outstanding balance."""
    return df[df['arbalance'] > 0].copy()


def aging_label(days):
    if days <= 30:
        return '0-30 hari'
    elif days <= 60:
        return '31-60 hari'
    elif days <= 90:
        return '61-90 hari'
    elif days <= 180:
        return '91-180 hari'
    else:
        return '>180 hari'


AGING_ORDER = ['0-30 hari', '31-60 hari', '61-90 hari', '91-180 hari', '>180 hari']


def apply_filters(df, area=None, salesname=None, bucket=None, kota=None, date_from=None, date_to=None):
    if area and area != 'all':
        df = df[df['area'] == area]
    if salesname and salesname != 'all':
        df = df[df['salesname'] == salesname]
    if kota and kota != 'all':
        df = df[df['kota'] == kota]
    if bucket and bucket != 'all':
        df['_bucket'] = df['umurpiutang'].apply(aging_label)
        df = df[df['_bucket'] == bucket]
    if date_from:
        df = df[df['aritemdate'] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df['aritemdate'] <= pd.to_datetime(date_to)]
    return df


def get_date_params():
    """Helper: ambil date_from & date_to dari request args."""
    return request.args.get('date_from'), request.args.get('date_to')


# ─── 0. DATE RANGE ────────────────────────────────────────────────────
@piutang_bp.route('/api/piutang/date-range')
def date_range():
    df = get_df()
    if df.empty:
        return jsonify({'min': None, 'max': None})
    return jsonify({
        'min': df['aritemdate'].min().strftime('%Y-%m-%d'),
        'max': df['aritemdate'].max().strftime('%Y-%m-%d'),
    })


# ─── 1. SUMMARY (KPI CARDS) ──────────────────────────────────────────
@piutang_bp.route('/api/piutang/summary')
def summary():
    df_all = get_df()
    if df_all.empty:
        return jsonify({'error': 'Data piutang belum tersedia'}), 503

    area      = request.args.get('area')
    salesname = request.args.get('salesname')
    kota      = request.args.get('kota')
    date_from, date_to = get_date_params()

    df = apply_filters(unpaid(df_all), area, salesname, kota=kota, date_from=date_from, date_to=date_to)

    total_outstanding = float(df['arbalance'].sum())
    jumlah_invoice    = int(len(df))
    jumlah_customer   = int(df['custname'].nunique())
    avg_umur          = float(df['umurpiutang'].mean()) if jumlah_invoice else 0.0
    overdue_count     = int((df['umurpiutang'] > 0).sum())

    return jsonify({
        'total_outstanding': total_outstanding,
        'jumlah_invoice':    jumlah_invoice,
        'jumlah_customer':   jumlah_customer,
        'avg_umur':          round(avg_umur, 1),
        'overdue_count':     overdue_count
    })


# ─── 2. AGING BREAKDOWN ──────────────────────────────────────────────
@piutang_bp.route('/api/piutang/aging')
def aging():
    df_all = get_df()
    if df_all.empty:
        return jsonify({'error': 'Data piutang belum tersedia'}), 503

    area      = request.args.get('area')
    salesname = request.args.get('salesname')
    kota      = request.args.get('kota')
    date_from, date_to = get_date_params()

    df = apply_filters(unpaid(df_all), area, salesname, kota=kota, date_from=date_from, date_to=date_to)
    df['bucket'] = df['umurpiutang'].apply(aging_label)

    grouped = df.groupby('bucket').agg(
        total=('arbalance', 'sum'),
        count=('arbalance', 'count')
    ).reindex(AGING_ORDER, fill_value=0).reset_index()

    result = [
        {
            'bucket': row['bucket'],
            'total':  float(row['total']),
            'count':  int(row['count'])
        }
        for _, row in grouped.iterrows()
    ]
    return jsonify(result)


# ─── 3. TOP DEBTORS ───────────────────────────────────────────────────
@piutang_bp.route('/api/piutang/top-debtors')
def top_debtors():
    df_all = get_df()
    if df_all.empty:
        return jsonify([])

    area      = request.args.get('area')
    salesname = request.args.get('salesname')
    kota      = request.args.get('kota')
    limit     = int(request.args.get('limit', 10))
    date_from, date_to = get_date_params()

    df = apply_filters(unpaid(df_all), area, salesname, kota=kota, date_from=date_from, date_to=date_to)

    grouped = (
        df.groupby('custname')
        .agg(
            total_outstanding=('arbalance', 'sum'),
            jumlah_invoice=('arbalance', 'count'),
            area=('area', 'first'),
            salesname=('salesname', 'first'),
            kota=('kota', 'first')
        )
        .reset_index()
        .sort_values('total_outstanding', ascending=False)
        .head(limit)
    )

    result = [
        {
            'custname':          row['custname'],
            'total_outstanding': float(row['total_outstanding']),
            'jumlah_invoice':    int(row['jumlah_invoice']),
            'area':              row['area'],
            'salesname':         row['salesname'],
            'kota':              row['kota'] if pd.notna(row['kota']) else '—'
        }
        for _, row in grouped.iterrows()
    ]
    return jsonify(result)


# ─── 4. PER SALES ─────────────────────────────────────────────────────
@piutang_bp.route('/api/piutang/per-sales')
def per_sales():
    df_all = get_df()
    if df_all.empty:
        return jsonify([])

    area   = request.args.get('area')
    kota   = request.args.get('kota')
    bucket = request.args.get('bucket')
    date_from, date_to = get_date_params()

    df = apply_filters(unpaid(df_all), area, None, bucket, kota=kota, date_from=date_from, date_to=date_to)

    grouped = (
        df.groupby('salesname')
        .agg(
            total_outstanding=('arbalance', 'sum'),
            jumlah_invoice=('arbalance', 'count'),
            jumlah_customer=('custname', 'nunique')
        )
        .reset_index()
        .sort_values('total_outstanding', ascending=False)
    )

    result = [
        {
            'salesname':         row['salesname'],
            'total_outstanding': float(row['total_outstanding']),
            'jumlah_invoice':    int(row['jumlah_invoice']),
            'jumlah_customer':   int(row['jumlah_customer'])
        }
        for _, row in grouped.iterrows()
    ]
    return jsonify(result)


# ─── 5. DETAIL TABLE (paginated + filterable) ─────────────────────────
@piutang_bp.route('/api/piutang/detail')
def detail():
    df_all = get_df()
    if df_all.empty:
        return jsonify({'data': [], 'total': 0, 'page': 1, 'pages': 0})

    area      = request.args.get('area')
    salesname = request.args.get('salesname')
    kota      = request.args.get('kota')
    bucket    = request.args.get('bucket')
    search    = request.args.get('search', '').strip().lower()
    page      = max(1, int(request.args.get('page', 1)))
    limit     = min(100, int(request.args.get('limit', 50)))
    sort_by   = request.args.get('sort_by', 'arbalance')
    sort_asc  = request.args.get('sort_asc', 'false').lower() == 'true'
    show_paid = request.args.get('show_paid', 'false').lower() == 'true'
    date_from, date_to = get_date_params()

    df = unpaid(df_all) if not show_paid else df_all.copy()
    df = apply_filters(df, area, salesname, bucket, kota=kota, date_from=date_from, date_to=date_to)

    if search:
        df = df[df['custname'].str.lower().str.contains(search, na=False)]

    allowed_sorts = {'arbalance', 'umurpiutang', 'aritemduedate', 'aritemgrandtotal', 'aritemdate'}
    if sort_by not in allowed_sorts:
        sort_by = 'arbalance'
    df = df.sort_values(sort_by, ascending=sort_asc)

    total  = len(df)
    pages  = max(1, -(-total // limit))
    offset = (page - 1) * limit
    page_df = df.iloc[offset:offset + limit]

    def fmt_date(v):
        if pd.isna(v):
            return None
        return str(v)[:10]

    rows = [
        {
            'aritemno':         row['aritemno'],
            'custname':         row['custname'],
            'salesname':        row['salesname'],
            'area':             row['area'],
            'kota':             row['kota'] if pd.notna(row.get('kota')) else '—',
            'aritemdate':       fmt_date(row['aritemdate']),
            'aritemduedate':    fmt_date(row['aritemduedate']),
            'umurpiutang':      float(row['umurpiutang']) if pd.notna(row['umurpiutang']) else 0,
            'aritemgrandtotal': float(row['aritemgrandtotal']),
            'sumbayar':         float(row['sumbayar']) if pd.notna(row['sumbayar']) else 0,
            'arbalance':        float(row['arbalance']),
            'bucket':           aging_label(float(row['umurpiutang']) if pd.notna(row['umurpiutang']) else 0)
        }
        for _, row in page_df.iterrows()
    ]

    return jsonify({'data': rows, 'total': total, 'page': page, 'pages': pages})


# ─── 6. FILTER OPTIONS ────────────────────────────────────────────────
@piutang_bp.route('/api/piutang/filters')
def filters():
    df_all = get_df()
    if df_all.empty:
        return jsonify({'areas': [], 'salesnames': [], 'kotas': []})

    areas = sorted(df_all['area'].dropna().unique().tolist())
    sales = sorted(df_all['salesname'].dropna().unique().tolist())
    kotas = sorted([k for k in df_all['kota'].dropna().unique().tolist() if k and k != 'None'])
    return jsonify({'areas': areas, 'salesnames': sales, 'kotas': kotas})
