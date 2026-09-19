# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""degenerate_inputs — 空・極小・1-D・RGB の退化入力で、どの op でも同じ文が返ることを確かめる。

    py -3.11 examples/degenerate_inputs.py

【この例が示すこと】
2026-09-19、image/region 入力の全 681 op に 7 種の退化入力を ``on_error="raise"`` で渡して分類した
(空 (0,0) / 1×1 / 2×2 / 1-D / inf / 範囲外 / RGB (H,W,3))。空配列は **271 op が 49 種類の生エラー**
(numpy の reduction、OpenCV の assert、FFT の data points 0、ZeroDivisionError …)で落ち、410 op は
空や定数を黙って返していた。極小画像では kornia / numpy / skimage の、**どの op が投げたか書いていない**
例外が 9〜19 群。直したあとの形を 1 本ずつ確かめる:

1. 空配列は**どの op でも同じ 1 文**(`empty input … check the step upstream`)。既定方針では台帳に記録して
   sort の既定値、`raise` で止まる
2. 極小画像で op の中から出る生の例外には、**型も文も変えず** op 名と入力の形を注記(Python 3.11+ の
   `add_note`。`raise` の約束「op の本当の例外をそのまま」を守る)
3. 1-D 配列と RGB (H,W,3) は既存の門が断る(RGB は `docs/KNOWN_ISSUES.md` #32-4 のとおり 3-D を体積として
   通す op があり、ここでは 1-D だけ assert)

EXTEND: 自分の op 群に同じ走査を掛けるなら、`fs.op_names()` を回して例外の型と文を集計する(この例の
`survey()`)。「生エラー」の判定 = 文に op 名も fullseye の語も無い。
"""
from __future__ import annotations

import os
import sys
import warnings

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402

EMPTY = np.zeros((0, 0))
SAMPLE = ["gaussian", "sobel_amp", "otsu", "tophat", "fft_image", "lowpass", "reg_erode", "median_image"]


def survey(names, arr, label):
    """*arr* を各 op に raise で渡し、(clean, raw, ok) の件数を返す。"""
    clean = raw = ok = 0
    for n in names:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                fs.apply(arr, n, on_error="raise")
            ok += 1
        except Exception as e:  # noqa: BLE001 - 分類のために全部受ける
            if n in str(e) or "fullseye" in str(e).lower():
                clean += 1
            else:
                raw += 1
    print("%-6s: ok %d / clean error %d / raw error %d" % (label, ok, clean, raw))
    return clean, raw, ok


def main() -> int:
    # 1. 空配列: 全部が同じ文
    clean, raw, ok = survey(SAMPLE, EMPTY, "empty")
    assert raw == 0 and ok == 0 and clean == len(SAMPLE), (clean, raw, ok)
    try:
        fs.apply(EMPTY, "gaussian", on_error="raise")
    except ValueError as e:
        assert "empty input" in str(e) and "upstream" in str(e)
        print("   e.g.", str(e)[:110], "...")
    fs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = fs.apply(EMPTY, "gaussian")                       # 既定方針: 記録して既定値
    assert any("empty input" in e["error"] for e in fs.fallbacks()) and isinstance(out, np.ndarray)
    print("   default policy: recorded in fullseye.fallbacks(), returned", out.shape)

    # 2. 極小画像: 生の例外に op 名と形の注記
    if hasattr(BaseException, "add_note"):
        try:
            fs.apply(np.full((1, 1), 0.5), "structure_tensor_orientation", on_error="raise")
            raise AssertionError("1x1 の勾配が通った")
        except ValueError as e:
            notes = getattr(e, "__notes__", [])
            assert any("structure_tensor_orientation" in n and "(1, 1)" in n for n in notes), notes
            print("2. tiny  : %s: %s" % (type(e).__name__, str(e)[:60]))
            print("   note  :", notes[0][:110], "...")
    else:
        print("2. tiny  : (add_note needs Python 3.11+; skipped)")

    # 3. 1-D は既存の門
    try:
        fs.apply(np.zeros(32), "gaussian", on_error="raise")
        raise AssertionError("1-D が通った")
    except ValueError as e:
        assert "expects a image" in str(e)
        print("3. 1-D   :", str(e)[:90])
    # 4. 部分 NaN: 出力は有限に「なる」が、黙ってはならない(台帳に output 起源の記録 / raise では停止)
    x = np.random.default_rng(0).random((9, 9))
    x[4, 4] = np.nan
    fs.clear_fallbacks()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = fs.apply(x, "gaussian")
    recs = [e for e in fs.fallbacks() if e["source"] == "output" and "non_finite_output" in e["error"]]
    assert np.isfinite(out).all() and recs, recs
    print("4. NaN in :", "finite output, recorded:", recs[0]["error"][:90], "...")
    try:
        fs.apply(x, "gaussian", on_error="raise")
        raise AssertionError("部分 NaN が raise で通った")
    except ValueError as e:
        assert "non_finite_output" in str(e)
        print("   raise  :", str(e)[:80], "...")

    # 5. n-ary op は op_find から見える(op_names には 1 入力の op しか無い)
    hits = [h["op"] for h in fs.op_find("add_image")]
    assert "add_image" in hits[:3], hits[:5]
    assert "add_image" not in fs.op_names()
    print("5. op_find :", hits[:3], "| call:", next(h["call"] for h in fs.op_find("add_image") if h["op"] == "add_image"))
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
