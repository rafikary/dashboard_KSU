# 🚀 Quick Start Guide

Panduan cepat untuk memulai development frontend dashboard.

## 📋 Prerequisites

Pastikan Anda sudah menginstall:
- Node.js 18+ ([Download](https://nodejs.org/))
- npm (biasanya sudah include dengan Node.js)
- Backend API sudah running di `http://localhost:5000`

## ⚡ Quick Start

### 1. Install Dependencies

```bash
cd frontend
npm install
```

**Estimasi waktu:** 2-3 menit (tergantung koneksi internet)

### 2. Start Development Server

```bash
npm run dev
```

Server akan berjalan di **http://localhost:3000**

### 3. Buka di Browser

Navigasi ke http://localhost:3000 dan Anda akan melihat dashboard!

## 🎯 Fitur yang Sudah Tersedia

### ✅ Interactive Data Table
**Halaman:** `/customers`

Fitur:
- Pagination & sorting otomatis
- Search real-time
- Column visibility toggle
- Export ke Excel/CSV
- Row selection
- Custom actions per row

**Cara pakai:**
```tsx
import { DataTable } from '@/components/DataTable';

<DataTable
  data={yourData}
  columns={columns}
  actions={actions}
  pagination
  searchable
  exportable
/>
```

### ✅ Comparison Mode Visualizations
**Halaman:** `/comparison`

Fitur:
- Period comparison (bulan, quarter, tahun)
- KPI metrics dengan trend indicators
- Multiple chart types (line, bar)
- Side-by-side comparison
- Variance analysis (aktual vs target)

**Cara pakai:**
```tsx
import { 
  ComparisonMetrics, 
  ComparisonChart 
} from '@/components/ComparisonMode';

<ComparisonMetrics metrics={metrics} />
<ComparisonChart 
  title="Trend Omzet"
  periods={periods}
  data={data}
  chartType="line"
/>
```

## 📁 File Structure

```
src/
├── components/          # Reusable components
│   ├── DataTable/      # ✅ Interactive table
│   ├── ComparisonMode/ # ✅ Comparison charts
│   ├── KPICard/        # ✅ KPI metric cards
│   ├── Layout/         # ✅ App layout & navigation
│   └── ConfirmDialog/  # ✅ Confirmation dialog
├── pages/              # Page components
│   ├── CustomersPage.tsx       # ✅ Demo DataTable
│   └── SalesComparisonPage.tsx # ✅ Demo Comparison
├── lib/                # API & configs
│   ├── axios.ts        # ✅ HTTP client setup
│   └── api.ts          # ✅ API endpoints
├── types/              # TypeScript types
├── utils/              # Helper functions
└── App.tsx             # Main app
```

## 🎨 Customize

### Menambah Halaman Baru

1. **Buat file page baru** di `src/pages/`:
```tsx
// src/pages/MyNewPage.tsx
import React from 'react';
import { Container, Typography } from '@mui/material';

const MyNewPage = () => {
  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Typography variant="h4">My New Page</Typography>
    </Container>
  );
};

export default MyNewPage;
```

2. **Tambahkan route** di `src/App.tsx`:
```tsx
import MyNewPage from './pages/MyNewPage';

// Di dalam <Routes>
<Route path="mynewpage" element={<MyNewPage />} />
```

3. **Tambahkan menu** di `src/components/Layout/Layout.tsx`:
```tsx
const navigationItems = [
  // ... existing items
  { 
    title: 'My New Page', 
    path: '/mynewpage', 
    icon: <YourIcon /> 
  },
];
```

### Ubah Theme

Edit `src/App.tsx`:
```tsx
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2', // Ubah warna primary
    },
    secondary: {
      main: '#dc004e', // Ubah warna secondary
    },
  },
});
```

### Tambah API Endpoint

Edit `src/lib/api.ts`:
```tsx
export const myApi = {
  getData: async () => {
    const response = await api.get('/my-endpoint');
    return response.data;
  },
};
```

## 🔧 Common Tasks

### Export Data ke Excel
```tsx
import { exportApi } from '@/lib/api';

const handleExport = async () => {
  const blob = await exportApi.exportToExcel({
    area: 'Jakarta',
    months: 6
  });
  downloadFile(blob, 'data.xlsx');
};
```

### Format Currency
```tsx
import { formatCurrency } from '@/utils/helpers';

formatCurrency(2500000); // "Rp 2.5 Jt"
```

### Format Date
```tsx
import { formatDate } from '@/utils/helpers';

formatDate('2026-05-08'); // "08 Mei 2026"
```

## 🐛 Troubleshooting

### Module not found error
```bash
# Clear cache dan reinstall
rm -rf node_modules package-lock.json
npm install
```

### Port already in use
```bash
# Ubah port di vite.config.ts
server: {
  port: 3001,
}
```

### Backend API tidak terkoneksi
1. Pastikan backend running di port 5000
2. Check proxy di `vite.config.ts`
3. Check CORS settings di backend

### TypeScript errors
```bash
# Check type errors
npm run build
```

## 📚 Belajar Lebih Lanjut

- **React**: https://react.dev
- **TypeScript**: https://www.typescriptlang.org/
- **Material-UI**: https://mui.com
- **TanStack Table**: https://tanstack.com/table
- **Recharts**: https://recharts.org

## 💡 Tips

1. **Hot Reload**: Edit file dan save, browser auto-refresh
2. **Component First**: Buat reusable components
3. **Type Safety**: Gunakan TypeScript types
4. **React Query**: Gunakan untuk data fetching
5. **Responsive**: Test di mobile view (DevTools > Toggle Device)

## 🎯 Next Steps

1. ✅ Explore demo pages (`/customers`, `/comparison`)
2. ✅ Baca component documentation
3. ✅ Custom theme sesuai brand Anda
4. ✅ Tambah pages sesuai kebutuhan
5. ✅ Integrate dengan backend API
6. ✅ Deploy ke production

---

**Selamat coding! 🚀**
