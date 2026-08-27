"""CTボリュームから骨をセグメンテーションし、本数と体積を計測する例。

実世界の問題:
    CT スキャンから「骨だけ」を取り出し(セグメンテーション)、独立した骨が何本
    あるかを数え、それぞれの体積を測る。整形外科の骨計測、骨折片のカウント、
    インプラント設計、骨密度解析などの出発点になる基本オペレーション。

原理:
    骨は軟部組織より X線密度が高いので、しきい値処理(> 平均 + 標準偏差)で骨マスクを
    作れる。ただしこのファントムは 1 本につながった手骨メッシュをボクセル化したもので、
    指骨どうしが関節部で接触しているため、単純に連結成分ラベリングすると全部が 1 塊に
    なってしまう(実測 n=1)。そこで軽い収縮(erosion)で関節の細い接続を切ってから
    ラベリングし、個々の骨コアを数える(接触物体を分離する定番手法)。

    ラベリングには fullseye の volops.vol_label(vol_binary, connectivity=26) を使う。
    返り値は (labels, n)。※ (v, a, b) 規約ではなく 1〜2 個の位置引数を取る点に注意。
    体積(ボクセル数)は元の(収縮前)骨マスクで測る — 収縮はあくまで「数える」ための
    分離処理であり、体積の真値ではないため。
"""
from __future__ import annotations

import os
import sys

import numpy as np
from scipy import ndimage

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import volops  # fullseye: vol_label(vol_binary, connectivity=26) -> (labels, n)


def load_volume() -> np.ndarray:
    path = os.path.join(_REPO_ROOT, "studio_assets", "sample_3d", "skeleton_ct.npy")
    return np.load(path).astype(np.float64)


def main() -> int:
    vol = load_volume()
    grid_voxels = vol.size
    print(f"[GT] volume shape = {vol.shape}, total voxels = {grid_voxels}")

    # (1) しきい値処理で骨マスク。
    thr = float(vol.mean() + vol.std())
    bone_mask = vol > thr
    bone_voxels = int(bone_mask.sum())
    bone_fraction = bone_voxels / grid_voxels
    print(f"[GT] threshold = mean+std = {thr:.3f}")
    print(f"[GT] bone voxels = {bone_voxels} "
          f"({bone_fraction * 100:.2f}% of the grid)")

    # 参考: 収縮せず素直にラベリングすると接触して 1 塊になることを示す(教育目的)。
    _, n_naive = volops.vol_label(bone_mask, connectivity=26)
    print(f"[GT] naive vol_label -> n = {n_naive} 個 "
          f"(骨が関節で接触し 1 塊になる)")

    # (2) 関節の細い接続を収縮で切ってから個々の骨コアを分離してラベリング。
    struct = ndimage.generate_binary_structure(3, 3)  # 26-近傍
    separated = ndimage.binary_erosion(bone_mask, structure=struct, iterations=2)
    labels, n_bones = volops.vol_label(separated, connectivity=26)

    # (3) 成分ごとのボクセル体積(骨コア)。
    comp_sizes = np.bincount(labels.ravel())[1:]  # 0=背景を除く
    comp_sizes = np.sort(comp_sizes)[::-1]
    print(f"[GT] separated vol_label -> n = {n_bones} 個の骨成分")
    print(f"[GT] per-component voxel volumes (骨コア) = {comp_sizes.tolist()}")

    # --- 自己検証(いずれも「幾何を無視した出鱈目な結果」なら失敗する判別的検査) ---
    assert labels.shape == vol.shape, "ラベル体積の形状が元と不一致"

    # (a) 閾値マスクが本当に「密な骨」を捉えている: マスク内の平均密度はマスク外より
    #     有意に高いはず。前景をランダムに選ぶだけのマスクでは成り立たない。
    inside = float(vol[bone_mask].mean())
    outside = float(vol[~bone_mask].mean())
    print(f"[GT] 骨マスク内/外の平均密度 = {inside:.3f} / {outside:.3f} "
          f"(比 {inside / max(outside, 1e-9):.2f}x)")
    assert inside > 1.5 * outside, \
        f"閾値が密な骨を捉えていない: 内 {inside:.3f} vs 外 {outside:.3f}"

    # (b) 収縮による分離が「幾何に基づく」ことの判別: 接触で 1 塊になる naive ラベリング
    #     より多くの骨コアに分かれるはず。座標を無視するラベラーなら両者は同数で失敗する。
    assert n_bones > n_naive, \
        f"収縮分離が naive ラベリング(n={n_naive})を上回らない(幾何無視の疑い): n={n_bones}"
    assert n_bones >= 3, f"妥当な骨成分数(>=3)が得られていない: n={n_bones}"

    # (c) 骨体積はグリッドの妥当な割合(スカスカでも埋め尽くしでもない)。
    assert 0.02 < bone_fraction < 0.30, \
        f"骨体積のグリッド占有率が不自然: {bone_fraction:.4f}"
    assert int(comp_sizes.sum()) <= bone_voxels, \
        "収縮後コアの総体積が元マスクを超えるのはおかしい"

    print(f"PASS: 密度コントラスト {inside / max(outside, 1e-9):.1f}x で骨を分離、"
          f"naive の 1 塊を {n_bones} 本の骨コアへ切り分け、"
          f"総骨体積 {bone_voxels} voxel ({bone_fraction * 100:.2f}%) を計測")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
