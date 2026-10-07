# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""CI では作り直せない生成物の**見出しの数字**を、コミット済みの入力から数え直す門(2026-10-07)。

``tools/regen_all.py`` の鎖に入れられない生成器が 2 本ある:

* ``honest_summary.py`` —— 入力の MVTec 表 ``data/halcon_operators.json`` が手元にしか無い
* ``lib_coverage.py``   —— 表の半分が「入れてある cv2 / skimage の版」で変わる

鎖に入らない生成物は**必ず古びる**(LIB_COVERAGE.md は 885 op のまま置き去りだった)。
だから出力を丸ごと作り直す代わりに、**数字だけ**を CI にある材料で数え直して照合する:

* HALCON の見出し ``N / 2313`` は、名前しか要らない —— 同梱の ``halcon_names_data``
  (表から機械生成した名前の写し)で ``honest_summary`` と同じ集合を作れる。
* ライブラリ別 op 数は registry の名前の接頭辞だけで決まる —— 同梱索引
  ``docs/OP_INDEX.json`` から数える(生きた registry は torch の無い CI で縮む)。
"""
from __future__ import annotations

import collections
import json
import re
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _halcon_counts():
    """``honest_summary.main`` と同じ集合を、同梱の名前表から作る。"""
    warnings.filterwarnings("ignore")
    import backends_auto as BA
    import halcon_coverage as HC
    import halcon_names_data as HN
    import imgops_nary as NA
    import ops as R
    import verify_auto as VA

    data = {"operators": [{"name": n, "chapters": []} for n in HN.HALCON_NAMES],
            "version": HN.HALCON_VERSION}
    a = HC.analyze(data, R.REGISTRY, None)
    reg_covered = set(a["covered"])
    auto_pass = set(VA.run(verbose_failures=False)["passing_ops"])
    auto_names = {s["halcon"] for s in BA.load_specs()}
    reg_counted = reg_covered - ((reg_covered & auto_names) - auto_pass)
    nary = set(NA.coverage()["halcon_names"])
    return len(reg_counted | nary), a["n_real"], len(reg_covered), a["n_registry"]


def test_halcon_parity_headline_matches_a_recount_from_the_shipped_names():
    total, n_real, reg_cov, n_registry = _halcon_counts()
    md = (ROOT / "docs" / "HALCON_PARITY.md").read_text(encoding="utf-8")
    m = re.search(r"\*\*(\d+)\s*/\s*(\d+) distinct real HALCON operators", md)
    assert m, "docs/HALCON_PARITY.md に見出し `**N / M distinct real HALCON operators` が無い"
    assert (int(m.group(1)), int(m.group(2))) == (total, n_real), (
        "HALCON_PARITY.md の見出しは %s / %s、同梱の名前表から数え直すと %d / %d —— "
        "手元(data/halcon_operators.json のある checkout)で `py -3.11 honest_summary.py` を回すこと"
        % (m.group(1), m.group(2), total, n_real))
    # ★2026-10-07(CI で判明): registry の op 数は入っている backend で変わる(py3.10/3.12 の CI は 910)。
    #   見出し(上)は同梱の名前表だけで決まるので常に照合し、registry 行は完全な registry の環境でだけ照合する。
    from conftest import requires_full_registry
    requires_full_registry()
    m2 = re.search(r"registry ops: (\d+) ; distinct real HALCON ops covered: \*\*(\d+)\*\*", md)
    assert m2 and (int(m2.group(1)), int(m2.group(2))) == (n_registry, reg_cov), (
        "HALCON_PARITY.md の registry 行が古い(数え直し: registry %d / covered %d)"
        % (n_registry, reg_cov))


def test_lib_coverage_registry_table_matches_the_shipped_index():
    import lib_coverage as L

    idx = json.loads((ROOT / "docs" / "OP_INDEX.json").read_text(encoding="utf-8"))
    names = [o["name"] for o in idx["ops"] if o["tier"] in ("registry", "color")]
    assert len(names) > 500, "索引から registry の op を数えられていない(%d)" % len(names)

    class _Op:  # registry_by_library は .name しか見ない
        def __init__(self, n):
            self.name = n

    import ops as R
    real_registry = R.REGISTRY
    try:
        R.REGISTRY = [_Op(n) for n in names]
        expect = L.registry_by_library()
    finally:
        R.REGISTRY = real_registry

    md = (ROOT / "docs" / "LIB_COVERAGE.md").read_text(encoding="utf-8")
    m = re.search(r"\| \*\*total\*\* \| \*\*(\d+)\*\* \|", md)
    assert m, "docs/LIB_COVERAGE.md に total 行が無い"
    assert int(m.group(1)) == len(names), (
        "LIB_COVERAGE.md の合計は %s op、同梱索引では %d op —— `py -3.11 lib_coverage.py` を回すこと"
        % (m.group(1), len(names)))
    got = collections.Counter({k: int(v) for k, v in
                               re.findall(r"^\| ([^|*][^|]*?) \| (\d+) \|$", md, re.M)})
    assert got == expect, "LIB_COVERAGE.md のライブラリ別 op 数が索引と食い違う: 表 %s / 索引 %s" % (
        dict(got), dict(expect))
