# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""interactive_poc_viewer — PoC の結果を「触って見る」1 枚の HTML にする(fs.write_viewer)。

    py -3.11 examples/interactive_poc_viewer.py

【この例が示すこと】
タブ(同じ課題を違う方法で)・正直なバッジ(門を通った / 限界を見せる / 何もしない場合)・実測の数字・
ドラッグで回せる 3-D 点群・コマ送りの 2-D 動画と時系列・前後を比べる分割線を、**自己完結した 1 ファイル**
(暗色、外部読み込み無し、file:// と iPhone の Safari で動く)に書き出す。言語は ``lang`` で選ぶ:
``"ja"`` なら単言語、``["ja", "en", "fr"]`` なら切り替えつき(先頭が既定)。文字列は
``fs.viewer_text(ja, en, zh=..., ...)`` で言語ごとに渡し、要求した言語が欠けたら黙って補わず ValueError。

ここでは小さな合成データで 4 種のペイロードを 1 本のビューアにし、書いた HTML を読み戻して
(埋めた位置が量子化の刻みの半分以内で戻る / 外部 URL が無い)を確かめて PASS を出す。

EXTEND: 実際の PoC のビューアは ``tools/build_view2026_viewers.py``(CAD の偏差 / LiDAR の地形変化 /
テンプレート追跡)。自分の PoC なら、その計算で得た配列を ``viewer_points_tab`` などに渡すだけ。
数字は手で写さず、実行から取る(カードの ``numbers`` に ``viewer_number`` で渡す)。
"""
from __future__ import annotations

import json
import os
import re
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fullseye as fs  # noqa: E402


def _t(ja: str, en: str) -> dict:
    return fs.viewer_text(ja, en)


def main() -> int:
    rng = np.random.default_rng(0)

    # 1) 点群: 平らな板に、中央だけへこんだ「実測」。色 = 符号付き偏差 [µm]
    xy = rng.uniform(-20, 20, (4000, 2))
    dent = -60.0 * np.exp(-(xy ** 2).sum(1) / (2 * 6.0 ** 2))
    pts = np.column_stack([xy, 0.001 * dent])
    cb = {"lo": -100.0, "hi": 100.0, "unit": "µm", "cmap": "div", "label": _t("偏差", "Deviation")}
    t_pts = fs.viewer_points_tab(
        "dent", _t("へこみ", "A dent"), "passed", _t("中央に 60 µm のへこみ。", "A 60 µm dent at the centre."),
        pts, val=dent + rng.normal(0, 3, len(dent)), cbar=cb,
        numbers=[fs.viewer_number(_t("最大", "Max"), "%.1f µm" % -dent.min())])
    t_null = fs.viewer_points_tab(
        "flat", _t("何もしない", "Do nothing"), "null", _t("へこみを入れない対照。", "A control without the dent."),
        pts, val=rng.normal(0, 3, len(dent)), cbar=cb)

    # 2) 2-D 動画: 動く明るい点を、真の位置と(わざと遅れた)推定で追う
    T, H, W = 20, 48, 64
    tx = np.linspace(8, 56, T)
    ty = 24 + 10 * np.sin(np.linspace(0, 3, T))
    yy, xx = np.mgrid[0:H, 0:W]
    frames = np.stack([np.exp(-((xx - tx[i]) ** 2 + (yy - ty[i]) ** 2) / 18.0) for i in range(T)])
    est = np.column_stack([np.r_[tx[0], tx[:-1]], np.r_[ty[0], ty[:-1]]])      # 1 コマ遅れ
    err = np.hypot(est[:, 0] - tx, est[:, 1] - ty)
    t_fr = fs.viewer_frames_tab(
        "track", _t("追跡", "Tracking"), "limit", _t("推定は 1 コマ遅れる。", "The estimate lags by one frame."),
        frames, dt=0.2,
        boxes=[{"label": _t("真の位置", "Truth"), "color": "#4fc3f7", "xy": np.column_stack([tx, ty]), "size": [9, 9]},
               {"label": _t("推定", "Estimate"), "color": "#ffb74d", "xy": est, "size": [11, 11],
                "flag": err > 2.5, "flag_text": _t("ずれ", "off")}],
        series=[{"label": _t("誤差", "Error"), "values": err, "lo": 0.0, "hi": 5.0, "unit": "px", "decimals": 1}])

    # 3) 前後の分割
    before = (255 * np.clip(frames[0], 0, 1)).astype(np.uint8)
    after = (255 * np.clip(frames[-1], 0, 1)).astype(np.uint8)
    t_sp = fs.viewer_split_tab("split", _t("前後", "Before/after"), "passed", _t("ドラッグして比べる。", "Drag to compare."),
                               before, after, _t("最初", "First"), _t("最後", "Last"))

    # 4) 三角形メッシュ + 頂点ごとの値
    gx, gy = np.meshgrid(np.linspace(-1, 1, 20), np.linspace(-1, 1, 20))
    verts = np.column_stack([gx.ravel(), gy.ravel(), 0.3 * np.cos(3 * gx.ravel()) * np.cos(3 * gy.ravel())])
    idx = np.arange(400).reshape(20, 20)
    a, b, c, d = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel()
    faces = np.concatenate([np.column_stack([a, b, c]), np.column_stack([b, d, c])])
    t_me = fs.viewer_mesh_tab("mesh", _t("曲面", "Surface"), "passed", _t("高さで色づけ。", "Coloured by height."),
                              verts, faces, verts[:, 2], {"lo": -0.3, "hi": 0.3, "unit": "mm", "cmap": "seq"})

    spec = fs.viewer_spec("interactive_poc_viewer", _t("触って見るビューアの見本", "A sample interactive viewer"),
                          _t("4 種のペイロードを 1 本に。", "Four payload kinds in one page."),
                          _t("ドラッグで回転、ホイールで拡大。", "Drag to rotate, wheel to zoom."),
                          [t_pts, t_null, t_fr, t_sp, t_me])
    with tempfile.TemporaryDirectory() as d:
        path = fs.write_viewer(spec, os.path.join(d, "sample.html"), ["ja", "en"])     # 切り替えつき(ja が既定)
        single = fs.write_viewer(spec, os.path.join(d, "sample_en.html"), "en")        # 英語だけ
        html = open(path, encoding="utf-8").read()
        print("書いた: %.0f KB(ja+en)/ %.0f KB(en だけ)、タブ %d 本"
              % (os.path.getsize(path) / 1e3, os.path.getsize(single) / 1e3, len(spec["tabs"])))
        data = json.loads(re.search(r"const D = (\{.*?\});\nconst \$ = ", html, re.S).group(1))
        rec = data["arrays"][next(t for t in data["tabs"] if t["id"] == "dent")["pos"]]
        back = fs.pocviewer.decode_array(rec)
        step = fs.pocviewer.quant_step(rec)
        worst = float(np.max(np.abs(back - pts) / (step / 2)))
        print("位置の復元: 最悪で刻みの半分の %.2f 倍(1 以下なら量子化の範囲内)" % worst)
        assert worst <= 1.0 + 1e-9, worst
        assert "http://" not in html and "https://" not in html, "外部 URL がある"
        try:                                         # 欠けた訳は黙って補わない
            fs.write_viewer(spec, os.path.join(d, "x.html"), ["ja", "fr"])
        except ValueError as exc:
            print("fr の訳が無いので拒否: %s" % str(exc)[:80])
        else:
            raise AssertionError("fr の訳が無いのに書けてしまった")
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
