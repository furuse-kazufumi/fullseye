# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""genspark_external_review — 第三者(GenSpark)が 0.2.0 で見つけた「初見の利用者を迷わせる摩擦」を、直したあとの形で 1 本ずつ確かめる。

    py -3.11 examples/genspark_external_review.py

【この例が示すこと】
2026-09-19、GenSpark が fullseye 0.2.0 を core(`pip install fullseye`)と all(`fullseye[all]`)の 2 環境で
使い込み、実行出力つきで 12 + 3 + 3 件を報告した。1 件ずつ再現してからバグ側を直し、この例が
**利用者が最初に読むエラー文**を固定する(記録 = docs/hardening/unknown-operator-hides-missing-backend.md ほか 2 本):

1. 「無い」と「入っていない」を分ける —— 本当に無い名前は KeyError で実在の CLI(`fullseye has`)と
   `op_find` を案内し、backend が入っていないだけの名前は ``fs.MissingBackendError``(KeyError の派生)が
   モジュール・不足依存・`pip install "fullseye[<extra>]"` を言う
2. ``run_pipeline`` の書き方 5 形が同じ結果になり、外した形は**原因を指す** TypeError になる
3. 判別できない入力 —— 全 NaN の otsu は明示エラー(fallback 方針では台帳へ)、文字列・複素配列は
   **方針に依らず** TypeError(落とし先が無い入力を「全 0」にするのは fallback でなく嘘)
4. n-ary の形状不一致は「同じ形で / crop・pad・resize を先に」を文で言う
5. ``Op`` は名前で pickle できる(multiprocessing / joblib に渡せる)

を assert で確かめる。設計として変えなかった点(既定 ``on_error="fallback"``、警告は op ごとに 1 度、
float32 の昇格は記録しない)も最後に実演する。

EXTEND: 厳格運用にするなら環境変数 ``FULLSEYE_ON_ERROR=raise`` を立てる(全 apply / run_pipeline の既定が
fail-closed になる)。CI や検証ではそれを推奨(docs/GETTING_STARTED.md の「失敗したらどうなるか」)。
"""
from __future__ import annotations

import os
import pickle
import sys
import warnings

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402
import ops  # noqa: E402


def main() -> int:
    img = np.random.default_rng(0).random((32, 32))

    # 1. 「無い」と「入っていない」
    try:
        fs.apply(img, "no_such_op_xyz")
    except fs.MissingBackendError:
        raise AssertionError("本当に無い名前が MissingBackendError になった")
    except KeyError as e:
        msg = str(e)
        assert "fullseye has no_such_op_xyz" in msg and "op_find" in msg, msg
        print("1a. unknown :", msg[:110], "...")
    # backend が無い環境を、同梱索引を差し替えて再現する(この checkout は all 相当なので本物は起きない)
    import api
    saved = api._SHIPPED_INDEX_CACHE
    api._SHIPPED_INDEX_CACHE = {"demo_missing_op": {"name": "demo_missing_op", "tier": "registry",
                                                    "module": "backends_ski2", "requires": ["skimage", "not_installed_demo_mod"]}}
    try:
        fs.apply(img, "demo_missing_op")
    except fs.MissingBackendError as e:
        assert isinstance(e, KeyError) and "pip install" in str(e), str(e)
        print("1b. missing :", str(e)[:150], "...")
    finally:
        api._SHIPPED_INDEX_CACHE = saved
    row = api._shipped_index()["otsu"]
    print("1c. index   : otsu ->", row["module"], row["requires"], "| sk_canny ->",
          api._shipped_index().get("sk_canny", {}).get("requires"))

    # 2. run_pipeline の 5 形 + 外した形
    ref = fs.run_pipeline(img, [("gaussian", 0.3, 0.5), ("otsu", 0.5, 0.5)])
    for stages in ([("gaussian", {"a": 0.3}), ("otsu", {})],
                   [{"op": "gaussian", "a": 0.3}, {"name": "otsu"}],
                   [("gaussian", 0.3), "otsu"]):
        assert np.array_equal(fs.run_pipeline(img, stages), ref)
    assert np.array_equal(fs.run_pipeline(img, "gaussian, otsu", a=0.3),
                          fs.run_pipeline(img, ["gaussian", "otsu"], a=0.3))
    bad_forms = (
        (([("gaussian",), ("otsu",)], img), "swapped"),           # 引数の順が逆
        ((img, [("gaussian", {"sigma": 2})]), "unknown knob"),    # op は a と b しか持たない
        ((img, [(0.3, "gaussian")]), "stage 0"),                  # 段は名前で始まる
    )
    for bad, why in bad_forms:
        try:
            fs.run_pipeline(*bad)
            raise AssertionError("外した形が通った: %r" % (bad[1],))
        except TypeError as e:
            assert why in str(e), (why, str(e))
            print("2.  %-13s:" % why, str(e)[:100], "...")

    # 3. 判別できない入力
    try:
        fs.apply(np.full((8, 8), np.nan), "otsu", on_error="raise")
        raise AssertionError("全 NaN の otsu が通った")
    except ValueError as e:
        print("3a. all-NaN  :", str(e)[:90], "...")
    fs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = fs.apply(np.full((8, 8), np.nan), "otsu")          # 既定方針: 台帳に記録して region の既定値
    assert out.shape == (8, 8) and any(e["name"] == "otsu" for e in fs.fallbacks())
    for arr, why in ((np.array([["a"] * 4] * 4), "numeric"), (img + 1j * img[::-1], "imaginary")):
        last = ""
        for pol in ("fallback", "raise"):
            try:
                fs.apply(arr, "sobel_amp", on_error=pol)
                raise AssertionError("%s が %s で通った" % (arr.dtype, pol))
            except TypeError as e:
                assert why in str(e), str(e)
                last = str(e)
        print("3b. %-9s: TypeError under every policy —" % arr.dtype, last[:70], "...")

    # 4. n-ary の形状不一致
    try:
        fs.apply([img, img[:, :16]], "add_image", on_error="raise")
        raise AssertionError("形状不一致の add_image が通った")
    except ValueError as e:
        assert "share one shape" in str(e)
        print("4.  shapes   :", str(e)[:100], "...")

    # 5. Op は名前で pickle
    op = next(o for o in ops.REGISTRY if o.name == "otsu")
    assert pickle.loads(pickle.dumps(op)) is op
    print("5.  pickle   : Op('otsu') round-trips by name")

    # 変えなかった設計: 変換のある dtype は既定で通り、台帳に全件残る(警告は op ごとに 1 度)
    fs.clear_fallbacks()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        for arr in ((img * 255).astype(np.uint8), (img * 10).astype(np.int32), img > 0.5):
            fs.apply(arr, "median_image")
    # 台帳の文は "ValueError: dtype_converted: uint8 -> float64 (/255); ..." —— 変換元の dtype だけ抜く
    kinds = [e["error"].split("dtype_converted:")[1].split("->")[0].strip()
             for e in fs.fallbacks() if e["name"] == "median_image" and "dtype_converted:" in e["error"]]
    print("6.  design   : %d conversions recorded %s, %d warning(s) (once per op); float32 is an exact upcast, not recorded"
          % (len(kinds), kinds, sum(isinstance(x.message, fs.FullseyeFallbackWarning) for x in w)))
    assert len(kinds) == 3
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
