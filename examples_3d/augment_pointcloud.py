"""事例: 学習用 3D 点群を「性質を保証したまま」ランダムに崩すデータ拡張 (augmentation).

素朴な問題(平易な言葉で):
    深度カメラや LiDAR で撮った点群 1 サンプルから、学習を頑健にするための variant を
    たくさん作りたい。ただし「ランダムに崩す」だけでは、拡張が本当に狙い通りに効いて
    いるか分からない。回転は形を歪めていないか? scale は指定倍率どおりか? dropout は
    指定割合ちょうど点を減らしたか? jitter のノイズ量は指定 sigma どおりか?

方法:
    既知の合成点群(=ground truth)に pcl_augment の 4 つの拡張を適用し、各拡張が
    保証する「共変/不変な性質」を数値で確かめる:
      - random_rotation : 剛体回転なので点対間距離は不変(形は保存)、向きだけ変わる。
      - random_scale    : scaled = points * s なので全点間距離がちょうど s 倍(共変)。
      - random_dropout  : 残る点数はちょうど round((1-ratio)*N)。
      - jitter          : 残差(拡張後-元)の標準偏差が指定 sigma に一致。
    最後に 4 つを連鎖 (rotation → scale → jitter → dropout) し、合成後も
    「距離が s 倍」「点数が指定どおり減る」という複合的性質が保たれることを確認する。

Ground truth と beat-the-null:
    合成点群は自分で作るので、各主張の期待値(距離不変/s 倍/残点数/sigma)は既知。
    比較の null は「恒等変換(何も崩さない)」。恒等は各主張の期待値と有意に食い違う:
      - 回転の null は点を全く動かさない(平均変位 0)→「向きが変わる」を満たさない。
      - scale の null は距離比 1.0(≠ s)。
      - dropout の null は点数 N(≠ round((1-ratio)*N))。
      - jitter の null は残差 std 0(≠ sigma)。
    各拡張が恒等 null を判別的に上回る(=主張の期待値に一致する)ことを assert する。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# リポジトリ直下 (pcl_augment.py の在り処) を import path へ。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pcl_augment import jitter, random_rotation, random_scale, random_dropout  # noqa: E402


def make_cloud(n: int = 600, seed: int = 0) -> np.ndarray:
    """非対称な直方体 (10x6x3) の内部に一様サンプルした既知の点群を返す。

    3 辺すべて異なる=非対称なので、回転で「向きが変わった」ことが変位量として現れる。
    """
    rng = np.random.default_rng(seed)
    dims = np.array([10.0, 6.0, 3.0])
    return rng.random((n, 3)) * dims


def upper_pairwise_dists(P: np.ndarray) -> np.ndarray:
    """点群の上三角(i<j)ペア間ユークリッド距離ベクトルを返す(対角の 0 を除く)。"""
    diff = P[:, None, :] - P[None, :, :]
    D = np.sqrt(np.sum(diff * diff, axis=-1))
    iu = np.triu_indices(P.shape[0], k=1)
    return D[iu]


def validate_cloud(P: np.ndarray) -> np.ndarray:
    """形状 (N,3)・N>=2・有限・非縮退(座標が一致しない)を検証した距離ベクトルを返す。

    縮退入力(全点一致など)を黙って通すと距離比が 0/0 になり結果を偽装しかねないため、
    ここで fail-closed に弾く。"""
    if P.ndim != 2 or P.shape[1] != 3:
        raise ValueError(f"points must be (N, 3), got shape {P.shape}")
    if P.shape[0] < 2:
        raise ValueError(f"need at least 2 points, got {P.shape[0]}")
    if not np.all(np.isfinite(P)):
        raise ValueError("points contain non-finite values")
    d0 = upper_pairwise_dists(P)
    if d0.size == 0 or np.min(d0) <= 0.0 or not np.all(np.isfinite(d0)):
        raise ValueError("degenerate cloud: coincident or non-finite pairwise distances")
    return d0


def main() -> None:
    P = make_cloud(n=600, seed=0)
    d0 = validate_cloud(P)                       # 元の点対距離(=不変量の基準)
    n = P.shape[0]
    scale = float(np.linalg.norm(P.max(0) - P.min(0)))   # 物体の対角長 ~ 12

    print(f"点数 N                       : {n}")
    print(f"物体スケール(対角長)         : {scale:.3f}")

    # --- 1) random_rotation: 剛体回転 → 距離不変・向きだけ変わる ------------------ #
    rotated, R = random_rotation(P, seed=1)
    if not np.allclose(R @ R.T, np.eye(3), atol=1e-9) or abs(np.linalg.det(R) - 1.0) > 1e-9:
        raise ValueError("random_rotation returned a non-rotation matrix")
    d_rot = upper_pairwise_dists(rotated)
    rot_dist_err = float(np.max(np.abs(d_rot - d0)))          # 距離不変量のズレ
    real_disp = float(np.mean(np.linalg.norm(rotated - P, axis=1)))  # 実際の平均変位
    null_disp = 0.0                                           # 恒等 null は動かさない
    print(f"[rotation] 点対距離の最大誤差 : {rot_dist_err:.3e}  (剛体回転なら ~0)")
    print(f"[rotation] 平均変位 real/null : {real_disp:.3f} / {null_disp:.3f}  "
          f"(向きが変わったか)")
    assert rot_dist_err < 1e-8 * max(scale, 1.0), "回転が形を歪めている(距離不変が破れた)"
    assert real_disp > 0.1 * scale, "回転で向きが変わっていない(恒等 null と区別できない)"

    # --- 2) random_scale: scaled = points * s → 全点間距離が s 倍 ---------------- #
    scaled, s = random_scale(P, lo=1.5, hi=2.5, seed=2)
    d_scl = upper_pairwise_dists(scaled)
    real_ratio = float(np.median(d_scl / d0))
    ratio_err = float(np.max(np.abs(d_scl / d0 - s)))        # 全ペアで s に一致するか
    null_ratio = 1.0                                          # 恒等 null は距離比 1
    print(f"[scale] s={s:.4f}  距離比 real/null : {real_ratio:.4f} / {null_ratio:.4f}  "
          f"(最大偏差 {ratio_err:.2e})")
    assert ratio_err < 1e-6 * s, f"scale=s の距離共変が破れた(最大偏差 {ratio_err:.2e})"
    assert abs(real_ratio - s) < 1e-6 * s, "距離比が s と一致しない"
    assert abs(null_ratio - s) > 0.3, "恒等 null(比1)が s と区別できない(自明な設定)"

    # --- 3) random_dropout: 残点数 == round((1-ratio)*N) ------------------------ #
    ratio_drop = 0.3
    kept, kept_idx = random_dropout(P, ratio=ratio_drop, seed=3)
    expected_keep = int(round((1.0 - ratio_drop) * n))
    null_keep = n                                             # 恒等 null は全点残す
    print(f"[dropout] ratio={ratio_drop}  残点数 real/expected/null : "
          f"{kept.shape[0]} / {expected_keep} / {null_keep}")
    assert kept.shape[0] == expected_keep, "残点数が round((1-ratio)*N) と一致しない"
    assert np.array_equal(kept, P[kept_idx]), "kept と points[kept_idx] が一致しない"
    assert null_keep != expected_keep, "恒等 null(全点)が期待残点数と区別できない"

    # --- 4) jitter: 残差(拡張後-元)の std ≈ sigma ----------------------------- #
    sigma = 0.05 * scale
    jittered = jitter(P, sigma=sigma, seed=4)
    resid_std = float((jittered - P).std())
    null_std = 0.0                                            # 恒等 null はノイズ 0
    print(f"[jitter] sigma={sigma:.4f}  残差 std real/null : "
          f"{resid_std:.4f} / {null_std:.4f}")
    assert abs(resid_std - sigma) < 0.15 * sigma, "jitter の残差 std が sigma と乖離"
    assert resid_std > 0.5 * sigma, "残差がほぼ 0(恒等 null と区別できない)"

    # --- 5) 連鎖 rotation → scale → jitter → dropout: 複合的性質を確認 --------- #
    # rotation(距離不変) → scale(距離 s 倍) と重ねると、ノイズ前の距離は元の s 倍。
    s_fixed = 2.0
    c1, _ = random_rotation(P, seed=10)
    c2, s2 = random_scale(c1, lo=s_fixed, hi=s_fixed, seed=11)   # lo==hi で s を固定
    d_chain = upper_pairwise_dists(c2)
    chain_ratio_err = float(np.max(np.abs(d_chain / d0 - s2)))   # 回転+scale 後も s 倍か
    c3 = jitter(c2, sigma=0.01 * scale, seed=12)                 # 小ノイズを重畳
    c4, _ = random_dropout(c3, ratio=0.2, seed=13)              # 20% 欠損
    chain_expected_keep = int(round(0.8 * n))
    print(f"[chain] rot+scale の距離比偏差 : {chain_ratio_err:.2e}  (s={s2:.2f})")
    print(f"[chain] 最終点数 real/expected/null : "
          f"{c4.shape[0]} / {chain_expected_keep} / {n}")
    assert chain_ratio_err < 1e-6 * s2, "連鎖で回転+scale の距離共変(s倍)が破れた"
    assert c4.shape[0] == chain_expected_keep, "連鎖後の残点数が期待と一致しない"
    assert n != chain_expected_keep, "恒等 null(全点)が連鎖後の期待残点数と区別できない"

    print("PASS: 4 拡張とも指定パラメータどおり(回転=距離不変+向き変化, "
          f"scale=s{s:.2f}倍, dropout={expected_keep}点, jitter std≈{sigma:.3f}) "
          "かつ恒等 null を判別的に上回り、連鎖でも複合性質を保持")


if __name__ == "__main__":
    main()
