# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""shape2d_morph_descriptor_tour — XLD 輪郭 → 不変記述子 → 対応点ワープ(区分アフィン / TPS)を真値つきで一巡する。

    py -3.11 examples/shape2d_morph_descriptor_tour.py

【この例が示すこと】
輪郭抽出の出力(XLD dict ``{"shape", "cs"}``)から ``fourierdesc.from_xld`` で点列を
取り出し、``invariants`` で回転・拡大・移動・始点に不変な記述子を作り、同じ輪郭点を
**対応点**として ``imagemorph`` の 2 つのワープ(``warp_piecewise_affine`` /
``warp_tps_image``)に渡す。四隅の固定は ``add_frame_corners``。

【グラウンドトゥルース(すべて assert で落とす)】
1. ``from_xld`` は ``cs[i]`` を **(row, col)** のまま (N,2) float で返す(画素単位で同一)。
2. 円(半径 10)の第 1 高調波不変量は (10, 10)、高次は 1 % 未満。楕円を 37 度回して 1.8 倍し
   移動して始点を 50 点ずらしても ``invariants(scale_invariant=True)`` は 1e-9 で同じ。
   円と楕円の記述子距離はそれより桁違いに大きい。座標を (row,col)↔(x,y) と入れ替えても
   不変量は同じ(特異値は鏡映に不変)—— **記述子は座標順の事故に気づけない**。
3. ``add_frame_corners`` は入力の後ろに四隅 + 辺の中点 8 点をこの順で足す(閉形式)。
4. 対応点が同じ(src == dst)なら両ワープとも恒等(最大差 1e-12 / 1e-8)。
5. 全対応点(四隅込み)を (7, -5) 平行移動すると、円板は画素単位でそのぶん動く
   (区分アフィンは厳密、TPS はアフィン再現性により 1e-6)。
6. 中央の 1 点だけを (+9, -6) 動かすと、その点にあった輝点の最大値位置が着地先へ移り
   (1 px 以内)、他の対応点の画素値は変わらない(制御点上は厳密)。
7. 輪郭 32 点を中心から 1.25 倍へ動かすと円板面積は 1.25^2 倍(5 % 以内)。
   同じ点を **(row, col) のまま**渡す(入れ替え忘れ)と、円板が中心から外れた位置に
   あるため面積がほぼ変わらない —— 例外は出ないのに結果が違う(座標順の落とし穴)。

【読み方】各節の印字は「真値 / 実測 / 差」。PASS 行が出れば全部通っている。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fourierdesc as F       # noqa: E402  楕円フーリエ記述子 + XLD 取り出し
import imagemorph as IM       # noqa: E402  対応点駆動ワープ

H, W = 96, 128                # 非正方(row/col の取り違えが形で出る)


def _ellipse_rc(cy, cx, a, b, n=240, deg=0.0, start=0):
    """(row, col) 順の楕円輪郭。a=col 方向半径、b=row 方向半径、deg で回転、start で始点をずらす。"""
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    x, y = a * np.cos(t), b * np.sin(t)
    th = np.radians(deg)
    xr, yr = x * np.cos(th) - y * np.sin(th), x * np.sin(th) + y * np.cos(th)
    rc = np.column_stack([cy + yr, cx + xr])
    return np.roll(rc, -start, axis=0)


def _disk(cx, cy, r):
    """(x, y) 中心 (cx, cy)・半径 r の円板画像(値 1)。"""
    yy, xx = np.mgrid[0:H, 0:W]
    return (((xx - cx) ** 2 + (yy - cy) ** 2) < r * r).astype(np.float64)


def section_xld_descriptor():
    """1-2. XLD 取り出しと不変記述子。"""
    # 輪郭抽出 op の出力と同じ形の XLD dict(0 番: 楕円、1 番: 円)。
    # ★EXTEND: 自分の輪郭抽出結果(``{"shape": (H,W), "cs": [ (N,2) (row,col), ... ]}``)に差し替える
    ell = _ellipse_rc(48.0, 64.0, 30.0, 12.0)
    circ = _ellipse_rc(60.0, 30.0, 10.0, 10.0, n=160)
    xld = {"shape": (H, W), "cs": [ell, circ]}

    p0 = F.from_xld(xld, 0)                             # (row, col) のまま返る
    p1 = F.from_xld(xld, 1)
    same = np.array_equal(p0, ell) and np.array_equal(p1, circ) and p0.dtype == np.float64
    print(f"1) from_xld: cs[0]/cs[1] と画素単位で同一 {same}、形 {p0.shape} / {p1.shape}(row, col 順)")
    assert same and p0.shape == (240, 2) and p1.shape == (160, 2)

    # 円: 第 1 高調波 = (r, r)、高次 ≈ 0(円だけが弧長パラメータで厳密に 1 高調波)
    mc = F.elliptic_fourier(p1, 8)
    inv_c = F.invariants(mc, scale_invariant=False)
    hi = float(inv_c[1:].max() / inv_c[0, 0])
    print(f"2) 円の不変量: 第 1 高調波 ({inv_c[0, 0]:.3f}, {inv_c[0, 1]:.3f})(真値 10, 10)、"
          f"高次/第 1 の最大 {hi:.4f}")
    assert np.abs(inv_c[0] - 10.0).max() < 0.1 and hi < 0.01

    # 楕円: 回転 37 度・1.8 倍・移動・始点 50 点ずらし → スケール不変記述子は同じ
    me = F.elliptic_fourier(p0, 12)
    moved = _ellipse_rc(20.0, 40.0, 30.0 * 1.8, 12.0 * 1.8, deg=37.0, start=50)
    mm = F.elliptic_fourier(moved, 12)
    inv_e, inv_m = F.invariants(me), F.invariants(mm)   # scale_invariant=True(既定)
    d_same = float(np.abs(inv_e - inv_m).max())
    d_diff = F.descriptor_distance(me, mc, 8)
    inv_xy = F.invariants(F.elliptic_fourier(p0[:, ::-1], 12))   # (x, y) に入れ替えて
    d_swap = float(np.abs(inv_e - inv_xy).max())
    print(f"   楕円の不変性: 回転+拡大+移動+始点ずらし後の差 {d_same:.1e} / 円との距離 {d_diff:.3f}"
          f"(桁違い)/ 座標順を入れ替えても差 {d_swap:.1e}(鏡映に不変 = 座標順の事故は見えない)")
    assert d_same < 1e-9 and d_diff > 1e4 * max(d_same, 1e-15) and d_swap < 1e-9
    # 楕円の第 1 高調波は (a, b) に近いが厳密ではない(弧長パラメータの楕円は 1 高調波ではない)
    inv_e_raw = F.invariants(me, scale_invariant=False)[0]
    print(f"   楕円の第 1 高調波 ({inv_e_raw[0]:.2f}, {inv_e_raw[1]:.2f}) vs 幾何半径 (30, 12): "
          f"弧長パラメータ化のため高次に漏れるので一致しない(honest)")
    return {"from_xld_exact": same, "circle_first_harmonic": inv_c[0].tolist(),
            "invariance_err": d_same, "circle_vs_ellipse": d_diff, "swap_err": d_swap,
            "xld": xld}


def section_warp(xld):
    """3-7. 対応点ワープ。"""
    # 3) 四隅 + 辺の中点(閉形式)
    ctrl = np.array([[40.0, 30.0], [80.0, 30.0], [60.0, 60.0]])
    P = IM.add_frame_corners(ctrl, (H, W))
    x2, y2 = float(W - 1), float(H - 1)
    frame_want = np.array([[0, 0], [x2 / 2, 0], [x2, 0], [0, y2 / 2], [x2, y2 / 2],
                           [0, y2], [x2 / 2, y2], [x2, y2]], float)
    ok3 = P.shape == (11, 2) and np.array_equal(P[:3], ctrl) and np.array_equal(P[3:], frame_want)
    print(f"3) add_frame_corners: 3 点 → {P.shape[0]} 点、末尾 8 点が四隅+辺中点の閉形式と一致 {ok3}")
    assert ok3

    # 4) 恒等
    img = _disk(52.0, 44.0, 14.0) * 0.8 + 0.1
    e_aff = float(np.abs(IM.warp_piecewise_affine(img, P, P) - img).max())
    e_tps = float(np.abs(IM.warp_tps_image(img, P, P) - img).max())
    print(f"4) src == dst の恒等: 区分アフィン 最大差 {e_aff:.1e} / TPS {e_tps:.1e}")
    assert e_aff < 1e-12 and e_tps < 1e-8

    # 5) 全対応点を平行移動 → 円板が画素単位で動く(内側で比較)
    tx, ty = 7, -5
    src = IM.add_frame_corners(ctrl, (H, W))
    dst = src + np.array([tx, ty], float)
    want = np.full_like(img, 0.1)
    want[max(0, ty):H + min(0, ty), max(0, tx):W + min(0, tx)] = \
        img[max(0, -ty):H + min(0, -ty), max(0, -tx):W + min(0, -tx)]
    inner = (slice(8, H - 8), slice(8, W - 8))           # 動いた凸包の外(恒等になる縁)は除く
    e5a = float(np.abs(IM.warp_piecewise_affine(img, src, dst)[inner] - want[inner]).max())
    e5t = float(np.abs(IM.warp_tps_image(img, src, dst)[inner] - want[inner]).max())
    print(f"5) 全点 ({tx}, {ty}) 平行移動: 円板の内側の最大差 区分アフィン {e5a:.1e} / TPS {e5t:.1e}")
    assert e5a < 1e-12 and e5t < 1e-6

    # 6) 1 点だけ動かす: 輝点が着地先へ移り、他の制御点の画素は変わらない
    gy, gx = np.mgrid[0:H, 0:W]
    grid = np.array([[x, y] for y in (24.0, 48.0, 72.0) for x in (32.0, 64.0, 96.0)])
    src6 = IM.add_frame_corners(grid, (H, W))
    dst6 = src6.copy()
    dst6[4] += (9.0, -6.0)                                # 中央 (64,48) → (73,42)
    spot = np.exp(-((gx - 64.0) ** 2 + (gy - 48.0) ** 2) / (2 * 3.0 ** 2))
    others = [i for i in range(len(src6)) if i != 4]
    res6 = {}
    for name, fn in (("affine", IM.warp_piecewise_affine), ("tps", IM.warp_tps_image)):
        out = fn(spot, src6, dst6)
        py, px = np.unravel_index(int(np.argmax(out)), out.shape)
        land = float(np.hypot(px - 73.0, py - 42.0))
        keep = float(max(abs(out[int(y), int(x)] - spot[int(y), int(x)]) for x, y in src6[others]))
        res6[name] = (land, keep, float(out.max()))
        print(f"6) {name:6s}: 輝点の最大値位置 ({px}, {py}) 真値 (73, 42) → ずれ {land:.2f} px、"
              f"他の制御点の画素差 {keep:.1e}、最大値 {out.max():.4f}(元 1.0)")
        assert land <= 1.0 and keep < 1e-9 and out.max() > 0.95

    # 7) 輪郭点を対応点に: (row,col) → (x,y) の入れ替えが要る
    circ_rc = F.from_xld(xld, 1)[::5]                     # 円輪郭 32 点(row, col)
    cy, cx = 60.0, 30.0
    disk = _disk(cx, cy, 10.0)
    pts_xy = circ_rc[:, ::-1]                             # ★正しい: (row,col) → (x,y)
    src7 = IM.add_frame_corners(pts_xy, (H, W))
    dst7 = src7.copy()
    dst7[:len(pts_xy)] = np.array([cx, cy]) + 1.25 * (pts_xy - np.array([cx, cy]))
    area0 = float(disk.sum())
    area_ok = float((IM.warp_piecewise_affine(disk, src7, dst7) > 0.5).sum())
    area_tps = float((IM.warp_tps_image(disk, src7, dst7) > 0.5).sum())
    src_bad = IM.add_frame_corners(circ_rc, (H, W))       # ★間違い: (row,col) のまま
    dst_bad = src_bad.copy()
    dst_bad[:len(circ_rc)] = np.array([cy, cx]) + 1.25 * (circ_rc - np.array([cy, cx]))
    area_bad = float((IM.warp_piecewise_affine(disk, src_bad, dst_bad) > 0.5).sum())
    print(f"7) 輪郭 32 点を 1.25 倍へ: 面積比 区分アフィン {area_ok / area0:.3f} / TPS {area_tps / area0:.3f}"
          f"(真値 {1.25 ** 2:.4f})。(row,col) のまま渡すと {area_bad / area0:.3f} —— 例外は出ず円板は動かない")
    assert abs(area_ok / area0 - 1.5625) < 0.08 and abs(area_tps / area0 - 1.5625) < 0.08
    assert abs(area_bad / area0 - 1.0) < 0.05
    return {"frame_ok": ok3, "identity_err": (e_aff, e_tps), "translate_err": (e5a, e5t),
            "landing": res6, "area_ratio": (area_ok / area0, area_tps / area0),
            "area_ratio_wrong_order": area_bad / area0}


def run() -> dict:
    """全 7 節を回し、真値との照合結果を返す(失敗は assert で落ちる)。"""
    t0 = time.perf_counter()
    out = section_xld_descriptor()
    xld = out.pop("xld")
    out.update(section_warp(xld))
    out["elapsed_s"] = time.perf_counter() - t0
    return out


def main():
    r = run()
    print(f"\nPASS: from_xld / invariants / add_frame_corners / warp_piecewise_affine / warp_tps_image を"
          f"真値つきで一巡(不変量 1e-9、恒等・平行移動は画素単位、1 点の着地 1 px 以内、面積比 1.25^2)。"
          f" 実行 {r['elapsed_s']:.2f} 秒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
