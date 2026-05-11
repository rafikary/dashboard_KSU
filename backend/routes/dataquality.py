from flask import Blueprint, current_app
import pandas as pd

dataquality_bp = Blueprint('dataquality', __name__)


@dataquality_bp.route('/api/data-quality/summary')
def quality_summary():
    """
    Analisis kualitas data:
    1. Baris duplikat (customer+item+tanggal+harga persis sama)
    2. Row dengan qty negatif (kemungkinan return/void)
    3. Row dengan amount = 0
    4. Row dengan harga aneh (terlalu rendah atau tinggi)
    """
    df = current_app.config['DF_PENJUALAN'].copy()
    df['custname']     = df['custname'].str.strip()
    df['itemshortdesc'] = df['itemshortdesc'].str.strip()

    total_rows = len(df)

    # ── 1. Duplikat persis (semua kolom sama) ─────────────────────────
    dup_mask       = df.duplicated(keep=False)
    dup_rows       = int(dup_mask.sum())
    dup_first_mask = df.duplicated(keep='first')
    dup_first      = int(dup_first_mask.sum())  # baris yang perlu dihapus

    # Contoh duplikat
    dup_examples = []
    if dup_rows > 0:
        dup_df = df[dup_mask].head(5)
        dup_examples = dup_df[['custname','itemshortdesc','aritemdate','aritemqty','aritemdtlamt']].to_dict('records')

    # ── 2. Qty negatif (return / void) ────────────────────────────────
    neg_mask   = df['aritemqty'] < 0
    neg_rows   = int(neg_mask.sum())
    neg_amount = float(df[neg_mask]['aritemdtlamt'].sum())

    # Contoh negatif
    neg_examples = []
    if neg_rows > 0:
        neg_df = df[neg_mask].head(5)
        neg_examples = neg_df[['custname','itemshortdesc','aritemdate','aritemqty','aritemdtlamt']].to_dict('records')

    # ── 3. Amount nol ─────────────────────────────────────────────────
    zero_mask = df['aritemdtlamt'] == 0
    zero_rows = int(zero_mask.sum())

    # ── 4. Harga per unit sangat rendah (<100 Rp) – kemungkinan kotor ─
    df_safe   = df[df['aritemqty'] != 0].copy()
    df_safe['unit_price'] = df_safe['aritemdtlamt'] / df_safe['aritemqty']
    suspect_mask  = df_safe['unit_price'].abs() < 100
    suspect_rows  = int(suspect_mask.sum())

    # ── Dampak finansial jika duplikat semua dihapus ──────────────────
    dup_omzet_risk = float(df[dup_first_mask]['aritemdtlamt'].sum())
    neg_omzet_adj  = abs(neg_amount)

    # ── Bersih setelah filter ─────────────────────────────────────────
    clean_df       = df[~dup_first_mask & ~neg_mask & ~zero_mask]
    clean_rows     = len(clean_df)
    clean_omzet    = float(clean_df['aritemdtlamt'].sum())
    dirty_omzet    = float(df['aritemdtlamt'].sum())

    return {
        'status': 'success',
        'summary': {
            'total_rows': total_rows,
            'clean_rows': clean_rows,
            'dirty_rows': total_rows - clean_rows,
            'dirty_pct':  round((total_rows - clean_rows) / total_rows * 100, 2)
        },
        'issues': {
            'duplicates': {
                'count':       dup_rows,
                'removable':   dup_first,
                'omzet_risk':  dup_omzet_risk,
                'examples':    dup_examples
            },
            'negative_qty': {
                'count':          neg_rows,
                'total_amount':   neg_amount,
                'adjustment':     neg_omzet_adj,
                'examples':       neg_examples
            },
            'zero_amount': {
                'count': zero_rows
            },
            'suspect_price': {
                'count': suspect_rows
            }
        },
        'financial_impact': {
            'raw_omzet':         dirty_omzet,
            'clean_omzet':       clean_omzet,
            'over_count_amount': dirty_omzet - clean_omzet,
            'over_count_pct':    round((dirty_omzet - clean_omzet) / dirty_omzet * 100, 2) if dirty_omzet > 0 else 0
        }
    }


@dataquality_bp.route('/api/data-quality/duplicates')
def list_duplicates():
    """Return semua baris yang ter-duplikat (max 200 baris)"""
    df = current_app.config['DF_PENJUALAN'].copy()
    df['custname'] = df['custname'].str.strip()
    dup_df = df[df.duplicated(keep=False)].sort_values(['custname','aritemdate','itemshortdesc'])
    dup_df['aritemdate'] = dup_df['aritemdate'].astype(str)
    result = dup_df.head(200)[['area','custname','aritemdate','itemshortdesc','aritemqty','aritemprice','aritemdtlamt']].to_dict('records')
    return {
        'status': 'success',
        'total_duplicate_rows': int(df.duplicated(keep=False).sum()),
        'showing': len(result),
        'data': result
    }


@dataquality_bp.route('/api/data-quality/reliability-scores')
def reliability_scores():
    """
    Hitung Customer Reliability Score berdasarkan sejarah void & duplikat.
    Badge:
      - high_maintenance : void > 20% atau issue > 30%  → "High Maintenance"
      - confirm_payment  : void > 5%  atau issue > 10%  → "Konfirmasi H-2"
      - reliable         : selain itu
    """
    df = current_app.config['DF_PENJUALAN'].copy()
    df['custname'] = df['custname'].str.strip()

    cust_total = df.groupby('custname').size().rename('total_rows')
    cust_void  = df[df['aritemqty'] < 0].groupby('custname').size().rename('void_rows')
    cust_dup   = df[df.duplicated(keep=False)].groupby('custname').size().rename('dup_rows')

    scores = pd.concat([cust_total, cust_void, cust_dup], axis=1).fillna(0)
    scores['void_rate']  = (scores['void_rows'] / scores['total_rows'] * 100).round(1)
    scores['dup_rate']   = (scores['dup_rows']  / scores['total_rows'] * 100).round(1)
    scores['issue_rate'] = ((scores['void_rows'] + scores['dup_rows']) / scores['total_rows'] * 100).round(1)

    def classify(row):
        if row['void_rate'] > 20 or row['issue_rate'] > 30:
            return 'high_maintenance'
        elif row['void_rate'] > 5 or row['issue_rate'] > 10:
            return 'confirm_payment'
        return 'reliable'

    scores['badge'] = scores.apply(classify, axis=1)

    # Return semua customer dengan metadata badge (termasuk reliable)
    all_result = scores.reset_index().rename(columns={'custname': 'customer'})
    all_result = all_result[['customer', 'total_rows', 'void_rows', 'dup_rows',
                              'void_rate', 'dup_rate', 'issue_rate', 'badge']]
    all_result = all_result.sort_values('issue_rate', ascending=False)

    at_risk = all_result[all_result['badge'] != 'reliable']

    return {
        'status': 'success',
        'total_customers':   int(scores.shape[0]),
        'high_maintenance':  int((scores['badge'] == 'high_maintenance').sum()),
        'confirm_payment':   int((scores['badge'] == 'confirm_payment').sum()),
        'reliable':          int((scores['badge'] == 'reliable').sum()),
        'at_risk_data':      at_risk.to_dict('records'),
        'all_scores':        all_result.head(500).to_dict('records')
    }


@dataquality_bp.route('/api/data-quality/negatives')
def list_negatives():
    """Return semua baris qty negatif (return/void)"""
    df = current_app.config['DF_PENJUALAN'].copy()
    df['custname'] = df['custname'].str.strip()
    neg_df = df[df['aritemqty'] < 0].sort_values('aritemdate', ascending=False)
    neg_df['aritemdate'] = neg_df['aritemdate'].astype(str)
    result = neg_df.head(200)[['area','custname','aritemdate','itemshortdesc','aritemqty','aritemprice','aritemdtlamt']].to_dict('records')
    return {
        'status': 'success',
        'total_negative_rows': int((df['aritemqty'] < 0).sum()),
        'total_void_amount': float(df[df['aritemqty'] < 0]['aritemdtlamt'].sum()),
        'showing': len(result),
        'data': result
    }
