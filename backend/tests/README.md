# テストディレクトリ

## 概要

このディレクトリには、バックエンドアプリケーションのテストコードが含まれています。

## テストファイル

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

- [ ] pytestへの移行
- [ ] ユニットテストの追加
- [ ] 統合テストの追加
- [ ] カバレッジレポートの自動生成
- [ ] CI/CDパイプラインとの統合

---

**最終更新**: 2025年12月1日

