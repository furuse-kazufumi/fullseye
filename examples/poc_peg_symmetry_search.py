# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""ペグの対称性で回転の探索を 1/n に絞る —— 角・六角ペグの挿入を、群の恒等式と閉形式と MuJoCo で確かめる(2026-10-05)。

物理シミュ × Fullseye 系列(柔らかい手首のペグ挿入、失敗の分類、2 本指の膜)の続き。正 n 角柱のペグ(n = 3, 4, 6)と、角を 1 つ落とした
キー付きの正方形(対称は n = 1)を、同じ形を外へ 0.2 mm ずらした穴(45° の面取り 0.5 mm)へ入れる。向きの差は 2π/n を法としてしか意味が
無いので、(i) 画像から向きを 2π/n を法として読み(輪郭の複素フーリエ位相)、(ii) 回転の探索を 1 周期だけ、面取りが捕まえる角の 2 倍以下の
刻みで掃く。学習は使わない(対称性を学習で使う研究 = Symmetry-aware RL、ICRA 2024、arXiv:2402.18002 の題材を規則で)。
外から来るもの:
  * **閉形式(導出)**: 回転の窓 φ = π/n − arccos((A + δ + W) cos(π/n)/A)、摩擦で止まる限界 sin²β* = (√(1 + 8μ²) − 1)/2、
    期待試行回数 E = Σ_k (1 − |∪_{i<k} I_i|/P) と、刻みがちょうど 2φ の時の (M + 1)/2。
  * **公表式**: Goli ほか 2024(R. Soc. Open Sci. 11 240956、CC BY)の式 (2.28) φ = (v − v′)/h —— 長方形ペグの二点接触の小角の極限。
    円柱の Whitney の式(pegsim、原著未読・OCW の本文から)を内接円と外接円で使い、多角形の厳密な二点接触の深さを挟む。
  * **群の作用**: 角に 2π/n を足しても答えが同じ(畳み込み・画像の読み・MuJoCo の試行回数)、回した形の読みは同じだけ回る。
  * **物理エンジン(--full)**: MuJoCo の凸メッシュのペグと箱の壁の穴、手首 / 上向きカメラの画像、試行の成否、mj_geomDistance。

門(既定 10 本は numpy、--full でさらに MuJoCo の 7 本):
  1 群の恒等式(畳み込みと画像の読み)/ 2 回転の窓: 閉形式 = 線形計画、キー付きは窓の外で入らない / 3 ペグと穴の画像から向きの差 /
  4 探索回数: 閉形式 vs 一様な誤差の格子で線形計画の判定、対称を知らない探索との比 → 1/n / 5 キー付きで n = 1 に落ちる /
  6 多角形の二点接触の深さ: 面に平行な傾きは円柱の式と一致・Goli の小角の極限・他の向きは内接円と外接円の式で挟まる /
  7 斜めの画像を平面に打ち直して読む(下から見た鏡像も)/ 8 らせん探索の覆いと期待点数 / 9 2 次モーメントの罠 / 10 綴り壊しと MJCF;
  --full: 11 MuJoCo の画像から向きの差(と +2π/n の恒等式)/ 12 捕まえる窓 vs 閉形式(摩擦の限界を含む)/ 13 六角形の窓の摩擦依存 /
  14 盲目の探索の試行回数 = 予言(試行ごと)と期待値、正方形 vs キー付き / 15 画像で 1 回 / 16 穴を 2π/n 回しても同じ回数 /
  17 二点接触の深さ: MuJoCo vs 厳密。
図(FULLSEYE_FIGURE_DIR があるとき、等倍): 既定 5 枚 = 回る形と読んだ向き(GIF、真値の線つき)、期待試行回数 vs n(閉形式・格子・1/n)、
回転の窓(線形計画の余裕と閉形式の線)、二点接触の深さ vs 傾きの向き(内接円・外接円の帯)、らせん探索の覆い;
--full でさらに 3 枚 = MuJoCo の探索の動く図(側面カメラ、試行の帯)、捕まえる窓 vs 摩擦(閉形式の曲線と MuJoCo の点)、手首 / 上向き
カメラの画像と打ち直した図。
正直に: 穴の向きは手首カメラ、ペグの向きは上向きカメラ(先端の高さは運動学から)で読む。摩擦の限界は 45° の面取り・偶数の n(並進しない)・
軸まわりのばねが弱い時の導出で、正方形の μ = 0.5 では MuJoCo の方が広く捕まえた(門 12 の内訳)。多角形の二点接触の閉形式は見つけられず
(Sturges 1988 / 1996 は未読)、厳密な数値解を円の式で挟んだ。キー付きは穴がペグの相似でないので向きの差に小さな偏りが残る。
Run: py -3.11 examples/poc_peg_symmetry_search.py [--full]        (--full は mujoco)
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs  # noqa: E402
import pegsym as S  # noqa: E402

FULL = "--full" in sys.argv
_GATES: list[tuple[str, bool]] = []
_NUM: dict = {}
A, DELTA, W, MU = 5.0e-3, 0.2e-3, 0.5e-3, 0.3
CUT = 1.8e-3
SHAPES = (("triangle", 3, 0.0), ("square", 4, 0.0), ("hexagon", 6, 0.0), ("keyed", 4, CUT))
RES, SIZE = 0.12e-3, 200                  # 上から見た合成図: 24 mm 四方


def gate(name, ok, detail=""):
    _GATES.append((name, bool(ok)))
    print("  [%s] %s %s" % ("ok" if ok else "NG", name, detail), flush=True)


def skip(name, why):
    print("  [skip] %s —— %s" % (name, why))


def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False


def _px(V, res=RES, size=SIZE):
    """世界 (x, y) → 上から見た図の画素 (col, row)(列 = +x、行 = −y)。"""
    c = (size - 1) / 2.0
    return np.stack([c + V[:, 0] / res, c - V[:, 1] / res], axis=1)


def _peg(n, cut, yaw=0.0):
    return S.polygon_peg(n, A, yaw=yaw, cut=cut)


def _hole(n, cut, yaw=0.0):
    return S.polygon_offset(_peg(n, cut, yaw)["vertices"], DELTA)["vertices"]


def _mouth(n, cut, yaw=0.0):
    return S.polygon_offset(_hole(n, cut, yaw), W)["vertices"]


def _cap(n, cut, mu=MU):
    """面取りが捕まえる角(正多角形は閉形式の phi_eff、キー付きは線形計画の窓の狭い側)。"""
    p = _peg(n, cut)
    rw = S.rotation_window(p["n"], A, DELTA, W, p["vertices"], _hole(n, cut), mu=mu)
    return rw.get("phi_eff", min(rw["lp"].values())), rw


def oblique_render(V_world, z, K, R, t, shape, bright=200.0, dark=30.0, object_bright=True, ss=3):
    """順方向の合成(:func:`pegsym.plane_topview` の逆写像と独立な経路): 各画素の副標本の光線を平面 z と交わらせ、凸多角形の内外で
    被覆率を数える。カメラは世界 → OpenCV の R・t。"""
    H, Wd = shape
    Ki = np.linalg.inv(K)
    nrm, h = S._halfplanes(S._poly(V_world, "oblique_render"))
    off = (np.arange(ss) + 0.5) / ss - 0.5
    vv, uu = np.mgrid[0:H, 0:Wd].astype(np.float64)
    C = -R.T @ t
    acc = np.zeros((H, Wd))
    for dv in off:
        for du in off:
            pix = np.stack([uu + du, vv + dv, np.ones_like(uu)], axis=-1).reshape(-1, 3)
            dirs = (pix @ Ki.T) @ R                               # カメラ系 → 世界系の向き(R の転置を右から)
            s = (z - C[2]) / dirs[:, 2]
            P = C[None, :2] + s[:, None] * dirs[:, :2]
            ins = np.all(P @ nrm.T <= h[None, :], axis=1) & (s > 0)
            acc += ins.reshape(H, Wd)
    cov = acc / ss ** 2
    return dark + (bright - dark) * (cov if object_bright else 1.0 - cov)


def look_at(eye, target, up=(0.0, 0.0, 1.0)):
    """世界 → OpenCV カメラの R・t(+z 前、+y 下)。"""
    eye, target = np.asarray(eye, float), np.asarray(target, float)
    zc = target - eye
    zc /= np.linalg.norm(zc)
    xc = np.cross(zc, up)
    if np.linalg.norm(xc) < 1e-9:
        xc = np.cross(zc, [0.0, 1.0, 0.0])
    xc /= np.linalg.norm(xc)
    yc = np.cross(zc, xc)
    R = np.stack([xc, yc, zc])
    return R, -R @ eye


# ======================================================================================================================
def numpy_part() -> dict:
    print("== 1. numpy の門(群の恒等式・回転の窓・画像の読み・探索回数・キー付き・二点接触・打ち直し・らせん・罠・綴り壊し)")
    out = {}
    # ── 1. 群の恒等式
    t0 = time.time()
    rng = np.random.default_rng(3)
    e_fold = 0.0
    for _ in range(400):
        n = int(rng.integers(1, 9))
        a = float(rng.uniform(-20, 20))
        k = int(rng.integers(-5, 6))
        e_fold = max(e_fold, abs(S.symmetry_fold(a + 2 * math.pi * k / n, n) - S.symmetry_fold(a, n)))
    # 同変性は 1 周期を 40 等分 + 黄金比のずれで密に走査する: 辺が画素の軸に揃う角の近く(六角形の 120° など)だけ副標本の量子化で誤差が
    # 0.1° に跳ねる —— まばらな 10 角では揃う角を外して 0.013° と出ていた(探針 1 枚は覆いでない)
    n_ang = 40
    eq_err, id_err, n_seen, worst_at = {}, {}, {}, {}
    rows_gif = []
    for name, n, cut in SHAPES:
        ref = S.polygon_yaw_read(S.polygon_coverage_image(_px(_peg(n, cut)["vertices"]), SIZE, 4), polarity="bright")
        nn = _peg(n, cut)["n"]
        P = 2 * math.pi / nn
        yaws = (np.arange(n_ang) + 0.618) / n_ang * P
        assert len(yaws) >= 10
        e_eq, e_id, seen, w_at = 0.0, 0.0, set(), 0.0
        for j, psi in enumerate(yaws):
            r = S.polygon_yaw_read(S.polygon_coverage_image(_px(_peg(n, cut, psi)["vertices"]), SIZE, 4), polarity="bright")
            seen.add(r["n_detected"])
            e = abs(S.symmetry_fold(r["yaw"] - ref["yaw"] - psi, nn))
            if e > e_eq:
                e_eq, w_at = e, math.degrees(psi)
            if j % 4 == 0:
                r2 = S.polygon_yaw_read(S.polygon_coverage_image(_px(_peg(n, cut, psi + P)["vertices"]), SIZE, 4), polarity="bright")
                e_id = max(e_id, abs(S.symmetry_fold(r2["yaw"] - r["yaw"], nn)))
        eq_err[name], id_err[name], n_seen[name], worst_at[name] = math.degrees(e_eq), math.degrees(e_id), seen, w_at
    _NUM.update(fold_identity=e_fold, equivariance_deg=eq_err, identity_deg=id_err)
    ok = (e_fold < 1e-12 and all(n_seen[nm] == {_peg(n, c)["n"]} for nm, n, c in SHAPES)
          and max(eq_err[nm] for nm in ("triangle", "square", "hexagon")) < 0.15 and eq_err["keyed"] < 0.5
          and max(id_err.values()) < 0.15)
    gate("門 1 群の恒等式: symmetry_fold(α + 2πk/n) = symmetry_fold(α)(400 組、1e-12)、形を 2π/n 余分に回して描いた図の読みが同じ(< 0.15°。同じ点集合なので像は丸めの桁で同じ —— 読みが像の関数であることの確認だけ、物理の恒等式は門 16)、"
         "回した形の読みは同じだけ回る(1 周期 40 角、正多角形 < 0.15°・キー付き < 0.5°。副標本 4 × 4 の量子化で辺が画素の軸に揃う角が最悪)、"
         "検出した n が 3 / 4 / 6 / 1",
         ok, "畳み込み %.1e、同変 %s°(最悪の角 %s°)、+2π/n %s°、n %s(%.2f s)" % (
             e_fold, {k: round(v, 3) for k, v in eq_err.items()}, {k: round(v, 1) for k, v in worst_at.items()},
             {k: round(v, 4) for k, v in id_err.items()}, {k: sorted(v) for k, v in n_seen.items()}, time.time() - t0))
    out["gif_rows"] = rows_gif
    # ── 2. 回転の窓: 閉形式 vs 線形計画、キー付きは窓の外で口に入らない
    t0 = time.time()
    e_win = 0.0
    wins = {}
    for name, n, cut in SHAPES[:3]:
        p = _peg(n, cut)
        rw = S.rotation_window(n, A, DELTA, W, p["vertices"], _hole(n, cut))
        rw0 = S.rotation_window(n, A, DELTA, 0.0, p["vertices"], _hole(n, cut))
        e_win = max(e_win, abs(rw["phi_cap"] - rw["lp"]["plus"]), abs(rw["phi_cap"] - rw["lp"]["minus"]),
                    abs(rw0["phi_fit"] - rw0["lp"]["plus"]))
        wins[name] = (math.degrees(rw["phi_fit"]), math.degrees(rw["phi_cap"]))
    pk = _peg(4, CUT)
    rwk = S.rotation_window(1, A, DELTA, W, pk["vertices"], _hole(4, CUT))
    c0 = pk["vertices"].mean(axis=0)
    mouth_k = _mouth(4, CUT)
    outside_fit = 0
    scan = np.radians(np.arange(0.0, 360.0, 1.0))
    for a in scan:
        if min(abs(S.symmetry_fold(a, 1)), 10.0) <= rwk["lp"]["plus"] + 1e-9:
            continue
        P = (pk["vertices"] - c0) @ S._rot2(a).T + c0
        outside_fit += int(S.polygon_fit_check(P, mouth_k)["fit"])
    _NUM.update(window_closed_vs_lp_rad=e_win, keyed_window_deg=math.degrees(rwk["lp"]["plus"]))
    gate("門 2 回転の窓: 正 n 角形の閉形式(φ = π/n − arccos((A + δ + W)cos(π/n)/A)、atan2 で)= 平行移動も自由な線形計画の二分法(1e-8 rad)、"
         "キー付き(角を 1.8 mm 落とす)は 0 を含む窓の外の 1° 刻み全部で口に入らない",
         e_win < 1e-8 and outside_fit == 0,
         "最大差 %.1e rad、窓 [最狭部, 口] %s°、キー付きの窓 ±%.2f°、窓の外で入った角 %d(%.2f s)" % (
             e_win, {k: (round(a, 2), round(b, 2)) for k, (a, b) in wins.items()}, math.degrees(rwk["lp"]["plus"]), outside_fit,
             time.time() - t0))
    out["windows"] = wins
    # ── 3. ペグと穴の画像から向きの差(穴は暗い口、ペグは明るい端面)
    t0 = time.time()
    rel_err = {}
    for name, n, cut in SHAPES:
        nn = _peg(n, cut)["n"]
        e = 0.0
        for psi, hy in ((0.1, 0.45), (1.3, 0.2), (2.9, 4.0), (5.5, 0.05)):
            img_p = S.polygon_coverage_image(_px(_peg(n, cut, psi)["vertices"]), SIZE, 4)
            img_h = 1.0 - S.polygon_coverage_image(_px(_mouth(n, cut, hy)), SIZE, 4)
            rel = S.relative_yaw_from_images(img_p, img_h, nn)
            e = max(e, abs(S.symmetry_fold(rel["delta"] - (psi - hy), nn)))
        rel_err[name] = math.degrees(e)
    _NUM["relative_yaw_err_deg"] = rel_err
    gate("門 3 ペグ(明るい端面)と穴(暗い口)の図から向きの差 mod 2π/n: 正多角形 < 0.1°(穴は相似なので形の位相の定数が消える)、"
         "キー付き < 0.5°(穴が相似でない分の偏り)",
         max(rel_err[k] for k in ("triangle", "square", "hexagon")) < 0.1 and rel_err["keyed"] < 0.5,
         "%s °(%.2f s)" % ({k: round(v, 4) for k, v in rel_err.items()}, time.time() - t0))
    # ── 4. 探索回数: 閉形式 vs 格子(線形計画で判定)、比 → 1/n
    t0 = time.time()
    ex = {}
    for name, n, cut in SHAPES:
        nn = _peg(n, cut)["n"]
        cap, _ = _cap(n, cut, mu=None)
        E = S.search_expected_tries(nn, cap)
        plan = S.rotation_search_plan(nn, cap)
        P = plan["period"]
        p = _peg(n, cut)
        c0 = p["vertices"].mean(axis=0)
        mouth = _mouth(n, cut)
        n_grid = 48 if nn > 1 else 96
        tries = []
        for j in range(n_grid):
            e = (j + 0.5) / n_grid * P
            k_ok = None
            for k, a in enumerate(plan["angles"]):
                Pv = (p["vertices"] - c0) @ S._rot2(e - a).T + c0
                if S.polygon_fit_check(Pv, mouth)["fit"]:
                    k_ok = k + 1
                    break
            tries.append(k_ok if k_ok is not None else np.nan)
        ex[name] = {"E": E["expected"], "closed": E["closed"], "grid": float(np.mean(tries)), "M": plan["M"], "ratio": E["ratio_vs_blind"],
                    "n": nn, "blind": E["blind_expected"], "missing": int(np.sum(np.isnan(tries))), "n_grid": n_grid}
    asym = {n: S.search_expected_tries(n, math.radians(0.2))["ratio_vs_blind"] * n for n in (3, 4, 6)}
    ok = (all(abs(v["grid"] - v["E"]) / v["E"] < 0.03 and v["missing"] == 0 for v in ex.values())
          and all(abs(a - 1.0) < 0.01 for a in asym.values()))
    _NUM["expected_tries"] = ex
    gate("門 4 期待試行回数: 区間の和の閉形式 E vs 一様な誤差の格子(48 点、キー付き 96 点、成否は口への線形計画 —— 閉形式の窓を使わない別の経路)で 3 % 以内、"
         "取りこぼし 0、対称を知らない探索との比 × n → 1(φ = 0.2° で 1 %)",
         ok, "%s、比 × n(φ = 0.2°)%s(%.2f s)" % (
             {k: "E %.2f 格子 %.2f M %d 比 %.3f" % (v["E"], v["grid"], v["M"], v["ratio"]) for k, v in ex.items()},
             {k: round(v, 4) for k, v in asym.items()}, time.time() - t0))
    out["expected"] = ex
    # ── 5. キー付きは n = 1
    k_ = ex["keyed"]
    sq = ex["square"]
    gate("門 5 キー付きのペグで n = 1 に落ちる: 輪郭の n = 1(門 1)、探索の周期 2π で比 = 1、期待回数は正方形の ≈ 4 倍(閉形式の比 (M+1)/(4M+1) の向き)",
         k_["n"] == 1 and abs(k_["ratio"] - 1.0) < 1e-12 and 2.5 < k_["E"] / sq["E"] < 4.0,
         "キー付き E %.2f(M %d)、正方形 E %.2f(M %d)、比 %.2f、(M+1)/(4M+1) の逆数 %.2f" % (
             k_["E"], k_["M"], sq["E"], sq["M"], k_["E"] / sq["E"], (4 * sq["M"] + 1) / (sq["M"] + 1)))
    # ── 6. 多角形の二点接触の深さ
    t0 = time.time()
    e_face, below, above, rows_tp, below_rel = 0.0, 0, 0, [], 0.0
    for name, n, cut in SHAPES[:3]:
        p = _peg(n, cut)["vertices"]
        h = _hole(n, cut)
        for th_deg in (1.0, 3.0, 6.0):
            for psi in np.linspace(0.0, 2 * math.pi / n, 7):
                r = S.polygon_two_point_depth(p, h, math.radians(th_deg), float(psi))
                if n == 4 and abs(S.symmetry_fold(psi, 4)) < 1e-9:
                    e_face = max(e_face, abs(r["l2"] - r["circle_in"]))
                below += int(r["l2"] < r["circle_in"] - 1e-9)
                below_rel = max(below_rel, (r["circle_in"] - r["l2"]) / r["circle_in"])
                above += int(r["l2"] > r["circle_out"] + 1e-9)
                if th_deg == 3.0:
                    rows_tp.append((name, float(psi), r["l2"], r["circle_in"], r["circle_out"]))
    p4, h4 = _peg(4, 0.0)["vertices"], _hole(4, 0.0)
    r_small = S.polygon_two_point_depth(p4, h4, math.radians(0.5), 0.0, depth_max=0.2)
    goli = r_small["l2"] / r_small["goli_small_angle"]
    _NUM.update(two_point_face_vs_circle=e_face, goli_ratio=goli)
    gate("門 6 多角形の二点接触の深さ(厳密 = 凸包の頂点の線形計画 + 二分法): 正方形を面に平行な軸で傾けると円柱の Whitney の式(内接円)と一致"
         "(1e-9 m)、θ = 0.5° で Goli ほか 2024 の式 (2.28) の小角の極限 l₂ tanθ = 2δ に 0.2 % 以内、3 / 4 / 6 角 × 傾き 3 段 × 向き 7 つ "
         "が内接円と外接円の式の間(内接円の側は 0.1 % まで許す: 傾き 6° の正方形で 1 µm 下に出る)",
         e_face < 1e-9 and abs(goli - 1.0) < 2e-3 and below_rel < 1e-3 and above == 0,
         "面の向きの差 %.1e m、Goli 比 %.5f、下 / 上に外れた組 %d / %d(下は最大 %.3f %%)(%.2f s)" % (e_face, goli, below, above, 100 * below_rel, time.time() - t0))
    out["two_point"] = rows_tp
    # ── 7. 斜めの画像を平面に打ち直して読む(手首カメラの斜め、上向きカメラの鏡像)
    t0 = time.time()
    K = np.array([[300.0, 0, 119.5], [0, 300.0, 89.5], [0, 0, 1]])
    errs = {}
    for label, eye, z_plane, bright in (("oblique 35 deg", (-0.03, -0.012, 0.045), 0.0, False), ("from below", (0.002, -0.001, -0.03), 0.0, True)):
        R, t = look_at(eye, (0.0, 0.0, z_plane), up=(0.0, 1.0, 0.0) if label == "from below" else (0.0, 0.0, 1.0))
        e = 0.0
        for psi in (0.2, 0.9):
            V = _peg(4, 0.0, psi)["vertices"] if bright else _mouth(4, 0.0, psi)
            img = oblique_render(V, z_plane, K, R, t, (180, 240), object_bright=bright)
            top = S.plane_topview(img, K, R, t, z=z_plane, extent=0.02, res=0.08e-3, fill=200.0 if not bright else 30.0)
            rr = S.polygon_yaw_read(top, n=4, polarity="bright" if bright else "dark")
            ref_img = S.polygon_coverage_image(_px(_peg(4, 0.0)["vertices"] if bright else _mouth(4, 0.0), 0.08e-3, 250), 250, 4)
            ref = S.polygon_yaw_read(ref_img if bright else 1 - ref_img, n=4, polarity="bright" if bright else "dark")
            e = max(e, abs(S.symmetry_fold(rr["yaw"] - ref["yaw"] - psi, 4)))
        errs[label] = math.degrees(e)
    _NUM["rectify_err_deg"] = errs
    gate("門 7 斜めの画像(順方向の光線の合成、打ち直しの逆写像と独立)を平面 z = 0 の上から見た図に打ち直して向きを読む: 斜め 35° の手首側 "
         "と下から見た鏡像の両方 < 0.1°(打ち直しの図は世界の向きなので鏡像でも符号が反らない)",
         max(errs.values()) < 0.1, "%s °(%.2f s)" % ({k: round(v, 4) for k, v in errs.items()}, time.time() - t0))
    # ── 8. らせん探索
    t0 = time.time()
    c = W + DELTA                                                  # 面取りが横に捕まえる半径(導出: 口の辺心距離の余り)
    good = S.spiral_search_points(1.6 * c, 1.0 * c, 4.0e-3)
    bad = S.spiral_search_points(3.0 * c, 1.0 * c, 4.0e-3)
    eg = S.spiral_expected_tries(good["points"], c, 3.0e-3, grid=121)
    eb = S.spiral_expected_tries(bad["points"], c, 3.0e-3, grid=121)
    rel_sp = abs(eg["measured"] - eg["closed"]) / eg["closed"]
    _NUM.update(spiral_measured=eg["measured"], spiral_closed=eg["closed"], spiral_bad_uncovered=eb["uncovered"])
    gate("門 8 らせん探索: 隙間の十分条件 √((p/2)² + (s/2)²) ≤ c を満たす刻みで覆いの穴 0、期待点数 = 掃いた面積の近似 πρ²/(2ps) + ½ に 10 % 以内; "
         "ピッチ 3c(条件を破る)は穴が出る",
         good["worst_gap"] <= c and eg["uncovered"] == 0 and rel_sp < 0.10 and bad["worst_gap"] > c and eb["uncovered"] > 0,
         "点 %d、格子 %.1f vs 閉形式 %.1f(%.1f %%)、ピッチ 3c の穴 %d / %d(%.2f s)" % (
             good["n"], eg["measured"], eg["closed"], 100 * rel_sp, eb["uncovered"], eb["n_grid"], time.time() - t0))
    out["spiral"] = (good, eg, c)
    # ── 9. 2 次モーメントの罠
    iso = {}
    for name, n, cut in SHAPES:
        img = S.polygon_coverage_image(_px(_peg(n, cut, 0.4)["vertices"]), SIZE, 4)
        yy, xx = np.mgrid[0:SIZE, 0:SIZE]
        m0 = img.sum()
        cy, cx = (img * yy).sum() / m0, (img * xx).sum() / m0
        mu20 = (img * (xx - cx) ** 2).sum() / m0
        mu02 = (img * (yy - cy) ** 2).sum() / m0
        mu11 = (img * (xx - cx) * (yy - cy)).sum() / m0
        iso[name] = math.hypot(mu20 - mu02, 2 * mu11) / (mu20 + mu02)
    gate("門 9 罠: 2 次モーメントの向きは n ≥ 3 の正多角形で慣性が等方(異方度 < 1e-3)になり向きを持たない —— フーリエ位相(門 1)なら読める。"
         "キー付きは異方で、2 次モーメントの向きが残る",
         max(iso[k] for k in ("triangle", "square", "hexagon")) < 1e-3 and iso["keyed"] > 1e-3,
         "異方度 %s" % {k: "%.1e" % v for k, v in iso.items()})
    # ── 10. 綴り壊し + MJCF
    bad_calls = [
        lambda: S.polygon_peg(2), lambda: S.polygon_peg(4, -1.0), lambda: S.polygon_peg(4, A, cut=3e-3),
        lambda: S.polygon_offset([[0, 0], [1, 0], [0.2, 0.2], [0, 1]], 0.1), lambda: S.polygon_offset(_peg(4, 0)["vertices"], -1e-3),
        lambda: S.polygon_fit_check(np.zeros((0, 2)), _hole(4, 0)), lambda: S.rotation_window(0, A, DELTA),
        lambda: S.rotation_window(4, A, DELTA, peg_vertices=_peg(4, 0)["vertices"]), lambda: S.rotation_window(4, A, DELTA, mu=-0.1),
        lambda: S.polygon_two_point_depth(_peg(4, 0)["vertices"], _hole(4, 0), 0.0),
        lambda: S.polygon_coverage_image([[0, 0], [1, 0], [0, 1]], 4), lambda: S.plane_topview(np.zeros((10, 10)), np.eye(2), np.eye(3), [0, 0, 1]),
        lambda: S.polygon_yaw_read(np.ones((40, 40))), lambda: S.polygon_yaw_read(np.eye(40), polarity="grey"),
        lambda: S.relative_yaw_from_images(np.eye(40), np.eye(40), 0), lambda: S.symmetry_fold(float("nan"), 4),
        lambda: S.rotation_search_plan(4, 0.0), lambda: S.rotation_search_plan(4, 0.1, order="random"),
        lambda: S.search_expected_tries(0, 0.1), lambda: S.spiral_search_points(0.0, 1e-3, 1e-2),
        lambda: S.spiral_expected_tries(np.zeros((2, 2)), 1e-3, 1e-3), lambda: S.pegsym_scene_mjcf(_peg(4, 0)["vertices"], _hole(4, 0), chamfer=-1e-3),
    ]
    assert len(bad_calls) >= 20
    n_bad = sum(_raises(f) for f in bad_calls)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(S.pegsym_scene_mjcf(_peg(6, 0)["vertices"], _hole(6, 0), chamfer=W))
    names = {g.get("name") for g in root.iter("geom")}
    cams = {c_.get("name") for c_ in root.iter("camera")}
    mesh_v = len(root.find("asset/mesh").get("vertex").split()) // 3
    gate("門 10 綴り壊し %d 本は全部 ValueError(fail-closed)、MJCF は六角の穴に壁・面取り・襟が 6 つずつ、カメラ 3 台、ペグのメッシュの頂点 12" % len(bad_calls),
         n_bad == len(bad_calls) and all("wall%d" % i in names and "chamf%d" % i in names and "collar%d" % i in names for i in range(6))
         and cams == {"wrist", "up", "side"} and mesh_v == 12,
         "%d / %d、カメラ %s、メッシュ頂点 %d" % (n_bad, len(bad_calls), sorted(cams), mesh_v))
    return out


# ======================================================================================================================
def full_part(out) -> dict:
    print("== 2. MuJoCo の門(画像から向き・捕まえる窓・摩擦・盲目の探索・画像で 1 回・群の恒等式・二点接触)")
    try:
        import mujoco  # noqa: F401
    except ImportError:
        skip("門 11〜17", "mujoco が無い")
        return out
    # ── 11. MuJoCo の画像から向きの差
    t0 = time.time()
    rel_err, id_err, views = {}, {}, {}
    for name, n, cut in SHAPES:
        nn = _peg(n, cut)["n"]
        e, e_id = 0.0, 0.0
        for hy in (0.3, 1.1, 2.2, 4.4):
            res = []
            for extra in (0.0, 2 * math.pi / nn):
                sc = S.pegsym_scene_build(_peg(n, cut)["vertices"], _hole(n, cut, hy + extra), chamfer=W, mu=MU)
                v = S.pegsym_views(sc)
                rel = S.relative_yaw_from_images(v["peg_view"], v["hole_view"], nn)
                truth = S.symmetry_fold(v["peg_yaw"] - hy, nn)
                res.append(rel["delta"])
                e = max(e, abs(S.symmetry_fold(rel["delta"] - truth, nn)))
                if extra == 0.0 and hy == 0.3:
                    views[name] = v
                S.pegsym_scene_close(sc)
            e_id = max(e_id, abs(S.symmetry_fold(res[1] - res[0], nn)))
        rel_err[name], id_err[name] = math.degrees(e), math.degrees(e_id)
    _NUM.update(mujoco_rel_err_deg=rel_err, mujoco_identity_deg=id_err)
    out["views"] = views
    gate("門 11 MuJoCo の画像(手首カメラで穴の口、上向きカメラでペグの端面、それぞれ平面に打ち直す)から向きの差 mod 2π/n が真値(qpos の yaw)に "
         "正多角形 0.3° 以内・キー付き 1° 以内(相似でない穴の偏り、窓 ±8.7° に対して)、穴を 2π/n 余分に回して組み直した場面でも同じ読み(0.3°)",
         max(rel_err[k] for k in ("triangle", "square", "hexagon")) < 0.3 and rel_err["keyed"] < 1.0 and max(id_err.values()) < 0.3,
         "誤差 %s°、+2π/n %s°(%.1f s)" % ({k: round(v, 3) for k, v in rel_err.items()}, {k: round(v, 3) for k, v in id_err.items()}, time.time() - t0))
    # ── 12. 捕まえる窓 vs 閉形式(μ = 0.3)
    t0 = time.time()
    cap_rows = {}
    hy = 0.35
    for name, n, cut in SHAPES:
        cap, rw = _cap(n, cut)
        sc = S.pegsym_scene_build(_peg(n, cut)["vertices"], _hole(n, cut, hy), chamfer=W, mu=MU)
        ok_e = []
        for e_deg in np.arange(0.0, 30.01, 0.25):
            r = S.pegsym_insert_try(sc, yaw=hy + math.radians(e_deg))
            if not r["success"]:
                break
            ok_e.append(e_deg)
        neg = S.pegsym_insert_try(sc, yaw=hy - math.radians(max(ok_e) if ok_e else 0.0))["success"]
        cap_rows[name] = (math.degrees(cap), max(ok_e) if ok_e else 0.0, neg)
    _NUM["capture_deg"] = cap_rows
    gate("門 12 面取りが捕まえる回転の窓: MuJoCo(0.25° 刻み、0 から外へ最初の失敗まで)vs 閉形式 phi_eff(幾何と摩擦の限界の小さい方)が "
         "0.5° 以内、負の側も同じ角で入る(鏡映)",
         all(abs(a - b) <= 0.5 and neg for a, b, neg in cap_rows.values()),
         "%s(閉形式°, MuJoCo°, 負側)(%.1f s)" % ({k: (round(a, 2), b, ng) for k, (a, b, ng) in cap_rows.items()}, time.time() - t0))
    # ── 13. 六角形の窓の摩擦依存
    t0 = time.time()
    fr = []
    for mu in (0.0, 0.1, 0.2, 0.3, 0.4, 0.5):
        rw = S.rotation_window(6, A, DELTA, W, mu=mu)
        sc = S.pegsym_scene_build(_peg(6, 0)["vertices"], _hole(6, 0, hy), chamfer=W, mu=mu)
        last = 0.0
        for e_deg in np.arange(0.0, 30.01, 0.25):
            if not S.pegsym_insert_try(sc, yaw=hy + math.radians(e_deg))["success"]:
                break
            last = e_deg
        fr.append((mu, math.degrees(rw["phi_eff"]), last, math.degrees(rw["phi_cap"]), math.degrees(rw["phi_fit"])))
    sq = []
    for mu in (0.5, 0.6, 0.8):
        rw = S.rotation_window(4, A, DELTA, W, mu=mu)
        sc = S.pegsym_scene_build(_peg(4, 0)["vertices"], _hole(4, 0, hy), chamfer=W, mu=mu)
        last = 0.0
        for e_deg in np.arange(0.0, 30.01, 0.25):
            if not S.pegsym_insert_try(sc, yaw=hy + math.radians(e_deg))["success"]:
                break
            last = e_deg
        sq.append((mu, math.degrees(rw["phi_eff"]), last))
    _NUM.update(hex_friction=fr, square_friction=sq)
    out["friction"] = (fr, sq)
    gate("門 13 六角形の窓は摩擦で狭まる: μ = 0〜0.5 の 6 点で MuJoCo の窓が導出の phi_eff(β* = asin √((√(1+8μ²) − 1)/2)、窓 = π/n − β*、"
         "最狭部の窓 phi_fit が下限)に 0.75° 以内。正方形の μ ≥ 0.5 は内訳として出す(門にしない)",
         all(abs(b - c) <= 0.75 for _, b, c, _, _ in fr),
         "六角 %s;正方形(μ, 閉形式, MuJoCo)%s(%.1f s)" % ([(m, round(b, 2), c) for m, b, c, _, _ in fr], [(m, round(b, 2), c) for m, b, c in sq],
                                                     time.time() - t0))
    # ── 14. 盲目の探索の試行回数
    t0 = time.time()
    srch = {}
    for name, n, cut in SHAPES:
        nn = _peg(n, cut)["n"]
        cap, _ = _cap(n, cut)
        plan = S.rotation_search_plan(nn, cap)
        E = S.search_expected_tries(nn, cap)
        P = plan["period"]
        meas, pred = [], []
        n_hy = 12
        for j in range(n_hy):
            hy_ = (j + 0.37) / n_hy * P
            sc = S.pegsym_scene_build(_peg(n, cut)["vertices"], _hole(n, cut, hy_), chamfer=W, mu=MU)
            r = S.pegsym_search_run(sc, nn, cap, hy_)
            d = np.abs((r["e_true"] - plan["angles"] + P / 2) % P - P / 2)
            pred.append(int(np.argmax(d <= cap)) + 1)
            meas.append(r["tries"] if r["tries"] is not None else np.nan)
        lattice = float(np.mean(pred))
        srch[name] = {"meas": meas, "pred": pred, "mean": float(np.nanmean(meas)), "lattice": lattice, "E": E["expected"], "M": plan["M"],
                      "agree": int(sum(1 for a, b in zip(meas, pred) if a == b)), "fail": int(np.sum(np.isnan(meas)))}
    _NUM["mujoco_search"] = {k: {kk: vv for kk, vv in v.items() if kk not in ("meas", "pred")} for k, v in srch.items()}
    out["search"] = srch
    ratio = srch["square"]["mean"] / srch["keyed"]["mean"]
    gate("門 14 盲目の回転探索(12 個の穴の向き、各回 MuJoCo で試す): 試行回数が予言(候補の列と phi_eff)と 12 中 11 以上一致・失敗 0、平均が "
         "同じ 12 点の予言の平均に 0.5 回以内、正方形 / キー付き の比が 1/2〜1/4(閉形式の比の向き)",
         all(v["agree"] >= 11 and v["fail"] == 0 and abs(v["mean"] - v["lattice"]) <= 0.5 for v in srch.values()) and 0.25 <= ratio <= 0.5,
         "%s、正方形/キー付き %.3f(%.1f s)" % ({k: "一致 %d/12 平均 %.2f(予言 %.2f、一様の E %.2f、M %d)" % (v["agree"], v["mean"], v["lattice"], v["E"], v["M"])
                                          for k, v in srch.items()}, ratio, time.time() - t0))
    # ── 15. 画像で 1 回
    t0 = time.time()
    one = {}
    for name, n, cut in SHAPES:
        nn = _peg(n, cut)["n"]
        cap, _ = _cap(n, cut)
        n1 = 0
        for hy_ in (0.21, 0.83, 1.9, 3.7):
            sc = S.pegsym_scene_build(_peg(n, cut)["vertices"], _hole(n, cut, hy_), chamfer=W, mu=MU)
            v = S.pegsym_views(sc)
            rel = S.relative_yaw_from_images(v["peg_view"], v["hole_view"], nn)
            r = S.pegsym_search_run(sc, nn, cap, hy_, peg_yaw0=0.0, estimate=-rel["delta"])
            n1 += int(r["tries"] == 1)
            S.pegsym_scene_close(sc)
        one[name] = n1
    gate("門 15 画像の読みを推定値にすると 1 回目で入る(4 形 × 4 向き = 16 / 16)", sum(one.values()) == 16,
         "%s(%.1f s)" % (one, time.time() - t0))
    # ── 16. 穴を 2π/n 回しても同じ回数
    t0 = time.time()
    same, tot = 0, 0
    for name, n, cut in SHAPES[:3]:
        cap, _ = _cap(n, cut)
        for hy_ in (0.13, 0.61):
            tr = []
            for k in (0, 1, 2):
                sc = S.pegsym_scene_build(_peg(n, cut)["vertices"], _hole(n, cut, hy_ + 2 * math.pi * k / n), chamfer=W, mu=MU)
                tr.append(S.pegsym_search_run(sc, n, cap, hy_ + 2 * math.pi * k / n)["tries"])
            same += int(len(set(tr)) == 1 and tr[0] is not None)
            tot += 1
    gate("門 16 群の恒等式を物理で: 穴を 2πk/n(k = 0, 1, 2)余分に回して組み直した場面(壁の箱の三角関数は別の値)で試行回数が同じ",
         same == tot, "%d / %d(%.1f s)" % (same, tot, time.time() - t0))
    # ── 17. 二点接触の深さ: MuJoCo vs 厳密
    t0 = time.time()
    worst = 0.0
    rows = []
    for name, n, cut in SHAPES[:3]:
        sc = S.pegsym_scene_build(_peg(n, cut)["vertices"], _hole(n, cut), chamfer=W)
        for th_deg in (2.0, 4.0):
            for psi in (0.0, math.pi / n, 0.3):
                l_sim = S.pegsym_two_point_depth_sim(sc, math.radians(th_deg), psi)
                l_ex = S.polygon_two_point_depth(_peg(n, cut)["vertices"], _hole(n, cut), math.radians(th_deg), psi)["l2"]
                lat = abs(l_sim - l_ex) * math.tan(math.radians(th_deg))
                worst = max(worst, lat)
                rows.append((name, th_deg, math.degrees(psi), l_sim, l_ex))
    _NUM["two_point_mujoco_lateral_um"] = worst * 1e6
    gate("門 17 二点接触の深さ: MuJoCo(mj_geomDistance、平行移動のパターン探索 + 二分法)vs 厳密(線形計画): 3 / 4 / 6 角 × 傾き 2 段 × 向き 3 つで、"
         "差を横の隙間に直して 8 µm 以内(隙間 δ = 200 µm の 4 %、MuJoCo の距離は常に浅い側)", worst < 8e-6,
         "最大 %.2f µm(深さの差は最大 %.3f mm)(%.1f s)" % (worst * 1e6, max(abs(a - b) for *_, a, b in rows) * 1e3, time.time() - t0))
    return out


# ======================================================================================================================
def figures(out):
    t0 = time.time()
    # 1. 回る形と読んだ向き(GIF): 上から見た図に、真値の面の法線(緑)と読み(橙)を重ねる
    frames = []
    for psi in np.radians(np.arange(0, 181, 6)):
        tiles = []
        for name, n, cut in (("square", 4, 0.0), ("hexagon", 6, 0.0), ("keyed", 4, CUT)):
            p = _peg(n, cut, psi)
            img = S.polygon_coverage_image(_px(p["vertices"]), SIZE, 3)
            ref = S.polygon_yaw_read(S.polygon_coverage_image(_px(_peg(n, cut)["vertices"]), SIZE, 3), polarity="bright")
            rd = S.polygon_yaw_read(img, polarity="bright")
            est = S.symmetry_fold(rd["yaw"] - ref["yaw"], p["n"])
            rgb = np.repeat((40 + 170 * img)[..., None], 3, axis=2)
            c = (SIZE - 1) / 2
            for ang, col, L in ((S.symmetry_fold(psi, p["n"]), (60, 200, 90), 90), (est, (255, 150, 30), 70)):
                for s in np.linspace(0, L, 200):
                    x, y = int(round(c + s * math.cos(ang))), int(round(c - s * math.sin(ang)))
                    if 0 <= x < SIZE and 0 <= y < SIZE:
                        rgb[max(0, y - 1):y + 2, max(0, x - 1):x + 2] = col
            tiles.append(rgb)
        frames.append(np.concatenate(tiles, axis=1).astype(np.uint8))
    figs.save_gif("pegsym_rotating_shapes_read_mod_2pi_over_n", frames, fps=6.0,
                  caption="正方形・正六角形・キー付きの正方形を 0〜180° 回す。緑 = 真の向きを 2π/n で畳んだもの、橙 = 輪郭の複素フーリエ位相の読み"
                          "(2π/n を法とした角)。正方形は 90°、六角形は 60° ごとに読みが同じ所へ戻り(群の恒等式)、キー付きは 1 周しないと戻らない。")
    # 2. 期待試行回数 vs n
    ex = out["expected"]
    ns = np.array([1, 3, 4, 6])
    capd = math.radians(5.0)
    th_E = [S.search_expected_tries(int(n), capd)["expected"] for n in range(1, 9)]
    figs.save_plot("pegsym_expected_tries_vs_symmetry",
                   [("closed form, same window 5 deg", np.arange(1, 9), np.array(th_E)),
                    ("blind / n", np.arange(1, 9), th_E[0] / np.arange(1, 9)),
                    ("this rig: closed form", np.array([ex[k]["n"] for k in ("keyed", "triangle", "square", "hexagon")]),
                     np.array([ex[k]["E"] for k in ("keyed", "triangle", "square", "hexagon")])),
                    ("this rig: lattice of errors, fit by LP", np.array([ex[k]["n"] for k in ("keyed", "triangle", "square", "hexagon")]),
                     np.array([ex[k]["grid"] for k in ("keyed", "triangle", "square", "hexagon")]))],
                   xlabel="symmetry order n", ylabel="expected rotation tries", title="Searching one period 2 pi / n cuts the tries by ~1/n",
                   kinds=["line", "line", "scatter", "scatter"], styles=[None, "dashed", None, None],
                   caption="線 = 窓 5° を共通にした時の閉形式 E(n)、破線 = 対称を知らない探索の E を n で割ったもの。点 = この装置(窓は形ごとに違う)"
                           "の閉形式と、一様な誤差の格子で口への線形計画が判定した平均。キー付きは n = 1。")
    # 3. 回転の窓
    series = []
    for name, n, cut in SHAPES:
        p = _peg(n, cut)
        c0 = p["vertices"].mean(axis=0)
        mouth = _mouth(n, cut)
        angs = np.radians(np.linspace(-25, 25, 201))
        mg = [S.polygon_fit_check((p["vertices"] - c0) @ S._rot2(a).T + c0, mouth)["margin"] * 1e6 for a in angs]
        series.append(("%s (LP margin)" % name, np.degrees(angs), np.array(mg)))
    series.append(("zero margin", np.array([-25.0, 25.0]), np.array([0.0, 0.0])))
    wins = out["windows"]
    figs.save_plot("pegsym_rotation_window_margin", series, xlabel="yaw error [deg]", ylabel="best clearance in the chamfer mouth [um]",
                   title="Rotation window: LP margin vs the closed form", kinds=["line"] * 5, styles=[None, None, None, "dotted", "dashed"],
                   caption="平行移動も自由にした時の口の中の最良の余裕(線形計画)。0 を切る角 = 面取りが捕まえる窓。閉形式の窓: %s°。キー付き(点線)は"
                           "窓の中で正方形と重なり、周期が 360°。" % {k: round(b, 2) for k, (a, b) in wins.items()})
    # 4. 二点接触の深さ vs 傾きの向き(図のために 1 周期を 49 点で計算し直す。内接円の式で割って形どうしを重ねる)
    series, styles, colors = [], [], []
    bounds = []
    for name, n, cut in SHAPES[:3]:
        p, h = _peg(n, cut)["vertices"], _hole(n, cut)
        psi = np.linspace(0.0, 2 * math.pi / n, 49)
        rr = [S.polygon_two_point_depth(p, h, math.radians(3.0), float(a_)) for a_ in psi]
        series.append(("%s exact / inscribed circle" % name, psi * n / (2 * math.pi), np.array([r_["l2"] / r_["circle_in"] for r_ in rr])))
        styles.append(None)
        colors.append(None)
        bounds.append(("%s circumscribed circle" % name, np.array([0.0, 1.0]), np.full(2, rr[0]["circle_out"] / rr[0]["circle_in"])))
    for b_ in bounds:
        series.append(b_)
        styles.append("dashed")
        colors.append("reference")
    series.append(("inscribed circle (Whitney, Goli 2.28 limit)", np.array([0.0, 1.0]), np.ones(2)))
    styles.append("dotted")
    colors.append("reference")
    figs.save_plot("pegsym_two_point_depth_vs_tilt_direction", series, xlabel="tilt direction / period 2 pi / n  (0 = face normal, 0.5 = vertex)",
                   ylabel="l2 / inscribed-circle l2 at 3 deg", title="Polygonal peg: exact two-point depth between the circle bounds",
                   kinds=["line"] * len(series), styles=styles, colors=colors, size=(640, 380),
                   caption="傾き 3° の二点接触の深さ(厳密、凸包の頂点の線形計画)を内接円の円柱の Whitney の式で割ったもの。横軸は傾ける向きを 1 周期で"
                           "割った値(0 = 面の法線、0.5 = 頂点)。偶数の n は面の法線の向きで 1(正方形では Goli ほか 2024 の (2.28) の小角の極限と同じ)、頂点の向きで"
                           "外接円の式(破線)に近づく。三角形は面の向かいが頂点なので、どの向きでも 1 より上(面の法線方向の幅が辺心距離 + 外接円の半径)。")
    # 5. らせん
    good, eg, c = out["spiral"]
    P = good["points"]
    t_ = np.linspace(0, 2 * math.pi, 120)
    figs.save_plot("pegsym_spiral_search_cover", [("spiral path", 1e3 * P[:, 0], 1e3 * P[:, 1]), ("probe points", 1e3 * P[:, 0], 1e3 * P[:, 1]),
                                                 ("prior disc rho = 3 mm", 3 * np.cos(t_), 3 * np.sin(t_)),
                                                 ("capture radius c (first point)", 1e3 * c * np.cos(t_), 1e3 * c * np.sin(t_))],
                   xlabel="x [mm]", ylabel="y [mm]", title="Lateral spiral search: pitch 1.6c, step c",
                   kinds=["line", "scatter", "line", "line"], styles=[None, None, "dashed", "dashed"],
                   caption="Archimedes のらせん。期待点数: 格子 %.1f、閉形式 πρ²/(2ps) + ½ = %.1f。回転と入れ子にすると (E_らせん − 1)·M + E_回転 なので、"
                           "回転の M が 1/n になれば全体もほぼ 1/n。" % (eg["measured"], eg["closed"]))
    if FULL and "search" in out:
        _figures_full(out)
    print("  図: %s(%.1f s)" % (figs.errors() or "ok", time.time() - t0))


def _figures_full(out):
    import mujoco
    # 6. 探索の動く図(正方形、側面カメラ)
    n, cut = 4, 0.0
    cap, _ = _cap(n, cut)
    hy = 0.37 / 12 * (2 * math.pi / 4) + 5 / 12 * (2 * math.pi / 4)
    sc = S.pegsym_scene_build(_peg(n, cut)["vertices"], _hole(n, cut, hy), chamfer=W, mu=MU, image_size=(320, 240))
    r = S.pegsym_search_run(sc, n, cap, hy, record=True)
    m, d = sc["model"], sc["data"]
    ren = mujoco.Renderer(m, height=240, width=320)
    frames = []
    for row in r["rows"]:
        fr = row["frames"][::6]
        assert len(fr) >= 1
        for q in fr:
            d.qpos[:] = q
            mujoco.mj_forward(m, d)
            ren.update_scene(d, camera="side")
            img = ren.render().copy()
            bar = np.zeros((14, 320, 3), np.uint8)
            for k in range(len(r["rows"])):
                col = (60, 200, 90) if r["rows"][k]["status"] == "success" else (200, 70, 60)
                if k <= row["k"] - 1:
                    bar[2:12, 4 + 22 * k:22 + 22 * k] = col
            frames.append(np.concatenate([img, bar], axis=0))
    ren.close()
    figs.save_gif("pegsym_mujoco_blind_rotation_search", frames, fps=12.0,
                  caption="正方形のペグの盲目の回転探索(MuJoCo、斜め上の固定カメラ)。候補は 90° の 1 周期を %d 等分(刻み %.1f°、面取りの窓 ±%.2f°)。"
                          "下の帯 = 試行(赤 = 面取りか襟で止まった、緑 = 入った)。%d 回目で入り、予言も %d 回。" % (
                              r["M"], 90.0 / r["M"], math.degrees(cap), r["tries"] or -1, r["tries"] or -1))
    # 7. 窓 vs 摩擦
    fr, sq = out["friction"]
    mus = np.linspace(0, 0.6, 61)
    th = [math.degrees(S.rotation_window(6, A, DELTA, W, mu=mu)["phi_eff"]) for mu in mus]
    th4 = [math.degrees(S.rotation_window(4, A, DELTA, W, mu=mu)["phi_eff"]) for mu in mus]
    figs.save_plot("pegsym_capture_window_vs_friction",
                   [("hexagon closed form", mus, np.array(th)), ("hexagon MuJoCo", np.array([f[0] for f in fr]), np.array([f[2] for f in fr])),
                    ("square closed form", mus, np.array(th4)), ("square MuJoCo", np.array([s[0] for s in sq]), np.array([s[2] for s in sq]))],
                   xlabel="wall friction mu", ylabel="captured yaw error [deg]", title="Chamfer rotation capture is friction-limited for hexagons",
                   kinds=["line", "scatter", "line", "scatter"], styles=[None, None, "dashed", None],
                   caption="面取りが回して入れる最大の向きの誤差。線 = 導出(幾何の窓、摩擦の限界 π/n − β*、最狭部の窓の大きい方)。六角形は頂点が面の法線に"
                           "近く、回すモーメントが摩擦に負ける。正方形の μ ≥ 0.5 は MuJoCo の方が広い(導出の仮定 —— 並進しない —— が崩れる内訳)。")
    # 8. カメラの画像と打ち直した図
    v = out["views"]["square"]
    tiles = [v["rgb_hole"], v["rgb_peg"]]                         # 等倍(縮小しない)
    hv = np.repeat(np.clip(v["hole_view"], 0, 255)[..., None], 3, axis=2).astype(np.uint8)
    pv = np.repeat(np.clip(v["peg_view"], 0, 255)[..., None], 3, axis=2).astype(np.uint8)
    figs.save_grid("pegsym_wrist_and_up_camera_rectified", [tiles[0], tiles[1], hv, pv],
                   captions=["wrist camera (hole)", "up camera (peg end face)", "rectified z = 0", "rectified tip plane"], ncols=2,
                   caption="手首カメラ(下向き)で穴の口、上向きカメラでペグの端面を撮り、それぞれの平面を真上から見た図に打ち直す(世界の向き、下からの鏡像も同じ"
                           "向き)。どちらも輪郭の位相で向きを 90° を法として読み、差がペグに加える回転。")


# ======================================================================================================================
def main() -> int:
    t_all = time.time()
    c_all = time.process_time()
    out = numpy_part()
    if FULL:
        out = full_part(out)
    else:
        skip("門 11〜17(MuJoCo)", "--full のときだけ")
    if figs.enabled():
        figures(out)
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    n_ng = sum(1 for _, ok in _GATES if not ok)
    print("gates: %d / %d ok  (%.1f s、この過程の CPU %.1f s)" % (len(_GATES) - n_ng, len(_GATES), time.time() - t_all, time.process_time() - c_all))
    if n_ng or figs.errors():
        print("FAIL")
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
