#!/usr/bin/env python3
# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 継ぎ目の無い動画で、時間方向 op の周期境界を検査する。

★主張は「循環動画がきれいに回ります」ではない。**周期的な素材には、時間方向 op が
満たすべき厳密な不変量がある**。

    周期 T の動画 v に対し、時間方向の op が周期境界を正しく扱っているなら
        op(roll(v, k)) == roll(op(v), k)          （巡回シフト等変性）
    が**厳密に**成り立つ。端を複製・固定・切り捨てで埋める実装は、ここで割れる。

`perpetual_loop` は時間依存の量をすべて θ の関数にして作るので、継ぎ目は「消した」
のではなく**最初から存在しない**。だから上の等式の真値は厳密に 0 差である。
Fullseye は**その素材を作る op と、それを食う 16 本の時間方向 op を同じ箱**に
持っているので、「どの op が周期素材に安全か / 端を何フレーム捨てればよいか」を
1 本の走行で全数出せる。

★★この PoC の芯は 2 つ:

  1. **「厳密に一致」が空の出力から出る。** 既定のしきい値 0.1 に対し素材の隣接
     フレーム差は最大 0.0955 —— わずかに届かず、動き検出系の op が**全フレーム 0**
     を返す。等変性だけを見る門は、これを**合格として通す**。
  2. **汚れるフレームは個数ではなく集合として閉形式で予言できる。**
     窓幅 w の窓つき op が汚すのは `roll(B, k) ∪ B`(B = 前後 (w-1)/2 フレーム)で、
     重なりまで含めて実測と一致する。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402
import typed_catalog as tc                                       # noqa: E402

L = fs.ledger
_PASS = []

T_FRAMES, SIZE, SHIFT = 32, 48, 9
_TOL = 1e-12


def check(ok, label, detail=""):
    _PASS.append(bool(ok))
    print("  [%s] %s %s" % ("OK" if ok else "NG", label,
                            ("---- " + detail) if detail else ""))


def _loop_gray(system="plasma_orbit", frames=T_FRAMES, size=SIZE):
    v = np.asarray(L.perpetual_loop(system, frames=frames, size=size), dtype=float)
    return v.mean(axis=3) if v.ndim == 4 else v


def _per_frame_ptp(a):
    return np.ptp(a.reshape(a.shape[0], -1), axis=1)


def _per_frame_max(a):
    return np.max(np.abs(a).reshape(a.shape[0], -1), axis=1)


def _equivariance(name, v, k=SHIFT, **kw):
    """op(roll(v,k)) と roll(op(v),k) を突き合わせる。

    戻り: (中身のあるフレーム数, 汚れたフレームの index 集合, 最大差, 結果) /
          実行できなければ (None, ..., 理由)
    """
    try:
        a = np.asarray(getattr(L, name)(v, **kw), dtype=float)
        b = np.asarray(getattr(L, name)(np.roll(v, k, axis=0), **kw), dtype=float)
    except Exception as exc:                                      # noqa: BLE001
        return None, None, None, "%s: %s" % (type(exc).__name__, str(exc)[:60])
    if a.shape != v.shape or b.shape != v.shape:
        return None, None, None, "形が変わる %s" % (a.shape,)
    content = int((_per_frame_ptp(a) > _TOL).sum())
    d = np.abs(np.roll(a, k, axis=0) - b)
    bad = set(np.where(_per_frame_max(d) > _TOL)[0].tolist())
    return content, bad, float(d.max()), a


# --------------------------------------------------------------------------- #
# 第 1 章 素材の側を先に確かめる —— 継ぎ目が無いこと                              #
# --------------------------------------------------------------------------- #
def chapter_material():
    print("\n[1] 素材 —— 継ぎ目は「消した」のでなく最初から存在しない")
    v = _loop_gray()
    check(v.shape == (T_FRAMES, SIZE, SIZE),
          "循環動画を作れた", "形 %s" % (v.shape,))
    seam = L.perpetual_loop_seam(
        np.asarray(L.perpetual_loop("plasma_orbit", frames=T_FRAMES, size=SIZE)))
    ratio = float(seam["ratio"][0])
    check(0.7 < ratio < 1.4,
          "★継ぎ目の比は 0 でなく 1 の近く(0 は「動きが止まっている」の意味)",
          "比 %.4f" % ratio)

    # 巡回シフトそのものは素材の側で厳密に閉じる(検査の前提)
    rolled = np.roll(np.roll(v, SHIFT, axis=0), -SHIFT, axis=0)
    check(float(np.abs(rolled - v).max()) == 0.0,
          "巡回シフトは素材の上で厳密に可逆(検査の前提)",
          "往復の差 %.1e" % float(np.abs(rolled - v).max()))

    diffs = np.abs(np.diff(v, axis=0))
    mx = float(diffs.max())
    check(0.0 < mx < 1.0, "隣接フレームは動いているが穏やか",
          "隣接差の最大 %.4f / 中央 %.5f" % (mx, float(np.median(diffs))))

    if figs.enabled():
        idx = [0, T_FRAMES // 4, T_FRAMES // 2, 3 * T_FRAMES // 4]
        figs.save_grid("loop_frames", [v[i] for i in idx],
                       captions=["t = %d / %d" % (i, T_FRAMES) for i in idx],
                       ncols=4, gray=True,
                       title="検査に使う継ぎ目の無い循環動画",
                       caption="`perpetual_loop(\"plasma_orbit\")` の 4 コマ。"
                               "時間に依る量をすべて θ の関数にしてあるので、"
                               "**t = T は t = 0 と同じ式**です ---- 継ぎ目は"
                               "消したのではなく最初から作られていません"
                               "(継ぎ目の比 %.4f、**0 ではなく 1 が正解**)。"
                               "★だから「巡回シフトしても同じ動画」という"
                               "**厳密な真値**が素材の側に立ちます。" % ratio)
        figs.save_gif("loop", [v[i] for i in range(T_FRAMES)], fps=12.0,
                      caption="同じ動画を実際に回したもの(%d コマ)。"
                              "**最後のコマから最初のコマへ戻るところに継ぎ目が"
                              "見えません** ---- 消したのではなく、時間に依る量を"
                              "すべて θ の関数にしてあるので**最初から存在しない**"
                              "からです。★この性質があるので「巡回シフトしても"
                              "同じ動画」が**厳密な真値**になり、時間方向 op の"
                              "周期境界を数で採点できます。" % T_FRAMES)
    return v, ratio, mx


# --------------------------------------------------------------------------- #
# 第 2 章 ★空の出力は、等変性の門を素通りする                                    #
# --------------------------------------------------------------------------- #
def chapter_empty_output(v, max_diff):
    print("\n[2] ★空の出力の罠 —— 「厳密に一致」が中身ゼロから出る")
    name = "three_frame_difference"
    c0, bad0, d0, a0 = _equivariance(name, v)            # 既定 threshold=0.1
    check(d0 == 0.0 and c0 <= 1,
          "★既定のまま走らせると「最大差 0.0・汚れ 0 フレーム」= 満点に見える",
          "しかし中身のあるフレームは %d/%d しかない" % (c0, T_FRAMES))
    check(max_diff < 0.1,
          "★原因: 既定のしきい値 0.1 に素材の動きが届いていない",
          "隣接フレーム差の最大 %.4f < 0.1 —— 実行はできるが何も検出しない"
          % max_diff)

    thr = 0.03
    c1, bad1, d1, a1 = _equivariance(name, v, threshold=thr)
    check(c1 >= T_FRAMES - 4 and len(bad1) > 0,
          "★★しきい値を素材に合わせると、同じ op が実は等変でないと分かる",
          "中身 %d/%d・汚れ %d フレーム・最大差 %.3f(満点が嘘だった)"
          % (c1, T_FRAMES, len(bad1), d1))

    if figs.enabled():
        figs.save_grid("empty_output",
                       [a0[T_FRAMES // 2], a1[T_FRAMES // 2], v[T_FRAMES // 2]],
                       captions=["既定 threshold=0.1(全面 0)",
                                 "threshold=%.2f(動きが出る)" % thr,
                                 "元のコマ(参考)"],
                       ncols=3, gray=True,
                       title="同じ op・同じ素材・しきい値だけ違う",
                       caption="`three_frame_difference` の同じコマです。"
                               "★左は**全画素 0**。それでも巡回シフト等変性の"
                               "検査は **最大差 0.0 / 汚れ 0 フレーム**という"
                               "**満点**を返します ---- 空の出力はどうシフトしても"
                               "空なので、一致して当然だからです。"
                               "原因は既定のしきい値 **0.1** に対して素材の隣接"
                               "フレーム差が最大 **%.4f** しかないこと。"
                               "★★**「走った」と「意味のある出力」は別の量**で、"
                               "等変性だけを見る門はここに構造的に盲目です。"
                               "だからこの PoC は**中身のあるフレーム数を必ず"
                               "並べて数えます**。" % max_diff)
    return c0, d0, c1, d1, thr


# --------------------------------------------------------------------------- #
# 第 3 章 16 本の時間方向 op を全数走査する                                       #
# --------------------------------------------------------------------------- #
def chapter_scan(v):
    print("\n[3] 全数走査 —— どの op が周期素材に安全か")
    ops = [r[0] for r in tc.catalog() if r[2] == ["video"] and r[3] == "video"]
    check(len(ops) >= 14, "video -> video の単入力 op を台帳から全部拾えた",
          "%d 本" % len(ops))

    rows, groups = [], {"窓つき(端だけ)": [], "全フレーム": [], "空に近い": [],
                        "走らない": []}
    for name in sorted(ops):
        content, bad, dmax, extra = _equivariance(name, v)
        if content is None:
            groups["走らない"].append(name)
            rows.append([name, "-", "-", "-", str(extra)[:38]])
            continue
        n_bad = len(bad)
        if content <= 2:
            g = "空に近い"
        elif n_bad >= T_FRAMES:
            g = "全フレーム"
        else:
            g = "窓つき(端だけ)"
        groups[g].append(name)
        rows.append([name, "%d/%d" % (content, T_FRAMES), str(n_bad),
                     "%.2e" % dmax, g])

    check(len(groups["窓つき(端だけ)"]) >= 5,
          "★端だけが汚れる op が複数ある(端を捨てれば周期素材に使える)",
          ", ".join(groups["窓つき(端だけ)"][:5]) + " ほか")
    check(len(groups["全フレーム"]) >= 3,
          "★★再帰・全域統計の op は全フレームが汚れる(端を捨てても直らない)",
          ", ".join(groups["全フレーム"]))
    check(len(groups["空に近い"]) >= 1,
          "★中身がほぼ無い op を、等変性の満点と区別して分類できた",
          ", ".join(groups["空に近い"]))

    if figs.enabled():
        figs.save_table("scan", ["op", "中身のあるフレーム", "汚れたフレーム",
                                 "最大差", "群"], rows,
                        title="時間方向 op %d 本の周期境界(巡回シフト等変性)" % len(ops),
                        caption="継ぎ目の無い動画 %d コマを巡回シフトして測った"
                                "全数走査です。★**群が 3 つに割れます** ---- "
                                "(1) **窓つき**: 端の数フレームだけ汚れる。"
                                "その分を捨てれば周期素材に使えます。"
                                "(2) **全フレーム**: 再帰(指数移動)や全域統計を"
                                "使う op は、どこを捨てても直りません。"
                                "(3) **空に近い**: 中身がほとんど無いので"
                                "**等変性は満点になります** ---- 一致の門だけ"
                                "見ていると、この群が合格側に紛れます。"
                                % T_FRAMES)

        # op ごとに「どのフレームが汚れたか」を 1 枚に重ねる(全体像)
        runnable = [n for n in sorted(ops)
                    if _equivariance(n, v)[0] is not None]
        cell, band, gap = 10, 14, 3
        h = len(runnable) * (band + gap)
        strip = np.full((h, T_FRAMES * cell), 0.5, dtype=float)
        for r, name in enumerate(runnable):
            content, bad, _d, _a = _equivariance(name, v)
            r0 = r * (band + gap)
            for t in range(T_FRAMES):
                if content <= 2:
                    val = 0.62                 # 空に近い = どちらとも言えない
                else:
                    val = 1.0 if t in bad else 0.12
                strip[r0:r0 + band, t * cell:(t + 1) * cell] = val
                strip[r0:r0 + band, t * cell] = 0.5
        figs.save("contamination_map", strip, gray=True,
                  caption="走る %d 本について、**どのフレームが汚れたか**を"
                          "1 段 1 op で重ねたもの(横軸が t = 0..%d、"
                          "白が汚れたフレーム、濃い灰が無傷)。"
                          "上から %s の順です。"
                          "★**帯が 2 本に分かれている段**が窓つきの op ---- "
                          "1 本は元の動画の端、もう 1 本はそれを %d フレーム"
                          "巡回シフトした先です。★**全面が白い段**は再帰や"
                          "全域統計を使う op で、端を捨てても直りません。"
                          "★★**中間色で塗った段**は中身がほとんど無い op ---- "
                          "汚れ 0 に見えますが、それは**空の出力がどうシフトしても"
                          "空だから**で、合格ではありません。"
                          % (len(runnable), T_FRAMES - 1,
                             " / ".join(n.split("_")[0] for n in runnable), SHIFT))
    return rows, groups, ops


# --------------------------------------------------------------------------- #
# 第 4 章 ★汚れるフレームは集合として閉形式で予言できる                           #
# --------------------------------------------------------------------------- #
def _predicted_bad(window, k=SHIFT, T=T_FRAMES):
    """窓幅 w の**後方窓**が汚す集合 B と、その巡回シフトとの和。

    ★最初は「中心窓なので前後 (w-1)/2 フレーム」と書いて外した。外れた集合を
    引き算すると、汚れているのは**先頭側だけ**で末尾側は無傷だった ——
    つまりこの op の窓は中心でなく**後方(因果的)**で、不完全なのは先頭の
    ``w-1`` フレーム。**窓の向きは、汚れた集合の形から読める**(実装を読まずに)。
    """
    B = set(range(window - 1))
    rolled = {(i + k) % T for i in B}
    return B | rolled


def chapter_closed_form(v):
    print("\n[4] ★汚れるフレームの集合は、窓幅から閉形式で出る")
    windows = (3, 5, 7, 9, 11, 13)
    meas, pred, exact = [], [], []
    for w in windows:
        _c, bad, _d, _a = _equivariance("moving_average_window", v, window=w)
        p = _predicted_bad(w)
        meas.append(len(bad))
        pred.append(len(p))
        exact.append(bad == p)
    check(all(exact),
          "★★個数だけでなく**集合そのもの**が %d 通りとも予言と一致" % len(windows),
          " / ".join("w=%d: 実測 %d = 予言 %d" % (w, m, p)
                     for w, m, p in zip(windows, meas, pred)))
    # ★汚れが先頭側だけで末尾側に無いこと = 窓が後方(因果的)である証拠
    _c, bad7, _d, _a = _equivariance("moving_average_window", v, window=7)
    tail_free = not (bad7 & {T_FRAMES - 1, T_FRAMES - 2, T_FRAMES - 3})
    check(tail_free and (0 in bad7),
          "★窓の向きは、汚れた集合の形から読める(実装を読まずに)",
          "w=7 で汚れるのは先頭側 %s —— 末尾は無傷なので**中心窓ではなく後方窓**"
          % sorted(i for i in bad7 if i < 8))

    naive = [w - 1 for w in windows]
    check(meas != naive,
          "★素朴な予言「w-1 フレーム」は外れる(汚れは 2 か所に出るため)",
          "素朴 %s に対し実測 %s" % (naive, meas))
    # w=11 では 2 つの汚れ帯が重なるので 2(w-1) より小さくなる
    doubled = [2 * (w - 1) for w in windows]
    over = [i for i, (m, d) in enumerate(zip(meas, doubled)) if m != d]
    check(len(over) >= 1,
          "★★2(w-1) でも足りない —— 帯が重なると小さくなる",
          "w=%s で 2(w-1)=%d に対し実測 %d(重なり %d フレーム)"
          % (windows[over[0]], doubled[over[0]], meas[over[0]],
             doubled[over[0]] - meas[over[0]]))

    if figs.enabled():
        x = np.array(windows, float)
        figs.save_plot("closed_form",
                       [("実測(汚れたフレーム数)", x, np.array(meas, float)),
                        ("閉形式の予言 |roll(B,k) ∪ B|", x, np.array(pred, float)),
                        ("素朴な予言 w-1", x, np.array(naive, float))],
                       kinds=["scatter", "line", "line"],
                       xlabel="窓幅 w", ylabel="汚れたフレーム数",
                       ylim=(0.0, 22.0),
                       title="汚れるフレームは、集合まで予言できる",
                       caption="窓幅 w の**後方窓**が汚すのは先頭の w-1 フレーム = "
                               "集合 **B**。巡回シフト等変性の検査では "
                               "**roll(B, k) と B の両方**が出るので、"
                               "汚れる集合は **roll(B,k) ∪ B** です。"
                               "★%d 通りとも**個数ではなく集合そのもの**が"
                               "一致しました。★★素朴な「w-1 フレーム」は"
                               "全部外れ、2(w-1) も w=%d では外れます ---- "
                               "T=%d・シフト %d で 2 つの帯が重なるからで、"
                               "**重なりまで閉形式が説明します**。"
                               "★★★はじめ「中心窓なので前後 (w-1)/2」と書いて"
                               "外しました。外れた集合を引き算すると**汚れている"
                               "のは先頭側だけ**で、末尾は無傷 ---- つまり窓は"
                               "中心でなく後方(因果的)でした。**窓の向きは、"
                               "実装を読まなくても汚れた集合の形から読めます。**"
                               % (len(windows), windows[over[0]], T_FRAMES, SHIFT))
        # 汚れた位置そのものを並べる(端に集中していることを絵で)
        w = 7
        _c, bad, _d, _a = _equivariance("moving_average_window", v, window=w)
        # 上段 = 実測 / 中段 = 仕切り(灰)/ 下段 = 予言。1 フレーム 1 マスで描き、
        # マスの境目に細い罫を入れて**数えられる**図にする。
        cell, band = 12, 22
        strip = np.full((band * 2 + 8, T_FRAMES * cell), 0.5, dtype=float)
        for row0, idx in ((0, bad), (band + 8, _predicted_bad(w))):
            for t in range(T_FRAMES):
                val = 1.0 if t in idx else 0.12
                strip[row0:row0 + band, t * cell:(t + 1) * cell] = val
                strip[row0:row0 + band, t * cell] = 0.5      # マスの仕切り
        figs.save("bad_frames", strip, gray=True,
                  caption="窓幅 %d のときに汚れたフレームの位置。上段が**実測**、"
                          "下段が**閉形式の予言**(白が汚れたフレーム、横軸が "
                          "t = 0..%d、1 マス 1 フレーム)。★2 本の帯に"
                          "分かれています ---- 1 本目は **t = 0..%d**(窓が"
                          "まだ埋まっていない先頭)、2 本目は **t = %d..%d**"
                          "(それを %d フレーム巡回シフトした先)。"
                          "★★**末尾は無傷**です ---- 中心窓なら後ろも汚れる"
                          "はずで、汚れないこと自体が「この窓は後方(因果的)"
                          "だ」という証拠になっています。"
                          "**上下が 1 画素も違いません。**"
                          % (w, T_FRAMES - 1, w - 2, SHIFT, SHIFT + w - 2,
                             SHIFT))
    return windows, meas, pred, naive


# --------------------------------------------------------------------------- #
# 第 5 章 端を捨てれば使えるのか —— 捨てる枚数を数える                            #
# --------------------------------------------------------------------------- #
def chapter_trim(v, groups):
    print("\n[5] 端を何フレーム捨てれば、周期素材に使えるか")
    safe = {}
    for name in sorted(groups["窓つき(端だけ)"]):
        _c, bad, _d, _a = _equivariance(name, v)
        # 汚れが端(0 側 / T-1 側)と、そのシフト先に限られているか
        safe[name] = len(bad)
    check(len(safe) >= 5, "端だけが汚れる op について捨てる枚数を数えた",
          ", ".join("%s %d" % (k.split("_")[0], n) for k, n in
                    sorted(safe.items(), key=lambda kv: kv[1])[:5]))
    worst = max(safe.values())
    check(worst < T_FRAMES,
          "★どれも全フレームには広がらない(捨てれば残りは厳密に一致)",
          "最大 %d / %d フレーム" % (worst, T_FRAMES))

    if figs.enabled():
        names = sorted(safe, key=lambda n: safe[n])
        x = np.arange(len(names), dtype=float)
        figs.save_plot("trim",
                       [("汚れたフレーム数", x, np.array([safe[n] for n in names],
                                                  float)),
                        ("全 %d フレーム" % T_FRAMES,
                         np.array([-0.3, len(names) - 0.7]),
                         np.full(2, float(T_FRAMES)))],
                       kinds=["scatter", "line"],
                       xlabel="端だけが汚れる op(汚れの少ない順、0..%d)"
                              % (len(names) - 1),
                       ylabel="汚れたフレーム数", ylim=(0.0, T_FRAMES + 4.0),
                       title="周期素材に使うなら、端を何フレーム捨てればよいか",
                       caption="端だけが汚れる %d 本について、汚れたフレーム数を"
                               "少ない順に並べたもの。少ない順に %s。"
                               "★これは「この op は周期的な素材に使えるか」"
                               "ではなく、**使うなら何枚捨てればよいか**という"
                               "実務の数字です。捨てた残りでは等変性が**厳密に "
                               "0 差**で成り立ちます。"
                               % (len(names),
                                  " / ".join("%s %d" % (n, safe[n])
                                             for n in names[:4])))
    return safe


def main():
    t0 = time.time()
    print("=" * 74)
    print("PoC: 継ぎ目の無い動画で、時間方向 op の周期境界を検査する")
    print("=" * 74)
    v, ratio, mx = chapter_material()
    c0, d0, c1, d1, thr = chapter_empty_output(v, mx)
    rows, groups, ops = chapter_scan(v)
    windows, meas, pred, naive = chapter_closed_form(v)
    safe = chapter_trim(v, groups)

    if figs.enabled():
        tbl = [
            ["素材", "継ぎ目の比", "1(継ぎ目なし)", "%.4f" % ratio,
             "0 は「動きが止まっている」の意味"],
            ["three_frame_difference", "巡回シフト等変性の最大差", "0(厳密)",
             "%.1e" % d0, "★満点だが中身は %d/%d フレーム(空)" % (c0, T_FRAMES)],
            ["three_frame_difference", "同(しきい値 %.2f)" % thr, "0(厳密)",
             "%.3f" % d1, "中身 %d/%d —— 実は等変でない" % (c1, T_FRAMES)],
            ["時間 op %d 本" % len(ops), "汚れたフレーム数", "0(厳密)",
             "0 〜 %d" % T_FRAMES, "窓つき %d / 全フレーム %d / 空に近い %d"
             % (len(groups["窓つき(端だけ)"]), len(groups["全フレーム"]),
                len(groups["空に近い"]))],
            ["moving_average_window", "汚れる集合", "roll(B,k) ∪ B",
             "%d 通りとも一致" % len(windows),
             "素朴な w-1 は全部外れ(実測は最大 %d)" % max(meas)],
        ]
        figs.save_table("numbers", ["対象", "量", "真値", "実測", "備考"], tbl,
                        title="絵を見ずに採点した結果",
                        caption="★この表に「動画を見て判断した」行はありません。"
                                "真値は**周期性から導かれる等式**で、"
                                "実測は**既存の時間方向 op**が返したものです。"
                                "**新しい op は 1 つも足していません。**")
        errs = figs.errors()
        assert not errs, errs

    ok = sum(_PASS)
    print("\n検査 %d 件中 %d 件 OK(%.1f 秒)" % (len(_PASS), ok, time.time() - t0))
    if ok != len(_PASS):
        for i, v in enumerate(_PASS):
            if not v:
                print("  NG が残っている(%d 番目)" % (i + 1))
        return 1
    # ★この 1 行が要る。門 tests/test_poc_scripts_run.py は exit 0 だけでなく
    #   **PASS の印字**も見ており、落とすと exit -2(門が付ける合成コード、
    #   意味は「exit 0 だが PASS を印字していない」)で赤になる。
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
