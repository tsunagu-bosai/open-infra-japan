#!/usr/bin/env python3
import csv, importlib.util, sys
from datetime import date, datetime, time

from pathlib import Path

from tools.normalize.core.normalization import StandardCsvWriter
from tools.normalize.core.xlsx import read_xlsx_values

ROOT = Path.cwd()
RAW = ROOT/"data/raw"
OUT = ROOT/"data/normalized"
SCHEMA_PATH = ROOT/"schema/standard/public-toilet/schema.csv"
GENERIC = ROOT/"tools/normalize_public_toilet.py"

TARGETS = {
"03207":("03-岩手県","03207-久慈市",{"多機能トイレ数":1}),
"04100":("04-宮城県","04100-仙台市",{"":3}),
"05209":("05-秋田県","05209-鹿角市",{}),
"09201":("09-栃木県","09201-宇都宮市",{"多機能トイレ数":1}),
"11203":("11-埼玉県","11203-川口市",{"多機能トイレ数":1}),
"11225":("11-埼玉県","11225-入間市",{}),
"13225":("13-東京都","13225-稲城市",{"":1}),
"13229":("13-東京都","13229-西東京市",{"":5}),
"13201":("13-東京都","13201-八王子市",{"NO":1,"所管部課":1,"トイレへの誘導路として点字ブロックを敷設している":1,"トイレの位置等を音声で案内している":1,"戸の形式":1,"車椅子が出入りできる（出入口の有効幅員80cm以上）":1,"車椅子が転回できる（直径150cm以上の円が内接できる）":1,"便座に背もたれがある":1,"便座に手すりがある":1,"オストメイト用設備がある":1,"オストメイト用設備が温水対応している":1,"大型ベッドを備えている":1,"乳幼児用おむつ交換台等を備えている":1,"乳幼児用椅子を備えている":1,"非常用呼び出しボタンを設置している":1}),
"15212":("15-新潟県","15212-村上市",{"":2}),
"17201":("17-石川県","17201-金沢市",{"_id":1}),
"17209":("17-石川県","17209-かほく市",{}),
"17210":("17-石川県","17210-白山市",{"_id":1}),
"17212":("17-石川県","17212-野々市市",{"_id":1}),
"17365":("17-石川県","17365-内灘町",{"_id":1}),
"17463":("17-石川県","17463-能登町",{"多機能トイレ数":1}),
"24210":("24-三重県","24210-亀山市",{"多機能トイレ数":1}),
"24324":("24-三重県","24324-東員町",{"":11}),
"25204":("25-滋賀県","25204-近江八幡市",{"":1}),
"27203":("27-大阪府","27203-豊中市",{"多機能トイレ数":1}),
"42209":("42-長崎県","42209-対馬市",{"項目名":1}),
"42211":("42-長崎県","42211-五島市",{"多機能トイレ数":1}),
"42307":("42-長崎県","42307-長与町",{"多機能トイレ数":1}),
"43468":("43-熊本県","43468-氷川町",{"":17}),
"44211":("44-大分県","44211-宇佐市",{"":1}),
"47350":("47-沖縄県","47350-南風原町",{"HP先に画像リンク":1}),
}

SOURCE_SHEETS = {
    "11225": "13.公衆トイレ一覧",
    "13201": "八王子市_public_toilet",
}

PRESERVE_EXTRAS = {
    "13201": True,
}

def schema():
    with SCHEMA_PATH.open(encoding="utf-8-sig",newline="") as f:
        return [r["name"] for r in csv.DictReader(f)]

def enc(path):
    b=path.read_bytes()
    for e in ("utf-8-sig","utf-8","cp932","shift_jis"):
        try: b.decode(e); return e
        except UnicodeDecodeError: pass
    raise RuntimeError(f"cannot decode {path}")

def extras(header, sch):
    d={}
    for x in header:
        if x not in sch: d[x]=d.get(x,0)+1
    return d

def note(cur, s):
    cur=(cur or "").strip()
    return f"{cur} / {s}" if cur else s

def cell_text(value):
    if value is None:
        return ""
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, datetime):
        if value.date() == date(1900, 1, 1):
            return value.strftime("%H:%M")
        return value.isoformat(sep=" ")
    return str(value).strip()

def read_tabular(path, sheet_name=None):
    if path.suffix.lower() == ".xlsx":
        values=read_xlsx_values(path, sheet_name)
        if not values:
            raise RuntimeError(f"{path}: empty XLSX")
        h=[cell_text(x) for x in values[0]]
        rows=[[cell_text(x) for x in row] for row in values[1:]]
        return h, rows, "xlsx"
    e=enc(path)
    with path.open(encoding=e,newline="") as f:
        r=csv.reader(f)
        h=next(r)
        return h, list(r), e

def read_source(path, sch, expected_extra, *, sheet_name=None, preserve_extras=False):
    h, source_rows, e = read_tabular(path, sheet_name)
    miss=[c for c in sch if c not in h]
    if miss: raise RuntimeError(f"{path}: missing {miss}")
    actual=extras(h,sch)
    if actual!=expected_extra:
        raise RuntimeError(f"{path}: extras actual={actual!r} expected={expected_extra!r}")
    idx={c:h.index(c) for c in sch}
    midx=h.index("多機能トイレ数") if "多機能トイレ数" in h else None
    extra_indexes=[(i, name) for i, name in enumerate(h) if name not in sch and name]
    rows=[]
    for ln,v in enumerate(source_rows,2):
        if not any((x or "").strip() for x in v): continue
        if len(v)<len(h): v=v+[""]*(len(h)-len(v))
        if len(v)>len(h): raise RuntimeError(f"{path}:{ln}: too many columns")
        row={c:(v[idx[c]] or "").strip() for c in sch}
        if midx is not None:
            mv=(v[midx] or "").strip()
            if mv: row["備考"]=note(row["備考"],f"原データ多機能トイレ数={mv}")
        if preserve_extras:
            for i, name in extra_indexes:
                value=(v[i] or "").strip()
                if value:
                    row["備考"]=note(row["備考"],f"原データ{name}={value}")
        rows.append(row)
    return rows,e



NUMERIC_FIELDS = [
    "男性トイレ総数",
    "男性トイレ数（小便器）",
    "男性トイレ数（和式）",
    "男性トイレ数（洋式）",
    "女性トイレ総数",
    "女性トイレ数（和式）",
    "女性トイレ数（洋式）",
    "男女共用トイレ総数",
    "男女共用トイレ数（和式）",
    "男女共用トイレ数（洋式）",
    "バリアフリートイレ数",
]

BOOL_FIELDS = [
    "車椅子使用者用トイレ有無",
    "乳幼児用設備設置トイレ有無",
    "オストメイト設置トイレ有無",
]


def set_value(row, field, new, note_field=None):
    old = (row.get(field) or "").strip()
    if old == new:
        return 0
    if note_field:
        row[note_field] = note(
            row.get(note_field, ""),
            f"原データ{field}={old}",
        )
    row[field] = new
    return 1


def apply_superset_corrections(code, rows):
    n = 0

    if code == "04100":
        for row in rows:
            if (
                row.get("男女共用トイレ数（洋式）") or ""
            ).strip() == "0..":
                n += set_value(
                    row,
                    "男女共用トイレ数（洋式）",
                    "0",
                    "備考",
                )

            for field in NUMERIC_FIELDS + BOOL_FIELDS:
                if (row.get(field) or "").strip() == "-":
                    n += set_value(row, field, "", "備考")

    elif code == "09201":
        for row in rows:
            for field in (
                "全国地方公共団体コード",
                "所在地_全国地方公共団体コード",
            ):
                if (row.get(field) or "").strip() == "92011":
                    n += set_value(
                        row,
                        field,
                        "092011",
                        "備考",
                    )

            if (row.get("緯度") or "").strip() == "369.56056":
                n += set_value(row, "緯度", "", "備考")

    elif code == "15212":
        for row in rows:
            start = (row.get("利用開始時間") or "").strip()
            end = (row.get("利用終了時間") or "").strip()

            if end == "24":
                n += set_value(
                    row,
                    "利用終了時間",
                    "23:59",
                    "利用可能時間特記事項",
                )

            if end == "日没":
                n += set_value(
                    row,
                    "利用終了時間",
                    "",
                    "利用可能時間特記事項",
                )

            if start == "24時間利用可能":
                n += set_value(
                    row,
                    "利用開始時間",
                    "00:00",
                    "利用可能時間特記事項",
                )

            if end == "24時間利用可能":
                n += set_value(
                    row,
                    "利用終了時間",
                    "23:59",
                    "利用可能時間特記事項",
                )

    elif code == "17212":
        for row in rows:
            if (row.get("利用終了時間") or "").strip() == "24:00":
                n += set_value(
                    row,
                    "利用終了時間",
                    "23:59",
                    "備考",
                )

    elif code == "24324":
        for row in rows:
            lat = (row.get("緯度") or "").strip()
            if lat.endswith(","):
                stripped = lat[:-1]
                try:
                    float(stripped)
                except ValueError:
                    pass
                else:
                    n += set_value(row, "緯度", stripped, "備考")

            if (
                row.get("バリアフリートイレ数") or ""
            ).strip() == "可":
                n += set_value(
                    row,
                    "バリアフリートイレ数",
                    "",
                    "備考",
                )

            if (
                row.get("車椅子使用者用トイレ有無") or ""
            ).strip() == "可":
                n += set_value(
                    row,
                    "車椅子使用者用トイレ有無",
                    "有",
                    "備考",
                )

    elif code == "42211":
        expected = "422118"
        for row in rows:
            for field in (
                "全国地方公共団体コード",
                "所在地_全国地方公共団体コード",
            ):
                value = (row.get(field) or "").strip()
                if value and value != expected:
                    n += set_value(
                        row,
                        field,
                        expected,
                        "備考",
                    )

    elif code == "42307":
        for row in rows:
            if (
                row.get("乳幼児用設備設置トイレ有無") or ""
            ).strip() == "1":
                n += set_value(
                    row,
                    "乳幼児用設備設置トイレ有無",
                    "有",
                    "備考",
                )

    elif code == "43468":
        for row in rows:
            for field in ("利用開始時間", "利用終了時間"):
                if (row.get(field) or "").strip() == "-":
                    n += set_value(
                        row,
                        field,
                        "",
                        "利用可能時間特記事項",
                    )

            if (
                row.get("利用終了時間") or ""
            ).strip() == "21：00":
                n += set_value(
                    row,
                    "利用終了時間",
                    "21:00",
                    "備考",
                )


    return n


def main():
    sch=schema()
    if len(sch)!=39: raise RuntimeError(f"schema={len(sch)}")
    sp=importlib.util.spec_from_file_location("n",GENERIC)
    mod=importlib.util.module_from_spec(sp); sys.modules["n"]=mod; sp.loader.exec_module(mod)
    prepared=[]
    for code,(pd,md,expected_extra) in TARGETS.items():
        rd=RAW/pd/md/"public-toilet"
        files=sorted([*rd.glob("*.csv"), *rd.glob("*.xlsx")])
        if len(files)!=1: raise RuntimeError(f"{code}: source count={len(files)}")
        dest=OUT/pd/md/"public-toilet/public-toilet.csv"
        if dest.exists(): raise RuntimeError(f"{code}: output exists")
        rows,e=read_source(
            files[0],
            sch,
            expected_extra,
            sheet_name=SOURCE_SHEETS.get(code),
            preserve_extras=PRESERVE_EXTRAS.get(code, False),
        )
        if not rows: raise RuntimeError(f"{code}: no data rows")
        for row in rows:
            row["利用開始時間"]=mod.normalize_time(row["利用開始時間"])
            row["利用終了時間"]=mod.normalize_time(row["利用終了時間"])
        apply_superset_corrections(code, rows)
        patches=mod.load_patches(pd, md)
        applied, problems=mod.apply_patches(rows, patches, files[0])
        if problems:
            raise RuntimeError("\n".join(problems))
        prepared.append((code,md,files[0],dest,rows,e,applied))
    print("preflight OK:",len(prepared))
    for code,md,src,dest,rows,e,applied in prepared:
        StandardCsvWriter().write(dest, sch, rows)
        print(f"OK {code} {md}: rows={len(rows)} source={src.name} encoding={e} patches={applied}")

if __name__=="__main__":
    main()
