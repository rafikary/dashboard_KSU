from flask import Blueprint, request, current_app, jsonify
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

ksu_bp = Blueprint('ksu', __name__)


def get_ksu_df():
    """Get KSU dataframe from RAM"""
    df = current_app.config.get('DF_KSU')
    if df is None or df.empty:
        return pd.DataFrame()
    return df.copy()


@ksu_bp.route('/api/ksu/summary')
def ksu_summary():
    """
    Get overall KSU summary statistics
    Query params:
    - date_from: start date (YYYY-MM-DD)
    - date_to: end date (YYYY-MM-DD)
    - branch_code: filter by specific branch
    """
    df = get_ksu_df()
    
    if df.empty:
        return jsonify({'error': 'No data available'}), 404
    
    # Apply filters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    branch_code = request.args.get('branch_code')
    
    if date_from:
        df = df[df['tglnominatif'] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df['tglnominatif'] <= pd.to_datetime(date_to)]
    if branch_code:
        df = df[df['kode'].str.upper() == branch_code.upper()]
    
    # Get latest data for each branch
    latest_df = df.sort_values('tglnominatif').groupby('kode').last().reset_index()
    
    # Calculate summary
    total_pinjaman = latest_df['pinjaman'].sum()
    total_sisa_pinjaman = latest_df['sisapinjaman'].sum()
    total_jasa_ttg = latest_df['totaljasattg'].sum()
    total_jasa_ttg_1 = latest_df['jasattg1'].sum()
    total_jasa_ttg_2 = latest_df['jasattg2'].sum()
    total_jasa_ttg_3 = latest_df['jasattg3'].sum()
    total_jasa_ttg_np = latest_df['jasattgnp'].sum()
    total_sisa_pinjaman_np = latest_df['sisapinjamannp'].sum()
    
    summary = {
        'total_pinjaman': float(total_pinjaman),
        'total_sisa_pinjaman': float(total_sisa_pinjaman),
        'total_jasa_tertunggak': float(total_jasa_ttg),
        'total_jasa_ttg_1': float(total_jasa_ttg_1),
        'total_jasa_ttg_2': float(total_jasa_ttg_2),
        'total_jasa_ttg_3': float(total_jasa_ttg_3),
        'total_jasa_ttg_np': float(total_jasa_ttg_np),
        'jasa_ttg_ratio': float((total_jasa_ttg / total_sisa_pinjaman * 100) if total_sisa_pinjaman > 0 else 0),
        'total_sisa_pinjaman_np': float(total_sisa_pinjaman_np),
        'npl_ratio': float((total_sisa_pinjaman_np / total_sisa_pinjaman * 100) if total_sisa_pinjaman > 0 else 0),
        'npl_amount_ratio': float((total_sisa_pinjaman_np / total_pinjaman * 100) if total_pinjaman > 0 else 0),
        'total_saldo_kas': float(latest_df['saldokas'].sum()),
        'total_saldo_bank': float(latest_df['saldobank'].sum()),
        'jumlah_cabang': int(latest_df['kode'].nunique()),
        'collection_rate': float(((total_pinjaman - total_sisa_pinjaman) / total_pinjaman * 100) if total_pinjaman > 0 else 0),
        'latest_date': df['tglnominatif'].max().strftime('%Y-%m-%d') if not df.empty else None
    }
    
    return jsonify(summary)


@ksu_bp.route('/api/ksu/branches')
def list_branches():
    """
    Get list of branches with their latest statistics
    Query params:
    - date: specific date (YYYY-MM-DD), default to latest
    - date_from: start date (YYYY-MM-DD)
    - date_to: end date (YYYY-MM-DD)
    - sort_by: field to sort by (default: sisapinjaman)
    - order: asc or desc (default: desc)
    """
    df = get_ksu_df()
    
    if df.empty:
        return jsonify({'branches': [], 'total': 0}), 200
    
    # Backward-compatible snapshot parameter
    date_param = request.args.get('date')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if date_from:
        df = df[df['tglnominatif'] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df['tglnominatif'] <= pd.to_datetime(date_to)]

    if df.empty:
        return jsonify({'branches': [], 'total': 0}), 200

    if date_param:
        target_date = pd.to_datetime(date_param)
        # Get closest date per branch
        df_filtered = df[df['tglnominatif'] <= target_date]
        if df_filtered.empty:
            return jsonify({'branches': [], 'total': 0}), 200
        df_latest = df_filtered.sort_values('tglnominatif').groupby('kode').last().reset_index()
    else:
        # Get latest data for each branch
        df_latest = df.sort_values('tglnominatif').groupby('kode').last().reset_index()
    
    # Calculate additional metrics
    df_latest['npl_ratio'] = (df_latest['sisapinjamannp'] / df_latest['sisapinjaman'] * 100).fillna(0)
    df_latest['npl_amount_ratio'] = (df_latest['sisapinjamannp'] / df_latest['pinjaman'] * 100).fillna(0)
    df_latest['collection_rate'] = ((df_latest['pinjaman'] - df_latest['sisapinjaman']) / df_latest['pinjaman'] * 100).fillna(0)
    df_latest['total_liquidity'] = df_latest['saldokas'] + df_latest['saldobank']
    df_latest['jasa_ttg_ratio'] = (df_latest['totaljasattg'] / df_latest['sisapinjaman'] * 100).fillna(0)
    
    # Sort
    sort_by = request.args.get('sort_by', 'sisapinjaman')
    order = request.args.get('order', 'desc')
    ascending = order == 'asc'

    sort_alias = {
        'sisa_pinjaman': 'sisapinjaman',
        'total_jasa_ttg': 'totaljasattg',
        'sisa_pinjaman_np': 'sisapinjamannp',
        'saldo_kas': 'saldokas',
        'saldo_bank': 'saldobank',
    }
    sort_by = sort_alias.get(sort_by, sort_by)
    
    if sort_by in df_latest.columns:
        df_latest = df_latest.sort_values(sort_by, ascending=ascending)
    
    # Convert to list
    branches = []
    for _, row in df_latest.iterrows():
        branches.append({
            'kode': row['kode'],
            'nama': row['nama'],
            'flag': row['flag'],
            'pinjaman': float(row['pinjaman']),
            'sisa_pinjaman': float(row['sisapinjaman']),
            'jasa_ttg_1': float(row['jasattg1']),
            'jasa_ttg_2': float(row['jasattg2']),
            'jasa_ttg_3': float(row['jasattg3']),
            'jasa_ttg_np': float(row['jasattgnp']),
            'total_jasa_ttg': float(row['totaljasattg']),
            'jasa_ttg_ratio': float(row['jasa_ttg_ratio']),
            'sisa_pinjaman_np': float(row['sisapinjamannp']),
            'npl_ratio': float(row['npl_ratio']),
            'npl_amount_ratio': float(row['npl_amount_ratio']),
            'saldo_kas': float(row['saldokas']),
            'saldo_bank': float(row['saldobank']),
            'collection_rate': float(row['collection_rate']),
            'total_liquidity': float(row['total_liquidity']),
            'tanggal': row['tglnominatif'].strftime('%Y-%m-%d')
        })
    
    return jsonify({
        'branches': branches,
        'total': len(branches)
    })


@ksu_bp.route('/api/ksu/trend')
def ksu_trend():
    """
    Get trend data over time
    Query params:
    - date_from: start date (YYYY-MM-DD)
    - date_to: end date (YYYY-MM-DD)
    - branch_code: filter by specific branch
    - granularity: day, week, month (default: month)
    - metrics: comma-separated metrics (default: all)
    """
    df = get_ksu_df()
    
    if df.empty:
        return jsonify({'error': 'No data available'}), 404
    
    # Apply filters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    branch_code = request.args.get('branch_code')
    granularity = request.args.get('granularity', 'month')
    
    if date_from:
        df = df[df['tglnominatif'] >= pd.to_datetime(date_from)]
    if date_to:
        df = df[df['tglnominatif'] <= pd.to_datetime(date_to)]
    if branch_code:
        df = df[df['kode'].str.upper() == branch_code.upper()]
    
    # Group by time period
    if granularity == 'day':
        df['period'] = df['tglnominatif'].dt.date
    elif granularity == 'week':
        df['period'] = df['tglnominatif'].dt.to_period('W').dt.start_time
    else:  # month
        df['period'] = df['tglnominatif'].dt.to_period('M').dt.start_time
    
    # Aggregate by period
    trend_df = df.groupby('period').agg({
        'pinjaman': 'sum',
        'sisapinjaman': 'sum',
        'totaljasattg': 'sum',
        'sisapinjamannp': 'sum',
        'saldokas': 'sum',
        'saldobank': 'sum'
    }).reset_index()
    
    # Calculate ratios
    trend_df['npl_ratio'] = (trend_df['sisapinjamannp'] / trend_df['sisapinjaman'] * 100).fillna(0)
    trend_df['collection_rate'] = ((trend_df['pinjaman'] - trend_df['sisapinjaman']) / trend_df['pinjaman'] * 100).fillna(0)
    
    # Convert to list
    trend_data = []
    for _, row in trend_df.iterrows():
        trend_data.append({
            'period': row['period'].strftime('%Y-%m-%d'),
            'pinjaman': float(row['pinjaman']),
            'sisa_pinjaman': float(row['sisapinjaman']),
            'total_jasa_ttg': float(row['totaljasattg']),
            'sisa_pinjaman_np': float(row['sisapinjamannp']),
            'saldo_kas': float(row['saldokas']),
            'saldo_bank': float(row['saldobank']),
            'npl_ratio': float(row['npl_ratio']),
            'collection_rate': float(row['collection_rate'])
        })
    
    return jsonify({
        'data': trend_data,
        'granularity': granularity,
        'total_points': len(trend_data)
    })


@ksu_bp.route('/api/ksu/branch/<branch_code>')
def branch_detail(branch_code):
    """
    Get detailed information for a specific branch
    Query params:
    - date_from: start date (YYYY-MM-DD)
    - date_to: end date (YYYY-MM-DD)
    """
    df = get_ksu_df()
    
    if df.empty:
        return jsonify({'error': 'No data available'}), 404
    
    # Filter by branch
    df_branch = df[df['kode'].str.upper() == branch_code.upper()]
    
    if df_branch.empty:
        return jsonify({'error': f'Branch {branch_code} not found'}), 404
    
    # Apply date filters
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    
    if date_from:
        df_branch = df_branch[df_branch['tglnominatif'] >= pd.to_datetime(date_from)]
    if date_to:
        df_branch = df_branch[df_branch['tglnominatif'] <= pd.to_datetime(date_to)]
    
    # Get latest data
    latest = df_branch.sort_values('tglnominatif').iloc[-1]
    
    # Get historical trend
    history = []
    for _, row in df_branch.sort_values('tglnominatif').iterrows():
        history.append({
            'tanggal': row['tglnominatif'].strftime('%Y-%m-%d'),
            'pinjaman': float(row['pinjaman']),
            'sisa_pinjaman': float(row['sisapinjaman']),
            'total_jasa_ttg': float(row['totaljasattg']),
            'saldo_kas': float(row['saldokas']),
            'saldo_bank': float(row['saldobank'])
        })
    
    # Calculate statistics
    npl_ratio = (latest['sisapinjamannp'] / latest['sisapinjaman'] * 100) if latest['sisapinjaman'] > 0 else 0
    collection_rate = ((latest['pinjaman'] - latest['sisapinjaman']) / latest['pinjaman'] * 100) if latest['pinjaman'] > 0 else 0
    
    detail = {
        'kode': latest['kode'],
        'nama': latest['nama'],
        'flag': latest['flag'],
        'latest_data': {
            'tanggal': latest['tglnominatif'].strftime('%Y-%m-%d'),
            'pinjaman': float(latest['pinjaman']),
            'sisa_pinjaman': float(latest['sisapinjaman']),
            'jasa_ttg_1': float(latest['jasattg1']),
            'jasa_ttg_2': float(latest['jasattg2']),
            'jasa_ttg_3': float(latest['jasattg3']),
            'jasa_ttg_np': float(latest['jasattgnp']),
            'total_jasa_ttg': float(latest['totaljasattg']),
            'sisa_pinjaman_np': float(latest['sisapinjamannp']),
            'saldo_kas': float(latest['saldokas']),
            'saldo_bank': float(latest['saldobank']),
            'npl_ratio': float(npl_ratio),
            'collection_rate': float(collection_rate)
        },
        'history': history,
        'statistics': {
            'avg_pinjaman': float(df_branch['pinjaman'].mean()),
            'max_pinjaman': float(df_branch['pinjaman'].max()),
            'min_pinjaman': float(df_branch['pinjaman'].min()),
            'avg_npl_ratio': float((df_branch['sisapinjamannp'] / df_branch['sisapinjaman'] * 100).mean()),
            'data_points': len(df_branch)
        }
    }
    
    return jsonify(detail)


@ksu_bp.route('/api/ksu/npl-ranking')
def npl_ranking():
    """
    Get branches ranked by NPL (Non-Performing Loan) ratio
    Query params:
    - date: specific date (YYYY-MM-DD), default to latest
    - limit: number of results (default: 10)
    """
    df = get_ksu_df()
    
    if df.empty:
        return jsonify({'ranking': [], 'total': 0}), 200
    
    # Get date parameter
    date_param = request.args.get('date')
    limit = int(request.args.get('limit', 10))
    
    if date_param:
        target_date = pd.to_datetime(date_param)
        df_filtered = df[df['tglnominatif'] <= target_date]
        if df_filtered.empty:
            return jsonify({'ranking': [], 'total': 0}), 200
        df_latest = df_filtered.sort_values('tglnominatif').groupby('kode').last().reset_index()
    else:
        df_latest = df.sort_values('tglnominatif').groupby('kode').last().reset_index()
    
    # Calculate NPL ratio
    df_latest['npl_ratio'] = (df_latest['sisapinjamannp'] / df_latest['sisapinjaman'] * 100).fillna(0)
    
    # Sort and limit
    df_ranked = df_latest.sort_values('npl_ratio', ascending=False).head(limit)
    
    ranking = []
    for idx, (_, row) in enumerate(df_ranked.iterrows(), 1):
        ranking.append({
            'rank': idx,
            'kode': row['kode'],
            'nama': row['nama'],
            'npl_ratio': float(row['npl_ratio']),
            'sisa_pinjaman_np': float(row['sisapinjamannp']),
            'sisa_pinjaman': float(row['sisapinjaman']),
            'total_jasa_ttg': float(row['totaljasattg'])
        })
    
    return jsonify({
        'ranking': ranking,
        'total': len(ranking),
        'date': df_latest['tglnominatif'].max().strftime('%Y-%m-%d')
    })


@ksu_bp.route('/api/ksu/report/summary')
def summary_report():
    """
    Generate summary report in official format (matching LAPORAN SUMMARY KOPERASI)
    Query params:
    - date: specific date (YYYY-MM-DD), default to latest
    
    Returns data matching the official report structure with tunggakan jasa breakdown
    """
    df = get_ksu_df()
    
    if df.empty:
        return jsonify({'error': 'No data available'}), 404
    
    # Get date parameter
    date_param = request.args.get('date')
    if date_param:
        target_date = pd.to_datetime(date_param)
        df_filtered = df[df['tglnominatif'] <= target_date]
        if df_filtered.empty:
            return jsonify({'error': 'No data available for specified date'}), 404
        df_latest = df_filtered.sort_values('tglnominatif').groupby('kode').last().reset_index()
        report_date = target_date.strftime('%d %B %Y')
    else:
        df_latest = df.sort_values('tglnominatif').groupby('kode').last().reset_index()
        report_date = df['tglnominatif'].max().strftime('%d %B %Y')
    
    # Calculate all metrics
    df_latest['tunggakan_jasa_pct'] = (df_latest['totaljasattg'] / df_latest['sisapinjaman'] * 100).fillna(0)
    df_latest['kredit_npl_pct'] = (df_latest['sisapinjamannp'] / df_latest['sisapinjaman'] * 100).fillna(0)
    
    # Sort by nama for consistent ordering
    df_latest = df_latest.sort_values('nama')
    
    # Build report data
    report_data = []
    for idx, (_, row) in enumerate(df_latest.iterrows(), 1):
        report_data.append({
            'no': idx,
            'nama_koperasi': row['nama'],
            'kode': row['kode'],
            'flag': row['flag'],
            'kredit': float(row['sisapinjaman']),
            'tunggakan_jasa': {
                '1_bulan': float(row['jasattg1']),
                '2_bulan': float(row['jasattg2']),
                '3_bulan': float(row['jasattg3']),
                'npl': float(row['jasattgnp']),
                'total': float(row['totaljasattg']),
                'persen': float(row['tunggakan_jasa_pct'])
            },
            'kredit_npl': {
                'amount': float(row['sisapinjamannp']),
                'persen': float(row['kredit_npl_pct'])
            },
            'saldo_kas': float(row['saldokas']),
            'saldo_bank': float(row['saldobank'])
        })
    
    # Calculate totals
    totals = {
        'kredit': float(df_latest['sisapinjaman'].sum()),
        'tunggakan_jasa': {
            '1_bulan': float(df_latest['jasattg1'].sum()),
            '2_bulan': float(df_latest['jasattg2'].sum()),
            '3_bulan': float(df_latest['jasattg3'].sum()),
            'npl': float(df_latest['jasattgnp'].sum()),
            'total': float(df_latest['totaljasattg'].sum()),
            'persen': float((df_latest['totaljasattg'].sum() / df_latest['sisapinjaman'].sum() * 100) if df_latest['sisapinjaman'].sum() > 0 else 0)
        },
        'kredit_npl': {
            'amount': float(df_latest['sisapinjamannp'].sum()),
            'persen': float((df_latest['sisapinjamannp'].sum() / df_latest['sisapinjaman'].sum() * 100) if df_latest['sisapinjaman'].sum() > 0 else 0)
        },
        'saldo_kas': float(df_latest['saldokas'].sum()),
        'saldo_bank': float(df_latest['saldobank'].sum())
    }
    
    return jsonify({
        'report_title': 'LAPORAN SUMMARY KOPERASI',
        'report_date': report_date,
        'data': report_data,
        'totals': totals,
        'jumlah_koperasi': len(df_latest)
    })


@ksu_bp.route('/api/ksu/comparison')
def branch_comparison():
    """
    Compare multiple branches
    Query params:
    - branches: comma-separated branch codes
    - date: specific date (YYYY-MM-DD), default to latest
    """
    df = get_ksu_df()
    
    if df.empty:
        return jsonify({'error': 'No data available'}), 404
    
    branches_param = request.args.get('branches', '')
    if not branches_param:
        return jsonify({'error': 'No branches specified'}), 400
    
    branch_codes = [b.strip().upper() for b in branches_param.split(',')]
    
    # Get date parameter
    date_param = request.args.get('date')
    if date_param:
        target_date = pd.to_datetime(date_param)
        df_filtered = df[df['tglnominatif'] <= target_date]
        if df_filtered.empty:
            return jsonify({'comparison': [], 'total': 0}), 200
        df_latest = df_filtered.sort_values('tglnominatif').groupby('kode').last().reset_index()
    else:
        df_latest = df.sort_values('tglnominatif').groupby('kode').last().reset_index()
    
    # Filter by specified branches
    df_comparison = df_latest[df_latest['kode'].str.upper().isin(branch_codes)]
    
    if df_comparison.empty:
        return jsonify({'error': 'No data found for specified branches'}), 404
    
    # Calculate metrics
    df_comparison['npl_ratio'] = (df_comparison['sisapinjamannp'] / df_comparison['sisapinjaman'] * 100).fillna(0)
    df_comparison['collection_rate'] = ((df_comparison['pinjaman'] - df_comparison['sisapinjaman']) / df_comparison['pinjaman'] * 100).fillna(0)
    
    comparison = []
    for _, row in df_comparison.iterrows():
        comparison.append({
            'kode': row['kode'],
            'nama': row['nama'],
            'pinjaman': float(row['pinjaman']),
            'sisa_pinjaman': float(row['sisapinjaman']),
            'total_jasa_ttg': float(row['totaljasattg']),
            'sisa_pinjaman_np': float(row['sisapinjamannp']),
            'saldo_kas': float(row['saldokas']),
            'saldo_bank': float(row['saldobank']),
            'npl_ratio': float(row['npl_ratio']),
            'collection_rate': float(row['collection_rate'])
        })
    
    return jsonify({
        'comparison': comparison,
        'total': len(comparison),
        'date': df_comparison['tglnominatif'].max().strftime('%Y-%m-%d')
    })
