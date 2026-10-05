from __future__ import annotations

import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG = REPO_ROOT / "catalog" / "datasets.csv"
RAW_ROOT = REPO_ROOT / "data" / "raw"
NORMALIZED_ROOT = REPO_ROOT / "data" / "normalized"
OVERRIDES = REPO_ROOT / "tools" / "normalize" / "progress_overrides.csv"


@dataclass(frozen=True)
class ProgressItem:
    prefecture_code: str
    prefecture_name: str
    municipality_code: str
    municipality_name: str
    status: str
    reason: str = ""


@dataclass
class ProgressSummary:
    items: list[ProgressItem]

    @property
    def total(self) -> int:
        return len(self.items)

    def by_status(self) -> dict[str, list[ProgressItem]]:
        grouped: dict[str, list[ProgressItem]] = defaultdict(list)
        for item in self.items:
            grouped[item.status].append(item)
        return grouped


STATUS_LABELS = {
    "complete": "正規化済み",
    "pending": "元データあり・未正規化",
    "review": "内容確認が必要",
    "reacquire": "元データ再取得",
    "not_acquired": "元データ未取得",
    "unavailable": "データ取得不可",
}

STATUS_ORDER = (
    "complete",
    "pending",
    "review",
    "reacquire",
    "not_acquired",
    "unavailable",
)


def _read_overrides() -> dict[str, tuple[str, str]]:
    if not OVERRIDES.exists():
        return {}
    out: dict[str, tuple[str, str]] = {}
    with OVERRIDES.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            code = (row.get("municipality_code") or "").strip()
            status = (row.get("status") or "").strip()
            reason = (row.get("reason") or "").strip()
            if not code or status not in STATUS_LABELS:
                continue
            out[code] = (status, reason)
    return out


def _has_raw(pref_code: str, municipality_code: str) -> bool:
    if not RAW_ROOT.exists():
        return False
    for pref_dir in RAW_ROOT.glob(f"{pref_code}-*"):
        for mun_dir in pref_dir.glob(f"{municipality_code}-*"):
            data_dir = mun_dir / "public-toilet"
            if data_dir.exists() and any(p.is_file() for p in data_dir.iterdir()):
                return True
    return False


def _has_normalized(pref_code: str, municipality_code: str) -> bool:
    if not NORMALIZED_ROOT.exists():
        return False
    for pref_dir in NORMALIZED_ROOT.glob(f"{pref_code}-*"):
        for mun_dir in pref_dir.glob(f"{municipality_code}-*"):
            if (mun_dir / "public-toilet" / "public-toilet.csv").is_file():
                return True
    return False


def load_progress(prefecture_codes: Iterable[str] | None = None) -> ProgressSummary | None:
    if not CATALOG.exists():
        return None

    scope = set(prefecture_codes or ())
    overrides = _read_overrides()

    municipalities: dict[str, dict[str, str]] = {}
    with CATALOG.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            if (row.get("dataset_type") or "").strip() != "public-toilet":
                continue
            if (row.get("publication_status") or "").strip() != "published":
                continue
            pref_code = (row.get("prefecture_code") or "").strip()
            if scope and pref_code not in scope:
                continue
            code = (row.get("municipality_code") or "").strip()
            if not code:
                continue
            municipalities.setdefault(code, {
                "prefecture_code": pref_code,
                "prefecture_name": (row.get("prefecture_name") or "").strip(),
                "municipality_name": (row.get("municipality_name") or "").strip(),
            })

    items: list[ProgressItem] = []
    for code, meta in sorted(municipalities.items()):
        pref_code = meta["prefecture_code"]
        if _has_normalized(pref_code, code):
            status, reason = "complete", ""
        elif code in overrides:
            status, reason = overrides[code]
        elif _has_raw(pref_code, code):
            status, reason = "pending", "元データあり・正規化未完了"
        else:
            status, reason = "not_acquired", "カタログ登録あり・元データファイル未保存"

        items.append(ProgressItem(
            prefecture_code=pref_code,
            prefecture_name=meta["prefecture_name"],
            municipality_code=code,
            municipality_name=meta["municipality_name"],
            status=status,
            reason=reason,
        ))

    return ProgressSummary(items)


def _display_item(item: ProgressItem) -> str:
    place = f"{item.prefecture_name} {item.municipality_name}".strip()
    text = f"{place} ({item.municipality_code})"
    if item.reason:
        text += f" — {item.reason}"
    return text


def print_progress_summary(
    prefecture_codes: Iterable[str] | None = None,
    *,
    max_items_per_status: int = 20,
) -> None:
    summary = load_progress(prefecture_codes)
    print()
    print("公衆トイレデータの整備状況:")
    if summary is None:
        print("  集計できません: catalog/datasets.csv がこの実行環境にありません")
        return

    grouped = summary.by_status()
    complete = len(grouped.get("complete", []))
    remaining = summary.total - complete

    print(f"  対象自治体: {summary.total}")
    print(f"  正規化済み: {complete}")
    print(f"  残件: {remaining}")
    print("  残件内訳:")
    for status in ("pending", "review", "reacquire", "not_acquired", "unavailable"):
        print(f"    {STATUS_LABELS[status]}: {len(grouped.get(status, []))}")

    if not remaining:
        return

    print()
    print("残件一覧:")
    for status in ("pending", "review", "reacquire", "not_acquired", "unavailable"):
        items = grouped.get(status, [])
        if not items:
            continue
        print(f"  {STATUS_LABELS[status]}:")
        for item in items[:max_items_per_status]:
            print(f"    - {_display_item(item)}")
        if len(items) > max_items_per_status:
            print(f"    - ...ほか{len(items) - max_items_per_status}自治体")

    if grouped.get("not_acquired"):
        print()
        print("  ※「元データ未取得」は、データを取得できないという意味ではありません。")
        print("    対象には含まれていますが、元データファイルがまだ保存されていない自治体です。")
    if grouped.get("unavailable"):
        print("  ※「データ取得不可」は、公開元の事情などで取得できないことを確認済みの自治体です。")
