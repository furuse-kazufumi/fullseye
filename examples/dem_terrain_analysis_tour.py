# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""地形解析ツアー —— 粗さ・位置指数・D8 流向・河道・地平線仰角・可視領域を、答えが数えられる地形で検算する。

    py -3.11 examples/dem_terrain_analysis_tour.py
    FULLSEYE_FIGURE_DIR=out/figs py -3.11 examples/dem_terrain_analysis_tour.py   # 図も書く

【この例が示すこと】
DEM の局所統計(``dem_roughness`` / ``dem_tpi``)、水文(``dem_flow_direction`` /
``dem_stream_network``)、見通し(``dem_horizon_angle`` / ``dem_viewshed``)の 6 op を、
**平面・柱・円錐・V 字谷・壁**という「答えを手で数えられる地形」で通す。

【グラウンドトゥルース(閉形式か、セルを数えて出る)】
1. 粗さ TRI: 1 セルあたりの勾配ベクトルが (p, q) の平面では、8 近傍差の二乗和が
   6(p²+q²) なので TRI = √(3/4)·|∇z|·cell。平坦面は 0。高さ H の柱は柱で H、隣で H/√8。
2. TPI: 平面では内側が厳密に 0(近傍平均 = 自セル)。柱は +H、その直交隣は -H/8。
   ガウス丘の頂点は amp·(1 - (4e^{-c²/2σ²} + 4e^{-c²/σ²})/8)。反転した丘(窪地)は負。
3. D8 流向: 南へ下る平面は全セルが「南(6)」、最下行は流出先なし(-1)。円錐は頂点から
   放射状(北 1 / 東 4 / 北東 2 / 南西 5)。V 字谷は両岸が谷底へ(東 4 / 西 3)、谷底は南(6)。
   ``nodata``: 欠測に隣接する窪地は ``outlet`` で欠測へ落ち、``barrier`` で -1。
4. 河道: V 字谷の谷底 i 行目の集水量は幅 W × (i+1) 個。閾値 T の河道マスクは
   「谷底かつ W(i+1) ≥ T」の行だけ —— セル単位で一致する。
5. 地平線仰角: 平坦面に高さ H の壁(1 列)を立てると、k セル手前から東を見た仰角は
   atan(H/(k·cell)) —— 一致は 1e-9 度。壁の向こうから東を見れば 0。北へ登る傾斜 s の面で
   北を見れば s、南を見れば 0(下り勾配は「地平線より下」なので 0 に張り付く)。
6. 可視領域: 平坦面の観測者(眼高 e)から距離 d0 に高さ H(< e) の壁があると、視線が
   壁の上端をかすめて地面に戻るまでの列 d0 < d < e·d0/(e-H) が隠れ、その先はまた見える。
   壁を「列 1 本すべて」にすると、この条件が**全行で列だけの式**になる。境界の ±1 列は
   視線の標本化で決まるので判定から外し、その個数を印字する。

【読み方】
各節が「地形 / op の返り / 閉形式 / 差」を印字し、閾値を超えると assert で落ちる。
図は環境変数を与えたときだけ書く。最後に所要秒数を印字する(60 秒未満が規約)。

★EXTEND: 実データを使うなら ``dem`` と ``CELL`` を差し替える(行 0 が北、単位 m)。
欠測は ``nan`` にしてから渡す(-9999 のような番兵は fail-closed で拒否される)。
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

# ★リポジトリ直下を通しておかないと ``demops`` が見つからない(この例は
#   `fullseye` を import しないので、パスフックが効かない)。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import demops                                                    # noqa: E402
import examplefig as figs                                        # noqa: E402

# D8 の並び(docstring の宣言どおり、0-7 が ``_D8`` の順)。ここに書いた表が
# 実装とずれたら例ごと落とす(索引の意味が変わったら気づけるように)。
D8 = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))
NW, N, NE, W, E, SW, S, SE = range(8)
NONE = -1                                     # 流出先なし
assert tuple(demops._D8) == D8, "D8 の並びが docstring の宣言と違う"

# ★EXTEND: セル寸法 [m]。実データでは dem_cell_size_webmercator(zoom, 緯度) で出す。
CELL = 5.0


def _big(a, k=3):
    """図に載せるためだけの最近傍拡大(小さい格子だと題が入らない)。"""
    return np.repeat(np.repeat(np.asarray(a, float), k, axis=0), k, axis=1)


def plane(h, w, cell, slope_deg, aspect_deg):
    """既知の傾斜・方位の平面。行 0 が北、方位は「下る向き」で北 0 度・東回り。"""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    g = math.tan(math.radians(slope_deg))
    a = math.radians(aspect_deg)
    return -g * ((xx * cell) * math.sin(a) + (-yy * cell) * math.cos(a))


def cone(n, cell, slope_deg, top=100.0):
    """中心が頂点の円錐。傾斜は一定、流れは放射状。"""
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    return top - math.tan(math.radians(slope_deg)) * np.hypot(yy - n // 2, xx - n // 2) * cell


def run() -> dict:
    """全節を実行し、検算した数字を dict で返す。"""
    t0 = time.perf_counter()
    out: dict = {}
    cell = CELL

    # ------------------------------------------------------------------ 1
    print("=== 1. 粗さ TRI —— 平面は √(3/4)·|∇z|·cell、柱は H ===")
    for slope_deg, aspect_deg in ((20.0, 90.0), (30.0, 225.0)):
        z = plane(31, 31, cell, slope_deg, aspect_deg)
        tri = demops.dem_roughness(z, cell)[1:-1, 1:-1]            # 縁は edge パディングの影響
        expect = math.sqrt(0.75) * math.tan(math.radians(slope_deg)) * cell
        print(f"  平面 傾斜 {slope_deg} 度・方位 {aspect_deg} 度: TRI {np.mean(tri):.6f} m"
              f"(閉形式 {expect:.6f}、最大差 {np.max(np.abs(tri - expect)):.2e})")
        assert np.max(np.abs(tri - expect)) < 1e-9
    flat = np.zeros((15, 15))
    assert np.max(demops.dem_roughness(flat, cell)) == 0.0
    H = 12.0
    pillar = flat.copy()
    pillar[7, 7] = H
    tri_p = demops.dem_roughness(pillar, cell)
    print(f"  高さ {H} m の柱: 柱 {tri_p[7, 7]:.6f}(閉形式 {H})/ 直交隣 {tri_p[7, 8]:.6f}"
          f"(閉形式 H/√8 = {H / math.sqrt(8):.6f})/ 平坦面 {tri_p[0, 0]:.1f}")
    assert abs(tri_p[7, 7] - H) < 1e-12 and abs(tri_p[7, 8] - H / math.sqrt(8)) < 1e-12
    out["tri_plane_err"] = float(np.max(np.abs(tri - expect)))

    # ------------------------------------------------------------------ 2
    print("\n=== 2. 位置指数 TPI —— 平面は 0、尾根は正、窪地は負 ===")
    z = plane(31, 31, cell, 25.0, 300.0)
    tpi = demops.dem_tpi(z, cell)[1:-1, 1:-1]
    print(f"  平面: |TPI| 最大 {np.max(np.abs(tpi)):.2e} m(閉形式 0)")
    assert np.max(np.abs(tpi)) < 1e-9
    tpi_p = demops.dem_tpi(pillar, cell)
    print(f"  柱: 柱 {tpi_p[7, 7]:.6f}(閉形式 +{H})/ 直交隣 {tpi_p[7, 8]:.6f}(閉形式 -H/8 = {-H / 8})")
    assert abs(tpi_p[7, 7] - H) < 1e-12 and abs(tpi_p[7, 8] + H / 8) < 1e-12
    amp, sigma, n = 50.0, 40.0, 41
    yy, xx = (np.mgrid[0:n, 0:n] - n // 2) * cell
    hill = amp * np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma ** 2))
    top_expect = amp * (1.0 - (4 * math.exp(-cell ** 2 / (2 * sigma ** 2))
                               + 4 * math.exp(-cell ** 2 / sigma ** 2)) / 8.0)
    top = demops.dem_tpi(hill, cell)[n // 2, n // 2]
    bottom = demops.dem_tpi(-hill, cell)[n // 2, n // 2]
    print(f"  ガウス丘の頂点 {top:.6f} m(閉形式 {top_expect:.6f})/ 反転した窪地の底 {bottom:.6f}(符号が逆)")
    assert abs(top - top_expect) < 1e-9 and abs(bottom + top_expect) < 1e-9
    out["tpi_hill_top"] = float(top)

    # ------------------------------------------------------------------ 3
    print("\n=== 3. D8 流向 —— 平面・円錐・V 字谷・欠測 ===")
    z = plane(20, 15, cell, 10.0, 180.0)                           # 南へ下る
    d = demops.dem_flow_direction(z, cell)
    print(f"  南向き平面: 内側の流向 {np.unique(d[:-1, 1:-1])}(閉形式 [S={S}])"
          f"/ 最下行 {np.unique(d[-1])}(閉形式 [{NONE}])")
    assert np.all(d[:-1, 1:-1] == S) and np.all(d[-1] == NONE)
    # 縁の列: 東西の隣が無い側は南か南斜め。南の 1 セルが最大の落差なので S のまま。
    assert np.all(d[:-1, 0] == S) and np.all(d[:-1, -1] == S)
    zc = cone(41, cell, 20.0)
    dc = demops.dem_flow_direction(zc, cell)
    probes = {(10, 20): N, (20, 30): E, (10, 30): NE, (30, 10): SW, (30, 20): S, (20, 10): W}
    got = {rc: int(dc[rc]) for rc in probes}
    print(f"  円錐(頂点 (20,20)): {got}(閉形式 {probes})")
    assert got == probes
    # 欠測: 窪地が欠測に隣接するときだけ方針で答えが変わる。
    pit = np.zeros((9, 9))
    pit[4, 4] = np.nan
    pit[4, 3] = -1.0                                               # 欠測の西隣が窪地
    d_out = demops.dem_flow_direction(pit, cell, nodata="outlet")
    d_bar = demops.dem_flow_direction(pit, cell, nodata="barrier")
    print(f"  欠測の隣の窪地: outlet → {d_out[4, 3]}(閉形式 E={E}、欠測へ出る)"
          f"/ barrier → {d_bar[4, 3]}(閉形式 {NONE})/ 欠測セル自身 {d_out[4, 4]}, {d_bar[4, 4]}")
    assert d_out[4, 3] == E and d_bar[4, 3] == NONE
    assert d_out[4, 4] == NONE and d_bar[4, 4] == NONE
    try:
        demops.dem_flow_direction(pit, cell)                       # 既定 nodata="error"
        raise AssertionError("欠測入りの DEM が既定で通ってしまった")
    except ValueError:
        print("  欠測入り・既定(error): 拒否(方針を明示しないと通らない)")
    # ★正直な観察: 斜面の途中に欠測があるとき、その北隣は outlet でも欠測へは落ちず
    #   南西(有限の落差がある方向)へ行く。実装は「他に下る先が無いときだけ欠測へ」で、
    #   docstring の「欠測へ向かう流れを許す」より狭い。ここでは印字だけで assert しない。
    zs = plane(21, 21, cell, 10.0, 180.0)
    zs[10, 10] = np.nan
    ds_out = demops.dem_flow_direction(zs, cell, nodata="outlet")
    print(f"  斜面の途中の欠測 (10,10) の北隣 (9,10): outlet → {ds_out[9, 10]}"
          f"(S={S} なら欠測へ、SW={SW} なら迂回)")
    out["flow_dir_cone_ok"] = got == probes

    # ------------------------------------------------------------------ 4
    print("\n=== 4. 河道 —— V 字谷の集水量は数えられる ===")
    hv, wv, jc = 60, 41, 20
    g_valley, g_axis = 0.2, 0.05                                   # 谷壁 > 谷底の縦断勾配
    yy, xx = np.mgrid[0:hv, 0:wv].astype(np.float64)
    valley = g_valley * np.abs(xx - jc) * cell - g_axis * yy * cell
    dv = demops.dem_flow_direction(valley, cell)
    expect_dir = np.where(xx < jc, E, np.where(xx > jc, W, S)).astype(int)
    expect_dir[-1, jc] = NONE                                      # 谷底の最下行は流出
    mism = int(np.sum(dv != expect_dir))
    print(f"  流向の不一致セル {mism} / {dv.size}(両岸は谷底へ、谷底は南へ)")
    assert mism == 0
    acc = demops.dem_flow_accumulation(valley, cell)
    axis_expect = wv * (np.arange(hv) + 1)
    print(f"  谷底の集水量 先頭 {acc[:3, jc].astype(int)} … 末尾 {acc[-1, jc]:.0f}"
          f"(閉形式 W(i+1): {axis_expect[:3]} … {axis_expect[-1]})")
    assert np.array_equal(acc[:, jc], axis_expect)
    T = 500.0
    stream = demops.dem_stream_network(valley, cell, threshold_cells=T)
    expect_stream = np.zeros((hv, wv))
    expect_stream[axis_expect >= T, jc] = 1.0
    diff = int(np.sum(stream != expect_stream))
    first = int(np.argmax(stream[:, jc] > 0))
    print(f"  閾値 {T:.0f} セルの河道: 谷底 {first} 行目から(閉形式 ceil({T:.0f}/{wv})-1 = "
          f"{math.ceil(T / wv) - 1})、河道セル {int(stream.sum())} 個、不一致 {diff}")
    assert diff == 0
    # 閾値を越えないと河道は 1 セルも出ない。
    assert demops.dem_stream_network(valley, cell, threshold_cells=hv * wv + 1).sum() == 0
    figs.save_grid("valley_stream",
                   [_big(valley, 4), _big(dv.astype(float), 4), _big(np.log10(acc), 4), _big(stream, 4)],
                   ["標高", "D8 流向", "集水量 log10", "河道"],
                   ncols=2, title="V 字谷 —— 流向・集水量・河道がセル単位で数えられる",
                   caption="流向は 0-7(谷底は 6=南)。谷底 i 行目の集水量は幅 W×(i+1)。"
                           f"河道は閾値 {T:.0f} セルを越えた行から始まる。")
    out["stream_cells"] = int(stream.sum())

    # ------------------------------------------------------------------ 5
    print("\n=== 5. 地平線仰角 —— 壁と傾斜面 ===")
    hw, ww, jw, Hw = 21, 41, 25, 30.0
    wall = np.zeros((hw, ww))
    wall[:, jw] = Hw                                               # 1 列すべてが壁
    hz_e = demops.dem_horizon_angle(wall, cell, azimuth_deg=90.0)    # 東を見る
    hz_w = demops.dem_horizon_angle(wall, cell, azimuth_deg=270.0)   # 西を見る
    k = np.arange(1, jw + 1)                                       # 壁までの列数
    expect_e = np.degrees(np.arctan(Hw / (k * cell)))              # 列 jw-k から東を見た仰角
    err_e = np.max(np.abs(hz_e[:, jw - k] - expect_e[None, :]))
    kw = np.arange(1, ww - jw)
    expect_w = np.degrees(np.arctan(Hw / (kw * cell)))
    err_w = np.max(np.abs(hz_w[:, jw + kw] - expect_w[None, :]))
    print(f"  壁(高さ {Hw} m)の手前から東: 1 セル手前 {hz_e[5, jw - 1]:.4f} 度(閉形式 "
          f"{expect_e[0]:.4f})/ 10 セル手前 {hz_e[5, jw - 10]:.4f}({expect_e[9]:.4f})/ 最大差 {err_e:.2e}")
    print(f"  壁の向こうから西: 最大差 {err_w:.2e} / 壁の向こうから東(平坦): 最大 {np.max(hz_e[:, jw + 1:]):.1f}")
    assert err_e < 1e-9 and err_w < 1e-9
    assert np.max(hz_e[:, jw + 1:]) == 0.0 and np.max(hz_w[:, :jw]) == 0.0
    # 距離を切ると、壁が届かないセルでは 0 になる。
    hz_cut = demops.dem_horizon_angle(wall, cell, azimuth_deg=90.0, max_distance_m=5 * cell)
    print(f"  max_distance 5 セル: 6 セル手前 {hz_cut[5, jw - 6]:.1f}(閉形式 0)/ 5 セル手前 "
          f"{hz_cut[5, jw - 5]:.4f}({expect_e[4]:.4f})")
    assert hz_cut[5, jw - 6] == 0.0 and abs(hz_cut[5, jw - 5] - expect_e[4]) < 1e-9
    s_deg = 15.0
    zs = plane(31, 31, cell, s_deg, 180.0)                         # 南へ下る = 北へ登る
    hz_n = demops.dem_horizon_angle(zs, cell, azimuth_deg=0.0)[1:, :]
    hz_s = demops.dem_horizon_angle(zs, cell, azimuth_deg=180.0)
    hz_e2 = demops.dem_horizon_angle(zs, cell, azimuth_deg=90.0)
    print(f"  北へ登る傾斜 {s_deg} 度の面: 北 {np.mean(hz_n):.6f}(閉形式 {s_deg}、最大差 "
          f"{np.max(np.abs(hz_n - s_deg)):.2e})/ 南 {np.max(hz_s):.1f}(0)/ 東 {np.max(np.abs(hz_e2)):.1e}(0)")
    assert np.max(np.abs(hz_n - s_deg)) < 1e-9 and np.max(hz_s) == 0.0 and np.max(np.abs(hz_e2)) < 1e-9
    out["horizon_wall_err_deg"] = float(max(err_e, err_w))

    # ------------------------------------------------------------------ 6
    print("\n=== 6. 可視領域 —— 壁の影は列だけで決まる ===")
    hv2, wv2 = 41, 81
    r0, c0 = 20, 10                                                # 観測点
    jw2, Hw2, eye = 30, 5.5, 10.0                                  # 壁の列・高さ、眼高
    wall2 = np.zeros((hv2, wv2))
    wall2[:, jw2] = Hw2
    vis = demops.dem_viewshed(wall2, cell, (r0, c0), observer_height_m=eye)
    assert vis[r0, c0] == 1.0, "観測点自身は常に可視"
    d0 = jw2 - c0                                                  # 壁までの列数
    d_star = eye * d0 / (eye - Hw2)                                # 影が終わる列数(閉形式)
    dx = np.arange(wv2)[None, :] - c0
    # 標本化で壁に当たる位置が ±0.5 列ずれるので、影の終わりも e(d0±0.5)/(e-H) の幅を持つ。
    lo = eye * (d0 - 0.5) / (eye - Hw2)
    hi = eye * (d0 + 0.5) / (eye - Hw2)
    hidden_sure = (dx > d0) & (dx < lo)                            # どちらの端でも隠れる
    visible_sure = (dx <= d0) | (dx > hi)                          # どちらの端でも見える
    ambiguous = ~(hidden_sure | visible_sure)
    n_amb = int(ambiguous.sum())
    bad_hidden = int(np.sum(vis[np.broadcast_to(hidden_sure, vis.shape)] != 0.0))
    bad_visible = int(np.sum(vis[np.broadcast_to(visible_sure, vis.shape)] != 1.0))
    print(f"  眼高 {eye} m・壁 {Hw2} m・壁まで {d0} 列: 影は列 {d0 + 1} から {math.floor(d_star)} まで"
          f"(閉形式 e·d0/(e-H) = {d_star:.2f})")
    print(f"  隠れるはずのセルで見えた {bad_hidden} / 見えるはずのセルで隠れた {bad_visible}"
          f" / 標本化で決まる境界セル {n_amb}(判定から除外)")
    assert bad_hidden == 0 and bad_visible == 0
    row = "".join("#" if v else "." for v in vis[r0])
    print(f"  観測者の行: {row}")
    # 壁より高い眼高でなければ、壁の向こうは全部隠れる(視線が上向きになる)。
    vis_low = demops.dem_viewshed(wall2, cell, (r0, c0), observer_height_m=1.7)
    print(f"  眼高 1.7 m: 壁の向こうの可視セル {int(vis_low[:, jw2 + 1:].sum())}(閉形式 0)"
          f"/ 手前 {int(vis_low[:, :jw2].sum())} / {hv2 * jw2}(閉形式 全部)")
    assert vis_low[:, jw2 + 1:].sum() == 0 and vis_low[:, :jw2].sum() == hv2 * jw2
    # 距離で切る: 半径 10 セルの円板の外は 0。
    vis_cut = demops.dem_viewshed(np.zeros((hv2, wv2)), cell, (r0, c0), max_distance_m=10 * cell)
    yy2, xx2 = np.mgrid[0:hv2, 0:wv2]
    inside = np.hypot(yy2 - r0, xx2 - c0) <= 10.0
    print(f"  平坦面・半径 10 セル: 可視 {int(vis_cut.sum())}(閉形式 {int(inside.sum())})")
    assert np.array_equal(vis_cut, inside.astype(float))
    figs.save_grid("viewshed_wall",
                   [_big(wall2, 2), _big(vis, 2), _big(vis_low, 2)],
                   ["壁(列 1 本、高さ 5.5 m)", "眼高 10 m: 影の先が見える", "眼高 1.7 m: 向こうは全部隠れる"],
                   ncols=3, title="可視領域 —— 壁の影の長さは e·d0/(e-H) で決まる",
                   caption="観測点は左端の中央。境界の 1〜2 列は視線の標本化で決まる。")
    out["viewshed_ambiguous_cells"] = n_amb

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    out["elapsed_s"] = time.perf_counter() - t0
    return out


if __name__ == "__main__":
    r = run()
    print(f"\n所要 {r['elapsed_s']:.2f} 秒")
    print("PASS")
