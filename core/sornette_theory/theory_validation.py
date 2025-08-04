"""
Sornette Theory Validation Module

This module provides validation functions to ensure that LPPL implementations
and parameters comply with the theoretical constraints established in Sornette's papers.

🚨 PROTECTED: This module is critical for maintaining scientific integrity
and must enforce the 100/100 score validation requirement.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from .lppl_model import (
    SORNETTE_THEORETICAL_BETA, 
    SORNETTE_BETA_TOLERANCE,
    SORNETTE_OMEGA_MIN,
    SORNETTE_OMEGA_MAX
)


def validate_sornette_parameters(parameters: Dict[str, float]) -> Dict[str, any]:
    """
    Comprehensive validation of LPPL parameters against Sornette theory
    
    Args:
        parameters: Dictionary containing LPPL parameters
                   Expected keys: tc, beta, omega, phi, A, B, C
                   
    Returns:
        dict: Comprehensive validation results
    """
    # Extract parameters
    tc = parameters.get('tc', None)
    beta = parameters.get('beta', None) 
    omega = parameters.get('omega', None)
    phi = parameters.get('phi', None)
    
    if any(param is None for param in [tc, beta, omega, phi]):
        return {
            'valid': False,
            'error': 'Missing required parameters',
            'required_parameters': ['tc', 'beta', 'omega', 'phi']
        }
    
    validation_results = {
        'parameter_validation': {},
        'theoretical_compliance': {},
        'overall_assessment': {}
    }
    
    # Individual parameter validation
    validation_results['parameter_validation'] = {
        'tc': {
            'value': tc,
            'valid': 1.0 < tc < 2.0,
            'optimal_range': '1.01 < tc < 1.5',
            'current_status': 'within_bounds' if 1.01 <= tc <= 1.5 else 'acceptable' if 1.0 < tc < 2.0 else 'invalid'
        },
        'beta': {
            'value': beta,
            'valid': 0.1 < beta < 0.7,
            'theoretical_optimal': abs(beta - SORNETTE_THEORETICAL_BETA) <= SORNETTE_BETA_TOLERANCE,
            'sornette_value': SORNETTE_THEORETICAL_BETA,
            'tolerance': SORNETTE_BETA_TOLERANCE,
            'deviation': abs(beta - SORNETTE_THEORETICAL_BETA),
            'current_status': 'optimal' if abs(beta - SORNETTE_THEORETICAL_BETA) <= SORNETTE_BETA_TOLERANCE else 'acceptable' if 0.1 < beta < 0.7 else 'invalid'
        },
        'omega': {
            'value': omega,
            'valid': 2.0 < omega < 20.0,
            'theoretical_optimal': SORNETTE_OMEGA_MIN <= omega <= SORNETTE_OMEGA_MAX,
            'sornette_range': f'{SORNETTE_OMEGA_MIN}-{SORNETTE_OMEGA_MAX}',
            'current_status': 'optimal' if SORNETTE_OMEGA_MIN <= omega <= SORNETTE_OMEGA_MAX else 'acceptable' if 2.0 < omega < 20.0 else 'invalid'
        },
        'phi': {
            'value': phi,
            'valid': -8*np.pi < phi < 8*np.pi,
            'current_status': 'valid' if -8*np.pi < phi < 8*np.pi else 'invalid'
        }
    }
    
    # Theoretical compliance assessment
    all_valid = all(param['valid'] for param in validation_results['parameter_validation'].values())
    beta_optimal = validation_results['parameter_validation']['beta']['theoretical_optimal']
    omega_optimal = validation_results['parameter_validation']['omega']['theoretical_optimal']
    
    validation_results['theoretical_compliance'] = {
        'all_parameters_valid': all_valid,
        'beta_in_sornette_range': beta_optimal,
        'omega_in_sornette_range': omega_optimal,
        'theoretically_optimal': beta_optimal and omega_optimal,
        'compliance_score': calculate_compliance_score(validation_results['parameter_validation'])
    }
    
    # Overall assessment
    validation_results['overall_assessment'] = {
        'validation_passed': all_valid,
        'theoretical_quality': 'excellent' if beta_optimal and omega_optimal else 'good' if all_valid else 'poor',
        'recommendation': get_parameter_recommendations(validation_results['parameter_validation']),
        'scientific_integrity_maintained': all_valid and beta_optimal  # Critical for 100/100 score
    }
    
    return validation_results


def calculate_compliance_score(parameter_validation: Dict) -> float:
    """
    Calculate a numerical compliance score (0-100) based on parameter quality
    
    Args:
        parameter_validation: Parameter validation results
        
    Returns:
        float: Compliance score (0-100)
    """
    score = 0.0
    
    # TC score (20 points)
    tc_status = parameter_validation['tc']['current_status']
    if tc_status == 'within_bounds':
        score += 20
    elif tc_status == 'acceptable':
        score += 15
    
    # Beta score (40 points - most critical)
    beta_status = parameter_validation['beta']['current_status']
    if beta_status == 'optimal':
        score += 40
    elif beta_status == 'acceptable':
        score += 20
    
    # Omega score (30 points)
    omega_status = parameter_validation['omega']['current_status']
    if omega_status == 'optimal':
        score += 30
    elif omega_status == 'acceptable':
        score += 15
    
    # Phi score (10 points)
    phi_status = parameter_validation['phi']['current_status']
    if phi_status == 'valid':
        score += 10
    
    return score


def get_parameter_recommendations(parameter_validation: Dict) -> List[str]:
    """
    Generate recommendations for parameter improvement
    
    Args:
        parameter_validation: Parameter validation results
        
    Returns:
        List[str]: List of recommendations
    """
    recommendations = []
    
    # TC recommendations
    tc_data = parameter_validation['tc']
    if not tc_data['valid']:
        recommendations.append(f"Adjust tc to be within valid range (1.0 < tc < 2.0). Current: {tc_data['value']:.3f}")
    elif tc_data['current_status'] != 'within_bounds':
        recommendations.append(f"Consider adjusting tc to optimal range (1.01 < tc < 1.5). Current: {tc_data['value']:.3f}")
    
    # Beta recommendations
    beta_data = parameter_validation['beta']
    if not beta_data['valid']:
        recommendations.append(f"Adjust beta to valid range (0.1 < beta < 0.7). Current: {beta_data['value']:.3f}")
    elif not beta_data['theoretical_optimal']:
        target = SORNETTE_THEORETICAL_BETA
        recommendations.append(f"Consider adjusting beta closer to Sornette theoretical value {target:.3f} ± {SORNETTE_BETA_TOLERANCE:.3f}. Current: {beta_data['value']:.3f}")
    
    # Omega recommendations
    omega_data = parameter_validation['omega']
    if not omega_data['valid']:
        recommendations.append(f"Adjust omega to valid range (2.0 < omega < 20.0). Current: {omega_data['value']:.3f}")
    elif not omega_data['theoretical_optimal']:
        recommendations.append(f"Consider adjusting omega to Sornette range ({SORNETTE_OMEGA_MIN}-{SORNETTE_OMEGA_MAX}). Current: {omega_data['value']:.3f}")
    
    # Phi recommendations
    phi_data = parameter_validation['phi']
    if not phi_data['valid']:
        recommendations.append(f"Adjust phi to valid range (-8π < phi < 8π). Current: {phi_data['value']:.3f}")
    
    if not recommendations:
        recommendations.append("All parameters are within theoretical ranges. Excellent compliance with Sornette theory.")
    
    return recommendations


def validate_historical_reproduction(predicted_params: Dict, known_crash_params: Dict, tolerance: float = 0.1) -> Dict:
    """
    Validate that predicted parameters can reproduce known historical crashes
    
    This is critical for maintaining the 100/100 score requirement.
    
    Args:
        predicted_params: Parameters from current prediction
        known_crash_params: Known parameters from historical validation
        tolerance: Acceptable deviation tolerance
        
    Returns:
        dict: Historical reproduction validation results
    """
    reproduction_results = {
        'beta_match': abs(predicted_params.get('beta', 0) - known_crash_params.get('beta', 0)) <= tolerance,
        'omega_match': abs(predicted_params.get('omega', 0) - known_crash_params.get('omega', 0)) <= tolerance,
        'parameter_deviations': {},
        'reproduction_quality': 'unknown'
    }
    
    # Calculate individual deviations
    for param in ['tc', 'beta', 'omega']:
        if param in predicted_params and param in known_crash_params:
            deviation = abs(predicted_params[param] - known_crash_params[param])
            reproduction_results['parameter_deviations'][param] = {
                'predicted': predicted_params[param],
                'historical': known_crash_params[param],
                'deviation': deviation,
                'within_tolerance': deviation <= tolerance
            }
    
    # Overall quality assessment
    matches = sum(1 for dev in reproduction_results['parameter_deviations'].values() if dev['within_tolerance'])
    total_params = len(reproduction_results['parameter_deviations'])
    
    if total_params > 0:
        match_ratio = matches / total_params
        if match_ratio >= 0.8:
            reproduction_results['reproduction_quality'] = 'excellent'
        elif match_ratio >= 0.6:
            reproduction_results['reproduction_quality'] = 'good'
        else:
            reproduction_results['reproduction_quality'] = 'poor'
    
    reproduction_results['maintains_100_score'] = reproduction_results['reproduction_quality'] in ['excellent', 'good']
    
    return reproduction_results


# Known theoretical constraints from Sornette papers
THEORETICAL_CONSTRAINTS = {
    'critical_exponent_beta': {
        'optimal_value': 0.33,
        'tolerance': 0.03,
        'physical_meaning': 'Critical exponent determining power law behavior near crash',
        'reference': 'Sornette 2004, equation (54)'
    },
    'angular_frequency_omega': {
        'optimal_range': (6.0, 8.0),
        'physical_meaning': 'Frequency of log-periodic oscillations',
        'reference': 'Sornette 2004, empirical observations'
    },
    'critical_time_tc': {
        'constraint': 'tc > max(time_series)',
        'typical_range': (1.01, 1.5),
        'physical_meaning': 'Predicted crash time (normalized)',
        'reference': 'Sornette theory fundamentals'
    }
}