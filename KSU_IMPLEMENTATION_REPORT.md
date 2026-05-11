# KSU Dashboard - Analysis & Implementation Report

## Data Analysis

### Parquet Data Structure (ksu.parquet)
File data yang ada berisi **131,614 baris** data nominatif KSU dari **2021-01-01 sampai 2026-05-01** dengan kolom-kolom berikut:

**Kolom Data:**
1. `tglnominatif` - Tanggal nominatif
2. `kode` - Kode cabang KSU
3. `nama` - Nama cabang
4. `flag` - Flag (A/B)
5. `pinjaman` - Total pinjaman
6. `sisapinjaman` - Sisa pinjaman (outstanding)
7. `jasattg1`, `jasattg2`, `jasattg3` - Jasa tertunggak periode 1, 2, 3
8. `jasattgnp` - Jasa tertunggak non-performing
9. `totaljasattg` - Total jasa tertunggak
10. `sisapinjamannp` - Sisa pinjaman non-performing (NPL)
11. `saldokas` - Saldo kas
12. `saldobank` - Saldo bank
13. `uid` - Unique ID (kombinasi tanggal + kode)

## Changes Implemented

### 1. Backend Changes

#### **New Route: `/backend/routes/ksu.py`** ✅
API endpoints untuk data KSU:
- `GET /api/ksu/summary` - Overview summary (total pinjaman, NPL ratio, collection rate, dll)
- `GET /api/ksu/branches` - List semua cabang dengan metrik lengkap
- `GET /api/ksu/trend` - Trend data over time (day/week/month)
- `GET /api/ksu/branch/<code>` - Detail spesifik cabang
- `GET /api/ksu/npl-ranking` - Ranking cabang berdasarkan NPL ratio
- `GET /api/ksu/comparison` - Perbandingan antar cabang

#### **Updated: `/backend/app.py`** ✅
- Load data dari `ksu.parquet` instead of `penjualan.parquet`
- Register blueprint KSU
- Disable routes yang tidak relevan:
  - ❌ `trend_bp` (penjualan)
  - ❌ `items_bp` (produk penjualan)
  - ❌ `customers_bp` (customer penjualan)
  - ❌ `geography` (geografis penjualan)
  - ❌ `category` (kategori produk)
  - ❌ `marketing_bp` (marketing/sales person)
  - ❌ `insights_bp` (insights penjualan)
  - ❌ `chatbot_bp` (chatbot AI)
  - ❌ `aireport_bp` (AI reports)
  - ❌ `piutang_bp` (piutang penjualan)
- Update metadata endpoint untuk data KSU
- Remove AI chatbot logs endpoints

### 2. Frontend Changes

#### **Updated: `/frontend/src/pages/DashboardPage.vue`** ✅
Dashboard utama sekarang menampilkan:
- **4 KPI Cards:**
  1. Total Pinjaman
  2. Sisa Pinjaman (dengan Collection Rate)
  3. Jasa Tertunggak (dengan NPL)
  4. Total Likuiditas (Kas + Bank)
- **Welcome Banner** dengan info:
  - Total Cabang
  - NPL Ratio keseluruhan
  - Collection Rate keseluruhan
- **Fitur Dashboard:**
  - Data Cabang
  - Analisis NPL
  - Trend Pinjaman

#### **New Page: `/frontend/src/pages/BranchesPage.vue`** ✅
Halaman baru untuk analisis cabang:
- **Filters:**
  - Date picker untuk pilih tanggal
  - Sort by (Sisa Pinjaman, NPL Ratio, Collection Rate, dll)
  - Sort order (ascending/descending)
- **Summary Cards:**
  - Total Cabang
  - Total Pinjaman
  - Average NPL Ratio
  - Average Collection Rate
- **Data Table** dengan kolom:
  - Kode & Nama Cabang
  - Sisa Pinjaman
  - NPL Ratio (dengan color coding)
  - Jasa Tertunggak
  - Collection Rate
  - Total Likuiditas
  - Action button untuk detail
- **Detail Modal** menampilkan semua metrik cabang lengkap
- **Color-coded rows:**
  - 🔴 Red highlight: NPL > 10%
  - 🟠 Orange highlight: NPL 5-10%
  - ✅ Normal: NPL < 5%

#### **Updated: `/frontend/src/router/index.ts`** ✅
- Tambah route baru: `/branches` → BranchesPage
- Disable routes lama yang tidak relevan

#### **Updated: `/frontend/src/layouts/MainLayout.vue`** ✅
- Update judul: "KSU Dashboard" (Koperasi Simpan Pinjam)
- Update menu items:
  - ✅ Dashboard
  - ✅ Data Cabang
  - ❌ Removed: Analisa Penjualan, Customer, Kategori, Geografis, Marketing, dll
- Update page titles & descriptions untuk KSU context

### 3. Removed/Disabled Files

#### Backend Routes (Not deleted, just disabled):
- `trend.py`, `items.py`, `customers.py`, `geography.py`
- `category.py`, `marketing.py`, `insights.py`
- `chatbot.py`, `aireport.py`, `piutang.py`

#### Frontend Pages (Not deleted, just not accessible):
- `CustomersPage.vue`
- `SalesComparisonPage.vue`

## Key Metrics & Analysis

### 1. NPL (Non-Performing Loan) Analysis
- **NPL Ratio** = (Sisa Pinjaman NP / Sisa Pinjaman Total) × 100%
- **Health Indicator:**
  - ✅ Good: NPL < 5%
  - ⚠️ Warning: NPL 5-10%
  - 🔴 Critical: NPL > 10%

### 2. Collection Rate
- **Formula** = ((Total Pinjaman - Sisa Pinjaman) / Total Pinjaman) × 100%
- Higher = Better (menunjukkan efektivitas collection)

### 3. Liquidity
- **Total Liquidity** = Saldo Kas + Saldo Bank
- Indikator kesehatan kas flow cabang

### 4. Jasa Tertunggak
- Breakdown by period: TTG1, TTG2, TTG3, NP
- Total jasa yang belum dibayar

## API Examples

### Get Summary
```bash
GET http://localhost:5000/api/ksu/summary
```

### Get Branches List
```bash
GET http://localhost:5000/api/ksu/branches?sort_by=npl_ratio&order=desc
```

### Get Branch Detail
```bash
GET http://localhost:5000/api/ksu/branch/KSP13
```

### Get Trend
```bash
GET http://localhost:5000/api/ksu/trend?granularity=month&date_from=2025-01-01
```

### Get NPL Ranking
```bash
GET http://localhost:5000/api/ksu/npl-ranking?limit=10
```

## How to Run

### Backend
```bash
cd backend
python app.py
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Data Sync
```bash
cd backend
python sync_data.py
```

## Future Enhancements

1. **Trend Charts** - Visualisasi grafik trend NPL dan collection rate over time
2. **Export to Excel** - Export data cabang ke Excel
3. **Email Alerts** - Alert otomatis untuk cabang dengan NPL tinggi
4. **Forecasting** - Prediksi NPL menggunakan ML
5. **Comparison View** - Bandingkan performa antar cabang side-by-side
6. **Historical Analysis** - Analisis perubahan metrik cabang dari waktu ke waktu

## Notes

- ✅ Data loaded: 131,614 rows
- ✅ Date range: 2021-01-01 to 2026-05-01
- ✅ Backend API tested: Working
- ✅ Frontend UI: KSU-themed
- ✅ Old sales routes: Disabled but not deleted
- ⚠️ Chatbot AI: Disabled (not implemented for KSU yet)
