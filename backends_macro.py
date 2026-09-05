"""Self-expanding registry — macro operators condensed from evolved champions.

This is the closed loop of the evolutionary core: a champion pipeline discovered
by ``evolve.py`` / ``robust.py`` is *frozen into a single reusable operator* — a
"DNA op" unique to this system — and registered like any other op. Once present it
becomes a candidate the NEXT evolution can select in one slot, so the search can
build on its own discoveries. That is the "self-expanding registry": op count
grows not only by wrapping libraries but by condensing what the search itself
found.

Data, not code: every macro op lives as one entry in ``data/macro_champions.json``
(written by ``champion_to_macro.py`` from a ``champion_<problem>.json``), so adding
a DNA op is a data edit + a recapture, never a hand-written pipeline. Each entry
carries the champion's name-pinned stages plus honest provenance (which splits it
was measured on, its holdout/locked score, and the hand baselines it is compared
against — including where it does NOT win).

Faithfulness contract (proven in ``tests/test_macro_ops.py``): a macro op runs the
champion's exact name-pinned stages via ``ops.decode_by_names`` + ``ops.run_stages``
— the same code path evolution scored — so its output is BIT-IDENTICAL to running
that pipeline stage-by-stage on the evaluation images. The op's own ``a,b`` knobs
are FROZEN (unused): a macro op is a fixed pipeline with its evolved knobs baked in,
not a re-parameterization. Fail-soft: if a DNA op is absent in this install the
composite degrades to a sort-valid value of the input (same contract every backend
honours).

``halcon = ""`` for every macro op: a champion pipeline is a novel composite an
evolutionary search discovered — no single HALCON operator is its equivalent — so
it makes NO coverage claim. It is a brand-new, system-unique capability.
"""
from __future__ import annotations

import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_DNA_PATH = os.path.join(_HERE, "data", "macro_champions.json")


def _load_entries() -> list:
    """The macro-champion DNA entries (``[]`` if none).

    Prefers the generated py-module ``macro_champions_data.MACROS``: a flat-layout
    ``.py`` always ships in the wheel, whereas ``data/`` files do NOT — so this is
    what lets macro ops register on a ``pip``-installed package, not only in the
    editable source tree. Falls back to the human-readable
    ``data/macro_champions.json`` when the module is absent (e.g. a partial
    checkout). Both are written together by ``champion_to_macro.py``.
    """
    try:
        from macro_champions_data import MACROS
        if isinstance(MACROS, list) and MACROS:
            return MACROS
    except Exception:  # noqa: BLE001 - module optional; fall back to the JSON
        pass
    if os.path.exists(_DNA_PATH):
        try:
            with open(_DNA_PATH, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                data = data.get("macros", [])
            if isinstance(data, list):
                return data
        except (OSError, ValueError):
            pass
    return []


def _make_runner(stages_spec, out_sort):
    """Return ``fn(v, a, b)`` that runs the FROZEN champion pipeline.

    ``a, b`` are unused: a macro op IS its discovered pipeline (evolved knobs baked
    into ``stages_spec``), so the output is bit-identical to running that pipeline
    stage-by-stage. Fail-soft per the op contract: any failure (e.g. a DNA op is
    absent in this install, so ``decode_by_names`` fail-closes with ``KeyError``)
    degrades to a sort-valid value derived from the input.
    """
    def body(v, a, b):
        import ops  # fully initialised by call time (build() runs mid-import)
        return ops.run_stages(ops.decode_by_names(stages_spec), v)

    from backend_safe import guard
    # fail-soft per op contract, but RECORDED (ledger) and strict-aware — a macro whose
    # DNA op is absent in this install used to look like a working identity.
    return guard(body, out_sort)


#: lambda で定義された op の説明ではなく、``_make_runner`` が返す汎用クロージャ
#: ``body`` に docstring を書いても全マクロ op で同じ文字列になってしまう(``a,b`` と
#: 違い、繋いだ op の並びは名前ごとに異なる)ため、ここで名前ごとに書く。
#: ops.py の登録ループが Op.doc に積む。キーは op 名。内容は
#: ``data/macro_champions.json`` / ``macro_champions_data.py`` の ``pipeline`` /
#: ``provenance`` をそのまま反映しており、op の並びを変えたら追記が必要。
DOCS = {
    "macro_denoise": (
        "進化探索（``evolve.py`` / ``robust.py``）が発見した固定パイプライン: "
        "``bilateral(a=0.10,b=0.76)`` → ``bilateral(a=0.12,b=0.27)`` → "
        "``bilateral(a=0.73,b=0.11)``（既存 op のバイラテラルフィルタを、強さの違う"
        "パラメータで 3 段連ねたもの）。\n\n"
        "``a``, ``b`` は凍結済みで未使用 —— このパイプライン自体が進化で選ばれた"
        "1 つの固定構成である。denoise 課題（PSNR）でロック済みホールドアウト"
        "26.28dB、手作りベースライン 22.83dB を上回る（train/holdout/locked_holdout"
        "のどれで測っても手作りベースラインに勝っている）。HALCON に対応する単一"
        "オペレータは無い（``halcon=\"\"``）。"
    ),
    "macro_edge": (
        "進化探索が発見した固定パイプライン: ``gamma(a=0.39,b=0.94)`` → "
        "``bilateral(a=0.22,b=0.08)`` → ``sobel_mag(a=0.81,b=0.80)`` → "
        "``scale_clip(a=1.00,b=0.90)`` → ``otsu(a=0.78,b=0.93)``（ガンマ補正 → "
        "平滑化 → 勾配強度 → スケーリング → 大津の判別分析法（Otsu's method）による"
        "二値化、の 5 段）。\n\n"
        "``a``, ``b`` は凍結済みで未使用。edge 課題（F1）でロック済みホールドアウト"
        "0.91、手作りベースライン 0.77 を上回る。出力は image ではなく region（二値"
        "マスク）。HALCON に対応する単一オペレータは無い。"
    ),
    "macro_binarize": (
        "進化探索が発見した固定パイプライン: ``bilateral(a=0.06,b=0.89)`` → "
        "``unsharp(a=0.51,b=0.34)`` → ``bilateral(a=0.04,b=0.24)`` → "
        "``lowpass(a=0.75,b=0.59)`` → ``gopen(a=0.38,b=1.00)`` → "
        "``unsharp(a=0.78,b=0.68)``（平滑化とアンシャープマスクを交互に重ね、"
        "ローパスとグレースケールオープニングで整えてから再度シャープ化する 6 段）。"
        "\n\n"
        "``a``, ``b`` は凍結済みで未使用。binarize 課題（IoU）でロック済みホール"
        "ドアウト 0.75、手作りベースライン 0.62 を上回るが、train 0.91 / holdout"
        "0.95 に対し locked_holdout は 0.75 まで落ちる —— 分割ごとの差を隠さず"
        "書く（feedback_benchmark_honest_disclosure）。HALCON に対応する単一"
        "オペレータは無い。"
    ),
    "macro_vol_denoise": (
        "進化探索が発見した固定パイプライン（3-D ボリューム版）: "
        "``vol_threshold(a=0.52,b=0.76)`` → ``vol_gaussian(a=0.08,b=0.89)``（3-D "
        "しきい値処理をかけてからガウシアン平滑化する 2 段）。\n\n"
        "``a``, ``b`` は凍結済みで未使用。in_sort/out_sort は volume。volume の "
        "denoise 課題（PSNR）でロック済みホールドアウト 25.74dB、手作りベースライン"
        "20.94dB を上回る。HALCON に対応する単一オペレータは無い。"
    ),
}


def build(Op, IMAGE, REGION, FEATURE, CONTOUR, norm, binm):
    """Construct one ``Op`` per DNA entry. Malformed entries are skipped
    individually (a single bad row never suppresses the rest). Sorts are plain
    strings (``"image"``/``"region"``/...), so entry values are used directly."""
    out = []
    for e in _load_entries():
        try:
            name = e["name"]
            in_sort = e.get("in_sort", IMAGE)
            out_sort = e.get("out_sort", IMAGE)
            stages_spec = [(s["op"], float(s["a"]), float(s["b"])) for s in e["stages"]]
            if not name or not stages_spec:
                continue
            out.append(Op(name, e.get("category", "macro"), "", in_sort, out_sort,
                          _make_runner(stages_spec, out_sort)))
        except (KeyError, TypeError, ValueError):
            continue
    return out
