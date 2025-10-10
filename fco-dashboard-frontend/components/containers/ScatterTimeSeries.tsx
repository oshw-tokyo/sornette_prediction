import React, { useState, useEffect } from 'react'
import { FCOTimeSeriesChart } from '@/components/charts/FCOTimeSeriesChart'
import { FCOTimeSeriesWithPrice } from '@/types/fco'
import { fcoApi } from '@/lib/api-client'
import { Loader2, TrendingUp, Calendar, AlertCircle } from 'lucide-react'

interface ScatterTimeSeriesProps {
  symbol: string
  viewMode: string
  analyses: any[]  // FCO analysis results
  displayPeriod: {
    start: Date
    end: Date
  } | null
}

export const ScatterTimeSeries: React.FC<ScatterTimeSeriesProps> = ({
  symbol,
  viewMode,
  analyses,
  displayPeriod
}) => {
  const [timeSeriesData, setTimeSeriesData] = useState<FCOTimeSeriesWithPrice[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [topN, setTopN] = useState(3)  // Default to top 3

  useEffect(() => {
    if (analyses.length === 0) {
      setTimeSeriesData([])
      return
    }

    loadTimeSeriesData()
  }, [symbol, analyses, viewMode, topN])

  const loadTimeSeriesData = async () => {
    setLoading(true)
    setError(null)

    try {
      // Filter analyses based on display period
      let filteredAnalyses = analyses
      if (displayPeriod) {
        filteredAnalyses = analyses.filter(a => {
          const analysisDate = new Date(a.analysis_basis_date)
          return analysisDate >= displayPeriod.start && analysisDate <= displayPeriod.end
        })
      }

      // Sort by confidence and get top N
      const topAnalyses = filteredAnalyses
        .sort((a, b) => (b.ds_lppls_confidence || 0) - (a.ds_lppls_confidence || 0))
        .slice(0, topN)

      // Load time series data for each analysis
      const promises = topAnalyses.map(async (analysis) => {
        try {
          // Use the symbol from the analysis if no specific symbol is selected
          const targetSymbol = symbol || analysis.symbol
          const data = await fcoApi.getPriceSeries(
            targetSymbol,
            analysis.id,
            365  // Get 365 days of data before analysis date
          )
          return data
        } catch (err) {
          console.error(`Failed to load time series for analysis ${analysis.id}:`, err)
          return null
        }
      })

      const results = await Promise.all(promises)
      const validResults = results.filter(r => r !== null) as FCOTimeSeriesWithPrice[]
      setTimeSeriesData(validResults)

    } catch (err) {
      console.error('Failed to load time series data:', err)
      setError('Failed to load time series data')
    } finally {
      setLoading(false)
    }
  }

  // Remove the check for symbol since we can display data for all symbols

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
        <span className="ml-2">Loading time series data...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-400">
        <AlertCircle className="w-6 h-6 mr-2" />
        <span>{error}</span>
      </div>
    )
  }

  if (timeSeriesData.length === 0) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        <div className="text-center">
          <Calendar className="w-12 h-12 mx-auto mb-2 opacity-50" />
          <p>No time series data available for the selected period</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Top N Selector */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">
          Top {topN} Time Series by DS-LPPLS Confidence {symbol && `- ${symbol}`}
        </h3>
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-400">Display:</span>
          <select
            value={topN.toString()}
            onChange={(e) => setTopN(parseInt(e.target.value))}
            className="w-24 px-3 py-1 bg-gray-700 text-white rounded-md border border-gray-600 focus:border-blue-500 focus:outline-none"
          >
            <option value="1">Top 1</option>
            <option value="3">Top 3</option>
            <option value="5">Top 5</option>
            <option value="10">Top 10</option>
          </select>
        </div>
      </div>

      {/* Time Series Charts - Vertical Layout */}
      <div className="space-y-8 max-h-[2000px] overflow-y-auto">
        {timeSeriesData.map((data, index) => (
          <div key={index} className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <div className="mb-4">
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="text-lg font-semibold text-white">Analysis #{index + 1}</h3>
                  <p className="text-sm text-gray-400 mt-1">
                    Analysis Basis Date: {data.analysis_basis_date}
                  </p>
                </div>
                <div className="text-right">
                  <div className={`text-lg font-bold ${
                    data.confidence >= 0.7 ? 'text-green-400' :
                    data.confidence >= 0.4 ? 'text-yellow-400' : 'text-red-400'
                  }`}>
                    {(data.confidence * 100).toFixed(1)}% Confidence
                  </div>
                  <p className="text-sm text-gray-400 mt-1">
                    Trust: {(data.trust * 100).toFixed(1)}%
                  </p>
                  {data.predicted_crash_date && (
                    <p className="text-sm text-amber-400 mt-1">
                      Crash: {data.predicted_crash_date}
                    </p>
                  )}
                </div>
              </div>
            </div>
            <FCOTimeSeriesChart
              data={data}
              height={500}  // Increased height for better visibility
              showTitle={false}
            />
          </div>
        ))}
      </div>

      {/* Additional Information */}
      <div className="mt-4 p-4 bg-gray-800 rounded-lg border border-gray-700">
        <h4 className="text-sm font-semibold text-gray-300 mb-2">Understanding the Charts</h4>
        <ul className="text-xs text-gray-400 space-y-1">
          <li>• <span className="text-green-400">Green line</span>: Historical market price data in log scale</li>
          <li>• <span className="text-orange-400">Orange solid line</span>: LPPL model fit in log scale</li>
          <li>• <span className="text-red-400">Red dash-dot line</span>: Predicted crash date</li>
          <li>• Y-axis shows log(Price) with actual price values as labels</li>
          <li>• Log scale reveals exponential growth patterns and bubble formation</li>
          <li>• Higher DS-LPPLS confidence (≥70%) indicates stronger bubble pattern</li>
          <li>• Trust score represents statistical reliability from bootstrap analysis</li>
        </ul>
      </div>
    </div>
  )
}