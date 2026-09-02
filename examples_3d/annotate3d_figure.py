# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: レンダリングの上に 3-D アンカーの矢印・引き出し線・スケールバー・座標軸・箱・距離を射影して描く.

    py -3.11 examples_3d/annotate3d_figure.py
    py -3.11 examples_3d/annotate3d_figure.py --save out/annotate3d_figure.png

実世界の問題:
    メッシュや点群の結果を論文図にするとき、「この頂点が欠陥」「この 2 点の距離が 12 mm」
    「このバーが 10 mm」を、描いた絵の上に矢印や線で示したい。3-D 座標を持っている側が
    画素座標を手で計算すると、軸の向き・主点・-Z 慣習で必ずどこかがずれる。
    ``annotate3d`` 族は render3d と同じ射影を 1 か所に閉じ込め、2-D の描画は
    annotate に任せる。depth を渡せば裏側のアンカーは破線で描かれる。

原理:
    - annotate3d_project : X_c = R X + t、z = -X_c[2]、u = fx X_c[0]/z + cx、v = cy - fy X_c[1]/z
    - annotate3d_scale_bar: 3-D の線分を射影 → 像面平行なら画素長 = f L / z(短縮を正直に)
    - 遮蔽: render_mesh の depth(前方距離)と z を比べ、d < z(1-tol) なら hidden

検証(GT):
    - 既知カメラ(look_at)と既知点の画素が閉形式と 1e-9 で一致。
    - 像面平行のスケールバーの画素長が f L / z と 1e-9 で一致。
    - 球の裏側(カメラから見て奥)の頂点は depth で hidden、手前の頂点は visible。
    - 距離の値は 3-D 距離そのもの(射影で短縮しても数字は変わらない)。

beat-the-null:
    - null =「2-D の画素座標を目分量で置く」。射影を持たない null は、カメラを動かした
      瞬間にアンカーが対象から外れる。ここでは 2 つの姿勢で同じ 3-D アンカーが
      それぞれ正しい画素(閉形式)に落ちることを示す。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

import annotate3d as T   # noqa: E402
import render3d          # noqa: E402
import sdf_ops           # noqa: E402

W, H = 320, 240


def _scene():
    """球(半径 1、中心 (0,0,1))+ 床(z=0 の板)のメッシュ。"""
    n = 40
    g = np.stack(np.meshgrid(np.linspace(-2, 2, n), np.linspace(-2, 2, n),
                             np.linspace(-0.2, 2.2, n), indexing="ij"), axis=-1)
    sph = sdf_ops.sphere_sdf(g, (0.0, 0.0, 1.0), 1.0)
    verts, faces = render3d.marching_cubes(sph, 0.0)[:2]
    # marching_cubes は格子 index 座標で返すので world へ写す
    step = np.array([4.0 / (n - 1), 4.0 / (n - 1), 2.4 / (n - 1)])
    verts = verts * step + np.array([-2.0, -2.0, -0.2])
    # 床(2 三角形)
    fv = np.array([[-2, -2, 0], [2, -2, 0], [2, 2, 0], [-2, 2, 0]], float)
    ff = np.array([[0, 1, 2], [0, 2, 3]]) + len(verts)
    return np.vstack([verts, fv]), np.vstack([faces, ff])


def run():
    V, F = _scene()
    K = render3d.intrinsics_from_fov(40.0, W, H)
    pose = render3d.look_at((4.0, -5.0, 3.5), (0.0, 0.0, 0.8), up=(0.0, 0.0, 1.0))
    r = render3d.render_mesh(V, F, pose, K, width=W, height=H)
    depth = r["depth"]
    shade = np.where(np.isfinite(depth), 0.25 + 0.6 * np.clip(r["normals"][..., 2], 0, 1), 0.92)
    img = np.stack([shade] * 3, axis=-1)

    top = (0.0, 0.0, 2.0)                    # 球の天頂(見える)
    back = (0.0, 1.0, 1.0)                   # カメラから見て裏側の赤道点
    front = (0.0, -1.0, 1.0)                 # 手前の赤道点
    out = T.annotate3d_axes(img, pose, K, origin=(-1.6, -1.6, 0.0), length=0.8)
    out = T.annotate3d_bbox(out, ((-1, -1, 0), (1, 1, 2)), pose, K, depth=depth, color="neutral")
    out = T.annotate3d_label(out, "apex", top, pose, K, depth=depth, offset=(30, -26))
    out = T.annotate3d_label(out, "hidden side", back, pose, K, depth=depth, offset=(40, -10))
    out = T.annotate3d_label(out, "front", front, pose, K, depth=depth, offset=(36, 30))
    out = T.annotate3d_arrow(out, (1.6, -1.2, 0.0), (0.75, -0.65, 0.3), pose, K, color="wrong")
    out = T.annotate3d_scale_bar(out, (0.3, -1.95, 0.0), (1, 0, 0), 1.0, pose, K, unit="m")
    out = T.annotate3d_measure(out, front, top, pose, K, unit="m", color="reference")

    # ---- GT ----------------------------------------------------------------
    P = pose
    Xc = np.asarray(top) @ P[:3, :3].T + P[:3, 3]
    z = -Xc[2]
    want = (K[0, 0] * Xc[0] / z + K[0, 2], K[1, 2] - K[1, 1] * Xc[1] / z)
    tab = T.annotate3d_project([top, back, front], pose, K, depth=depth)   # 台帳名の op
    res = {
        "proj_err": float(np.max(np.abs(tab["uv"][0] - want))),
        "hidden": tab["hidden"].tolist(), "visible": tab["visible"].tolist(),
    }
    # 像面平行バー: 光軸に直交する 2 点 → f L / z
    fpose = render3d.look_at((0.0, 0.0, 10.0), (0.0, 0.0, 0.0), up=(0.0, 1.0, 0.0))
    t2 = T.project_anchors([(0.0, 0.0, 0.0), (1.5, 0.0, 0.0)], fpose, K)
    res["bar_px"] = float(np.linalg.norm(t2["uv"][1] - t2["uv"][0]))
    res["bar_want"] = float(K[0, 0] * 1.5 / 10.0)
    res["measure_value"] = float(np.linalg.norm(np.subtract(top, front)))
    # null: 別姿勢でも同じアンカーが閉形式の画素に落ちる(目分量の 2-D 座標は外れる)
    pose2 = render3d.look_at((-4.0, 4.0, 2.5), (0.4, 0.4, 0.6), up=(0.0, 0.0, 1.0))
    Xc2 = np.asarray(front) @ pose2[:3, :3].T + pose2[:3, 3]
    z2 = -Xc2[2]
    want2 = (K[0, 0] * Xc2[0] / z2 + K[0, 2], K[1, 2] - K[1, 1] * Xc2[1] / z2)
    uv2 = T.project_anchors([front], pose2, K)["uv"][0]
    res["proj_err_pose2"] = float(np.max(np.abs(uv2 - want2)))
    res["null_shift_px"] = float(np.linalg.norm(uv2 - tab["uv"][2]))
    res["image"] = out
    return res


def main(save=None):
    r = run()
    print("3-D 図注(annotate3d)を球 + 床のレンダリングに載せ、射影を閉形式で検証した:")
    print(f"- 既知カメラ・既知点の画素誤差: {r['proj_err']:.2e} px(別姿勢 {r['proj_err_pose2']:.2e} px)")
    print(f"- 像面平行のスケールバー: {r['bar_px']:.6f} px = f L / z = {r['bar_want']:.6f} px")
    print(f"- 遮蔽判定 [apex, hidden side, front]: hidden={r['hidden']} visible={r['visible']}")
    print(f"- 距離の値(3-D): {r['measure_value']:.6f} m(front→apex、射影の短縮とは無関係)")
    print(f"- null(目分量の 2-D 座標)は姿勢を変えると {r['null_shift_px']:.1f} px 外れる; 射影 op は追従する")
    assert r["proj_err"] < 1e-9 and r["proj_err_pose2"] < 1e-9
    assert abs(r["bar_px"] - r["bar_want"]) < 1e-9
    assert r["hidden"] == [False, True, False] and r["visible"] == [True, False, True]
    assert abs(r["measure_value"] - np.sqrt(2.0)) < 1e-12
    assert r["null_shift_px"] > 10.0
    print("\nPASS: 3-D アンカーは閉形式どおりの画素に落ち、裏側のアンカーは depth で隠れ判定された。")
    if save:
        from PIL import Image
        Path(save).parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(np.round(r["image"] * 255.0).astype(np.uint8)).save(save)
        print(f"saved: {save}")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", default=None)
    args = ap.parse_args()
    raise SystemExit(main(save=args.save))
