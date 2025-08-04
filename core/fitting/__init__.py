"""
Core Fitting Algorithms - Protected Scientific Implementation

This package contains the advanced LPPL fitting algorithms, parameter optimization,
and quality evaluation systems that form the computational core of crash prediction.

🚨 PROTECTED: Changes to this package must maintain 100/100 validation score

Main Components:
    - LogarithmPeriodicFitter: Core LPPL fitting engine
    - Multi-criteria selection system: Advanced parameter candidate evaluation
    - Quality assessment framework: Statistical significance and fit quality evaluation

Scientific Protection:
    All fitting algorithms in this package are protected by historical validation
    requirements and must maintain reproducibility of known crash predictions.
"""

from .fitter import LogarithmPeriodicFitter, FittingResult
from .multi_criteria_selection import (
    FittingCandidate,
    SelectionResult, 
    MultiCriteriaSelector
)
from .fitting_quality_evaluator import (
    FittingQualityEvaluator,
    QualityAssessment,
    FittingQuality
)

__all__ = [
    'LogarithmPeriodicFitter',
    'FittingResult',
    'FittingCandidate', 
    'SelectionResult',
    'MultiCriteriaSelector',
    'FittingQualityEvaluator',
    'QualityAssessment',
    'FittingQuality'
]

# Protected fitting system version
__version__ = "2.0.0-protected"
__protection_status__ = "100/100 validation maintained"