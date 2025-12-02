#!/bin/bash

# 実際のCSVファイルでテストするスクリプト

API_BASE="http://localhost:8000"
CSV_FILE="/Users/matsushimaittoku/Downloads/data_masked.csv"

echo "=== 顧客分析API テスト（実データ） ==="
echo ""

# ステップ1: ホテル登録
echo "1. ホテル登録中..."
RESPONSE=$(curl -s -X POST "$API_BASE/api/analysis/hotels" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "テスト施設",
    "address": "徳島県"
  }')

HOTEL_ID=$(echo $RESPONSE | jq -r '.id')
echo "   ✓ ホテルID: $HOTEL_ID"
echo ""

# ステップ2: CSV分析
echo "2. CSV分析実行中..."
echo "   ファイル: $CSV_FILE"
curl -X POST "$API_BASE/api/analysis/upload-csv" \
  -F "hotel_id=$HOTEL_ID" \
  -F "file=@$CSV_FILE" | jq .

echo ""
echo "=== テスト完了 ==="

