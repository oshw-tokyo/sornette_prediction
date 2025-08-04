"""
Sornette Theory - Pure Mathematical Implementation
Pure LPPL (Log-Periodic Power Law) theory implementation based on Sornette papers.
"""

from .lppl_model import logarithm_periodic_func, power_law_func
from .theory_validation import validate_sornette_parameters

__all__ = [
    'logarithm_periodic_func',
    'power_law_func', 
    'validate_sornette_parameters'
]