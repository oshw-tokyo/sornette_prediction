import React, { useMemo } from 'react'
import dynamic from 'next/dynamic'
import { FCOAnalysis } from '@/types/fco'

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false })

interface FCOScatterPlotProps {
  data: FCOAnalysis[]
  showNegative?: boolean
}

export const FCOScatterPlot: React.FC<FCOScatterPlotProps> = ({
  data,
  showNegative = false
}) => {
  const { plotData, validDataForLayout } = useMemo(() => {
    if (!data || data.length === 0) return { plotData: [], validDataForLayout: [] }

    // Filter and normalize bubble types
    const filteredData = data.filter(d => {
      const bubbleType = d.bubble_type?.toLowerCase() || ''
      if (showNegative) {
        return bubbleType.includes('negative')
      }
      return bubbleType.includes('positive') || bubbleType === 'weak_positive'
    })

    // Prepare data for plotting - axis reversed as requested
    // Filter out entries without predicted crash date
    const validData = filteredData.filter(d => d.predicted_crash_date && d.predicted_crash_date !== null)

    const xDates = validData.map(d => d.predicted_crash_date)  // X axis: Predicted crash date
    const yDates = validData.map(d => d.analysis_basis_date)   // Y axis: Fitting basis date (reversed)

    // Use appropriate confidence values based on bubble type
    const confidenceValues = validData.map(d =>
      showNegative ?
        (d.ds_lppls_confidence_neg || 0) * 100 :
        (d.ds_lppls_confidence || 0) * 100
    )

    // Get symbols for hover text
    const symbols = validData.map(d => d.symbol)
    const trustValues = validData.map(d =>
      (d.ds_lppls_trust || 0) * 100
    )

    const plot = [{
      x: xDates,
      y: yDates,
      mode: 'markers',
      type: 'scatter',
      marker: {
        size: 12,
        color: confidenceValues,
        colorscale: showNegative ? [
          // Viridis-like gradient for negative bubble (blue to yellow-green)
          [0, '#440154'],    // Very dark purple-blue
          [0.2, '#31688e'],  // Dark blue
          [0.4, '#35b779'],  // Teal-green
          [0.6, '#6ece58'],  // Light green
          [0.8, '#b5de2b'],  // Yellow-green
          [1, '#fde725']     // Bright yellow
        ] : [
          // Viridis gradient for positive bubble (standard scientific colormap)
          [0, '#440154'],    // Very dark purple (low confidence)
          [0.2, '#414487'],  // Dark blue-purple
          [0.4, '#2a788e'],  // Blue
          [0.6, '#22a884'],  // Teal
          [0.8, '#7ad151'],  // Green-yellow
          [1, '#fde725']     // Bright yellow (high confidence)
        ],
        showscale: true,
        // IMPORTANT: Always display 0-100% scale regardless of actual data values
        cmin: 0,  // Always start from 0%
        cmax: 100,  // Always end at 100%
        colorbar: {
          title: showNegative ? 'DS-LPPLS<br>Confidence<br>Negative (%)' : 'DS-LPPLS<br>Confidence (%)',
          titleside: 'right',
          tickmode: 'linear',
          tick0: 0,
          dtick: 20,
          tickvals: [0, 20, 40, 60, 80, 100],  // Explicit tick values
          len: 0.75,
          thickness: 20,
          bgcolor: 'rgba(0, 0, 0, 0.3)',
          bordercolor: '#444',
          borderwidth: 1,
          tickfont: {
            color: '#fff'
          },
          titlefont: {
            color: '#fff'
          }
        },
        line: {
          color: 'rgba(255, 255, 255, 0.2)',
          width: 1
        }
      },
      text: validData.map((d, i) =>
        `Symbol: ${symbols[i]}<br>` +
        `Fitting Date: ${d.analysis_basis_date}<br>` +
        `Predicted Crash: ${d.predicted_crash_date}<br>` +
        `Confidence: ${confidenceValues[i].toFixed(2)}%<br>` +
        `Trust: ${trustValues[i].toFixed(2)}%`
      ),
      hovertemplate: '%{text}<extra></extra>',
      hoverlabel: {
        bgcolor: 'rgba(31, 41, 55, 0.95)',  // Dark gray background for readability
        bordercolor: 'rgba(255, 255, 255, 0.2)',
        font: {
          color: '#fff',
          size: 14
        }
      },
      name: showNegative ? 'Negative Bubble' : 'Positive Bubble'
    }]

    return { plotData: plot, validDataForLayout: validData }
  }, [data, showNegative])

  const layout = useMemo(() => {
    // Use the already filtered validData from plotData calculation
    if (!validDataForLayout || validDataForLayout.length === 0) {
      return {
        title: {
          text: 'No valid data for visualization',
          font: { color: '#fff', size: 20 }
        },
        plot_bgcolor: 'rgba(17, 24, 39, 0.95)',
        paper_bgcolor: 'rgba(17, 24, 39, 0.95)',
      }
    }

    const allXDates = validDataForLayout.map(d => new Date(d.predicted_crash_date!).getTime())
    const allYDates = validDataForLayout.map(d => new Date(d.analysis_basis_date).getTime())

    const minDate = Math.min(...allXDates, ...allYDates)
    const maxDate = Math.max(...allXDates, ...allYDates)

    // Add padding to the date range (5% on each side to prevent point clipping)
    const dateRange = maxDate - minDate
    const padding = dateRange * 0.05
    const paddedMinDate = minDate - padding
    const paddedMaxDate = maxDate + padding

    const minDateStr = new Date(minDate).toISOString().split('T')[0]
    const maxDateStr = new Date(maxDate).toISOString().split('T')[0]
    const paddedMinDateStr = new Date(paddedMinDate).toISOString().split('T')[0]
    const paddedMaxDateStr = new Date(paddedMaxDate).toISOString().split('T')[0]

    return {
      title: {
        text: showNegative ?
          'FCO Analysis - Negative Bubble Predictions' :
          'FCO Analysis - Positive Bubble Predictions',
        font: {
          color: '#fff',
          size: 20
        }
      },
      // IMPORTANT: Maintain 1:1 aspect ratio for proper data visualization
      // The square aspect ensures equal scale on both axes for accurate visual comparison
      // DO NOT change scaleanchor/scaleratio as it maintains data integrity
      xaxis: {
        title: 'Predicted Crash Date',
        gridcolor: 'rgba(255, 255, 255, 0.1)',
        zerolinecolor: 'rgba(255, 255, 255, 0.2)',
        tickfont: {
          color: '#aaa'
        },
        titlefont: {
          color: '#fff',
          size: 14
        },
        range: [paddedMinDateStr, paddedMaxDateStr],  // Set explicit range with padding
        scaleanchor: 'y',  // Link X axis scale to Y axis
        scaleratio: 1,     // 1:1 aspect ratio
        constrain: 'domain'  // Constrain the aspect ratio
      },
      yaxis: {
        title: 'Fitting Basis Date',
        gridcolor: 'rgba(255, 255, 255, 0.1)',
        zerolinecolor: 'rgba(255, 255, 255, 0.2)',
        tickfont: {
          color: '#aaa'
        },
        titlefont: {
          color: '#fff',
          size: 14
        },
        range: [paddedMinDateStr, paddedMaxDateStr],  // Set same range as X axis with padding
        constrain: 'domain'  // Constrain the aspect ratio
      },
      plot_bgcolor: 'rgba(17, 24, 39, 0.95)',
      paper_bgcolor: 'rgba(17, 24, 39, 0.95)',
      hovermode: 'closest',
      showlegend: false,
      // Responsive square aspect ratio
      autosize: true,
      margin: {
        l: 80,
        r: 120,
        t: 80,
        b: 80
      },
      shapes: [
        // Reference line where fitting date = crash date
        {
          type: 'line',
          x0: minDateStr,
          y0: minDateStr,
          x1: maxDateStr,
          y1: maxDateStr,
          line: {
            color: 'rgba(255, 255, 255, 0.3)',
            width: 2,
            dash: 'dash'
          }
        }
      ],
      annotations: [
        {
          text: 'Fitting Date = Crash Date',
          x: maxDateStr,
          y: maxDateStr,
          xref: 'x',
          yref: 'y',
          showarrow: false,
          font: {
            color: 'rgba(255, 255, 255, 0.5)',
            size: 12
          },
          xanchor: 'right',
          yanchor: 'bottom'
        }
      ]
    }
  }, [validDataForLayout, showNegative])

  const config = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d', 'autoScale2d']
  }

  return (
    // IMPORTANT: Square container maintains 1:1 aspect ratio for data visualization integrity
    // max-w-4xl prevents excessive width while aspect-square ensures square plot area
    <div className="w-full flex justify-center">
      <div className="w-full max-w-4xl aspect-square">
        {plotData.length > 0 ? (
          <Plot
            data={plotData}
            layout={layout}
            config={config}
            style={{ width: '100%', height: '100%' }}
          />
        ) : (
          <div className="flex items-center justify-center h-full min-h-[600px]">
            <p className="text-gray-400">No data available for visualization</p>
          </div>
        )}
      </div>
    </div>
  )
}