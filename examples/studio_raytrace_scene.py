# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 光線そのものを追いかけて、影・反射・欠陥の見え方を「式で」確かめる。

やりたいこと: 検査画像を作る前に、レンダラを**信用してよいか**を確かめる。
そのために、絵ではなく光線の量で答え合わせをする —— 交点はどこか、法線はどちらを
向くか、反射は反射の法則を満たすか、遮蔽があると可視率はどう落ちるか。
そのうえで、同じ形状を製品写真向けの環境光で描く。

使う op(optscene): scene_box / scene_difference / surface_defect /
camera_rays / trace_rays / reflect_rays / illumination_visibility /
env_studio / env_lightbox / render_studio。

検証(GT): 閉じた式か、幾何から一意に決まる値とだけ突き合わせる。
  * カメラ光線の方向は**単位ベクトル**(1 に厳密)。
  * 作動距離 200 mm から高さ 3 mm の天面を見ると交点は z = 3、距離 t = 197(厳密)。
  * 反射の法則: 入射 d と反射 r の法線成分は符号が反転する。|d·n + r·n| は
    機械精度(1e-15 未満)。反射は**長さを変えない**。
  * くり抜き(scene_difference)は空洞の中だけ当たり判定が消える —— 穴の底は
    元の天面より深い位置で当たる。
  * 遮蔽物を置くと可視率が 1 から下がる。遮蔽が無ければ 1(厳密)。
  * 環境光を替えると明るさが変わる。lightbox(base 0.45)は studio(sky 0.14)より明るい。
  * 凹凸だけの欠陥(色は変えない)は、真値マスクに必ず出る —— 見えるかどうかとは別。

beat-the-null: 「レンダリング結果を目で見て、それらしいので良しとする」零点との
対比 —— それでは法線が裏返っていても、遮蔽が効いていなくても気づけない
(どちらも「それらしい絵」になる)。ここでは絵を見ずに、光線の量が式と一致するか
だけを見ている。合わなければ絵が綺麗でも不合格。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import optscene as OS


def main() -> None:
    print("=" * 78)
    print("光線で答え合わせをする: 交点・法線・反射・遮蔽、それから環境光で描く")
    print("=" * 78)

    cam = OS.optical_camera(focal_mm=8.0, pixel_um=3.45, resolution=(32, 24),
                            working_distance_mm=200.0)
    metal = OS.scene_material("conductor", metal="al", roughness_um=0.03)
    block = OS.scene_box((0.0, 0.0, 0.0), (6.0, 6.0, 3.0), metal)

    # --- 1) カメラ光線 ---------------------------------------------------------
    origins, directions = OS.camera_rays(cam)
    origins = np.asarray(origins, dtype=float)
    directions = np.asarray(directions, dtype=float)
    norms = np.linalg.norm(directions, axis=-1)
    print(f"\n[1] カメラ光線 {origins.shape[0]} 本  方向の長さ "
          f"[{norms.min():.15f}, {norms.max():.15f}]")
    assert origins.shape == directions.shape == (32 * 24, 3)
    assert np.allclose(norms, 1.0, atol=1e-12)          # 方向は単位ベクトル

    # --- 2) 交点と法線(幾何から一意に決まる)-----------------------------------
    hit = OS.trace_rays([block], origins, directions)
    seen = np.isfinite(hit["t"])
    top_z = hit["point"][seen][:, 2]
    print(f"\n[2] 交点 {int(seen.sum())}/{seen.size} 本  z = "
          f"[{top_z.min():.9f}, {top_z.max():.9f}]  (天面は z = 3)")
    assert bool(seen.all())                             # 視野が箱に収まっている
    assert np.allclose(top_z, 3.0, atol=1e-9)
    # 距離は作動距離 − 天面高さ。カメラは z = WD にある
    assert np.allclose(hit["t"][seen], 200.0 - 3.0, atol=2e-2)
    normals = hit["normal"][seen]
    print(f"    法線の平均 {np.round(normals.mean(axis=0), 12)}  "
          f"(天面なので +z を向くのが正)")
    assert np.allclose(normals, np.array([0.0, 0.0, 1.0]), atol=1e-12)
    assert np.allclose(np.linalg.norm(normals, axis=-1), 1.0, atol=1e-12)

    # --- 3) 反射の法則 ---------------------------------------------------------
    incident = directions[seen]
    reflected = np.asarray(OS.reflect_rays(incident, normals), dtype=float)
    dot_in = (incident * normals).sum(-1)
    dot_out = (reflected * normals).sum(-1)
    resid = float(np.abs(dot_in + dot_out).max())
    print(f"\n[3] 反射  max |d·n + r·n| = {resid:.3e}  "
          f"(法線成分だけが符号反転すれば 0)")
    assert resid < 1e-14
    # 反射は向きを変えるだけで長さを変えない
    assert np.allclose(np.linalg.norm(reflected, axis=-1), 1.0, atol=1e-12)
    # 接線成分は不変(法線成分を抜いた残りが一致する)
    tan_in = incident - dot_in[:, None] * normals
    tan_out = reflected - dot_out[:, None] * normals
    assert np.allclose(tan_in, tan_out, atol=1e-12)

    # --- 4) くり抜き(穴の底は天面より深い)-------------------------------------
    # 視野は 2.76 x 2.07 mm。穴はその内側に収まる大きさにする —— 穴が視野より
    # 大きいと全画素が穴の底に当たり、「天面が残ること」を確かめられない
    cavity = OS.scene_box((0.0, 0.0, 2.0), (0.5, 0.5, 2.0), metal)
    drilled = OS.scene_difference(block, cavity)
    hit2 = OS.trace_rays([drilled], origins, directions)
    z2 = hit2["point"][np.isfinite(hit2["t"])][:, 2]
    deep = float(z2.min()) + 0.0          # -0.0 を 0.0 にして表示を揃える
    print(f"\n[4] くり抜き  最も深い交点 z = {deep:.6f}  (元の天面 3.0 より下)")
    assert deep < 3.0 - 1e-6
    # 空洞の外側は変わらない —— 穴を開けても天面は天面のまま
    assert abs(float(z2.max()) - 3.0) < 1e-9

    # --- 5) 遮蔽 —— 影は「置いたら暗くなる」で確かめる -------------------------
    ring = OS.light_spec(kind="ring", radius_mm=50.0, height_mm=70.0, n=24)
    probes = hit["point"][seen][:64]
    open_vis = np.asarray(OS.illumination_visibility([block], probes, ring), dtype=float)
    # 一部だけ塞ぐ帯 —— 全部塞ぐと 0 になるだけで「部分的に暗くなる」が見えない
    blocker = OS.scene_box((0.0, 22.0, 30.0), (40.0, 12.0, 0.5), metal)
    shaded = np.asarray(OS.illumination_visibility([block, blocker], probes, ring),
                        dtype=float)
    print(f"\n[5] 可視率  遮蔽なし {open_vis.mean():.6f}  →  "
          f"リングの片側を帯で塞ぐと {shaded.mean():.6f}")
    assert np.allclose(open_vis, 1.0, atol=1e-12)        # 遮るものが無ければ 1
    assert shaded.max() < open_vis.min()                 # 全点が暗くなる
    assert float(shaded.min()) >= 0.0

    # --- 6) 凹凸だけの欠陥は「見える」とは別に真値がある -----------------------
    yy, xx = np.mgrid[0:64, 0:64]
    bump = np.exp(-(((xx - 32) / 6.0) ** 2 + ((yy - 32) / 6.0) ** 2))
    flawed = OS.surface_defect(block, bump, mask=bump > 0.3, uv_size_mm=(4.0, 4.0),
                               height_um=2.0, roughness_um=0.6)
    mask = np.asarray(OS.optscene_defect_mask([flawed], cam))
    print(f"\n[6] 欠陥マスク {int(np.count_nonzero(mask))} px / {mask.size} px "
          f"(色を変えない凹凸でも真値は出る)")
    assert 0 < int(np.count_nonzero(mask)) < mask.size
    # 欠陥を入れても土台の形は変わらない(天面はそのまま)
    hit3 = OS.trace_rays([flawed], origins, directions)
    assert abs(float(hit3["point"][np.isfinite(hit3["t"])][:, 2].max()) - 3.0) < 1e-2

    # --- 7) 環境光で描く -------------------------------------------------------
    up = np.array([[0.0, 0.0, 1.0], [0.0, 0.0, -1.0], [1.0, 0.0, 0.0]])
    print("\n[7] 環境光")
    print(f"    env_studio  (上/下/横) = {np.round(np.asarray(OS.env_studio(up)), 4)}")
    print(f"    env_lightbox(上/下/横) = {np.round(np.asarray(OS.env_lightbox(up)), 4)}")

    wide = OS.optical_camera(focal_mm=8.0, pixel_um=3.45, resolution=(48, 36),
                             working_distance_mm=150.0)
    studio = np.asarray(OS.render_studio([block], wide, depth=2, samples=8,
                                         supersample=1))
    lightbox = np.asarray(OS.render_studio([block], wide, depth=2, samples=8,
                                           supersample=1, environment=OS.env_lightbox))
    print(f"    render_studio   平均 {studio.mean():.4f}   (既定の環境)")
    print(f"    render_studio   平均 {lightbox.mean():.4f}   (env_lightbox)")
    assert studio.shape == lightbox.shape == (36, 48, 3)
    assert np.isfinite(studio).all() and np.isfinite(lightbox).all()
    assert float(studio.min()) >= 0.0 and float(lightbox.min()) >= 0.0
    # 撮影ボックスは一様に明るい環境なので、既定のスタジオ照明より明るく写る
    assert lightbox.mean() > studio.mean()
    # 同じ環境・同じ種で描けば決定的(乱数が漏れていない)
    again = np.asarray(OS.render_studio([block], wide, depth=2, samples=8,
                                        supersample=1, environment=OS.env_lightbox))
    assert np.array_equal(lightbox, again)

    print("\n" + "=" * 78)
    print("PASS: 交点・法線・反射・遮蔽が式と一致した。絵の綺麗さでは判定していない")
    print("=" * 78)


if __name__ == "__main__":
    main()
