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
7. n-ary op は ``op_names(include_nary=True)`` で一覧でき(既定は 1 入力の一覧のまま)、``list_ops`` の各行に
   ``knobs``(``a`` の効き方 continuous / discrete / unused、``b`` を使うか、実測の無い op は None)が乗り、
   CLI は ``fullseye apply add_image a.png out.png --input2 b.png`` で 2 入力の op を呼べる(第 18〜20 報 N60 / I1)
8. 台帳の引き方は fail-closed —— ``op_producers`` / ``op_consumers`` は未知の型(と op 名)を ValueError で断り
   (``op_sorts()`` が型名の一覧)、``op_presets`` は未知の op を断る。``write_wav`` の ``path`` は台帳でデータ扱いされず、
   配列や None を渡すと 1 文の TypeError(stdlib の Wave_write が「Exception ignored」を吐かない)。
   入口の関門を持つ 4 op は ``list_ops()`` の ``native_guard`` に理由が載る(第 15・16 報 N67 / N68 / N69 / N71)
9. 画像 I/O は失敗を捨てない —— ``write_image`` は親ディレクトリ不在・書けない拡張子で 1 文の例外(以前は cv2 の False を
   捨てて無言)、``read_image`` は無い / ディレクトリ / 読めないを別の例外で言う。uint16 は 16 bit のまま書け、float は
   既定 8 bit(文書化)で ``depth=16`` / ``depth="float"`` が無損失(第 18 報 N75〜N79)

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

    for bad in ("abc", 5, {"a": 1}):                             # 第 26 報 N97: 素の str / スカラー / dict
        try:
            fs.apply(bad, "sobel_amp")
            raise AssertionError("配列でない image %r が通った" % (bad,))
        except TypeError as e:
            assert "sobel_amp" in str(e)
    print("3c. scalar/str/dict: TypeError regardless of policy (used to come back unchanged under the default fallback)")

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

    # 7. n-ary の一覧と、つまみの機械可読な説明(第 18〜20 報 N60 / I1)
    import api
    names = fs.op_names()
    both = fs.op_names(include_nary=True)
    nary = sorted(set(both) - set(names))
    assert "add_image" not in names and "add_image" in both
    assert nary == sorted({o.name for o in api._nary_by_name().values()}) and both == sorted(both)
    rows = {r["name"]: r for r in fs.list_ops()}
    assert all("knobs" in r for r in rows.values())
    k = rows["add_noise_distribution"]["knobs"]
    assert k["a"] == "continuous" and k["b"] is True, k
    assert rows["abs_image"]["knobs"]["a"] == "unused" and fs.knob_summary("abs_image") == rows["abs_image"]["knobs"]
    n_meas = sum(1 for r in rows.values() if r["knobs"] is not None)
    print("7.  nary/knobs: op_names() %d, with nary %d (+%d: %s ...); knobs measured for %d ops, None for the rest"
          % (len(names), len(both), len(nary), ", ".join(nary[:3]), n_meas))
    print("    CLI       : fullseye apply add_image a.png out.png --input2 b.png   (2 inputs; 1-input ops refuse --input2)")

    # 8. 台帳の引き方は fail-closed、write_wav の path、入口の関門の可視性(第 15・16 報)
    sorts = fs.op_sorts()
    assert "normalmap" in sorts and "signal" in sorts and fs.op_producers("normalmap")
    for bad, why in (("no_such_sort", "unknown sort"), ("gaussian", "op name")):
        try:
            fs.op_producers(bad)
            raise AssertionError("op_producers(%r) が通った" % bad)
        except ValueError as e:
            assert why in str(e), str(e)
    try:
        fs.op_presets("no_such_op_xyz")
        raise AssertionError("未知の op の op_presets が通った")
    except ValueError as e:
        assert "not in any ledger" in str(e)
    assert fs.op_presets("read_wav") == {}                       # 台帳にある op の {} は「意図して無し」
    import dsp
    sig = np.linspace(-0.5, 0.5, 64)
    try:
        dsp.write_wav(sig, sig)                                  # 引数の取り違え
        raise AssertionError("配列を path に渡した write_wav が通った")
    except TypeError as e:
        assert "second argument" in str(e), str(e)
    spec = {p["name"]: p for p in fs.op_assist("write_wav")["params"]} if "params" in fs.op_assist("write_wav") else \
        {p["name"]: p for p in __import__("opassist").param_spec("write_wav")}
    assert spec["path"]["kind"] != "data" and spec["x"]["kind"] == "data" and spec["x"]["sort"] == "signal"
    guarded = {r["name"]: r["native_guard"] for r in rows.values() if r.get("native_guard")}
    assert {"cv_cc_count", "xsitk_minmax_curv_flow", "xsk3_h_minima", "xsk_random_walker"} <= set(guarded)
    print("8.  ledger    : %d sorts; unknown sort / op name / unknown op are ValueError; write_wav(path, x) refuses a non-path;"
          " %d ops carry native_guard" % (len(sorts), len(guarded)))

    # 9. 画像 I/O は失敗を捨てない(第 18 報 N75〜N79)
    try:
        import cv2  # noqa: F401
    except ImportError:
        print("9.  image io  : skipped (opencv-python not installed)")
    else:
        import tempfile
        d = tempfile.mkdtemp()
        x = np.random.default_rng(1).random((24, 24))
        for path, why in ((os.path.join(d, "no_dir", "x.png"), "directory does not exist"), (os.path.join(d, "x.qqq"), "not a writable")):
            try:
                fs.write_image(path, x)
                raise AssertionError("write_image(%r) が無言で通った" % path)
            except (OSError, ValueError) as e:
                assert why in str(e), str(e)
        fs.write_image(os.path.join(d, "g.ppm"), x)                       # ppm は灰を 3 ch に複製
        assert fs.read_image(os.path.join(d, "g.ppm")).shape == (24, 24)
        fs.write_image(os.path.join(d, "u16.png"), np.round(x * 65535).astype(np.uint16))
        fs.write_image(os.path.join(d, "f16.png"), x, depth=16)
        fs.write_image(os.path.join(d, "f32.pfm"), x, depth="float")
        fs.write_image(os.path.join(d, "f8.png"), x)
        err = {n: float(np.abs(fs.read_image(os.path.join(d, n)) - x).max()) for n in ("u16.png", "f16.png", "f32.pfm", "f8.png")}
        assert err["u16.png"] < 1e-4 and err["f16.png"] < 1e-4 and err["f32.pfm"] < 1e-6 and 1e-3 < err["f8.png"] <= 1 / 510 + 1e-9, err
        for bad, exc in ((os.path.join(d, "nope.png"), FileNotFoundError), (d, IsADirectoryError)):
            try:
                fs.read_image(bad)
                raise AssertionError("read_image(%r) が通った" % bad)
            except exc:
                pass
        print("9.  image io  : write refuses missing dir / bad ext; ppm ok; round-trip error u16 %.1e, depth=16 %.1e, float %.1e, default 8-bit %.1e"
              % (err["u16.png"], err["f16.png"], err["f32.pfm"], err["f8.png"]))
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
