# Sales Analytics Dashboard - Frontend

Dashboard analytics penjualan dengan React, TypeScript, dan Material-UI.

## 🚀 Fitur Utama

### ✅ Interactive Data Tables
- **Pagination & Sorting**: Navigasi data yang mudah
- **Search & Filter**: Pencarian real-time dan filter per kolom
- **Column Visibility**: Toggle tampilan kolom sesuai kebutuhan
- **Row Selection**: Pilih multiple rows untuk bulk actions
- **Export Data**: Export ke Excel dan CSV
- **Custom Actions**: Actions per row (View, Edit, Delete, dll)
- **Responsive Design**: Tampilan optimal di mobile dan desktop

### ✅ Comparison Mode Visualizations
- **Period Comparison**: Bandingkan data antar periode (bulan, quarter, tahun)
- **Metrics Cards**: KPI cards dengan perbandingan dan trend indicators
- **Side-by-Side Charts**: Visualisasi perbandingan dengan bar progress
- **Variance Analysis**: Analisa varians aktual vs target
- **Multi-Series Charts**: Line & bar charts untuk multiple periods
- **Smart Insights**: AI-generated insights dan rekomendasi

## 📦 Tech Stack

- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **UI Library**: Material-UI (MUI) v5
- **Charts**: Recharts
- **Data Tables**: TanStack Table
- **State Management**: Zustand
- **Data Fetching**: TanStack Query (React Query)
- **Forms**: React Hook Form + Zod
- **HTTP Client**: Axios
- **Date Handling**: date-fns
- **Routing**: React Router v6
- **Notifications**: React Hot Toast

## 🛠️ Installation

### Prerequisites
- Node.js 18+ dan npm/yarn
- Backend API running di http://localhost:5000

### Steps

1. **Navigate ke folder frontend**
   ```bash
   cd frontend
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm run dev
   ```

   Aplikasi akan berjalan di http://localhost:3000

4. **Build untuk production**
   ```bash
   npm run build
   ```

   Output akan ada di folder `dist/`

5. **Preview production build**
   ```bash
   npm run preview
   ```

## 📁 Struktur Folder

```
frontend/
├── src/
│   ├── components/         # Reusable components
│   │   ├── DataTable/     # Interactive data table component
│   │   ├── ComparisonMode/ # Comparison visualizations
│   │   └── Layout/        # App layout & navigation
│   ├── pages/             # Page components
│   │   ├── CustomersPage.tsx
│   │   ├── SalesComparisonPage.tsx
│   │   └── ...
│   ├── lib/               # Libraries & configurations
│   │   └── axios.ts       # Axios setup with interceptors
│   ├── types/             # TypeScript type definitions
│   │   └── index.ts
│   ├── utils/             # Helper functions
│   │   └── helpers.ts     # Format currency, dates, etc.
│   ├── App.tsx            # Main app component
│   ├── main.tsx           # Entry point
│   └── index.css          # Global styles
├── public/                # Static assets
├── index.html            # HTML template
├── package.json          # Dependencies
├── tsconfig.json         # TypeScript config
├── vite.config.ts        # Vite config
└── README.md
```

## 🎨 Komponen Utama

### DataTable Component
```tsx
import { DataTable } from '@/components/DataTable';

<DataTable
  data={customers}
  columns={columns}
  actions={actions}
  loading={loading}
  pagination
  searchable
  exportable
  selectable
  onSelectionChange={setSelected}
/>
```

### Comparison Mode Components
```tsx
import {
  ComparisonChart,
  ComparisonMetrics,
  SideBySideComparison,
  VarianceAnalysis
} from '@/components/ComparisonMode';

// Metrics cards
<ComparisonMetrics metrics={metrics} />

// Line/Bar chart
<ComparisonChart
  title="Trend Omzet"
  periods={periods}
  data={data}
  chartType="line"
/>

// Side-by-side comparison
<SideBySideComparison
  title="Per Kategori"
  periods={periods}
  data={categoryData}
/>

// Variance analysis
<VarianceAnalysis
  title="Aktual vs Target"
  data={varianceData}
/>
```

## 🔧 Konfigurasi

### API Endpoint
Edit `vite.config.ts` untuk mengubah API URL:
```ts
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:5000',
      changeOrigin: true,
    },
  },
}
```

### Theme Customization
Edit `src/App.tsx` untuk custom theme:
```tsx
const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    // ... customize more
  },
});
```

## 📊 Contoh Implementasi

### Data Table dengan Actions
Lihat file: `src/pages/CustomersPage.tsx`
- Full-featured customer list
- Multiple actions per row
- Bulk operations
- Export functionality

### Comparison Visualizations
Lihat file: `src/pages/SalesComparisonPage.tsx`
- Multi-period comparison
- KPI metrics with trends
- Various chart types
- Insights & recommendations

## 🚀 Development Tips

1. **Hot Reload**: Perubahan otomatis reload
2. **TypeScript**: Gunakan type checking untuk avoid errors
3. **Component Reusability**: Buat components yang reusable
4. **API Integration**: Gunakan React Query untuk caching & loading states
5. **Responsive Design**: Test di berbagai screen sizes

## 📝 Available Scripts

```bash
npm run dev      # Start development server
npm run build    # Build for production
npm run preview  # Preview production build
npm run lint     # Run ESLint
```

## 🐛 Troubleshooting

### Port sudah digunakan
```bash
# Ubah port di vite.config.ts
server: {
  port: 3001, // Change port
}
```

### Module not found
```bash
# Clear cache dan reinstall
rm -rf node_modules package-lock.json
npm install
```

### API tidak terkoneksi
- Pastikan backend running di http://localhost:5000
- Check CORS settings di backend
- Check proxy config di `vite.config.ts`

## 📚 Resources

- [React Documentation](https://react.dev)
- [Material-UI](https://mui.com)
- [TanStack Table](https://tanstack.com/table)
- [Recharts](https://recharts.org)
- [Vite](https://vitejs.dev)

## 🎯 Next Steps

1. Tambahkan authentication pages
2. Implement remaining pages (Sales, Categories, etc.)
3. Add more chart types
4. Implement real-time updates
5. Add unit tests
6. Optimize performance

---

**Created with ❤️ for QL Dashboard Project**
