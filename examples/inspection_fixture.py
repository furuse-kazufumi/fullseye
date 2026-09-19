# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""inspection_fixture — 既知の良品/不良品セットで検査レシピと仕様を配備前に検定し、余裕(margin)を測る。

    py -3.11 examples/inspection_fixture.py

【この例が示すこと】
レシピと仕様を決めたあとの最初の問い「良品は全部通り、不良品は全部止まるか」「どれくらい余裕があるか」を
``fs.inspection_fixture`` 1 回で答える:

1. 合成の良品 6 枚 / 不良品 4 枚(明部の大きさが違う)で仕様 400±60 px → **passed**、余裕は限界幅の 1.0 倍
2. 仕様を締めすぎる(mean ≤ 0.3)と良品が全部 ng = **過検出で failed**(false_rejects に行が並ぶ)
3. 仕様を緩めすぎる(400±600 px)と不良品が全部 ok = **見逃しで failed**(escapes に行が並ぶ)
4. 壊れたファイルが 1 枚混ざると error で failed(黙って passed にしない)

を assert で確かめる。margin は仕様の単位で返り、負なら超過。

EXTEND: ``measure`` にゴールデン比較(``fs.golden_measure``)を入れれば、良品/不良品セットでゴールデン比較の
閾値と max_shift の余裕を測れる。レポートは ``report_path`` で良品/不良品それぞれ .xlsx/.md/.jsonl に。
"""
from __future__ import annotations

import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402


def plate(k=10, seed=0):
    rng = np.random.default_rng(seed)
    im = 0.30 + 0.02 * rng.standard_normal((64, 64))
    im[32 - k:32 + k, 32 - k:32 + k] = 0.9
    return np.clip(im, 0, 1)


def measure(im):
    return {"mean": float(im.mean()), "bright_px": float((im > 0.5).sum())}


SPEC = {"bright_px": {"nominal": 400.0, "tol": 60.0}, "mean": {"min": 0.2, "max": 0.6}}


def main() -> int:
    work = tempfile.mkdtemp(prefix="fullseye_fixture_")
    good, bad = os.path.join(work, "good"), os.path.join(work, "bad")
    os.makedirs(good); os.makedirs(bad)
    for i in range(6):
        np.save(os.path.join(good, "good_%02d.npy" % i), plate(10, seed=i))
    for i, k in enumerate((13, 15, 7, 15)):
        np.save(os.path.join(bad, "bad_%02d.npy" % i), plate(k, seed=10 + i))

    # 1. 分離できる仕様 → passed + margin
    f = fs.inspection_fixture(good, bad, None, measure=measure, spec=SPEC,
                              report_path=os.path.join(work, "fixture.md"), title="Fixture A")
    print("A:", f["detail"])
    print("   margins:", {k: (round(v["min_margin"], 3), round(v["min_margin_norm"], 3)) for k, v in f["margins"].items()})
    assert f["passed"] and f["confusion"]["bad"]["ng"] == 4
    assert abs(f["margins"]["bright_px"]["min_margin_norm"] - 1.0) < 1e-9

    # 2. 締めすぎ → 過検出
    f = fs.inspection_fixture(good, bad, None, measure=measure, spec=dict(SPEC, mean={"min": 0.2, "max": 0.3}))
    print("B:", f["detail"])
    assert not f["passed"] and len(f["false_rejects"]) == 6

    # 3. 緩めすぎ → 見逃し
    f = fs.inspection_fixture(good, bad, None, measure=measure, spec=dict(SPEC, bright_px={"nominal": 400.0, "tol": 600.0}))
    print("C:", f["detail"])
    assert not f["passed"] and len(f["escapes"]) == 4

    # 4. 壊れたファイルは error で failed
    with open(os.path.join(bad, "bad_99.npy"), "wb") as fh:
        fh.write(b"broken")
    f = fs.inspection_fixture(good, bad, None, measure=measure, spec=SPEC)
    print("D:", f["detail"])
    assert not f["passed"] and len(f["errors"]) == 1
    print("reports:", os.path.join(work, "fixture_good.md"), "/ fixture_bad.md")
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
