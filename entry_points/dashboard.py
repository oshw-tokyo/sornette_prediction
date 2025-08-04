#!/usr/bin/env python3
"""
Dashboard Launcher - Quick Dashboard Access

🖥️ Quick launcher for Streamlit dashboards

Usage:
    python entry_points/dashboard.py [--symbol-view]
    python entry_points/dashboard.py [--main-view]
"""

import argparse
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def launch_symbol_dashboard():
    """Launch symbol-specific dashboard"""
    print("🚀 Launching Symbol Visualization Dashboard...")
    print("📊 URL: http://localhost:8501")
    
    subprocess.run([
        sys.executable, '-m', 'streamlit', 'run',
        'applications/dashboards/symbol_dashboard.py',
        '--server.port', '8501'
    ])

def launch_main_dashboard():
    """Launch main analysis dashboard"""
    print("🚀 Launching Main Analysis Dashboard...")  
    print("📊 URL: http://localhost:8502")
    
    subprocess.run([
        sys.executable, '-m', 'streamlit', 'run',
        'applications/dashboards/main_dashboard.py',
        '--server.port', '8502'
    ])

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Dashboard Launcher - Quick Dashboard Access"
    )
    
    parser.add_argument('--symbol-view', action='store_true',
                       help='Launch symbol-specific dashboard (default)')
    parser.add_argument('--main-view', action='store_true', 
                       help='Launch main analysis dashboard')
    
    args = parser.parse_args()
    
    if args.main_view:
        launch_main_dashboard()
    else:  # Default to symbol dashboard
        launch_symbol_dashboard()

if __name__ == "__main__":
    main()