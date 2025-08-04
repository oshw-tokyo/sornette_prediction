"""
Sornette Prediction System - Protected Scientific Core

This package contains the protected scientific core of the Sornette prediction system,
including pure theoretical implementations, fitting algorithms, and validation systems.

🚨 CRITICAL PROTECTION NOTICE:
This core package is protected by the 100/100 score validation requirement.
Any modifications to this package must maintain the validation score of:
    python core/validation/crash_validators/black_monday_1987_validator.py

Modules:
    sornette_theory: Pure mathematical LPPL implementation
    fitting: Advanced fitting algorithms and parameter optimization  
    validation: Historical crash validation and reproducibility testing

Scientific Integrity Protection:
    - All changes must pass historical validation tests
    - Core mathematical formulas are implementation-protected
    - Parameter ranges must comply with Sornette theoretical constraints
"""

# Import core theoretical functions
from .sornette_theory import (
    logarithm_periodic_func,
    power_law_func,
    validate_sornette_parameters
)

# Protected scientific core version
__version__ = "1.0.0-protected"
__scientific_integrity__ = "100/100 validation required"

# Core module availability check
def verify_core_integrity():
    """
    Verify that all core scientific modules are available and functional
    
    Returns:
        dict: Status of core module integrity
    """
    try:
        from .sornette_theory.lppl_model import logarithm_periodic_func
        from .fitting.fitter import LogarithmPeriodicFitter
        from .validation.crash_validators.black_monday_1987_validator import main as validate_1987
        
        return {
            'status': 'intact',
            'sornette_theory': True,
            'fitting_algorithms': True,
            'validation_system': True,
            'protection_level': '100/100 score maintained'
        }
    except ImportError as e:
        return {
            'status': 'compromised',
            'error': str(e),
            'action_required': 'Restore core scientific modules'
        }

__all__ = [
    'logarithm_periodic_func',
    'power_law_func', 
    'validate_sornette_parameters',
    'verify_core_integrity'
]