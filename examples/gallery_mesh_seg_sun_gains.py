# -*- coding: utf-8 -*-
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 球のメッシュ・分割の分割表・太陽のブルームの円・RGB のゲインを、閉形式と手計算で確かめる(台帳 op 4 本)

平たく言うと:
  台帳のうち、族のギャラリーから漏れていた 4 本を 1 本ずつ、答えが外から分かる入力で呼ぶ。
  * ``ballworld.icosphere`` —— 正 20 面体を分割して球へ押し出したメッシュ。頂点数・面数は分割回数の閉形式、
    頂点は全部半径の上、オイラー標数 2、面は外向き、表面積は下から 4πr² に近づく。
  * ``segcompare.seg_contingency`` —— 正解ラベルと候補ラベルの分割表。手で数えた (正解, 候補) の組の数と一致、
    行和・列和・総数の恒等式、候補のラベル名を付け替えても表は変わらない。
  * ``geocam.sun_bloom_fit`` —— 飽和した太陽のブルームの縁に円を当てる。中心の分かった合成のブルームで、
    切れていない場合と画像の右端で切れた場合の両方で中心を戻す(切れると重心は内側へ偏るが、円の中心は偏らない)。
  * ``gfx2d.rgb_apply_gains`` —— R, G, B に別々のゲインを掛けて [0, 1] で切る。numpy の積と一致、
    3 番目のゲインが B に効く、0 以下のゲインは拒む。
  各行に「何を期待し、何が出て、合ったか」を印字し、外れたら exit 1。

    py -3.11 examples/gallery_mesh_seg_sun_gains.py
"""
from __future__ import annotations

import math
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import ballworld  # noqa: E402
import geocam  # noqa: E402
import gfx2d  # noqa: E402
import segcompare  # noqa: E402

ROWS: list = []


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def demo_icosphere() -> None:
    r = 0.75
    areas = []
    for s in range(4):
        V, F = ballworld.icosphere(r, s)
        nv, nf = 10 * 4 ** s + 2, 20 * 4 ** s
        edges = {tuple(sorted(e)) for f in F for e in ((f[0], f[1]), (f[1], f[2]), (f[2], f[0]))}
        euler = len(V) - len(edges) + len(F)
        rad = np.linalg.norm(V, axis=1)
        tri = V[F]
        n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
        outward = float((np.einsum("ij,ij->i", n, tri.mean(axis=1)) > 0).mean())
        areas.append(0.5 * float(np.linalg.norm(n, axis=1).sum()))
        check("icosphere", f"半径 {r}、分割 {s} 回", f"頂点 {nv}・面 {nf}・V − E + F = 2・|v| = r・全面が外向き",
              f"頂点 {len(V)}・面 {len(F)}・{euler}・|v| − r の最大 {np.abs(rad - r).max():.1e}・外向き {outward:.0%}",
              len(V) == nv and len(F) == nf and euler == 2 and np.abs(rad - r).max() < 1e-12 and outward == 1.0)
    sphere = 4 * math.pi * r * r
    ratios = [a / sphere for a in areas]
    check("icosphere", "表面積 / 4πr²(分割 0〜3 回)", "1 未満で単調に 1 へ近づく(内接多面体)、3 回で 0.99 超",
          " → ".join(f"{q:.5f}" for q in ratios),
          all(q < 1.0 for q in ratios) and all(x < y for x, y in zip(ratios, ratios[1:])) and ratios[-1] > 0.99)
    try:
        ballworld.icosphere(-1.0, 1)
        refused = False
    except ValueError:
        refused = True
    check("icosphere", "負の半径", "ValueError で拒む", "拒んだ" if refused else "通した", refused)


def demo_contingency() -> None:
    truth = np.array([[1, 1, 1, 2, 2, 2],
                      [1, 1, 1, 2, 2, 2],
                      [1, 1, 3, 3, 2, 2],
                      [4, 4, 3, 3, 3, 3],
                      [4, 4, 4, 3, 3, 3],
                      [4, 4, 4, 4, 3, 3]])
    cand = np.array([[7, 7, 7, 7, 5, 5],
                     [7, 7, 7, 7, 5, 5],
                     [7, 7, 9, 9, 5, 5],
                     [8, 8, 9, 9, 9, 9],
                     [8, 8, 8, 9, 9, 9],
                     [8, 8, 8, 8, 8, 9]])
    t = segcompare.seg_contingency(truth, cand)
    got = {(int(t["labels_a"][r]), int(t["labels_b"][c])): int(n) for r, c, n in zip(t["rows"], t["cols"], t["counts"])}
    want = dict(Counter(zip(truth.ravel().tolist(), cand.ravel().tolist())))     # 手で数えた組
    check("seg_contingency", "6×6 の正解 4 物体 × 候補 4 物体", f"(正解, 候補) の組 {len(want)} 種と個数が一致",
          f"{len(got)} 種、{sorted(got.items())}", got == want)
    rs = {int(lab): int(v) for lab, v in zip(t["labels_a"], t["row_sums"])}
    cs = {int(lab): int(v) for lab, v in zip(t["labels_b"], t["col_sums"])}
    check("seg_contingency", "行和 = 正解の物体の大きさ / 列和 = 候補の大きさ / 総数",
          "np.unique の数え / 36 = Σcounts = Σ行和 = Σ列和",
          f"{rs} / {cs} / {t['n']}, {int(np.sum(t['counts']))}",
          rs == dict(zip(*[x.tolist() for x in np.unique(truth, return_counts=True)]))
          and cs == dict(zip(*[x.tolist() for x in np.unique(cand, return_counts=True)]))
          and t["n"] == 36 == int(np.sum(t["counts"])) == sum(rs.values()) == sum(cs.values()))
    relabel = np.vectorize({5: 50, 7: 70, 8: 80, 9: 90}.get)(cand)
    t2 = segcompare.seg_contingency(truth, relabel)
    check("seg_contingency", "候補のラベル名を付け替える(5→50 など)", "数の並び(行・列・個数)は同じ",
          f"個数 {t2['counts'].tolist()}", np.array_equal(t2["counts"], t["counts"]) and np.array_equal(t2["rows"], t["rows"])
          and np.array_equal(t2["cols"], t["cols"]))


def _bloom(H, W, cu, cv, r, ramp=10.0, bg=0.35):
    """中心 (cu, cv)・半径 r の飽和円盤(値 1)と、その外へ 1 / ramp 画素の傾きで落ちる裾。0.97 の等値線は r + 0.3。"""
    v, u = np.mgrid[0:H, 0:W]
    d = np.hypot(u - cu, v - cv)
    return np.clip(np.maximum(bg, 1.0 - np.maximum(d - r, 0.0) / ramp), 0.0, 1.0)


def demo_sun() -> None:
    cu, cv, r = 61.4, 47.7, 16.0
    img = _bloom(110, 150, cu, cv, r)
    img[5:9, 110:140] = 1.0                                        # 局名の白い文字の帯(小さい飽和塊)
    f = geocam.sun_bloom_fit(img)
    err = math.hypot(f["u"] - cu, f["v"] - cv)
    check("sun_bloom_fit", f"切れていないブルーム(中心 ({cu}, {cv})・半径 {r} + 0.3)", "中心 ±0.2 px・半径 ±1 px・切れ 0",
          f"({float(f['u']):.3f}, {float(f['v']):.3f})、r {float(f['r']):.2f}、切れ {int(f['clipped'])}",
          err < 0.2 and abs(f["r"] - (r + 0.3)) < 1.0 and int(f["clipped"]) == 0)

    cu2 = 140.0                                                    # 右端(u = 149)から 9 px —— 円盤の右が切れる
    img2 = _bloom(110, 150, cu2, cv, r)
    f2 = geocam.sun_bloom_fit(img2)
    e_fit = math.hypot(f2["u"] - cu2, f2["v"] - cv)
    e_cen = math.hypot(f2["centroid_u"] - cu2, f2["centroid_v"] - cv)
    check("sun_bloom_fit", "右端で切れたブルーム(中心 u = 140、端まで 9 px)", "切れ 1・円の中心 ±0.3 px・重心は内側(左)へ偏る",
          f"切れ {int(f2['clipped'])}、円 ({float(f2['u']):.3f}, {float(f2['v']):.3f}) 誤差 {e_fit:.3f} px、"
          f"重心の u {float(f2['centroid_u']):.2f}(誤差 {e_cen:.2f} px)",
          int(f2["clipped"]) == 1 and e_fit < 0.3 and f2["centroid_u"] < cu2 - 1.0)
    try:
        geocam.sun_bloom_fit(np.full((60, 80), 0.5))
        refused = False
    except ValueError:
        refused = True
    check("sun_bloom_fit", "飽和画素の無い画像", "ValueError で拒む(太陽と決めつけない)", "拒んだ" if refused else "値を返した", refused)


def demo_gains() -> None:
    rgb = np.random.default_rng(3).random((8, 10, 3))
    g = (1.5, 0.5, 0.8)
    out = gfx2d.rgb_apply_gains(rgb, g)
    want = np.clip(rgb * np.array(g)[None, None, :], 0.0, 1.0)
    check("rgb_apply_gains", f"ゲイン (R, G, B) = {g}", "clip(rgb · g, 0, 1)", f"最大差 {np.abs(out - want).max():.1e}",
          np.abs(out - want).max() == 0.0)
    only_b = gfx2d.rgb_apply_gains(np.full((2, 2, 3), 0.5), (1.0, 1.0, 0.25))
    check("rgb_apply_gains", "B だけ 0.25 倍(3 番目のゲインが B に効く)", "(0.5, 0.5, 0.125)", f"{only_b[0, 0].tolist()}",
          np.array_equal(only_b[0, 0], [0.5, 0.5, 0.125]))
    try:
        gfx2d.rgb_apply_gains(rgb, (1.0, 0.0, 1.0))
        refused = False
    except ValueError:
        refused = True
    check("rgb_apply_gains", "ゲイン 0 を含む", "ValueError で拒む", "拒んだ" if refused else "通した", refused)


def main() -> int:
    t0 = time.time()
    demo_icosphere()
    demo_contingency()
    demo_sun()
    demo_gains()
    w_op = max(len(r[0]) for r in ROWS)
    print(f"{'op':<{w_op}} | 確かめたこと | 期待 | 出た値 | 判定")
    for op, what, exp, got, ok in ROWS:
        print(f"{op:<{w_op}} | {what} | {exp} | {got} | {'合格' if ok else '★不合格'}")
    bad = [r for r in ROWS if not r[4]]
    if bad:
        print(f"FAIL: {len(bad)}/{len(ROWS)} 行が外れた({', '.join(sorted({r[0] for r in bad}))})")
        return 1
    print(f"PASS: {len({r[0] for r in ROWS})} op を {len(ROWS)} 行の真値で確認({time.time() - t0:.1f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
