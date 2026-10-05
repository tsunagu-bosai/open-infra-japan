from __future__ import annotations

import argparse
import contextlib
import importlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence, TextIO

from .registry import Handler
from .progress import print_progress_summary

REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_ROOT = Path(
    os.environ.get(
        "TSUNAGU_NORMALIZE_LOG_ROOT",
        str(REPO_ROOT / "logs" / "normalize" / "public-toilet"),
    )
)
NORMALIZED_ROOT = Path(
    os.environ.get(
        "TSUNAGU_NORMALIZE_OUTPUT_ROOT",
        str(REPO_ROOT / "data" / "normalized"),
    )
)


@dataclass
class RunResult:
    rc: int
    changed_files: list[Path] = field(default_factory=list)
    skipped_codes: list[str] = field(default_factory=list)
    failed_stage: str | None = None
    error: str | None = None
    failed_stages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class _DetailWriter:
    def __init__(self, log_file: TextIO, terminal: TextIO | None = None):
        self.log_file = log_file
        self.terminal = terminal

    def write(self, text: str) -> int:
        self.log_file.write(text)
        self.log_file.flush()
        if self.terminal is not None:
            self.terminal.write(text)
            self.terminal.flush()
        return len(text)

    def flush(self) -> None:
        self.log_file.flush()
        if self.terminal is not None:
            self.terminal.flush()


class Reporter:
    def __init__(self, scope: str, *, verbose: bool = False):
        self.verbose = verbose
        LOG_ROOT.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base = LOG_ROOT / f"{stamp}-{scope}.log"
        path = base
        suffix = 2
        while path.exists():
            path = base.with_name(f"{base.stem}-{suffix}{base.suffix}")
            suffix += 1
        self.path = path
        self._log = self.path.open("w", encoding="utf-8", newline="")
        self._detail = _DetailWriter(
            self._log,
            sys.__stdout__ if verbose else None,
        )
        self.log(f"started: {datetime.now().isoformat(timespec='seconds')}")
        self.log(f"repo: {REPO_ROOT}")
        self.log(f"verbose: {verbose}")

    def close(self) -> None:
        if not self._log.closed:
            self.log(f"finished: {datetime.now().isoformat(timespec='seconds')}")
            self._log.close()

    def log(self, text: str = "") -> None:
        self._log.write(text + "\n")
        self._log.flush()

    def stage(self, text: str) -> None:
        self.log()
        self.log(f"=== {text} ===")

    @contextlib.contextmanager
    def capture(self):
        with contextlib.redirect_stdout(self._detail), contextlib.redirect_stderr(self._detail):
            yield

    def log_exception(self) -> None:
        traceback.print_exc(file=self._log)
        self._log.flush()
        if self.verbose:
            traceback.print_exc(file=sys.__stderr__)

    def run_subprocess(self, cmd: Sequence[str], *, cwd: Path) -> int:
        self.log("$ " + " ".join(str(x) for x in cmd))
        proc = subprocess.Popen(
            [str(x) for x in cmd],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            self._detail.write(line)
        return proc.wait()


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _is_temporary_test_environment() -> bool:
    forced = os.environ.get("TSUNAGU_NORMALIZE_TEST", "").strip().lower()
    if forced in {"1", "true", "yes", "on"}:
        return True
    return REPO_ROOT.name.startswith("open-infra-normalize-test")


def _run_isolated_test(scope_slug: str) -> int:
    """Re-run the current CLI entry point in a clean temporary repository."""
    entry = Path(sys.argv[0]).resolve()
    try:
        entry_rel = entry.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise RuntimeError(
            f"実行ファイルがレポジトリ配下ではありません: {entry}"
        ) from exc

    test_root = Path(tempfile.gettempdir()) / f"open-infra-normalize-test-{scope_slug}"

    if test_root.exists():
        shutil.rmtree(test_root)

    (test_root / "data").mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO_ROOT / "tools", test_root / "tools")

    # Read-only source/reference trees are linked to the real repository.
    # The normalized output tree is always new and empty.
    for rel in (
        Path("data/raw"),
        Path("data/reference"),
        Path("schema"),
        Path("patches"),
        Path("catalog"),
        Path("sources"),
    ):
        source = REPO_ROOT / rel
        if not source.exists():
            continue
        dest = test_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(source, target_is_directory=True)

    (test_root / "data/normalized").mkdir(parents=True, exist_ok=True)

    child_entry = test_root / entry_rel
    child_args = [arg for arg in sys.argv[1:] if arg != "--test"]

    env = os.environ.copy()
    env["TSUNAGU_NORMALIZE_TEST"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    return subprocess.run(
        [sys.executable, str(child_entry), *child_args],
        cwd=test_root,
        env=env,
    ).returncode


def _strip_cli_option_with_value(args: Sequence[str], option: str) -> list[str]:
    result: list[str] = []
    i = 0
    prefix = option + "="
    while i < len(args):
        arg = args[i]
        if arg == option:
            if i + 1 >= len(args):
                raise RuntimeError(f"{option} に保存先が指定されていません")
            i += 2
            continue
        if arg.startswith(prefix):
            i += 1
            continue
        result.append(arg)
        i += 1
    return result


def _run_with_output_root(scope_slug: str, output_root_arg: str) -> int:
    """Run the current CLI with normalized output redirected safely."""
    entry = Path(sys.argv[0]).resolve()
    try:
        entry_rel = entry.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise RuntimeError(
            f"実行ファイルがレポジトリ配下ではありません: {entry}"
        ) from exc

    output_root = Path(output_root_arg).expanduser()
    if not output_root.is_absolute():
        output_root = (Path.cwd() / output_root).resolve()
    else:
        output_root = output_root.resolve()
    normal_root = (REPO_ROOT / "data" / "normalized").resolve()
    try:
        output_root.relative_to(normal_root)
    except ValueError:
        pass
    else:
        raise RuntimeError(
            "--output-root には通常の data/normalized/ 配下を指定できません"
        )

    output_root.mkdir(parents=True, exist_ok=True)

    isolated_root = (
        Path(tempfile.gettempdir())
        / f"open-infra-normalize-output-{scope_slug}"
    )
    if isolated_root.exists():
        shutil.rmtree(isolated_root)

    (isolated_root / "data").mkdir(parents=True, exist_ok=True)
    shutil.copytree(REPO_ROOT / "tools", isolated_root / "tools")

    for rel in (
        Path("data/raw"),
        Path("data/reference"),
        Path("schema"),
        Path("patches"),
        Path("catalog"),
        Path("sources"),
    ):
        source = REPO_ROOT / rel
        if not source.exists():
            continue
        dest = isolated_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.symlink_to(source, target_is_directory=True)

    # Existing normalizers can keep writing to <repo>/data/normalized.
    # In this isolated repo that path points to the requested destination.
    normalized_link = isolated_root / "data" / "normalized"
    normalized_link.symlink_to(output_root, target_is_directory=True)

    child_entry = isolated_root / entry_rel
    child_args = _strip_cli_option_with_value(sys.argv[1:], "--output-root")

    env = os.environ.copy()
    env["TSUNAGU_NORMALIZE_OUTPUT_ROOT"] = str(output_root)
    env["TSUNAGU_NORMALIZE_LOG_ROOT"] = str(
        REPO_ROOT / "logs" / "normalize" / "public-toilet"
    )
    env["PYTHONDONTWRITEBYTECODE"] = "1"

    return subprocess.run(
        [sys.executable, str(child_entry), *child_args],
        cwd=isolated_root,
        env=env,
    ).returncode


def _display_log_path(path: Path) -> str:
    if _is_temporary_test_environment():
        return str(path)
    return _relative(path)


def _print_environment_intro(*, overwrite: bool = False) -> None:
    custom_output = os.environ.get("TSUNAGU_NORMALIZE_OUTPUT_ROOT", "").strip()
    if custom_output:
        print("実行環境: 出力先指定")
        if overwrite:
            print("実行モード: 上書き再生成")
        else:
            print("実行モード: 通常")
        print(f"正規化CSVは、指定した保存先に保存します: {custom_output}")
        print("通常の data/normalized/ は変更しません。")
        return

    if _is_temporary_test_environment():
        print("実行環境: 一時テスト環境")
        print("この実行では、取得済みの元データから正規化CSVを再生成できるか確認します。")
        print("生成した正規化CSVと詳細ログは、一時テスト用フォルダに保存します。")
        print("普段使うレポジトリ内の data/normalized/ は、このテストでは変更しません。")
    else:
        print("実行環境: 通常環境")
        if overwrite:
            print("実行モード: 上書き再生成")
            print("既存の正規化CSVも、取得済みの元データから再作成します。")
        else:
            print("実行モード: 通常")
            print("既存の正規化CSVは変更せず、未生成の自治体だけを追加します。")
        print("正規化CSVは、このレポジトリの data/normalized/ に保存します。")


def _print_log_location(reporter: "Reporter") -> None:
    print("詳細ログの保存先:")
    print(f"  {_display_log_path(reporter.path)}")


def _print_output_location(path: Path, *, label: str = "正規化CSVの保存先") -> None:
    if _is_temporary_test_environment():
        print(f"{label}（一時テスト用）:")
        print(f"  {path}")
    else:
        print(f"{label}:")
        print(f"  {_relative(path)}/")


def _print_postrun_progress_summary(prefecture_codes: set[str]) -> None:
    """Print repository status normally, reproduction wording in temp tests."""
    if not _is_temporary_test_environment():
        print_progress_summary(prefecture_codes)
        return

    # progress.py remains the source of truth for counts and classification.
    # Only user-facing wording changes in the isolated reproduction environment.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        print_progress_summary(prefecture_codes)

    rendered = buf.getvalue()
    replacements = (
        ("公衆トイレデータの整備状況:", "再生成テスト結果:"),
        ("  正規化済み:", "  今回再生成できた:"),
        ("  残件:", "  今回再生成できなかった:"),
        ("  残件内訳:", "  再生成できなかった内訳:"),
        ("    元データあり・未正規化:", "    元データあり・今回再生成できず:"),
        ("残件一覧:", "今回再生成できなかった自治体:"),
        ("  元データあり・未正規化:", "  元データあり・今回再生成できず:"),
    )
    for old, new in replacements:
        rendered = rendered.replace(old, new)

    print(rendered, end="")


def _output_dir(prefecture_code: str, prefecture_name: str) -> Path:
    return NORMALIZED_ROOT / f"{prefecture_code}-{prefecture_name}"


@dataclass
class _OutputBackup:
    data: bytes
    atime_ns: int
    mtime_ns: int
    mode: int


def _output_files(output_dir: Path) -> list[Path]:
    if not output_dir.exists():
        return []
    return sorted(output_dir.rglob("public-toilet.csv"))


def _code_from_output_path(path: Path, output_dir: Path) -> str | None:
    try:
        first = path.relative_to(output_dir).parts[0]
    except (ValueError, IndexError):
        return None
    code = first[:5]
    return code if len(code) == 5 and code.isdigit() else None


def _existing_codes(output_dir: Path) -> set[str]:
    result: set[str] = set()
    for path in _output_files(output_dir):
        code = _code_from_output_path(path, output_dir)
        if code:
            result.add(code)
    return result


def _backup_outputs(output_dir: Path) -> dict[Path, _OutputBackup]:
    backup: dict[Path, _OutputBackup] = {}
    for path in _output_files(output_dir):
        stat = path.stat()
        backup[path] = _OutputBackup(
            data=path.read_bytes(),
            atime_ns=stat.st_atime_ns,
            mtime_ns=stat.st_mtime_ns,
            mode=stat.st_mode,
        )
    return backup


def _restore_one(path: Path, item: _OutputBackup) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".restore-tmp")
    tmp.write_bytes(item.data)
    os.chmod(tmp, item.mode)
    os.utime(tmp, ns=(item.atime_ns, item.mtime_ns))
    tmp.replace(path)


def _rollback_outputs(output_dir: Path, backup: dict[Path, _OutputBackup]) -> None:
    for path in _output_files(output_dir):
        if path not in backup:
            path.unlink()
    for path, item in backup.items():
        _restore_one(path, item)


def _restore_existing_outputs(
    output_dir: Path,
    backup: dict[Path, _OutputBackup],
    *,
    keep_regenerated_codes: set[str] | None = None,
) -> None:
    keep_regenerated_codes = keep_regenerated_codes or set()
    for path, item in backup.items():
        code = _code_from_output_path(path, output_dir)
        if code in keep_regenerated_codes:
            continue
        _restore_one(path, item)


def _remove_all_outputs(output_dir: Path) -> None:
    for path in _output_files(output_dir):
        path.unlink()


def _remove_unintended_new_outputs(
    output_dir: Path,
    backup: dict[Path, _OutputBackup],
    allowed_codes: set[str] | None,
) -> None:
    if allowed_codes is None:
        return
    before = set(backup)
    for path in _output_files(output_dir):
        if path in before:
            continue
        code = _code_from_output_path(path, output_dir)
        if code not in allowed_codes:
            path.unlink()


def _ensure_codes_exist(output_dir: Path, codes: set[str]) -> None:
    existing = _existing_codes(output_dir)
    missing = sorted(codes - existing)
    if missing:
        raise RuntimeError(
            "正規化CSVが生成されませんでした: " + ", ".join(missing)
        )


def _snapshot(output_dir: Path) -> dict[Path, tuple[int, int]]:
    if not output_dir.exists():
        return {}
    result: dict[Path, tuple[int, int]] = {}
    for path in output_dir.rglob("public-toilet.csv"):
        try:
            stat = path.stat()
        except FileNotFoundError:
            continue
        result[path] = (stat.st_mtime_ns, stat.st_size)
    return result


def _changed_files(before: dict[Path, tuple[int, int]], output_dir: Path) -> list[Path]:
    after = _snapshot(output_dir)
    changed = [path for path, meta in after.items() if before.get(path) != meta]
    return sorted(changed)


def _municipality_name(code: str) -> str:
    raw_root = REPO_ROOT / "data" / "raw"
    if raw_root.exists():
        matches = sorted(raw_root.glob(f"*/{code}-*"))
        if matches:
            name = matches[0].name
            if "-" in name:
                return name.split("-", 1)[1]
    return code


def _codes_label(codes: Sequence[str]) -> str:
    if not codes:
        return "専用正規化"
    names = [_municipality_name(code) for code in codes]
    if len(names) <= 3:
        return "・".join(names)
    return f"{'・'.join(names[:2])}ほか{len(names) - 2}自治体"




_HANDLER_DISPLAY_NAMES = {
    "legacy32_standard": "旧32列形式",
    "legacy32_reviewed": "旧32列形式（確認済み）",
    "standard_superset": "標準39列拡張形式",
    "nearstandard": "準標準形式",
    "alias_variants": "列名差異形式",
    "fukui_english39_standard": "福井県英語列形式",
    "fukui_english39_special": "福井県英語列形式（個別変換）",
}



def _handler_display_name(module: str) -> str:
    return _HANDLER_DISPLAY_NAMES.get(module, "自治体別形式")



def _plan_targets(codes: Sequence[str]) -> list[str]:
    if not codes:
        return ["県内一括"]
    return [f"{_municipality_name(code)} ({code})" for code in codes]


def _scope_slug(prefix: str, value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    cleaned = "-".join(part for part in cleaned.split("-") if part)
    return f"{prefix}-{cleaned}" if cleaned else prefix


def _code_from_target_item(item) -> str | None:
    if isinstance(item, str):
        m = item[:5]
        return m if len(m) == 5 and m.isdigit() else None
    if isinstance(item, tuple) and item:
        s = str(item[0])
        return s if len(s) == 5 and s.isdigit() else None
    return None


def _filter_targets(targets, codes: set[str]):
    if isinstance(targets, dict):
        return {k: v for k, v in targets.items() if str(k) in codes}
    if isinstance(targets, set):
        return {x for x in targets if _code_from_target_item(x) in codes}
    if isinstance(targets, list):
        return [x for x in targets if _code_from_target_item(x) in codes]
    if isinstance(targets, tuple):
        return tuple(x for x in targets if _code_from_target_item(x) in codes)
    raise TypeError(f"unsupported TARGETS type: {type(targets).__name__}")


def run_handler(handler: Handler, *, codes_override: Sequence[str] | None = None) -> None:
    old_argv = sys.argv[:]
    old_cwd = Path.cwd()
    codes = tuple(codes_override) if codes_override is not None else tuple(handler.codes)
    try:
        os.chdir(REPO_ROOT)
        # Some historical implementations inspect cwd/sys.argv at import time.
        # Sanitize both before importing them.
        sys.argv = [handler.module]
        module = importlib.import_module(f"tools.normalize.implementations.{handler.module}")
        sys.argv = [getattr(module, "__file__", handler.module)]
        if codes and hasattr(module, "TARGETS"):
            original = module.TARGETS
            module.TARGETS = _filter_targets(original, set(codes))
            try:
                module.main()
            finally:
                module.TARGETS = original
        else:
            module.main()
    finally:
        sys.argv = old_argv
        os.chdir(old_cwd)




def run_exact_standard(
    prefecture_code: str,
    reporter: Reporter | None = None,
    *,
    overwrite: bool = False,
    exclude_codes: Sequence[str] = (),
) -> int:
    """Normalize exact official-39 sources not managed by specialized handlers."""
    cmd = [
        sys.executable, str(REPO_ROOT / "tools/normalize_public_toilet.py"),
        "--prefecture", prefecture_code, "--only-standard",
    ]
    for code in sorted(set(exclude_codes)):
        cmd.extend(["--exclude-code", code])
    if overwrite:
        cmd.append("--overwrite")
    if reporter is not None:
        return reporter.run_subprocess(cmd, cwd=REPO_ROOT)
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def validate_prefecture(prefecture_code: str, reporter: Reporter | None = None) -> int:
    cmd = [
        sys.executable,
        str(REPO_ROOT / "tools/validate_public_toilet.py"),
        "--prefecture", prefecture_code,
        "--input", "normalized",
    ]
    if reporter is not None:
        return reporter.run_subprocess(cmd, cwd=REPO_ROOT)
    return subprocess.run(cmd, cwd=REPO_ROOT).returncode


def print_prefecture_plan(
    prefecture_code: str,
    prefecture_name: str,
    handlers: Iterable[Handler],
    *,
    verbose: bool = False,
) -> None:
    handlers = list(handlers)
    print(f"=== {prefecture_code} {prefecture_name} ===")

    if handlers:
        print("正規化:")
        for h in handlers:
            display_name = _handler_display_name(h.module)
            targets = _plan_targets(h.codes)
            for target in targets:
                print(f"  - {target} — {display_name}")
            if verbose:
                print(f"      実装: {h.module}")
    else:
        print("正規化:")
        print("  - 専用変換なし")

    print("共通処理:")
    print("  - 標準39列形式を自動検出")
    if verbose:
        print("      実装: normalize_public_toilet.py --only-standard")


def _run_stage(
    reporter: Reporter,
    label: str,
    action,
    *,
    show_progress: bool,
    index: int,
    total: int,
) -> tuple[bool, str | None]:
    reporter.stage(label)
    if show_progress:
        print(f"[{index}/{total}] {label} ... ", end="", flush=True)
    try:
        with reporter.capture():
            result = action()
        if isinstance(result, int) and result != 0:
            if show_progress:
                print("NG")
            reporter.log(f"result: NG (exit={result})")
            return False, f"exit={result}"
    except Exception as exc:
        if show_progress:
            print("NG")
        reporter.log(f"result: NG ({type(exc).__name__}: {exc})")
        reporter.log_exception()
        return False, f"{type(exc).__name__}: {exc}"
    if show_progress:
        print("OK")
    reporter.log("result: OK")
    return True, None


def execute_prefecture(
    prefecture_code: str,
    prefecture_name: str,
    handlers: Iterable[Handler],
    *,
    validate: bool,
    overwrite: bool,
    continue_on_error: bool = False,
    reporter: Reporter,
    show_tasks: bool,
) -> RunResult:
    handlers = list(handlers)
    output_dir = _output_dir(prefecture_code, prefecture_name)
    before = _snapshot(output_dir)
    generated_codes: set[str] = set()
    # 通常モードでは実行開始時点で存在する正規化CSVはすべて保持される。
    # 専用handlerだけでなく、後段の標準39列共通処理が担当する自治体も
    # 「既存CSVのためスキップ」に含めるため、県内の既存出力を初期値にする。
    skipped_codes: set[str] = set() if overwrite else _existing_codes(output_dir)
    failures: list[tuple[str, str]] = []

    # --continue-on-error では、複数自治体を束ねた handler も
    # 1自治体ずつ実行する。1件の異常で同じ県の後続自治体が未確認に
    # ならないようにするため。
    handler_runs: list[tuple[Handler, tuple[str, ...]]] = []
    for h in handlers:
        if continue_on_error and h.codes:
            handler_runs.extend((h, (code,)) for code in h.codes)
        else:
            handler_runs.append((h, tuple(h.codes)))

    total = len(handler_runs) + 1 + (1 if validate else 0)
    index = 0

    reporter.stage(f"{prefecture_code} {prefecture_name}")
    reporter.log(f"output: {_relative(output_dir)}")
    reporter.log(f"overwrite: {overwrite}")
    reporter.log(f"continue_on_error: {continue_on_error}")

    def record_failure(label: str, error: str | None) -> RunResult | None:
        message = error or "unknown error"
        failures.append((label, message))
        reporter.log(f"continue after failure: {label}: {message}")
        if continue_on_error:
            return None
        return build_result()

    def build_result() -> RunResult:
        failed_stages = [label for label, _ in failures]
        errors = [message for _, message in failures]
        return RunResult(
            rc=1 if failures else 0,
            changed_files=_changed_files(before, output_dir),
            skipped_codes=sorted(skipped_codes),
            failed_stage=failed_stages[0] if failed_stages else None,
            error=errors[0] if errors else None,
            failed_stages=failed_stages,
            errors=errors,
        )

    for h, requested_codes in handler_runs:
        index += 1
        registered_codes = tuple(requested_codes)
        managed_codes = tuple(h.managed_codes)
        existing = _existing_codes(output_dir)

        if overwrite:
            active_codes = registered_codes
        elif registered_codes:
            active_codes = tuple(code for code in registered_codes if code not in existing)
            skipped_codes.update(code for code in registered_codes if code in existing)
        else:
            active_codes = registered_codes
            skipped_codes.update(code for code in managed_codes if code in existing)

        label_codes = active_codes if active_codes else registered_codes
        label = f"正規化: {_codes_label(label_codes)}"

        if registered_codes and not active_codes:
            reporter.stage(label)
            reporter.log("result: SKIP (all registered outputs already exist)")
            if show_tasks:
                print(f"[{index}/{total}] {label} ... SKIP（既存CSVあり）")
            continue

        if (
            not overwrite
            and not registered_codes
            and managed_codes
            and set(managed_codes) <= existing
        ):
            reporter.stage(label)
            reporter.log("result: SKIP (all managed outputs already exist)")
            if show_tasks:
                print(f"[{index}/{total}] {label} ... SKIP（既存CSVあり）")
            continue

        backup = _backup_outputs(output_dir)
        target_codes = set(active_codes) if active_codes else None

        def handler_action(
            h=h,
            active_codes=active_codes,
            target_codes=target_codes,
            backup=backup,
        ) -> None:
            _remove_all_outputs(output_dir)
            run_handler(
                h,
                codes_override=active_codes if active_codes else None,
            )

            if target_codes is not None:
                _remove_unintended_new_outputs(output_dir, backup, target_codes)
                _ensure_codes_exist(output_dir, target_codes)

            if overwrite:
                # wildcard handler は target_codes=None になる。
                # 全出力を削除して handler を実行しているため、この時点で
                # 存在するコードが今回 handler によって再生成されたコード。
                regenerated_codes = (
                    set(target_codes)
                    if target_codes is not None
                    else _existing_codes(output_dir)
                )

                _restore_existing_outputs(
                    output_dir,
                    backup,
                    keep_regenerated_codes=regenerated_codes,
                )
                new_codes = regenerated_codes
            else:
                new_codes = {
                    code
                    for path in _output_files(output_dir)
                    if path not in backup
                    for code in [_code_from_output_path(path, output_dir)]
                    if code
                }
                _restore_existing_outputs(output_dir, backup)

            generated_codes.update(new_codes)

        ok, error = _run_stage(
            reporter,
            label,
            handler_action,
            show_progress=show_tasks,
            index=index,
            total=total,
        )
        if not ok:
            _rollback_outputs(output_dir, backup)
            result = record_failure(label, error)
            if result is not None:
                return result
            continue

    index += 1
    label = "標準39列データ"
    exact_backup = _backup_outputs(output_dir)

    specialized_codes = {
        code
        for handler in handlers
        for code in (
            *handler.codes,
            *handler.managed_codes,
            *handler.exact39_exclude_codes,
        )
    }

    def exact_standard_action() -> int:
        rc = run_exact_standard(
            prefecture_code,
            reporter,
            overwrite=overwrite,
            exclude_codes=sorted(specialized_codes),
        )
        if rc != 0:
            return rc

        if overwrite and generated_codes:
            # Keep the outputs just regenerated by specialized handlers.
            # The common 39-column scan may also see their raw files, so restore the
            # specialized versions captured immediately before this stage.
            other_codes = _existing_codes(output_dir) - generated_codes
            _restore_existing_outputs(
                output_dir,
                exact_backup,
                keep_regenerated_codes=other_codes,
            )
        return 0

    ok, error = _run_stage(
        reporter,
        label,
        exact_standard_action,
        show_progress=show_tasks,
        index=index,
        total=total,
    )
    if not ok:
        _rollback_outputs(output_dir, exact_backup)
        result = record_failure(label, error)
        if result is not None:
            return result

    if validate:
        index += 1
        label = "検証"
        ok, error = _run_stage(
            reporter,
            label,
            lambda: validate_prefecture(prefecture_code, reporter),
            show_progress=show_tasks,
            index=index,
            total=total,
        )
        if not ok:
            result = record_failure(label, error)
            if result is not None:
                return result

    return build_result()


def run_prefecture(
    prefecture_code: str,
    prefecture_name: str,
    handlers: Iterable[Handler],
    *,
    validate: bool = False,
    list_only: bool = False,
    overwrite: bool = False,
    continue_on_error: bool = False,
) -> int:
    """Backward-compatible programmatic entry point."""
    if list_only:
        print_prefecture_plan(prefecture_code, prefecture_name, handlers)
        return 0

    reporter = Reporter(f"p{prefecture_code}")
    try:
        result = execute_prefecture(
            prefecture_code,
            prefecture_name,
            handlers,
            validate=validate,
            overwrite=overwrite,
            continue_on_error=continue_on_error,
            reporter=reporter,
            show_tasks=True,
        )
        return result.rc
    finally:
        reporter.close()


def _print_prefecture_summary(
    prefecture_code: str,
    prefecture_name: str,
    result: RunResult,
    reporter: Reporter,
) -> None:
    output_dir = _output_dir(prefecture_code, prefecture_name)
    print()
    print(f"結果: {'OK' if result.rc == 0 else 'NG'}")
    failed_stages = result.failed_stages or (
        [result.failed_stage] if result.failed_stage else []
    )
    if failed_stages:
        if len(failed_stages) == 1:
            print(f"失敗箇所: {failed_stages[0]}")
        else:
            print(f"失敗処理: {len(failed_stages)}件")
            for stage in failed_stages:
                print(f"  - {stage}")
    print(f"生成・更新ファイル: {len(result.changed_files)}")
    if result.skipped_codes:
        print(f"既存CSVのためスキップ: {len(set(result.skipped_codes))}自治体")
    _print_output_location(output_dir)
    if result.changed_files and len(result.changed_files) <= 20:
        print("出力ファイル:")
        for path in result.changed_files:
            print(f"  {path if _is_temporary_test_environment() else _relative(path)}")
    _print_postrun_progress_summary({prefecture_code})
    print()
    _print_log_location(reporter)


def prefecture_cli(
    prefecture_code: str,
    prefecture_name: str,
    handlers: Iterable[Handler],
) -> int:
    p = argparse.ArgumentParser(description=f"{prefecture_name}の公衆トイレ正規化")
    p.add_argument("--list", action="store_true", help="処理計画だけ表示")
    p.add_argument("--test", action="store_true", help="空の一時環境で元データから再生成テスト")
    p.add_argument(
        "--output-root",
        metavar="DIR",
        help="正規化CSVの保存先を data/normalized/ 以外に指定",
    )
    p.add_argument("--validate", action="store_true", help="正規化後に県単位validatorを実行")
    p.add_argument(
        "--continue-on-error",
        action="store_true",
        help="失敗した自治体・処理を記録し、県内の後続処理も続行",
    )
    p.add_argument("--verbose", action="store_true", help="詳細ログを画面にも表示")
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="既存の正規化CSVも元データから再作成",
    )
    a = p.parse_args()

    if a.test and a.output_root:
        p.error("--test と --output-root は同時に指定できません")
    if a.list and a.output_root:
        p.error("--list と --output-root は同時に指定できません")
    if a.test and not a.list:
        return _run_isolated_test(f"p{prefecture_code}")
    if a.output_root:
        return _run_with_output_root(f"p{prefecture_code}", a.output_root)

    if a.list:
        print_prefecture_plan(
            prefecture_code, prefecture_name, handlers, verbose=a.verbose
        )
        print_progress_summary({prefecture_code})
        return 0

    reporter = Reporter(f"p{prefecture_code}", verbose=a.verbose)
    try:
        print(f"公衆トイレ正規化: {prefecture_name}")
        _print_environment_intro(overwrite=a.overwrite)
        print()
        _print_log_location(reporter)
        print()
        result = execute_prefecture(
            prefecture_code,
            prefecture_name,
            handlers,
            validate=a.validate,
            overwrite=a.overwrite,
            continue_on_error=a.continue_on_error,
            reporter=reporter,
            show_tasks=True,
        )
        _print_prefecture_summary(prefecture_code, prefecture_name, result, reporter)
        return result.rc
    finally:
        reporter.close()


def region_cli(region_name: str, prefecture_modules: Sequence[str]) -> int:
    p = argparse.ArgumentParser(description=f"{region_name}の公衆トイレ正規化")
    p.add_argument("--list", action="store_true", help="処理計画だけ表示")
    p.add_argument("--test", action="store_true", help="空の一時環境で元データから再生成テスト")
    p.add_argument(
        "--output-root",
        metavar="DIR",
        help="正規化CSVの保存先を data/normalized/ 以外に指定",
    )
    p.add_argument("--validate", action="store_true", help="各都道府県の正規化後にvalidatorを実行")
    p.add_argument("--continue-on-error", action="store_true", help="失敗後も県内の後続処理・次の都道府県を続行")
    p.add_argument("--verbose", action="store_true", help="詳細ログを画面にも表示")
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="既存の正規化CSVも元データから再作成",
    )
    a = p.parse_args()

    if a.test and a.output_root:
        p.error("--test と --output-root は同時に指定できません")
    if a.list and a.output_root:
        p.error("--list と --output-root は同時に指定できません")
    if a.test and not a.list:
        return _run_isolated_test(_scope_slug("region", region_name))
    if a.output_root:
        return _run_with_output_root(
            _scope_slug("region", region_name),
            a.output_root,
        )

    modules = [importlib.import_module(name) for name in prefecture_modules]
    if a.list:
        for m in modules:
            print_prefecture_plan(
                m.PREFECTURE_CODE, m.PREFECTURE_NAME, m.HANDLERS,
                verbose=a.verbose,
            )
        print_progress_summary({m.PREFECTURE_CODE for m in modules})
        return 0

    reporter = Reporter(_scope_slug("region", region_name), verbose=a.verbose)
    failures: list[str] = []
    changed_files: list[Path] = []
    skipped_codes: set[str] = set()
    failed_stage_count = 0
    try:
        print(f"公衆トイレ正規化: {region_name}")
        _print_environment_intro(overwrite=a.overwrite)
        print()
        _print_log_location(reporter)
        print()

        for index, m in enumerate(modules, 1):
            print(f"[{index}/{len(modules)}] {m.PREFECTURE_NAME} ... ", end="", flush=True)
            try:
                result = execute_prefecture(
                    m.PREFECTURE_CODE,
                    m.PREFECTURE_NAME,
                    m.HANDLERS,
                    validate=a.validate,
                    overwrite=a.overwrite,
                    continue_on_error=a.continue_on_error,
                    reporter=reporter,
                    show_tasks=False,
                )
            except Exception as exc:
                reporter.log(f"unexpected region-level error: {type(exc).__name__}: {exc}")
                reporter.log_exception()
                result = RunResult(1, failed_stage="県処理", error=str(exc))

            changed_files.extend(result.changed_files)
            skipped_codes.update(result.skipped_codes)
            failed_stage_count += len(result.failed_stages) or (1 if result.failed_stage else 0)
            if result.rc == 0:
                print("OK")
            else:
                print("NG")
                failures.append(m.PREFECTURE_NAME)
                if not a.continue_on_error:
                    break

        print()
        print(f"結果: {'OK' if not failures else 'NG'}")
        print(f"成功: {len(modules) - len(failures) if not failures else max(0, index - len(failures))} / {len(modules)}")
        if failures:
            print(f"失敗: {'、'.join(failures)}")
            if failed_stage_count:
                print(f"失敗処理: {failed_stage_count}件（詳細はログ参照）")
        print(f"生成・更新ファイル: {len(changed_files)}")
        if skipped_codes:
            print(f"既存CSVのためスキップ: {len(skipped_codes)}自治体")
        if _is_temporary_test_environment():
            _print_output_location(NORMALIZED_ROOT, label="テスト用の正規化CSV保存先")
        else:
            print("正規化CSVの保存先:")
            for m in modules:
                print(f"  {_relative(_output_dir(m.PREFECTURE_CODE, m.PREFECTURE_NAME))}/")
        _print_postrun_progress_summary({m.PREFECTURE_CODE for m in modules})
        print()
        _print_log_location(reporter)
        return 1 if failures else 0
    finally:
        reporter.close()


def all_japan_cli(region_modules: Sequence[str]) -> int:
    p = argparse.ArgumentParser(description="全国47都道府県の公衆トイレ正規化")
    p.add_argument("--list", action="store_true", help="処理計画だけ表示")
    p.add_argument("--test", action="store_true", help="空の一時環境で元データから再生成テスト")
    p.add_argument(
        "--output-root",
        metavar="DIR",
        help="正規化CSVの保存先を data/normalized/ 以外に指定",
    )
    p.add_argument("--validate", action="store_true", help="各都道府県の正規化後にvalidatorを実行")
    p.add_argument("--continue-on-error", action="store_true", help="失敗後も県内の後続処理・次の都道府県を続行")
    p.add_argument("--verbose", action="store_true", help="詳細ログを画面にも表示")
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="既存の正規化CSVも元データから再作成",
    )
    a = p.parse_args()

    if a.test and a.output_root:
        p.error("--test と --output-root は同時に指定できません")
    if a.list and a.output_root:
        p.error("--list と --output-root は同時に指定できません")
    if a.test and not a.list:
        return _run_isolated_test("all-japan")
    if a.output_root:
        return _run_with_output_root("all-japan", a.output_root)

    region_objects = [importlib.import_module(name) for name in region_modules]
    prefectures = []
    for region in region_objects:
        for pref_module in region.PREFECTURE_MODULES:
            prefectures.append((region.REGION_NAME, importlib.import_module(pref_module)))

    if a.list:
        for _, m in prefectures:
            print_prefecture_plan(
                m.PREFECTURE_CODE, m.PREFECTURE_NAME, m.HANDLERS,
                verbose=a.verbose,
            )
        print_progress_summary({m.PREFECTURE_CODE for _, m in prefectures})
        return 0

    reporter = Reporter("all-japan", verbose=a.verbose)
    failures: list[str] = []
    changed_files: list[Path] = []
    skipped_codes: set[str] = set()
    failed_stage_count = 0
    completed = 0
    current_region: str | None = None
    try:
        print("公衆トイレ正規化: 全国")
        _print_environment_intro(overwrite=a.overwrite)
        print()
        _print_log_location(reporter)
        print()

        for index, (region_name, m) in enumerate(prefectures, 1):
            if region_name != current_region:
                current_region = region_name
                print(f"-- {region_name} --")
            print(f"[{index:02d}/{len(prefectures)}] {m.PREFECTURE_NAME} ... ", end="", flush=True)
            result = execute_prefecture(
                m.PREFECTURE_CODE,
                m.PREFECTURE_NAME,
                m.HANDLERS,
                validate=a.validate,
                overwrite=a.overwrite,
                continue_on_error=a.continue_on_error,
                reporter=reporter,
                show_tasks=False,
            )
            changed_files.extend(result.changed_files)
            skipped_codes.update(result.skipped_codes)
            failed_stage_count += len(result.failed_stages) or (1 if result.failed_stage else 0)
            completed += 1
            if result.rc == 0:
                print("OK")
            else:
                print("NG")
                failures.append(m.PREFECTURE_NAME)
                if not a.continue_on_error:
                    break

        print()
        print(f"結果: {'OK' if not failures else 'NG'}")
        print(f"処理済み都道府県: {completed} / {len(prefectures)}")
        if failures:
            print(f"失敗: {'、'.join(failures)}")
            if failed_stage_count:
                print(f"失敗処理: {failed_stage_count}件（詳細はログ参照）")
        print(f"生成・更新ファイル: {len(changed_files)}")
        if skipped_codes:
            print(f"既存CSVのためスキップ: {len(skipped_codes)}自治体")
        _print_output_location(NORMALIZED_ROOT)
        _print_postrun_progress_summary({m.PREFECTURE_CODE for _, m in prefectures})
        print()
        _print_log_location(reporter)
        return 1 if failures else 0
    finally:
        reporter.close()
