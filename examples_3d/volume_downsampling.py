"""事例: ボリューム(3D CT)の間引きで重い解析を回せるサイズに落とす (mesh_process).

工業用CT・ラミノグラフィのボリュームは 260^3 = 1758 万ボクセルにもなり、Hessian
固有値を使う重い op(Frangi/Sato)の上限(``MAX_EIGEN_VOXELS`` ≒ 256^3)を超える。
``volops.volume_downsample`` はブロックプーリングで整数倍に間引く。**mode の選択が肝**:

  * ``mean`` — 平均プール。滑らかな濃淡には正しい(サブサンプル前の帯域制限)。
  * ``max``  — 最大プール。**微小で明るい構造(欠陥ボクセル・骨・血管)を残す**。
               平均だと周囲に薄まって閾値以下に沈む。

検証(GT): 既知個数 K=8 の明るい微小欠陥を埋めたボリュームで、(1) フル解像度は
Frangi の上限を超えて弾かれる (2) 4倍間引きで上限内に収まり Frangi が回る
(3) **max プールは 8 欠陥を全て残すが mean プールは薄めて消す**(閾値+ラベリングで
計数)。max と mean の差で「なぜ欠陥検出には max か」を判別的に示す(beat-the-null)。
"""
import numpy as np
from scipy import ndimage
import volops

K = 8            # 埋め込む欠陥の既知個数(=ground truth)
R = 2.0          # 欠陥半径(ボクセル)= 微小
SHAPE = (260, 260, 260)


def synthetic_ct(shape=SHAPE, k=K, r=R):
    """暗い母材(0.1)に、明るい微小球(1.0)を k 個、既知位置に埋めた CT を作る。"""
    vol = np.full(shape, 0.10)
    zz, yy, xx = np.mgrid[0:shape[0], 0:shape[1], 0:shape[2]]
    grid = np.linspace(0.2, 0.8, 4)
    centers = [(int(a * shape[0]), int(b * shape[1]), int(0.5 * shape[2]))
               for a in (0.25, 0.75) for b in grid][:k]
    for cz, cy, cx in centers:
        vol[(zz - cz) ** 2 + (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r] = 1.0
    return vol


def count_defects(v, thr=0.5):
    """閾値 thr 以上の連結成分数(=検出された欠陥の個数)。"""
    _, n = ndimage.label(v > thr)
    return n


# --- 1) フル解像度 CT --------------------------------------------------------
vol = synthetic_ct()
print(f"フル解像度            : {vol.shape} = {vol.size} ボクセル")
print(f"Frangi 上限           : {volops.MAX_EIGEN_VOXELS} ボクセル")

# --- 2) フル解像度は重い op の上限を超えて弾かれる(=間引きが必要な理由)-----
assert vol.size > volops.MAX_EIGEN_VOXELS, "この例はフルが上限超過である前提"
try:
    volops.vol_frangi(vol, scales=(1,))
    raise AssertionError("フル解像度で Frangi が通ってしまった(上限が効いていない)")
except ValueError as e:
    assert "exceeds" in str(e) or "cap" in str(e).lower(), f"想定外のエラー: {e}"
    print(f"フルで Frangi        : 上限超過で正しく拒否 ({str(e)[:48]}...)")

# --- 3) 4倍間引き(max)で上限内へ → 重い op が回る -------------------------
ds_max = volops.volume_downsample(vol, 4, mode="max")
ds_mean = volops.volume_downsample(vol, 4, mode="mean")
print(f"4倍間引き後          : {ds_max.shape} = {ds_max.size} ボクセル")
assert ds_max.shape == (65, 65, 65), f"間引き後 shape が想定外: {ds_max.shape}"
assert ds_max.size < volops.MAX_EIGEN_VOXELS, "間引いても上限内に入っていない"
_ = volops.vol_frangi(ds_max, scales=(1,))          # もう弾かれない(例外が出なければ成功)

# --- 4) GT: max は 8 欠陥を全て残す / mean は薄めて消す ---------------------
n_max = count_defects(ds_max)
n_mean = count_defects(ds_mean)
print(f"max プール 後 欠陥数 : {n_max}   (真値 {K})")
print(f"mean プール後 欠陥数 : {n_mean}   (平均で薄まり最大値 {ds_mean.max():.2f} < 0.5)")

assert n_max == K, f"max プールが欠陥を保存できていない: {n_max} != {K}"
assert n_mean < K, f"mean プールが欠陥を washout していない(この例の主張が崩れる): {n_mean}"
print(f"PASS: フル {vol.size} → 4倍間引き {ds_max.size}(上限内)。"
      f"max は欠陥 {n_max}/{K} を保持・mean は {n_mean}/{K} に washout "
      f"= 微小欠陥検出には max プールが正しい")
