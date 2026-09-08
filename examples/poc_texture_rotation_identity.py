# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_texture_rotation_identity — 回しても素材を見分けられるか(実写テクスチャ)。

    py -3.11 examples/poc_texture_rotation_identity.py

【なぜ要るか】
著者の指摘(2026-09-08)「PoC の評価に回転成分が入っていない」「物によっては回転を
かけても成り立つのか見れるものもありそう」。テクスチャ記述子は**まさにその「物」**で、
LBP には「回転不変」と名の付く符号化があり、GLCM には角度がある。ここで問うのは

    **記述子がどれだけ動いたか**ではなく、**回した自分は、まだ別の素材より近いか**

という**判断のレベル**の問い。振れ幅は「大きい / 小さい」としか言えないが、
取り違えの回数は「使えるか / 使えないか」を直接答える。

【素材 —— 実写(CC0)】
`brick` / `grass` / `gravel`(CC0Textures、scikit-image 同梱。追加ダウンロードなし)。
**異方な素材(brick は横方向の目地)と等方な素材(grass, gravel)を混ぜてある** ――
どちらか片方だけだと、結論が素材の性質か記述子の性質か分けられない。

【グラウンドトゥルース(すべて assert で落とす)】
0. **回す前に、0 度どうしで 3 素材が分かれていること**を確かめる。ここが 0 なら
   「回して取り違えた」も何も測れていない(分母を先に見る)。
1. 回転は `reshape=False` + `mode="reflect"` で行い、**中央を小さく切り出す**。
   こうしないと外周のゼロ埋めがテクスチャ統計に混ざり、記述子でなく縁を測ることになる。
2. **GLCM(`cooc_feature_matrix`)は角度 0 度固定**なので、向きに依存するのが道理。
   `b >= 0.75` の 4 方向平均で救えるはず。★ここで**予測を外した**: 「異方な brick では
   平均が逆効果になる」と読んでいたが、実際に効き方を決めていたのは素材の異方性ではなく
   **共起距離 `a`** だった。距離 1 では平均が効き(3/36 -> 0/36)、距離 4 では悪化する
   (3/36 -> 8/36)。原因は平均ではなく**分母** —— 距離を伸ばすと 3 素材の 0 度での差
   そのものが 0.0448 -> 0.0221 と半分に潰れ、残り少ない差が平均で先に消える。
3. **LBP の「回転不変」符号化(`uniform` / `ror`)は、実写では救いにならない**はず
   (`sk_lbp` の docstring に既にそう書いてある)。ここで公開の展示として数える。

【読み方】各節は「予測 → 実測 → 差」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import sys
import time
import warnings
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import realdata                                                  # noqa: E402

MATS = ("brick", "grass", "gravel")
ANGLES = np.arange(0.0, 180.0, 15.0)         # 12 角度(テクスチャは 180 度で一巡)
SRC, CROP = 200, 120                         # 切り出しを小さくして縁を混ぜない


def _patch(name):
    im = np.asarray(realdata.sample_photo(name), dtype=np.float64)
    if im.ndim == 3:
        im = im.mean(axis=2)
    h, w = im.shape[:2]
    r0, c0 = (h - SRC) // 2, (w - SRC) // 2
    return im[r0:r0 + SRC, c0:c0 + SRC]


def _rot(img, deg):
    """回してから**中央を小さく切る**。外周のゼロ埋めを統計に入れないため。"""
    from scipy import ndimage
    r = ndimage.rotate(img, float(deg), reshape=False, order=1, mode="reflect")
    h, w = r.shape
    r0, c0 = (h - CROP) // 2, (w - CROP) // 2
    return r[r0:r0 + CROP, c0:c0 + CROP]


# --------------------------------------------------------------------------- #
# 記述子 —— どちらも fullseye の op
# --------------------------------------------------------------------------- #
def _glcm(img, a=0.5, b=0.5):
    return np.array([float(fs.op.cooc_feature_matrix(img, a=a, b=b))])


def _lbp(img, b, bins=32):
    with warnings.catch_warnings():
        # skimage は float 入力に注意を出す(隣接画素の差が極小のとき)。
        # ここは実写の連続階調なので想定どおりの使い方。
        warnings.simplefilter("ignore", UserWarning)
        v = np.asarray(fs.op.sk_lbp(img, b=b), dtype=np.float64).ravel()
    h, _ = np.histogram(v, bins=bins, range=(0.0, 1.0), density=True)
    return h / max(float(h.sum()), 1e-12)


def _audit(desc, tag):
    """0 度の分離 → 回転での取り違え。**分母(分離)を先に返す**。"""
    base = {m: desc(_rot(_patch(m), 0.0)) for m in MATS}
    sep = min(float(np.abs(base[a] - base[c]).sum())
              for i, a in enumerate(MATS) for c in MATS[i + 1:])
    per, swings = {}, {}
    for m in MATS:
        wrong = 0
        vals = []
        for d in ANGLES:
            h = desc(_rot(_patch(m), float(d)))
            vals.append(h)
            d_self = float(np.abs(h - base[m]).sum())
            if min(float(np.abs(h - base[o]).sum()) for o in MATS if o != m) < d_self:
                wrong += 1
        per[m] = wrong
        v = np.asarray(vals)
        swings[m] = float(np.abs(v.max(axis=0) - v.min(axis=0)).sum())
    return {"tag": tag, "sep": sep, "wrong": per, "swing": swings,
            "total": len(ANGLES) * len(MATS), "base": base}


def _print(r):
    print("   %-22s 0 度の分離 %.4f" % (r["tag"], r["sep"]))
    for m in MATS:
        print("     %-7s 取り違え %2d/%2d   振れ幅 %.4f(分離の %.2f 倍)"
              % (m, r["wrong"][m], len(ANGLES), r["swing"][m],
                 r["swing"][m] / max(r["sep"], 1e-12)))
    print("     合計 %d/%d" % (sum(r["wrong"].values()), r["total"]))


# --------------------------------------------------------------------------- #
def main():
    t0 = time.perf_counter()
    print("素材(CC0Textures / scikit-image 同梱、追加ダウンロードなし):",
          ", ".join("%s(%s)" % (m, realdata.SAMPLE_PHOTOS[m][2]) for m in MATS))

    print("\n0) 分母を先に見る —— 回す前に 3 素材が分かれているか")
    g0 = _audit(lambda im: _glcm(im, 0.0, 0.5), "GLCM 0 度固定・距離 1")
    assert g0["sep"] > 0.02, ("0 度で素材が分かれていない。取り違えを数えても意味が無い",
                              g0["sep"])
    print("   GLCM の 0 度の値: %s、最小の素材間差 %.4f"
          % ({m: round(float(g0["base"][m][0]), 4) for m in MATS}, g0["sep"]))

    print("\n1) GLCM は角度 0 度固定 —— 予測: 向きに依存するので、4 方向平均が効くはず。")
    print("   ★ただし『効く』は距離 a に依らない、とは限らない。a を振って確かめる。")
    grid = {}
    for a in (0.0, 0.5, 1.0):
        for b, tag in ((0.5, "0deg"), (0.8, "4avg")):
            grid[(a, b)] = _audit(lambda im, a=a, b=b: _glcm(im, a, b), tag)
    print("   距離  そろえ方   0 度の分離  取り違え   振れ幅/分離(brick/grass/gravel)")
    for a in (0.0, 0.5, 1.0):
        for b, tag in ((0.5, "0 度固定"), (0.8, "4 方向平均")):
            r = grid[(a, b)]
            rat = tuple(r["swing"][m] / max(r["sep"], 1e-12) for m in MATS)
            print("   %-5d %-10s %8.4f   %2d/%2d      %.2f / %.2f / %.2f"
                  % (1 + int(a * 3), tag, r["sep"], sum(r["wrong"].values()),
                     r["total"], *rat))

    w = {(a, b): sum(grid[(a, b)]["wrong"].values()) for a, b in grid}
    print("   -> 距離 1 では平均が効く(%d/36 -> %d/36)。距離 4 では**悪化する**"
          "(%d/36 -> %d/36)。" % (w[(0.0, 0.5)], w[(0.0, 0.8)],
                                   w[(1.0, 0.5)], w[(1.0, 0.8)]))
    print("      ★悪化の原因は平均ではなく**分母**: 距離を伸ばすと 3 素材の 0 度での"
          "差そのものが %.4f -> %.4f と半分に潰れる。"
          % (grid[(0.0, 0.5)]["sep"], grid[(1.0, 0.5)]["sep"]))
    print("      残り少ない差を平均すれば、先に消える。**長い距離で平均を掛ける前に、"
          "素材が分かれているかを確かめること。**")
    assert w[(0.0, 0.5)] > 0 and w[(0.0, 0.8)] == 0, (w[(0.0, 0.5)], w[(0.0, 0.8)])
    assert w[(1.0, 0.8)] > w[(1.0, 0.5)], (w[(1.0, 0.5)], w[(1.0, 0.8)])
    assert grid[(1.0, 0.5)]["sep"] < grid[(0.0, 0.5)]["sep"] * 0.6, (
        grid[(0.0, 0.5)]["sep"], grid[(1.0, 0.5)]["sep"])
    # 既定(距離 2)では平均が brick の余裕を大きく増やす
    r0, r4 = grid[(0.5, 0.5)], grid[(0.5, 0.8)]
    b0 = r0["swing"]["brick"] / r0["sep"]
    b4 = r4["swing"]["brick"] / r4["sep"]
    print("      既定の距離 2 ではどちらも %d/36 だが、brick の振れ幅は分離の "
          "%.2f -> %.2f 倍へ下がる(余裕が増える)。" % (w[(0.5, 0.5)], b0, b4))
    assert b4 < b0 * 0.8, (b0, b4)
    g0 = grid[(0.0, 0.5)]

    print("\n2) LBP の「回転不変」符号化は、実写では救いにならない")
    l0 = _audit(lambda im: _lbp(im, 0.0), "LBP default(不変でない)")
    l1 = _audit(lambda im: _lbp(im, 0.8), "LBP uniform(回転不変)")
    _print(l0)
    _print(l1)
    a_lbp, b_lbp = sum(l0["wrong"].values()), sum(l1["wrong"].values())
    print("   -> 合計 %d/%d -> %d/%d。**名前に「不変」と付いていても、実写では"
          "半分前後を取り違える**。" % (a_lbp, l0["total"], b_lbp, l1["total"]))
    assert a_lbp > l0["total"] * 0.3 and b_lbp > l1["total"] * 0.3, (a_lbp, b_lbp)
    assert abs(a_lbp - b_lbp) <= l0["total"] * 0.2, (
        "uniform が劇的に効くなら、この結論は古い", a_lbp, b_lbp)

    # 図
    n = 0
    if figs.enabled():
        tiles = []
        for m in MATS:
            row = [np.clip(_rot(_patch(m), float(d)), 0, 1) for d in (0.0, 45.0, 90.0)]
            tiles.append(np.concatenate(row, axis=1))
        # ★実写は**グレーのまま**出す。2-D をそのまま渡すと examplefig が
        #   疑似カラー(viridis)を掛けてしまい、「写真だから説得力がある」
        #   という趣旨が消える。RGB にして渡せば色を触られない。
        sheet = np.concatenate(tiles, axis=0)
        sheet = np.repeat(np.clip(sheet, 0.0, 1.0)[..., None], 3, axis=2)
        figs.save("texture_rotations", sheet,
                  caption="上から brick / grass / gravel、左から 0 / 45 / 90 度。"
                          "brick だけ**向きが手がかり**になっているのが目で判る。")
        frames = []
        for d in ANGLES:
            row = np.concatenate([np.clip(_rot(_patch(m), float(d)), 0, 1) for m in MATS],
                                 axis=1)
            rgb = np.repeat(row[..., None], 3, axis=2)
            tsv = "素材\t取り違え\n" + "\n".join(
                "%s\t%d/%d" % (m, g0["wrong"][m], len(ANGLES)) for m in MATS)
            rgb = fs.annotate_table(rgb, tsv, (6, 6), anchor="lt", font_size=11,
                                    header=True)
            rgb = fs.text_box(rgb, "%3d 度" % int(d), (rgb.shape[1] - 6, rgb.shape[0] - 6),
                              anchor="rb", font_size=13, bold=True)
            frames.append(rgb)
        figs.save_gif("texture_turning", frames, fps=4,
                      caption="3 素材を同時に回す。GLCM は角度 0 度固定なので、"
                              "回すと grass が 12 角度中 3 回「別の素材のほうが近い」と答える。")
        n = len(frames)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))

    print("\nPASS: 回しても素材を見分けられるか(実写 3 素材 x 12 角度)。"
          "GLCM の 4 方向平均は距離 1 で %d/36 -> %d/36 と効き、距離 4 では %d/36 -> %d/36 と"
          "悪化する(原因は分母 —— 素材間の差が %.4f -> %.4f に潰れる)。"
          "LBP は「回転不変」符号化でも %d/%d -> %d/%d。GIF %d コマ。 実行 %.2f 秒"
          % (w[(0.0, 0.5)], w[(0.0, 0.8)], w[(1.0, 0.5)], w[(1.0, 0.8)],
             grid[(0.0, 0.5)]["sep"], grid[(1.0, 0.5)]["sep"],
             a_lbp, l0["total"], b_lbp, l1["total"], n, time.perf_counter() - t0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
