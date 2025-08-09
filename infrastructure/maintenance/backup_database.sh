#!/bin/bash
# データベースバックアップスクリプト
# 誤削除防止とバックアップ管理

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_FILE="$PROJECT_ROOT/results/analysis_results.db"
BACKUP_DIR="$PROJECT_ROOT/results/backups"

# バックアップディレクトリ作成
mkdir -p "$BACKUP_DIR"

# タイムスタンプ付きバックアップ
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/analysis_results_${TIMESTAMP}.db"

# バックアップ実行
if [ -f "$DB_FILE" ]; then
    cp "$DB_FILE" "$BACKUP_FILE"
    echo "✅ バックアップ完了: $BACKUP_FILE"
    
    # サイズ表示
    ls -lh "$BACKUP_FILE"
    
    # 30日以上古いバックアップを削除
    find "$BACKUP_DIR" -name "analysis_results_*.db" -mtime +30 -delete
    echo "📋 30日以上古いバックアップを削除しました"
    
    # 現在のバックアップ数
    BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/analysis_results_*.db 2>/dev/null | wc -l)
    echo "📊 現在のバックアップ数: $BACKUP_COUNT"
else
    echo "❌ データベースが見つかりません: $DB_FILE"
    exit 1
fi