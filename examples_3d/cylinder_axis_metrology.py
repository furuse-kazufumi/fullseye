# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 汚れた産業スキャンからパイプ/シャフトの軸と半径を計測する (metrology).

工場の据付検査では、配管やシャフトの点群をレーザースキャンし「軸がどこを向き・
半径が図面どおりか」を測る。ところが現場スキャンには、隣接部品・反射・粉塵・
位置合わせ用ターゲットなどの **グロス外れ値(gross outliers)** が全点の 3 割ほど
混じる。外れ値を無視して全点に当てはめると、軸も半径も外れ値に引きずられて破綻する。
ここでは既知半径 R・既知軸方向の円筒面から点群を作り、そこへ ~30% の外れ値を撒き、
pcseg.fit_cylinder_ransac(点+法線サンプルの RANSAC, Rusu 2009)で円筒を復元する。

検証(GT): 円筒は自分で組んだので真値がわかる。
  * 復元半径 R_est が真値 R の相対 3% 以内。
  * 復元軸方向が真の軸から数度以内。
  * 復元円筒の面残差(真の表面点に対する RMS 半径ずれ)がノイズ床の水準。
  beat-null: (A) 外れ値を捨てない **非ロバスト当てはめ**(全点で法線から軸を取り
  Kåsa 円で半径を出す)は半径が大きく膨れる。(B) **誤ったプリミティブ**(平面 RANSAC)
  は円筒面を表現できず面残差が桁違いに大きい。実ロバスト当てはめが両 null を広い
  マージンで上回ることを assert する(弱い assert ではなく既知真値と桁差で突き合わせる)。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# 直接実行時もリポジトリルートの本物モジュールを確実に import させる(順序保証・無害)。
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

import pcseg  # noqa: E402  fit_cylinder_ransac / fit_plane_ransac
from pointcloud import estimate_normals  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# 幾何ヘルパ
# ═══════════════════════════════════════════════════════════════════════════
def perp_basis(axis: np.ndarray):
    """軸に直交する正規直交基底 (e1, e2) を返す。"""
    a = axis / np.linalg.norm(axis)
    t = np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(a, t); e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    return e1, e2


def axis_angle_deg(a, b) -> float:
    """2 単位ベクトルのなす角(度)。軸は符号不定なので |cos| を取る。"""
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    return float(np.degrees(np.arccos(np.clip(abs(a @ b), -1.0, 1.0))))


def perp_dist_to_axis(P, c, w) -> np.ndarray:
    """点 P から、点 c を通り方向 w の直線(=軸)までの垂直距離。"""
    w = w / np.linalg.norm(w)
    rel = P - c
    perp = rel - (rel @ w)[:, None] * w
    return np.linalg.norm(perp, axis=1)


# ═══════════════════════════════════════════════════════════════════════════
# 合成データ(既知パラメータ = ground truth)
# ═══════════════════════════════════════════════════════════════════════════
def make_scan(R, axis_pt, axis_dir, length=0.40, n_inlier=1400, n_outlier=600,
              noise=0.0008, box_margin=0.30, seed=0):
    """既知円筒面 + グロス外れ値の「汚れたスキャン」点群を作る。

    戻り値: (points(N,3), is_surface(N,) 真の表面点マスク)。表面点は円筒面上に
    小さなセンサノイズを乗せ、外れ値は円筒 AABB を少し広げた箱内に一様散布する
    (隣接部品・反射・粉塵のクラッタ相当)。点はシャッフルして順序で見分けられない
    ようにする。"""
    rng = np.random.default_rng(seed)
    axis_dir = axis_dir / np.linalg.norm(axis_dir)
    e1, e2 = perp_basis(axis_dir)

    # --- 表面点(既知円筒面 + ノイズ)---
    t = rng.uniform(-length / 2, length / 2, n_inlier)         # 軸方向
    phi = rng.uniform(0.0, 2.0 * np.pi, n_inlier)              # 周方向(全周 360°)
    surf = (axis_pt + t[:, None] * axis_dir
            + R * (np.cos(phi)[:, None] * e1 + np.sin(phi)[:, None] * e2))
    surf = surf + rng.normal(0.0, noise, surf.shape)

    # --- グロス外れ値(円筒 AABB を margin 拡大した箱内に一様)---
    lo, hi = surf.min(0), surf.max(0)
    ext = hi - lo
    lo = lo - box_margin * ext
    hi = hi + box_margin * ext
    outl = rng.uniform(lo, hi, (n_outlier, 3))

    pts = np.vstack([surf, outl])
    is_surface = np.concatenate([np.ones(n_inlier, bool), np.zeros(n_outlier, bool)])
    order = rng.permutation(len(pts))                          # 順序で見分けさせない
    return pts[order], is_surface[order]


# ═══════════════════════════════════════════════════════════════════════════
# beat-null 用の「非ロバスト」円筒当てはめ(全点を使う=外れ値を捨てない)
# ═══════════════════════════════════════════════════════════════════════════
def cylinder_fit_nonrobust(P, N):
    """外れ値を捨てず **全点** で当てる非ロバスト円筒フィット → (axis_dir, radius)。

    円筒面の法線は全て軸に直交するので、法線の共分散の最小固有ベクトル =軸方向。
    その後、軸に直交する平面へ全点を射影し Kåsa の代数円フィットで半径を出す。
    外れ値の法線はばらつき・射影点は箱内に散るため、半径が大きく膨れる(=破綻)。"""
    M = N.T @ N
    _, V = np.linalg.eigh(M)               # 昇順固有値
    axis = V[:, 0]                         # 最小固有ベクトル ≒ 軸
    axis = axis / np.linalg.norm(axis)
    e1, e2 = perp_basis(axis)
    rel = P - P.mean(0)
    u, v = rel @ e1, rel @ e2              # 軸直交平面への 2D 射影(全点)
    A = np.column_stack([2.0 * u, 2.0 * v, np.ones_like(u)])
    b = u * u + v * v
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)   # Kåsa 代数円フィット
    cx, cy, c0 = sol
    radius = float(np.sqrt(max(c0 + cx * cx + cy * cy, 0.0)))
    return axis, radius


# ═══════════════════════════════════════════════════════════════════════════
# メイン
# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    # --- 真値(既知パラメータ)---
    R_TRUE = 0.05                                   # 半径 5cm のパイプ/シャフト
    AXIS_PT_TRUE = np.array([0.10, -0.20, 0.05])    # 軸上の 1 点
    AXIS_DIR_TRUE = np.array([0.30, 0.90, 0.40])    # 軸方向(非軸整列=一般姿勢)
    AXIS_DIR_TRUE = AXIS_DIR_TRUE / np.linalg.norm(AXIS_DIR_TRUE)
    NOISE = 0.0008                                  # センサノイズ σ=0.8mm
    N_IN, N_OUT = 1400, 600                         # 外れ値率 = 600/2000 = 30%

    pts, is_surf = make_scan(R_TRUE, AXIS_PT_TRUE, AXIS_DIR_TRUE, length=0.40,
                             n_inlier=N_IN, n_outlier=N_OUT, noise=NOISE, seed=0)
    outlier_frac = 1.0 - is_surf.mean()

    # 法線はスキャンから推定(現場では真の法線は無い)。ロバスト op と非ロバスト
    # null に **同じ** 法線を渡す = 差は純粋に「外れ値を捨てるか否か(ロバスト性)」。
    N_all = estimate_normals(pts, k=16)

    # --- 1) ロバスト当てはめ(実 op)---------------------------------------
    THRESH = 0.004                                  # ノイズ σ の 5 倍を許容
    res = pcseg.fit_cylinder_ransac(pts, normals=N_all, thresh=THRESH,
                                    iters=500, seed=0, min_inlier_frac=0.20)
    assert res is not None, "ロバスト円筒当てはめが None(合意集合に到達せず)"
    axis_pt, axis_dir, R_est, inliers = res

    radius_rel_err = abs(R_est - R_TRUE) / R_TRUE
    axis_err = axis_angle_deg(axis_dir, AXIS_DIR_TRUE)
    # 復元円筒の面残差(真の表面点に対する RMS 半径ずれ)= ノイズ床の指標
    rms_robust = float(np.sqrt(np.mean(
        (perp_dist_to_axis(pts[is_surf], axis_pt, axis_dir) - R_est) ** 2)))
    # 合意集合が表面点をどれだけ拾えたか(混入した外れ値の割合)
    inlier_purity = float(is_surf[inliers].mean())

    print(f"外れ値率                  : {outlier_frac:.2f}  (全 {len(pts)} 点中 {N_OUT} 点)")
    print(f"注入ノイズ σ              : {NOISE:.4f} m   RANSAC thresh {THRESH:.4f} m")
    print(f"[ロバスト] 半径 R_est      : {R_est:.5f} m  (真 {R_TRUE:.5f} m, 相対誤差 {radius_rel_err*100:.2f}%)")
    print(f"[ロバスト] 軸方向誤差      : {axis_err:.3f}°")
    print(f"[ロバスト] 面残差 RMS      : {rms_robust:.5f} m  (ノイズ σ={NOISE:.4f} と同水準なら成功)")
    print(f"[ロバスト] 合意集合の純度  : {inlier_purity:.3f}  ({int(inliers.sum())} 点, 表面点率)")

    # --- 2) beat-null A: 非ロバスト全点フィット(外れ値を捨てない)----------
    null_axis, R_null = cylinder_fit_nonrobust(pts, N_all)
    radius_rel_err_null = abs(R_null - R_TRUE) / R_TRUE
    axis_err_null = axis_angle_deg(null_axis, AXIS_DIR_TRUE)
    print(f"[null-A 非ロバスト] 半径   : {R_null:.5f} m  (相対誤差 {radius_rel_err_null*100:.1f}%)・軸誤差 {axis_err_null:.2f}°")

    # --- 3) beat-null B: 誤プリミティブ(平面 RANSAC)------------------------
    plane, _ = pcseg.fit_plane_ransac(pts, thresh=THRESH, iters=500, seed=0)
    # 平面の面残差(真の表面点に対する点-平面距離 RMS)。円筒面は平面で表せない。
    d_surf = pts[is_surf] @ plane[:3] + plane[3]
    rms_plane = float(np.sqrt(np.mean(d_surf ** 2)))
    print(f"[null-B 平面] 面残差 RMS   : {rms_plane:.5f} m  (円筒面は平面で表せない)")

    # ═══ GT 検証(既知真値と桁差で突き合わせる)═══════════════════════════
    # (a) メトロロジー: 半径 3% 以内・軸 3° 以内で復元
    assert radius_rel_err < 0.03, f"半径の相対誤差が大きい: {radius_rel_err*100:.2f}%"
    assert axis_err < 3.0, f"軸方向誤差が大きい: {axis_err:.3f}°"
    # (b) 面残差がノイズ床の水準(=本当に表面に当たっている)
    assert rms_robust < 3.0 * NOISE, f"面残差がノイズ床に収束していない: {rms_robust:.5f}"
    # (c) 合意集合は主に表面点(外れ値をきちんと排除できている)
    assert inlier_purity > 0.95, f"合意集合に外れ値が混入しすぎ: 純度 {inlier_purity:.3f}"

    # ═══ beat-null(実 op が両 null を広いマージンで上回る)══════════════════
    BEAT = 5.0
    # null-A: 非ロバスト半径は「真の失敗」(相対誤差が大きい)であることを先に確認
    assert radius_rel_err_null > 0.20, \
        f"null-A(非ロバスト)が失敗になっていない: 半径相対誤差 {radius_rel_err_null*100:.1f}%"
    # 実 op の半径誤差が非ロバストを判別的に(5 倍以上)下回る
    assert radius_rel_err * BEAT < radius_rel_err_null, \
        f"実 op が非ロバスト null を半径で上回れていない: {radius_rel_err*100:.2f}% vs {radius_rel_err_null*100:.1f}%"
    # null-B: 平面は円筒面を表せず面残差がノイズを桁で超える(=真の失敗)
    assert rms_plane > 20.0 * NOISE, \
        f"null-B(平面)残差がノイズ並み(退化): {rms_plane:.5f}"
    # 実 op の面残差が平面を判別的に(5 倍以上)下回る
    assert rms_robust * BEAT < rms_plane, \
        f"実 op が平面 null を面残差で上回れていない: {rms_robust:.5f} vs {rms_plane:.5f}"

    ratio_radius = radius_rel_err_null / max(radius_rel_err, 1e-9)
    ratio_rms = rms_plane / max(rms_robust, 1e-9)
    print(f"PASS: 30%外れ値下で円筒を復元 — 半径誤差 {radius_rel_err*100:.2f}%(<3%)・"
          f"軸誤差 {axis_err:.2f}°(<3°)・面残差 {rms_robust:.5f}m(ノイズ床)。"
          f"beat-null: 非ロバスト半径誤差 {radius_rel_err_null*100:.0f}%(={ratio_radius:.0f}x悪)/"
          f"平面残差 {rms_plane:.4f}m(={ratio_rms:.0f}x悪)を判別的に上回った")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
