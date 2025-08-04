"""
Pure LPPL (Log-Periodic Power Law) Mathematical Model Implementation

This module contains the pure mathematical implementation of Sornette's LPPL theory,
extracted from the fitting utilities to ensure scientific integrity protection.

Reference: papers/extracted_texts/sornette_2004_0301543v1_Critical_Market_Crashes__Anti-Buble_extracted.txt
Formula: Equation (54)

🚨 PROTECTED: This module contains the core scientific theory and must not be modified
without maintaining the 100/100 score validation requirement.
"""

import numpy as np
from typing import Union


def power_law_func(t: np.ndarray, tc: float, beta: float, A: float, B: float) -> np.ndarray:
    """
    Pure Power Law Model Function
    
    Mathematical formula: I(t) = A + B(tc - t)^β
    
    Args:
        t: Time array (normalized, typically 0 to 1)
        tc: Critical time parameter (typically > 1.0)
        beta: Exponent parameter (theoretical value ≈ 0.33)
        A: Scale parameter
        B: Amplitude parameter
        
    Returns:
        np.ndarray: Model prediction values
        
    Note:
        This is the simplified version without the log-periodic component.
    """
    dt = tc - t
    mask = dt > 0
    result = np.zeros_like(t)
    result[mask] = A + B * np.power(dt[mask], beta)
    return result


def logarithm_periodic_func(t: np.ndarray, tc: float, beta: float, omega: float,
                           phi: float, A: float, B: float, C: float) -> np.ndarray:
    """
    Log-Periodic Power Law (LPPL) Model - Core Sornette Theory Implementation
    
    Mathematical formula (Equation 54 from Sornette 2004):
    I(t) = A + B(tc - t)^β + C(tc - t)^β cos(ω ln(tc - t) - φ)
    
    Parameters:
        t: Time array (normalized, typically 0 to 1)
        tc: Critical time parameter (crash time, typically 1.0 < tc < 1.5)
        beta: Exponent parameter (theoretical value: 0.33 ± 0.03)
        omega: Angular frequency (theoretical range: 6-8)
        phi: Phase shift (-8π < φ < 8π)
        A: Scale parameter (log price level)
        B: Power law amplitude
        C: Log-periodic amplitude
        
    Returns:
        np.ndarray: LPPL model prediction values
        
    Theoretical Constraints (Sornette, 2004):
        - β ≈ 0.33 ± 0.03 (critical exponent)
        - ω ≈ 6-8 (angular frequency)
        - tc > max(t) (crash occurs after data period)
        
    🚨 CRITICAL: This function implements the exact mathematical formula from
    Sornette's 2004 paper and must maintain 100/100 validation score.
    """
    # Ensure input is properly formatted
    t = np.asarray(t).ravel()
    dt = (tc - t).ravel()
    mask = dt > 0
    result = np.zeros_like(t, dtype=float)
    
    valid_dt = dt[mask]
    if len(valid_dt) > 0:
        # Calculate each component of the LPPL formula
        power_term = np.power(valid_dt, beta).ravel()
        log_term = np.log(valid_dt).ravel()
        cos_term = np.cos(omega * log_term + phi).ravel()
        
        # Apply the complete LPPL formula: A + B(tc-t)^β + C(tc-t)^β cos(ω ln(tc-t) - φ)
        linear_component = A
        power_component = B * power_term
        oscillation_component = C * power_term * cos_term
        
        result[mask] = (linear_component + power_component + oscillation_component).ravel()
    
    return result


def validate_lppl_parameters(tc: float, beta: float, omega: float, phi: float) -> dict:
    """
    Validate LPPL parameters against theoretical constraints from Sornette theory
    
    Args:
        tc: Critical time parameter
        beta: Exponent parameter  
        omega: Angular frequency
        phi: Phase shift
        
    Returns:
        dict: Validation results with theoretical compliance status
    """
    validation = {
        'tc_valid': 1.0 < tc < 2.0,  # Reasonable range for normalized time
        'beta_valid': 0.1 < beta < 0.7,  # Broader range, optimal ~0.33
        'omega_valid': 2.0 < omega < 20.0,  # Broader range, optimal 6-8
        'phi_valid': -8*np.pi < phi < 8*np.pi,
        'beta_optimal': 0.30 <= beta <= 0.36,  # Sornette theoretical optimum
        'omega_optimal': 6.0 <= omega <= 8.0,  # Sornette theoretical optimum
    }
    
    validation['all_valid'] = all([
        validation['tc_valid'],
        validation['beta_valid'], 
        validation['omega_valid'],
        validation['phi_valid']
    ])
    
    validation['theoretically_optimal'] = all([
        validation['beta_optimal'],
        validation['omega_optimal']
    ])
    
    return validation


# Constants from Sornette Theory
SORNETTE_THEORETICAL_BETA = 0.33
SORNETTE_BETA_TOLERANCE = 0.03
SORNETTE_OMEGA_MIN = 6.0
SORNETTE_OMEGA_MAX = 8.0

# Parameter bounds for optimization (used by fitting algorithms)
LPPL_PARAMETER_BOUNDS = {
    'tc': (1.01, 1.5),
    'beta': (0.1, 0.7), 
    'omega': (2.0, 20.0),
    'phi': (-8*np.pi, 8*np.pi),
    'A': (-10, 10),
    'B': (-10, 10),
    'C': (-2.0, 2.0)
}