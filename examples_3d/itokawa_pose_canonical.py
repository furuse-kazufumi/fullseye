# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""itokawa_pose_canonical — 小惑星の姿勢を主成分で正準化する。

【この例が解く現実問題】
探査機やレーダーが小惑星の形状点群を得たとき、その「向き(姿勢)」は撮影ジオメトリ
まかせでバラバラになる。形状カタログと比較したり、複数観測を重ねたりするには、まず
各点群を **形状固有の正準姿勢** に揃える必要がある。剛体の主慣性軸(= 点群の主成分軸/
PCA 軸)は形状に固定された座標系なので、これに合わせれば「未知の回転で置かれた小惑星」を
決まった向きへ引き戻せる。イトカワは 558×301×242 m の細長い非対称体で、最長軸が
はっきりしている(固有値比 ~4:1)ため、主軸による正準化が符号を除いて一意に決まる。

対象データ: studio_assets/sample_3d/itokawa_points.npy
    近地球小惑星 25143 イトカワ(JAXA はやぶさ / Gaskell 形状モデル、public-domain、
    NASA PDS 併載)を間引いた実測の表面点群(float32, ~3000 点)。

使う op: match3d.moment_axes(点群 → 重心・主軸・固有値)。

検証: 未知回転 R を掛けたあと主軸を再計算し、(1) 各主軸が「R × 元の主軸」と符号を除いて
一致すること(|cos|≈1)、(2) 両方を主軸フレームへ正準化(歪度で符号を確定)すると
点群が一致することを assert する。
"""
import sys
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

# --- 自己完結: リポジトリルートを import パスに載せて fullseye モジュールを解決 ---
_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

import match3d    # moment_axes(点群 → 重心・主軸・固有値)
import metrics3d  # chamfer_distance(正準化後の一致度)

DATA = _REPO / "studio_assets" / "sample_3d" / "itokawa_points.npy"


def canonicalize(points):
    """点群を主軸フレームへ正準化して返す。

    重心を原点に移し、主軸(match3d.moment_axes、固有値降順で列=主軸)へ射影する。
    固有ベクトルは符号が任意なので、各軸方向の **歪度(3次モーメント)** の符号で向きを確定
    する。非対称なイトカワは各軸の歪度が明確に非ゼロなので、符号が一意に決まる。
    """
    c, axes, vals = match3d.moment_axes(points)
    q = (points - c) @ axes            # 主軸フレームでの座標
    skew = np.mean(q ** 3, axis=0)     # 各主軸方向の歪度(向きを確定する符号)
    sign = np.where(skew >= 0.0, 1.0, -1.0)
    return q * sign, axes, vals, skew


def main():
    pts = np.load(DATA).astype(np.float64)
    pts = pts - pts.mean(axis=0)       # 重心を原点へ
    extent = pts.max(axis=0) - pts.min(axis=0)
    diag = float(np.linalg.norm(extent))

    # --- 元の姿勢の主軸(グラウンドトゥルース) ---
    c0, axes0, vals0, skew0 = canonicalize(pts)

    print("=== グラウンドトゥルース(元の姿勢) ===")
    print(f"外接寸法 (m)      : {extent[0]:.1f} x {extent[1]:.1f} x {extent[2]:.1f}")
    print(f"主慣性固有値      : {vals0[0]:.1f}, {vals0[1]:.1f}, {vals0[2]:.1f}")
    print(f"最長:次           : 比 = {vals0[0] / vals0[1]:.2f}(>1 なので最長軸は一意)")
    print(f"各軸の歪度        : {skew0[0]:.1f}, {skew0[1]:.1f}, {skew0[2]:.1f}(符号確定に使用)")

    # --- 未知の回転で小惑星を置き直す ---
    R_unknown = Rotation.from_rotvec(np.array([0.30, 0.70, 0.60]) /
                                     np.linalg.norm([0.30, 0.70, 0.60]) *
                                     np.radians(50.0)).as_matrix()
    pts_rot = pts @ R_unknown.T
    _, axes1, vals1, _ = canonicalize(pts_rot)

    # --- 検証1: 回転後の主軸が「R × 元の主軸」と符号を除いて一致するか ---
    print("\n=== 検証1: 主軸の回復(符号を除く) ===")
    cos_axes = []
    for i in range(3):
        expected = R_unknown @ axes0[:, i]     # 回転で主軸もこう動くはず
        cos = abs(float(np.dot(axes1[:, i], expected)))
        cos_axes.append(cos)
        print(f"主軸{i}: |cos(回復, 期待)| = {cos:.6f}")
    assert all(c > 0.999 for c in cos_axes), \
        f"主軸が回復できていない: {cos_axes}"

    # --- 検証2: 両方を正準化すると同じ姿勢に揃うか ---
    q_orig, _, _, _ = canonicalize(pts)
    q_rot, _, _, _ = canonicalize(pts_rot)
    canon_chamfer = metrics3d.chamfer_distance(q_orig, q_rot)
    rel = canon_chamfer / diag
    print("\n=== 検証2: 正準化後の一致(未知回転を除去) ===")
    print(f"正準化点群どうしの chamfer = {canon_chamfer:.3e} m "
          f"(外接対角 {diag:.1f} m の {rel:.2e} 倍)")
    assert rel < 1e-6, f"正準化後に一致しない: 相対 chamfer = {rel:.2e}"

    print("\nPASS: 未知回転で置かれたイトカワを主成分で正準姿勢へ正しく引き戻せた"
          "(最長軸が明確なため符号を除いて一意)。")


if __name__ == "__main__":
    main()
