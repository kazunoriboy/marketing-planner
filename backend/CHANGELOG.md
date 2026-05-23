# 変更履歴

## [Unreleased]

### 🔄 変更
- 使用 AI モデルを更新
  - デフォルト: `gemini-2.5-flash-lite` → `gemini-3.1-flash-lite`
  - 高品質テキスト / LP / プラン修正: `gemini-3.5-flash`
  - 画像生成: `gemini-3.1-flash-image-preview`

## [1.0.0] - 2025-12-01

### ✨ 追加
- **顧客分析機能の実装** (Gemini 2.5 Flash-Lite版)
  - エンコーディング自動判別機能（UTF-8、Shift_JIS、CP932等）
  - AIによるCSVスキーマ推定
  - 統計情報計算（キャンセル率、リードタイム、人気プラン等）
  - AIマーケティングインサイト生成
  
- **新規サービス**
  - `app/services/analysis_service.py` - メイン分析ロジック

- **新規APIエンドポイント**
  - `POST /api/analysis/upload-csv` - CSV分析エンドポイント（推奨）

- **ドキュメント体系の整備**
  - `docs/` ディレクトリの作成
  - `docs/README.md` - ドキュメント一覧
  - `docs/QUICKSTART.md` - クイックスタートガイド
  - `docs/CUSTOMER_ANALYSIS_SPEC.md` - 機能仕様書
  - `docs/IMPLEMENTATION_GUIDE.md` - 実装ガイド
  - `docs/API_GUIDE.md` - APIガイド

- **テスト体系の整備**
  - `tests/` ディレクトリの作成
  - `tests/test_analysis.py` - 顧客分析機能のテスト
  - `tests/README.md` - テストガイド

- **依存関係**
  - `chardet` - エンコーディング自動判別用

### 🔄 変更
- **LLMクライアント** (`app/core/llm.py`)
  - Gemini 2.5 Flash-Lite対応
  - モデル名を指定可能に変更
  - 便利関数 `generate_text()` を追加

- **CSV分析サービス** (`app/services/csv_analyzer.py`)
  - エンコーディング自動判別機能を追加
  - スキーマ推定プロンプトの改善
  - サンプルデータ行数を3行→10行に増加

- **既存APIエンドポイント**
  - `POST /api/analysis/customer` も Gemini 2.5 Flash-Lite に対応

- **README更新**
  - `backend/README.md` - ディレクトリ構造とドキュメントリンクを追加
  - `README.md` (プロジェクトルート) - 新機能とドキュメントを追加

### 📝 ドキュメント
- ドキュメントを `docs/` ディレクトリに集約
- テストファイルを `tests/` ディレクトリに移動
- 各機能の詳細な仕様書を作成
- クイックスタートガイドを作成

### 🗑️ 削除
- `backend/IMPLEMENTATION_SUMMARY.md` - `docs/` に移動
- `QUICKSTART_ANALYSIS.md` - `backend/docs/QUICKSTART.md` に統合
- `backend/app/services/README_ANALYSIS.md` - `docs/API_GUIDE.md` に変更

## ディレクトリ構造の変更

### Before
```
backend/
├── app/
│   └── services/
│       └── README_ANALYSIS.md
├── test_analysis.py
├── IMPLEMENTATION_SUMMARY.md
└── README.md
```

### After
```
backend/
├── app/
│   └── services/
│       └── analysis_service.py (新規)
├── docs/ (新規)
│   ├── README.md
│   ├── QUICKSTART.md
│   ├── CUSTOMER_ANALYSIS_SPEC.md
│   ├── IMPLEMENTATION_GUIDE.md
│   └── API_GUIDE.md
├── tests/ (新規)
│   ├── __init__.py
│   ├── README.md
│   └── test_analysis.py
├── CHANGELOG.md (新規)
└── README.md (更新)
```

## 互換性

### 破壊的変更
なし。既存のエンドポイント `POST /api/analysis/customer` は引き続き動作します。

### 非推奨
なし

### 推奨事項
- 新規開発では `POST /api/analysis/upload-csv` の使用を推奨
- エンコーディング自動判別とより詳細な統計情報に対応

## 今後の予定

### バージョン 1.1.0 (予定)
- [ ] pytestへの完全移行
- [ ] ユニットテストの追加
- [ ] カバレッジレポートの自動生成
- [ ] CSVファイルサイズ制限の明示的な実装

### バージョン 1.2.0 (予定)
- [ ] カスタムスキーママッピングの保存機能
- [ ] 時系列トレンド分析
- [ ] 複数CSVファイルの比較分析

### バージョン 2.0.0 (予定)
- [ ] 予測モデル（需要予測、キャンセル予測）
- [ ] リアルタイムダッシュボード
- [ ] 多言語対応

---

**凡例**:
- ✨ 追加: 新機能
- 🔄 変更: 既存機能の変更
- 🐛 修正: バグ修正
- 📝 ドキュメント: ドキュメントのみの変更
- 🗑️ 削除: 削除された機能

