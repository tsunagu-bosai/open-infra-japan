import csv
from tools import normalize_public_toilet as common
from pathlib import Path

ROOT = Path.cwd()
RAW = ROOT / "data/raw/04-宮城県"
OUT = ROOT / "data/normalized/04-宮城県"
SCHEMA = ROOT / "schema/standard/public-toilet/schema.csv"

TARGETS = {
    "04202-石巻市",
    "04203-塩竈市",
    "04206-白石市",
    "04207-名取市",
    "04209-多賀城市",
    "04213-栗原市",
    "04214-東松島市",
    "04322-村田町",
    "04323-柴田町",
    "04361-亘理町",
    "04401-松島町",
    "04421-大和町",
    "04501-涌谷町",
}

with SCHEMA.open(encoding="utf-8-sig", newline="") as f:
    FIELDS = [r["name"] for r in csv.DictReader(f)]

ALIASES = {
    "名　称": "名称",
    "建物名等（方書）": "建物名等(方書)",
    "画像ライセンス": "画像_ライセンス",
}

LEGACY_MAP = {
    "NO": "ID",
    "No": "ID",
    "名称": "名称",
    "名称_カナ": "名称_カナ",
    "名称_英語": "名称_英語",
    "住所": "所在地_連結表記",
    "都道府県名": "所在地_都道府県",
    "市区町村名": "所在地_市区町村",
    "方書": "建物名等(方書)",
    "設置位置": "設置位置",
    "緯度": "緯度",
    "経度": "経度",
    "男性トイレ総数": "男性トイレ総数",
    "男性トイレ数（小便器）": "男性トイレ数（小便器）",
    "男性トイレ数（和式）": "男性トイレ数（和式）",
    "男性トイレ数（洋式）": "男性トイレ数（洋式）",
    "女性トイレ総数": "女性トイレ総数",
    "女性トイレ数（和式）": "女性トイレ数（和式）",
    "女性トイレ数（洋式）": "女性トイレ数（洋式）",
    "男女共用トイレ総数": "男女共用トイレ総数",
    "男女共用トイレ数（和式）": "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）": "男女共用トイレ数（洋式）",
    "車椅子使用者用トイレ有無": "車椅子使用者用トイレ有無",
    "車いす使用者用トイレ有無": "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無": "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無": "オストメイト設置トイレ有無",
    "利用開始時間": "利用開始時間",
    "利用終了時間": "利用終了時間",
    "利用可能時間特記事項": "利用可能時間特記事項",
    "画像": "画像",
    "画像_ライセンス": "画像_ライセンス",
    "備考": "備考",
}


def s(v):
    return "" if v is None else str(v).strip()


def read_csv(path):
    raw = path.read_bytes()

    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            pass
    else:
        raise RuntimeError(f"encoding: {path}")

    first = text.splitlines()[0] if text.splitlines() else ""
    delimiter = "\t" if first.count("\t") > first.count(",") else ","

    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))

    hi = next(
        i for i, row in enumerate(rows)
        if any(
            ALIASES.get(s(v), s(v)) == "名称"
            for v in row
        )
    )

    header = [
        ALIASES.get(s(v), s(v))
        for v in rows[hi]
    ]

    data = []
    for row in rows[hi + 1:]:
        if not any(s(v) for v in row):
            continue

        item = {}
        for i, value in enumerate(row):
            if i >= len(header):
                break
            key = header[i]
            if key:
                item[key] = s(value)

        data.append(item)

    return data, delimiter


def main() -> None:
    total = 0

    for src in sorted(RAW.glob("*/public-toilet/*")):
        municipality = src.parents[1].name

        if municipality not in TARGETS:
            continue

        if src.suffix.lower() != ".csv":
            continue

        rows, delimiter = read_csv(src)

        if not rows:
            print(municipality, "source=0 normalized=0")
            continue

        legacy = "都道府県コード又は市区町村コード" in rows[0]

        output = []

        for r in rows:
            name = s(r.get("名称"))
            if name in {"◎", "○", "△"}:
                continue

            meaningful = [
                s(v)
                for k, v in r.items()
                if k not in {
                    "ID", "NO", "No",
                    "全国地方公共団体コード",
                    "都道府県コード又は市区町村コード",
                    "地方公共団体名",
                    "都道府県名",
                    "市区町村名",
                }
                and s(v)
            ]
            if not meaningful:
                continue

            out = {field: "" for field in FIELDS}

            if legacy:
                for source, target in LEGACY_MAP.items():
                    if source in r and target in out:
                        out[target] = s(r[source])

                out["地方公共団体名"] = s(
                    r.get("市区町村名") or r.get("都道府県名")
                )

                code = s(r.get("都道府県コード又は市区町村コード"))
                if len(code) == 6 and code.isdigit():
                    out["全国地方公共団体コード"] = code

            else:
                for field in FIELDS:
                    if field in r:
                        out[field] = s(r[field])

            extras = []

            # 多機能トイレ数はバリアフリートイレ数へ変換しない。
            if s(r.get("多機能トイレ数")):
                extras.append(
                    "多機能トイレ数:" + s(r["多機能トイレ数"])
                )

            if s(r.get("多機能トイレ有無")):
                extras.append(
                    "多機能トイレ有無:" + s(r["多機能トイレ有無"])
                )

            if extras:
                note = s(out.get("備考"))
                out["備考"] = (
                    note + ("; " if note else "") + "; ".join(extras)
                )

            # 有無欄は「有」「無」だけ標準欄へ残す。
            for source_field, target_field in (
                ("車椅子使用者用トイレ有無", "車椅子使用者用トイレ有無"),
                ("車いす使用者用トイレ有無", "車椅子使用者用トイレ有無"),
                ("乳幼児用設備設置トイレ有無", "乳幼児用設備設置トイレ有無"),
                ("オストメイト設置トイレ有無", "オストメイト設置トイレ有無"),
            ):
                value = s(r.get(source_field))
                if value and value not in {"有", "無"}:
                    if out.get(target_field) == value:
                        out[target_field] = ""

                    note = s(out.get("備考"))
                    preserved = f"{source_field}:{value}"

                    if preserved not in note:
                        out["備考"] = (
                            note + ("; " if note else "") + preserved
                        )

            # 標準欄へ入れられない原典値は推測補正せず備考へ保存。
            def preserve_original(label, value):
                value = s(value)
                if not value:
                    return
                item = f"{label}:{value}"
                note = s(out.get("備考"))
                if item not in note:
                    out["備考"] = (
                        note + ("; " if note else "") + item
                    )

            # 自治体コードは6桁かつ当該自治体の正式コードと一致する場合だけ残す。
            expected_codes = {
                "04202-石巻市": "042021",
                "04203-塩竈市": "042030",
                "04206-白石市": "042064",
                "04207-名取市": "042072",
                "04209-多賀城市": "042099",
                "04213-栗原市": "042137",
                "04214-東松島市": "042145",
                "04322-村田町": "043222",
                "04323-柴田町": "043231",
                "04361-亘理町": "043613",
                "04401-松島町": "044016",
                "04421-大和町": "044211",
                "04501-涌谷町": "045012",
            }

            code = s(out.get("全国地方公共団体コード"))
            expected_code = expected_codes[municipality]

            if code and code != expected_code:
                preserve_original("全国地方公共団体コード", code)
                out["全国地方公共団体コード"] = ""

            # 明らかに緯度として成立しない数値も推測で小数点を補わない。
            lat_value = s(out.get("緯度"))
            if lat_value:
                try:
                    lat_number = float(lat_value)
                    if not -90 <= lat_number <= 90:
                        preserve_original("緯度", lat_value)
                        out["緯度"] = ""
                except ValueError:
                    preserve_original("緯度", lat_value)
                    out["緯度"] = ""

            # 「終日」は時刻値ではなく利用可能時間の情報として保持。
            if (
                s(out.get("利用開始時間")) == "終日"
                or s(out.get("利用終了時間")) == "終日"
            ):
                out["利用開始時間"] = ""
                out["利用終了時間"] = ""

                note = s(out.get("利用可能時間特記事項"))
                if "終日" not in note:
                    out["利用可能時間特記事項"] = (
                        f"{note}; 終日" if note else "終日"
                    )

            # 単独の「0」は 00:00 と断定しない。
            if s(out.get("利用開始時間")) == "0":
                preserve_original("利用開始時間", "0")
                out["利用開始時間"] = ""

            # 24:00 は 00:00 に変換すると日付の意味が変わるため退避。
            if s(out.get("利用終了時間")) == "24:00":
                preserve_original("利用終了時間", "24:00")
                out["利用終了時間"] = ""

            # 明白な緯度経度逆転だけ補正。
            try:
                lat = float(out["緯度"])
                lon = float(out["経度"])
                if 120 <= lat <= 150 and 20 <= lon <= 50:
                    out["緯度"], out["経度"] = (
                        out["経度"], out["緯度"]
                    )
            except (ValueError, TypeError):
                pass

            # 意味を変えない時刻書式のみ HH:MM に揃える。
            for field in ("利用開始時間", "利用終了時間"):
                value = s(out.get(field))
                parts = value.split(":")

                # 24:00 / 24:00:00 は翌日0時を表すため、
                # HH:MMへ変換せず原典値を備考へ保存する。
                if len(parts) in (2, 3):
                    try:
                        hour = int(parts[0])
                        minute = int(parts[1])

                        if hour == 24 and minute == 0:
                            preserve_original(field, value)
                            out[field] = ""
                            continue
                    except ValueError:
                        pass

                if len(parts) == 3 and parts[2] == "00":
                    parts = parts[:2]

                if len(parts) == 2:
                    try:
                        hour = int(parts[0])
                        minute = int(parts[1])
                        if 0 <= hour <= 23 and 0 <= minute <= 59:
                            out[field] = f"{hour:02d}:{minute:02d}"
                    except ValueError:
                        pass

            output.append(out)

        patches = common.load_patches("04-宮城県", municipality)

        if patches:
            applied, problems = common.apply_patches(
                output,
                patches,
                src,
            )
            if problems:
                raise RuntimeError(
                    f"{municipality}: patch errors: "
                    + " | ".join(problems)
                )
            print(
                f"{municipality}: patches applied={applied}"
            )

        dest = (
            OUT / municipality /
            "public-toilet/public-toilet.csv"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)

        with dest.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as f:
            writer = csv.DictWriter(
                f,
                fieldnames=FIELDS,
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(output)

        kind = "legacy32" if legacy else "current-like"
        sep = "TSV" if delimiter == "\t" else "CSV"

        print(
            municipality,
            f"source={len(rows)}",
            f"normalized={len(output)}",
            f"type={kind}",
            f"input={sep}",
        )

        total += len(output)

    print("total normalized:", total)


if __name__ == "__main__":
    main()
