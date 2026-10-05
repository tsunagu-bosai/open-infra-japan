# 公衆トイレ正規化ツール

公開・保守時の入口は **都道府県 → 地方ブロック → 全国** の3層です。

## 実行単位

```bash
# 都道府県
python3 tools/normalize/prefectures/p23_aichi.py --list
python3 tools/normalize/prefectures/p23_aichi.py --validate

# 8地方区分
python3 tools/normalize/regions/chubu.py --list

# 全国
python3 tools/normalize/all_japan.py --list
```

地方区分は本プロジェクト内で固定します。三重県は近畿地方、沖縄県は九州地方に含めます。

## 8地方区分

| 地方 | 都道府県 |
| --- | --- |
| 北海道地方 | 北海道 |
| 東北地方 | 青森、岩手、宮城、秋田、山形、福島 |
| 関東地方 | 茨城、栃木、群馬、埼玉、千葉、東京、神奈川 |
| 中部地方 | 新潟、富山、石川、福井、山梨、長野、岐阜、静岡、愛知 |
| 近畿地方 | 三重、滋賀、京都、大阪、兵庫、奈良、和歌山 |
| 中国地方 | 鳥取、島根、岡山、広島、山口 |
| 四国地方 | 徳島、香川、愛媛、高知 |
| 九州地方 | 福岡、佐賀、長崎、熊本、大分、宮崎、鹿児島、沖縄 |

本プロジェクトでは三重県を近畿、沖縄県を九州地方に固定します。

## ディレクトリ責務

- `prefectures/`: 47都道府県の公開入口。対象自治体と実装の対応を明示する。
- `regions/`: 北海道・東北・関東・中部・近畿・中国・四国・九州の8入口。
- `all_japan.py`: 8地方を順に実行する全国入口。
- `implementations/`: 非標準データ用の正規化ロジック。作業順の `next*` / `safe*` 名を廃止し、内容が分かる名前に変更。
- `tools/normalize_public_toilet.py --only-standard`: 完全に公式39列と一致するrawを県単位で補完処理する。
- `core/`: routing/runner。
- `registry.csv`: 都道府県・実装・対象自治体の機械可読対応表。

## 重要

過去に正規化後のCSVへ適用していた補正は、すべて該当する `implementations/` へ吸収済みです。
`corrections/` 移行層および correction 実行機構は撤去し、各正規化処理だけで同じ成果物を再生成する構成にしています。

また `implementations/fukui_english39_*.py` は、旧English39形式との互換処理を内部に持ちますが、取得済みrawから直接再生成する構成へ移行済みです。

<!-- normalize-test-mode -->

## 再生成テスト（`--test`）

正規化処理が、取得済みの元データから現在の正規化CSVを再生成できるか確認する場合は
`--test` を使用します。

`--test` は通常の `data/normalized/` を変更しません。実行時に一時テスト環境を作成し、
空の `data/normalized/` に対して正規化を実行します。

このテストには、公開元から取得した `data/raw/` が必要です。
元データそのものはこの公開リポジトリには含めていないため、
clone直後の公開リポジトリだけでは全国再生成テストは完結しません。

`data/raw/` を保持している作業環境では、元データ、schema、patch等を参照して、
公開前の再現性確認や正規化ロジック変更後の確認に利用できます。

### 地方単位の再生成テスト

例: 中部地方

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/normalize/regions/chubu.py   --test --validate --continue-on-error
```

テスト成功時は、通常の整備状況とは区別して次のように表示されます。

```text
再生成テスト結果:
  対象自治体: 87
  今回再生成できた: 87
  今回再生成できなかった: 0
```

### 都道府県単位

例: 愛知県

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/normalize/prefectures/p23_aichi.py   --test --validate
```

### 全国

```bash
PYTHONDONTWRITEBYTECODE=1 python3 tools/normalize/all_japan.py   --test --validate --continue-on-error
```

### 主なオプション

- `--test`: 空の一時環境で元データから再生成テストを行います。
- `--validate`: 正規化後にvalidatorを実行します。
- `--continue-on-error`: 地方・全国実行で、一部の都道府県が失敗しても後続を続行します。
- `--overwrite`: 通常環境で既存の正規化CSVも元データから再作成します。
- `--verbose`: 詳細ログを画面にも表示します。
- `--list`: 実処理せず、処理計画と現在の整備状況を表示します。

`--test` の一時環境は毎回作り直されます。通常の正規化CSVを更新したい場合は
`--test` を付けずに実行してください。

<!-- normalize-output-root -->

## 出力先を変更する（`--output-root`）

通常は正規化CSVを `data/normalized/` に保存します。

検証用の出力を別の場所へ保存したい場合は、`--output-root` で保存先ディレクトリを指定できます。

例: 中部地方の正規化CSVを `/tmp/chubu-output-root-test` に保存する場合

```bash
PYTHONDONTWRITEBYTECODE=1 \
python3 tools/normalize/regions/chubu.py \
  --output-root /tmp/chubu-output-root-test \
  --validate --continue-on-error
```

指定したディレクトリの下に、通常の `data/normalized/` と同じ都道府県・自治体構成でCSVを生成します。

```text
/tmp/chubu-output-root-test/
├── 15-新潟県/
├── 16-富山県/
├── 17-石川県/
├── 18-福井県/
├── 19-山梨県/
├── 20-長野県/
├── 21-岐阜県/
├── 22-静岡県/
└── 23-愛知県/
```

`--output-root` を使用した実行では、通常の `data/normalized/` は変更しません。

`--output-root` は、既存の正規化CSVと別に結果を確認したい場合や、差分比較用のCSVを作成したい場合に使用します。

### `--test` との違い

- `--test`
  - 毎回、空の一時テスト環境を自動作成します。
  - rawから全対象を再生成できるか確認する用途です。
  - テスト用出力先も自動で決まります。

- `--output-root DIR`
  - 出力先を利用者が指定します。
  - 指定先に既存CSVがある場合は、通常モードのスキップ規則が適用されます。
  - `--overwrite` を併用すると、指定先の既存CSVも再生成します。

`--test` と `--output-root` は同時に指定できません。
また、`--list` と `--output-root` も同時には使用しません。
