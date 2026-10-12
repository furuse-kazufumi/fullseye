# -*- coding: utf-8 -*-
"""事例: 柔らかい手首のペグ挿入を手首カメラと指の触覚で読む(運転の台帳 op ギャラリー: pegsim / pegtactile)

平たく言うと:
  ペグを穴に差し込むロボットの PoC は、手首の RGB-D カメラで「穴の中心」「ペグの先端」「手首のたわみ」を測り、
  2 本指の触覚の膜で「どこが当たっているか」を読む。その部品を、**真値が分かる合成の世界**で 1 本ずつ呼ぶ。
  合成 RGB-D(:func:`pegsim.peg_synthetic_rgbd`)は解析的なレイキャストなので、穴とペグの真の位置が分かっている
  (MuJoCo は要らない)。各行に「何を期待し、何が出て、合ったか」を印字し、外れたら exit 1。

確かめ方(op ごとの真値):
  * coverage_edge_points       —— 16 倍の超標本で描いた円盤の縁の点が、真の円から 0.1 px 以内、円の当てはめで中心 0.01 px
  * cylinder_fit_known_radius  —— 軸が既知の半円柱の格子点から、ずらした初期値で出発して軸を 1e-6 rad で戻す
  * hole_centre_from_rgbd      —— 合成 RGB-D で穴の中心(世界の原点)のカメラ座標と半径 R + 面取り(6.2 mm)
  * peg_tip_from_rgbd          —— ペグ先端の投影: 横 ≤ 0.1 px、軸方向 ≤ 1 px(影の端 1 画素から読む限界、docstring の正直な値)
  * insertion_grid_summary     —— 手で作った 12 行の成功表から、補正あり/なしの成功率・全部成功する最大の ε₀ を手計算と照合
  * contact_candidates         —— 穴の中央で鉛直なら触れる候補なし / −x の壁に寄せると −x 側の縁だけ / 二点接触なら口の縁は +x
  * pad_shear_asymmetry        —— 同じ向きのせん断は偶力 0、逆向きは純粋な偶力 1、共通 = (q_R + q_L)/2 の手計算
  * wrist_deflection_from_rgbd —— 2° 傾けたペグの軸がヒンジの高さを通る点(手計算)と傾き 2°

    py -3.11 examples/gallery_drive_peg.py
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402

import camera  # noqa: E402
import measure as FM  # noqa: E402
import pegsim as PS  # noqa: E402
import pegtactile as PT  # noqa: E402

ROWS: list = []
DEG = math.pi / 180.0
KP = PS.peg_params()


def check(op: str, what: str, expected: str, got: str, ok: bool) -> None:
    """表の 1 行を貯める(何を期待し、何が出て、合ったか)。"""
    ROWS.append((op, what, expected, got, bool(ok)))


def _aa_disc(H, W, cy, cx, r, ss=16, bright=200.0, dark=20.0):
    """16 倍超標本の円盤(内側 dark・外側 bright)。被覆率で混ぜた灰色画像と、画素中心で割った内外マスク。"""
    yy, xx = np.mgrid[0:H * ss, 0:W * ss]
    y = (yy + 0.5) / ss - 0.5
    x = (xx + 0.5) / ss - 0.5
    inside = ((y - cy) ** 2 + (x - cx) ** 2) <= r * r
    cov = inside.reshape(H, ss, W, ss).mean(axis=(1, 3))
    gray = bright * (1 - cov) + dark * cov
    yi, xi = np.mgrid[0:H, 0:W]
    d = np.hypot(yi - cy, xi - cx)
    return gray, d > r, d <= r


def _half_cylinder(axis_pt, axis, r, n_len=12, n_ang=15):
    """カメラから見える側の半円柱の格子点(一様乱数でなく構造のある入力)。"""
    axis = np.asarray(axis, float) / np.linalg.norm(axis)
    e1 = np.cross(axis, [0, 1.0, 0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    t = np.linspace(0, 0.03, n_len)
    ph = np.linspace(-np.pi / 2, np.pi / 2, n_ang)
    T, PH = np.meshgrid(t, ph, indexing="ij")
    return (np.asarray(axis_pt)[None, :] + T.ravel()[:, None] * axis[None, :]
            + r * np.cos(PH).ravel()[:, None] * e1[None, :] + r * np.sin(PH).ravel()[:, None] * e2[None, :])


def demo_geometry() -> None:
    cy, cx, r = 60.37, 70.81, 25.3
    gray, outside_px, inside_px = _aa_disc(120, 140, cy, cx, r)
    uv = PS.coverage_edge_points(gray, outside_px, inside_px)          # 明るい側(板)が inside、暗い円盤(穴)が outside
    rad = np.hypot(uv[:, 1] - cy, uv[:, 0] - cx) - r
    check("coverage_edge_points", f"反エイリアスの円盤(r = {r} px)の縁 {len(uv)} 点", "真の円から < 0.1 px、平均 < 0.01 px",
          f"最大 {np.abs(rad).max():.3f} px、平均 {rad.mean():+.4f} px", np.abs(rad).max() < 0.1 and abs(rad.mean()) < 0.01)
    c = FM.fit_circle(np.column_stack([uv[:, 1], uv[:, 0]]))
    err = max(abs(c["cy"] - cy), abs(c["cx"] - cx), abs(c["r"] - r))
    check("coverage_edge_points", "その点で円を当てる(measure.fit_circle)", f"中心 ({cx}, {cy})・半径 {r} ± 0.01 px",
          f"({c['cx']:.4f}, {c['cy']:.4f})、{c['r']:.4f}", err < 0.01)

    axis = np.array([0.03, 0.0, 1.0])
    axis /= np.linalg.norm(axis)
    c0 = np.array([0.002, -0.001, 0.09])
    pts = _half_cylinder(c0, axis, 5e-3)
    a0 = axis + np.array([0.02, 0.01, 0.0])
    fit = PS.cylinder_fit_known_radius(pts, 5e-3, c0 + np.array([0.3e-3, -0.2e-3, 0.0]), a0)
    ang = math.acos(min(1.0, abs(float(fit["axis"] @ axis))))
    d = fit["axis_point"] - c0
    off = float(np.linalg.norm(d - (d @ axis) * axis))
    check("cylinder_fit_known_radius", "半円柱 180 点(初期の軸を 1.3° ずらす)", "軸 < 1e-6 rad、軸の位置 < 1e-7 m",
          f"軸の角 {ang:.1e} rad、位置 {off:.1e} m、rms {fit['rms']:.1e}", ang < 1e-6 and off < 1e-7)


def demo_rgbd() -> None:
    tip = np.array([0.002, 0.001, 0.010])
    th = 2.0 * DEG
    axis = np.array([math.sin(th), 0.0, math.cos(th)])
    syn = PS.peg_synthetic_rgbd(KP, tip, axis)
    rgb, depth, K, R, t = syn["rgb"], syn["depth"], syn["K"], syn["R"], syn["t"]
    hole = PS.hole_centre_from_rgbd(rgb, depth, K)
    want = R @ np.zeros(3) + t                                           # 穴の中心 = 世界の原点
    err = float(np.linalg.norm(hole["centre_cam"] - want))
    check("hole_centre_from_rgbd", "穴の中心(カメラ座標)", np.array2string(want * 1e3, precision=4) + " mm",
          f"誤差 {err * 1e6:.2f} µm", err < 5e-6)
    r_want = KP["R"] + KP["chamfer"]
    check("hole_centre_from_rgbd", "見える縁の半径", f"R + 面取り = {r_want * 1e3:.2f} mm", f"{hole['radius'] * 1e3:.4f} mm",
          abs(hole["radius"] - r_want) < 0.01e-3)
    pk = PS.peg_tip_from_rgbd(rgb, depth, K)
    uv_true, _ = camera.project_points(tip[None, :], K, R, t)
    du = pk["uv"] - uv_true[0]
    check("peg_tip_from_rgbd", "ペグ先端の投影(横 = 画像の u、軸方向 = v)", "横 ≤ 0.1 px、軸方向 ≤ 1 px(影の端の限界)",
          f"Δu = {du[0]:+.3f} px、Δv = {du[1]:+.3f} px", abs(du[0]) < 0.1 and abs(du[1]) < 1.0)
    ang = math.degrees(math.acos(min(1.0, abs(float(pk["axis"] @ (R @ axis))))))
    check("peg_tip_from_rgbd", "ペグの軸の向き", "真の軸と < 0.3°", f"{ang:.3f}°", ang < 0.3)

    tip2 = np.array([1.0e-3, 0.5e-3, 0.004])
    ax2 = np.array([math.sin(2 * DEG), 0.0, math.cos(2 * DEG)])
    sy = PS.peg_synthetic_rgbd(KP, tip_xyz=tip2, axis=ax2, width=160, height=120, supersample=2)
    hz = 0.02
    wd = PT.wrist_deflection_from_rgbd(sy["rgb"], sy["depth"], sy["K"], sy["R_cam_to_world"], -sy["R"].T @ sy["t"],
                                       np.zeros(3), KP["r"], hinge_z=hz)
    want2 = tip2 + (hz - tip2[2]) / ax2[2] * ax2                       # 軸の直線がヒンジの高さを通る点
    e2 = math.hypot(wd["dx"] - want2[0], wd["dy"] - want2[1])
    check("wrist_deflection_from_rgbd", "ヒンジの高さ 20 mm での横ずれ (Δx, Δy)",
          f"({want2[0] * 1e3:.4f}, {want2[1] * 1e3:.4f}) mm ± 30 µm", f"({wd['dx'] * 1e3:.4f}, {wd['dy'] * 1e3:.4f}) mm", e2 < 30e-6)
    check("wrist_deflection_from_rgbd", "傾き θ_y", "2° ± 0.1°", f"{math.degrees(wd['tilt_y']):.4f}°", abs(wd["tilt_y"] - 2 * DEG) < 0.1 * DEG)


def demo_summary_contact() -> None:
    rows = []
    for corr in (False, True):
        for e in (0.0, 1.0, 2.0):
            for tl in (0.0, 2.0):
                rows.append({"eps_mm": e, "tilt_deg": tl, "correct": corr, "success": corr or e <= 1.0})
    s = PS.insertion_grid_summary(rows)
    check("insertion_grid_summary", "補正なし: ε₀ ≤ 1 mm だけ成功(6 行)", "成功率 [[1,1],[1,1],[0,0]]、4/6、全部成功の最大 ε₀ = 1",
          f"{s['rate'][False].tolist()}、{s['success_count'][False]}、{s['max_eps_all_ok'][False]}",
          np.array_equal(s["rate"][False], [[1, 1], [1, 1], [0, 0]]) and s["success_count"][False] == (4, 6)
          and s["max_eps_all_ok"][False] == 1.0)
    check("insertion_grid_summary", "補正あり: 全部成功(6 行)", "6/6、全部成功の最大 ε₀ = 2", f"{s['success_count'][True]}、{s['max_eps_all_ok'][True]}",
          s["success_count"][True] == (6, 6) and s["max_eps_all_ok"][True] == 2.0)

    a = np.array([0.0, 0.0, 1.0])
    centred = PT.contact_candidates(KP, [0.0, 0.0, -5e-3], a)
    check("contact_candidates", f"穴の中央で鉛直(隙間 {(KP['R'] - KP['r']) * 1e3:.1f} mm)", "触れる候補なし",
          f"縁 {int(centred['rim_ok'].sum())}、口 {int(centred['mouth_ok'].sum())}", not centred["rim_ok"].any() and not centred["mouth_ok"].any())
    touching = PT.contact_candidates(KP, [-(KP["R"] - KP["r"]), 0.0, -5e-3], a)
    ok = touching["tip_rim"][touching["rim_ok"]]
    check("contact_candidates", "−x の壁に寄せた鉛直のペグ", "−x 側の縁だけ・半径 ≥ R",
          f"{len(ok)} 点、x の最大 {ok[:, 0].max() * 1e3:.3f} mm" if len(ok) else "0 点",
          len(ok) >= 1 and ok[:, 0].max() < 0 and np.hypot(ok[:, 0], ok[:, 1]).max() >= KP["R"] - 1e-9)
    th = 3.0 * DEG
    ww = PT.whitney_wrench(KP, "two_point", th, KP["chamfer"] + PS.two_point_depth(KP, th), 0.3, 0.6, 0.78)
    both = PT.contact_candidates(KP, ww["tip"], ww["axis"])
    mx = both["mouth"][both["mouth_ok"]]
    check("contact_candidates", "3° 傾けた二点接触(Whitney の閉形式)", "先端の縁と口の縁の両方、口は +x 側",
          f"縁 {int(both['rim_ok'].sum())}、口 {int(both['mouth_ok'].sum())}、口の x の最小 {mx[:, 0].min() * 1e3:.3f} mm" if len(mx) else "口 0",
          both["rim_ok"].any() and len(mx) > 0 and mx[:, 0].min() > 0)

    same = PT.pad_shear_asymmetry([0.0, 0.3], [0.0, 0.3])
    couple = PT.pad_shear_asymmetry([0.0, 0.3], [0.0, -0.3])
    check("pad_shear_asymmetry", "左右が同じ向き 0.3 N", "偶力の比 0", f"{same['ratio_v']}", same["ratio_v"] == 0.0 and not same["opposite_v"])
    check("pad_shear_asymmetry", "左右が逆向き ±0.3 N", "純粋な偶力: 比 1、共通 0", f"{couple['ratio_v']}、共通 {couple['common'].tolist()}",
          couple["ratio_v"] == 1.0 and couple["opposite_v"] and np.allclose(couple["common"], 0.0))
    qR, qL = np.array([0.1, 0.5]), np.array([-0.05, 0.1])
    mix = PT.pad_shear_asymmetry(qR, qL)
    com, dif = (qR + qL) / 2, (qR - qL) / 2
    want = abs(dif[1]) / (abs(com[1]) + abs(dif[1]))
    check("pad_shear_asymmetry", "q_R = (0.1, 0.5)、q_L = (−0.05, 0.1)", f"共通 {com.tolist()}、比 {want:.6f}",
          f"{np.round(mix['common'], 12).tolist()}、{mix['ratio_v']:.6f}",
          np.allclose(mix["common"], com) and np.allclose(mix["diff"], dif) and abs(mix["ratio_v"] - want) < 1e-15)


def main() -> int:
    t0 = time.time()
    demo_geometry()
    demo_rgbd()
    demo_summary_contact()
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
