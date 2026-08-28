# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 円錐・トーラス・楕円体を点群に当てはめる (extended primitive fitting).

実世界の問題:
    3D スキャンや計測では、対象を「解析的なプリミティブ 1 個」に還元できると強い。
    半径・軸・頂点といった少数のパラメータで CAD 照合・寸法検査・把持計画・姿勢推定が
    まわるからだ。球・平面・円筒までは既存の RANSAC で当たるが、曲率が場所で変わる
      - 円錐(漏斗・ノズル・面取り・砂山)
      - トーラス(O リング・配管の曲がり・ドーナツ状部品)
      - 3 軸楕円体(細胞・小惑星・慣性楕円体・扁平な粒)
    は当てられなかった。ここではこの 3 種を追加し、既知パラメータからの復元で検証する。

原理:
    - fit_cone   … 子午面での点-母線直交距離 ``a·sinα − ρ·cosα`` を least_squares で最小化。
    - fit_torus  … 点-トーラス距離 ``sqrt((ρ−R)² + a²) − r`` を least_squares で最小化。
    - fit_ellipsoid … 一般二次曲面 ``xᵀA x + b·x + c = 0`` の代数フィット(楕円体拘束下の
      一般化固有問題, Li & Griffiths 2004)。初期値不要・決定論・大域解。

検証(GT):
    既知パラメータの円錐/トーラス/楕円体の表面から点群を(小ノイズつきで)サンプルし、
      - 円錐: 頂点 apex・軸 axis・半角 half_angle
      - トーラス: 中心 center・軸 axis・主半径 R・管半径 r
      - 楕円体: 中心 center・3 半径 radii・主軸 axes
    を許容誤差内で復元できるかを assert する。当てずっぽうを排除するため、真値を数値で
    直接照合する。

beat-the-null(誤モデルの零点を判別的に上回る):
    「間違ったプリミティブ」を当てた残差(RMS 点-面距離)を基準線にする。
      - 円錐/トーラス … 球フィットと平面フィットの残差。
      - 楕円体 … 等方球フィットの残差(3 軸が異なる楕円体は 1 半径の球では表せない)。
    正しいプリミティブの残差がこれらを桁で下回って初めて「当たっている」と言える。
    誤モデルの残差はノイズの何十倍にもなる(= 形が説明できていない)ことも併せて確認する。

    注(honest): 楕円体の残差は Taubin 1 次近似の点-面距離、球の基準線は厳密な点-面距離
    を用いる。Taubin はやや過大評価なので、この比較は楕円体に不利側=保守的であり、
    それでも球を桁で下回るなら結論は堅い。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
# この例のファイル名はモジュール ``fit_primitives_ext.py`` と同名。直接実行するとスクリプトの
# 置き場所(examples_3d/)が sys.path 先頭に入り自分自身を import して循環するので、リポジトリ
# ルートを **無条件で先頭へ** 挿入して本物のモジュールを優先させる(PYTHONPATH=. が既に
# ルートを含む場合でも順序を確実にするため guard 無しで insert)。
sys.path.insert(0, str(_REPO_ROOT))

from fit_primitives_ext import fit_cone, fit_ellipsoid, fit_torus  # noqa: E402


# ═══════════════════════════════════════════════════════════════════════════
# 合成データ(既知パラメータ = ground truth)
# ═══════════════════════════════════════════════════════════════════════════
def _perp_basis(axis: np.ndarray):
    """軸に直交する正規直交基底 (e1, e2) を返す。"""
    a = axis / np.linalg.norm(axis)
    t = np.array([1.0, 0.0, 0.0]) if abs(a[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = np.cross(a, t)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(a, e1)
    return e1, e2


def sample_cone(apex, axis, half_angle, n=600, h_range=(0.5, 2.5),
                noise=0.005, seed=0):
    """既知の円錐面から点群を一様サンプル(+ ガウスノイズ)。真の頂点/軸/半角を返す。

    頂点から軸方向へ距離 h 進むと半径 ``h·tanα`` の円になる幾何を使う。
    """
    rng = np.random.default_rng(seed)
    axis = axis / np.linalg.norm(axis)
    e1, e2 = _perp_basis(axis)
    h = rng.uniform(h_range[0], h_range[1], n)
    phi = rng.uniform(0.0, 2.0 * np.pi, n)
    rad = h * np.tan(half_angle)
    pts = (apex + h[:, None] * axis
           + rad[:, None] * (np.cos(phi)[:, None] * e1 + np.sin(phi)[:, None] * e2))
    pts += rng.normal(0.0, noise, pts.shape)
    return pts


def sample_torus(center, axis, R, r, n=800, noise=0.004, seed=1):
    """既知のトーラス面から点群をサンプル(+ ノイズ)。"""
    rng = np.random.default_rng(seed)
    axis = axis / np.linalg.norm(axis)
    e1, e2 = _perp_basis(axis)
    theta = rng.uniform(0.0, 2.0 * np.pi, n)      # 主円まわり
    psi = rng.uniform(0.0, 2.0 * np.pi, n)        # 管まわり
    ring = (R + r * np.cos(psi))[:, None] * (
        np.cos(theta)[:, None] * e1 + np.sin(theta)[:, None] * e2)
    pts = center + ring + (r * np.sin(psi))[:, None] * axis
    pts += rng.normal(0.0, noise, pts.shape)
    return pts


def _random_rotation(seed):
    """行列式 +1 の直交行列(QR 分解由来)。"""
    rng = np.random.default_rng(seed)
    Q, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    if np.linalg.det(Q) < 0:
        Q[:, 0] = -Q[:, 0]
    return Q


def sample_ellipsoid(center, Rrot, radii, n=1500, noise=0.005, seed=2):
    """既知姿勢の 3 軸楕円体面から点群をサンプル(+ ノイズ)。``Rrot`` の列 = 主軸方向。"""
    rng = np.random.default_rng(seed)
    u = rng.normal(size=(n, 3))
    u /= np.linalg.norm(u, axis=1, keepdims=True)   # 単位球面上
    pts = center + (u * radii) @ Rrot.T             # 軸整列楕円体 → 回転
    pts += rng.normal(0.0, noise, pts.shape)
    return pts


# ═══════════════════════════════════════════════════════════════════════════
# beat-the-null 用の「誤モデル」フィッタ(自明ベースライン)
# ═══════════════════════════════════════════════════════════════════════════
def sphere_ls(P):
    """代数最小二乗の等方球フィット → (center(3,), radius)。"""
    A = np.hstack([2.0 * P, np.ones((len(P), 1))])
    b = (P ** 2).sum(1)
    sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    c = sol[:3]
    return c, float(np.sqrt(max(sol[3] + c @ c, 0.0)))


def plane_ls(P):
    """最小二乗平面 → (unit_normal(3,), point(3,))。法線=共分散最小主軸。"""
    c = P.mean(0)
    _, V = np.linalg.eigh((P - c).T @ (P - c))
    return V[:, 0], c


def rms_point_sphere(P):
    """球フィットの RMS 点-面距離(誤モデル基準線)。"""
    c, r = sphere_ls(P)
    return float(np.sqrt(np.mean((np.linalg.norm(P - c, axis=1) - r) ** 2)))


def rms_point_plane(P):
    """平面フィットの RMS 点-面距離(誤モデル基準線)。"""
    n, c = plane_ls(P)
    return float(np.sqrt(np.mean(((P - c) @ n) ** 2)))


def axis_angle_deg(a, b):
    """2 単位ベクトルのなす角(度)。符号無視は呼び出し側で abs を取ること。"""
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    return float(np.degrees(np.arccos(np.clip(a @ b, -1.0, 1.0))))


# ═══════════════════════════════════════════════════════════════════════════
# 描画(matplotlib Agg、無ければスキップ)
# ═══════════════════════════════════════════════════════════════════════════
def render_png(path, cone_pts, cone, torus_pts, torus, ell_pts, ell,
               cone_null, torus_null, ell_null) -> bool:
    """円錐/トーラス/楕円体の点群 + 復元表面を 3 パネルで並べて保存。成功で True。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.font_manager as fm
    except Exception:
        return False

    have = {f.name for f in fm.fontManager.ttflist}
    for cand in ("Yu Gothic", "Meiryo", "MS Gothic", "Noto Sans JP", "Malgun Gothic"):
        if cand in have:
            plt.rcParams["font.family"] = cand
            break
    plt.rcParams["axes.unicode_minus"] = False

    fig = plt.figure(figsize=(16.8, 5.6))

    # --- パネル A: 円錐 ---
    axA = fig.add_subplot(1, 3, 1, projection="3d")
    axA.scatter(cone_pts[:, 0], cone_pts[:, 1], cone_pts[:, 2],
                s=5, c="#3b6ea5", alpha=0.35, label="点群 (N=%d)" % len(cone_pts))
    apex, ax, ha = cone["apex"], cone["axis"], cone["half_angle"]
    e1, e2 = _perp_basis(ax)
    hmax = float(np.max((cone_pts - apex) @ ax))
    hg = np.linspace(0.0, hmax, 26)
    pg = np.linspace(0.0, 2.0 * np.pi, 40)
    HH, PP = np.meshgrid(hg, pg)
    rad = HH * np.tan(ha)
    Xc = apex[0] + HH * ax[0] + rad * (np.cos(PP) * e1[0] + np.sin(PP) * e2[0])
    Yc = apex[1] + HH * ax[1] + rad * (np.cos(PP) * e1[1] + np.sin(PP) * e2[1])
    Zc = apex[2] + HH * ax[2] + rad * (np.cos(PP) * e1[2] + np.sin(PP) * e2[2])
    axA.plot_wireframe(Xc, Yc, Zc, color="#e08a1e", linewidth=0.5,
                       rstride=3, cstride=2)
    axA.scatter([apex[0]], [apex[1]], [apex[2]], c="#b5670c", s=45, marker="^")
    axA.set_title("fit_cone\n半角 %.2f°(真 %.2f°)・残差 %.4f  <<  球 %.3f / 平面 %.3f"
                  % (np.degrees(ha), np.degrees(cone["gt_half_angle"]),
                     cone["residual"], cone_null["sphere"], cone_null["plane"]),
                  fontsize=9)
    axA.legend(loc="upper left", fontsize=8)

    # --- パネル B: トーラス ---
    axB = fig.add_subplot(1, 3, 2, projection="3d")
    axB.scatter(torus_pts[:, 0], torus_pts[:, 1], torus_pts[:, 2],
                s=5, c="#3b6ea5", alpha=0.30)
    c, ax, R, r = torus["center"], torus["axis"], torus["R"], torus["r"]
    e1, e2 = _perp_basis(ax)
    tg = np.linspace(0.0, 2.0 * np.pi, 46)
    sg = np.linspace(0.0, 2.0 * np.pi, 24)
    TT, SS = np.meshgrid(tg, sg)
    rr = R + r * np.cos(SS)
    Xt = c[0] + rr * (np.cos(TT) * e1[0] + np.sin(TT) * e2[0]) + r * np.sin(SS) * ax[0]
    Yt = c[1] + rr * (np.cos(TT) * e1[1] + np.sin(TT) * e2[1]) + r * np.sin(SS) * ax[1]
    Zt = c[2] + rr * (np.cos(TT) * e1[2] + np.sin(TT) * e2[2]) + r * np.sin(SS) * ax[2]
    axB.plot_wireframe(Xt, Yt, Zt, color="#27865a", linewidth=0.4,
                       rstride=2, cstride=3)
    axB.set_title("fit_torus\nR %.3f / r %.3f(真 %.2f / %.2f)・残差 %.4f  <<  球 %.3f"
                  % (R, r, torus["gt_R"], torus["gt_r"], torus["residual"],
                     torus_null["sphere"]), fontsize=9)
    axB.plot([], [], c="#27865a", label="復元トーラス面")
    axB.legend(loc="upper left", fontsize=8)

    # --- パネル C: 楕円体 ---
    axC = fig.add_subplot(1, 3, 3, projection="3d")
    axC.scatter(ell_pts[:, 0], ell_pts[:, 1], ell_pts[:, 2],
                s=5, c="#3b6ea5", alpha=0.28)
    ec, axes, radii = ell["center"], ell["axes"], ell["radii"]
    ug = np.linspace(0.0, 2.0 * np.pi, 40)
    vg = np.linspace(0.0, np.pi, 22)
    su = np.outer(np.cos(ug), np.sin(vg))
    sv = np.outer(np.sin(ug), np.sin(vg))
    sw = np.outer(np.ones_like(ug), np.cos(vg))
    Xe = (ec[0] + radii[0] * su * axes[0, 0] + radii[1] * sv * axes[0, 1]
          + radii[2] * sw * axes[0, 2])
    Ye = (ec[1] + radii[0] * su * axes[1, 0] + radii[1] * sv * axes[1, 1]
          + radii[2] * sw * axes[1, 2])
    Ze = (ec[2] + radii[0] * su * axes[2, 0] + radii[1] * sv * axes[2, 1]
          + radii[2] * sw * axes[2, 2])
    axC.plot_wireframe(Xe, Ye, Ze, color="#8e44ad", linewidth=0.4,
                       rstride=2, cstride=2)
    axC.set_title("fit_ellipsoid\n半径 [%.2f %.2f %.2f](真 [%.1f %.1f %.1f])・"
                  "残差 %.4f  <<  等方球 %.3f"
                  % (radii[0], radii[1], radii[2], ell["gt_radii"][0],
                     ell["gt_radii"][1], ell["gt_radii"][2], ell["residual"],
                     ell_null["sphere"]), fontsize=9)
    axC.plot([], [], c="#8e44ad", label="復元楕円体面")
    axC.legend(loc="upper left", fontsize=8)

    fig.suptitle("fit_primitives_ext — 円錐・トーラス・楕円体の当てはめ"
                 "(既知パラメータを復元、誤モデルの残差を桁で下回る)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return True


# ═══════════════════════════════════════════════════════════════════════════
# メイン: GT 検証 + beat-null + 描画
# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    # ─────────────────────────────────────────────────────────────────────
    # 1) 円錐
    # ─────────────────────────────────────────────────────────────────────
    gt_apex = np.array([0.3, -0.2, 0.5])
    gt_cone_axis = np.array([0.2, 0.3, 1.0]); gt_cone_axis /= np.linalg.norm(gt_cone_axis)
    gt_half = np.deg2rad(22.0)
    cone_noise = 0.005
    cone_pts = sample_cone(gt_apex, gt_cone_axis, gt_half, n=600,
                           noise=cone_noise, seed=0)
    if cone_pts.shape[1] != 3 or len(cone_pts) < 6:
        raise ValueError("円錐点群が退化(合成失敗)")

    cone = fit_cone(cone_pts)
    cone["gt_half_angle"] = gt_half
    cone_apex_err = float(np.linalg.norm(cone["apex"] - gt_apex))
    cone_ax_ang = axis_angle_deg(cone["axis"], gt_cone_axis)
    cone_half_err = abs(cone["half_angle"] - gt_half)
    cone_null = {"sphere": rms_point_sphere(cone_pts),
                 "plane": rms_point_plane(cone_pts)}

    print("[円錐] 頂点誤差 %.4f・軸誤差 %.3f°・半角 %.3f°(真 %.3f°)・残差 %.4f"
          % (cone_apex_err, cone_ax_ang, np.degrees(cone["half_angle"]),
             np.degrees(gt_half), cone["residual"]))
    print("       null 球残差 %.4f / 平面残差 %.4f(ノイズ σ=%.3f)"
          % (cone_null["sphere"], cone_null["plane"], cone_noise))

    # ─────────────────────────────────────────────────────────────────────
    # 2) トーラス
    # ─────────────────────────────────────────────────────────────────────
    gt_torus_center = np.array([-0.4, 0.6, 0.1])
    gt_torus_axis = np.array([0.1, -0.2, 1.0]); gt_torus_axis /= np.linalg.norm(gt_torus_axis)
    gt_R, gt_r = 1.2, 0.35
    torus_noise = 0.004
    torus_pts = sample_torus(gt_torus_center, gt_torus_axis, gt_R, gt_r,
                             n=800, noise=torus_noise, seed=1)
    if torus_pts.shape[1] != 3 or len(torus_pts) < 7:
        raise ValueError("トーラス点群が退化(合成失敗)")

    torus = fit_torus(torus_pts)
    torus["gt_R"], torus["gt_r"] = gt_R, gt_r
    torus_c_err = float(np.linalg.norm(torus["center"] - gt_torus_center))
    torus_ax_cos = abs(float(torus["axis"] @ gt_torus_axis))
    torus_R_err = abs(torus["R"] - gt_R)
    torus_r_err = abs(torus["r"] - gt_r)
    torus_null = {"sphere": rms_point_sphere(torus_pts),
                  "plane": rms_point_plane(torus_pts)}

    print("[トーラス] 中心誤差 %.4f・軸|cos| %.5f・R %.4f(真 %.2f)・r %.4f(真 %.2f)・残差 %.4f"
          % (torus_c_err, torus_ax_cos, torus["R"], gt_R, torus["r"], gt_r,
             torus["residual"]))
    print("           null 球残差 %.4f(ノイズ σ=%.3f)"
          % (torus_null["sphere"], torus_noise))

    # ─────────────────────────────────────────────────────────────────────
    # 3) 楕円体
    # ─────────────────────────────────────────────────────────────────────
    gt_ell_center = np.array([0.2, 0.3, -0.1])
    gt_ell_radii = np.array([1.5, 0.9, 0.5])       # 降順
    gt_ell_R = _random_rotation(seed=7)            # 列 = 主軸方向
    ell_noise = 0.005
    ell_pts = sample_ellipsoid(gt_ell_center, gt_ell_R, gt_ell_radii,
                               n=1500, noise=ell_noise, seed=2)
    if ell_pts.shape[1] != 3 or len(ell_pts) < 10:
        raise ValueError("楕円体点群が退化(合成失敗)")

    ell = fit_ellipsoid(ell_pts)
    ell["gt_radii"] = gt_ell_radii
    ell_c_err = float(np.linalg.norm(ell["center"] - gt_ell_center))
    ell_radii_rel = np.abs(ell["radii"] - gt_ell_radii) / gt_ell_radii
    # 主軸の一致(半径降順で対応、符号無視)
    ell_axis_cos = np.array([abs(float(ell["axes"][:, j] @ gt_ell_R[:, j]))
                             for j in range(3)])
    ell_null = {"sphere": rms_point_sphere(ell_pts)}

    print("[楕円体] 中心誤差 %.4f・半径 [%.3f %.3f %.3f](真 [%.1f %.1f %.1f])・"
          "主軸|cos| [%.4f %.4f %.4f]・残差 %.4f"
          % (ell_c_err, ell["radii"][0], ell["radii"][1], ell["radii"][2],
             gt_ell_radii[0], gt_ell_radii[1], gt_ell_radii[2],
             ell_axis_cos[0], ell_axis_cos[1], ell_axis_cos[2], ell["residual"]))
    print("         null 等方球残差 %.4f(ノイズ σ=%.3f)"
          % (ell_null["sphere"], ell_noise))

    # ─────────────────────────────────────────────────────────────────────
    # GT アサーション(真値を数値で照合)
    # ─────────────────────────────────────────────────────────────────────
    # 円錐
    assert cone_apex_err < 0.03, f"円錐 頂点誤差が大きい: {cone_apex_err:.4f}"
    assert cone_ax_ang < 1.5, f"円錐 軸誤差が大きい: {cone_ax_ang:.3f}°"
    assert cone_half_err < np.deg2rad(1.0), \
        f"円錐 半角誤差が大きい: {np.degrees(cone_half_err):.3f}°"
    assert cone["residual"] < 0.02, f"円錐 残差が大きい: {cone['residual']:.4f}"
    # トーラス
    assert torus_c_err < 0.02, f"トーラス 中心誤差が大きい: {torus_c_err:.4f}"
    assert torus_ax_cos > 0.999, f"トーラス 軸誤差が大きい: |cos|={torus_ax_cos:.5f}"
    assert torus_R_err < 0.02, f"トーラス R 誤差が大きい: {torus_R_err:.4f}"
    assert torus_r_err < 0.02, f"トーラス r 誤差が大きい: {torus_r_err:.4f}"
    assert torus["residual"] < 0.02, f"トーラス 残差が大きい: {torus['residual']:.4f}"
    # 楕円体
    assert ell_c_err < 0.03, f"楕円体 中心誤差が大きい: {ell_c_err:.4f}"
    assert np.all(ell_radii_rel < 0.03), \
        f"楕円体 半径の相対誤差が大きい: {ell_radii_rel}"
    assert np.all(ell_axis_cos > 0.99), \
        f"楕円体 主軸の一致が不十分: {ell_axis_cos}"
    assert ell["residual"] < 0.02, f"楕円体 残差が大きい: {ell['residual']:.4f}"

    # ─────────────────────────────────────────────────────────────────────
    # beat-the-null(誤モデルの零点を判別的に上回る = 5 倍以上小さい残差)
    # ─────────────────────────────────────────────────────────────────────
    BEAT = 5.0
    # 誤モデルの残差はノイズを大きく超える(= 形が説明できていない正当な基準線)
    assert cone_null["sphere"] > 20 * cone_noise, "円錐 球基準線がノイズ並み(退化)"
    assert cone_null["plane"] > 20 * cone_noise, "円錐 平面基準線がノイズ並み(退化)"
    assert torus_null["sphere"] > 20 * torus_noise, "トーラス 球基準線がノイズ並み(退化)"
    assert ell_null["sphere"] > 20 * ell_noise, "楕円体 等方球基準線がノイズ並み(退化)"
    # 正しいプリミティブが誤モデルを桁で下回る
    assert cone["residual"] * BEAT < cone_null["sphere"], \
        f"円錐 が球基準を判別的に下回れていない: {cone['residual']:.4f} vs {cone_null['sphere']:.4f}"
    assert cone["residual"] * BEAT < cone_null["plane"], \
        f"円錐 が平面基準を判別的に下回れていない: {cone['residual']:.4f} vs {cone_null['plane']:.4f}"
    assert torus["residual"] * BEAT < torus_null["sphere"], \
        f"トーラス が球基準を判別的に下回れていない: {torus['residual']:.4f} vs {torus_null['sphere']:.4f}"
    assert ell["residual"] * BEAT < ell_null["sphere"], \
        f"楕円体 が等方球基準を判別的に下回れていない: {ell['residual']:.4f} vs {ell_null['sphere']:.4f}"

    # ─────────────────────────────────────────────────────────────────────
    # デモ PNG
    # ─────────────────────────────────────────────────────────────────────
    out_png = _REPO_ROOT / "examples_3d" / "_gallery" / "fit_primitives_ext.png"
    drawn = render_png(out_png, cone_pts, cone, torus_pts, torus, ell_pts, ell,
                       cone_null, torus_null, ell_null)
    if drawn:
        print(f"[描画] {out_png} を保存")
    else:
        print("[描画] matplotlib 不在のため PNG はスキップ(GT アサートは実施済)")

    # ─────────────────────────────────────────────────────────────────────
    # PASS(結果と beat-null 差)
    # ─────────────────────────────────────────────────────────────────────
    cone_ratio = cone_null["sphere"] / cone["residual"]
    torus_ratio = torus_null["sphere"] / torus["residual"]
    ell_ratio = ell_null["sphere"] / ell["residual"]
    print("PASS: 円錐(頂点誤差 %.4f・半角誤差 %.3f°、残差 %.4f=球比 %.0fx改善)/ "
          "トーラス(中心誤差 %.4f・R,r 誤差 %.4f,%.4f、残差 %.4f=球比 %.0fx)/ "
          "楕円体(中心誤差 %.4f・半径相対誤差<%.1f%%、残差 %.4f=等方球比 %.0fx)を GT 復元。"
          "誤モデルの零点を全て判別的に上回った"
          % (cone_apex_err, np.degrees(cone_half_err), cone["residual"], cone_ratio,
             torus_c_err, torus_R_err, torus_r_err, torus["residual"], torus_ratio,
             ell_c_err, 100 * float(ell_radii_rel.max()), ell["residual"], ell_ratio))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
