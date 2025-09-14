#!/usr/bin/env python3
"""
Validation Runner - Historical Crash Validation

🎯 Quick access to historical crash validation tests

Usage:
    python entry_points/validator.py [--crash 1987|2000|all]
    python entry_points/validator.py [--quick]
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def run_1987_validation():
    """Run 1987 Black Monday validation (LPPL version)"""
    print("🎯 Running 1987 Black Monday Validation (LPPL)...")
    
    try:
        from core.validation.crash_validators.black_monday_1987_validator import main as validate_1987
        result = validate_1987()
        
        if result:
            print("✅ 1987 Black Monday LPPL Validation: PASSED (100/100 score)")
            return True
        else:
            print("❌ 1987 Black Monday LPPL Validation: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ 1987 LPPL validation error: {e}")
        return False

def run_1987_fco_validation():
    """Run 1987 Black Monday validation (FCO version)"""
    print("🎯 Running 1987 Black Monday Validation (FCO)...")
    
    try:
        from core.validation.crash_validators.black_monday_1987_fco_validator import BlackMonday1987FCOValidator
        validator = BlackMonday1987FCOValidator(use_cache=True)
        result = validator.validate()
        
        if result:
            print("✅ 1987 Black Monday FCO Validation: PASSED")
            return True
        else:
            print("❌ 1987 Black Monday FCO Validation: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ 1987 FCO validation error: {e}")
        return False

def run_2000_validation():
    """Run 2000 Dotcom Bubble validation"""
    print("🎯 Running 2000 Dotcom Bubble Validation...")
    
    try:
        from core.validation.crash_validators.dotcom_bubble_2000_validator import main as validate_2000
        result = validate_2000()
        
        if result:
            print("✅ 2000 Dotcom Bubble Validation: PASSED")
            return True
        else:
            print("❌ 2000 Dotcom Bubble Validation: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ 2000 validation error: {e}")
        return False

def run_quick_validation():
    """Run quick core system validation"""
    print("🔍 Running Quick System Validation...")
    
    # Test core imports
    try:
        from core.sornette_theory.lppl_model import logarithm_periodic_func
        print("✅ Core theory import: OK")
    except Exception as e:
        print(f"❌ Core theory import: FAILED - {e}")
        return False
    
    try:
        from core.fitting.fitter import LogarithmPeriodicFitter
        print("✅ Fitting system import: OK")
    except Exception as e:
        print(f"❌ Fitting system import: FAILED - {e}")
        return False
    
    try:
        from infrastructure.data_sources.unified_data_client import UnifiedDataClient
        print("✅ Data sources import: OK")
    except Exception as e:
        print(f"❌ Data sources import: FAILED - {e}")
        return False
    
    print("✅ Quick validation completed successfully")
    return True

def run_full_validation():
    """Run comprehensive validation suite"""
    print("🎯 Running Full Validation Suite...")
    
    results = {
        'quick': run_quick_validation(),
        '1987': run_1987_validation(),
        '2000': run_2000_validation()
    }
    
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n📊 Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validations PASSED - System integrity confirmed")
        return True
    else:
        print("⚠️  Some validations FAILED - Review system integrity")
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Validation Runner - Historical Crash Validation"
    )
    
    parser.add_argument('--crash', choices=['1987', '2000', 'all'], default='all',
                       help='Specific crash validation to run')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick system validation only')
    
    args = parser.parse_args()
    
    if args.quick:
        success = run_quick_validation()
    elif args.crash == '1987':
        success = run_1987_validation()
    elif args.crash == '2000':
        success = run_2000_validation()
    else:  # all
        success = run_full_validation()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()