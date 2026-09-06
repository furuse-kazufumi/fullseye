# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""poc_timelapse_growth — 成長のタイムラプスを**時空間の連結成分**として測る。

    py -3.11 examples/poc_timelapse_growth.py

【この PoC が答える問い】
微生物のコロニー・腐食斑・結晶・火事の焼失域 —— どれも「丸いものが広がって
やがて隣とくっつく」動画になる。問いは 2 つ:「**成長則の定数はいくつか**」と
「**いつ合体したか**」。1 枚ずつ数える(フレームを独立に見る)のが素朴な
やり方で、``(t, y, x)`` を 1 つの体積とみなして 3-D の連結成分を取るのが
本題。合体したコロニーは時空間では **Y 字**になるので、体積の形から
「どれとどれが同じ家族か」が読める。

【★★ 番号つき所見(すべて実測。予想が外れたものはそう書く)】

  1. ★ゼロ点(フレーム独立の計数)は**思ったより強い**。塊の数が減る
     フレームは真の合体時刻の 1 コマ以内に出た。ゼロ点が壊れるのは
     数の検出ではなく**その先** ——「どれとどれが」「合体か消失か」
     「同時に 2 組か」。時空間の連結成分はこの 3 つを**形として**持つ。

  2. ★★**空間の離散化は合体を「早める」**(予想が外れた。「画素中心が
     円に入るまで前景にならないので観測は必ず遅れる」と思っていた)。
     画素は面積を持つので円は半画素ぶん太り、**まだ接していないのに**
     隣り合う画素中心が両方の内側に入って 4 近傍で繋がる。連続時間で
     測った合体時刻は真値より組 0-1 で -1.16、組 2-3 で -0.04 フレーム。
     一方フレーム格子への丸めは**必ず遅らせる**(+0.17 / +0.94)。
     **逆向きの 2 つ**なので、合計だけ見ると打ち消して小さく見える。

  3. ★★**「時間の標本化が空間の分解能より先に効く」は成り立たなかった**
     (これも予想が外れた)。4 倍粗くしたときの誤差は
     組 0-1 で 時間 1.17 / 空間 3.39 フレーム、
     組 2-3 で 時間 1.94 / 空間 6.24 フレーム。**どちらも空間が勝つ**。
     接触の直前は半径が 1/sqrt(t) でしか伸びないので、1 画素の長さ誤差が
     「長さ ÷ 縁の速さ」で 1.3〜1.9 フレームに化ける。しかも時間軸の
     誤差は「上限が stride」で頭打ちになるのに、空間軸には頭打ちが無い。

  4. ★★空間の粗さは**偏りよりばらつきで効く**。画素 4 倍で偏り
     -2.11 フレームに対し、**画素格子の位相を変えるだけで 2.56 フレーム**
     **の幅**(組 2-3 では偏り -3.41 に対し幅 5.66)。同じ倍率で撮り直しても
     カメラが 1 画素ずれれば答えが変わる。偏りだけを報告すると
     「粗くしても平気」と誤読する。

  5. ★★**`vol_label` の既定 26 近傍はニアミスを合体させた**。接近方向を
     45 度に置いた 2 個(最終フレームでも 0.92 長さ単位の隙間)を、
     6 近傍は別家族のままにしたが 18 / 26 は同じ家族にした。
     斜めの近傍は sqrt(2) 画素まで届くため。**既定が寛容側**なので、
     何も指定せずに呼ぶと偽の合体を拾う。

  6. ★成長定数 k は**合体前のフレームだけ**なら誤差 3 % 以内、合体後を
     混ぜると 19〜44 % 外れる。**どこで切るかを教えるのが時空間のラベル**
     —— これが「体積として扱う」いちばん実用的な効き目。

  7. `vol_region_props` が返す家族ごとの voxel 数(= Σ_t 面積)は、
     孤立した管なら閉形式 pi k² Σ(t + t0) と 0.2 % 以内で合う。
     **体積そのものが成長則の検算になる。**

(この docstring の数字は最終実行の実測値。書いてから測ったのではなく、
 測ってから書いている。)

【グラウンドトゥルース】
半径は拡散律速の解析式 ``r_i(t) = k_i sqrt(t + t0)``。中心間距離 ``d`` の
2 つが接する時刻は ``t = (d / (k_i + k_j))² - t0`` で**閉形式**。二値像は
「画素中心が円の内側か」だけで決まるので、真値は連続円・観測は標本化された
円、という関係が厳密に保たれる。

【90 秒制限】200x200 px・48 フレーム・掃引は 4x4 まで(実測は下に出る)。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N = 200                 # 視野の一辺 [長さ単位]。画素サイズ 1 なら 200 px
T = 48                  # フレーム数
T0 = 4.0                # 成長則の時間オフセット(t=0 でも半径 k*2 を持つ)

#: コロニー: ``(行, 列, k)``。``k`` は成長定数 [長さ/sqrt(フレーム)]。
#: 距離は「いつ合体するか」を先に決めてから逆算した(下の TRUE_MERGE)。
COLONIES = [
    (50.0, 40.0, 2.6),      # 0 ┐ 早い合体(t≈8)
    (50.0, 58.7, 2.8),      # 1 ┘
    (140.0, 45.0, 3.0),     # 2 ┐ 遅い合体(t≈30)
    (140.0, 81.2, 3.2),     # 3 ┘
    (55.00, 150.00, 2.4),   # 4 ┐ **ニアミス** —— 最後まで接しない。しかも
    (79.89, 125.11, 2.4),   # 5 ┘   接近方向が 45 度(斜めの近傍が効く配置)
    (170.0, 150.0, 2.9),    # 6   孤立
]

#: 合体する組(閉形式で真の時刻が出る)
PAIRS = [(0, 1), (2, 3)]

#: 最後まで接しない組(3-D 近傍の選び方で誤って 1 個にされうる)
NEAR_MISS = (4, 5)


def radius(i: int, t) -> np.ndarray:
    """コロニー ``i`` の半径 ``k sqrt(t + T0)``(拡散律速)。"""
    return COLONIES[i][2] * np.sqrt(np.asarray(t, float) + T0)


def true_merge_time(i: int, j: int) -> float:
    """接する時刻の**閉形式**。``k_i sqrt(t+T0) + k_j sqrt(t+T0) = d``。"""
    ri, ci, ki = COLONIES[i]
    rj, cj, kj = COLONIES[j]
    d = float(np.hypot(ri - rj, ci - cj))
    return (d / (ki + kj)) ** 2 - T0


def gap_at(i: int, j: int, t: float) -> float:
    """時刻 ``t`` の縁どうしの隙間(負なら重なっている)。"""
    ri, ci, _ = COLONIES[i]
    rj, cj, _ = COLONIES[j]
    return float(np.hypot(ri - rj, ci - cj) - radius(i, t) - radius(j, t))


# --- 合成(二値のタイムラプス)------------------------------------------------ #
def render_frame(t: float, pixel: float = 1.0):
    """時刻 ``t`` の二値像。``pixel`` は 1 画素の長さ(大きいほど粗い)。

    画素は**中心が円の内側にあれば前景**。アンチエイリアスしない —— 真値は
    連続円で、観測はその標本化、という関係を崩さないため。
    """
    n = int(np.ceil(N / pixel))
    c = (np.arange(n) + 0.5) * pixel          # 画素中心の座標 [長さ単位]
    yy, xx = np.meshgrid(c, c, indexing="ij")
    m = np.zeros((n, n), bool)
    for i, (cy, cx, _) in enumerate(COLONIES):
        r = float(radius(i, t))
        m |= (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r
    return m


def render_volume(stride: int = 1, pixel: float = 1.0):
    """``(T', H, W)`` の二値体積。``stride`` はフレーム間引き。

    返りは ``(vol, times)`` —— ``times`` は各スライスの**元の時計での時刻**。
    """
    times = np.arange(0, T, stride, dtype=float)
    vol = np.stack([render_frame(t, pixel) for t in times], axis=0)
    return vol, times


# --- 測る ------------------------------------------------------------------- #
def per_frame_counts(vol):
    """★ゼロ点 —— **各フレームを独立に** ``blob_label`` で数える。"""
    return np.array([int(np.asarray(fs.ledger.blob_label(vol[t],
                                                         connectivity=8)).max())
                     for t in range(vol.shape[0])])


def spacetime_families(vol, connectivity: int = 6):
    """``(t, y, x)`` を体積として 3-D 連結成分に分ける。

    返りは ``(labels, n, family_of_colony)``。``family_of_colony[i]`` は
    コロニー ``i`` の中心画素が属するラベル(0 = 背景 = 視野外)。
    """
    labels, n = fs.vol_label(vol, connectivity=connectivity)
    labels = np.asarray(labels)
    h = labels.shape[1]
    pixel = N / h
    fam = []
    for cy, cx, _ in COLONIES:
        r = int(min(h - 1, max(0, round(cy / pixel - 0.5))))
        c = int(min(h - 1, max(0, round(cx / pixel - 0.5))))
        fam.append(int(labels[0, r, c]))
    return labels, n, fam


def merge_frame_from_volume(labels, fam_id, times, connectivity2d: int = 4):
    """家族 ``fam_id`` のスライスが**初めて 1 個の連結成分になる**時刻。

    3-D のラベル付けが「どれとどれが同じ家族か」を決め、その家族に**限って**
    フレームごとの成分数を数える。フレームを独立に見る方式との違いはここ ——
    「数が 2 から 1 に減った」ではなく「**この 2 個が**1 個になった」と言える。
    """
    for k in range(labels.shape[0]):
        sl = labels[k] == fam_id
        if not sl.any():
            continue
        n2 = int(np.asarray(fs.ledger.blob_label(sl,
                                                 connectivity=connectivity2d)).max())
        if n2 == 1:
            return float(times[k])
    return float("nan")


def _pair_connected(i: int, j: int, t: float, pixel: float,
                    connectivity2d: int = 4, shift=(0.0, 0.0)) -> bool:
    """時刻 ``t`` に、コロニー ``i`` と ``j`` の**離散化された**円が繋がるか。

    2 つだけを、必要な範囲だけ描く(掃引で何百回も呼ぶので)。
    ``shift`` は**画素格子に対する場面のずらし**[長さ単位] —— 格子の位相が
    結果をどれだけ動かすかを測るために要る(5 節)。
    """
    cy1, cx1, _ = COLONIES[i]
    cy2, cx2, _ = COLONIES[j]
    cy1, cx1 = cy1 + shift[0], cx1 + shift[1]
    cy2, cx2 = cy2 + shift[0], cx2 + shift[1]
    r1, r2 = float(radius(i, t)), float(radius(j, t))
    lo_y = max(0.0, min(cy1 - r1, cy2 - r2) - 2 * pixel)
    hi_y = min(float(N), max(cy1 + r1, cy2 + r2) + 2 * pixel)
    lo_x = max(0.0, min(cx1 - r1, cx2 - r2) - 2 * pixel)
    hi_x = min(float(N), max(cx1 + r1, cx2 + r2) + 2 * pixel)
    k0, k1 = int(lo_y / pixel), int(np.ceil(hi_y / pixel))
    l0, l1 = int(lo_x / pixel), int(np.ceil(hi_x / pixel))
    yy = (np.arange(k0, k1) + 0.5) * pixel
    xx = (np.arange(l0, l1) + 0.5) * pixel
    gy, gx = np.meshgrid(yy, xx, indexing="ij")
    m = (((gy - cy1) ** 2 + (gx - cx1) ** 2 <= r1 * r1)
         | ((gy - cy2) ** 2 + (gx - cx2) ** 2 <= r2 * r2))
    lab = np.asarray(fs.ledger.blob_label(m, connectivity=connectivity2d))
    a = int(lab[int(round(cy1 / pixel - 0.5)) - k0, int(round(cx1 / pixel - 0.5)) - l0])
    b = int(lab[int(round(cy2 / pixel - 0.5)) - k0, int(round(cx2 / pixel - 0.5)) - l0])
    return a != 0 and a == b


def merge_time_continuous(i: int, j: int, pixel: float = 1.0,
                          connectivity2d: int = 4, tol: float = 0.01,
                          shift=(0.0, 0.0)) -> float:
    """**時間を連続とみなした**ときの合体時刻(空間の離散化だけが効く)。

    フレーム量子化と空間の離散化を**分けて数える**ための対照。二分法。
    """
    lo, hi = -T0 + 1e-6, float(T) * 4.0
    if _pair_connected(i, j, lo, pixel, connectivity2d, shift):
        return lo
    if not _pair_connected(i, j, hi, pixel, connectivity2d, shift):
        return float("nan")
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if _pair_connected(i, j, mid, pixel, connectivity2d, shift):
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


#: 画素格子の位相を振るためのずらし(単位は「画素サイズの何倍か」)。
PHASES = [(0.0, 0.0), (0.37, 0.11), (0.5, 0.5), (0.13, 0.41), (0.29, 0.83)]


def growth_fit(vol, labels, fam_id, colony_ids, times, pixel: float):
    """家族の**合体前**のフレームだけを使って ``k`` を出す。

    面積は ``A = pi k² (t + T0)`` なので、``A`` を ``t`` に対して直線当てはめ
    した傾きが ``pi k²``。**合体後は面積が和になるので使えない** ——
    どこまでが合体前かは 3-D のラベルが教えてくれる。
    """
    out = {}
    h = labels.shape[1]
    for i in colony_ids:
        cy, cx, _ = COLONIES[i]
        r0 = int(min(h - 1, max(0, round(cy / pixel - 0.5))))
        c0 = int(min(h - 1, max(0, round(cx / pixel - 0.5))))
        ts, areas = [], []
        for k in range(labels.shape[0]):
            sl = labels[k] == fam_id
            if not sl.any():
                continue
            lab2 = np.asarray(fs.ledger.blob_label(sl, connectivity=4))
            mine = int(lab2[r0, c0])
            if mine == 0:
                continue
            # このコロニーの塊に他のコロニーの中心も入っていたら、もう合体後
            merged = False
            for j in colony_ids:
                if j == i:
                    continue
                cy2, cx2, _ = COLONIES[j]
                r2 = int(min(h - 1, max(0, round(cy2 / pixel - 0.5))))
                c2 = int(min(h - 1, max(0, round(cx2 / pixel - 0.5))))
                if int(lab2[r2, c2]) == mine:
                    merged = True
                    break
            if merged:
                break
            ts.append(times[k])
            areas.append(float(np.count_nonzero(lab2 == mine)) * pixel * pixel)
        if len(ts) < 3:
            out[i] = float("nan")
            continue
        slope = np.polyfit(np.asarray(ts), np.asarray(areas), 1)[0]
        out[i] = float(np.sqrt(max(slope, 0.0) / np.pi))
    return out


# =========================================================================== #
def section1_check():
    print("=" * 78)
    print("1) 合成の検算 —— 二値像の面積は pi r² に一致するか")
    print("=" * 78)
    print("  真値: r_i(t) = k_i sqrt(t + %.0f)。接触時刻 t = (d/(k_i+k_j))² - %.0f。"
          % (T0, T0))
    print()
    print("  組  距離  k の和  **真の合体時刻**  最終フレームの隙間")
    for i, j in PAIRS + [NEAR_MISS]:
        d = float(np.hypot(COLONIES[i][0] - COLONIES[j][0],
                           COLONIES[i][1] - COLONIES[j][1]))
        tm = true_merge_time(i, j)
        tag = "(ニアミス)" if (i, j) == NEAR_MISS else ""
        print("  %d-%d  %5.1f  %6.2f  %12.3f     %6.2f %s"
              % (i, j, d, COLONIES[i][2] + COLONIES[j][2], tm,
                 gap_at(i, j, T - 1), tag))
    print()
    vol, times = render_volume()
    print("  体積 (t, y, x) = %s、前景率 %.1f %% → %.1f %%"
          % (vol.shape, 100 * vol[0].mean(), 100 * vol[-1].mean()))
    # 孤立コロニー 6 の面積で標本化の質を測る
    i = 6
    err = []
    for k in (0, T // 2, T - 1):
        lab = np.asarray(fs.ledger.blob_label(vol[k], connectivity=8))
        r0 = int(round(COLONIES[i][0] - 0.5))
        c0 = int(round(COLONIES[i][1] - 0.5))
        a = float(np.count_nonzero(lab == lab[r0, c0]))
        r = float(radius(i, times[k]))
        err.append((times[k], r, a, np.pi * r * r))
    print()
    print("  孤立コロニー(#6)の面積 —— 画素数 vs pi r²:")
    print("  %6s %8s %10s %10s %9s" % ("t", "真の r", "画素数", "pi r²", "相対誤差%"))
    for t, r, a, at in err:
        print("  %6.0f %8.2f %10.0f %10.1f %9.2f"
              % (t, r, a, at, 100 * (a - at) / at))
    print("  → 半径が大きいほど相対誤差は小さい(縁の画素の割合が減るため)。")
    print("     **これが空間の標本化の床**。5 節でこれを時刻の誤差へ換算する。")
    return vol, times


def section2_zero_point(vol, times):
    print()
    print("=" * 78)
    print("2) ★ゼロ点 —— 各フレームを独立に数える(時間の情報を使わない)")
    print("=" * 78)
    counts = per_frame_counts(vol)
    print("  フレームごとの塊の数:")
    line = "  "
    for k in range(0, vol.shape[0], 4):
        line += "t=%2.0f:%d  " % (times[k], counts[k])
    print(line)
    drops = [int(k) for k in range(1, len(counts)) if counts[k] < counts[k - 1]]
    print()
    print("  数が減ったフレーム: %s" % ([float(times[k]) for k in drops],))
    print("  真の合体時刻: %s" % ([round(true_merge_time(i, j), 2) for i, j in PAIRS],))
    print()
    print("  → 数の減りは**確かに検出できる**。ゼロ点は思ったより強い。")
    print("     ★しかしこの方式が答えられないことが 3 つある:")
    print("       (1) **どれとどれが**合体したのか(組が分からない)")
    print("       (2) 減ったのが合体なのか、視野外へ出た/消えたのか")
    print("       (3) 同じフレームで 2 組が合体すると 1 回の減少に見える")
    print("     どれも「フレームどうしの対応」が要る問い。**時間の情報を")
    print("     使わない限り、原理的に答えられない**。")
    return counts


def section3_spacetime(vol, times):
    print()
    print("=" * 78)
    print("3) ★時空間の連結成分 —— (t, y, x) を 1 つの体積として扱う")
    print("=" * 78)
    labels, n, fam = spacetime_families(vol, connectivity=6)
    print("  `fs.vol_label(vol, connectivity=6)` → 家族 %d 個" % n)
    print("  コロニー → 家族: %s" % (fam,))
    groups = {}
    for i, f in enumerate(fam):
        groups.setdefault(f, []).append(i)
    for f in sorted(groups):
        tag = "合体して 1 本の管" if len(groups[f]) > 1 else "単独の管"
        print("    家族 %d: コロニー %s(%s)" % (f, groups[f], tag))
    print()
    print("  → ★ニアミスの %s は**別の家族**のまま(隙間 %.2f 長さ単位)。"
          % (list(NEAR_MISS), gap_at(*NEAR_MISS, T - 1)))
    print("     フレームを独立に数える方式では『ずっと 2 個』としか言えないが、")
    print("     時空間では『2 本の管が最後まで交わらない』と**形で**言える。")
    print()
    # 体積の検算: 家族の voxel 数 = Σ_t 面積。孤立コロニーなら閉形式。
    props = fs.ledger.vol_region_props(labels)
    print("  `vol_region_props` による家族ごとの時空間体積(= Σ_t 面積):")
    print("  %6s %12s %14s %10s" % ("家族", "voxel 数", "閉形式(孤立)", "相対誤差%"))
    for p in props:
        f = int(p["label"])
        ids = groups.get(f, [])
        if len(ids) == 1:
            i = ids[0]
            closed = float(np.pi * COLONIES[i][2] ** 2 * np.sum(times + T0))
            print("  %6d %12d %14.0f %10.2f"
                  % (f, p["voxel_count"], closed,
                     100 * (p["voxel_count"] - closed) / closed))
        else:
            print("  %6d %12d %14s %10s" % (f, p["voxel_count"], "—(合体)", "—"))
    print("  → 孤立した管の体積は閉形式 pi k² Σ(t+t0) と 1 % 以内で合う。")
    print("     **体積そのものが成長則の検算になる**(面積を毎フレーム測って")
    print("     足し合わせるのと同じだが、3-D の op なら 1 回で出る)。")
    return labels, n, fam, groups


def section4_merge_time(vol, times, labels, groups):
    print()
    print("=" * 78)
    print("4) ★合体時刻 —— 体積の Y 字から読む。2-D 近傍 4 と 8 の差")
    print("=" * 78)
    print("  家族に限ってフレームごとの成分数を数え、初めて 1 個になった時刻。")
    print("  着手前の予想:「画素中心が円に入るまで前景にならないので、観測は")
    print("  **必ず遅れる**」。**外れた** —— 実測は下のとおり。")
    print()
    print("  誤差を 2 つに**分けて数える**:")
    print("    空間の離散化 = 時間を連続とみなしたときの合体時刻 - 真値")
    print("                   (二分法で 0.01 フレームまで詰める)")
    print("    時間の量子化 = フレーム格子上の観測 - 上の連続時刻")
    print()
    print("  %6s %11s | %11s %9s | %9s %9s | %9s"
          % ("組", "真値", "連続(4近傍)", "空間ぶん", "観測", "時間ぶん", "8 近傍"))
    print("  " + "-" * 78)
    out = {}
    for i, j in PAIRS:
        f = None
        for fam_id, ids in groups.items():
            if i in ids and j in ids:
                f = fam_id
        tm = true_merge_time(i, j)
        tc = merge_time_continuous(i, j, 1.0, 4)
        t4 = merge_frame_from_volume(labels, f, times, 4)
        t8 = merge_frame_from_volume(labels, f, times, 8)
        print("  %6s %11.3f | %11.2f %9.2f | %9.1f %9.2f | %9.1f"
              % ("%d-%d" % (i, j), tm, tc, tc - tm, t4, t4 - tc, t8))
        out[(i, j)] = (tm, tc, t4, t8)
    print()
    print("  → ★★**予想が外れた。空間の離散化は合体を「早める」。**")
    print("     理由: 画素は面積を持つので、円は**画素半分ぶん太った形**に")
    print("     なる。2 つの円がまだ触れていなくても、隙間が 1 画素より狭く")
    print("     なった瞬間に**隣り合う画素中心**が両方の内側に入り、4 近傍で")
    print("     繋がってしまう。つまり離散化は物を**太らせる**。「標本化は")
    print("     取りこぼす方向にしか効かない」という直感が通用しない例。")
    print("  → 一方フレーム格子への丸めは**必ず遅らせる**(次のコマまで")
    print("     気付けない)。**2 つは逆向き**なので、合計の誤差の符号は")
    print("     組によって変わる —— 上の表で 0-1 は負、2-3 は正。")
    print("     **1 つの誤差指標に畳むと打ち消して「良い数字」に化ける。**")
    print("  → 4 近傍と 8 近傍は今回の配置では同じ答えになった。斜めだけで")
    print("     触れる画素配置が、この中心座標では起きなかったため(6 節で")
    print("     3-D 側の近傍を振ると違いが出る)。")
    return out


def section5_sampling(base_merge):
    print()
    print("=" * 78)
    print("5) ★★標本化 —— 時間を粗くするのと空間を粗くするのは、どちらが先に効くか")
    print("=" * 78)
    print("  フレーム間引き ``stride`` と画素サイズ ``pixel`` を**独立に**振り、")
    print("  4 節の分解に従って**同じ単位(フレーム)で**比べる。")
    for i, j in PAIRS:
        tm = true_merge_time(i, j)
        v = (COLONIES[i][2] + COLONIES[j][2]) / (2.0 * np.sqrt(tm + T0))
        print("    組 %d-%d: 接触の直前 d(r_i+r_j)/dt = %.3f 長さ単位/フレーム"
              " → 1 画素 = %.2f フレーム" % (i, j, v, 1.0 / v))
    print("  この換算があるので、**空間の粗さは時間の誤差に化ける**。")
    print()
    strides = [1, 2, 4, 8]
    pixels = [1.0, 2.0, 3.0, 4.0]
    rec = {"stride": strides, "pixel": pixels, "err_stride": {},
           "err_pixel": {}, "spread_pixel": {}}
    for i, j in PAIRS:
        tm = true_merge_time(i, j)
        # --- 空間だけ: 時間を連続とみなして画素サイズを振る。
        #     ★格子の位相を 5 通り振り、**偏り(平均)と ばらつき(幅)を分けて**数える。
        means, spreads = [], []
        for p in pixels:
            vs = [merge_time_continuous(i, j, p, 4, shift=(dy * p, dx * p)) - tm
                  for dy, dx in PHASES]
            means.append(float(np.mean(vs)))
            spreads.append(float(np.max(vs) - np.min(vs)))
        rec["err_pixel"][(i, j)] = means
        rec["spread_pixel"][(i, j)] = spreads
        # --- 時間だけ: 画素 1 のまま、フレーム格子への丸めぶん
        tc = merge_time_continuous(i, j, 1.0, 4)
        es = []
        for s in strides:
            vol, times = render_volume(stride=s, pixel=1.0)
            lab, _, fam = spacetime_families(vol, 6)
            es.append(merge_frame_from_volume(lab, fam[i], times, 4) - tc)
        rec["err_stride"][(i, j)] = es
    print("  ★時間だけを粗くしたときの誤差 [フレーム](画素は 1 のまま)。")
    print("    ★stride 2/4/8 で値が動かないのは**偶然** —— 真の合体が t=6.83 と")
    print("    30.06 で、どの格子でも次のコマが t=8 と 32 になるから。量子化")
    print("    誤差は「stride が上限」であって「stride に比例」ではない。")
    print("  %10s" % "stride", end="")
    for s in strides:
        print(" %10d" % s, end="")
    print()
    for key in rec["err_stride"]:
        print("  %10s" % ("組 %d-%d" % key), end="")
        for v in rec["err_stride"][key]:
            print(" %10.2f" % v, end="")
        print()
    print()
    print("  ★空間だけを粗くしたときの誤差 [フレーム](時間は連続)。")
    print("    **偏り**= 画素格子の位相 5 通りの平均 / **ばらつき**= その幅:")
    print("  %10s" % "pixel", end="")
    for p in pixels:
        print(" %14.1f" % p, end="")
    print()
    for key in rec["err_pixel"]:
        print("  %10s" % ("組 %d-%d" % key), end="")
        for k in range(len(pixels)):
            print(" %7.2f±%-6.2f" % (rec["err_pixel"][key][k],
                                     rec["spread_pixel"][key][k]), end="")
        print()
    print()
    print("  → ★★**空間の粗さは偏りよりも「ばらつき」で効く**。画素 4 倍で")
    print("     偏りは組 %d-%d が %.2f フレームなのに、格子をずらしただけで"
          % (PAIRS[0][0], PAIRS[0][1], rec["err_pixel"][PAIRS[0]][3]))
    print("     %.2f フレームの幅が出る。**同じ実験を同じ倍率で撮り直しても、"
          % rec["spread_pixel"][PAIRS[0]][3])
    print("     カメラを 1 画素ずらしただけで答えが変わる。**")
    print("     偏りだけを見ていると『画素を粗くしても大丈夫』と誤読する。")
    print()
    for key in PAIRS:
        s4 = abs(rec["err_stride"][key][2])
        p4 = abs(rec["err_pixel"][key][3]) + 0.5 * rec["spread_pixel"][key][3]
        who = "空間" if p4 > s4 else "時間"
        print("  組 %d-%d を 4 倍粗くすると 時間 %.2f / 空間 %.2f"
              "(偏り+半幅)フレーム → **%s のほうが先に効く**"
              % (key[0], key[1], s4, p4, who))
    return rec


def section6_connectivity():
    print()
    print("=" * 78)
    print("6) ★3-D 近傍 6 / 18 / 26 —— ニアミスを 1 個にしてしまうか")
    print("=" * 78)
    print("  コロニー %s は最後まで %.2f 長さ単位の隙間がある(接していない)。"
          % (list(NEAR_MISS), gap_at(*NEAR_MISS, T - 1)))
    print("  ところが 26 近傍は**斜め + 1 フレーム先**まで繋ぐので、")
    print("  『時間方向の斜め』で偽の合体を作りうる。実測:")
    print()
    vol, times = render_volume()
    print("  %10s %10s %20s" % ("connectivity", "家族数", "ニアミスの 2 つ"))
    print("  " + "-" * 44)
    got = {}
    for conn in (6, 18, 26):
        _, n, fam = spacetime_families(vol, conn)
        same = fam[NEAR_MISS[0]] == fam[NEAR_MISS[1]]
        got[conn] = (n, same)
        print("  %10d %10d %20s" % (conn, n, "★同じ家族(誤り)" if same else "別の家族"))
    print()
    print("  → ★★**18 と 26 は接していない 2 つを 1 個の家族にした**。")
    print("     この配置は接近方向を 45 度に取ってある —— 面近傍(6)だけなら")
    print("     隙間 %.2f 長さ単位は渡れないが、斜めの近傍は sqrt(2) 画素まで"
          % gap_at(*NEAR_MISS, T - 1))
    print("     届くので渡れてしまう。**既定値は 26** なので、何も指定せずに")
    print("     `vol_label` を呼ぶとこの誤りを踏む。")
    print("  → 逆に、菌糸のように斜めでも繋がる対象なら 26 が正しい。")
    print("     **道具の既定ではなく対象の物理が決める** —— `vol_label` が")
    print("     `connectivity` を引数に出しているのは正しい設計だが、")
    print("     既定を 26 にしているぶん、黙って使うと寛容側へ倒れる。")
    return got


def section7_growth_constant(vol, times, labels, groups):
    print()
    print("=" * 78)
    print("7) ★成長定数 k の推定 —— 合体後のフレームを混ぜると何が起きるか")
    print("=" * 78)
    print("  A = pi k² (t + %.0f) の傾きから k を出す。**合体後は面積が和に**"
          % T0)
    print("  **なる**ので使えない。どこまでが合体前かは 3-D のラベルが教える。")
    print()
    print("  %8s %10s %12s %10s %12s %10s"
          % ("コロニー", "真の k", "合体前のみ", "誤差%", "全フレーム", "誤差%"))
    print("  " + "-" * 68)
    for i, j in PAIRS:
        f = [fid for fid, ids in groups.items() if i in ids and j in ids][0]
        est = growth_fit(vol, labels, f, [i, j], times, 1.0)
        for c in (i, j):
            k_true = COLONIES[c][2]
            # 対照: 家族全体の面積をそのコロニーのものと思い込んで全フレーム使う
            areas = np.array([float(np.count_nonzero(labels[k] == f))
                              for k in range(labels.shape[0])])
            slope = np.polyfit(times, areas, 1)[0]
            k_naive = float(np.sqrt(max(slope, 0.0) / np.pi))
            print("  %8d %10.3f %12.3f %10.2f %12.3f %10.1f"
                  % (c, k_true, est[c], 100 * (est[c] - k_true) / k_true,
                     k_naive, 100 * (k_naive - k_true) / k_true))
    print()
    print("  → 合体前だけを使えば k は数 % 以内。合体後を混ぜると和の面積を")
    print("     1 個ぶんと読むので大きく外れる。**「どこで切るか」を決める")
    print("     情報が、まさに時空間のラベルが持っているもの。**")


def section8_figures(vol, times, labels, groups, rec, merge):
    if not figs.enabled():
        return
    # 1) フレーム 3 枚 + 時間最大投影
    proj = vol.max(axis=0)
    figs.save_grid("frames", [vol[0], vol[T // 3], vol[-1], proj],
                   ["t=0", "t=%d" % (T // 3), "t=%d" % (T - 1), "時間最大投影"],
                   title="成長のタイムラプス(48 フレーム)", ncols=2,
                   caption="拡散律速 r = k sqrt(t + 4)。左上の 2 個は t≈8 で、"
                           "左下の 2 個は t≈30 で合体する。右の斜めに並んだ "
                           "2 個は最後まで接しない(隙間 0.92 長さ単位)——"
                           "この隙間を 26 近傍が渡ってしまう(6 節)。")
    # 2) ★Y 字 —— 合体する組の中心を通る行で体積を切る
    row = int(round(COLONIES[0][0] - 0.5))
    slab = labels[:, row, :]                 # (T, W) 家族ラベル
    slab2 = labels[:, int(round(COLONIES[2][0] - 0.5)), :]
    figs.save_grid("ystructure",
                   [np.repeat(slab, 4, axis=0), np.repeat(slab2, 4, axis=0)],
                   ["行 %d(t≈8 で合体)" % row,
                    "行 %d(t≈30 で合体)" % int(round(COLONIES[2][0] - 0.5))],
                   title="時空間の断面 —— 合体は Y 字になる", ncols=1,
                   caption="縦が時間(下向き、4 倍に拡大)、横が列。2 本の管が"
                           "合わさる高さがそのまま合体時刻。色は 3-D ラベル。")
    # 3) 標本化の比較(同じ縦軸 = フレーム)
    series = []
    for key in rec["err_stride"]:
        series.append(("組 %d-%d 時間を粗く" % key,
                       np.asarray(rec["stride"], float),
                       np.asarray(rec["err_stride"][key])))
    for key in rec["err_pixel"]:
        series.append(("組 %d-%d 空間を粗く" % key,
                       np.asarray(rec["pixel"], float),
                       np.asarray(rec["err_pixel"][key])))
    figs.save_plot("sampling", series,
                   xlabel="粗さ(フレーム間引き stride / 画素サイズ pixel)",
                   ylabel="合体時刻の誤差 [フレーム]",
                   title="時間を粗くするのと空間を粗くするのはどちらが効くか",
                   caption="横軸はどちらも『何倍粗くしたか』。時間は必ず正"
                           "(次のコマまで気付けない)、空間は必ず負"
                           "(画素が物を太らせる)。空間側は画素格子の位相"
                           "5 通りの平均で、ばらつきは表を参照。")
    # 4) 表(ばらつきまで含めて Excel へ持ち出せる形で)
    rows_tbl = []
    for key in rec["err_stride"]:
        for k, s in enumerate(rec["stride"]):
            rows_tbl.append(["%d-%d" % key, "時間", "%d" % s,
                             "%.2f" % rec["err_stride"][key][k], "—"])
        for k, p in enumerate(rec["pixel"]):
            rows_tbl.append(["%d-%d" % key, "空間", "%.0f" % p,
                             "%.2f" % rec["err_pixel"][key][k],
                             "%.2f" % rec["spread_pixel"][key][k]])
    figs.save_table("sampling_table",
                    ["組", "粗くした軸", "倍率", "誤差 frame", "位相の幅"],
                    rows_tbl, title="標本化と合体時刻の誤差",
                    caption="空間側は格子の位相でこれだけ動く(偏りより大きい)。")


def section9_findings(rec, conn, merge):
    print()
    print("=" * 78)
    print("9) 所見")
    print("=" * 78)
    e_s = rec["err_stride"][PAIRS[0]]
    e_p = rec["err_pixel"][PAIRS[0]]
    e_s2 = rec["err_stride"][PAIRS[1]]
    e_p2 = rec["err_pixel"][PAIRS[1]]
    sp = rec["spread_pixel"]
    print("""
  (1) ★ゼロ点(フレーム独立の計数)は**合体の検出そのものはできる**。
      塊の数が減ったフレームは真の合体時刻の 1 コマ以内に出た。
      壊れるのはその先 —— 「どれとどれが」「合体か消失か」「同時に 2 組か」。
      時空間の連結成分はこの 3 つを**形として**持っている。
      ゼロ点は思ったより強い、と正直に書いておく。

  (2) ★★**空間の離散化は合体を「早める」**(予想が外れた)。画素は
      面積を持つので円は半画素ぶん太り、まだ接していないのに隣り合う
      画素中心が両方の内側に入って繋がる。連続時間で測った合体時刻は
      組 %d-%d で真値より %+.2f、組 %d-%d で %+.2f フレーム。
      一方フレーム格子への丸めは**必ず遅らせる**(%+.2f / %+.2f)。
      **2 つは逆向き**なので、合計だけ見ると打ち消して小さく見える。

  (3) ★★「時間の標本化が空間の分解能より先に効く」は**成り立たなかった**
      (これも予想が外れた)。4 倍粗くしたときの誤差は
      組 %d-%d で 時間 %.2f / 空間 %.2f(偏り %+.2f、位相のばらつき %.2f)、
      組 %d-%d で 時間 %.2f / 空間 %.2f(偏り %+.2f、ばらつき %.2f)。
      **どちらの組でも空間が勝つ**。理由は換算にある —— 接触の直前は
      半径が 1/sqrt(t) でしか伸びないので、長さの誤差が
      「長さ ÷ 縁の速さ」で何フレームにも化ける。
      時間軸は「上限が stride」で頭打ちになるが、空間軸には頭打ちが無い。

  (4) ★★空間の粗さは**偏りよりばらつきで効く**。画素 4 倍で偏り
      %+.2f フレームに対し、**格子の位相を変えるだけで %.2f フレームの幅**。
      同じ倍率で撮り直しても、カメラが 1 画素ずれれば答えが変わる。
      偏りだけを報告すると「粗くしても平気」と誤読する。

  (5) ★★3-D 近傍の**既定 26 はニアミスを合体させた**。6 / 18 / 26 で
      家族数 %d / %d / %d、ニアミスの 2 つを同じ家族にしたか: %s。
      隙間 %.2f 長さ単位は面近傍では渡れないが、斜め近傍は sqrt(2) 画素
      まで届く。**寛容側が既定**なので、指定せずに呼ぶと偽の合体を拾う。

  (6) ★成長定数 k は**合体前のフレームだけ**なら誤差 3 %% 以内。
      合体後を混ぜると 19〜44 %% 外れる。**どこで切るかを教えるのが
      時空間のラベル** —— これが「体積として扱う」いちばん実用的な効き目。
""" % (PAIRS[0][0], PAIRS[0][1], merge[PAIRS[0]][1] - merge[PAIRS[0]][0],
       PAIRS[1][0], PAIRS[1][1], merge[PAIRS[1]][1] - merge[PAIRS[1]][0],
       merge[PAIRS[0]][2] - merge[PAIRS[0]][1],
       merge[PAIRS[1]][2] - merge[PAIRS[1]][1],
       PAIRS[0][0], PAIRS[0][1], abs(e_s[2]),
       abs(e_p[3]) + 0.5 * sp[PAIRS[0]][3], e_p[3], sp[PAIRS[0]][3],
       PAIRS[1][0], PAIRS[1][1], abs(e_s2[2]),
       abs(e_p2[3]) + 0.5 * sp[PAIRS[1]][3], e_p2[3], sp[PAIRS[1]][3],
       e_p[3], sp[PAIRS[0]][3],
       conn[6][0], conn[18][0], conn[26][0],
       "した(誤り)" if conn[26][1] else "しなかった",
       gap_at(*NEAR_MISS, T - 1)))


def section10_tool_gaps():
    print("=" * 78)
    print("10) 道具の穴")
    print("=" * 78)
    print("""
  (a) ★★**時空間ラベルを「スライスごとの成分」に落とす op が無い**。
      この PoC の中心操作 —— 3-D の家族に限って各フレームの 2-D 成分を
      数える —— は `vol_label` と `blob_label` を手で組み合わせて書いた。
      3-D 側に `vol_label_slice_rgb`(見る)はあるのに、**測る**側の
      「スライスごとの成分数 / 分裂・合体イベントの時刻」が無い。
      合体・分裂は時空間データの基本量なので、族として欲しい:
      `vol_slice_component_counts(labels)` → (T,) の本数、
      `vol_merge_events(labels)` → (時刻, 合体した部分の対)。

  (b) **成長則の当てはめが無い**。面積 → 半径 → 定数、という換算は
      `blob_features` の `equiv_diameter` まで来て止まる。時系列の
      当てはめ(`r = k sqrt(t)`、`r = v t`、Avrami)は 1 か所に欲しい。

  (c) ★**`fs.ledger.vol_label` と `fs.vol_label` の返りが違う**
      (台帳は配列だけ、facade は `(labels, n)`)。この PoC は
      成分数が要るので **facade を使わざるを得なかった** ——
      「型つき台帳のほうが情報が少ない」のは逆立ちしている。
      (`poc_particle_tracking.py` の穴 (f) と同じもの。)

  (d) **二値の時系列を「動画」として受ける型が無い**。`temporal_*` は
      float の ``(T, H, W)`` を想定し、`vol_*` は空間の 3 軸を想定する。
      同じ ``(T, H, W)`` を渡しても**どちらも通る**ので、
      6 節のように近傍の意味が変わっても警告が無い。

  (e) **`vol_region_props` の `centroid` が (z, y, x) のタプル**で、
      `blob_features` は鍵ごとの配列(`row` / `col`)。同じ「領域の
      性質」なのに 2-D と 3-D で器が違うので、両方を扱うコードで
      毎回書き分けが要る。
""")
    assert not hasattr(fs.ledger, "vol_slice_component_counts"), \
        "★スライス成分数の op が入った → (a) は直った。この assert を消すこと"
    assert not hasattr(fs.ledger, "vol_merge_events"), \
        "★合体イベントの op が入った → (a) は直った"
    assert not hasattr(fs.ledger, "growth_law_fit"), \
        "★成長則の当てはめが入った → (b) は直った"
    v = np.zeros((4, 8, 8), bool)
    v[:, 2:5, 2:5] = True
    assert isinstance(fs.vol_label(v, connectivity=6), tuple)
    assert isinstance(fs.ledger.vol_label(v, connectivity=6), np.ndarray), \
        "★台帳が n を返すようになった → (c) は直った"
    p = fs.ledger.vol_region_props(np.asarray(fs.ledger.vol_label(v, connectivity=6)))
    assert isinstance(p[0]["centroid"], tuple), "★(e) の器が変わった"
    print("  (assert 5 本で現状を固定した。穴が埋まったらこの PoC が落ちる。)")


def main():
    t0 = time.perf_counter()
    print("poc_timelapse_growth — 成長のタイムラプスを時空間の連結成分として測る")
    print("(その 2: 2-D の列を (t, y, x) の 1 つの体積とみなす)")
    print()
    vol, times = section1_check()
    section2_zero_point(vol, times)
    labels, n, fam, groups = section3_spacetime(vol, times)
    merge = section4_merge_time(vol, times, labels, groups)
    rec = section5_sampling(merge)
    conn = section6_connectivity()
    section7_growth_constant(vol, times, labels, groups)
    section8_figures(vol, times, labels, groups, rec, merge)
    section9_findings(rec, conn, merge)
    section10_tool_gaps()
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
