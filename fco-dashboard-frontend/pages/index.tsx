import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fcoApi } from '@/lib/api-client'
import { FCOSymbol, FCOAnalysis } from '@/types/fco'
import { FCOScatterPlot } from '@/components/charts/FCOScatterPlot'
import { FCOClusteringPlot } from '@/components/charts/FCOClusteringPlot'
import { TrendingUp, TrendingDown, Activity, AlertCircle, BarChart3, ScatterChart } from 'lucide-react'

export default function Dashboard() {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('')
  const [viewMode, setViewMode] = useState<'scatter' | 'clustering'>('scatter')
  const [showNegative, setShowNegative] = useState(false)

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

  const getBubbleTypeColor = (type: string) => {
    return type === 'positive' ? 'text-red-500' : 'text-blue-500'
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.7) return 'text-green-500'
    if (confidence >= 0.4) return 'text-yellow-500'
    return 'text-red-500'
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-600 bg-clip-text text-transparent">
            FCO v2.1 Dashboard
          </h1>
          <p className="text-gray-400">DS-LPPLS Analysis System with Advanced Clustering</p>
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
                  className={`flex-1 px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors ${
                    viewMode === 'scatter'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                  onClick={() => setViewMode('scatter')}
                >
                  <ScatterChart size={18} />
                  Scatter Plot
                </button>
                <button
                  className={`flex-1 px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-colors ${
                    viewMode === 'clustering'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                  onClick={() => setViewMode('clustering')}
                >
                  <BarChart3 size={18} />
                  Clustering
                </button>
              </div>
            </div>

            {/* Bubble Type Selector (for scatter view) */}
            {viewMode === 'scatter' && (
              <div>
                <label className="block text-sm font-medium mb-2">Bubble Type</label>
                <div className="flex gap-2">
                  <button
                    className={`flex-1 px-4 py-2 rounded-lg transition-colors ${
                      !showNegative
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                    onClick={() => setShowNegative(false)}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <TrendingUp size={18} />
                      Positive
                    </div>
                  </button>
                  <button
                    className={`flex-1 px-4 py-2 rounded-lg transition-colors ${
                      showNegative
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                    }`}
                    onClick={() => setShowNegative(true)}
                  >
                    <div className="flex items-center justify-center gap-2">
                      <TrendingDown size={18} />
                      Negative
                    </div>
                  </button>
                </div>
              </div>
            )}
          </div>
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
              const filteredData = selectedSymbol
                ? allAnalyses.filter(a => a.symbol === selectedSymbol)
                : allAnalyses;

              return filteredData.length > 0 ? (
                viewMode === 'scatter' ? (
                  <FCOScatterPlot data={filteredData} showNegative={showNegative} />
                ) : (
                  <FCOClusteringPlot data={filteredData} />
                )
              ) : (
                <div className="flex items-center justify-center h-[600px]">
                  <div className="text-center">
                    <AlertCircle size={48} className="text-gray-600 mx-auto mb-4" />
                    <p className="text-gray-400 text-lg">No data available for {selectedSymbol}</p>
                    <p className="text-gray-500 text-sm mt-2">Select a different symbol or "All Symbols"</p>
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