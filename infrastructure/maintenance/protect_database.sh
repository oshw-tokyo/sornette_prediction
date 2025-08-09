#!/bin/bash
# データベース保護設定スクリプト

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_FILE="$PROJECT_ROOT/results/analysis_results.db"

echo "🔒 データベース保護設定"
echo "========================"

# 1. 読み取り専用属性を設定（誤削除防止）
# chattr +i "$DB_FILE"  # 要root権限

# 2. エイリアスで保護（推奨）
echo "
# データベース保護エイリアス
alias rm='rm -i'  # 削除時に確認
alias protect_db='chmod 444 $DB_FILE'  # 読み取り専用
alias unprotect_db='chmod 644 $DB_FILE'  # 書き込み可能
alias backup_db='$SCRIPT_DIR/backup_database.sh'  # バックアップ
" >> ~/.bashrc

echo "✅ 以下のエイリアスを追加しました:"
echo "  rm         : 削除時に確認プロンプト"
echo "  protect_db : データベースを読み取り専用に"
echo "  unprotect_db: データベースを書き込み可能に"
echo "  backup_db  : データベースをバックアップ"
echo ""
echo "📋 新しいターミナルを開くか、以下を実行してください:"
echo "  source ~/.bashrc"