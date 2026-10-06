# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""opsresidue — fullseye residue / Chinese-remainder op registry.

Motivation (2026-10-06): a phase tells a quantity only modulo its period — a band's
local phase gives a displacement modulo its wavelength, an n-fold feature gives a
rotation modulo 360/n degrees. fullseye had phase measurement in several families
(motionmag, fringe, interferometry, rangedoppler) but every one of them stopped at
the single-period wrap limit. This registry is the shared pathway that combines
several periods by the Chinese remainder theorem (residue.py, 5 ops / 3 categories):
the theorem itself, a weighted robust real-valued version with redundant-band fault
localisation, and two image ops built on it.

Provenance is public literature only (docs/PROVENANCE.md naming rule): Garner 1959
(mixed-radix CRT) / Xia & Wang, robust CRT for reals (IEEE TSP 2007, ML version 2015)
/ Watson & Hastings 1966 (redundant residue number systems) / Fleet & Jepson 1990
(phase-based displacement) / Ozaki, Uchino & Imamura 2025, arXiv:2504.08009 (the same
residue arithmetic rebuilding FP64 products from INT8 ones).

Coexistence with existing assets (compose, do not re-implement):
  * ``motionmag.phase_displacement`` is the single-band method whose half-wavelength
    limit ``crt_displacement`` passes; it stays the right tool for small motions.
  * ``fringe.absolute_phase`` resolves one fringe order from one coarse estimate;
    ``residue_crt`` is the general form over any number of periods.
  * global translation is better served by ``filters_freq.phase_correlation_fft``.

Usage:
    import opsresidue
    opsresidue.list_ops("theorem")
    opsresidue.get("residue_crt")(residues, periods)
"""
import residue

_MOD = {"residue": residue}

# --------------------------------------------------------------------------
# Type vocabulary: no new word is coined (it all fits the existing pool).
# --------------------------------------------------------------------------
#   * signal  — integer residues / moduli, and real periods: 1-D sequences.
#   * matrix  — residues of many samples at once, band axis first, (N, M).
#   * image2d — the two images compared by the image ops.
#   * table   — every op returns a dict (value, margins, per-band residuals, the
#     faulty band): the existing table sort.
#
# カテゴリ → [(op 名, module, [入力種別], 出力種別)]
_CATALOG = {
    # 定理そのもの。任意精度の整数で丸めが 1 つも無い —— 残りの op の真値になる。
    "theorem": [
        ("residue_integer_crt", "residue", ["signal", "signal"], "table"),
    ],
    # 実数・重み付き・冗長な帯域で犯人探し。重み = その帯域の位相を出した振幅。
    "robust": [
        ("residue_crt", "residue", ["matrix", "signal"], "table"),
        ("residue_fault_locate", "residue", ["matrix", "signal"], "table"),
    ],
    # 画像。互いに素な波長の帯域の位相で局所変位、対称の回数が互いに素な輪で 360° の向き。
    "image": [
        ("crt_displacement", "residue", ["image2d", "image2d"], "table"),
        ("harmonic_rotation", "residue", ["image2d", "image2d"], "table"),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = ""
            if fn is not None and fn.__doc__:
                doc = fn.__doc__.strip().splitlines()[0]
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "func": fn, "doc": doc}
    return reg


OPSRESIDUE = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPSRESIDUE.items()
            if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


#: 宣言 out 型と素の返りの橋渡し。**空 — 意図的に**。5 op はすべて宣言型どおり
#: (dict = table)を素で返す。
RESULT_ADAPTERS = {}


def get(name):
    """op 名 → 実体(callable)。"""
    return OPSRESIDUE[name]["func"]


def call(name, *args, **kwargs):
    """op を実行し、台帳の宣言 out 型どおりの値を返す(adapter 適用)。"""
    result = OPSRESIDUE[name]["func"](*args, **kwargs)
    ad = RESULT_ADAPTERS.get(name)
    return result if ad is None else ad(result)


def info(name):
    """op のメタ情報。"""
    return OPSRESIDUE[name]


def missing():
    """台帳にあるのに実体の無い op(空であるべき)。"""
    return [n for n, m in OPSRESIDUE.items() if m["func"] is None]


if __name__ == "__main__":
    for c in categories():
        print(c, list_ops(c))
    print("missing:", missing())
