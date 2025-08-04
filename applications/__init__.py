"""
Applications Layer - User-Facing Functionality

This package contains all user-facing applications built on top of the
protected scientific core, including schedulers, dashboards, analysis tools, and examples.

🔧 MODIFIABLE: This layer can be changed without affecting scientific integrity

Components:
    schedulers/: Analysis scheduling and automation
    dashboards/: Web-based user interfaces  
    analysis_tools/: Market analysis applications
    examples/: Demonstration and tutorial code

Flexibility:
    Unlike the protected core/, this layer is designed for:
    - User interface improvements
    - New analysis workflows
    - Additional scheduling options
    - Enhanced visualization features
"""

# Application layer version
__version__ = "1.0.0-flexible"
__layer_type__ = "USER_FACING_APPLICATIONS"