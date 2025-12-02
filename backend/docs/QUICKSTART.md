# 顧客分析機能 - クイックスタートガイド

## 🚀 5分でセットアップ

### 1. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成します：

```bash
# プロジェクトルートで実行
cd /Users/matsushimaittoku/Projects/marketing-planner

# .envファイルを作成
cat >> .env << 'EOF'
GOOGLE_API_KEY=your_api_key_here
DATABASE_URL=postgresql://postgres:postgres@db:5432/marketing_planner
EOF
```

### 2. コンテナの起動

```bash
# Dockerコンテナを起動
docker compose up -d

# ログを確認
docker compose logs -f backend
```

### 3. 依存関係のインストール

```bash
# 依存関係をインストール
docker compose exec backend pip install -r requirements.txt

# エンコーディング自動判別用ライブラリ（追加で必要）
docker compose exec backend pip install chardet
```

## 📝 使い方

### オプション1: テストスクリプトで試す（推奨）

サンプルデータで自動テストを実行します：

```bash
# プロジェクトルートから実行
cd /Users/matsushimaittoku/Projects/marketing-planner
docker compose exec backend python tests/test_analysis.py
```

**実行される内容:**
- ✅ サンプルCSVデータ生成（100件）
- ✅ エンコーディング自動判別のテスト
- ✅ AIスキーマ推定（Gemini 2.5 Flash-Lite）
- ✅ 統計情報計算（キャンセル率、リードタイムなど）
- ✅ マーケティングインサイト生成
- ✅ Shift_JISエンコーディングのテスト

**出力例:**
```
============================================================
顧客分析機能テスト - Gemini 2.5 Flash-Lite版
============================================================

1. サンプルCSVデータを生成中...
   ✓ 12345 バイトのCSVデータを生成しました

2. AnalysisServiceを初期化中...
   ✓ 使用モデル: gemini-2.5-flash-lite

3. エンコーディングを検出中...
   ✓ 検出されたエンコーディング: utf-8

4. CSVを読み込み中...
   ✓ 100 件のレコードを読み込みました
   ✓ カラム: ['予約ID', '予約日', '宿泊日', 'プラン名', '合計金額', 'ステータス', '宿泊人数']

5. AIによるスキーマ推定中...
   （Gemini 2.5 Flash-Liteで処理中...）
   ✓ スキーママッピング:
     - booking_date: 予約日
     - stay_date: 宿泊日
     - plan_name: プラン名
     - total_price: 合計金額
     - status: ステータス

6. 統計情報を計算中...
   ✓ 統計情報:
     - 総レコード数: 100
     - 期間: 2024-01-15 〜 2024-12-28
     - キャンセル率: 18.0%
     - 直前キャンセル率: 35.2%
     - 平均リードタイム: 28.3 日
     - 人気プランTop3:
       1. 素泊まりプラン: 32件
       2. 朝食付きプラン: 28件
       3. 夕朝食付きプラン: 24件
     - 価格統計:
       - 平均: ¥18,450
       - 最小: ¥5,200
       - 最大: ¥48,900

7. AIマーケティングインサイトを生成中...
   （Gemini 2.5 Flash-Liteで処理中...）
   ✓ インサイト:

------------------------------------------------------------
【顧客分析インサイト】

平均リードタイムが28.3日と長く、お客様は計画的に予約する傾向が
あります。早期予約のインセンティブ強化が効果的でしょう。

キャンセル率18%のうち35%が直前キャンセルで、機会損失が発生して
います。7日前からのキャンセルポリシー強化を検討してください。

人気は「素泊まり」「朝食付き」でシンプルなプランが支持されています。
これらのプランの付加価値向上や、セット割引の導入で客単価アップを
目指しましょう。

【推奨アクション】
1. 30日前予約で15%オフキャンペーン
2. キャンセルポリシーの見直し（前払い制度導入）
3. 朝食メニューの強化・地域特産品の活用
------------------------------------------------------------

8. 一気通貫分析テスト...
   （エンコーディング判別 → スキーマ推定 → 統計計算 → インサイト生成）
   ✓ 完了！

============================================================
テスト完了！
============================================================
```

### オプション2: APIで試す

#### ステップ1: 宿泊施設を登録

```bash
curl -X POST "http://localhost:8000/api/analysis/hotels" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "サンプルホテル",
    "address": "東京都渋谷区"
  }'
```

**レスポンス:**
```json
{
  "id": 1,
  "name": "サンプルホテル",
  "address": "東京都渋谷区",
  "created_at": "2024-12-01T12:00:00"
}
```

#### ステップ2: CSVファイルをアップロード

```bash
# CSVファイルを用意（例: customer_data.csv）
curl -X POST "http://localhost:8000/api/analysis/upload-csv" \
  -F "hotel_id=1" \
  -F "file=@customer_data.csv"
```

**レスポンス:**
```json
{
  "session_id": 1,
  "statistics": {
    "total_records": 1000,
    "schema_mapping": {
      "booking_date": "予約日",
      "stay_date": "宿泊日",
      "plan_name": "プラン名",
      "total_price": "合計金額",
      "status": "ステータス"
    },
    "cancellation_stats": {
      "total_bookings": 1000,
      "cancelled_bookings": 150,
      "cancellation_rate_percent": 15.0
    },
    "average_lead_time": 21.5,
    "top_plans": {
      "素泊まりプラン": 300,
      "朝食付きプラン": 250
    },
    "price_stats": {
      "average": 12000,
      "min": 5000,
      "max": 50000
    }
  },
  "insights": "【マーケティングインサイト】...",
  "created_at": "2024-12-01T12:00:00"
}
```

## 📊 CSVファイルの形式

### 推奨フォーマット

```csv
予約ID,予約日,宿泊日,プラン名,合計金額,ステータス
B0001,2024/01/15,2024/02/20,素泊まりプラン,8000,確定
B0002,2024/01/20,2024/03/10,朝食付きプラン,12000,キャンセル
B0003,2024/01/25,2024/04/05,夕朝食付きプラン,18000,確定
```

### 対応エンコーディング

自動判別に対応:
- ✅ UTF-8
- ✅ Shift_JIS
- ✅ CP932（Windows版Shift_JIS）
- ✅ EUC-JP
- ✅ ISO-2022-JP

### カラム要件

AIが以下のカラムを自動認識します（カラム名は柔軟に対応）:

| 項目 | 例 | 必須度 |
|-----|---|--------|
| 予約日 | 予約日、予約受付日、受付日 | 推奨 |
| 宿泊日 | 宿泊日、チェックイン日、IN日 | 推奨 |
| プラン名 | プラン名、プラン、商品名 | 推奨 |
| 金額 | 合計金額、料金、価格、金額 | 推奨 |
| ステータス | ステータス、状態、予約状態 | 推奨 |

## 🔧 サンプルCSVの生成

Pythonで簡単にサンプルCSVを生成できます:

```python
import pandas as pd
from datetime import datetime, timedelta
import random

data = []
for i in range(100):
    stay_date = datetime.now() + timedelta(days=random.randint(7, 180))
    booking_date = stay_date - timedelta(days=random.randint(7, 60))
    
    data.append({
        "予約ID": f"B{i+1:04d}",
        "予約日": booking_date.strftime("%Y/%m/%d"),
        "宿泊日": stay_date.strftime("%Y/%m/%d"),
        "プラン名": random.choice(["素泊まり", "朝食付き", "夕朝食付き"]),
        "合計金額": random.randint(5000, 30000),
        "ステータス": random.choice(["確定", "確定", "確定", "キャンセル"])
    })

df = pd.DataFrame(data)
df.to_csv("sample.csv", index=False, encoding='utf-8')
print("sample.csv を生成しました！")
```

## 🛠️ トラブルシューティング

### エラー: `GOOGLE_API_KEY環境変数が設定されていません`

**解決策:**
```bash
# .envファイルを確認
cat .env | grep GOOGLE_API_KEY

# API Keyが設定されているか確認
# 設定されていない場合は追加
echo "GOOGLE_API_KEY=your_api_key_here" >> .env

# コンテナを再起動
docker compose restart backend
```

### エラー: `CSVファイルの読み込みに失敗しました`

**原因:**
- ファイルが破損している
- 対応していないエンコーディング
- BOM付きUTF-8

**解決策:**
1. ファイルをテキストエディタで開いて確認
2. UTF-8で保存し直す
3. BOMを削除する

### エラー: `分析エラー: ...`

**解決策:**
```bash
# ログを確認
docker compose logs backend

# コンテナ内でPythonを実行して詳細確認
docker compose exec backend python -c "
from app.services.analysis_service import AnalysisService
import asyncio
service = AnalysisService()
print('OK')
"
```

## 📚 次のステップ

1. ✅ 自分のCSVデータで試してみる
2. ✅ 生成されたインサイトを確認
3. ✅ 統計情報をビジネス判断に活用
4. ✅ フロントエンドとの連携を検討

## 📖 詳細ドキュメント

- **機能仕様**: [CUSTOMER_ANALYSIS_SPEC.md](CUSTOMER_ANALYSIS_SPEC.md)
- **実装ガイド**: [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)
- **APIガイド**: [API_GUIDE.md](API_GUIDE.md)

## 🔗 リンク

- [FastAPI Docs](http://localhost:8000/docs) - API仕様書（Swagger UI）
- [Gemini API](https://ai.google.dev/docs) - Gemini公式ドキュメント

---

**バージョン**: 1.0  
**最終更新**: 2025年12月1日  
**使用モデル**: Gemini 2.5 Flash-Lite

