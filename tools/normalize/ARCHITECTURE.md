# Public-toilet normalizer architecture

## Goal

Municipality-specific implementations should describe data differences, not reimplement infrastructure.

## Core responsibilities

`tools.normalize.core.normalization` owns reusable normalization infrastructure:

- `SourceReader` strategy interface
- `CsvDictSourceReader` / `XlsxSourceReader` adapters
- `RowSupport` for text cleaning, blank-row detection, and note appending
- `StableIdStrategy` / `Sha256StableIdStrategy`
- `StandardCsvWriter`

Implementation modules should own only:

- source-specific column mappings
- municipality-specific validation rules
- municipality-specific semantic corrections

## Rules for new implementations

Do not add local versions of these helpers unless the implementation has genuinely different semantics:

- `clean`
- `append_note`
- `stable_id`
- `write_atomic`
- generic CSV/XLSX source readers

Do not hard-code the number of ordinary data rows. Blank rows must be filtered by the source reader. A normal dataset is valid when at least one active data row remains and structural validation passes.

Count assertions are allowed only for semantic transformations where the count is part of the validation rule, for example verifying that a known exceptional value was corrected exactly once. Such checks should be narrowly named and documented.

## Patterns

- Strategy: source readers and stable-ID generation
- Adapter: CSV/XLSX readers normalize different physical formats into `SourceTable`
- Service object: `RowSupport`
- Repository/output boundary: `StandardCsvWriter`

The prefecture runner remains the orchestration layer. Implementation modules should not duplicate orchestration concerns.

## Migration

The first migration covers the generic handlers most frequently extended:

- `simple_location.py`
- `nearstandard.py`
- `alias_variants.py`
- `legacy32_standard.py`
- `hayama.py`

The second migration removes repeated infrastructure and ordinary row-count hard-coding from:

- `atsugi.py`
- `hirakata.py`
- `ikoma.py`
- `kawachinagano.py`
- `kitakyushu.py`
- `legacy26_standard.py`
- `minato.py`
- `osaka_city.py`

Legacy municipality-specific handlers can be migrated incrementally. New code should use the core API immediately so duplication does not grow while migration is in progress.

The third migration removes repeated helpers and ordinary row-count assertions from:

- `bunkyo.py`
- `gifu_remaining.py`
- `kobe.py`
- `okayama_city.py`
- `sasebo.py`
- `suzuka.py`
- `tokushima_prefecture.py`

For multi-source handlers, fixed snapshot counts are not structural validation. Preserve relationship checks instead, such as requiring paired CSV and GeoJSON sources to contain the same number of active records.

The fourth migration moves common helpers out of:

- `kumagaya.py`
- `kamakura.py`
- `kyoto.py`
- `nagakute.py`
- `saitama_remaining.py`
- `takarazuka.py`

Spreadsheet layout checks may retain fixed physical row positions when those positions are part of the parser contract (for example, fixed header/footer locations). Snapshot counts of ordinary active data rows must not be used as validity checks.

The fifth migration moves additional repeated helpers and snapshot row counts out of:

- `aichi_custom.py`
- `fukui_ikeda.py`
- `ishikawa_variants.py`
- `nagano_custom.py`
- `tottori.py`
- `yamanashi_remaining.py`

`ValueCleaner` is the shared Strategy for source-specific placeholder values such as `-`, `ー`, `－`, `無し`, and `なし`. Use `preserve_placeholder=True` only when the original literal is semantically meaningful and must be retained.

Classification or relationship checks remain local when they express source semantics. For example, a multi-source reconciliation may require exactly one unmatched source record, while an ordinary dataset must not require a fixed total row count.


The sixth migration removes repeated helpers and snapshot row-count assertions from:

- `nagoya.py`
- `gifu_custom.py`
- `yamanashi_custom.py`
- `chiba_standard_variants.py`
- `kibichuo.py`
- `hirakawa_namerikawa.py`

Known exceptional corrections may still assert a narrow semantic count (for example, one known municipality-code correction). Distribution counts such as the current number of rows using a particular valid time pattern are not parser contracts and must not be fixed in code. Stable-ID strategies must preserve the historical hash material exactly; use `include_code_in_material=False` when migrating a legacy ID whose digest did not include the municipality code.

The seventh migration removes repeated note/writer helpers and snapshot distribution counts from:

- `aizu_machida.py`
- `chippubetsu_fussa_matsuyama.py`
- `hitachi_shibuya_nakano_sabae.py`
- `karuizawa_uda_kainan_hiroshima.py`
- `manazuru_nagano_yokkaichi.py`
- `noshiro_namegata_meguro.py`
- `tama_shinshiro_kumano_kurume_taku.py`

Dynamic validation should reject malformed values and structural drift without pinning the current source distribution. The architecture test also rejects bare calls to migrated local helpers, so deleting a helper definition cannot leave an unresolved legacy call behind.

The eighth migration removes the remaining duplicated CSV writers from:

- `fukui_english39_special.py`
- `fukui_english39_standard.py`
- `furano_oga_sanjo_oyabe_sakai.py`
- `hakodate_aomori_daisen_akiruno.py`
- `kasama_gosen_miyoshi_tamba_otoyo_genkai_tamana_nagomi.py`
- `legacy32_reviewed.py`
- `sakado_otsu.py`

`RowSupport.append_text` is the shared primitive for idempotent slash-separated text appending to arbitrary standard fields; `append_note` delegates to it for `備考`. Distribution counts such as the current number of blank source rows, transformed time values, or boolean conversions are not parser contracts. Keep structural checks and narrowly scoped known-exception checks instead.


The tenth migration removes the final local note/clean helpers from:

- `gifu.py`
- `hiroshima.py`
- `kumamoto_takamori.py`
- `takamatsu.py`
- `uki_taketomi.py`

and removes snapshot row/correction counts from `standard_superset.py` and `archive_standard.py`.

`RowSupport.append_text` and `append_note` accept a configurable separator so source-specific output formatting can be preserved without reintroducing local append helpers. Correction logic must validate the values and structures it knows how to repair; it must not require the current number of affected records.

### Time normalization strategies

Time parsing is a source-variation boundary. Handlers should reuse a strategy from
`core/normalization.py` when their behavior is equivalent instead of defining another
local `normalize_time()` helper. Separate strategies intentionally preserve different
policies: strict rejection, invalid-value preservation for notes, `24:00` handling,
and lenient pass-through. Municipality-specific time semantics stay local when they
cannot be represented without hiding source-specific rules.

The remaining reusable policies also include strict `HH:MM`, lenient `24:00` preservation,
and `24:00 -> 23:59` with source-text preservation. `fukui_english39_standard.py`
intentionally keeps its local helper because municipality-specific prose extraction and
note-writing are part of that source adapter rather than generic time parsing.


### Allowed-value validation strategy

The fourteenth migration moves repeated scalar allowed-value validation from
`fukui_ikeda.py`, `gifu_custom.py`, `nagoya.py`, `yamanashi_custom.py`, and
`yamanashi_remaining.py` into `AllowedValueStrategy`. The strategy accepts a
source-appropriate cleaner, so CSV text cleaning and spreadsheet cell cleaning
remain explicit rather than being silently unified.

Do not mechanically merge note helpers merely because they share a name. Some
handlers append to row fields, others build temporary note lists, and some suppress
duplicate text. Those are distinct output semantics and may remain local until an
exact common abstraction exists.

## Final architecture decisions

The architecture audit is considered complete when repeated infrastructure has been moved to
the core without erasing source-specific semantics.

The remaining local `add_note` helpers are intentional. They do not represent one common
operation: some append to standard-row fields, some build temporary note collections, some
use different output separators or label formats, and some suppress duplicate text. They
should remain local unless an exact shared abstraction preserves those semantics explicitly.

`fukui_english39_standard.py` intentionally keeps its local `normalize_time()` helper.
That function is part of the source adapter: it handles municipality-specific prose,
embedded annotations, and note extraction in addition to time parsing. Moving it into a
generic time strategy would hide source-specific responsibilities rather than simplify them.

Do not split or merge implementation modules solely because of file length, function count,
or repeated generic function names such as `read_source`, `prepare_one`, or `read_rows`.
Refactor only when a real responsibility boundary exists and the resulting abstraction
reduces duplicated infrastructure without obscuring municipality-specific mappings,
validation rules, or semantic corrections.
