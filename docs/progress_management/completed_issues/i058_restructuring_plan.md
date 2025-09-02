# Issue I058: Dashboard Restructuring Implementation Plan

## Current Structure (v1.4)

### Tab Structure
1. **📊 Crash Prediction Data** - `render_prediction_data_tab()`
   - Main scatter plot (Fitting Basis Date vs Predicted Crash Date)
   - Basic data visualization
   
2. **🎯 Prediction Clustering** - `render_crash_clustering_tab()`
   - R²-weighted clustering
   - Clustering parameters (Distance, Min Cluster, Min R², Min Days to Crash)
   - Cluster analysis results table
   
3. **📈 LPPL Fitting Plot** - `render_price_predictions_tab()`
   - Latest Analysis Details
   - Integrated Predictions
   - Individual Fitting Results (limited to 20)
   
4. **📋 Parameters** - `render_parameters_tab()`
   - Parameter table with all LPPL values
   - CSV export functionality
   
5. **📚 References** - `render_references_tab()`
   - Historical benchmarks (1987, 2000)
   - General quality benchmarks

## Target Structure (after I058)

### Tab Structure
1. **📊 Crash Prediction Data** (Enhanced)
   - Main scatter plot (unchanged)
   - + Latest Analysis Details (moved from LPPL Fitting Plot)
   - + Integrated Predictions (moved from LPPL Fitting Plot)
   
2. **🎯 Clustering Analysis** (Renamed & Enhanced)
   - Section 1: Filtering Settings
   - Section 2: Clustering Analysis (existing functionality)
   - Section 3: Individual Results (cluster-based selection)
     - Cluster dropdown selection
     - "Show Individual Fitting Results" button
     - Max 100 results (configurable)
     - Sort by date/R²
   
3. ~~**📈 LPPL Fitting Plot**~~ (DELETED)
   
4. **📋 Parameters** (unchanged)
   
5. **📚 References** (unchanged)

## Key Functions to Move/Modify

### From `render_price_predictions_tab()` to `render_prediction_data_tab()`:
- Lines 1738-1889: Latest Analysis Details
- Lines 1891-2011: Integrated Predictions

### From `render_price_predictions_tab()` to new cluster-based Individual Results:
- Lines 2228-2427: Individual Fitting Results
- Need modification for cluster-based filtering

### Session State Management Changes:
- Add: `selected_cluster_id`
- Add: `individual_results_sort_by` (date/r2)
- Add: `individual_results_max_count`
- Add: `cached_cluster_data`

## API Optimization Strategy:
1. On cluster selection: fetch all data for cluster date range
2. Cache in session state
3. Reuse cache for sorting/filtering changes

## Implementation Phases:
- Phase 1: Backup & Documentation ✅
- Phase 2: Tab structure changes ✅
- Phase 3: Individual Results implementation ✅
- Phase 4: Function moves ✅ (Partially - LPPL tab still commented)
- Phase 5: Testing & optimization (In Progress)