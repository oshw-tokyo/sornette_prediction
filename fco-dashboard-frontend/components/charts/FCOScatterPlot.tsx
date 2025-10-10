import React, { useMemo } from 'react'
import dynamic from 'next/dynamic'
import { FCOAnalysis } from '@/types/fco'

// Dynamically import Plotly to avoid SSR issues
const Plot = dynamic(() => import('react-plotly.js'), { ssr: false })

interface FCOScatterPlotProps {
  data: FCOAnalysis[]
  onPointClick?: (analysisId: number) => void
}

export const FCOScatterPlot: React.FC<FCOScatterPlotProps> = ({
  data,
  onPointClick
}) => {
  const { plotData, validDataForLayout, analysisIds } = useMemo(() => {
    if (!data || data.length === 0) return { plotData: [], validDataForLayout: [], analysisIds: [] }

    // Show all data - no filtering by bubble type
    // Filter out entries without predicted crash date
    const validData = data.filter(d => d.predicted_crash_date && d.predicted_crash_date !== null)

    // Store analysis IDs for click handling
    const ids = validData.map(d => d.id)

    // Separate positive and negative bubbles
    const positiveData = validData.filter(d => {
      const bubbleType = d.bubble_type?.toLowerCase() || ''
      return bubbleType.includes('positive') || !d.bubble_type
    })

    const negativeData = validData.filter(d => {
      const bubbleType = d.bubble_type?.toLowerCase() || ''
      return bubbleType.includes('negative')
    })

    // Create traces for each bubble type
    const traces: any[] = []

    // Positive bubble trace (circles)
    if (positiveData.length > 0) {
      const xDatesPos = positiveData.map(d => d.predicted_crash_date)
      const yDatesPos = positiveData.map(d => d.analysis_basis_date)
      const confidencePos = positiveData.map(d => (d.ds_lppls_confidence || 0) * 100)
      const symbolsPos = positiveData.map(d => d.symbol)
      const trustPos = positiveData.map(d => (d.ds_lppls_trust || 0) * 100)

      traces.push({
        x: xDatesPos,
        y: yDatesPos,
        mode: 'markers',
        type: 'scatter',
        marker: {
          size: 12,
          symbol: 'circle',  // Circle for positive bubbles
          color: confidencePos,
          colorscale: [
            [0, '#440154'],    // Very dark purple (low confidence)
            [0.2, '#414487'],  // Dark blue-purple
            [0.4, '#2a788e'],  // Blue
            [0.6, '#22a884'],  // Teal
            [0.8, '#7ad151'],  // Green-yellow
            [1, '#fde725']     // Bright yellow (high confidence)
          ],
          showscale: true,
          cmin: 0,
          cmax: 100,
          colorbar: {
            title: 'DS-LPPLS<br>Confidence (%)',
            titleside: 'right',
            tickmode: 'linear',
            tick0: 0,
            dtick: 20,
            tickvals: [0, 20, 40, 60, 80, 100],
            len: 0.75,
            thickness: 20,
            bgcolor: 'rgba(0, 0, 0, 0.3)',
            bordercolor: '#444',
            borderwidth: 1,
            tickfont: { color: '#fff' },
            titlefont: { color: '#fff' }
          },
          line: {
            color: 'rgba(255, 255, 255, 0.2)',
            width: 1
          }
        },
        text: positiveData.map((d, i) =>
          `Symbol: ${symbolsPos[i]}<br>` +
          `Type: Positive Bubble<br>` +
          `Fitting Date: ${d.analysis_basis_date}<br>` +
          `Predicted Crash: ${d.predicted_crash_date}<br>` +
          `Confidence: ${confidencePos[i].toFixed(2)}%<br>` +
          `Trust: ${trustPos[i].toFixed(2)}%`
        ),
        hovertemplate: '%{text}<extra></extra>',
        hoverlabel: {
          bgcolor: 'rgba(31, 41, 55, 0.95)',
          bordercolor: 'rgba(255, 255, 255, 0.2)',
          font: { color: '#fff', size: 14 }
        },
        name: 'Positive Bubble (○)'
      })
    }

    // Negative bubble trace (squares)
    if (negativeData.length > 0) {
      const xDatesNeg = negativeData.map(d => d.predicted_crash_date)
      const yDatesNeg = negativeData.map(d => d.analysis_basis_date)
      const confidenceNeg = negativeData.map(d => (d.ds_lppls_confidence_neg || 0) * 100)
      const symbolsNeg = negativeData.map(d => d.symbol)
      const trustNeg = negativeData.map(d => (d.ds_lppls_trust || 0) * 100)

      traces.push({
        x: xDatesNeg,
        y: yDatesNeg,
        mode: 'markers',
        type: 'scatter',
        marker: {
          size: 12,
          symbol: 'square',  // Square for negative bubbles
          color: confidenceNeg,
          colorscale: [
            [0, '#440154'],
            [0.2, '#31688e'],
            [0.4, '#35b779'],
            [0.6, '#6ece58'],
            [0.8, '#b5de2b'],
            [1, '#fde725']
          ],
          showscale: false,  // Don't show second colorbar
          cmin: 0,
          cmax: 100,
          line: {
            color: 'rgba(255, 255, 255, 0.2)',
            width: 1
          }
        },
        text: negativeData.map((d, i) =>
          `Symbol: ${symbolsNeg[i]}<br>` +
          `Type: Negative Bubble<br>` +
          `Fitting Date: ${d.analysis_basis_date}<br>` +
          `Predicted Crash: ${d.predicted_crash_date}<br>` +
          `Confidence (Neg): ${confidenceNeg[i].toFixed(2)}%<br>` +
          `Trust: ${trustNeg[i].toFixed(2)}%`
        ),
        hovertemplate: '%{text}<extra></extra>',
        hoverlabel: {
          bgcolor: 'rgba(31, 41, 55, 0.95)',
          bordercolor: 'rgba(255, 255, 255, 0.2)',
          font: { color: '#fff', size: 14 }
        },
        name: 'Negative Bubble (□)'
      })
    }

    return { plotData: traces, validDataForLayout: validData, analysisIds: ids }
  }, [data])

  // Handle point click
  const handlePlotClick = (event: any) => {
    if (!onPointClick || !event.points || event.points.length === 0) return

    const pointIndex = event.points[0].pointIndex
    if (pointIndex !== undefined && analysisIds && analysisIds[pointIndex] !== undefined) {
      onPointClick(analysisIds[pointIndex])
    }
  }

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
        text: 'FCO Analysis - Bubble Predictions',
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
  }, [validDataForLayout])

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
            onClick={handlePlotClick}
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