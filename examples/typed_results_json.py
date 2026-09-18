# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""typed_results_json — op の返り値(型付き)を JSON に出して、bit そのままで戻す。

    py -3.11 examples/typed_results_json.py

【この例が示すこと】
``fs.to_json(value, sort)`` / ``fs.from_json(text)`` で、image / region / points / contour /
feature / matrix / table を JSON にして戻す。浮動小数は base64 の float64 なので往復で
**bit が一致**する(assert)。region は run-length、非有限値は封筒に印を立てて bytes で運ぶ。
最後に薄い便利関数(``save_json`` / ``load_json`` でファイル一往復、``to_json_lines`` /
``from_json_lines`` で (value, sort) の列を JSON Lines)も示す。

EXTEND: ファイルに書くなら ``fs.save_json(value, sort, path)``、MCP に渡すなら structuredContent にそのまま。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402


def main() -> int:
    rng = np.random.default_rng(0)
    img = rng.random((6, 8))
    img[0, 0] = np.pi
    samples = {
        "image": img,
        "region": (img > 0.5).astype(np.float64),
        "points": np.array([[1.5, 2.0], [3.25, 4.0], [1.0 / 3.0, 0.1]]),
        "matrix": np.linalg.inv(np.array([[2.0, 1.0], [1.0, 3.0]])),
        "feature": float(np.pi),
        "contour": {"shape": (6, 8), "cs": [np.array([[0.5, 1.5], [2.5, 3.5], [4.5, 1.5]])]},
        "table": {"n": 3, "labels": ["a", "b"], "means": np.array([0.1, 0.2])},
    }
    for sort, value in samples.items():
        text = fs.to_json(value, sort)
        back, s = fs.from_json(text)
        env = json.loads(text)
        if isinstance(value, np.ndarray):
            exact = np.array_equal(value.view(np.uint8), np.asarray(back).view(np.uint8))
        elif sort == "contour":
            exact = np.array_equal(value["cs"][0], back["cs"][0]) and tuple(back["shape"]) == value["shape"]
        elif sort == "table":
            exact = back["means"] == [0.1, 0.2]
        else:
            exact = back == value
        enc = env["payload"].get("encoding", "json") if isinstance(env["payload"], dict) else "json"
        print("%-8s -> %5d bytes  encoding=%-6s  往復 bit 一致=%s" % (sort, len(text), enc, exact))
        assert s == sort and exact, sort
    # 人が読める形(小さい値向け)。数のリストだが、repr は最短の往復可能 10 進なので厳密。
    readable = fs.to_json(samples["points"], "points", readable=True)
    print("readable:", readable[:96], "...")
    back, _ = fs.from_json(readable)
    assert np.array_equal(back.view(np.uint8), samples["points"].view(np.uint8))

    # 便利関数 1: ファイルへ一往復。
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "pts.json")
        fs.save_json(samples["points"], "points", p)
        back, sort = fs.load_json(p)
        assert sort == "points" and np.array_equal(back.view(np.uint8), samples["points"].view(np.uint8))
        print("save/load:", os.path.basename(p), "-> 往復 bit 一致=True")

    # 便利関数 2: (value, sort) の列を JSON Lines(1 行 1 封筒。台帳・ログ向き)。
    items = [(samples["points"], "points"), (samples["feature"], "feature"),
             (samples["region"], "region")]
    jl = fs.to_json_lines(items)
    rows = fs.from_json_lines(jl)
    print("jsonl:    %d 行, 戻した sort = %s" % (jl.count("\n") + 1, [s for _, s in rows]))
    assert [s for _, s in rows] == ["points", "feature", "region"]

    # 便利関数 3: 引数で JSON を渡す。as_value は値でも封筒でも受けて値を返す。
    assert fs.as_value(samples["points"]) is samples["points"]        # 値はそのまま
    v = fs.as_value(fs.to_json(samples["points"], "points"))          # 文字列の封筒 → 値
    assert np.array_equal(v.view(np.uint8), samples["points"].view(np.uint8))
    print("as_value: 値も JSON 封筒も同じ入口で受ける")

    # 便利関数 4: どの op でも JSON 入力 → JSON 出力(apply_json)。出力 sort はレジストリ由来。
    img_json = fs.to_json(img, "image")
    out_json = fs.apply_json(img_json, "gaussian", 1.0, 1.0)          # 画像を封筒で渡す
    out, out_sort = fs.from_json(out_json)
    assert out_sort == "image" and np.array_equal(out, fs.apply(img, "gaussian", 1.0, 1.0))
    print("apply_json: gaussian を JSON 入出力で。otsu →", fs.from_json(fs.apply_json(img, "otsu"))[1])

    # fail-closed: match は橋が無い(慣例が 2 つ混在するため)。
    try:
        fs.to_json(np.zeros(3), "match")
    except ValueError as exc:
        print("match は断られる:", str(exc)[:60])
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
