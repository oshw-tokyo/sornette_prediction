import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fcoApi } from '@/lib/api-client'
import { FCOSymbol, FCOAnalysis } from '@/types/fco'
import { FCOScatterPlot } from '@/components/charts/FCOScatterPlot'
import { FCOClusteringPlot } from '@/components/charts/FCOClusteringPlot'
import { FCOTimeSeriesChart } from '@/components/charts/FCOTimeSeriesChart'
import { TrendingUp, TrendingDown, Activity, AlertCircle, BarChart3, ScatterChart, Calendar, Clock } from 'lucide-react'

// Historical event definitions with associated symbols
const HISTORICAL_EVENTS = [
  { name: 'Black Monday', date: '1987-10-19', symbol: 'NASDAQCOM', label: 'Black Monday (1987-10-19) [NASDAQCOM]' },
  { name: 'Dotcom Bubble', date: '2000-03-10', symbol: 'NASDAQCOM', label: 'Dotcom Bubble (2000-03-10) [NASDAQCOM]' },
  { name: 'Lehman Shock', date: '2008-09-15', symbol: 'SP500', label: 'Lehman Shock (2008-09-15) [SP500]' },
] as const

// Period options based on market trading days (252 days/year)
const PERIOD_OPTIONS = [
  { label: '1ヶ月 (21日)', value: 21 },
  { label: '3ヶ月 (63日)', value: 63 },
  { label: '6ヶ月 (126日)', value: 126 },
  { label: '1年 (252日)', value: 252 },
  { label: '2年 (504日)', value: 504 },
  { label: '3年 (756日)', value: 756 },
  { label: '5年 (1260日)', value: 1260 },
  { label: '10年 (2520日)', value: 2520 },
  { label: '20年 (5040日)', value: 5040 },
  { label: 'Full Period (全期間)', value: 10000 },
] as const

export default function Dashboard() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('SP500')
  const [viewMode, setViewMode] = useState<'scatter' | 'clustering'>('scatter')

  // Period filter states (replacing sortBy and displayCount)
  const [periodMode, setPeriodMode] = useState<'latest' | 'historical' | 'user-defined'>('latest')
  const [selectedEvent, setSelectedEvent] = useState<string>('Black Monday')
  const [baseDate, setBaseDate] = useState<string>(new Date().toISOString().split('T')[0])
  const [periodDays, setPeriodDays] = useState<number>(252) // Default: 1年

  // Other states
  const [selectedAnalysisId, setSelectedAnalysisId] = useState<number | null>(null)

  // 銘柄一覧を取得
  const { data: symbols, isLoading: symbolsLoading } = useQuery({
    queryKey: ['symbols'],
    queryFn: () => fcoApi.getSymbols(),
  })

  // 選択された銘柄の最新分析を取得
  const { data: latestAnalysis, isLoading: analysisLoading } = useQuery({
    queryKey: ['latest', selectedSymbol],
    queryFn: () => fcoApi.getLatestAnalysis(selectedSymbol),
    enabled: !!selectedSymbol,
  })

  // 時系列データを取得
  const { data: timeSeries } = useQuery({
    queryKey: ['timeseries', selectedSymbol],
    queryFn: () => fcoApi.getTimeSeries(selectedSymbol),
    enabled: !!selectedSymbol,
  })

  // Get all FCO analyses for visualization
  const { data: allAnalyses, isLoading: allAnalysesLoading } = useQuery({
    queryKey: ['all-analyses'],
    queryFn: () => fcoApi.getAllAnalyses(),
  })

  // Get selected analysis details
  const selectedAnalysis = allAnalyses?.find(a => a.id === selectedAnalysisId)

  // Fetch time series data for selected analysis
  const { data: timeSeriesData, isLoading: timeSeriesLoading } = useQuery({
    queryKey: ['price-series', selectedAnalysis?.symbol, selectedAnalysisId],
    queryFn: () => {
      if (!selectedAnalysis) return null
      return fcoApi.getPriceSeries(selectedAnalysis.symbol, selectedAnalysisId!, 365)
    },
    enabled: !!selectedAnalysisId && !!selectedAnalysis,
  })

  // Calculate date range based on period mode
  const getDateRange = () => {
    if (periodMode === 'historical') {
      const event = HISTORICAL_EVENTS.find(e => e.name === selectedEvent)
      if (event) {
        const eventDate = new Date(event.date)
        const startDate = new Date(eventDate)
        startDate.setDate(startDate.getDate() - periodDays)
        return { start: startDate.toISOString().split('T')[0], end: event.date }
      }
    } else if (periodMode === 'user-defined') {
      const endDate = new Date(baseDate)
      const startDate = new Date(endDate)
      startDate.setDate(startDate.getDate() - periodDays)
      return { start: startDate.toISOString().split('T')[0], end: baseDate }
    }
    // For 'latest' mode, use the most recent analysis date minus period
    if (allAnalyses && allAnalyses.length > 0) {
      const latestDate = allAnalyses.reduce((max, a) => {
        const date = new Date(a.analysis_basis_date)
        return date > max ? date : max
      }, new Date(0))
      const startDate = new Date(latestDate)
      startDate.setDate(startDate.getDate() - periodDays)
      return { start: startDate.toISOString().split('T')[0], end: latestDate.toISOString().split('T')[0] }
    }
    return null
  }

  // Get last updated timestamp
  const getLastUpdated = () => {
    if (!allAnalyses || allAnalyses.length === 0) return null
    const latestDate = allAnalyses.reduce((max, a) => {
      const date = new Date(a.analysis_basis_date)
      return date > max ? date : max
    }, new Date(0))
    return latestDate.toISOString().split('T')[0]
  }

  // Auto-select first point when data loads or filters change
  useEffect(() => {
    if (viewMode === 'scatter' && allAnalyses && allAnalyses.length > 0 && !selectedAnalysisId) {
      // Apply same filtering logic to get first point
      let filteredData = selectedSymbol
        ? allAnalyses.filter(a => a.symbol === selectedSymbol)
        : allAnalyses;

      // Apply date range filter
      const dateRange = getDateRange()
      if (dateRange) {
        filteredData = filteredData.filter(a => {
          const date = a.analysis_basis_date
          return date >= dateRange.start && date <= dateRange.end
        })
      }

      // Sort by latest (always)
      filteredData = [...filteredData].sort((a, b) =>
        new Date(b.analysis_basis_date).getTime() - new Date(a.analysis_basis_date).getTime()
      );

      // Select first point if available
      if (filteredData.length > 0 && filteredData[0].id) {
        console.log('[Auto-Select] Setting initial point:', filteredData[0].id, filteredData[0].symbol)
        setSelectedAnalysisId(filteredData[0].id)
      } else {
        console.log('[Auto-Select] No filtered data available')
      }
    }
  }, [viewMode, allAnalyses, selectedSymbol, selectedAnalysisId, periodMode, selectedEvent, baseDate, periodDays])

  // Debug logging for Time Series rendering
  useEffect(() => {
    console.log('[Time Series Debug]', {
      viewMode,
      selectedAnalysisId,
      hasTimeSeriesData: !!timeSeriesData,
      timeSeriesLoading,
      selectedAnalysisSymbol: selectedAnalysis?.symbol,
      timeSeriesDataLength: timeSeriesData?.prices?.length
    })
  }, [viewMode, selectedAnalysisId, timeSeriesData, timeSeriesLoading, selectedAnalysis])

  const getBubbleTypeColor = (type: string) => {
    return type === 'positive' ? 'text-red-500' : 'text-blue-500'
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.7) return 'text-green-500'
    if (confidence >= 0.4) return 'text-yellow-500'
    return 'text-red-500'
  }

  const lastUpdated = getLastUpdated()
  const dateRange = getDateRange()

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent">
                FCO v2.1 Dashboard
              </h1>
              <p className="text-gray-400">DS-LPPLS Analysis System with Advanced Clustering</p>
            </div>
            {lastUpdated && (
              <div className="flex items-center gap-2 text-sm text-gray-400 bg-gray-800 px-4 py-2 rounded-lg">
                <Clock size={16} />
                <span>最終データ更新: {lastUpdated}</span>
              </div>
            )}
          </div>
        </div>

        {/* Control Panel */}
        <div className="mb-8 bg-gray-800 rounded-lg p-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Symbol Selector */}
            <div>
              <label className="block text-sm font-medium mb-2">Select Symbol</label>
              <select
                className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 w-full"
                value={selectedSymbol}
                onChange={(e) => setSelectedSymbol(e.target.value)}
              >
                <option value="">-- All Symbols --</option>
                {symbols?.map((symbol) => (
                  <option key={symbol.symbol} value={symbol.symbol}>
                    {symbol.symbol} - {symbol.name}
                  </option>
                ))}
              </select>
            </div>

            {/* View Mode Selector */}
            <div>
              <label className="block text-sm font-medium mb-2">View Mode</label>
              <div className="flex gap-2">
                <button
                  className={`flex-1 px-3 py-2 rounded-lg flex items-center justify-center gap-1 transition-colors ${
                    viewMode === 'scatter'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                  onClick={() => setViewMode('scatter')}
                >
                  <ScatterChart size={16} />
                  <span className="text-sm">Scatter</span>
                </button>
                <button
                  className={`flex-1 px-3 py-2 rounded-lg flex items-center justify-center gap-1 transition-colors ${
                    viewMode === 'clustering'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                  onClick={() => setViewMode('clustering')}
                >
                  <BarChart3 size={16} />
                  <span className="text-sm">Cluster</span>
                </button>
              </div>
            </div>
          </div>

          {/* Scatter View Filters */}
          {viewMode === 'scatter' && (
            <div className="mt-4 pt-4 border-t border-gray-700">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Period Filter */}
                <div className="space-y-3">
                  <label className="block text-sm font-medium flex items-center gap-2">
                    <Calendar size={16} />
                    Analysis Period Filter
                  </label>

                  {/* Period Mode Selection */}
                  <div className="space-y-2">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="periodMode"
                        value="latest"
                        checked={periodMode === 'latest'}
                        onChange={(e) => setPeriodMode(e.target.value as any)}
                        className="w-4 h-4"
                      />
                      <span className="text-sm">Latest (最新データ)</span>
                    </label>

                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="periodMode"
                        value="historical"
                        checked={periodMode === 'historical'}
                        onChange={(e) => setPeriodMode(e.target.value as any)}
                        className="w-4 h-4"
                      />
                      <span className="text-sm">Historical Event</span>
                    </label>

                    {periodMode === 'historical' && (
                      <div className="ml-6 space-y-2">
                        <select
                          className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 w-full text-sm"
                          value={selectedEvent}
                          onChange={(e) => setSelectedEvent(e.target.value)}
                        >
                          {HISTORICAL_EVENTS.map((event) => (
                            <option key={event.name} value={event.name}>
                              {event.label}
                            </option>
                          ))}
                        </select>
                        <div className="text-xs text-blue-400 bg-blue-900/20 px-3 py-2 rounded">
                          💡 推奨銘柄: {HISTORICAL_EVENTS.find(e => e.name === selectedEvent)?.symbol}
                        </div>
                      </div>
                    )}

                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="periodMode"
                        value="user-defined"
                        checked={periodMode === 'user-defined'}
                        onChange={(e) => setPeriodMode(e.target.value as any)}
                        className="w-4 h-4"
                      />
                      <span className="text-sm">User Defined</span>
                    </label>
                  </div>
                </div>

                {/* Period Display / User Defined Controls */}
                <div className="space-y-3">
                  <label className="block text-sm font-medium">
                    Display Period
                  </label>

                  {periodMode === 'user-defined' ? (
                    // User Defined mode: show editable controls
                    <div className="space-y-3">
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">Base Date:</label>
                        <input
                          type="date"
                          value={baseDate}
                          onChange={(e) => setBaseDate(e.target.value)}
                          className="bg-gray-700 border border-gray-600 rounded px-3 py-2 w-full text-sm"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-400 block mb-1">Period:</label>
                        <select
                          value={periodDays}
                          onChange={(e) => {
                            const value = parseInt(e.target.value)
                            if (!isNaN(value) && value > 0) {
                              setPeriodDays(value)
                            }
                          }}
                          className="bg-gray-700 border border-gray-600 rounded px-3 py-2 w-full text-sm"
                        >
                          {PERIOD_OPTIONS.map(option => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ) : (
                    // Latest/Historical mode: show period display only
                    <div className="bg-gray-700 rounded-lg px-4 py-3 h-full flex flex-col justify-center">
                      {dateRange && (
                        <>
                          <div className="text-sm text-gray-300 mb-2">
                            <span className="font-medium">Period:</span> {periodDays} days
                          </div>
                          <div className="text-xs text-gray-400">
                            {dateRange.start} 〜 {dateRange.end}
                          </div>
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Analysis Display */}
        {/* NOTE: Metrics cards removed to avoid confusion with view mode selection.
            All relevant metrics are available via hover tooltips on the plots. */}
        {/*
        {selectedSymbol && latestAnalysis && (
          <div className="mb-8">
            // Key Metrics Cards - Removed to prevent confusion
            // DS-LPPLS Confidence: Percentage of time windows meeting filtering conditions
            // DS-LPPLS Trust: Bootstrap-based statistical reliability
            // Bubble Type: Latest analysis bubble type (may differ from view selection)
          </div>
        )}
        */}

        {/* Main Visualization Area */}
        <div className="bg-gray-800 rounded-lg p-6">
          {allAnalysesLoading ? (
            <div className="flex items-center justify-center h-[600px]">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
                <p className="text-gray-400">Loading analysis data...</p>
              </div>
            </div>
          ) : allAnalyses && allAnalyses.length > 0 ? (
            (() => {
              // Filter data based on selected symbol
              let filteredData = selectedSymbol
                ? allAnalyses.filter(a => a.symbol === selectedSymbol)
                : allAnalyses;

              // Apply Scatter View filters
              if (viewMode === 'scatter') {
                // Apply date range filter
                if (dateRange) {
                  filteredData = filteredData.filter(a => {
                    const date = a.analysis_basis_date
                    return date >= dateRange.start && date <= dateRange.end
                  })
                }

                // Always sort by latest
                filteredData = [...filteredData].sort((a, b) =>
                  new Date(b.analysis_basis_date).getTime() - new Date(a.analysis_basis_date).getTime()
                );
              }

              return filteredData.length > 0 ? (
                <>
                  {viewMode === 'scatter' ? (
                    <FCOScatterPlot
                      data={filteredData}
                      onPointClick={(analysisId) => setSelectedAnalysisId(analysisId)}
                    />
                  ) : (
                    <FCOClusteringPlot data={filteredData} />
                  )}

                  {/* Time Series Display (below scatter plot when point is clicked) */}
                  {viewMode === 'scatter' && selectedAnalysisId && timeSeriesData && (
                    <div className="mt-6">
                      <FCOTimeSeriesChart data={timeSeriesData} height={400} showTitle={true} />
                    </div>
                  )}
                </>
              ) : (
                <div className="flex items-center justify-center h-[600px]">
                  <div className="text-center">
                    <AlertCircle size={48} className="text-gray-600 mx-auto mb-4" />
                    <p className="text-gray-400 text-lg">
                      {periodMode === 'historical'
                        ? 'この期間にデータがありません'
                        : selectedSymbol
                          ? `No data available for ${selectedSymbol}`
                          : 'No data available'}
                    </p>
                    <p className="text-gray-500 text-sm mt-2">
                      {periodMode === 'historical'
                        ? '期間を変更するか、推奨銘柄を選択してください'
                        : 'Select a different symbol, period, or adjust filters'}
                    </p>
                  </div>
                </div>
              );
            })()
          ) : (
            <div className="flex items-center justify-center h-[600px]">
              <div className="text-center">
                <AlertCircle size={48} className="text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 text-lg">No analysis data available</p>
                <p className="text-gray-500 text-sm mt-2">Run FCO analysis to generate data</p>
              </div>
            </div>
          )}
        </div>

        {/* Footer Info */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>FCO v2.1 - Financial Crash Observatory with DS-LPPLS Indicators</p>
          <p>Axes: X = Predicted Crash Date, Y = Fitting Basis Date (reversed as requested)</p>
        </div>
      </div>
    </div>
  )
}