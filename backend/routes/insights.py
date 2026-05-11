from flask import Blueprint, current_app
import pandas as pd
import numpy as np
from datetime import timedelta

insights_bp = Blueprint('insights', __name__)


def _compact(v):
    if v is None: return 'Rp 0'
    if abs(v) >= 1e9: return f'Rp {v/1e9:.1f} M'
    if abs(v) >= 1e6: return f'Rp {v/1e6:.1f} Jt'
    return f'Rp {v:,.0f}'


@insights_bp.route('/api/insights/executive-summary')
def executive_summary():
    """
    Generate narasi otomatis berdasarkan data aktual:
    - Pertumbuhan per area (3 bulan vs 3 bulan sebelumnya)
    - Area yang perlu dikunjungi segera (declinng)
    - Status kualitas data
    - Customer terbesar bulan ini
    """
    df = current_app.config['DF_PENJUALAN'].copy()
    df['custname'] = df['custname'].str.strip()
    df['area']     = df['area'].str.strip()

    latest     = df['aritemdate'].max()
    cutoff_now = latest - timedelta(days=90)   # 3 bulan terakhir
    cutoff_prev= latest - timedelta(days=180)  # 3 bulan sebelumnya

    df_now  = df[df['aritemdate'] > cutoff_now]
    df_prev = df[(df['aritemdate'] > cutoff_prev) & (df['aritemdate'] <= cutoff_now)]

    # ── Area growth ───────────────────────────────────────────────────
    area_now  = df_now.groupby('area')['aritemdtlamt'].sum()
    area_prev = df_prev.groupby('area')['aritemdtlamt'].sum()
    area_df   = pd.DataFrame({'now': area_now, 'prev': area_prev}).fillna(0)
    area_df   = area_df[area_df['prev'] > 0]  # exclude area yang baru muncul
    area_df['growth_pct'] = ((area_df['now'] - area_df['prev']) / area_df['prev'] * 100).replace([np.inf, -np.inf], 0).round(1)

    best_area     = area_df['growth_pct'].idxmax()  if not area_df.empty else '-'
    best_pct      = float(area_df.loc[best_area, 'growth_pct']) if not area_df.empty else 0
    best_omzet    = float(area_df.loc[best_area, 'now'])        if not area_df.empty else 0

    declining = area_df[area_df['growth_pct'] < 0].sort_values('growth_pct')
    worst_area = declining.index[0]             if not declining.empty else None
    worst_pct  = float(declining['growth_pct'].iloc[0]) if not declining.empty else 0
    worst_omzet= float(declining['now'].iloc[0])         if not declining.empty else 0

    # ── Data quality ──────────────────────────────────────────────────
    total_rows = len(df)
    dup_rows   = int(df.duplicated(keep=False).sum())
    neg_rows   = int((df['aritemqty'] < 0).sum())
    dirty_rows = dup_rows + neg_rows
    dirty_pct  = round(dirty_rows / total_rows * 100, 1)
    clean_pct  = round(100 - dirty_pct, 1)

    void_by_area    = df[df['aritemqty'] < 0].groupby('area').size()
    worst_void_area = void_by_area.idxmax() if not void_by_area.empty else None

    # ── Top customer 3 bulan terakhir ─────────────────────────────────
    top_cust_s   = df_now.groupby('custname')['aritemdtlamt'].sum().nlargest(1)
    top_cust_nm  = top_cust_s.index[0]   if not top_cust_s.empty else '-'
    top_cust_val = float(top_cust_s.iloc[0]) if not top_cust_s.empty else 0

    # ── Build insight cards ───────────────────────────────────────────
    insights = []

    # Card 1 — top performing area
    if best_pct > 0:
        card1_title = f'Area {best_area} tumbuh {best_pct:.1f}% — performa terbaik'
        card1_body  = (
            f'{best_area} mencatat pertumbuhan omzet tertinggi sebesar {best_pct:.1f}% '
            f'dibanding 3 bulan sebelumnya, dengan total {_compact(best_omzet)}. '
            f'Pertahankan frekuensi kunjungan ke area ini.'
        )
    else:
        card1_title = f'Area {best_area} — performa relatif terbaik ({best_pct:.1f}%)'
        card1_body  = (
            f'Seluruh area mengalami tekanan bulan ini. {best_area} masih yang paling '
            f'stabil dengan omzet {_compact(best_omzet)}. '
            f'Evaluasi strategi kunjungan untuk memperbaiki tren keseluruhan.'
        )
        
    insights.append({
        'type':  'growth',
        'level': 'positive' if best_pct > 0 else 'warning',
        'title': card1_title,
        'body':  card1_body,
        'action': None
    })

    # Card 2 — declining area / warning
    if worst_area:
        void_count = int(void_by_area.get(worst_area, 0))
        void_note  = f' Tercatat {void_count} transaksi void di area ini.' if void_count > 0 else ''
        insights.append({
            'type':  'warning',
            'level': 'danger',
            'title': f'Area {worst_area} turun {abs(worst_pct):.1f}% — perlu kunjungan segera',
            'body':  (
                f'{worst_area} mengalami penurunan omzet sebesar {abs(worst_pct):.1f}% '
                f'dibanding periode sebelumnya.{void_note} '
                f'Segera jadwalkan kunjungan untuk re-confirm anggaran dan status SO aktif.'
            ),
            'action': f'Prioritas kunjungan: {worst_area}'
        })

    # Card 3 — data quality
    if dirty_pct > 3:
        void_area_note = f' Area {worst_void_area} adalah yang paling banyak mencatat void.' if worst_void_area else ''
        insights.append({
            'type':  'data_quality',
            'level': 'warning',
            'title': f'{dirty_pct}% data berpotensi tidak akurat',
            'body':  (
                f'Ditemukan {dup_rows:,} baris yang terdeteksi duplikat dan '
                f'{neg_rows:,} transaksi dengan qty negatif (kemungkinan retur atau void SO).'
                f'{void_area_note} '
                f'Angka omzet yang ditampilkan mungkin lebih tinggi dari aktual.'
            ),
            'action': 'Cek detail di halaman Kualitas Data'
        })
    else:
        insights.append({
            'type':  'data_quality',
            'level': 'ok',
            'title': f'Data {clean_pct}% bersih — tidak ada masalah signifikan',
            'body':  (
                f'Hanya {dirty_pct}% data yang bermasalah ({dup_rows:,} duplikat, '
                f'{neg_rows:,} negatif). Angka omzet dapat dipercaya untuk pengambilan keputusan.'
            ),
            'action': None
        })

    # Card 4 — top customer
    insights.append({
        'type':  'top_customer',
        'level': 'info',
        'title': f'{top_cust_nm} adalah customer terbesar 3 bulan ini',
        'body':  (
            f'Omzet {_compact(top_cust_val)} dalam 3 bulan terakhir. '
            f'Customer ini berkontribusi signifikan — pastikan pipeline SO aktif '
            f'dan lakukan konfirmasi anggaran sebelum pengiriman untuk mencegah pembatalan mendadak.'
        ),
        'action': None
    })

    return {
        'status':       'success',
        'generated_at': str(latest.date()),
        'period':       '3 bulan terakhir vs 3 bulan sebelumnya',
        'quick_stats': {
            'top_area':       best_area,
            'top_area_growth': best_pct,
            'alert_area':     worst_area,
            'alert_area_drop': worst_pct,
            'clean_pct':      clean_pct,
            'dirty_pct':      dirty_pct,
            'top_customer':   top_cust_nm,
            'top_customer_val': top_cust_val
        },
        'insights': insights
    }
