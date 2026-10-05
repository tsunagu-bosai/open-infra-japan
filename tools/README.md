# Open Infra Japan tools

<!-- BEGIN TOOLS BEGINNER GUIDE -->

## 最初に読むところ

`tools/` には調査・取得・正規化・検査用のスクリプトがあります。

初めて使う場合、全部を理解する必要はありません。

まず使う可能性が高いのは次の2本です。

| 目的 | コマンド |
| --- | --- |
| 全国自治体の調査statusを再生成 | `python tools/catalog/build_public_toilet_municipality_status.py` |
| 正規化済みデータを検査 | `python tools/validate_public_toilet.py --input normalized` |

データを利用するだけなら `tools/` の実行自体が不要です。

全体の初心者向け手順は
`../GETTING_STARTED.md`
を先に参照してください。

### ツール群の大まかな役割

`tools/catalog/`

データセット探索、catalog作成、自治体status生成などを行います。

`tools/normalize/`

公開元ごとの非標準データを共通schemaへ変換します。

`tools/validate_public_toilet.py`

`data/normalized/` の公衆トイレデータを検査します。

`tools/download.py`

`catalog/datasets.csv` に登録されたURLをもとに、
元データ取得を補助します。

`tools/schema/`

標準schemaの管理・抽出に使用します。

### 注意

`data/raw/`、`sources/`、`catalog/reviews/` は作業環境用であり、
この公開リポジトリには含まれていません。

これらを入力とする調査・取得ツールを実行する場合は、
必要な元データや調査用ファイルを別途作業環境に用意してください。

現在の全国進捗の基準は

    catalog/public_toilet_municipality_status.csv

です。

candidate / discovery / review 系CSVは、
探索・検証工程の中間成果物を含みます。

<!-- END TOOLS BEGINNER GUIDE -->

## 公衆トイレ正規化の公開入口

正規化ツールは都道府県・8地方区分・全国の3層に整理しています。

- 都道府県: `tools/normalize/prefectures/`
- 地方ブロック: `tools/normalize/regions/`
- 全国: `tools/normalize/all_japan.py`
- 実装対応表: `tools/normalize/registry.csv`

新しい正規化処理は `next*` のような作業順名では追加せず、必ず該当都道府県の入口へ登録します。


Open Infra Japan
のデータ探索・確認・取得・正規化・検証に使用するツールの運用手順です。

この文書では、各ツールについて「何ができるか」だけでなく、「どこまで確認できるか」「何を保証しないか」「どの出力を人が確認する必要があるか」を記録します。

## 基本方針

ツールの出力は、原則として次の4種類に分けて扱います。

-   **原典・取得元記録**:
    `sources/`。公開元から取得したメタデータやAPIレスポンスを作業環境で保持する。このディレクトリは公開リポジトリには含めない。
-   **再生成可能な中間生成物**: `catalog/*candidate*.csv`、review
    queue、inspection結果など。元データとツールがあれば再生成できる。
-   **人手確認結果**:
    `catalog/reviews/` は作業環境で保持する人手確認結果で、公開リポジトリには含めない。`patches/public-toilet/` は正規化の再現に必要な検証済み補正として公開する。
-   **データ本体**: `data/raw/`
    は取得原本でGit管理対象外、`data/normalized/` はOpen Infra
    Japanが生成した正規化結果。

候補発見数は、公開データセット数や自治体の公開率を意味しません。検索サービスに収録されないポータルや、検索語に一致しないデータもあります。

各データセットの公開元更新日や確認日は `catalog/datasets.csv` を参照してください。READMEには調査途中の固定件数を記録せず、カタログをデータの鮮度に関する正本とします。

## パイプライン

``` text
                         ┌─ CKAN横断検索
公開元・データカタログ ─┼─ 地域ポータル直接API
                         └─ 個別公式サイト・既存取込
                                  ↓
                              candidates
                                  ↓
                    自治体解決・scope分類・grouping
                                  ↓
                              review queue
                                  ↓
                              人手レビュー
                                  ↓
                         catalog/datasets.csv
                                  ↓
                              download
                                  ↓
                              data/raw
                                  ↓
                    inspect / normalize / validate
                                  ↓
                         data/normalized
```

全国CKAN横断探索と地域ポータル直接探索は補完関係です。CKAN横断ルートだけでは発見できない公開データもあるため、地域ポータルや自治体公式サイトも確認します。

------------------------------------------------------------------------

## 1. 標準schema

### `tools/schema/extract_public_toilet_schema.py`

デジタル庁「自治体標準オープンデータセット」の原典XLSXから、公衆トイレ一覧のschemaを抽出します。

**出力**

``` text
schema/standard/public-toilet/schema.csv
```

現在の公衆トイレschemaは39項目です。

**できること**

公式XLSX内の `13.公衆トイレ一覧`
を読み、項目名、必須区分、説明、形式、例、英語名等をOpen Infra
Japan用schema CSVへ変換します。

**制約**

原典XLSXのシート名・セル配置を前提とするため、デジタル庁側の様式が変更された場合はツール修正が必要です。schema抽出は各自治体データが標準に準拠していることを保証しません。

------------------------------------------------------------------------

## 2. 全国CKAN横断探索

### `tools/catalog/discover_ckan_search.py`

CKAN横断検索から検索語に一致する全ページを取得します。

``` bash
python3 tools/catalog/discover_ckan_search.py --query 公衆トイレ
```

1リクエストあたりの件数はデフォルト100件で、`--rows`
で変更できます。APIが返す総件数までページングします。

**出力**

``` text
sources/ckan-search/public-toilet.json
catalog/ckan_search_candidates.csv
```

**制約**

-   CKAN横断検索に収録されていないポータルは発見できません。
-   検索結果件数は公衆トイレデータセット数そのものではありません。
-   説明文、タグ等へのヒットも含まれます。
-   API障害、仕様変更、検索インデックス更新状況の影響を受けます。
-   出力CSVの `source_url`
    は横断検索由来の情報であり、最終カタログ登録時は原則として元の公開元ページを確認します。

### `tools/catalog/filter_public_toilet_candidates.py`

横断検索結果を `likely / review / exclude` に分類します。

``` bash
python3 tools/catalog/filter_public_toilet_candidates.py
```

**判定方法と制約**

タイトル中の「公衆トイレ」「公園トイレ」「だれでもトイレ」等と、データ形式をヒューリスティックに評価します。タイトルに「トイレ」がない検索ヒットはexcludeになります。

これは最終判定ではありません。タイトルだけでは対象範囲やデータ内容を確認できず、偽陽性・偽陰性の可能性があります。exclude行もCSVから削除せず保持します。

### `tools/catalog/group_public_toilet_candidates.py`

候補間の重複・関連性を調べるためのgrouping情報を付与します。

**制約**

同じ自治体・タイトル・URL等の一致は「同一dataset
family」の手掛かりであり、真の重複を保証しません。異なる時点の版、同一データの複数カタログ掲載、同じ名称の別データを人が区別する必要があります。

### `tools/catalog/detect_candidate_municipalities.py`

候補のメタデータから自治体コード・自治体名の手掛かりを抽出します。

**制約**

数字の出現だけでは自治体コードと断定できません。特に裸の5桁数字は別の番号を誤検出する可能性があります。このツールの結果だけで自治体を確定しません。

### `tools/catalog/import_estat_municipalities.py`

e-Statから取得した市区町村コードCSVを、照合用の全国自治体マスターへ変換します。

``` bash
python3 tools/catalog/import_estat_municipalities.py \
  sources/municipalities/<downloaded-file>.csv
```

**出力**

``` text
data/reference/municipalities.csv
```

**制約**

参照マスターには指定都市の行政区等も含まれるため、全国の市町村数や公開率の分母としてそのまま使用しないでください。e-Stat原典更新時は再生成が必要です。

### `tools/catalog/resolve_candidate_municipalities.py`

抽出したコード・名称をe-Stat参照マスターと照合し、自治体を解決します。

**制約**

都道府県全体、複数自治体をまたぐデータ、交通・施設ネットワーク、名称が曖昧なものは自治体単位に解決できない場合があります。自動解決結果は公開元確認の代替ではありません。

### `tools/catalog/classify_public_toilet_scopes.py`

候補の対象範囲を分類し、採用候補かreview対象かを整理します。

**制約**

メタデータを使ったヒューリスティック分類です。`unknown`
やreviewを人手確認なしで最終カタログへ登録しません。

### `tools/catalog/build_public_toilet_review_queue.py`

scope分類結果から、人が確認すべき候補を優先度付きreview
queueへ変換します。

**制約**

queueは再生成可能な作業リストです。レビュー結果そのものではありません。

### `tools/catalog/apply_public_toilet_reviews.py`

永続化した人手レビューを生成済みqueueへ適用します。

**入力**

``` text
catalog/public_toilet_review_queue.csv
catalog/reviews/public-toilet.csv  # 作業環境用・公開repoには含まれません
```

**出力**

``` text
catalog/public_toilet_review_queue_reviewed.csv
```

**重要**

`catalog/reviews/public-toilet.csv` は作業環境で保持する人手確認済みデータです。
公開リポジトリには含まれません。
自動生成物として上書きしないでください。

**制約**

レビュー内容の正しさを自動検証するツールではありません。元ページの確認、対象範囲、ライセンス、公開状態等は人が確認します。

### `tools/catalog/report_public_toilet_coverage.py`

現在のCKAN候補がどの自治体まで到達しているかを集計します。


**重要な制約**

これは **discovery coverage** を確認するためのツールです。検索で到達できた自治体数を、そのまま全国自治体の公開率として解釈しないでください。参照マスターには行政区等が含まれ、CKAN横断検索に未収録の公開データもあります。

------------------------------------------------------------------------

## 3. 地域・自治体ポータル直接探索

### `tools/catalog/discover_ckan_portal.py`

CKAN互換ポータルから保存したAPI
JSONを読み、各datasetから代表resourceを1件選び、候補CSVへ変換します。

例:

``` bash
python3 tools/catalog/discover_ckan_portal.py \
  sources/ckan-portals/saitama/public-toilet.json \
  catalog/saitama_public_toilet_candidates.csv \
  --portal-id saitama \
  --prefecture-code 11 \
  --prefecture-name 埼玉県
```

**できること**

CSVを優先し、同一datasetに複数resourceがある場合は形式、resource名中の版の日付、更新/作成日、UTF-8表記等から代表resourceを選択します。CSVがなければJSON/GeoJSON、KML/SHP、HTML等を候補にします。

**制約**

-   APIへのアクセス自体はこのツールの役割ではなく、保存済みJSONを入力します。
-   「代表resource」は推定であり、dataset内の全resourceを捨ててよいという意味ではありません。原API
    JSONを保存します。
-   `package_url` がAPIレスポンスにない場合、`source_url`
    が空になる可能性があります。最終カタログ登録前に元datasetページを確認してください。
-   HTMLの先にある二段階配布、利用規約同意、JavaScript操作等は追跡しません。
-   portal metadataの `format`
    と実ファイル形式が一致するとは限りません。

### `tools/catalog/inspect_public_toilet_resources.py`

取得した公衆トイレresourceを公式39項目schemaと比較します。

現在のデフォルト値は埼玉調査用ですが、`--schema`、`--candidates`、`--files`、`--output`
で差し替え可能です。

**検査内容**

-   ファイルシグネチャによるCSV/XLSX判定
-   CSVのUTF-8 BOM / CP932判定
-   XLSXの `13.公衆トイレ一覧` シート読込
-   レコード数・列数
-   `declared_format` と `detected_format`
-   公式39項目とのheader比較

`schema_match` は次を使用します。

``` text
exact
trailing-empty-columns
extra-column
header-variation
legacy-or-independent
not-downloaded
error
```

`trailing-empty-columns`
は、余剰ヘッダーだけでなく全データ行の余剰セルが空であることも確認します。

**制約**

-   現在はCSV/XLSXを主対象としています。
-   XLSXでは `13.公衆トイレ一覧` というシート名を前提とします。
-   schema一致は値の正しさ、位置情報の正しさ、データの網羅性、ライセンス、公開状態を保証しません。
-   `header-variation`
    は表記を正規化すれば一致することを示す検査ラベルであり、配布元が公式標準準拠だと自動認定するものではありません。
-   `legacy-or-independent` から標準39項目への意味変換は行いません。

------------------------------------------------------------------------

## 4. 既存の個別カタログ取込

### `tools/catalog/import_tokyo.py`

東京都オープンデータカタログから保存した
`sources/13-tokyo/metadatalist.csv` を東京都候補CSVへ変換します。

**出力**

``` text
catalog/tokyo_candidates.csv
```

東京都向けに作られた個別importerで、全国汎用ツールではありません。

### `tools/catalog/merge_candidates.py`

candidate CSVを `catalog/datasets.csv`
へマージします。同一キーの重複登録を避ける初期運用ツールです。

**制約**

候補の内容を自動的に正しいと認定するものではありません。source
URL、download URL、license、coverage、update date、publication
status等を確認してから使用します。


## 5. 正式カタログから原本取得

### `tools/download.py`

`catalog/datasets.csv` の `download_url` からデータを `data/raw/`
へ取得します。

例:

``` bash
python3 tools/download.py --prefecture 13 --dataset public-toilet
```

`--overwrite`
を付けない限り既存ファイルをスキップします。`publication_status=published`
以外もスキップします。

**制約**

現在の実装には重要な制約があります。

-   保存先は `data/reference/municipalities.csv` の自治体名から現在の日本語ディレクトリ構造を生成します。
-   HTTP(S)で直接取得できるURLを前提とします。
-   利用規約への同意、ログイン、JavaScript操作、二段階リンク等には対応しません。
-   Content-Typeやファイルシグネチャを検証せず、portal
    metadataやURLからファイル名・拡張子を決めます。
-   一時ファイル + atomic
    rename、checksum、ETag/Last-Modifiedによる更新判定は未実装です。
-   `published` とHTTP取得成功/失敗は別概念ですが、専用の `fetch_status`
    はまだありません。

熊谷市のようなmanual-download対象を自動回避して取得しない運用が必要です。

------------------------------------------------------------------------

## 6. 原本の構造確認

### `tools/inspect_datasets.py`

rawファイルのCSV/XLSX構造を確認する補助ツールです。

**できること**

CSVの文字コード・header・行数、XLSXの構造等を確認します。

**制約**

対応形式には限りがあります。保存先の解決には `data/reference/municipalities.csv` を使用します。schema準拠性の最終判定やデータ内容の意味検証は行いません。

------------------------------------------------------------------------

## 7. 正規化

### `tools/normalize_public_toilet.py`

rawの公衆トイレCSV/XLSXを公式39項目順のUTF-8 BOM CSVへ変換します。

``` bash
python3 tools/normalize_public_toilet.py --prefecture 13
```

**出力**

``` text
data/normalized/<prefecture>/<municipality>/public-toilet/public-toilet.csv
```

**できること**

-   公式schema順の39列を出力
-   CSV: UTF-8 BOM、UTF-8、CP932、UTF-16を試行
-   XLSXを読込
-   時刻表現の安全な表記正規化
-   `24:00` を保持
-   検証済みpatchを、ID・field・original valueが一致した場合だけ適用
-   sourceファイル自体は変更しない
-   一時ファイルからatomic replaceして出力

**重要な制約**

このツールは **非標準schemaを意味的に変換するconverterではありません**。

各出力項目について `row.get(公式項目名, "")`
で取得するため、列名が異なるデータをそのまま通すと情報が空欄になります。

例えば本庄市の `男性トイレ数_小便器` を `男性トイレ数（小便器）`
に自動変換しません。上尾市、新座市、加須市等の旧形式・独自形式にも専用mappingが必要です。

したがって、resource
inspectionでschemaを確認せず非標準データへ実行しないでください。

またXLSXはactive sheetを読みます。複数sheet
workbookで公衆トイレsheetがactiveでない場合は、期待するデータを読めない可能性があります。

------------------------------------------------------------------------

## 8. 検証

### `tools/validate_public_toilet.py`

公衆トイレデータを公式schemaおよび値のルールに対して検証します。

**制約**

-   検証対象は `data/raw/` または `data/normalized/` に実在する自治体ディレクトリです。自治体情報は `data/reference/municipalities.csv` と照合します。
-   schemaや実装済みルールで検出できる問題だけを報告します。
-   ERRORが0でも現地の設備、座標、営業時間、網羅性が正しいことを保証しません。
-   曖昧な値を推測修正しません。
-   `24:00` の仕様解釈は確定していないためWARNING扱いです。
-   IDについて、原典から確証のない独自regexや12桁制約は課しません。

------------------------------------------------------------------------

## 9. patches

``` text
patches/public-toilet/<prefecture>/<municipality>.csv
```

元データに確認可能な誤りがあり、外部情報等で修正内容を検証できた場合のみ使用します。

patchは `ID + field + original_value`
が一致した場合だけ適用されます。元データが更新されて値が変わった場合、黙ってpatchせずエラーにします。

patchは人手検証結果なので、自動生成物として上書きしません。

------------------------------------------------------------------------

## 10. 現在の主な技術的課題

-   地域ポータル候補の `source_url`
    を確実に元datasetページへ結び付ける。
-   download時にContent-Type、magic bytes、checksum等を記録する。
-   `publication_status` と `fetch_status` を分離する。
-   manual-download / consent-required /
    second-hop等の取得方式を記録する。
-   非標準schema用converterを明示的に実装する。
-   全国統合データ生成時に、各レコードのsource/license/provenanceを追跡できるようにする。

## 全国公衆トイレ調査の進捗管理

### `tools/catalog/build_public_toilet_municipality_status.py`

全国自治体マスター、`catalog/datasets.csv`、自治体直接調査結果を突き合わせ、
自治体単位の最新ステータスを生成します。

実行コマンド:

`python3 tools/catalog/build_public_toilet_municipality_status.py`

出力:

`catalog/public_toilet_municipality_status.csv`

現在の全国調査の進捗確認では、このファイルを基準とします。

直接調査の詳細結果は作業環境の `catalog/reviews/` に保持しています。
このディレクトリは公開リポジトリには含めません。

公開リポジトリでは `catalog/public_toilet_municipality_status.csv` を
自治体単位の進捗確認に使用してください。

主なステータス:

- `cataloged`: データセット登録済み
- `searched-not-found`: 公式サイト等を直接確認したが対象の構造化データを確認できなかった
- `candidate`: 追加確認が必要な候補あり
- `not-searched`: 自治体単位の直接調査が未実施

candidate / discovery / review 系のCSVは探索・検証時の中間成果物であり、
現在の全国進捗そのものを表すものではありません。

### validator の重複ID

`tools/validate_public_toilet.py` では、公式データ由来のID重複を保持できるよう、
重複IDは `WARNING` として報告します。

元データのIDを正規化処理で任意に採番し直すことはしません。
