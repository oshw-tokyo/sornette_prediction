"""
Entry Points - Central Command Interface

This package provides unified entry points for all system operations,
creating a consistent interface for users and automation systems.

🎯 COMMAND_INTERFACE: Central access point for all system functionality

Components:
    main.py: Main CLI interface with subcommands
    dashboard.py: Dashboard launcher  
    scheduler.py: Analysis scheduler interface
    validator.py: Validation runner
    analyzer.py: Analysis runner

Usage:
    python entry_points/main.py [command] [options]
    python entry_points/dashboard.py
    python entry_points/scheduler.py [symbol]
    python entry_points/validator.py
    python entry_points/analyzer.py [symbol]

Design:
    - Unified command-line interface
    - Clear separation of concerns
    - Easy navigation for both users and AI
"""

__version__ = "1.0.0-unified-interface"
__interface_type__ = "CENTRAL_COMMAND"