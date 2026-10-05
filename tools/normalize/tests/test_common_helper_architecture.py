from __future__ import annotations

import ast
import unittest
from pathlib import Path


REFACTORED_IMPLEMENTATIONS = {
    "alias_variants.py",
    "atsugi.py",
    "hayama.py",
    "hirakata.py",
    "ikoma.py",
    "kawachinagano.py",
    "kitakyushu.py",
    "legacy26_standard.py",
    "legacy32_standard.py",
    "minato.py",
    "nearstandard.py",
    "osaka_city.py",
    "simple_location.py",
    "bunkyo.py",
    "gifu_remaining.py",
    "kobe.py",
    "okayama_city.py",
    "sasebo.py",
    "suzuka.py",
    "tokushima_prefecture.py",
    "kamakura.py",
    "kumagaya.py",
    "kyoto.py",
    "nagakute.py",
    "saitama_remaining.py",
    "takarazuka.py",
    "aichi_custom.py",
    "fukui_ikeda.py",
    "ishikawa_variants.py",
    "nagano_custom.py",
    "tottori.py",
    "yamanashi_remaining.py",
    "nagoya.py",
    "gifu_custom.py",
    "yamanashi_custom.py",
    "chiba_standard_variants.py",
    "kibichuo.py",
    "hirakawa_namerikawa.py",
    "aizu_machida.py",
    "chippubetsu_fussa_matsuyama.py",
    "hitachi_shibuya_nakano_sabae.py",
    "karuizawa_uda_kainan_hiroshima.py",
    "manazuru_nagano_yokkaichi.py",
    "noshiro_namegata_meguro.py",
    "tama_shinshiro_kumano_kurume_taku.py",
    "fukui_english39_special.py",
    "fukui_english39_standard.py",
    "furano_oga_sanjo_oyabe_sakai.py",
    "hakodate_aomori_daisen_akiruno.py",
    "kasama_gosen_miyoshi_tamba_otoyo_genkai_tamana_nagomi.py",
    "legacy32_reviewed.py",
    "sakado_otsu.py",
    "gifu.py",
    "hiroshima.py",
    "kumamoto_takamori.py",
    "takamatsu.py",
    "uki_taketomi.py",
}
FORBIDDEN_LOCAL_HELPERS = {"clean", "append_note", "stable_id", "write_atomic"}


BOOLEAN_STRATEGY_IMPLEMENTATIONS = {
    "fukui_ikeda.py",
    "gifu_custom.py",
    "nagoya.py",
    "yamanashi_custom.py",
    "yamanashi_remaining.py",
}
TIME_STRATEGY_IMPLEMENTATIONS = {
    "suzuka.py",
    "okayama_city.py",
    "legacy26_standard.py",
    "ishikawa_variants.py",
    "aichi_custom.py",
    "fukui_ikeda.py",
    "gifu.py",
    "gifu_custom.py",
    "hirakata.py",
    "kumamoto_takamori.py",
    "legacy32_standard.py",
    "nagakute.py",
    "nagano_custom.py",
    "nagoya.py",
    "takamatsu.py",
    "takarazuka.py",
    "yamagata_funagata.py",
    "yamagata_tendo.py",
    "yamaguchi.py",
    "yamanashi_custom.py",
    "yamanashi_remaining.py",
}


PHASE3_NO_ORDINARY_ROW_COUNT = {
    "bunkyo.py",
    "gifu_remaining.py",
    "kobe.py",
    "okayama_city.py",
    "sasebo.py",
    "suzuka.py",
    "tokushima_prefecture.py",
    "kamakura.py",
    "kumagaya.py",
    "kyoto.py",
    "nagakute.py",
    "saitama_remaining.py",
    "takarazuka.py",
    "aichi_custom.py",
    "fukui_ikeda.py",
    "ishikawa_variants.py",
    "nagano_custom.py",
    "tottori.py",
    "yamanashi_remaining.py",
    "gifu_custom.py",
    "nagoya.py",
    "yamanashi_custom.py",
    "chiba_standard_variants.py",
    "kibichuo.py",
    "hirakawa_namerikawa.py",
    "aizu_machida.py",
    "chippubetsu_fussa_matsuyama.py",
    "hitachi_shibuya_nakano_sabae.py",
    "karuizawa_uda_kainan_hiroshima.py",
    "manazuru_nagano_yokkaichi.py",
    "noshiro_namegata_meguro.py",
    "tama_shinshiro_kumano_kurume_taku.py",
    "fukui_english39_special.py",
    "fukui_english39_standard.py",
    "furano_oga_sanjo_oyabe_sakai.py",
    "hakodate_aomori_daisen_akiruno.py",
    "kasama_gosen_miyoshi_tamba_otoyo_genkai_tamana_nagomi.py",
    "legacy32_reviewed.py",
    "sakado_otsu.py",
    "standard_superset.py",
    "archive_standard.py",
}
ORDINARY_ROW_NAMES = {
    "rows",
    "source_rows",
    "src_rows",
    "normalized",
    "out",
    "features",
    "csv_rows",
    "xls_rows",
    "all_rows",
}


def _is_len_of_ordinary_rows(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "len"
        and len(node.args) == 1
        and isinstance(node.args[0], ast.Name)
        and node.args[0].id in ORDINARY_ROW_NAMES
    )


def _is_numeric_literal(node: ast.AST) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, int)


def _is_cfg_rows_lookup(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Name)
        and node.value.id == "cfg"
        and isinstance(node.slice, ast.Constant)
        and node.slice.value == "rows"
    )



class CommonHelperArchitectureTest(unittest.TestCase):
    def test_refactored_handlers_do_not_reintroduce_common_helpers(self) -> None:
        root = Path(__file__).resolve().parents[1] / "implementations"
        violations: list[str] = []

        for filename in sorted(REFACTORED_IMPLEMENTATIONS):
            path = root / filename
            tree = ast.parse(path.read_text(encoding="utf-8"))
            defined = {
                node.name
                for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
            duplicate = sorted(defined & FORBIDDEN_LOCAL_HELPERS)
            if duplicate:
                violations.append(f"{filename}: definitions: {', '.join(duplicate)}")

            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id in FORBIDDEN_LOCAL_HELPERS
                ):
                    violations.append(
                        f"{filename}:{node.lineno}: bare call: {node.func.id}"
                    )

        self.assertFalse(
            violations,
            "common helpers reintroduced: " + "; ".join(violations),
        )



    def test_boolean_strategy_handlers_do_not_reintroduce_local_validator(self) -> None:
        root = Path(__file__).resolve().parents[1] / "implementations"
        violations: list[str] = []

        for filename in sorted(BOOLEAN_STRATEGY_IMPLEMENTATIONS):
            path = root / filename
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "validate_boolean"
                ):
                    violations.append(f"{filename}:{node.lineno}: definition")
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "validate_boolean"
                ):
                    violations.append(f"{filename}:{node.lineno}: bare call")

        self.assertFalse(
            violations,
            "local validate_boolean reintroduced: " + "; ".join(violations),
        )

    def test_time_strategy_handlers_do_not_reintroduce_local_normalize_time(self) -> None:
        root = Path(__file__).resolve().parents[1] / "implementations"
        violations: list[str] = []

        for filename in sorted(TIME_STRATEGY_IMPLEMENTATIONS):
            path = root / filename
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == "normalize_time"
                ):
                    violations.append(f"{filename}:{node.lineno}: definition")
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "normalize_time"
                ):
                    violations.append(f"{filename}:{node.lineno}: bare call")

        self.assertFalse(
            violations,
            "local normalize_time reintroduced: " + "; ".join(violations),
        )

    def test_phase3_handlers_do_not_hardcode_ordinary_row_counts(self) -> None:
        root = Path(__file__).resolve().parents[1] / "implementations"
        violations: list[str] = []

        for filename in sorted(PHASE3_NO_ORDINARY_ROW_COUNT):
            path = root / filename
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Compare):
                    continue
                expressions = [node.left, *node.comparators]
                has_row_len = any(_is_len_of_ordinary_rows(expr) for expr in expressions)
                has_number = any(_is_numeric_literal(expr) for expr in expressions)
                has_cfg_rows = any(_is_cfg_rows_lookup(expr) for expr in expressions)
                if has_row_len and (has_number or has_cfg_rows):
                    violations.append(f"{filename}:{node.lineno}")

            for node in ast.walk(tree):
                if not isinstance(node, ast.Dict):
                    continue
                for key, value in zip(node.keys, node.values):
                    if (
                        isinstance(key, ast.Constant)
                        and key.value == "rows"
                        and _is_numeric_literal(value)
                    ):
                        violations.append(f"{filename}:{node.lineno}: rows config")

        self.assertFalse(
            violations,
            "ordinary row-count hardcoding reintroduced: " + "; ".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
