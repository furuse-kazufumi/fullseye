# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 検査セルを光学デジタルツインにして、学習画像を真値つきで生成する。

やりたいこと: 実機を作る前に「その光学構成で欠陥が写るか」を数字で確かめ、そのまま
外観検査 AI の学習データを作る。中心は AI ではなく、カメラ・レンズ・照明・ワーク・
欠陥・材質の光学挙動を結ぶシミュレーション。

使う op(optscene): scene_cylinder / scene_material / surface_finish / random_defects /
optical_camera / render_optscene / optscene_depth / optscene_mask /
optscene_defect_mask / optscene_instances / defocus_blur / sensor_capture /
inspection_dataset / dataset_throughput。照明は illumdesign.light_source。

検証(GT): 閉じた式か、同じ量を別経路で出した値とだけ突き合わせる。
  * 視野 = 画素数 × 画素ピッチ × 作動距離 / 焦点距離(厳密一致)。
  * 深度の真値は**光軸方向の z**。円盤の上面は WD − 高さに厳密一致。
  * 透過照明のシルエット面積 = πr² / 画素実寸²(1% 以内)。部品はちょうど 0。
  * 色を変えない凹凸だけの欠陥は、拡散照明では出ず低角照明で出る(桁で違う)。
  * 欠陥ラベルは照明によらず同じ画素数(見えなくても真値はある)。
  * 個体別 bbox の合計面積 = 合成マスクの画素数(取りこぼしゼロ)。
  * 絞りを開けるほど高周波が落ちる(被写界深度)。

beat-the-null: 「良品画像に 2-D の傷を描き足す」零点との対比 —— そのやり方では
照明を変えても見え方が変わらない。ここでは同じ欠陥・同じ部品で照明だけ替えると
コントラストが桁で動く。実機では照明を選ぶのが仕事なので、そこが動かない
生成器で学習させたモデルは現場の照明変更で壊れる。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import illumdesign
import optscene as OS


def main() -> None:
    print("=" * 78)
    print("検査セルの光学デジタルツイン: 撮って、真値を出して、学習データにする")
    print("=" * 78)

    # --- 1) デジタルツイン(部品・加工目・カメラ・照明)------------------------
    part = OS.surface_finish(
        OS.scene_cylinder((0.0, 0.0, 3.0), 10.0, 3.0,
                          OS.scene_material("conductor", metal="al", finish="circular")),
        kind="turned", pitch_um=320.0, depth_um=1.8, uv_size_mm=(19.0, 19.0), seed=1)
    cam = OS.optical_camera(focal_mm=8.0, pixel_um=3.45, resolution=(200, 200),
                            working_distance_mm=300.0)
    want = 200 * 3.45e-3 * 300.0 / 8.0
    print(f"視野                      : {cam['fov_mm'][0]:.3f} mm  "
          f"(閉じた式 N·p·WD/f = {want:.3f})")
    assert abs(cam["fov_mm"][0] - want) < 1e-12

    depth = OS.optscene_depth([part], cam)
    print(f"深度の真値(円盤の上面)    : {np.nanmin(depth):.3f} mm  (WD − 高さ = 294.000)")
    assert abs(float(np.nanmin(depth)) - 294.0) < 1e-9

    # --- 2) 透過照明のシルエット(閉じた式)----------------------------------
    back = illumdesign.light_source(kind="backlight", radius_mm=40.0, height_mm=60.0, n=40)
    img = OS.render_optscene([part], cam, [back]).mean(-1)
    mask = OS.optscene_mask([part], cam, 0)
    mm_px = cam["pixel_mm"] * 294.0 / cam["focal_mm"]
    area = np.pi * 10.0 ** 2 / mm_px ** 2
    print(f"シルエット面積            : {int(mask.sum())} 画素  (πr²/画素実寸² = {area:.0f})")
    print(f"部品の明るさ              : {img[mask].max():.1e}  (上から光が当たらない = 厳密に 0)")
    assert abs(int(mask.sum()) - area) < 0.01 * area and float(img[mask].max()) == 0.0

    # --- 3) 同じ欠陥、照明だけ替える ----------------------------------------
    made = OS.random_defects(part, count=2, kinds=("scratch", "pits"), seed=101,
                             uv_size_mm=(19.0, 19.0), height_um=(20.0, 45.0),
                             albedo_defects=False)          # 色は変えない = 凹凸だけ
    scene = [made["part"]] + made["objects"]
    label = OS.optscene_defect_mask(scene, cam)
    good = OS.optscene_mask(scene, cam, 0) & ~label
    got = {}
    for name, kw in (("拡散(ドーム)", dict(kind="dome", radius_mm=85.0, height_mm=70.0, n=96)),
                     ("低角(暗視野)", dict(kind="ring", radius_mm=95.0, height_mm=7.0, n=64))):
        light = illumdesign.light_source(**kw)
        v = OS.render_optscene(scene, cam, [light]).mean(-1)
        got[name] = abs(float(v[label].mean() - v[good].mean())) / max(float(v[good].mean()), 1e-30)
        print(f"欠陥コントラスト {name} : {got[name] * 100:+7.2f} %")
    ratio = got["低角(暗視野)"] / max(got["拡散(ドーム)"], 1e-12)
    print(f"照明を替えただけの倍率    : {ratio:.0f} 倍  (色は 1 画素も変えていない)")
    assert ratio > 20.0

    # ラベルは見え方によらない
    other = OS.optscene_defect_mask(scene, cam)
    print(f"欠陥ラベル                : {int(label.sum())} 画素(照明によらず同じ)")
    assert int(label.sum()) == int(other.sum()) > 0

    # --- 4) 個体別のアノテーション(取りこぼしゼロ)---------------------------
    inst = OS.optscene_instances(scene, cam, min_area_px=1)
    total = sum(i["area_px"] for i in inst)
    print(f"個体別アノテーション      : {len(inst)} 個体 / 合計 {total} 画素 "
          f"(合成マスク {int(label.sum())} と一致)")
    assert total == int(label.sum())
    for i in inst[:1]:
        x0, y0, x1, y1 = i["bbox"]
        assert i["mask"][y0:y1 + 1, x0:x1 + 1].sum() == i["area_px"]   # bbox が個体を包む

    # --- 5) 被写界深度(実機で合焦するか)------------------------------------
    tilted = OS.optical_camera(focal_mm=25.0, pixel_um=3.45, resolution=(120, 120),
                               working_distance_mm=200.0, tilt_deg=40.0)
    dome = illumdesign.light_source(kind="dome", radius_mm=80.0, height_mm=70.0, n=48)
    sc3 = [OS.scene_plane(0.0, OS.scene_material("lambert", 0.3)),
           OS.scene_sphere((0.0, 0.0, 6.0), 6.0, OS.scene_material("lambert", 0.7))]
    base = OS.render_optscene(sc3, tilted, [dome])
    zmap = OS.optscene_depth(sc3, tilted)
    sharp = []
    for fnum in (16.0, 5.6, 2.0):
        blur = OS.defocus_blur(base, zmap, tilted, f_number=fnum)
        sharp.append(float(np.abs(np.diff(blur.mean(-1), axis=0)).mean()))
        print(f"F{fnum:<5.1f} の高周波エネルギー : {sharp[-1]:.4e}")
    assert sharp[0] > sharp[1] > sharp[2]                    # 絞るほど深い = くっきり

    # --- 6) 大量生成のスループット(通常運用)--------------------------------
    lights = [illumdesign.light_source(kind=k, radius_mm=90.0, height_mm=h, n=48)
              for k, h in (("dome", 70.0), ("ring", 7.0))]
    small = OS.optical_camera(focal_mm=8.0, pixel_um=3.45, resolution=(128, 128),
                              working_distance_mm=300.0)
    ds = OS.inspection_dataset([part], small, lights, n=6, seed=3, jitter_mm=1.0,
                               intensity_jitter=0.2,
                               defects=dict(count=2, uv_size_mm=(19.0, 19.0),
                                            kinds=("scratch", "pits", "blob",
                                                   "stain", "foreign")))
    tp = OS.dataset_throughput(ds)
    print(f"生成スループット 128x128  : {tp['seconds_per_image']:.3f} 秒/枚 = "
          f"{tp['images_per_hour']:,.0f} 枚/時(レンダ {tp['render_fraction'] * 100:.0f}%)")
    assert tp["images"] == 6 and tp["seconds_per_image"] > 0.0
    assert all(set(d) == {"image", "defect_mask", "part_mask", "depth_mm", "meta"} for d in ds)
    assert {d["meta"]["light"] for d in ds} == {"dome", "ring"}

    print(f"PASS: 視野と深度が閉じた式に厳密一致・シルエット面積 πr² と 1% 以内・"
          f"色を変えない欠陥が照明だけで {ratio:.0f} 倍・ラベルは照明によらず一定・"
          f"個体別 bbox の合計が合成マスクと一致・絞るほど高周波が残る・"
          f"{tp['images_per_hour']:,.0f} 枚/時")


if __name__ == "__main__":
    main()
