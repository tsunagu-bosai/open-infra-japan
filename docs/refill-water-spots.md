# 全国給水スポット公開データ

全国の自治体・公的機関等が紹介する給水スポットと、マイボトル持参による割引サービスを別CSVで公開しています。公衆トイレ等を収録する `facilities-official.csv` には統合していません。

## 公開ファイルと件数

| ファイル | 件数 | 内容 |
| --- | ---: | --- |
| [`../dist/refill-water-spots.csv`](../dist/refill-water-spots.csv) | 4,093 | 座標がある公式掲載給水スポット（料金未確認を含む） |
| [`../dist/refill-discount-services.csv`](../dist/refill-discount-services.csv) | 16 | 既存形式のマイボトル割引サービス |
| [`../dist/mybottle-discount-locations-*.csv`](../dist/) | 2,102 | チェーン店舗候補（既存リンク2件を除き、新規位置2,100件） |
| [`../dist/water-search-facilities.json`](../dist/water-search-facilities.json) | 6,208 | 給水スポットと割引サービスの検索用結合データ（給水4,093、割引2,115） |
| [`../dist/refill-publication-attribution.csv`](../dist/refill-publication-attribution.csv) | 4,093 | 給水CSV各行のサービス情報元と座標出典・帰属 |
| [`../dist/refill-discount-coordinate-attribution.csv`](../dist/refill-discount-coordinate-attribution.csv) | 16 | 既存割引店舗の座標出典（Geolonia 11件、国土地理院住所検索5件） |
| [`../dist/ATTRIBUTION.md`](../dist/ATTRIBUTION.md) | — | 出典・帰属の表示案内 |

2026年版の給水CSVには `seasonal=true` の施設が84件あります。掲載候補4,102件のうち座標がない9件は、地図用CSVには含めていません。座標がないことを理由に内部の掲載候補自体を削除したものではありません。

## 無料給水と割引の区別

給水CSVの `service_type` は次の値を取ります。

- `free_refill`: 無料給水が確認された施設
- `unknown`: 公式の給水スポットとして掲載されていますが、料金に関する内部記録で無料を確認できていない施設。無料と断定する値ではありません

割引CSVでは、`discount` は商品・飲料購入時のマイボトル割引、`both` は割引に加えて無料給水も確認された施設です。有料飲料販売と割引のみの施設は `discount` です。給水施設と割引施設は別サービスとして収録され、同一建物や近接を理由に行を統合していません。

## 季節情報

- `seasonal=true`: 給水設備または施設の季節停止・期間限定利用が確認されたもの
- `seasonal=false`: 季節条件を確認し、季節停止・期間限定ではないと判定したもの。毎日・終日利用や設備の通年稼働を保証しません
- `seasonal=unknown`: 季節停止の有無が公開情報から確定できないもの

`seasonal=false` は季節条件を確認した結果、季節限定に該当しないと判断したことを表しますが、設備が毎日・終日または一年中稼働する保証ではありません。`seasonal=unknown` はその判定を裏付ける記録が不足している状態で、falseとは区別します。2026年版の現行CSVでは `true` 84件、`unknown` 4,009件、`false` 0件です。

`season_note` は `seasonal=true` の場合に利用者向けの期間説明を示します。それ以外では空欄です。2026年度など年度を含む案内は、その年度に確認された情報です。翌年度以降の利用を保証せず、年度をまたいで自動継続しません。利用前に施設・自治体の最新情報も確認してください。

## CSV列

### 給水スポット

`source_id`, `facility_name`, `address`, `latitude`, `longitude`, `source_url`, `service_type`, `seasonal`, `season_note`

### 割引サービス

`discount_id`, `candidate_id`, `facility_name`, `address`, `latitude`, `longitude`, `source_url`, `service_type`, `discount_content`

## 出典・帰属

各CSVの `source_url` は給水・割引サービス情報の提供元です。給水座標の出典は `refill-publication-attribution.csv`、既存割引店舗16件の座標出典は `refill-discount-coordinate-attribution.csv` の `coordinate_source_reference` / `coordinate_source_name` に記録しています（Geolonia 11件、国土地理院住所検索5件）。GSI住所検索由来の5件は住所代表点であり、店舗入口などの正確な位置ではありません。再利用条件が未確認のため、公開前に確認が必要です。新規チェーン店舗候補2,102件はOSM由来で、重複照合の確定リンク2件を除き、別業態確認待ち1件を検索対象から除外しています。Google Mapsの表示中心は公開座標に使用していません。OSM、Geolonia、国土地理院等の表示方法・利用条件は [`../dist/ATTRIBUTION.md`](../dist/ATTRIBUTION.md) と各帰属CSVを参照してください。サービスの情報提供元URLを座標の帰属表記の代用にしないでください。

タリーズコーヒー横浜市大附属病院店は閉店が確認されたため、現行の割引サービス一覧から除外しています。横浜市立大学の現行院内案内はCAFÉ COREを掲載し、同大学のキャンパスマップにはタリーズからCAFÉ COREへ変更した旨があります。

ライセンス全体の方針は [`../LICENSE-DATA.md`](../LICENSE-DATA.md) のとおり、各元データ提供者の利用条件を尊重します。

## 再生成・更新

公開CSVは、内部作業環境にある掲載評価・正規化データ・季節公開管理表・割引公開管理表から生成します。公開リポジトリには監査用入力、レビュー履歴、候補座標、内部関係台帳を置きません。

作業環境のリポジトリ親ディレクトリから、2026年版を再生成するコマンド:

```bash
python3 work/tools/export/build_refill_publication.py \
  --as-of-year 2026 \
  --output-dir /tmp/refill-publication-release
```

生成結果と件数・分類・季節情報・帰属を確認してから、給水CSV、割引CSV、給水帰属CSV、割引座標帰属CSV、`ATTRIBUTION.md` の5ファイルだけを `public/dist/` に反映します。検証JSONと給水・割引の内部関係表は公開リポジトリへコピーしません。

公開リポジトリのルートから、反映済みCSVのみを使って検証できます:

```bash
python3 tools/validate_refill_publication.py --as-of-year 2026
```

季節情報を更新する際は、確認済みの根拠と有効年度を内部管理表で更新してから再生成し、公開前検証を再実行してください。2026年度限定の情報を翌年度へ自動継続しないでください。
