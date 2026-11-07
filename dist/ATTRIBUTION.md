# 給水スポット公開データの出典・帰属

給水サービスの情報提供元は `refill-water-spots.csv` / `refill-discount-services.csv` の `source_url` を参照してください。
座標の出典は `refill-publication-attribution.csv` の `coordinate_source_reference` と `coordinate_source_name` に、サービス情報とは別に記録しています。
割引16件の座標出典は `refill-discount-coordinate-attribution.csv` に収録しています。Geolonia住所データの住所代表点と、OpenStreetMap由来の施設周辺代表点をsource_idごとに区別しています。国土地理院住所検索API由来だった5件は、出典と再利用条件が確認できるOSM座標へ置き換えました。2022年3月31日に閉店したタリーズコーヒー横浜市大附属病院店は現行サービスCSVから除外しています。
給水スポットや店舗の営業状況・設備稼働・個別のサービス提供状況には未確認のものがあり、掲載は現況を保証しません。

## OpenStreetMap
座標の一部にOpenStreetMap contributors のデータを使用しています。表示時は「© OpenStreetMap contributors」と明示し、データを配布する場合はODbL 1.0へのリンクを示してください。
ライセンス: [Open Database License (ODbL) 1.0](https://opendatacommons.org/licenses/odbl/1-0/)
著作権・帰属案内: https://www.openstreetmap.org/copyright
ODbLでは、データベースを改変・派生して配布する場合に同じライセンスで提供する条件があります。独立したデータベースをまとめた集合データベースは派生データベースと異なる扱いです。今回の各座標の利用形態がどちらに当たるかはデータベース全体の構成で判断してください。OSM由来レコードと参照先は帰属CSVで特定できます。
使用したOSMスナップショット名・日付はsource_idごとの座標出典欄に記録しています。

## Geolonia住所データ
使用データ: Geolonia Japanese Addresses v2。住所単位の配信元は `https://japanese-addresses-v2.geoloniamaps.com/api/ja/` 以下で、対象住所に応じた `地番.txt` / `住居表示.txt` 等を参照しています。公開成果物ではこの住所データを使って施設の代表座標を補完しました。入口や給水設備そのものの位置を示すものではありません。
配信データの系統はデジタル庁アドレス・ベース・レジストリ由来として記録されています。17件の再照合で使用したAPIデータ更新番号は `meta.updated=1735102668`（2024-12-25 04:57:48 UTC、2026-11-04取得）です。処理記録で確認できる住所正規化ライブラリの版は `@geolonia/normalize-japanese-addresses 3.1.3` です。過去に取得した給水座標298件については個別のAPI更新番号が記録されていません。
データライセンス: CC BY 4.0。出典を表示してください: [CC BY 4.0 日本語](https://creativecommons.org/licenses/by/4.0/deed.ja)。対象source_idと参照URLは帰属CSVを参照してください。

## 国土地理院由来の給水座標
給水CSVの一部は国土地理院の指定緊急避難場所CSV（自治体提供データ）を座標出典として記録しています。割引サービス5件で以前使用していた住所検索API由来の位置は公開成果物から除き、ライセンスと出典を確認できるOSM由来の施設周辺代表点へ置き換えました。出典URLは各帰属CSVに記録しています。
国土地理院コンテンツ利用規約（令和7年11月20日改正）は、特段の記載がないサイトコンテンツに公共データ利用規約（第1.0版）を適用し、出典と加工の明示を求める一方、外部データベース等とのAPI連携で取得した内容は提供元の利用条件に従うと定めています。国土地理院の2026年度地名検索API仕様資料は、address-search APIが国土地理院整備の地名データとCSISシンプルジオコーディング実験の検索結果をマージして返すと説明しています。このため、国土地理院サイト全般のPDL1.0記載だけでは、今回の個々の応答座標の再配布許諾を確定できません。
`https://msearch.gsi.go.jp/address-search/AddressSearch` の利用条件が未確定だった割引サービス5件のAPI座標は公開成果物に含めず、OSM由来の施設周辺代表点へ置き換えました。過去の調査経緯は作業記録に残していますが、今回の公開データの座標出典ではありません。
参考: [国土地理院コンテンツ利用規約](https://www.gsi.go.jp/kikakuchousei/kikakuchousei40182.html)、[国土地理院・住所検索API仕様資料](https://www.gsi.go.jp/SERVICE/keiyaku/oc_20260428_02.pdf)、[CSISシンプルジオコーディング実験・参加規約](https://geocode.csis.u-tokyo.ac.jp/home/simple-geocoding/simple-geocoding-tems-of-use/)、[国土地理院・測量成果利用手続](https://www.gsi.go.jp/LAW/2930-qa.html)

住所代表点・施設代表点の精度や個別の再利用条件はsource_id別の帰属CSVと元出典を確認してください。自治体等のサービス情報URLと座標出典URLを同一の出典として扱わないでください。

参照: https://geolonia.github.io/japanese-addresses-v2/

## 公衆トイレの住所座標補完

`facilities-official.csv` の住所参照点による公衆トイレ補完は、Geolonia Japanese Addresses v2由来368件と、Jageocoder住所データベース由来680件です。レコード単位の照合住所、座標、精度、出典URL、利用条件、加工内容は `public-toilet-coordinate-attribution.csv` に記録しています。これらは住所参照点であり、トイレ入口の実測位置ではありません。

出典: [Geolonia Japanese Addresses v2](https://github.com/geolonia/japanese-addresses-v2)
ライセンス: [Creative Commons Attribution 4.0 International](https://creativecommons.org/licenses/by/4.0/)
加工: 住所表記・自治体を照合し、施設レコードの空欄座標に住所参照点を追加。

## Jageocoder住所データベースの公衆トイレ座標

`facilities-official.csv` の公衆トイレ680件に、ローカルで使用した「jageocoder 用住所データベース（住居表示レベル）」の住所参照点を追加しました。デモサイト/APIは使用していません。辞書READMEの日付は2025-04-23です。Jageocoderライブラリは2.2.1.1、`dictionary_version()` の20230927は辞書形式の互換バージョンであり、住所データのリリース日・版番号ではありません。`installed_dictionary_version()` の20261025は辞書に `metadata.txt` がない場合のREADME更新日時のフォールバック値であり、データ版として扱いません。現存情報から公式配布アーカイブのファイル名までは確定できません。

辞書READMEは、歴史的行政区域データセットβ版地名辞書、国土交通省の位置参照情報、Geolonia住所データ、国土地理院の電子国土基本図（地名情報）住居表示住所、日本郵便の郵便番号データ、デジタル庁アドレス・ベース・レジストリ、法務省の登記所備付地図データ（デジタル庁加工）を組み合わせた複合辞書と説明しています。使用READMEが記録するデータ時点は、歴史的行政区域2022年度版（2024-01-06取得）、国交省位置参照情報令和5年（大字町丁目17.0b／街区22.0a、2024-06-13取得）、Geolonia v0.6.6（2024-06-13取得）、国土地理院住居表示住所2025-03-26更新版（2025-04-03取得、承認R 7JHs 54）、郵便番号2025-03-31更新版、アドレス・ベース・レジストリ2025-03-31／04-01等更新分、登記所備付地図データ2024-05-09更新分（2025-04-03取得）です。READMEの利用条件では、歴史的行政区域とGeoloniaはCC BY 4.0、国交省・デジタル庁・登記所備付地図データは政府標準利用規約第2.0版、日本郵便データは自由配布、国土地理院住居表示住所は記載の測量法承認によるとされています。READMEに従い、公開成果物では次の出典・加工表示を行います。

- 国土交通省「位置参照情報（大字町丁目・街区レベル）令和5年」を加工: https://nlftp.mlit.go.jp/cgi-bin/isj/dls/_choose_method.cgi
- 国土地理院「電子国土基本図（地名情報）住居表示住所」を加工（国土地理院長承認（使用）R 7JHs 54）: https://www.gsi.go.jp/kihonjohochousa/jukyo_jusho.html
- Geolonia Inc.「Geolonia 住所データ」を加工: https://geolonia.github.io/japanese-addresses/
- デジタル庁「アドレス・ベース・レジストリ」を加工: https://www.digital.go.jp/policies/base_registry_address
- 「登記所備付地図データ」（法務省）をデジタル庁が加工したデータを再加工: https://front.geospatial.jp/moj-chizu-xml-readme/

Jageocoderのソフトウェアライセンス（MIT）は住所辞書データの利用許諾として扱っていません。住所データベースREADMEの利用条件では、商用・非商用利用が認められ、二次利用で上記の出典・加工を表示するよう定めています。辞書そのものを再配布するのではなく、住所に照合した座標をCSVの表データとして公開しています。詳細は[Jageocoder公式の利用条件・出典](https://jageocoder.info-proto.com/license)と、使用辞書に同梱された2025-04-23付READMEを参照してください。

採用した680件は、自治体コード一致、住所文字列全体の一致、未解析末尾なしを確認したlevel 7または8の点です。level 7は街区・道路・地番、level 8は住居番号・枝番の住所参照点です。辞書の検索結果からは個々の点に使われた構成データセットを一意に割り当てられないため、辞書README記載の複合データ全体の出典を表示しています。住所代表点であり、各トイレの入口位置ではありません。照合住所・住所レベル・座標・辞書情報・加工内容は `public-toilet-coordinate-attribution.csv` を参照してください。
