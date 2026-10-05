# 自治体標準オープンデータセット 参照資料

## 公式情報

デジタル庁「オープンデータ」

https://www.digital.go.jp/resources/open_data

デジタル庁「自治体標準オープンデータセット（正式版）」

https://www.digital.go.jp/resources/open_data/municipal-standard-data-set-test

取得日: 2026-09-19

## source ディレクトリ

`source/` には、デジタル庁から取得した自治体標準オープンデータセットの
定義書、フォーマットサンプル、関連ツールの原本を保存する。

公式資料は加工せず保存し、Open Infra Japan で作成する検証用スキーマや
変換データとは分離して管理する。

## Open Infra Japanでの利用

自治体標準オープンデータセットの公式定義書および
フォーマットサンプルを、標準スキーマの確認・検証に使用する。

公衆トイレ一覧については、公式定義を基準として

`schema/standard/public-toilet/`

に検証用スキーマを整備する。

## 利用条件

本ディレクトリの `source/` に保存している資料は、
デジタル庁が公開する「自治体標準オープンデータセット」の
公式資料です。

出典：

デジタル庁「自治体標準オープンデータセット（正式版）」

https://www.digital.go.jp/resources/open_data/municipal-standard-data-set-test

利用条件：

公共データ利用規約（第1.0版）（PDL1.0）

https://www.digital.go.jp/resources/open_data/public_data_license_v1.0

Open Infra Japan で公式資料を基にスキーマの抽出、
形式変換その他の加工を行ったデータについては、
デジタル庁の原資料を基に Open Infra Japan が加工したものであることを
明示します。
