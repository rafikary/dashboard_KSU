export interface CustomerData {
  custname: string
  total_omzet: number
  total_transactions: number
  avg_transaction: number
  last_transaction: string
  area: string
  kota: string
}

export interface CategoryBreakdown {
  category: string
  omzet: number
  percentage: number
  growth?: number
  transactions: number
}

export interface ComparisonPeriod {
  id: string
  label: string
  startDate: string
  endDate: string
  color?: string
}

export interface ComparisonMetric {
  id: string
  label: string
  currentValue: number
  previousValue: number
  change: number
  changePercent: number
  format?: 'currency' | 'number' | 'percent'
}
