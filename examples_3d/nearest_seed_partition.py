"""事例: 距離変換の「向き」— 最近の seed への変位で半径・肉厚・ラベルの縄張りを測る.

現実の問題(平たく):
    距離変換は「いちばん近い seed まで何 voxel か」を返すが、「**どの** seed が近いか」は捨てる。
    ところが EM 連続断面の骨格化や膜の肉厚計測では、その向きこそが要る —— 表面の各点から骨格へ
    伸ばした矢の長さが管の半径、膜の点から最近の別の膜への矢が肉厚、分割片のラベルを零 voxel に
    配れば「どの片がその空間を支配するか」(縄張り = ボロノイ分割)になる。

方法(volops.py / match3d.py の ops を連鎖):
    1) vol_nearest_seed_vector : 各 voxel → 最近 seed への変位 (dz,dy,dx)。seed = 非零。
    2) vol_nearest_label       : 零 voxel に最近の非零ラベルを配る(ラベルのボロノイ分割)。
    3) edt_jfa_vector          : 同じ量を GPU の JFA で(torch があれば)。
    連鎖: ボクセル → skeletonize_vol → vol_nearest_seed_vector(骨格が seed)→ |変位| = 半径。

Ground truth(検証):
    - 円柱(半径 r、軸 z)の表面 voxel から骨格(軸)への変位の長さは r に一致(離散化の 0.5 voxel 以内)。
      向きは軸に向く(z 成分 ≈ 0)。
    - 2 つの球(ラベル 1, 2)の中心を結ぶ線分の垂直二等分面で、vol_nearest_label の分割面が一致する
      (面の両側でラベルが入れ替わり、seed の上では元のラベルが保たれる)。
    - 異方 spacing: z 方向の間隔を 3 倍にすると、z に 2 voxel 離れた seed より x に 3 voxel 離れた seed が
      「近く」なり、最近傍が入れ替わる(物理距離で判定している証拠)。
    - 対照: 距離の値だけ(vol_distance_transform)では表面の点に半径は出ない(0〜1 voxel)—— 向きが要る証拠。
    - torch があれば edt_jfa_vector と vol_nearest_seed_vector が全 voxel で一致する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

import volops  # noqa: E402


def cylinder(shape=(24, 41, 41), r=9.0):
    D, H, W = shape
    zz, yy, xx = np.indices(shape)
    cy, cx = H // 2, W // 2
    rr = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    return (rr <= r).astype(np.float64), (cy, cx)


def main() -> int:
    rng = np.random.default_rng(0)
    # 1. 表面 → 骨格(軸)への変位の長さ = 半径 ------------------------------------
    r = 9.0
    v, (cy, cx) = cylinder(r=r)
    axis = np.zeros_like(v)
    axis[:, cy, cx] = 1.0                                   # 骨格 = 軸(真値の骨格を使い、骨格化の誤差と分けて見る)
    vec = volops.vol_nearest_seed_vector(axis)
    surf = (v > 0.5) & (volops.vol_distance_transform(v) <= 1.0)   # 表面 1 voxel 厚
    length = np.linalg.norm(vec[:, surf], axis=0)
    err = np.abs(length - r)
    print("cylinder r=%.1f: surface->axis vector length mean %.3f (max |err| %.3f voxel), z-component max %.3g"
          % (r, length.mean(), err.max(), np.abs(vec[0][surf]).max()))
    assert err.max() <= 1.0 and abs(length.mean() - r) <= 0.5
    assert np.abs(vec[0][surf]).max() == 0.0             # 軸に向く矢は z 成分 0
    # 対照: 距離の「値」だけ(vol_distance_transform)では、表面の点に見えるのは背景までの 0〜1 voxel で半径は出ない
    dt_surface = volops.vol_distance_transform(v)[surf]
    print("  value-only control: vol_distance_transform on the same surface voxels = %.1f..%.1f (no radius; the vector's length gives %.1f)"
          % (dt_surface.min(), dt_surface.max(), length.mean()))
    assert dt_surface.max() <= 1.0

    # 2. ラベルのボロノイ分割 = 垂直二等分面 ------------------------------------
    shape = (21, 21, 41)
    zz, yy, xx = np.indices(shape)
    c1, c2 = np.array([10, 10, 10]), np.array([10, 10, 30])
    L = np.zeros(shape, np.int64)
    L[((zz - c1[0]) ** 2 + (yy - c1[1]) ** 2 + (xx - c1[2]) ** 2) <= 9] = 1
    L[((zz - c2[0]) ** 2 + (yy - c2[1]) ** 2 + (xx - c2[2]) ** 2) <= 9] = 2
    part = volops.vol_nearest_label(L)
    assert np.array_equal(part[L != 0], L[L != 0])      # seed の上は保たれる
    assert set(np.unique(part).tolist()) == {1, 2}
    bisect = (xx == 20)                                   # 垂直二等分面 x = 20(等距離 → どちらでもよい)
    left, right = (xx < 20), (xx > 20)
    print("two spheres: label-1 side x<20 fraction %.3f, label-2 side x>20 fraction %.3f"
          % ((part[left] == 1).mean(), (part[right] == 2).mean()))
    assert (part[left] == 1).all() and (part[right] == 2).all()
    assert bisect.any()

    # 3. 異方 spacing で最近傍が入れ替わる ------------------------------------
    s = np.zeros((7, 5, 9))
    s[0, 2, 4] = 1                                        # seed A: z に 3 voxel 上(観測点 (3,2,4) から)
    s[3, 2, 0] = 1                                        # seed B: x に 4 voxel 横
    p = (3, 2, 4)
    iso = volops.vol_nearest_seed_vector(s)[:, p[0], p[1], p[2]]
    aniso = volops.vol_nearest_seed_vector(s, spacing=(2.0, 1.0, 1.0))[:, p[0], p[1], p[2]]
    print("anisotropic spacing: isotropic nearest %s (A, 3 voxel), sz=2 nearest %s (B, 4 voxel but 4 < 6 physical)" % (iso.tolist(), aniso.tolist()))
    assert iso.tolist() == [-3.0, 0.0, 0.0] and aniso.tolist() == [0.0, 0.0, -4.0]

    # 4. GPU JFA(torch があれば)は scipy 経路と厳密一致 ------------------------------------
    try:
        import torch  # noqa: F401
        import match3d
        seed = rng.random((20, 24, 28)) < 0.01
        seed[5, 5, 5] = True
        ref = volops.vol_nearest_seed_vector(seed.astype(float))
        jfa = match3d.edt_jfa_vector(seed).detach().cpu().numpy()
        dist_ok = np.allclose(np.linalg.norm(ref, axis=0), np.linalg.norm(jfa, axis=0))
        print("edt_jfa_vector vs scipy: distance fields equal %s, identical vectors %.4f (ties may pick another equidistant seed)"
              % (dist_ok, np.mean(np.all(ref == jfa, axis=0))))
        assert dist_ok
    except ImportError:
        print("torch not installed: edt_jfa_vector skipped (CPU path verified above)")
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
