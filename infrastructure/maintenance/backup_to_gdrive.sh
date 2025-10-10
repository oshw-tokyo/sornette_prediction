#!/bin/bash
#
# Google Driveバックアップスクリプト
# FCO分析結果データベースを自動バックアップ
#
# 使用方法:
#   ./infrastructure/maintenance/backup_to_gdrive.sh
#
# cron設定例（毎日午前2時）:
#   0 2 * * * cd /home/no-rules/projects/12_sornnet_prediction/sornette_prediction && ./infrastructure/maintenance/backup_to_gdrive.sh >> logs/backup.log 2>&1
#

set -e  # エラー時に即座に停止

# プロジェクトルート（スクリプトの2階層上）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

# 設定
GDRIVE_REMOTE="zeroidea"
GDRIVE_BACKUP_DIR="sornette_prediction_backups"
DB_PATH="results/fco_analysis_results.db"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="fco_analysis_results_${TIMESTAMP}.db"

# ログ出力
echo "========================================="
echo "📦 FCO Database Backup to Google Drive"
echo "========================================="
echo "開始時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# データベース存在チェック
if [ ! -f "$DB_PATH" ]; then
    echo "❌ エラー: データベースファイルが見つかりません: $DB_PATH"
    exit 1
fi

# データベースサイズ確認
DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
echo "📊 バックアップ対象: $DB_PATH ($DB_SIZE)"

# Google Drive接続確認
if ! rclone listremotes | grep -q "^${GDRIVE_REMOTE}:"; then
    echo "❌ エラー: Google Drive接続 '${GDRIVE_REMOTE}:' が見つかりません"
    echo "   rclone config で設定を確認してください"
    exit 1
fi

echo "✅ Google Drive接続確認: ${GDRIVE_REMOTE}:"

# バックアップディレクトリ作成（存在しない場合）
echo "📁 バックアップ先: ${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/"
rclone mkdir "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}" 2>/dev/null || true

# バックアップ実行
echo "⏳ アップロード中..."
if rclone copy "$DB_PATH" "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/" --progress 2>&1 | tail -5; then
    # ファイル名をタイムスタンプ付きに変更
    rclone moveto \
        "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/fco_analysis_results.db" \
        "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}/${BACKUP_NAME}" \
        2>/dev/null || echo "⚠️  リネームスキップ（同名ファイル存在の可能性）"

    echo ""
    echo "✅ バックアップ完了: ${BACKUP_NAME}"
else
    echo "❌ バックアップ失敗"
    exit 1
fi

# 古いバックアップ削除（30日より古いもの）
echo ""
echo "🗑️  古いバックアップの整理（30日より古いファイルを削除）"
rclone delete "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}" --min-age 30d --verbose 2>&1 | grep -v "^$" || echo "   削除対象なし"

# Google Drive上のバックアップ一覧表示
echo ""
echo "📋 Google Drive バックアップ一覧:"
rclone ls "${GDRIVE_REMOTE}:${GDRIVE_BACKUP_DIR}" 2>/dev/null | tail -10 || echo "   （バックアップファイルがありません）"

echo ""
echo "完了時刻: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================="
