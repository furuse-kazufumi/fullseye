# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""voxel_labels_color — ボクセルのラベル色分け(volcolor)op を、産業 CT の粒子計測の
筋で一巡し、**「切ってから色を付ける」と「色を付けてから切る」の差**を数値に出す。

    py -3.11 examples/voxel_labels_color.py

【この例が解く問題】
CT ボリュームの中の粒子(あるいは気孔・介在物)を数えて測り、**目で追えるように
色分けする**。fullseye には既に `volops.vol_label`(3-D 連結成分)と
`volops.vol_region_props`(成分ごとの定量値)があったが、**色を付ける手段が 2-D の
`imgio.colorize_labels` しか無かった**。ボリュームを見るには 1 枚ずつ切ってから色を
付けるしかなく、その順序ではスライスごとにラベル番号が振り直されるので、
**同じ粒子が層ごとに別の色になる**。

(1) ★色の安定性: 同じ 2 値ボリュームに (A) スライスごとに色付け (B) ボリュームで
    色付けしてから切る、の 2 通りを掛け、色が変わった (成分, 断面) を数える。
    **この族の存在理由がそのまま測定量になっている。**
(2) 2-D との配色一致: 同じラベル番号・同じ seed なら 2-D の 1 枚でも 3-D でも
    色が一致することを `np.array_equal` で確かめる(番号に欠番があっても)。
(3) connectivity 6 / 18 / 26: 角だけで触れる 2 塊が 26 連結で 1 つに融合する。
(4) ★異方 spacing: z だけ 3 倍粗い格子で、spacing を渡し忘れると体積が 67 %
    狂い、**球が「板」に見える**(形状指標が逆の結論を出す)。
(5) 選別: 体積・伸長度・端接触で粒子をふるいにかける。**残った粒子の色は
    動かない**(番号を振り直さないから)。
(6) 重ね合わせ: 元のグレーボリュームに α で色を重ねる(fill / boundary)。
(7) 凡例: どの色がどの粒子で、体積が幾つか。**色だけの図を作らない。**
(8) 3-D: 成分ごとの色付きメッシュと、numpy だけの合成投影。
    チャネル別 MIP が**どの粒子の色でもない色**を作ることを数える。
(9) 性能: 1 ボクセル 1 ラベルの病的入力で二次爆発しないこと。
(10) fail-closed: 2-D / float ラベル / 負ラベル / ラベル値の爆発 / 0..255 の
    色ボリューム / チャネル別 max を拒否すること。

【グラウンドトゥルース(数値で嘘を弾く)】
1. 既知半径の球 N 個 —— 成分数は厳密一致、重心は完全一致、体積誤差はボクセル化
   だけに由来する(半径 4 で 1.6 %、半径 6 で 1.2 %)。
2. パレットは `imgio.colorize_labels` と同じ乱数列 —— バイト単位で一致。
3. ボリュームで色を付けた側のちらつきは**構造上 0**(番号が全体で一意だから)。
4. 異方 spacing の体積比は spacing の積そのもの(3.0 倍、厳密)。
5. `vol_label_shape_stats` の 5 キーは `volops.vol_region_props` と厳密一致。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import imgio                                                     # noqa: E402
import volcolor as VC                                            # noqa: E402
import volops                                                    # noqa: E402

SEED = 0


def particle_volume(shape=(24, 48, 48)):
    """16 個の粒子(球)を格子状に置いた決定的な合成 CT ボリューム。"""
    D, H, W = shape
    z, y, x = np.indices(shape).astype(np.float64)
    vol = np.zeros(shape)
    for gy in range(4):
        for gx in range(4):
            k = gy * 4 + gx
            cy, cx = 6.0 + gy * 12.0, 6.0 + gx * 12.0
            cz = 5.0 + (k % 4) * 4.5
            r = 2.0 + (k % 5) * 0.7
            vol[((z - cz) ** 2 + (y - cy) ** 2 + (x - cx) ** 2) <= r * r] = 1.0
    return vol


def main():                                             # noqa: C901 - 一本道の実演
    ok = True
    binary = particle_volume()
    labels, n = volops.vol_label(binary, connectivity=26)

    # ------------------------------------------------------------------ #
    # 1) ★色の安定性 —— この族の存在理由                                  #
    # ------------------------------------------------------------------ #
    f = VC.vol_label_color_flicker(binary, axis="z", seed=SEED)
    print("1) 色の安定性(16 粒子・(24,48,48)・connectivity=26):")
    print(f"   A スライスごとに色付け : {f['slices_with_change']} / {f['n_slices']} 断面で"
          f"色が変わり、(成分,断面) の変化 {f['changed_pairs']} / {f['pairs_checked']} 件"
          f"({f['flicker_rate'] * 100:.1f} %)、{f['changed_components']} / "
          f"{f['n_components']} 成分が一度は変わる")
    print(f"   B ボリュームで色付け   : {f['volume_slices_with_change']} 断面 / "
          f"{f['volume_changed_pairs']} 件 / {f['volume_changed_components']} 成分"
          f"  ← **構造上 0**(番号がボリューム全体で一意だから)")
    assert f["volume_changed_pairs"] == 0
    assert f["changed_pairs"] > 0

    rgbvol = VC.vol_colorize_labels(labels, seed=SEED)
    for i in range(1, n + 1):
        assert np.unique(rgbvol[labels == i], axis=0).shape[0] == 1
    print(f"   → {n} 成分すべてが、全断面を通じて 1 色のまま")

    # ------------------------------------------------------------------ #
    # 2) 2-D との配色一致                                                 #
    # ------------------------------------------------------------------ #
    same_vol = np.array_equal(rgbvol, imgio.colorize_labels(labels, seed=SEED))
    same_sl = all(np.array_equal(imgio.colorize_labels(labels[z], seed=SEED), rgbvol[z])
                  for z in range(labels.shape[0]))
    gap = np.zeros((8, 8, 8), np.int64)
    gap[1:3, 1:3, 1:3] = 3
    gap[5:7, 5:7, 5:7] = 9                              # 欠番あり(max=9, 成分=2)
    img2d = np.zeros((8, 8), np.int64)
    img2d[1:3, 1:3] = 3
    same_gap = np.array_equal(imgio.colorize_labels(img2d, seed=SEED)[1, 1],
                              VC.vol_colorize_labels(gap, seed=SEED)[1, 1, 1])
    print("\n2) 2-D `imgio.colorize_labels` との配色一致:")
    print(f"   ボリューム全体で一致        : {same_vol}")
    print(f"   全 24 断面それぞれで一致    : {same_sl}")
    print(f"   欠番のある番号(3 と 9)でも : {same_gap}"
          f"   (成分数 {len(VC.vol_label_legend(gap))} 件、max は {int(gap.max())})")
    ok &= same_vol and same_sl and same_gap

    pal_dist = {}
    for nc in (16, 64, 256):
        p = VC.vol_label_palette(nc, seed=SEED)[1:]
        d = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=2)
        np.fill_diagonal(d, np.inf)
        pal_dist[nc] = float(d.min())
    print("   ただし**色は識別子ではない**: 最近接色対の距離 = "
          + " / ".join("%d 色 %.4f" % (k, v) for k, v in pal_dist.items())
          + "(最大 1.732)。どれがどれかは凡例で読む ―― 下の (7)")

    # ------------------------------------------------------------------ #
    # 3) connectivity 6 / 18 / 26                                        #
    # ------------------------------------------------------------------ #
    corner = np.zeros((9, 9, 9))
    corner[2:5, 2:5, 2:5] = 1.0
    corner[5:8, 5:8, 5:8] = 1.0                         # 角 1 点で接する
    edge = np.zeros((9, 9, 9))
    edge[2:5, 2:5, 2:5] = 1.0
    edge[5:8, 5:8, 2:5] = 1.0                           # 稜線で接する
    print("\n3) connectivity(成分数 / 色数):")
    for tag, v in (("角で接する 2 塊", corner), ("稜線で接する 2 塊", edge),
                   ("離れた 16 粒子", binary)):
        row = []
        for c in (6, 18, 26):
            lab, k = volops.vol_label(v, connectivity=c)
            cols = np.unique(VC.vol_colorize_labels(lab, seed=SEED)[lab > 0], axis=0)
            row.append("%d 連結 = %d 成分 / %d 色" % (c, k, cols.shape[0]))
        print("   %-18s %s" % (tag, "  ".join(row)))
    assert [volops.vol_label(corner, connectivity=c)[1] for c in (6, 18, 26)] == [2, 2, 1]
    assert [volops.vol_label(edge, connectivity=c)[1] for c in (6, 18, 26)] == [2, 1, 1]

    # ------------------------------------------------------------------ #
    # 4) ★異方 spacing                                                    #
    # ------------------------------------------------------------------ #
    sp = (3.0, 1.0, 1.0)
    S = np.zeros((17, 33, 33))
    z, y, x = np.indices(S.shape).astype(np.float64)
    S[(((z - 8) * sp[0]) ** 2 + ((y - 16) * sp[1]) ** 2
       + ((x - 16) * sp[2]) ** 2) <= 6.0 ** 2] = 1.0
    SL, _ = volops.vol_label(S, connectivity=26)
    a = VC.vol_label_shape_stats(SL)[0]
    b = VC.vol_label_shape_stats(SL, spacing=sp)[0]
    truth = 4.0 / 3.0 * np.pi * 6.0 ** 3
    print("\n4) 異方 spacing(半径 6 mm の球を z だけ 3 mm 刻みの格子で標本化):")
    print(f"   真値(閉形式)          {truth:9.2f} mm**3")
    print(f"   spacing あり            {b['volume']:9.2f} mm**3  "
          f"誤差 {100 * (b['volume'] - truth) / truth:+6.2f} %   "
          f"isotropy {b['isotropy']:.4f}(ほぼ等方 = 正しい)")
    print(f"   spacing なし            {a['volume']:9.2f}        "
          f"mm**3 と読むと {100 * (a['volume'] - truth) / truth:+6.2f} %   "
          f"isotropy {a['isotropy']:.4f}(**球が板に見える**)")
    print(f"   等価直径 {b['equivalent_diameter']:.3f} mm vs "
          f"{a['equivalent_diameter']:.3f}(1.44 倍のずれ)")
    assert abs(b["volume"] / a["volume"] - 3.0) < 1e-12         # 比は spacing の積
    assert b["isotropy"] > 0.7 > 0.1 > a["isotropy"]

    props = volops.vol_region_props(labels)
    stats = VC.vol_label_shape_stats(labels)
    exact = all(p["label"] == s["label"] and p["voxel_count"] == s["voxel_count"]
                and p["bbox"] == s["bbox"]
                and abs(p["volume"] - s["volume"]) < 1e-12
                and max(abs(u - v) for u, v in zip(p["centroid"], s["centroid"])) < 1e-12
                for p, s in zip(props, stats))
    print(f"   `vol_region_props` との共通 5 キーは厳密一致: {exact}")
    ok &= exact

    # ------------------------------------------------------------------ #
    # 5) 選別 —— ふるいにかけても色は動かない                              #
    # ------------------------------------------------------------------ #
    counts = sorted(s["voxel_count"] for s in stats)
    thr = counts[8]
    keep, kept = VC.vol_select_labels(labels, stats, min_voxels=thr)
    rel, relids = VC.vol_select_labels(labels, stats, min_voxels=thr, relabel=True)
    m = keep > 0
    stable = np.array_equal(rgbvol[m], VC.vol_colorize_labels(keep, seed=SEED)[m])
    broken = np.array_equal(rgbvol[m], VC.vol_colorize_labels(rel, seed=SEED)[m])
    print(f"\n5) 選別(voxel_count >= {thr}):{len(kept)} / {n} 粒子が残る")
    print(f"   relabel=False(既定)残った粒子の色は 1 ボクセルも動かない : {stable}")
    print(f"   relabel=True        番号を 1..{len(relids)} へ振り直す → 色は総取り替え"
          f" : {not broken}")
    ok &= stable and not broken

    v = np.zeros((20, 20, 20))
    zz, yy, xx = np.indices(v.shape).astype(np.float64)
    v[((zz - 5) ** 2 + (yy - 5) ** 2 + (xx - 5) ** 2) <= 16.0] = 1.0     # 球
    v[13:16, 12:15, 2:18] = 1.0                                          # 棒
    RL, _ = volops.vol_label(v, connectivity=26)
    rs = VC.vol_label_shape_stats(RL)
    _out, round_only = VC.vol_select_labels(RL, rs, max_elongation=2.0)
    print("   形状でも分けられる: elongation = "
          + " / ".join("label %d: %.2f" % (r["label"], r["elongation"]) for r in rs)
          + f" → max_elongation=2.0 で残るのは label "
          + ", ".join(str(int(i)) for i in round_only) + "(球のほう)")
    assert len(round_only) == 1

    try:
        VC.vol_select_labels(RL, rs, min_sphericity=0.5)
        print("   [FAIL] props に無いキーの条件が黙って通った")
        ok = False
    except ValueError as exc:
        print(f"   props に無い条件は拒否: {str(exc).split('.')[0][:88]}")

    # ------------------------------------------------------------------ #
    # 6) 重ね合わせ                                                       #
    # ------------------------------------------------------------------ #
    rng = np.random.default_rng(3)
    grey = np.clip(0.25 + 0.15 * rng.standard_normal(binary.shape) + 0.35 * binary, 0, 1)
    base = VC.vol_label_overlay(grey, labels, seed=SEED, alpha=0.0)
    fg = labels > 0
    print("\n6) 重ね合わせ(元のグレーボリューム + 色ラベル):")
    for al in (0.0, 0.25, 0.5, 0.75, 1.0):
        o = VC.vol_label_overlay(grey, labels, seed=SEED, alpha=al)
        print(f"   alpha={al:.2f}  前景の平均変化 {np.abs(o[fg] - base[fg]).mean():.4f}"
              f"   背景の平均変化 {np.abs(o[~fg] - base[~fg]).mean():.4f}")
        assert np.abs(o[~fg] - base[~fg]).max() == 0.0
    shell = VC.vol_label_overlay(grey, labels, alpha=1.0, mode="boundary")
    fill = VC.vol_label_overlay(grey, labels, alpha=1.0, mode="fill")
    n_shell = int((shell != base).any(axis=3).sum())
    n_fill = int((fill != base).any(axis=3).sum())
    print(f"   mode='boundary' は殻だけ塗る: {n_shell} / {n_fill} ボクセル"
          f"({100 * n_shell / n_fill:.1f} %)= 下の構造が見える")

    # ------------------------------------------------------------------ #
    # 7) 凡例 —— 色だけの図を作らない                                     #
    # ------------------------------------------------------------------ #
    spacing = (0.5, 0.2, 0.2)
    legend = VC.vol_label_legend(labels, seed=SEED, spacing=spacing, measure="volume")
    print(f"\n7) 凡例(spacing={spacing} mm、体積の降順):")
    print("   順位 ラベル  色        体積 mm**3   全体比")
    for r in legend[:6]:
        print(f"   {r['rank']:>2}   {r['label']:>4}   {r['hex']}  "
              f"{r['value']:>9.4f}   {r['share'] * 100:5.1f} %")
    print(f"   ... 全 {len(legend)} 件、比率の合計 {sum(r['share'] for r in legend):.6f}")
    pal = VC.vol_label_palette(int(labels.max()), seed=SEED)
    assert all(np.allclose(r["rgb"], pal[r["label"]]) for r in legend)

    # ------------------------------------------------------------------ #
    # 8) 3-D 表示と合成投影                                               #
    # ------------------------------------------------------------------ #
    meshes = VC.vol_labels_to_meshes(labels, seed=SEED, spacing=spacing)
    tri = sum(int(md["faces"].shape[0]) for md in meshes)
    print(f"\n8) 色付きメッシュ: {len(meshes)} 個 / 三角形 {tri} 枚"
          f"(頂点は render3d の (x,y,z) 順、mm)")
    print("   断面図と 3-D で同じ粒子が同じ色: "
          + str(all(np.allclose(md["color"], pal[md["label"]]) for md in meshes)))

    slab = np.zeros((16, 16, 16))
    slab[0:6, 2:12, 2:12] = 1.0
    slab[7:11, 4:14, 4:14] = 1.0
    slab[12:16, 1:11, 6:16] = 1.0
    SB, _ = volops.vol_label(slab, connectivity=26)
    sb_pal = VC.vol_label_palette(int(SB.max()), seed=SEED)
    mip = VC.vol_colorize_labels(SB, seed=SEED).max(axis=0)      # 禁じ手
    front = VC.vol_label_volume_render(SB, "z", "front", seed=SEED)
    covered = (SB > 0).any(axis=0)

    def invented(img, mask):
        flat = img[mask].reshape(-1, 3)
        ok_ = np.zeros(len(flat), bool)
        for c in sb_pal:
            ok_ |= np.all(np.isclose(flat, c), axis=1)
        return int(len(flat)), int((~ok_).sum())

    n_fg, bad = invented(mip, covered)
    n_all, bad_front = invented(front, np.ones_like(covered))
    print(f"   合成投影(z 方向に重なる 3 枚の板):")
    print(f"     チャネル別 max(MIP)  前景 {n_fg} 画素のうち **{bad} 画素**が"
          f"どの成分の色でもない色")
    print(f"     mode='front'          {n_all} 画素すべてがパレットの色"
          f"(捏造 {bad_front})")
    try:
        VC.vol_label_volume_render(SB, mode="max")
        print("   [FAIL] mode='max' が通った")
        ok = False
    except ValueError:
        print("     → だから `mode=\"max\"` は拒否する(黙って混ぜない)")
    ok &= bad > 0 and bad_front == 0

    # ------------------------------------------------------------------ #
    # 9) 性能 —— 病的入力で二次爆発しないこと                              #
    # ------------------------------------------------------------------ #
    print("\n9) 1 ボクセル 1 ラベル(病的入力)の時間:")
    prev = None
    for side in (16, 32, 64):
        cb = np.zeros((side,) * 3)
        cb[::2, ::2, ::2] = 1.0
        lab, k = volops.vol_label(cb, connectivity=26)
        t = time.perf_counter()
        VC.vol_label_shape_stats(lab)
        dt = time.perf_counter() - t
        t = time.perf_counter()
        VC.vol_colorize_labels(lab)
        dc = time.perf_counter() - t
        grow = "" if prev is None else "  (前段の %.1f 倍 / 二次なら 64 倍)" % (dt / prev)
        print(f"   {side:>3}**3 = {cb.size:>7} ボクセル / {k:>6} 成分  "
              f"stats {dt:.4f} s  colorize {dc:.4f} s{grow}")
        prev = dt

    # ------------------------------------------------------------------ #
    # 10) fail-closed                                                     #
    # ------------------------------------------------------------------ #
    print("\n10) fail-closed(黙って通さないもの):")
    bad_inputs = [
        ("2-D のラベル画像", lambda: VC.vol_colorize_labels(np.zeros((4, 4), np.int64))),
        ("float のラベル", lambda: VC.vol_colorize_labels(np.zeros((4, 4, 4)))),
        ("負のラベル", lambda: VC.vol_colorize_labels(-np.ones((4, 4, 4), np.int64))),
        ("ラベル値の爆発(実在 2 成分・番号 10**9)",
         lambda: VC.vol_colorize_labels(np.array([[[0, 10 ** 9]]], np.int64))),
        ("0..255 の色ボリューム", lambda: VC.vol_label_slice_rgb(
            np.full((3, 3, 3, 3), 200.0), 0)),
        ("負の断面番号", lambda: VC.vol_label_slice_rgb(np.zeros((3, 3, 3, 3)), -1)),
        ("チャネル別 max", lambda: VC.vol_label_volume_render(
            np.zeros((4, 4, 4), np.int64), mode="max")),
        ("巨大 shape(300**3)", lambda: VC.vol_colorize_labels(
            np.lib.stride_tricks.as_strided(np.zeros(1, np.int64),
                                            (300, 300, 300), (0, 0, 0)))),
        ("軸順の綴り間違い", lambda: VC.vol_labels_to_meshes(labels, axes="yxz")),
    ]
    refused = 0
    for tag, call in bad_inputs:
        try:
            call()
            print(f"   [FAIL] {tag} が通った")
            ok = False
        except ValueError as exc:
            refused += 1
            print(f"   拒否 {tag}: {str(exc).split(' — ')[0].split('.')[0][:74]}")
    ok &= refused == len(bad_inputs)

    print("\n" + ("PASS: volcolor 11 op が閉形式のグラウンドトゥルースと一致し、"
                  "ボリュームで色を付けた側のちらつきは 0 だった"
                  if ok else "FAIL: 上の [FAIL] を見よ"))
    return ok


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
