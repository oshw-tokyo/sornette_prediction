import sys
import os
from datetime import datetime

# srcディレクトリをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(project_root)

from src.reproducibility_validation.crash_validator import CrashValidator
from src.reproducibility_validation.historical_crashes import get_crash_case


def validate_1987_october_crash():
    """1987年10月のクラッシュの再現性を検証"""
    print("\n=== 1987年10月クラッシュの再現性検証 ===\n")
    
    # クラッシュケースの情報を表示
    crash_case = get_crash_case('1987-10')
    print("検証対象:")
    print(f"- 名称: {crash_case.name}")
    print(f"- 期間: {crash_case.period.start_date.date()} から {crash_case.period.end_date.date()}")
    print(f"- クラッシュ日: {crash_case.period.crash_date.date()}")
    print(f"- 対象銘柄: {crash_case.symbol}")
    print("\n期待される値:")
    print(f"- べき指数(m): {crash_case.parameters.m:.3f} ± {crash_case.parameters.tolerance_m:.3f}")
    print(f"- 角振動数(ω): {crash_case.parameters.omega:.3f} ± {crash_case.parameters.tolerance_omega:.3f}")
    
    print("\n検証開始...")
    
    print("\n検証開始...")
    validator = CrashValidator()
    start_time = datetime.now()
    
    n_attempts = 5  # 複数回の試行
    success = False
    
    try:
        for i in range(n_attempts):
            print(f"\n試行 {i+1}/{n_attempts}")
            if validator.validate_crash('1987-10'):
                success = True
                break
                
        end_time = datetime.now()
        duration = end_time - start_time
        
        print(f"\n検証完了 (所要時間: {duration.total_seconds():.1f}秒)")
        print(f"結果: {'✓ 成功' if success else '✗ 失敗'}")
        
        return success
        
    except Exception as e:
        print(f"\n検証中にエラーが発生しました: {str(e)}")
        return False
    
if __name__ == "__main__":
    success = validate_1987_october_crash()
    sys.exit(0 if success else 1)