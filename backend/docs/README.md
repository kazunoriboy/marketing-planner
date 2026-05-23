# ドキュメント

顧客分析機能に関するドキュメント一覧です。

## 📚 ドキュメント構成

### 🚀 [QUICKSTART.md](QUICKSTART.md)
**5分でセットアップできるクイックスタートガイド**

- 環境構築手順
- テストスクリプトの実行方法
- APIの基本的な使い方
- トラブルシューティング

**対象読者**: 初めて機能を試す開発者

---

### 📋 [CUSTOMER_ANALYSIS_SPEC.md](CUSTOMER_ANALYSIS_SPEC.md)
**機能仕様書 - 顧客分析機能の詳細仕様**

- CSVフォーマット仕様
- AIスキーマ推定の仕組み
- 統計情報の計算方法
- APIエンドポイント仕様
- パフォーマンス・セキュリティ考慮事項

**対象読者**: プロダクトマネージャー、QAエンジニア、フロントエンド開発者

---

### 🔧 [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)
**実装ガイド - 技術的な実装詳細**

- アーキテクチャ設計
- 各クラス・メソッドの詳細実装
- コード例
- テスト方法
- デプロイ手順

**対象読者**: バックエンド開発者、コントリビューター

---

### 📐 [ARCHITECTURE.md](ARCHITECTURE.md)
**アーキテクチャ設計 - システム設計の詳細**

- CSV処理の設計パターン
- クラス構造と継承関係
- 設計の利点（DRY、単一責任等）
- データフロー
- 今後の拡張案

**対象読者**: バックエンド開発者、アーキテクト

---

### 🌐 [API_GUIDE.md](API_GUIDE.md)
**APIガイド - エンドポイントの使い方**

- 全エンドポイントの詳細
- リクエスト・レスポンス例
- エラーハンドリング
- ベストプラクティス

**対象読者**: フロントエンド開発者、API利用者

---

## 📖 読む順序

### 初めて使う場合
1. [QUICKSTART.md](QUICKSTART.md) - セットアップして動かす
2. [CUSTOMER_ANALYSIS_SPEC.md](CUSTOMER_ANALYSIS_SPEC.md) - 機能を理解する
3. [API_GUIDE.md](API_GUIDE.md) - API仕様を確認する

### 開発に参加する場合
1. [QUICKSTART.md](QUICKSTART.md) - 環境構築
2. [ARCHITECTURE.md](ARCHITECTURE.md) - システム設計を理解する
3. [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - 実装を理解する
4. [CUSTOMER_ANALYSIS_SPEC.md](CUSTOMER_ANALYSIS_SPEC.md) - 仕様を確認する

### フロントエンド開発の場合
1. [QUICKSTART.md](QUICKSTART.md) - バックエンドをローカルで起動
2. [API_GUIDE.md](API_GUIDE.md) - API仕様を確認
3. [CUSTOMER_ANALYSIS_SPEC.md](CUSTOMER_ANALYSIS_SPEC.md) - レスポンスデータの詳細を確認

## 🔗 関連リンク

### 外部ドキュメント
- [Gemini API公式ドキュメント](https://ai.google.dev/docs)
- [FastAPI公式ドキュメント](https://fastapi.tiangolo.com/)
- [pandas公式ドキュメント](https://pandas.pydata.org/docs/)

### プロジェクト内
- [本番デプロイ手順](../../DEPLOY.md) - EC2 への手動デプロイ（自動スクリプトなし）
- [テストコード](../tests/) - テスト実装とサンプルコード
- [サービス実装](../app/services/) - コアロジック
- [APIルーター](../app/api/) - エンドポイント実装

## 📝 ドキュメントの更新

ドキュメントに誤りや不足がある場合は、プルリクエストを送ってください。

### 更新時の注意事項
- 変更内容は明確に記載する
- コード例は動作確認済みのものを使用する
- バージョン番号と最終更新日を更新する

## 🤖 使用 AI モデル（アプリ全体）

顧客分析以外（LP 生成、画像生成、プラン修正など）も含めたモデル一覧は [ルート README](../../README.md#使用-ai-モデル) または [DEPLOY.md](../../DEPLOY.md) を参照してください。

---

**プロジェクト**: Marketing Planner  
**バージョン**: 1.0  
**最終更新**: 2026年5月22日

