# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 構造化光スキャナ 1 台ぶんを閉ループで回す(投影 → 撮影 → 復号 → 三角測量 → 真値照合)。

やりたいこと(素朴な言葉で): 実際の 3D スキャナは「プロジェクタで縞と縞番号を投げ、カメラで
撮り、位相から投影機のどのコラムに照らされたかを画素ごとに当て、視線とコラム平面の交点を
取って距離を出す」。ここではその一台ぶんを **fullseye の op だけで丸ごと組み**、しかも
**レンダラが持っている真の深度**と突き合わせて mm で採点する。

既存の `structured_light.py` との違い: あちらは既知の高さマップから縞画像を**合成**して
位相→高さの較正式を検証する(1 次元の比例関係)。こちらは実際に三角形メッシュを**描画**し、
投影機側からの遮蔽(影)まで含めて撮影を作り、**三角測量の幾何を解いて**深度に戻す。
つまり「較正定数 k を当てる」のではなく「スキャナの幾何そのもの」を検証する。

方法(op の鎖):
    メッシュ(球+段差箱+傾いた床)
      -> render3d.render_mesh      : カメラ深度(**真値**)/ 法線 / シルエット
      -> render3d.render_mesh      : 投影機視点の深度 = 影判定(投影機から見えない画素を捨てる)
      -> camera.depth_to_points    : 画素 -> カメラ系 3D 点(真値の点群)
      -> (投影機へ射影)            : 各画素が照らされている投影機コラム u_p(真値)
      -> 撮影の合成                 : 位相シフト 4 枚 + Gray code 9 面 + 全白 1 枚
      -> fringe.wrapped_phase      : 高精度だが 2π 不定の巻き込み位相
      -> fringe.graycode_decode    : 粗いが絶対のコラム番号(整数)
      -> fringe.absolute_phase     : 上の 2 つを合わせて絶対位相(次数を画素ごとに確定)★新 op
      -> fringe.triangulate_column : コラム -> 視線とコラム平面の交点 -> 深度 Z      ★新 op

検証(GT): 深度の真値は `render_mesh` が z-buffer で出したもの。復元深度との差を mm で測る
(シーンは mm 単位: 球 φ60、カメラ距離 420、基線 120)。

beat-the-null(零点を上回る): 同じ撮影から 2 つの零点を作る。
  (a) **Gray code だけ**(位相シフトを使わない): コラムが整数に量子化され、深度が階段になる。
  (b) **位相だけ**(Gray を使わず次数 0 と決め打ち): 2π 不定性が残り深度が桁で壊れる。
実手法(両者の合成)が (a) を RMSE で明確に下回り、(b) を桁で下回ることを assert する。
「小さい誤差が出た」ではなく「どちらの零点より判別的に良い」ことを示す。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import camera
import render3d
from fringe import (absolute_phase, graycode_decode, triangulate_column,
                    wrapped_phase)

CAM_W, CAM_H = 240, 180          # カメラ解像度(小さくても幾何の検証には十分)
PROJ_W, PROJ_H = 512, 512        # 投影機の解像度(Gray code は 9 ビットで 512 コラム)
GRAY_BITS = 9                    # 2**9 = 512 = PROJ_W(コラム番号を過不足なく符号化)
FREQ = 24                        # 投影機幅を横切る縞の本数(1 周期 = 512/24 = 21.3 px)
N_STEPS = 4                      # 位相シフト枚数
NOISE = 0.01                     # 撮影ノイズ(輝度 [0,1] に対する標準偏差)


def _sphere(center, radius, n_lat=24, n_lon=48):
    """緯度経度グリッドの球メッシュ (V, F)。"""
    lat = np.linspace(0.0, np.pi, n_lat)
    lon = np.linspace(0.0, 2.0 * np.pi, n_lon, endpoint=False)
    la, lo = np.meshgrid(lat, lon, indexing="ij")
    v = np.stack([np.sin(la) * np.cos(lo), np.sin(la) * np.sin(lo), np.cos(la)], -1)
    V = (v.reshape(-1, 3) * radius) + np.asarray(center, float)
    f = []
    for i in range(n_lat - 1):
        for j in range(n_lon):
            a = i * n_lon + j
            b = i * n_lon + (j + 1) % n_lon
            f.append([a, b, a + n_lon])
            f.append([b, b + n_lon, a + n_lon])
    return V, np.asarray(f, np.int64)


def _box(lo, hi):
    """軸平行な箱メッシュ (V, F)(段差 = 位相アンラップが繋げない不連続を作る)。"""
    lo = np.asarray(lo, float); hi = np.asarray(hi, float)
    V = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1])
                  for z in (lo[2], hi[2])], float)
    F = np.array([[0, 1, 3], [0, 3, 2], [4, 7, 5], [4, 6, 7], [0, 4, 5], [0, 5, 1],
                  [2, 3, 7], [2, 7, 6], [0, 2, 6], [0, 6, 4], [1, 5, 7], [1, 7, 3]], np.int64)
    return V, F


def _plane(size, z):
    """z = const の床(2 三角形)。"""
    s = float(size)
    V = np.array([[-s, -s, z], [s, -s, z], [s, s, z], [-s, s, z]], float)
    return V, np.array([[0, 1, 2], [0, 2, 3]], np.int64)


def _merge(parts):
    Vs, Fs, off = [], [], 0
    for V, F in parts:
        Vs.append(V); Fs.append(F + off); off += len(V)
    return np.concatenate(Vs), np.concatenate(Fs)


def _to_gray_bitplanes(code, bits):
    """整数コード(H,W) → Gray 符号のビット面 (bits,H,W)(MSB first、明=1/暗=0)。"""
    gray = code ^ (code >> 1)
    return np.stack([(gray >> (bits - 1 - i)) & 1 for i in range(bits)]).astype(np.float64)


def main() -> None:
    print("=" * 78)
    print("構造化光スキャナの閉ループ: 投影 → 撮影 → 復号 → 三角測量 → 真値照合")
    print("=" * 78)

    # --- 1) シーン(mm 単位)。段差箱は「位相を空間的に繋げない不連続」をわざと作る ---
    V, F = _merge([_sphere((0.0, 0.0, 30.0), 30.0),
                   _box((-90.0, -20.0, 0.0), (-45.0, 40.0, 28.0)),
                   _plane(160.0, 0.0)])

    # --- 2) カメラと投影機(基線 120 mm 横にずらす = 三角測量の分解能を作る) ---
    target = np.array([0.0, 0.0, 20.0])
    cam_eye = target + np.array([0.0, -380.0, 180.0])
    proj_eye = target + np.array([120.0, -360.0, 190.0])
    pose_c = render3d.look_at(cam_eye, target, up=(0, 0, 1))
    pose_p = render3d.look_at(proj_eye, target, up=(0, 0, 1))
    K_c = render3d.intrinsics_from_fov(40.0, CAM_W, CAM_H)
    K_p = render3d.intrinsics_from_fov(40.0, PROJ_W, PROJ_H)

    # カメラ系 → 投影機系: X_p = R·X_c + t
    # ★ 座標系の落とし穴: `look_at` は gluLookAt 規約(カメラは -Z を向き +Y が上)で
    # 姿勢を作るが、`render_mesh` はその Vc を (x, -y, -z) に直してから K を掛ける
    # (= depth_to_points / K と同じ CV 規約、depth は +Z 前方)。三角測量は CV 規約の
    # 側で閉じているので、姿勢も FLIP を掛けてから合成する。ここを飛ばすと投影機が
    # カメラの背後を向き、深度は「もっともらしい大きさ」のまま全部間違う
    # (最初の実行がまさにそれで、RMSE 78 mm = 零点と見分けがつかなかった)。
    FLIP = np.diag([1.0, -1.0, -1.0])
    Rc, tc = FLIP @ pose_c[:3, :3], FLIP @ pose_c[:3, 3]
    Rp, tp = FLIP @ pose_p[:3, :3], FLIP @ pose_p[:3, 3]
    R = Rp @ Rc.T
    t = tp - R @ tc
    print(f"シーン: 球 φ60 + 段差箱 + 床 / カメラ距離 {np.linalg.norm(cam_eye - target):.0f} mm "
          f"/ 基線 {np.linalg.norm(cam_eye - proj_eye):.0f} mm")

    # --- 3) 描画: カメラ深度が**真値**、投影機深度が**影判定** ---
    view = render3d.render_mesh(V, F, pose=pose_c, intrinsics=K_c,
                                width=CAM_W, height=CAM_H, background=np.nan)
    depth_gt = view["depth"]
    sil = view["silhouette"] > 0
    pview = render3d.render_mesh(V, F, pose=pose_p, intrinsics=K_p,
                                 width=PROJ_W, height=PROJ_H, background=np.nan)
    depth_proj = pview["depth"]

    # --- 4) 各画素が照らされている投影機コラム u_p(真値)と、投影機からの可視性 ---
    Xc = camera.depth_to_points(np.where(sil, depth_gt, np.nan), K_c, organized=True)
    Xp = Xc @ R.T + t
    zp = Xp[..., 2]
    with np.errstate(invalid="ignore", divide="ignore"):
        up = K_p[0, 0] * Xp[..., 0] / zp + K_p[0, 2]
        vp = K_p[1, 1] * Xp[..., 1] / zp + K_p[1, 2]
    inside = (zp > 0) & (up >= 0) & (up <= PROJ_W - 1) & (vp >= 0) & (vp <= PROJ_H - 1)
    ui = np.clip(np.nan_to_num(np.round(up)), 0, PROJ_W - 1).astype(np.int64)
    vi = np.clip(np.nan_to_num(np.round(vp)), 0, PROJ_H - 1).astype(np.int64)
    # 影: 投影機から見た深度より 1 mm 以上奥にある画素は、その光線が手前で遮られている
    seen = np.isfinite(depth_proj[vi, ui]) & (zp <= depth_proj[vi, ui] + 1.0)
    lit = sil & inside & np.nan_to_num(seen, nan=False) & np.isfinite(up)

    # --- 5) 撮影の合成(陰影 × パターン + ノイズ) ---
    #   投影機中心のカメラ系座標 = R⁻¹(0 − t)。そこへ向く方向で Lambert 陰影を作る。
    #   斜入射(cos < 0.15)の面は投影機の光がほとんど届かず、実機でも計測できない。
    #   `lit` から外す(残すと「暗い画素の復号が壊れた」だけの外れ値が RMSE を支配する)。
    proj_c = -R.T @ t
    with np.errstate(invalid="ignore"):
        Ldir = proj_c - Xc
        Ldir = Ldir / np.maximum(np.linalg.norm(Ldir, axis=-1, keepdims=True), 1e-9)
        n_cv = view["normals"] @ FLIP           # 法線も同じ FLIP で CV 規約へ
        cos_i = np.nan_to_num(np.einsum("ijk,ijk->ij", n_cv, Ldir))
    lit = lit & (cos_i > 0.15)
    shade = np.where(lit, 0.85 * cos_i, 0.0)
    print(f"照らされた画素: {int(lit.sum())} / {int(sil.sum())} "
          f"(シルエット内、影と斜入射 cos<=0.15 を除く) = {100 * lit.sum() / max(sil.sum(), 1):.1f}%")

    rng = np.random.default_rng(7)
    phase_true = 2.0 * np.pi * FREQ * np.nan_to_num(up) / PROJ_W
    shots = np.stack([
        np.clip(shade * (0.5 + 0.5 * np.cos(phase_true - 2.0 * np.pi * n / N_STEPS))
                + rng.normal(0.0, NOISE, shade.shape), 0.0, 1.0) for n in range(N_STEPS)])
    planes = _to_gray_bitplanes(ui, GRAY_BITS)
    def shoot(pat):
        return np.clip(shade[None] * pat + rng.normal(0.0, NOISE, pat.shape), 0.0, 1.0)
    # 相補 Gray code(Inokuchi 1984 の実務標準): 各ビット面とその反転を撮り、明暗を
    # **画素ごとに比べて**ビットを決める。反射率・陰影・環境光が両方に同じだけ乗るので
    # 打ち消え、固定しきい値のように「暗い画素だけ誤読する」ことがない。
    bits_hi, bits_lo = shoot(planes), shoot(1.0 - planes)
    bits_cmp = (bits_hi > bits_lo).astype(np.float64)
    n_shots = N_STEPS + 2 * GRAY_BITS
    print(f"撮影枚数: 位相シフト {N_STEPS} + 相補 Gray {2 * GRAY_BITS} = {n_shots} 枚 "
          f"/ ノイズ σ={NOISE}")

    # --- 6) 復号: 位相(精密・不定) + Gray(粗い・絶対) → 絶対位相 → コラム ---
    wrapped = wrapped_phase(shots)
    col_coarse = graycode_decode(bits_cmp, thresh=0.5).astype(np.float64)
    n_bad = int((lit & (np.abs(col_coarse - np.nan_to_num(np.round(up))) > 0)).sum())
    print(f"Gray 復号の誤り: {n_bad} / {int(lit.sum())} 画素 "
          f"({100 * n_bad / max(int(lit.sum()), 1):.3f}%)")
    coarse_phase = 2.0 * np.pi * FREQ * col_coarse / PROJ_W
    phi_abs = absolute_phase(wrapped, coarse_phase)
    col_hybrid = phi_abs * PROJ_W / (2.0 * np.pi * FREQ)

    # --- 7) 三角測量: コラム → 視線とコラム平面の交点 → 深度 ---
    def depth_of(col):
        d = triangulate_column(np.where(lit, col, np.nan), K_c, K_p, R, t)
        return d

    depth_hybrid = depth_of(col_hybrid)
    depth_gray = depth_of(col_coarse)                      # null (a): 整数コラムのみ
    depth_phase = depth_of(wrapped * PROJ_W / (2.0 * np.pi * FREQ))  # null (b): 次数 0 決め打ち

    # --- 8) GT 照合(mm) ---
    def stats(d):
        m = lit & np.isfinite(d) & np.isfinite(depth_gt)
        e = np.abs(d[m] - depth_gt[m])
        return float(np.sqrt(np.mean(e ** 2))), float(np.median(e)), int(m.sum())

    rmse_h, med_h, n_h = stats(depth_hybrid)
    rmse_g, med_g, _ = stats(depth_gray)
    rmse_p, med_p, _ = stats(depth_phase)
    span = float(np.nanmax(depth_gt[sil]) - np.nanmin(depth_gt[sil]))
    print(f"深度レンジ(真値)        : {span:.1f} mm")
    print(f"実手法 Gray+位相 の RMSE : {rmse_h:.4f} mm (中央値 {med_h:.4f} mm, {n_h} 画素)")
    print(f"null(a) Gray だけ  RMSE : {rmse_g:.4f} mm (中央値 {med_g:.4f} mm)")
    print(f"null(b) 位相だけ   RMSE : {rmse_p:.4f} mm (中央値 {med_p:.4f} mm)")
    print(f"零点比: Gray だけの {rmse_g / max(rmse_h, 1e-12):.1f} 倍良い / "
          f"位相だけの {rmse_p / max(rmse_h, 1e-12):.0f} 倍良い")

    # GT: 三角測量が真値深度を mm オーダで再現する(深度レンジの 1% 未満)。
    assert n_h > 0.5 * lit.sum(), f"復元できた画素が少なすぎる: {n_h} / {int(lit.sum())}"
    assert rmse_h < 0.01 * span, f"実手法の RMSE が深度レンジの 1% を超える: {rmse_h:.4f} mm"
    # 零点を判別的に上回る。
    assert rmse_h < rmse_g, f"Gray だけの零点に勝てていない: {rmse_h:.4f} >= {rmse_g:.4f}"
    assert rmse_p > 10.0 * rmse_g, "位相だけの零点が壊れていない(2π 不定性が効いていない)"
    assert rmse_h < 0.1 * rmse_p, f"位相だけの零点に判別的に勝てていない: {rmse_h:.4f} vs {rmse_p:.4f}"

    print(f"PASS: 描画した実シーンを {n_shots} 枚の撮影から三角測量し、真値深度を RMSE {rmse_h:.3f} mm "
          f"(レンジ {span:.0f} mm の {100 * rmse_h / span:.3f}%)で再現。"
          f"Gray だけ({rmse_g:.3f} mm)・位相だけ({rmse_p:.1f} mm)の零点を判別的に上回る")


if __name__ == "__main__":
    main()
