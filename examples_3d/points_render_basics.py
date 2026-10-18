"""事例: 点群をそのまま色の絵にする —— points_render の足跡・重ね方・カメラを、閉じた式で確かめる.

現実の問題(平たく):
    LiDAR・SfM・顕微鏡の細胞の位置など、面を張れない点群は多い。点を 1 画素ずつ置くと穴だらけで
    奥と手前の区別も付かず、円を「入力の順に」塗ると、後から来た奥の点が手前を隠す。
    点群を絵にするには、小数画素の位置・足跡・深さの順序を正しく扱う描画が要る。

方法(render3d.points_render、ops3d の render):
    P_cam = R P + t、正射影 u = fx X + cx(または透視 u = fx X / Z + cx)、画素 (r, c) の中心 = (u, v) = (c, r)。
    足跡 gaussian / disc / point、重ね方 over(深さの順のアルファ合成)/ add(光の総量を保つ加算)。

Ground truth(検証):
    - 小数画素に置いた点の像の重心が、閉じた式の射影位置に 1e-3 画素以内で乗る。
    - 2 点を同じ画素に重ねると、入力の順に依らず手前の色が勝つ(opacity 1)。
    - add の像の総和 = 点の色の総和(光の保存)。
    - 光軸まわりに 90 度回したカメラの像 = 元の像の numpy.rot90(描画器が知らない画素の並べ替え)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

import render3d  # noqa: E402


def main() -> int:
    K = np.array([[20.0, 0.0, 31.5], [0.0, 20.0, 31.5], [0.0, 0.0, 1.0]])

    # 1. 小数画素の位置 → 像の重心 ---------------------------------------------------
    P = np.array([[0.513, -0.231, 3.0]])                 # u = 20*0.513 + 31.5 = 41.76, v = 26.88
    img = render3d.points_render(P, size=64, K=K, composite="add", radius_px=1.5)[:, :, 0]
    rr, cc = np.mgrid[0:64, 0:64]
    cu, cv = (img * cc).sum() / img.sum(), (img * rr).sum() / img.sum()
    print("centroid (%.4f, %.4f) vs closed form (%.4f, %.4f)" % (cu, cv, 20 * 0.513 + 31.5, 20 * -0.231 + 31.5))
    assert abs(cu - (20 * 0.513 + 31.5)) < 1e-3 and abs(cv - (20 * -0.231 + 31.5)) < 1e-3

    # 2. 手前が勝つ(入力の順に依らない) ----------------------------------------------
    two = np.array([[0.0, 0.0, 5.0], [0.0, 0.0, 3.0]])   # 2 点目が手前
    col = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    for o in ([0, 1], [1, 0]):
        im = render3d.points_render(two[o], colors=col[o], size=64, K=K, footprint="disc", radius_px=2.0)
        assert np.array_equal(im[32, 32], [0.0, 1.0, 0.0])
    print("nearer point wins in both input orders: centre pixel = green")

    # 3. 光の保存 --------------------------------------------------------------------
    rng = np.random.default_rng(0)
    cloud = rng.normal(size=(5000, 3))
    c = rng.uniform(0, 1, (5000, 3))
    add = render3d.points_render(cloud, colors=c, size=96, composite="add", opacity=0.5)
    print("energy: image %.9f vs points %.9f" % (add.sum(), 0.5 * c.sum()))
    assert abs(add.sum() - 0.5 * c.sum()) < 1e-8

    # 4. 光軸まわりの 90 度 = rot90 ----------------------------------------------------
    Rz = np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    pts = np.column_stack([rng.normal(0, 0.5, 3000), rng.normal(0, 0.3, 3000), rng.uniform(3, 5, 3000)])
    kw = dict(colors=rng.uniform(0, 1, (3000, 3)), size=64, K=K, opacity=0.6, depth_cue=0.5)
    a = render3d.points_render(pts, **kw)
    b = render3d.points_render(pts, R=Rz, **kw)
    print("quarter turn vs rot90: max diff %.1e" % np.abs(b - np.rot90(a, k=-1)).max())
    assert np.abs(b - np.rot90(a, k=-1)).max() < 1e-9

    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
