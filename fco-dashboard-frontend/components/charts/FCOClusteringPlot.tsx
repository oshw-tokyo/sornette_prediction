import React, { useMemo, useState } from 'react'
import dynamic from 'next/dynamic'
import { FCOAnalysis } from '@/types/fco'

const Plot = dynamic(() => import('react-plotly.js'), { ssr: false })

interface ClusterResult {
  clusterId: number
  points: FCOAnalysis[]
  centerX: number
  centerY: number
  avgConfidence: number
}

interface FCOClusteringPlotProps {
  data: FCOAnalysis[]
}

export const FCOClusteringPlot: React.FC<FCOClusteringPlotProps> = ({
  data
}) => {
  const [selectedCluster, setSelectedCluster] = useState<number | null>(null)
  const [minClusterSize, setMinClusterSize] = useState(3)
  const [maxClusterDistance, setMaxClusterDistance] = useState(30)  // in days
  const [confidenceThreshold, setConfidenceThreshold] = useState(0.3)  // 30% minimum confidence

  const clusters = useMemo(() => {
    if (!data || data.length === 0) return []

    // Filter out data without required fields and apply confidence threshold
    const validData = data.filter(d =>
      d.predicted_crash_date &&
      d.analysis_basis_date &&
      d.ds_lppls_confidence !== null &&
      d.ds_lppls_confidence >= confidenceThreshold
    )

    if (validData.length === 0) return []

    // Convert dates to timestamps for clustering
    const points = validData.map(d => ({
      ...d,
      xTime: new Date(d.predicted_crash_date!).getTime(),
      yTime: new Date(d.analysis_basis_date!).getTime()
    }))

    // Simple density-based clustering
    const clusters: ClusterResult[] = []
    const visited = new Set<number>()
    const msPerDay = 24 * 60 * 60 * 1000
    const maxDistanceMs = maxClusterDistance * msPerDay

    for (let i = 0; i < points.length; i++) {
      if (visited.has(i)) continue

      const cluster: typeof points = []
      const stack = [i]

      while (stack.length > 0) {
        const idx = stack.pop()!
        if (visited.has(idx)) continue

        visited.add(idx)
        cluster.push(points[idx])

        // Find neighbors within distance
        for (let j = 0; j < points.length; j++) {
          if (visited.has(j)) continue

          const distX = Math.abs(points[idx].xTime - points[j].xTime)
          const distY = Math.abs(points[idx].yTime - points[j].yTime)
          const distance = Math.sqrt(distX * distX + distY * distY)

          if (distance <= maxDistanceMs) {
            stack.push(j)
          }
        }
      }

      if (cluster.length >= minClusterSize) {
        // Calculate cluster center (weighted by confidence)
        const totalConfidence = cluster.reduce((sum, p) => sum + (p.ds_lppls_confidence || 0), 0)
        const centerX = cluster.reduce((sum, p) => sum + p.xTime * (p.ds_lppls_confidence || 0), 0) / totalConfidence
        const centerY = cluster.reduce((sum, p) => sum + p.yTime * (p.ds_lppls_confidence || 0), 0) / totalConfidence
        const avgConfidence = totalConfidence / cluster.length

        clusters.push({
          clusterId: clusters.length,
          points: cluster,
          centerX,
          centerY,
          avgConfidence: avgConfidence * 100
        })
      }
    }

    return clusters.sort((a, b) => b.avgConfidence - a.avgConfidence)
  }, [data, minClusterSize, maxClusterDistance, confidenceThreshold])

  const plotData = useMemo(() => {
    const traces: any[] = []

    // Define color palette for clusters
    const colors = [
      '#ff6b6b', // Red
      '#4ecdc4', // Teal
      '#45b7d1', // Blue
      '#96ceb4', // Green
      '#feca57', // Yellow
      '#fd79a8', // Pink
      '#a29bfe', // Purple
      '#00b894', // Emerald
    ]

    clusters.forEach((cluster, idx) => {
      const color = colors[idx % colors.length]
      const isSelected = selectedCluster === cluster.clusterId

      // Add cluster points
      traces.push({
        x: cluster.points.map(p => p.predicted_crash_date),
        y: cluster.points.map(p => p.analysis_basis_date),
        mode: 'markers',
        type: 'scatter',
        name: `Cluster ${cluster.clusterId + 1}`,
        marker: {
          size: isSelected ? 14 : 10,
          color: cluster.points.map(p => (p.ds_lppls_confidence || 0) * 100),
          colorscale: [[0, color], [1, color]],
          opacity: isSelected ? 1 : 0.6,
          line: {
            color: isSelected ? '#fff' : color,
            width: isSelected ? 2 : 1
          }
        },
        text: cluster.points.map(p =>
          `Symbol: ${p.symbol}<br>` +
          `Cluster: ${cluster.clusterId + 1}<br>` +
          `Fitting: ${p.analysis_basis_date}<br>` +
          `Predicted: ${p.predicted_crash_date}<br>` +
          `Confidence: ${((p.ds_lppls_confidence || 0) * 100).toFixed(2)}%`
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
        legendgroup: `cluster${cluster.clusterId}`,
        showlegend: true
      })

      // Add cluster center as vertical line spanning entire plot
      const centerDate = new Date(cluster.centerX)
      const centerDateStr = centerDate.toISOString().split('T')[0]

      // Get overall Y range from ALL data points for consistent vertical lines
      const allYDates = data
        .filter(d => d.analysis_basis_date)
        .map(d => new Date(d.analysis_basis_date!).getTime())

      if (allYDates.length > 0) {
        const globalMinY = new Date(Math.min(...allYDates))
        const globalMaxY = new Date(Math.max(...allYDates))

        // Add vertical line for cluster center spanning full height
        traces.push({
          x: [centerDateStr, centerDateStr],
          y: [globalMinY.toISOString().split('T')[0], globalMaxY.toISOString().split('T')[0]],
          mode: 'lines',
          type: 'scatter',
          name: `Center ${cluster.clusterId + 1}`,
          line: {
            color,
            width: 3,
            dash: 'dashdot'
          },
          hovertemplate:
            `Cluster ${cluster.clusterId + 1} Center<br>` +
            `Predicted Crash: ${centerDateStr}<br>` +
            `${cluster.points.length} predictions<br>` +
            `Avg Confidence: ${cluster.avgConfidence.toFixed(2)}%<extra></extra>`,
          legendgroup: `cluster${cluster.clusterId}`,
          showlegend: false
        })
      }
    })

    // Add unclustered points
    const clusteredIndices = new Set(
      clusters.flatMap(c => c.points.map(p => data.indexOf(p)))
    )
    const unclusteredPoints = data.filter((_, idx) => !clusteredIndices.has(idx))

    if (unclusteredPoints.length > 0) {
      traces.push({
        x: unclusteredPoints.map(p => p.predicted_crash_date),
        y: unclusteredPoints.map(p => p.analysis_basis_date),
        mode: 'markers',
        type: 'scatter',
        name: 'Isolated Points',
        marker: {
          size: 8,
          color: 'rgba(255, 255, 255, 0.3)',
          line: {
            color: 'rgba(255, 255, 255, 0.1)',
            width: 1
          }
        },
        text: unclusteredPoints.map(p =>
          `Symbol: ${p.symbol}<br>` +
          `Isolated Point<br>` +
          `Fitting: ${p.analysis_basis_date}<br>` +
          `Predicted: ${p.predicted_crash_date}<br>` +
          `Confidence: ${((p.ds_lppls_confidence || 0) * 100).toFixed(2)}%`
        ),
        hovertemplate: '%{text}<extra></extra>',
        hoverlabel: {
          bgcolor: 'rgba(31, 41, 55, 0.95)',  // Dark gray background for readability
          bordercolor: 'rgba(255, 255, 255, 0.2)',
          font: {
            color: '#fff',
            size: 14
          }
        }
      })
    }

    return traces
  }, [clusters, data, selectedCluster])

  const layout = useMemo(() => {
    // Calculate date range
    const allXDates = data.map(d => new Date(d.predicted_crash_date).getTime())
    const allYDates = data.map(d => new Date(d.analysis_basis_date).getTime())

    const minDate = Math.min(...allXDates, ...allYDates)
    const maxDate = Math.max(...allXDates, ...allYDates)

    // Add padding to the date range (5% on each side to prevent point clipping)
    // This ensures cluster centers (star markers) and edge points are fully visible
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
        text: 'FCO Clustering Analysis - Prediction Convergence',
        font: {
          color: '#fff',
          size: 20
        }
      },
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
      showlegend: true,
      legend: {
        x: 1.02,
        y: 1,
        bgcolor: 'rgba(0, 0, 0, 0.5)',
        bordercolor: '#444',
        borderwidth: 1,
        font: {
          color: '#fff'
        }
      },
      // Responsive square aspect ratio
      autosize: true,
      margin: {
        l: 80,
        r: 200,
        t: 80,
        b: 80
      },
      shapes: [
        // Reference line
        {
          type: 'line',
          x0: minDateStr,
          y0: minDateStr,
          x1: maxDateStr,
          y1: maxDateStr,
          line: {
            color: 'rgba(255, 255, 255, 0.2)',
            width: 1,
            dash: 'dot'
          }
        }
      ]
    }
  }, [data])

  const config = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['pan2d', 'select2d', 'lasso2d']
  }

  return (
    <div className="w-full">
      {/* Clustering Parameters Control */}
      <div className="mb-6 p-4 bg-gray-800 rounded-lg border border-gray-700">
        <h3 className="text-lg font-semibold mb-4 text-white">Clustering Parameters</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Cluster Distance (days)
            </label>
            <input
              type="range"
              min="10"
              max="90"
              value={maxClusterDistance}
              onChange={(e) => setMaxClusterDistance(parseInt(e.target.value))}
              className="w-full"
            />
            <span className="text-xs text-gray-400">{maxClusterDistance} days</span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Min Cluster Size
            </label>
            <input
              type="range"
              min="2"
              max="10"
              value={minClusterSize}
              onChange={(e) => setMinClusterSize(parseInt(e.target.value))}
              className="w-full"
            />
            <span className="text-xs text-gray-400">{minClusterSize} points</span>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">
              Min Confidence
            </label>
            <input
              type="range"
              min="0"
              max="0.9"
              step="0.1"
              value={confidenceThreshold}
              onChange={(e) => setConfidenceThreshold(parseFloat(e.target.value))}
              className="w-full"
            />
            <span className="text-xs text-gray-400">{(confidenceThreshold * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* Cluster Statistics */}
      <div className="mb-4 p-4 bg-gray-800 rounded-lg">
        <h3 className="text-lg font-semibold mb-2 text-white">Cluster Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-gray-400 text-sm">Total Clusters</p>
            <p className="text-2xl font-bold text-blue-400">{clusters.length}</p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Clustered Points</p>
            <p className="text-2xl font-bold text-green-400">
              {clusters.reduce((sum, c) => sum + c.points.length, 0)}
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Best Cluster Confidence</p>
            <p className="text-2xl font-bold text-yellow-400">
              {clusters.length > 0 ? `${clusters[0].avgConfidence.toFixed(1)}%` : 'N/A'}
            </p>
          </div>
          <div>
            <p className="text-gray-400 text-sm">Total Valid Points</p>
            <p className="text-2xl font-bold text-purple-400">
              {data.filter(d => d.ds_lppls_confidence && d.ds_lppls_confidence >= confidenceThreshold).length}
            </p>
          </div>
        </div>
      </div>

      {/* Plot */}
      {/* IMPORTANT: Square container with mb-6 margin prevents overlap with table below */}
      <div className="w-full flex justify-center mb-6">
        <div className="w-full max-w-4xl aspect-square">
          {plotData.length > 0 ? (
            <Plot
              data={plotData}
              layout={layout}
              config={config}
              style={{ width: '100%', height: '100%' }}
              onHover={(event: any) => {
                if (event.points && event.points[0]) {
                  const point = event.points[0]
                  const clusterMatch = point.data.name?.match(/Cluster (\d+)/)
                  if (clusterMatch) {
                    setSelectedCluster(parseInt(clusterMatch[1]) - 1)
                  }
                }
              }}
              onUnhover={() => setSelectedCluster(null)}
            />
          ) : (
            <div className="flex items-center justify-center h-full min-h-[600px]">
              <p className="text-gray-400">No data available for clustering</p>
            </div>
          )}
        </div>
      </div>

      {/* Cluster Details Table */}
      {clusters.length > 0 && (
        <div className="mt-4 p-4 bg-gray-800 rounded-lg">
          <h3 className="text-lg font-semibold mb-2 text-white">Cluster Details</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left text-gray-300">
              <thead className="text-xs uppercase bg-gray-700">
                <tr>
                  <th className="px-4 py-2">Cluster</th>
                  <th className="px-4 py-2">Size</th>
                  <th className="px-4 py-2">Avg Confidence</th>
                  <th className="px-4 py-2">Center Date</th>
                  <th className="px-4 py-2">Days to Crash</th>
                  <th className="px-4 py-2">Symbols</th>
                </tr>
              </thead>
              <tbody>
                {clusters.map((cluster, idx) => {
                  const centerDate = new Date(cluster.centerX)
                  const today = new Date()
                  const daysToCenter = Math.round((centerDate.getTime() - today.getTime()) / (24 * 60 * 60 * 1000))
                  const symbols = [...new Set(cluster.points.map(p => p.symbol))].join(', ')

                  return (
                    <tr key={idx} className="border-b border-gray-700 hover:bg-gray-700">
                      <td className="px-4 py-2 font-medium">{idx + 1}</td>
                      <td className="px-4 py-2">{cluster.points.length}</td>
                      <td className="px-4 py-2">{cluster.avgConfidence.toFixed(2)}%</td>
                      <td className="px-4 py-2">{centerDate.toISOString().split('T')[0]}</td>
                      <td className="px-4 py-2">
                        <span className={daysToCenter < 30 ? 'text-red-400' : daysToCenter < 90 ? 'text-yellow-400' : 'text-green-400'}>
                          {daysToCenter} days
                        </span>
                      </td>
                      <td className="px-4 py-2 text-xs">{symbols}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}