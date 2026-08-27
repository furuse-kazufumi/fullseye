"""事例: テンプレート無しで体積中の平面と球を同時に検出 (parametric Hough).

問題(やさしい言葉で):
3D スキャン(CT や点群を voxel 化した体積)の中から、「平らな面(床・壁・テーブル)」と
「丸い部品(ボール・球状パーツ)」が、どこに・どんな向きで・どんな大きさで在るかを、
お手本(テンプレート)を一切持たずに当てたい。

方法:
- match3d.hough_plane_3d = 2D の Hough 直線検出を 3D に持ち上げたもの。境界 voxel の
  勾配(= 面の法線)を (法線方向 n, 原点からの距離 d) 空間へ投票し、票が集中した所を
  支配平面とする。返り値 = (法線 n(3,), 距離 d, inlier 数, 境界 voxel 総数)。
- match3d.hough_sphere_3d = 2D の Hough 円検出の 3D 版。境界 voxel が法線に沿って
  「中心候補 = p ± r·n」へ投票し、半径 r ごとに票のピークを見る。最大票の (中心, 半径)
  を球とする。返り値 = (votes, radius, center(z,y,x))。

合成データと正解 (GT):
既知の平面(法線 ntrue, 距離 dtrue)の半空間を塗り、そこから離れた位置に既知の球
(中心 ctrue, 半径 rtrue)を置き、さらに孤立ノイズ voxel を散布した体積を作る。
GT は自分で埋め込んだ ntrue / dtrue / ctrue / rtrue そのもの。座標系は (z, y, x)。

beat-the-null(素朴法との比較 = 手法の価値を測る零点):
- 平面: 占有 voxel 全部を素朴に主成分分析(PCA)で平面近似すると、塗りつぶした塊の
  形・球・ノイズに引きずられ、真の法線から大きく外れる。
- 球: 占有 voxel 全部の重心を素朴に球中心とすると、大きな平面の塊に引かれて真の中心から
  大きく外れる。
Hough は「票の集中で支配構造だけを取り出す」ため、この素朴法を明確に上回る。
それを実測して assert する(素朴法の誤差 >> Hough の誤差、かつ Hough は GT に一致)。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import match3d as M


def angle_between_deg(a, b):
    """2 つの向きの間の角度(度)。法線は符号反転が同義なので |cos| で測る。"""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    a = a / (np.linalg.norm(a) + 1e-12)
    b = b / (np.linalg.norm(b) + 1e-12)
    cos = abs(float(np.dot(a, b)))
    return float(np.degrees(np.arccos(np.clip(cos, 0.0, 1.0))))


def build_scene(n=48, n_true=(0.3, 0.5, 0.8), d_true=18.0,
                c_true=(34, 30, 33), r_true=8.0, n_noise=120, seed=0):
    """既知の平面 + 既知の球 + 散布ノイズ を埋め込んだ体積を作る (座標系 z,y,x)。

    平面: 半空間 n·p < d を sigmoid で塗る(iso=0.5 の等値面がちょうど n·p = d の平面)。
    球  : 中心からの距離 < r を sigmoid で塗る。球は平面の空側に置き、表面全体を露出させる。
    ノイズ: 空領域に孤立 voxel を散布(素朴な重心/PCA を汚す外れ値)。
    返り値: (vol, n_true(正規化), d_true, c_true, r_true)。
    """
    nt = np.asarray(n_true, float)
    nt = nt / np.linalg.norm(nt)
    z, y, x = np.mgrid[0:n, 0:n, 0:n].astype(float)

    # 平面(半空間 n·p < d を塗る)。等値面 0.5 が n·p = d。
    signed = nt[0] * z + nt[1] * y + nt[2] * x - d_true
    vol_plane = 1.0 / (1.0 + np.exp(signed / 1.0))

    # 球(中心 c, 半径 r の充実球)。
    cz, cy, cx = c_true
    rdist = np.sqrt((z - cz) ** 2 + (y - cy) ** 2 + (x - cx) ** 2)
    vol_sphere = 1.0 / (1.0 + np.exp((rdist - r_true) / 1.0))

    vol = np.maximum(vol_plane, vol_sphere)

    # 散布ノイズ: 平面の空側(n·p > d)にランダムな孤立 voxel を立てる。
    rng = np.random.default_rng(seed)
    empty = signed > 2.0          # 平面から十分空側
    empty_idx = np.argwhere(empty)
    if len(empty_idx) > 0 and n_noise > 0:
        pick = empty_idx[rng.choice(len(empty_idx),
                                    size=min(n_noise, len(empty_idx)),
                                    replace=False)]
        vol[pick[:, 0], pick[:, 1], pick[:, 2]] = 1.0

    return vol.astype(np.float64), nt, float(d_true), tuple(c_true), float(r_true)


def naive_plane_normal(vol, iso=0.5):
    """零点(平面): 占有 voxel 全部を素朴に PCA。最小分散方向を平面法線とみなす。"""
    occ = np.argwhere(vol > iso).astype(float)
    if len(occ) < 3:
        raise ValueError("占有 voxel が少なすぎて PCA できない (退化入力)")
    cov = np.cov((occ - occ.mean(0)).T)
    w, V = np.linalg.eigh(cov)          # 昇順固有値
    return V[:, 0]                      # 最小分散方向 = 素朴な法線


def naive_sphere_center(vol, iso=0.5):
    """零点(球): 占有 voxel 全部の重心を素朴に球中心とみなす。"""
    occ = np.argwhere(vol > iso).astype(float)
    if len(occ) < 3:
        raise ValueError("占有 voxel が少なすぎて重心を取れない (退化入力)")
    return occ.mean(0)


def main():
    n = 48
    n_true = (0.3, 0.5, 0.8)
    d_true = 18.0
    c_true = (34, 30, 33)
    r_true = 8.0

    vol, nt, dt, ct, rt = build_scene(
        n=n, n_true=n_true, d_true=d_true,
        c_true=c_true, r_true=r_true, n_noise=120, seed=0)

    # --- 入力の健全性チェック(退化入力で偽の結果を出さない) ---
    if vol.ndim != 3 or len(set(vol.shape)) != 1:
        raise ValueError(f"体積は立方体を期待: shape={vol.shape}")
    n_surface = int(((vol > 0.5)).sum())
    if n_surface < 50:
        raise ValueError(f"占有 voxel が少なすぎる: {n_surface}")

    # ============================================================
    # 1) 平面検出(Hough)+ 零点(素朴 PCA)
    # ============================================================
    plane = M.hough_plane_3d(vol, "cpu")
    if plane is None:
        raise RuntimeError("hough_plane_3d が平面を検出できなかった (None)")
    nrm, dval, inl, tot = plane

    # 法線の符号を GT に合わせて距離も同符号に整える(n と -n は同一平面)。
    s = 1.0 if np.dot(nrm, nt) >= 0 else -1.0
    d_aligned = s * dval

    plane_angle = angle_between_deg(nrm, nt)
    plane_d_err = abs(d_aligned - dt)
    inlier_frac = inl / max(tot, 1)

    null_normal = naive_plane_normal(vol)
    null_plane_angle = angle_between_deg(null_normal, nt)

    print("=== 平面検出 (hough_plane_3d) ===")
    print(f"真の法線                 : [{nt[0]:.3f}, {nt[1]:.3f}, {nt[2]:.3f}]")
    print(f"検出法線                 : [{s*nrm[0]:.3f}, {s*nrm[1]:.3f}, {s*nrm[2]:.3f}]")
    print(f"法線角度誤差             : {plane_angle:.3f} 度")
    print(f"距離 d  真値 / 検出       : {dt:.3f} / {d_aligned:.3f}  (誤差 {plane_d_err:.3f})")
    print(f"inlier 率                : {inlier_frac:.3f}  ({inl}/{tot})")
    print(f"零点(素朴PCA)の角度誤差 : {null_plane_angle:.3f} 度")

    # ============================================================
    # 2) 球検出(Hough)+ 零点(素朴 重心)
    # ============================================================
    sphere = M.hough_sphere_3d(vol, "cpu", radii=range(5, 13))
    if sphere is None:
        raise RuntimeError("hough_sphere_3d が球を検出できなかった (None)")
    votes, rad, center = sphere

    center = np.asarray(center, float)
    ct_arr = np.asarray(ct, float)
    center_err = float(np.max(np.abs(center - ct_arr)))     # 最大成分誤差 (voxel)
    radius_err = abs(rad - rt)

    null_center = naive_sphere_center(vol)
    null_center_err = float(np.max(np.abs(null_center - ct_arr)))

    print()
    print("=== 球検出 (hough_sphere_3d) ===")
    print(f"真の中心 (z,y,x)         : ({ct[0]}, {ct[1]}, {ct[2]})")
    print(f"検出中心 (z,y,x)         : ({center[0]:.0f}, {center[1]:.0f}, {center[2]:.0f})")
    print(f"中心誤差 (最大成分)      : {center_err:.3f} voxel")
    print(f"半径  真値 / 検出        : {rt:.3f} / {rad:.3f}  (誤差 {radius_err:.3f})")
    print(f"票数                     : {votes:.0f}")
    print(f"零点(素朴重心)の中心誤差: {null_center_err:.3f} voxel")

    # ============================================================
    # 3) GT 検証 + beat-the-null の assert
    # ============================================================
    # -- 平面: Hough は GT に一致し、素朴 PCA を明確に上回る --
    assert plane_angle < 3.0, f"平面の法線角度誤差が大きすぎる: {plane_angle:.3f} 度"
    assert plane_d_err < 1.5, f"平面の距離誤差が大きすぎる: {plane_d_err:.3f}"
    assert inlier_frac > 0.7, f"inlier 率が低すぎる: {inlier_frac:.3f}"
    assert plane_angle < 0.5 * null_plane_angle, (
        f"平面が零点を上回っていない: hough {plane_angle:.3f} 度 vs 素朴PCA "
        f"{null_plane_angle:.3f} 度")

    # -- 球: Hough は GT に一致し、素朴 重心を明確に上回る --
    assert center_err <= 2.0, f"球の中心誤差が大きすぎる: {center_err:.3f} voxel"
    assert radius_err < 1.5, f"球の半径誤差が大きすぎる: {radius_err:.3f}"
    assert center_err < 0.5 * null_center_err, (
        f"球が零点を上回っていない: hough {center_err:.3f} voxel vs 素朴重心 "
        f"{null_center_err:.3f} voxel")

    print()
    print(f"PASS: 平面 法線誤差 {plane_angle:.2f}度 (素朴PCA {null_plane_angle:.1f}度) / "
          f"距離誤差 {plane_d_err:.2f} / inlier {inlier_frac:.2f}; "
          f"球 中心誤差 {center_err:.2f}voxel (素朴重心 {null_center_err:.1f}voxel) / "
          f"半径誤差 {radius_err:.2f} — Hough が両方で零点を明確に上回った")


if __name__ == "__main__":
    main()
