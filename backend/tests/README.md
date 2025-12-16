# テストディレクトリ

## 概要

このディレクトリには、バックエンドアプリケーションのテストコードが含まれています。

## テストファイル

### test_marketing_auth.py

マルチテナント マーケティングAPI認証テスト。

**含まれるテスト:**
- 認証なしでのアクセス拒否テスト
- 権限なし施設へのアクセス拒否テスト（403）
- 権限あり施設へのアクセス許可テスト
- 権限レベル（owner/editor/viewer）のテスト
- 存在しない施設へのアクセステスト
- プラン操作（取得/更新/削除）のテスト
- クリエイティブAPI権限テスト
- クロスアクセス統合テスト

### test_dependencies.py

認証依存関係のユニットテスト。

**含まれるテスト:**
- `check_hotel_permission` 関数のテスト
- 権限なし時のFalse返却
- オーナー/編集者/閲覧者権限のテスト
- 存在しないホテル・管理者のテスト
- 権限ロールの値テスト

### test_hotels.py

ホテルAPIエンドポイントのテスト。

**含まれるテスト:**
- ホテル作成のテスト
- ホテル一覧取得のテスト
- ホテル詳細取得のテスト
- 統合テスト

### test_analysis.py

顧客分析機能のテストスクリプト。

**含まれるテスト:**
- サンプルCSVデータ生成
- エンコーディング自動判別のテスト
- AIスキーマ推定のテスト
- 統計計算のテスト
- AIインサイト生成のテスト
- Shift_JISエンコーディングのテスト

**実行方法:**
```bash
# プロジェクトルートから実行
cd /path/to/marketing-planner
docker compose exec backend python tests/test_analysis.py

# または、コンテナ内で実行
docker compose exec backend bash
cd /app
python tests/test_analysis.py

# pytestでの実行（今後追加予定）
docker compose exec backend python -m pytest tests/ -v
```

## テスト環境

### 必要な環境変数

```bash
GOOGLE_API_KEY=your_api_key_here
DATABASE_URL=postgresql://postgres:postgres@db:5432/marketing_planner
```

### 依存関係

```bash
# 必須パッケージ（初回のみ）
docker compose exec backend pip install -r requirements.txt

# 追加で必要なパッケージ
docker compose exec backend pip install chardet

# テストツール（今後追加予定）
docker compose exec backend pip install pytest pytest-asyncio pytest-cov
```

## テスト追加ガイドライン

### ファイル命名規則

- テストファイル: `test_*.py`
- テスト関数: `test_*()`
- テストクラス: `Test*`

### テストの書き方

```python
import pytest
from app.services.analysis_service import AnalysisService

@pytest.mark.asyncio
async def test_analyze_csv():
    """CSV分析のテスト"""
    service = AnalysisService()
    
    # サンプルCSVを用意
    csv_content = b"..."
    
    # 分析実行
    statistics, insights = await service.analyze_csv(csv_content)
    
    # アサーション
    assert statistics["total_records"] > 0
    assert len(insights) > 0
```

## 今後の追加予定

- [x] pytestへの移行
- [x] ユニットテストの追加
- [x] 統合テストの追加
- [ ] カバレッジレポートの自動生成
- [ ] CI/CDパイプラインとの統合

---

**最終更新**: 2025年12月16日

