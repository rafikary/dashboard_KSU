# Definisi Field Data KSU

Berdasarkan klarifikasi dari Mas Zefa (12 Mei 2026)

## Struktur Data

**Sumber Query:**
```sql
SELECT 
    tglNominatif, 
    gencode Kode, 
    gendesc Nama, 
    CASE WHEN flag = 1 THEN 'A' ELSE 'B' END flag, 
    pinjaman, 
    sisaPinjaman, 
    jasaTtg1, 
    jasaTtg2, 
    jasaTtg3, 
    jasaTtgNP, 
    totalJasaTtg, 
    sisaPinjamanNP, 
    saldoKas, 
    saldoBank 
FROM QL_NominatifSum s 
INNER JOIN QL_mstgen g ON g.gencode=s.cmpcode AND g.gengroup='BRANCHCODE' 
ORDER BY tglNominatif
```

## Field Definitions

### Identifikasi Cabang
- **tglNominatif**: Tanggal snapshot data
- **kode**: Kode cabang (KSP01 - KSP62)
- **nama**: Nama cabang
- **flag**: Jenis data
  - **A** = Data Pajak
  - **B** = Data Non Pajak

### Pinjaman
- **pinjaman**: Total pinjaman yang diberikan
- **sisaPinjaman**: Sisa pinjaman yang belum terbayar

### Jasa/Bunga Tertunggak
- **jasaTtg1**: Jasa/bunga tertunggak **1 bulan**
- **jasaTtg2**: Jasa/bunga tertunggak **2 bulan**
- **jasaTtg3**: Jasa/bunga tertunggak **3 bulan**
- **jasaTtgNP**: Jasa/bunga tertunggak **Non-Performing** (menunggak >3 bulan)
- **totalJasaTtg**: Total semua jasa tertunggak (jasaTtg1 + jasaTtg2 + jasaTtg3 + jasaTtgNP)

### Non-Performing Loan (NPL)
- **sisaPinjamanNP**: Sisa pinjaman yang menunggak **lebih dari 3 bulan**
- **NPL Ratio**: Persentase pinjaman bermasalah
  ```
  NPL Ratio = (sisaPinjamanNP / sisaPinjaman) × 100%
  ```

### Likuiditas
- **saldoKas**: Saldo kas (saldo akhir)
- **saldoBank**: Saldo bank (saldo akhir)
- **Total Likuiditas**: saldoKas + saldoBank

## Metrik Kesehatan KSU

### NPL Ratio Threshold
- **< 5%**: Sehat
- **5-10%**: Perlu Perhatian
- **10-30%**: Bermasalah
- **≥ 30%**: Sangat Bermasalah

### Collection Rate
Persentase pinjaman yang sudah terkumpul:
```
Collection Rate = ((pinjaman - sisaPinjaman) / pinjaman) × 100%
```

### Tunggakan Jasa Ratio
Persentase tunggakan jasa terhadap sisa pinjaman:
```
Tunggakan Jasa Ratio = (totalJasaTtg / sisaPinjaman) × 100%
```

### NPL Amount Ratio
Persentase kredit NPL terhadap total pinjaman:
```
NPL Amount Ratio = (sisaPinjamanNP / pinjaman) × 100%
```

## Catatan Penting

1. **Saldo sudah final**: saldoKas dan saldoBank adalah saldo akhir periode
2. **NP = Non-Performing**: Pinjaman yang menunggak **lebih dari 3 bulan**
3. **Flag A/B**: Membedakan data pajak (A) dan non-pajak (B) untuk keperluan pelaporan
4. **Jasa Tertunggak Berjenjang**: jasaTtg1/2/3 menunjukkan durasi tunggakan dalam bulan

## Dataset Aktual

- **Total Rows**: 131,614 records
- **Periode Data**: Januari 2021 - Mei 2026
- **Jumlah Cabang**: 53 cabang
- **Format File**: ksu.parquet

## API Endpoints

### 1. GET /api/ksu/summary
Ringkasan agregat keseluruhan KSU
- **Response**: Total pinjaman, sisa pinjaman, NPL ratio, collection rate, dll
- **Query params**: date_from, date_to, branch_code

### 2. GET /api/ksu/branches
Daftar semua cabang dengan metrik terkini
- **Response**: Array cabang dengan semua field termasuk jasa_ttg_ratio dan npl_amount_ratio
- **Query params**: date, date_from, date_to, sort_by, order

### 3. GET /api/ksu/trend
Data trend perkembangan KSU per periode
- **Response**: Array data per periode dengan agregasi
- **Query params**: date_from, date_to, branch_code, granularity (day/week/month)

### 4. GET /api/ksu/branch/{branch_code}
Detail dan histori satu cabang
- **Response**: Data terkini dan array histori cabang
- **Query params**: date_from, date_to

### 5. GET /api/ksu/npl-ranking
Ranking cabang berdasarkan NPL ratio
- **Response**: Top N cabang dengan NPL tertinggi
- **Query params**: date, limit (default: 10)

### 6. GET /api/ksu/report/summary ⭐ NEW
Laporan summary format resmi KSU (sesuai format PDF)
- **Response**: Data terstruktur untuk laporan summary lengkap dengan breakdown tunggakan jasa
- **Query params**: date
- **Format**: Cocok untuk display, print, atau export ke Excel/PDF

## Perhitungan NPL di Dashboard

Ada 2 metode:

1. **Weighted Average** (Dashboard Info Bar): 36.34%
   - Memperhitungkan ukuran pinjaman per cabang
   - Lebih mencerminkan risiko portofolio total

2. **Simple Average** (Halaman Cabang): 48.25%
   - Rata-rata sederhana NPL semua cabang
   - Setiap cabang punya bobot sama

Kedua metrik valid untuk analisis yang berbeda.
