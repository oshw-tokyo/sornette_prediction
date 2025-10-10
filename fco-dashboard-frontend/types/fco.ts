export interface FCOAnalysis {
  id?: number
  symbol: string
  analysis_basis_date: string
  ds_lppls_confidence: number
  ds_lppls_confidence_neg?: number
  ds_lppls_trust?: number | null
  bubble_type?: string
  predicted_crash_date?: string | null
  predicted_tc?: number
  tc_std?: number
  scenario_probability?: number
  data_period_start: string
  data_period_end: string
  analysis_date?: string
  r_squared?: number
  price_at_analysis?: number
  expected_price_at_tc?: number
  price_change_percent?: number
  data_period_days?: number
}

export interface FCOTimeSeries {
  date: string
  price: number
  fitted_price?: number
  confidence_upper?: number
  confidence_lower?: number
}

export interface FCOSymbol {
  symbol: string
  name: string
  latest_analysis_date?: string
  analysis_count: number
}

export interface FCOSummary {
  total_analyses: number
  latest_analysis: FCOAnalysis | null
  average_confidence: number
  high_confidence_count: number
  bubble_type_distribution: {
    positive: number
    negative: number
  }
}

export interface FCOTimeSeriesWithPrice {
  dates: string[]
  prices: number[]
  log_prices: number[]
  lppl_fit?: number[] | null
  confidence: number
  trust: number
  predicted_crash_date: string
  analysis_basis_date: string
  fitting_window_start_date?: string | null
  fitting_window_days?: number | null
  symbol: string
  bubble_type: string
  lppl_params?: {
    tc: number
    m: number
    omega: number
    phi: number
  } | null
}