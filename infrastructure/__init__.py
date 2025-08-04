"""
Infrastructure Layer - Support Systems and Utilities

This package contains all infrastructure and support systems that provide
services to both the protected core and the applications layer.

🔍 REPLACEABLE: This layer can be modified or replaced without affecting 
the scientific integrity of the core system.

Components:
    data_sources/: Market data acquisition and API clients
    database/: Data persistence and retrieval systems
    visualization/: Chart generation and plotting utilities
    config/: System configuration and settings management
    monitoring/: System monitoring and health checks

Design Philosophy:
    - Provides services to other layers
    - Can be replaced with alternative implementations
    - Maintains clear interfaces for layer independence
    - Supports both core validation and application functionality
"""

# Infrastructure layer version
__version__ = "1.0.0-replaceable"
__layer_type__ = "INFRASTRUCTURE_SERVICES"
__replaceability__ = "HIGH"