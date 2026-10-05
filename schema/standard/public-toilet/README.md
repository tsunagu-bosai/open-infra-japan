# 公衆トイレ一覧 標準スキーマ

Open Infra Japan で公衆トイレデータを検証するための
自治体標準オープンデータセット準拠スキーマ。

## 出典

デジタル庁
「自治体標準オープンデータセット（正式版）」

https://www.digital.go.jp/resources/open_data/municipal-standard-data-set-test

使用資料：

`20260801_resources_open_data_municipal-standard-open-dataset_table_a.xlsx`

シート：

`13.公衆トイレ一覧`

取得日：2026-09-19

利用条件：

公共データ利用規約（第1.0版）（PDL1.0）

https://www.digital.go.jp/resources/open_data/public_data_license_v1.0

## schema.csv

`schema.csv` は、デジタル庁が公開する
「自治体標準オープンデータセット・データ項目定義書A」の
「13.公衆トイレ一覧」から Open Infra Japan が機械処理用に
抽出・加工したものです。

公式資料そのものではありません。

以下のスクリプトで公式定義書から生成します。

`tools/schema/extract_public_toilet_schema.py`

## 運用方針

自治体から取得した原データは変更せず `data/raw/` に保存します。

検証では `schema.csv` および公式資料のデータ項目特記事項を基準とし、
自治体標準オープンデータセットへの適合状況を確認します。

表記・文字コード・時刻形式などの差異を正規化する場合も、
原データを上書きせず、変換処理を再現可能な形で管理します。
