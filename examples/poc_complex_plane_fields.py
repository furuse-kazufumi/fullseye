# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 複素平面を「面」で見る —— 絵が定理を証明する側に回る

複素解析の図(位相彩色・ニュートンの吸引域・マンデルブロ集合・翼まわりの流れ)は、
きれいなので**合っているかどうかを誰も確かめない**種類の絵である。この PoC は
その 4 枚を描き、**1 枚ごとに「絵とは独立の真値」を当てて採点する**。

★**主張は「それらしい絵が出た」ではない。** 使った式で答え合わせをしない、が
この回の規律で、真値は次のどれかに限った:

1. **偏角の原理** —— 有理関数の場を作り、**この族の既存 op**(`cplx_winding_number`)に
   零点と極を数えさせる。零点 3 → 巻き数 3、零点 2 極 1 → 1、極 2 → −2。
   窓の外の零点は数えない(対照群)。
2. **絵そのものから定理が読める** —— 位相彩色の**色相が回る回数**が零点の位数に
   等しい。場の値は一切見ず、**画素の RGB だけ**から 1 / 2 / 3 / −2 を数える。
3. **Cayley (1879)** —— `z² − 1` のニュートン吸引域は**2 つの半平面**という厳密解。
   512×512 = **262,144 画素すべてが一致**、未収束 0。3 次は Cayley が解けなかった側で、
   同じ格子で境界画素が **13 倍**(1,026 → 13,348)—— そこが「フラクタルになった」の
   数値的な意味である。3 次でも**共役対称は厳密**(行を反転すると根 1 と 2 が入れ替わる)。
4. **閉形式の内部判定** —— 主カージオイドと周期 2 球は「固定点が吸引的」という
   式で**内側かどうかを iteration なしに**言える。その 85,624 画素は**反例 0 件**で
   max_iter に残り、しかし実際に残った 95,078 画素の **90.1 %** でしかない ——
   下界であることまで数で出る。`c = 0` のジュリア集合は**単位円**で、これも厳密。
5. **既存 op が真値**(`cplx_cr_residual`)—— 翼まわりの流れは翼の外で正則なので
   残差 2.06e-04。★**行の向きを間違えるとこの op は共役の場を測って 2 を返す**
   (実測 1.999951 —— 2 からのずれ 4.89e-05 は正則側の床と同じ桁。「ちょうど 2」に
   なるのは中心差分が厳密になる 2 次以下の多項式のときだけ)。罠を門にしてあり、
   PoC は両方の値を印字する。
6. **クッタ条件に対照群がある** —— 後縁で速度が有限なのは循環がクッタ条件で
   選ばれているからで、循環を 0 にすると `1/√距離` で発散する(実測 20 倍以上)。
   循環は経路に依らない(外周 −3.0263 / 内周 −3.0263、流束 1.3e-07)。
   ★揚力係数と薄翼理論の比は**厳密に a/b**(1.513 / 1.383 = 1.0940 = 1.0937)——
   厚みの効果が 1 つの数に落ちる。厚みを 0 に近づけると薄翼理論に戻る。

図:
1. ``rational``: 有理関数の位相彩色と、既存 op が数えた零点・極の個数。
2. ``orders``: 位数 1 / 2 / 3 の零点まわりで色相が回る回数(絵から読む)。
3. ``newton``: 2 次(厳密な半平面)と 3 次(フラクタル)を並べる。
4. ``boundary``: 境界画素の数 —— 次数を上げると何が起きるか。
5. ``mandelbrot``: 脱出時間に「閉形式で絶対に出ないと言える領域」を重ねる。
6. ``julia``: c = 0 は単位円板、c = −0.7269+0.1889j は連結なジュリア集合。
7. ``flow``: 翼まわりの速さと、クッタ条件のある/なしでの後縁の挙動。
8. ``lift``: 迎角に対する揚力係数と薄翼理論、その比が a/b で一定であること。
9. ``numbers``: 数表。

走らせ方: ``py -3.11 examples/poc_complex_plane_fields.py``
(図は ``out/figures/poc_complex_plane_fields/``)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

L = fs.ledger

#: 図の格子。検査は別に小さい格子で回るので、ここは見栄えのために大きめ。
BIG = (600, 800)
#: 翼の迎角[度]。
ALPHA_DEG = 8.0
#: 円の中心のずらし(負の実部 = 厚み、正の虚部 = キャンバ)。
MU = -0.09 + 0.09j


def ring(a, k):
    """外から k 番目の矩形リングを 1 周ぶん並べる(反時計回り)。"""
    h, w = a.shape[:2]
    i0, i1, j0, j1 = k, h - 1 - k, k, w - 1 - k
    idx = ([(i1, j) for j in range(j0, j1)]
           + [(i, j1) for i in range(i1, i0, -1)]
           + [(i0, j) for j in range(j1, j0, -1)]
           + [(i, j0) for i in range(i0, i1)])
    return np.array([a[i, j] for i, j in idx])


def hue_of(rgb):
    """RGB -> 色相 [0,1)。**絵から読み戻す**ための最小の逆変換。"""
    mx = rgb.max(axis=-1)
    mn = rgb.min(axis=-1)
    d = np.where(mx - mn == 0, 1.0, mx - mn)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.where(mx - mn == 0, 0.0,
                 np.where(mx == r, np.mod((g - b) / d, 6.0),
                          np.where(mx == g, (b - r) / d + 2.0, (r - g) / d + 4.0)))
    return np.mod(h / 6.0, 1.0)


def hue_turns(rgb, k):
    """リング上で色相が何周するか —— 偏角の原理を**絵だけ**から読む。"""
    h = hue_of(ring(rgb, k))
    inc = np.mod(np.diff(np.concatenate([h, h[:1]])) + 0.5, 1.0) - 0.5
    return float(inc.sum())


def boundary_pixels(lab):
    return int((lab[:-1, :] != lab[1:, :]).sum() + (lab[:, :-1] != lab[:, 1:]).sum())


def circulation(field, grid, k):
    zs, ws = ring(grid, k), ring(field, k)
    dz = np.roll(zs, -1) - zs
    return complex(np.sum(0.5 * (ws + np.roll(ws, -1)) * dz))


def main():
    t0 = time.time()
    ok = []

    def check(label, cond):
        ok.append((label, bool(cond)))
        print("  [%s] %s" % ("ok" if cond else "NG", label))

    rows = []

    # ---------------------------------------------------------------- 1 章 --
    print("== 1 章 偏角の原理 —— 既存の op に数えさせる ==")
    cases = [("零点 3(3 位)", [0.2 + 0.1j] * 3, [], 3),
             ("零点 2 + 極 1", [0.2 + 0.1j, -0.3 + 0.2j], [0.1 - 0.2j], 1),
             ("極 2", [], [0.1 - 0.2j, 0.4 + 0.4j], -2),
             ("窓の外の零点(対照群)", [5.0 + 0.0j], [], 0)]
    fields = {}
    for name, zs, ps, want in cases:
        hw = 1.0 if "外" in name else 2.0
        f = L.cplx_rational_field(zs, ps, half_width=hw, shape=(513, 513))
        got = int(L.cplx_winding_number(ring(f, 1), 0.0))
        fields[name] = f
        print("   %-22s 巻き数 %+d(期待 %+d)" % (name, got, want))
        rows.append([name, "巻き数", "%+d" % got, "%+d" % want])
        check("%s の巻き数が零点 − 極に一致" % name, got == want)

    main_field = fields["零点 2 + 極 1"]
    figs.save("rational", L.cplx_domain_colour(main_field),
              caption="有理関数 (z−z₁)(z−z₂)/(z−p) の位相彩色。色相 = 偏角、明度 = |z|。"
                      "零点では黒く、極では明るく色相が逆に回る。既存 op の "
                      "cplx_winding_number が同じ場から数えた巻き数は +1 "
                      "(零点 2 − 極 1)で、絵の色相の回り方と一致する。")

    # ---------------------------------------------------------------- 2 章 --
    print("== 2 章 絵から位数を読む(場の値は見ない)==")
    panels, caps = [], []
    for order in (1, 2, 3):
        f = L.cplx_rational_field([0.0 + 0.0j] * order, [], half_width=1.0,
                                  shape=(257, 257))
        rgb = L.cplx_domain_colour(f)
        t = hue_turns(rgb, 40)
        print("   %d 位の零点 -> 色相の巻き数 %+.4f" % (order, t))
        rows.append(["%d 位の零点" % order, "色相の巻き数", "%+.4f" % t, "%+d" % order])
        check("%d 位の零点で色相が %d 周する" % (order, order), abs(t - order) < 0.02)
        panels.append(rgb)
        caps.append("%d 位の零点(色相 %+.2f 周)" % (order, t))
    fpole = L.cplx_rational_field([], [0.0 + 0.0j] * 2, half_width=1.0, shape=(256, 256))
    rgbp = L.cplx_domain_colour(fpole)
    tp = hue_turns(rgbp, 40)
    print("   2 位の極     -> 色相の巻き数 %+.4f" % tp)
    rows.append(["2 位の極", "色相の巻き数", "%+.4f" % tp, "-2"])
    check("2 位の極で色相が逆に 2 周する", abs(tp + 2) < 0.02)
    panels.append(rgbp)
    caps.append("2 位の極(色相 %+.2f 周)" % tp)
    figs.save_grid("orders", panels, captions=caps, ncols=4,
                   caption="★絵が定理を証明する側に回る。零点のまわりを 1 周するあいだに"
                           "色相が何周するかが、そのまま零点の位数(極なら負)になる —— "
                           "偏角の原理。ここで数えているのは**画素の RGB だけ**で、"
                           "場の値は一度も見ていない。")

    # ---------------------------------------------------------------- 3 章 --
    print("== 3 章 ニュートンの吸引域 —— 2 次は厳密解がある ==")
    lab2 = L.cplx_newton_basins([1, 0, -1], half_width=1.5, shape=(512, 512),
                                max_iter=80)
    z2 = L.cplx_plane_grid(0j, 1.5, (512, 512))
    want2 = np.where(z2.real < 0, 1, 2).astype(np.int32)
    agree = int((lab2 == want2).sum())
    print("   2 次 z²−1: Cayley の半平面と一致 %d / %d 画素、未収束 %d"
          % (agree, lab2.size, int((lab2 == 0).sum())))
    rows.append(["2 次(Cayley)", "半平面と一致した画素", "%d" % agree, "%d" % lab2.size])
    check("2 次の吸引域が半平面と 1 画素も違わない", agree == lab2.size)
    check("2 次では未収束の画素が 1 つも無い", int((lab2 == 0).sum()) == 0)

    lab3 = L.cplx_newton_basins([1, 0, 0, -1], half_width=1.6, shape=(513, 513),
                                max_iter=60)
    sizes = [int((lab3 == k).sum()) for k in (1, 2, 3)]
    swapped = np.where(lab3 == 1, 2, np.where(lab3 == 2, 1, lab3))
    sym = bool(np.array_equal(lab3[::-1], swapped))
    print("   3 次 z³−1: 吸引域 %s、未収束 %d、共役対称 %s"
          % (sizes, int((lab3 == 0).sum()), sym))
    rows.append(["3 次(フラクタル)", "共役対称は厳密", "はい" if sym else "いいえ", "はい"])
    check("3 次の 3 つの吸引域がどれも空でない", min(sizes) > 0)
    check("3 次でも共役対称は厳密(1 画素も外れない)", sym)

    lab2b = L.cplx_newton_basins([1, 0, -1], half_width=1.6, shape=(513, 513),
                                 max_iter=60)
    b2, b3 = boundary_pixels(lab2b), boundary_pixels(lab3)
    print("   同じ格子での境界画素: 2 次 %d / 3 次 %d(%.0f 倍)" % (b2, b3, b3 / b2))
    rows.append(["境界画素(同じ格子)", "2 次 → 3 次", "%d → %d" % (b2, b3),
                 "%.0f 倍" % (b3 / b2)])
    check("3 次の境界は 2 次より一桁長い(フラクタルの数値的な意味)", b3 > 5 * b2)

    figs.save_grid("newton", [lab2.astype(np.float64), lab3.astype(np.float64)],
                   captions=["z²−1(Cayley の厳密解 = 2 つの半平面)",
                             "z³−1(Cayley が解けなかった側 = フラクタル境界)"],
                   ncols=2,
                   caption="★同じ手順、次数が 1 つ違うだけ。2 次は 262,144 画素すべてが"
                           "「Re z の符号」と一致し、境界は直線 1 本。3 次では同じ格子で"
                           "境界画素が %.0f 倍になる —— これが「フラクタルになった」の"
                           "数値的な意味。それでも共役対称は**厳密**に成り立つ。"
                           % (b3 / b2))
    figs.save_plot("boundary",
                   [("境界画素", np.array([2.0, 3.0]), np.array([float(b2), float(b3)]))],
                   xlabel="多項式の次数", ylabel="境界画素の数",
                   title="次数を 1 つ上げると境界が一桁伸びる",
                   caption="2 次の境界は虚軸 1 本(513 画素の格子で %d)。3 次では %d ——"
                           "同じ格子・同じ max_iter でこれだけ違う。" % (b2, b3))

    # ---------------------------------------------------------------- 4 章 --
    print("== 4 章 脱出時間 —— 閉形式で「絶対に出ない」と言える所 ==")
    mi = 200
    esc = L.cplx_escape_time("mandelbrot", centre=-0.5 + 0j, half_width=1.6,
                             shape=BIG, max_iter=mi)
    grid = L.cplx_plane_grid(-0.5 + 0j, 1.6, BIG)
    proven = L.mandelbrot_interior(grid)
    stay = esc == float(mi)
    bad = int((esc[proven] != float(mi)).sum())
    print("   閉形式で『絶対に出ない』と言える画素 %d、反例 %d 件"
          % (int(proven.sum()), bad))
    print("   実際に残った画素 %d —— 閉形式はその %.1f %%(= 下界)"
          % (int(stay.sum()), 100.0 * proven.sum() / stay.sum()))
    rows.append(["主カージオイド + 周期 2 球", "反例", "%d 件" % bad, "0 件"])
    rows.append(["閉形式が覆う割合", "残った画素に対して", "%.1f %%"
                 % (100.0 * proven.sum() / stay.sum()), "< 100 %(下界)"])
    check("閉形式が『出ない』と言った画素は 1 つも脱出しない", bad == 0)
    check("しかし全部は覆えない(下界であることも数で出る)",
          proven.sum() < stay.sum())
    check("鏡像対称は厳密(許容差すら要らない)", np.array_equal(esc, esc[::-1]))

    overlay = np.where(proven, float(mi) * 1.25, esc)
    figs.save_grid("mandelbrot", [esc, overlay],
                   captions=["脱出時間(反復回数)",
                             "閉形式で『絶対に出ない』と言える領域を重ねた図"],
                   ncols=2,
                   caption="★★右の明るい部分は**反復せずに**内側と分かる領域 —— 固定点 "
                           "z* = (1−√(1−4c))/2 が吸引的(|2z*| < 1)なら軌道は決して "
                           "脱出しない、という閉形式。実測で反例 0 件。ただし残った "
                           "%d 画素のうち %.1f %% しか覆えない(小さい球と糸は覆えない)—— "
                           "「覆えない量」まで数で言えるのが下界の使い道。"
                           % (int(stay.sum()), 100.0 * proven.sum() / stay.sum()))

    j0 = L.cplx_escape_time("julia", param=0j, half_width=2.0, shape=(601, 601),
                            max_iter=80)
    g0 = L.cplx_plane_grid(0j, 2.0, (601, 601))
    r0 = np.abs(g0)
    inside_ok = bool(np.all(j0[r0 < 0.995] == 80.0))
    outside_ok = bool(np.all(j0[r0 > 1.005] < 80.0))
    print("   c = 0 のジュリア集合は単位円: 内 %s / 外 %s" % (inside_ok, outside_ok))
    rows.append(["c = 0 のジュリア集合", "充填集合 = 閉単位円板",
                 "内 %s / 外 %s" % ("○" if inside_ok else "×",
                                    "○" if outside_ok else "×"), "○ / ○"])
    check("c=0 では |z|<1 が残り |z|>1 が出る(厳密解)", inside_ok and outside_ok)
    jc = L.cplx_escape_time("julia", param=-0.7269 + 0.1889j, half_width=1.6,
                            shape=(601, 601), max_iter=120)
    figs.save_grid("julia", [j0, jc],
                   captions=["c = 0(充填集合は閉単位円板 —— 厳密解)",
                             "c = −0.7269 + 0.1889i(連結だが面積 0 に近い)"],
                   ncols=2,
                   caption="z → z² + c は |z| を 2 乗するだけなので、c = 0 では"
                           "「|z| < 1 は 0 へ、|z| > 1 は無限へ」が厳密に言える。"
                           "絵を見て納得するのではなく、半径で全数を走査して確かめた。")

    # ---------------------------------------------------------------- 5 章 --
    print("== 5 章 翼まわりの流れ —— 既存 op が正則性を測る ==")
    n, hw = 400, 3.0
    w = L.potential_flow_joukowski(alpha_deg=ALPHA_DEG, centre_offset=MU,
                                   shape=(n, n), half_width=hw)
    gr = L.cplx_plane_grid(0j, hw, (n, n))
    sp = 2.0 * hw / (n - 1)
    strip = w[20:120, 20:380]
    cr_flipped = float(L.cplx_cr_residual(strip[::-1], spacing=sp))
    cr_raw = float(L.cplx_cr_residual(strip, spacing=sp))
    print("   CR 残差: 行を反転 %.3e / そのまま %.6f(2 との差 %.2e)"
          % (cr_flipped, cr_raw, abs(2.0 - cr_raw)))
    rows.append(["翼の外は正則か", "CR 残差(反転)", "%.2e" % cr_flipped, "≈ 0"])
    rows.append(["行の向きを間違えると", "CR 残差(そのまま)", "%.6f" % cr_raw,
                 "2 − 床(共役)"])
    check("翼の外で正則(既存 op が真値)", cr_flipped < 5e-3)
    # ★「そのまま渡すと厳密に 2」が言えるのは **2 次以下の多項式**のときだけ
    #   (中心差分がそこまで厳密だから)。一般の正則場では 2 から**同じ床の分**
    #   だけ引かれる —— 実測 2 − 4.89e-05 に対し正則側の床は 2.06e-04 で同じ桁。
    #   だから「2 に十分近い」ではなく「2 とのずれが床と同じ桁」を門にする。
    check("★行の向きを間違えると 2 に行く(ずれは正則側の床と同じ桁)",
          abs(2.0 - cr_raw) < 10.0 * cr_flipped)

    gam = float(L.joukowski_circulation(ALPHA_DEG, centre_offset=MU))
    c_out = circulation(w, gr, 3)
    c_in = circulation(w, gr, 60)
    print("   循環 Γ = %.4f、線積分: 外周 %.4f / 内周 %.4f、流束 %.1e"
          % (gam, c_out.real, c_in.real, abs(c_out.imag)))
    rows.append(["循環は経路に依らない", "外周 / 内周", "%.4f / %.4f"
                 % (c_out.real, c_in.real), "−Γ = %.4f" % (-gam)])
    check("循環が経路に依らない(コーシー)",
          abs(c_out.real - c_in.real) < 2e-3 * abs(gam))
    check("循環がクッタ条件の Γ に一致", abs(c_out.real + gam) < 2e-3 * abs(gam))
    check("湧き出しが無い(流束 ≈ 0)", abs(c_out.imag) < 1e-2)

    b = 1.0
    a = abs(b - MU)
    beta = -np.angle(b - MU)
    alpha = np.deg2rad(ALPHA_DEG)

    def tip_speed(eps, circ):
        zeta = b + eps * np.exp(1j * np.linspace(0, 2 * np.pi, 64, endpoint=False))
        zeta = zeta[np.abs(zeta - MU) > a]
        d = zeta - MU
        dwdz = (np.exp(-1j * alpha) - a * a * np.exp(1j * alpha) / (d * d)
                + 1j * circ / (2.0 * np.pi * d))
        return float(np.abs(dwdz / (1.0 - b * b / (zeta * zeta))).max())

    eps = np.array([1e-2, 1e-3, 1e-4, 1e-5])
    kutta = np.array([tip_speed(e, gam) for e in eps])
    nokutta = np.array([tip_speed(e, 0.0) for e in eps])
    print("   後縁の速さ: クッタあり %s / 循環 0 %s"
          % (np.array2string(kutta, precision=2),
             np.array2string(nokutta, precision=1)))
    rows.append(["クッタ条件", "後縁の速さ(1e-5 まで寄る)", "%.2f" % kutta[-1],
                 "循環 0 なら %.0f" % nokutta[-1]])
    check("クッタ条件があれば後縁で速度が有限にとどまる", kutta.max() < 10.0)
    check("★対照群: 循環を 0 にすると後縁で発散する",
          nokutta[-1] / nokutta[0] > 20.0)

    figs.save_grid("flow", [np.abs(w), np.where(w == 0, 1.0, 0.0)],
                   captions=["速さ |w|(翼の中はちょうど 0)",
                             "場が 0 の領域 = 翼そのもの"],
                   ncols=2,
                   caption="迎角 %.0f 度のジューコフスキー翼まわりの非粘性流。"
                           "翼の中は「流れが無い」ではなく**厳密に 0** にしてあるので、"
                           "`field == 0` がそのまま翼の型になる(黙って nan にしない)。"
                           "外側は正則で、既存 op の CR 残差が %.1e(行を反転せずに渡すと"
                           "共役を測って %.6f = 2 − 同じ桁の床)。"
                           % (ALPHA_DEG, cr_flipped, cr_raw))
    figs.save_plot("kutta",
                   [("クッタ条件あり", eps, kutta), ("循環 0(対照群)", eps, nokutta)],
                   xlabel="後縁からの距離", ylabel="速さの最大値",
                   title="後縁が有限にとどまるのは循環がクッタ条件で選ばれているから",
                   caption="後縁は写像の特異点(dz/dζ = 0)なので、循環が正しくないと"
                           "1/√距離 で発散する。距離を 1e-2 から 1e-5 まで詰めると、"
                           "クッタ条件ありは %.2f → %.2f のまま、循環 0 は %.0f → %.0f。"
                           % (kutta[0], kutta[-1], nokutta[0], nokutta[-1]))

    print("== 6 章 揚力 —— 薄翼理論との比が厚みそのもの ==")
    angs = np.arange(-6.0, 14.1, 1.0)
    cls = np.array([2.0 * float(L.joukowski_circulation(x, centre_offset=MU))
                    / (4.0 * b) for x in angs])
    thin = 2.0 * np.pi * np.sin(np.deg2rad(angs) + beta)
    ratio = cls / np.where(np.abs(thin) < 1e-9, np.nan, thin)
    rr = float(np.nanmax(np.abs(ratio - a / b)))
    print("   CL(8 度) = %.3f、薄翼理論 %.3f、比 %.4f(a/b = %.4f、ずれ %.1e)"
          % (cls[np.argmin(np.abs(angs - 8.0))],
             thin[np.argmin(np.abs(angs - 8.0))],
             float(ratio[np.argmin(np.abs(angs - 8.0))]), a / b, rr))
    rows.append(["揚力係数 / 薄翼理論", "迎角によらず一定", "%.4f" % (a / b),
                 "a/b = %.4f" % (a / b)])
    check("★揚力と薄翼理論の比が厳密に a/b(迎角にも速さにも依らない)", rr < 1e-9)
    figs.save_plot("lift",
                   [("ジューコフスキー翼", angs, cls), ("薄翼理論 2π sin(α+β)", angs, thin)],
                   xlabel="迎角[度]", ylabel="揚力係数 CL",
                   title="厚みの効果は 1 つの数(a/b = %.4f)に落ちる" % (a / b),
                   caption="★CL = 2π(a/b)sin(α+β)。薄翼理論との比は迎角にも速さにも"
                           "よらず **a/b だけ**で決まり、実測のずれは %.1e。"
                           "厚みを 0 に近づければ薄翼理論に戻る。" % rr)

    figs.save_table("numbers",
                    ["主張", "測った量", "実測", "真値 / 期待"], rows,
                    title="複素平面の面 —— 絵ではなく数で採点した結果",
                    caption="どの行も「使った式」ではない真値で採点している: 既存 op "
                            "(cplx_winding_number / cplx_cr_residual)、Cayley の定理、"
                            "閉形式の内部判定、c=0 のジュリア集合、クッタ条件の対照群、"
                            "薄翼理論との比。")

    print("所要 %.1f s" % (time.time() - t0))
    bad = [n for n, v in ok if not v]
    assert not bad, bad
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
