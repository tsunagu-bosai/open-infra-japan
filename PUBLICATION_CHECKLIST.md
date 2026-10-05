# Open Infra Japan 公開前チェックリスト

## 1. 公開リポジトリ構成

- [x] 作業用 `work/` と公開用 `public/` を分離
- [x] `public/` を独立Gitリポジトリとして初期化
- [x] `data/raw/` を公開対象から除外
- [x] `logs/` を公開対象から除外
- [x] 正規化再現に必要な `patches/public-toilet/` を公開対象に含める
- [x] 調査用 `sources/` を公開対象から除外
- [x] 内部調査用 `catalog/reviews/` 等を公開対象から除外

## 2. 公開データ

- [x] `data/normalized/` を公開側へ配置
- [x] `dist/facilities-official.csv` を公開側へ配置
- [x] 47都道府県の正規化データ配置を確認
- [x] GitHubの通常Gitで扱えるサイズであることを確認
- [ ] 公開直前に全国exportを再生成
- [ ] 公開直前に件数を再確認
- [ ] README記載件数と実データ件数を一致させる

## 3. カタログ

- [x] `catalog/datasets.csv`
- [x] `catalog/normalized_sources.csv`
- [x] `data/reference/municipalities.csv`
- [x] 内部調査用 `public_toilet_municipality_status.csv` は初回公開から除外
- [ ] `datasets.csv` のライセンス欄を最終監査
- [ ] `datasets.csv` の `source_url` / `license_url` を最終確認
- [ ] 公開対象データにライセンス不明のものがないか確認

## 4. スキーマ

- [x] `schema/standard/public-toilet/schema.csv`
- [x] 公衆トイレschema README
- [x] 自治体標準オープンデータセットREADME
- [x] 第三者配布のXLSX / ZIP原本を公開対象から除外

## 5. ツール

- [x] 正規化ツール
- [x] exportツール
- [x] 検証ツール
- [x] schema関連ツール
- [x] `tools/catalog/` を初回公開から除外
- [x] `tools/history/` を初回公開から除外
- [x] 内部進捗管理ファイルを公開対象から除外
- [ ] 公開側だけでPython importエラーが発生しないか確認
- [ ] 公開側だけで検証ツールが動作するか確認
- [ ] 公開側だけでexportツールが動作するか確認

## 6. ドキュメント

- [x] `README.md`
- [x] `LICENSE`
- [x] `LICENSE-DATA.md`
- [x] `CONTRIBUTING.md`
- [x] `GETTING_STARTED.md`
- [ ] `GETTING_STARTED.md` を公開構成に合わせて最終確認
- [ ] `docs/methodology.md`
- [ ] `docs/data-schema.md`
- [ ] `docs/data-policy.md`
- [ ] `docs/known-limitations.md`

## 7. データ品質

- [x] provenance確認
- [x] 安定ID・重複確認
- [x] 行政区fallback確認
- [x] 施設名空欄確認
- [x] 公衆トイレ設備情報の全空欄自治体監査
- [x] 明確に変換可能な設備情報の正規化
- [x] 推測が必要な情報は未補完
- [ ] 全国の正規化データを最終validate
- [ ] `git diff --check`
- [ ] 統合CSVの重複・件数を最終確認

## 8. 既知の制約

- [ ] 元データ未公開・未発見自治体が存在することを明記
- [ ] 空欄は「なし」ではなく「不明」の場合があることを明記
- [ ] 座標を推測補完しない方針を明記
- [ ] 茨城町・涸沼自然公園の座標未確定事項を必要に応じて記載
- [ ] 公開元の更新とOpen Infra Japanへの反映に時間差があることを明記

## 9. GitHub

- [ ] 公開GitHubリポジトリを作成
- [ ] repository description設定
- [ ] websiteに `https://tsunagubosai.jp/` を設定
- [ ] Topics設定
- [ ] Issues有効化
- [ ] Pull Requests利用可能状態を確認
- [ ] 初期コミット
- [ ] GitHub Actions追加
- [ ] README表示確認
- [ ] LICENSE認識確認

## 10. GitHub Actions

- [ ] Pythonセットアップ
- [ ] 必要パッケージインストール
- [ ] 正規化済みデータ検証
- [ ] export結果の検証
- [ ] `git diff --check` 相当のチェック
- [ ] mainへのpush / PR時に自動実行

## 11. つなぐ防災サイト

- [ ] Open Infra Japan説明ページ
- [ ] GitHubへのリンク
- [ ] データ件数表示
- [ ] データ検索画面
- [ ] 都道府県フィルタ
- [ ] 自治体フィルタ
- [ ] 施設種別フィルタ
- [ ] 設備条件検索
- [ ] 出典表示
- [ ] ライセンス表示
- [ ] CSVダウンロード導線
- [ ] 「空欄＝なしではない」の説明

## 12. 公開直前

- [ ] `git status` 確認
- [ ] 不要ファイルが含まれていないことを確認
- [ ] 秘密情報・ローカルパス等がないことを確認
- [ ] README内リンク確認
- [ ] URL確認
- [ ] ライセンス確認
- [ ] 全検証成功
- [ ] 初期コミット
- [ ] GitHubへpush

## 13. 公開後

- [ ] つなぐ防災サイトから案内
- [ ] X等で公開告知
- [ ] Issue受付開始
- [ ] 更新手順を文書化
- [ ] 定期的なデータ更新方針を決定
