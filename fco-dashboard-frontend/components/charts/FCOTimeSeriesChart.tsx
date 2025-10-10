import React, { useMemo } from 'react'
import dynamic from 'next/dynamic'
import { FCOTimeSeriesWithPrice } from '@/types/fco'

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false })

interface FCOTimeSeriesChartProps {
  data: FCOTimeSeriesWithPrice
  height?: number
  showTitle?: boolean
}

export const FCOTimeSeriesChart: React.FC<FCOTimeSeriesChartProps> = ({
  data,
  height = 400,
  showTitle = true
}) => {
  const plotData = useMemo(() => {
    const traces: any[] = []

    // Separate historical and future data
    const validPrices = data.prices.filter(p => p !== null && !isNaN(p))
    const historicalIndices = data.prices.map((p, i) => p !== null && !isNaN(p) ? i : -1).filter(i => i >= 0)

    // Convert valid prices to log scale
    const logPrices = validPrices.map(p => Math.log(p))
    const minLogPrice = Math.min(...logPrices)

    // 1. Price data in log scale - split into fitting and non-fitting periods
    if (historicalIndices.length > 0 && data.fitting_window_start_date) {
      const fittingStartDate = data.fitting_window_start_date
      const fittingEndDate = data.analysis_basis_date

      // Split data into fitting and non-fitting periods
      const fittingDates: string[] = []
      const fittingLogPrices: number[] = []
      const fittingPrices: number[] = []
      const nonFittingDates: string[] = []
      const nonFittingLogPrices: number[] = []
      const nonFittingPrices: number[] = []

      historicalIndices.forEach(i => {
        const date = data.dates[i]
        const price = data.prices[i]
        const logPrice = Math.log(price)

        if (date >= fittingStartDate && date <= fittingEndDate) {
          fittingDates.push(date)
          fittingLogPrices.push(logPrice)
          fittingPrices.push(price)
        } else {
          nonFittingDates.push(date)
          nonFittingLogPrices.push(logPrice)
          nonFittingPrices.push(price)
        }
      })

      // Non-fitting period (dashed line, lighter blue)
      if (nonFittingDates.length > 0) {
        traces.push({
          x: nonFittingDates,
          y: nonFittingLogPrices,
          type: 'scatter',
          mode: 'lines',
          name: 'log(Price) - Non-fitting Period',
          line: {
            color: '#60a5fa',  // Light blue for non-fitting data
            width: 2.5,
            dash: 'dash'
          },
          yaxis: 'y',
          hovertemplate: 'Date: %{x}<br>log(Price): %{y:.4f}<br>Price: $%{customdata:.2f}<extra></extra>',
          customdata: nonFittingPrices
        })
      }

      // Fitting period (solid line, darker blue)
      if (fittingDates.length > 0) {
        traces.push({
          x: fittingDates,
          y: fittingLogPrices,
          type: 'scatter',
          mode: 'lines',
          name: 'log(Price) - Fitting Period',
          line: {
            color: '#2563eb',  // Dark blue for fitting data
            width: 2.5,
            dash: 'solid'
          },
          yaxis: 'y',
          hovertemplate: 'Date: %{x}<br>log(Price): %{y:.4f}<br>Price: $%{customdata:.2f}<extra></extra>',
          customdata: fittingPrices
        })
      }
    } else {
      // Fallback: show all data as single trace if fitting window info not available
      const historicalDates = historicalIndices.map(i => data.dates[i])
      const historicalLogPrices = historicalIndices.map(i => Math.log(data.prices[i]))
      const historicalPrices = historicalIndices.map(i => data.prices[i])

      traces.push({
        x: historicalDates,
        y: historicalLogPrices,
        type: 'scatter',
        mode: 'lines',
        name: 'log(Price) - Market Data',
        line: {
          color: '#2563eb',  // Blue for actual data
          width: 2.5
        },
        yaxis: 'y',
        hovertemplate: 'Date: %{x}<br>log(Price): %{y:.4f}<br>Price: $%{customdata:.2f}<extra></extra>',
        customdata: historicalPrices
      })
    }

    // 2. LPPL fit (already in log scale)
    if (data.lppl_fit && data.lppl_fit.length > 0) {
      // Filter out None/null values and get valid indices
      const validLpplIndices: number[] = []
      const validLpplValues: number[] = []
      const validLpplDates: string[] = []

      data.lppl_fit.forEach((val, i) => {
        if (val !== null && val !== undefined && !isNaN(val) && isFinite(val)) {
          validLpplIndices.push(i)
          validLpplValues.push(val)
          validLpplDates.push(data.dates[i])
        }
      })

      // Only plot if we have valid LPPL values
      if (validLpplValues.length > 0) {
        // Split LPPL fit into historical and future parts
        const lastHistoricalIndex = historicalIndices.length > 0 ? historicalIndices[historicalIndices.length - 1] : -1

        if (lastHistoricalIndex >= 0) {
          // Historical LPPL fit (up to last real data point)
          const historicalLpplDates: string[] = []
          const historicalLpplValues: number[] = []

          validLpplIndices.forEach((idx, i) => {
            if (idx <= lastHistoricalIndex) {
              historicalLpplDates.push(validLpplDates[i])
              historicalLpplValues.push(validLpplValues[i])
            }
          })

          if (historicalLpplValues.length > 0) {
            traces.push({
              x: historicalLpplDates,
              y: historicalLpplValues,
              type: 'scatter',
              mode: 'lines',
              name: 'LPPL Fit - Historical',
              line: {
                color: '#f97316',  // Orange for LPPL fit
                width: 2.5,
                dash: 'solid'
              },
              yaxis: 'y',
              hovertemplate: 'Date: %{x}<br>LPPL log(Price): %{y:.4f}<br>LPPL Price: $%{customdata:.2f}<extra></extra>',
              customdata: historicalLpplValues.map(logP => Math.exp(logP))
            })
          }

          // Future LPPL predictions (if any)
          if (data.dates.length > lastHistoricalIndex + 1) {
            const futureLpplDates: string[] = []
            const futureLpplValues: number[] = []

            validLpplIndices.forEach((idx, i) => {
              if (idx > lastHistoricalIndex) {
                futureLpplDates.push(validLpplDates[i])
                futureLpplValues.push(validLpplValues[i])
              }
            })

            if (futureLpplValues.length > 0) {
              traces.push({
                x: futureLpplDates,
                y: futureLpplValues,
                type: 'scatter',
                mode: 'lines',
                name: 'LPPL Fit - Prediction',
                line: {
                  color: '#f97316',  // Same orange but dashed for future
                  width: 2,
                  dash: 'dash'
                },
                yaxis: 'y',
                hovertemplate: 'Date: %{x}<br>Predicted log(Price): %{y:.4f}<br>Predicted Price: $%{customdata:.2f}<extra></extra>',
                customdata: futureLpplValues.map(logP => Math.exp(logP)),
                showlegend: true
              })
            }
          }
        } else {
          // All LPPL data (no historical prices available)
          traces.push({
            x: validLpplDates,
            y: validLpplValues,
            type: 'scatter',
            mode: 'lines',
            name: 'LPPL Fit',
            line: {
              color: '#f97316',
              width: 2,
              dash: 'solid'
            },
            yaxis: 'y',
            hovertemplate: 'Date: %{x}<br>LPPL log(Price): %{y:.4f}<br>LPPL Price: $%{customdata:.2f}<extra></extra>',
            customdata: validLpplValues.map(logP => Math.exp(logP))
          })
        }
      }
    }

    // 3. Predicted crash date vertical line
    if (data.predicted_crash_date) {
      const logPrices = data.prices.map(p => Math.log(p))
      const minLogPrice = Math.min(...logPrices)
      const maxLogPrice = Math.max(...logPrices)
      const range = maxLogPrice - minLogPrice

      // Add vertical line at crash date
      traces.push({
        x: [data.predicted_crash_date, data.predicted_crash_date],
        y: [minLogPrice - range * 0.1, maxLogPrice + range * 0.1],
        type: 'scatter',
        mode: 'lines',
        name: 'Predicted Crash Date',
        line: {
          color: '#dc2626',  // Red for crash prediction
          width: 2,
          dash: 'dashdot'
        },
        showlegend: true,
        hovertemplate: 'Predicted Crash: %{x}<extra></extra>'
      })
    }

    return traces
  }, [data])

  const layout = useMemo(() => {
    const logPrices = data.prices.map(p => Math.log(p))
    const minLogPrice = Math.min(...logPrices)
    const maxLogPrice = Math.max(...logPrices)
    const logRange = maxLogPrice - minLogPrice
    const padding = logRange * 0.1

    // Calculate nice tick values for log scale
    const minPrice = Math.min(...data.prices)
    const maxPrice = Math.max(...data.prices)
    const priceTickValues: number[] = []
    const priceTickText: string[] = []

    // Generate logarithmically spaced ticks
    const logMin = Math.floor(Math.log10(minPrice))
    const logMax = Math.ceil(Math.log10(maxPrice))

    for (let exp = logMin; exp <= logMax; exp++) {
      for (let mult of [1, 2, 5]) {
        const val = mult * Math.pow(10, exp)
        if (val >= minPrice && val <= maxPrice) {
          priceTickValues.push(Math.log(val))
          priceTickText.push(`$${val.toFixed(val >= 1000 ? 0 : val >= 10 ? 1 : 2)}`)
        }
      }
    }

    return {
      title: showTitle ? {
        text: `${data.symbol} - LPPL Time Series Analysis (Log Scale)`,
        font: {
          color: '#fff',
          size: 18
        }
      } : undefined,
      xaxis: {
        title: 'Date',
        gridcolor: 'rgba(255, 255, 255, 0.1)',
        tickfont: {
          color: '#aaa'
        },
        titlefont: {
          color: '#fff',
          size: 14
        }
      },
      yaxis: {
        title: 'log(Price)',
        gridcolor: 'rgba(255, 255, 255, 0.08)',
        tickfont: {
          color: '#aaa'
        },
        titlefont: {
          color: '#fff',
          size: 14
        },
        range: [minLogPrice - padding, maxLogPrice + padding],
        tickmode: 'array',
        tickvals: priceTickValues,
        ticktext: priceTickText,
        showgrid: true,
        gridwidth: 1,
        minor: {
          showgrid: true,
          gridcolor: 'rgba(255, 255, 255, 0.03)',
          gridwidth: 0.5
        }
      },
      plot_bgcolor: 'rgba(17, 24, 39, 0.95)',
      paper_bgcolor: 'rgba(17, 24, 39, 0.95)',
      hovermode: 'x unified',
      showlegend: true,
      legend: {
        x: 0,
        y: 1,
        bgcolor: 'rgba(0, 0, 0, 0.3)',
        bordercolor: '#444',
        borderwidth: 1,
        font: {
          color: '#fff'
        }
      },
      margin: {
        l: 60,
        r: 30,
        t: showTitle ? 60 : 30,
        b: 60
      },
      annotations: data.predicted_crash_date ? [
        {
          x: data.predicted_crash_date,
          y: Math.log(Math.max(...data.prices)) * 0.98,
          text: `Crash: ${data.predicted_crash_date}`,
          showarrow: true,
          arrowhead: 2,
          ax: 50,
          ay: -30,
          font: {
            color: '#dc2626',
            size: 12
          },
          bgcolor: 'rgba(0, 0, 0, 0.7)',
          bordercolor: '#dc2626',
          borderwidth: 1
        },
        {
          x: data.dates[Math.floor(data.dates.length * 0.7)],
          y: Math.log(Math.min(...data.prices)) * 1.02,
          text: `Confidence: ${(data.confidence * 100).toFixed(1)}%<br>Trust: ${(data.trust * 100).toFixed(1)}%`,
          showarrow: false,
          font: {
            color: '#fff',
            size: 11
          },
          bgcolor: 'rgba(0, 0, 0, 0.7)',
          bordercolor: '#444',
          borderwidth: 1,
          xanchor: 'left',
          yanchor: 'bottom'
        }
      ] : []
    }
  }, [data, showTitle])

  const config = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d', 'autoScale2d']
  }

  return (
    <div className="w-full">
      <Plot
        data={plotData}
        layout={layout}
        config={config}
        style={{ width: '100%', height }}
      />
    </div>
  )
}