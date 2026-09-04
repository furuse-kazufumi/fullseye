# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""事例: 型番から検査セルを組み、「写るか・運べるか」を撮る前に数字で決める。

やりたいこと: カタログの型番(センサー・レンズ・照明)を並べただけの状態から、
**買う前に**次の 4 つを確かめる —— ①レンズがセンサーを覆うか ②必要な欠陥寸法を
分解できるか ③そのフレームレートを伝送路が運べるか ④実際に撮ったらどう写るか。

使う op(optscene): sensor_catalog / sensor_spec / sensor_diagonal_mm /
lens_catalog / lens_spec / covers_sensor / light_catalog / light_spec /
register_light / light_wavelengths / optical_budget / airy_radius_um /
vision_layout / layout_capture / diffraction_blur / sensor_capture /
interface_budget / linescan_capture / observe_surface。

検証(GT): 閉じた式か、同じ量を別経路で出した値とだけ突き合わせる。
  * センサー対角 = 画素ピッチ × √(w² + h²)。IMX252 は 3.45 µm × 2560 = 8.832 mm(厳密)。
  * Airy 半径 = 1.22 · λ · N。F 値に**比例**する(F/2.8 は F/5.6 のちょうど半分)。
  * 実効 F 値 = N(1 + m)、物体側 Airy = Airy / m、物体側画素 = ピッチ / m(厳密)。
  * 視野 = 画素数 × 画素ピッチ × WD / f(厳密)。
  * 伝送帯域 = 規格帯域 × リンク数 × 効率、1 フレーム = w·h·(bit/8)、
    最大 fps = 帯域 / フレーム長(いずれも厳密)。
  * 回折ボケは**光を作りも消しもしない**(総和保存)。絞るとピークだけ落ちる。
  * ライン走査の走査方向画素 = 速度 / ライン周波数、直交方向画素 = ピッチ·WD/f。
    **既定では正方形にならない**。ライン周波数を合わせるとアスペクトが厳密に 1。
  * 露光を 2 倍にすると信号は 2 倍、飽和したら**折り返さず**張り付く。

beat-the-null: 「センサーとレンズのカタログ値を表に並べて眺める」零点との対比 ——
表を見ても①〜④は出てこない。ここでは同じ型番の組から、覆えるかは余裕 mm で、
分解できるかは物体側 µm で、運べるかは fps で、写るかは画素値で出る。
どれも**買う前に**決まる。
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import optscene as OS


def main() -> None:
    print("=" * 78)
    print("型番から検査セルを組む: 覆えるか / 分解できるか / 運べるか / 写るか")
    print("=" * 78)

    # --- 1) カタログから選ぶ ---------------------------------------------------
    sensors = OS.sensor_catalog(maker="Sony")
    lenses = OS.lens_catalog(mount="C")
    lights = OS.light_catalog(kind="ring")
    print(f"\n[1] カタログ: センサー {len(sensors)} / レンズ {len(lenses)} / 照明 {len(lights)}")

    sensor = OS.sensor_spec(model="IMX252")
    diag = OS.sensor_diagonal_mm(sensor)
    want = sensor["pixel_um"] * 1e-3 * np.hypot(sensor["width"], sensor["height"])
    print(f"    IMX252  {sensor['width']}x{sensor['height']} @ {sensor['pixel_um']} um"
          f"  対角 {diag:.3f} mm  (p·√(w²+h²) = {want:.3f})")
    assert abs(diag - want) < 1e-12                      # 対角は閉じた式そのもの

    lens = OS.lens_spec(model="Fujinon HF25XA-1", working_distance_mm=250.0)
    cover = OS.covers_sensor(lens, sensor)
    print(f"    HF25XA-1 イメージサークル {cover['image_circle_mm']} mm"
          f"  → 覆える: {cover['covers']}  余裕 {cover['margin_mm']:.3f} mm")
    assert cover["covers"] is True
    assert abs(cover["margin_mm"] - (cover["image_circle_mm"] - diag)) < 1e-12

    # 覆えない組は「買ってから気づく」典型。ここで落とす
    small_lens = OS.lens_spec(focal_mm=6.0, f_number=4.0, image_circle_mm=6.0)
    assert OS.covers_sensor(small_lens, sensor)["covers"] is False

    # --- 2) 分解できるか(回折と標本化のどちらが効いているか)-------------------
    print("\n[2] 光学バジェット")
    a56, a28 = OS.airy_radius_um(5.6), OS.airy_radius_um(2.8)
    print(f"    Airy 半径  F/5.6 = {a56:.4f} um   F/2.8 = {a28:.4f} um")
    assert abs(a56 - 1.22 * 0.550 * 5.6) < 1e-12         # 1.22·λ·N そのもの
    assert abs(a56 - 2.0 * a28) < 1e-12                  # F 値に比例

    budget = OS.optical_budget(focal_mm=25.0, working_distance_mm=250.0,
                               f_number=5.6, pixel_um=3.45)
    m = budget["magnification"]
    print(f"    倍率 {m:.4f}  実効 F {budget['f_number_working']:.4f}  "
          f"物体側 Airy {budget['airy_object_um']:.2f} um  "
          f"物体側画素 {budget['pixel_object_um']:.2f} um")
    print(f"    分解限界 {budget['limit_um']:.1f} um  ← 効いているのは "
          f"**{budget['limited_by']}**")
    assert abs(budget["f_number_working"] - 5.6 * (1.0 + m)) < 1e-12
    assert abs(budget["airy_object_um"] - budget["airy_um"] / m) < 1e-9
    assert abs(budget["pixel_object_um"] - 3.45 / m) < 1e-9
    assert abs(budget["numerical_aperture"] - 1.0 / (2.0 * 5.6)) < 1e-12
    # 分解限界は「回折」と「標本化(2 画素)」の**大きい方**。ここを取り違えると、
    # 絞りを開けて直る問題と直らない問題の区別がつかなくなる
    nyquist = 2.0 * budget["pixel_object_um"]
    assert abs(budget["limit_um"] - max(budget["airy_object_um"], nyquist)) < 1e-9
    assert budget["limited_by"] == "sampling" and nyquist > budget["airy_object_um"]

    # 高倍率・絞り込みでは回折側が律速になる(同じ式で切り替わる)
    macro = OS.optical_budget(focal_mm=50.0, working_distance_mm=100.0,
                              f_number=8.0, pixel_um=3.45)
    print(f"    倍率 {macro['magnification']:.2f} / F/8 では律速が "
          f"**{macro['limited_by']}** に変わる "
          f"(Airy {macro['airy_object_um']:.2f} um > 2 画素 "
          f"{2 * macro['pixel_object_um']:.2f} um)")
    assert macro["limited_by"] == "diffraction"

    # 絞るほど被写界深度は伸びるが分解は落ちる —— この交換が光学設計の芯
    tight = OS.optical_budget(focal_mm=25.0, working_distance_mm=250.0,
                              f_number=16.0, pixel_um=3.45)
    print(f"    F/5.6 → F/16: 被写界深度 {budget['dof_um']:.0f} → {tight['dof_um']:.0f} um, "
          f"物体側 Airy {budget['airy_object_um']:.1f} → {tight['airy_object_um']:.1f} um")
    assert tight["dof_um"] > budget["dof_um"]
    assert tight["airy_object_um"] > budget["airy_object_um"]
    # 被写界深度も閉じた式(幾何 2·N_w·c + 波動 2·λ·N_w²、いずれも物体側 /m²)
    nw, lam_um = budget["f_number_working"], budget["wavelength_nm"] * 1e-3
    want_dof = (2.0 * nw * budget["coc_um"] + 2.0 * lam_um * nw * nw) / (m * m)
    assert abs(budget["dof_um"] - want_dof) < 1e-6

    # --- 3) 照明(型番・自社登録・スペクトル)-----------------------------------
    print("\n[3] 照明")
    ring = OS.light_spec(model="generic ring-70")
    lams, weights = OS.light_wavelengths(ring, samples=5)
    print(f"    generic ring-70: {ring['source']} {ring['wavelength_nm']:.0f} nm "
          f"± {ring['bandwidth_nm']:.0f} nm  → 波長 {np.round(lams, 1)}")
    assert abs(float(np.sum(weights)) - 1.0) < 1e-12     # 重みは分布なので和は 1
    assert abs(float(lams[len(lams) // 2]) - ring["wavelength_nm"]) < 1e-9

    laser = OS.light_spec(source="laser", wavelength_nm=660.0, bandwidth_nm=30.0)
    ll, lw = OS.light_wavelengths(laser, samples=5)
    print(f"    レーザーは帯域 {laser['bandwidth_nm']:.0f} nm・単一波長 {ll} (coherent="
          f"{laser['coherent']})")
    assert laser["bandwidth_nm"] == 0.0 and len(ll) == 1  # 単色として扱う(引数によらず)

    key = OS.register_light("Acme", "AR-90", kind="ring", radius_mm=45.0,
                            wavelength_nm=470.0, bandwidth_nm=20.0)
    assert key in OS.light_catalog(maker="Acme")
    print(f"    自社照明を登録: {key} → 以後 model= で引ける")

    # --- 4) レイアウトを組んで撮る ---------------------------------------------
    print("\n[4] 撮る")
    small = OS.sensor_spec(pixel_um=3.45, resolution=(96, 72), bit_depth=8)
    wide = OS.lens_spec(focal_mm=8.0, f_number=4.0, working_distance_mm=200.0)
    dome = OS.light_spec(kind="dome", radius_mm=60.0, height_mm=80.0, n=48,
                         intensity=8000.0)
    part = OS.scene_box((0.0, 0.0, 2.0), (5.0, 4.0, 2.0),
                        OS.scene_material("lambert", albedo=0.7))
    layout = OS.vision_layout(small, wide, [dome], scene=[part])

    fov_w = 96 * 3.45e-3 * 200.0 / 8.0
    print(f"    視野 {layout['camera']['fov_mm'][0]:.4f} x "
          f"{layout['camera']['fov_mm'][1]:.4f} mm  (N·p·WD/f = {fov_w:.4f})")
    assert abs(layout["camera"]["fov_mm"][0] - fov_w) < 1e-12

    shots = {ms: OS.layout_capture(layout, exposure_ms=ms, supersample=1)
             for ms in (5.0, 10.0, 20.0)}
    for ms, cap in shots.items():
        print(f"    露光 {ms:5.1f} ms → 画素値 平均 {float(cap['image'].mean()):6.2f} "
              f"最大 {int(cap['image'].max()):3d} / 255")
    # 飽和していない範囲では信号は露光に比例する(±5%、ショット雑音のぶん)
    lo, hi = float(shots[5.0]["image"].mean()), float(shots[10.0]["image"].mean())
    assert lo > 0.0 and abs(hi / lo - 2.0) < 0.1
    assert int(shots[20.0]["image"].max()) <= 255       # 飽和は clip、折り返さない

    # 部品マスクは露光によらない(見え方が変わっても真値は同じ)
    masks = [np.count_nonzero(cap["part_mask"]) for cap in shots.values()]
    assert len(set(masks)) == 1
    print(f"    部品マスクは露光によらず {masks[0]} px(見えなくても真値はある)")

    # --- 5) 回折ボケは光を作りも消しもしない -----------------------------------
    print("\n[5] 回折")
    cam = layout["camera"]
    impulse = np.zeros((36, 48, 3))
    impulse[18, 24] = 1.0
    for n in (2.8, 22.0):
        blurred = np.asarray(OS.diffraction_blur(impulse, cam, f_number=n))
        print(f"    F/{n:<4} Airy {OS.airy_radius_um(n):6.3f} um  "
              f"ピーク {float(blurred.max()):.5f}  総和 {float(blurred.sum()):.5f}")
        assert abs(float(blurred.sum()) - 3.0) < 1e-9    # 3 チャネルぶんの光量が保存
    sharp = np.asarray(OS.diffraction_blur(impulse, cam, f_number=2.8))
    soft = np.asarray(OS.diffraction_blur(impulse, cam, f_number=22.0))
    assert soft.max() < sharp.max()                      # 絞るほどピークは落ちる

    # --- 6) 運べるか(光学が通っても伝送で落ちる)-------------------------------
    print("\n[6] 伝送バジェット")
    frame_bytes = sensor["width"] * sensor["height"] * (sensor["bit_depth"] / 8)
    for iface, links in (("CXP-12", 4), ("10GigE", 1), ("CameraLink-Full", 1)):
        b = OS.interface_budget(sensor, interface=iface, links=links)
        print(f"    {iface:16s} x{links}  {b['gbps']:6.2f} Gbps  → {b['max_fps']:8.1f} fps")
        assert abs(b["bytes_per_frame"] - frame_bytes) < 1e-9
        assert abs(b["max_fps"] - b["gbps"] * 1e9 / 8.0 / frame_bytes) < 1e-6
    # 効率は素通しでなく掛かる(12.5 x 4 x 0.85 = 42.5)
    assert abs(OS.interface_budget(sensor, "CXP-12", 4)["gbps"] - 12.5 * 4 * 0.85) < 1e-9

    # --- 7) ライン走査 —— 既定では画素が正方形にならない -----------------------
    print("\n[7] ライン走査")
    line_cam = OS.optical_camera(focal_mm=16.0, pixel_um=3.45, resolution=(64, 1),
                                 working_distance_mm=200.0)
    strip = OS.scene_box((0.0, 0.0, 1.0), (20.0, 3.0, 1.0),
                         OS.scene_material("lambert", albedo=0.7))
    bar = OS.light_spec(kind="bar", radius_mm=40.0, height_mm=60.0, n=24,
                        intensity=8000.0)
    scan = OS.linescan_capture([strip], line_cam, [bar], velocity_mm_s=100.0,
                               line_rate_hz=10000.0, lines=64)
    cross = 3.45e-3 * 200.0 / 16.0
    print(f"    100 mm/s @ 10 kHz → 走査 {scan['pixel_mm_scan']:.6f} mm / "
          f"直交 {scan['pixel_mm_cross']:.6f} mm  アスペクト {scan['aspect']:.4f}")
    assert abs(scan["pixel_mm_scan"] - 100.0 / 10000.0) < 1e-15
    assert abs(scan["pixel_mm_cross"] - cross) < 1e-15
    assert scan["aspect"] < 0.3                          # ここが像の伸縮の正体

    square_hz = 100.0 / cross
    fixed = OS.linescan_capture([strip], line_cam, [bar], velocity_mm_s=100.0,
                                line_rate_hz=square_hz, lines=64)
    print(f"    正方画素にする条件: ライン周波数 = 速度 / 直交画素 = {square_hz:.2f} Hz"
          f"  → アスペクト {fixed['aspect']:.6f}")
    assert abs(fixed["aspect"] - 1.0) < 1e-12

    # --- 8) 生の放射輝度からセンサー出力へ(雑音・飽和・量子化)-----------------
    print("\n[8] センサーの応答")
    # 電子数 = radiance · 露光[ms] · gain / 1000。10 ms・gain 5e4 なら
    # radiance 20 でちょうど満杯(full_well 1e4)—— **radiance は正規化された単位**
    # なので、この換算は自分のシーンで一度合わせる必要がある
    radiance = np.linspace(0.0, 20.0, 7).reshape(1, 7)
    dn = OS.sensor_capture(radiance, exposure_ms=10.0, gain_e_per_unit=5.0e4,
                           read_noise_e=2.5, full_well_e=1.0e4, bit_depth=8, seed=0)
    print(f"    radiance {np.round(radiance.ravel(), 1)} → DN {dn.ravel()}")
    assert dn.shape == radiance.shape and dn.dtype == np.int32
    assert int(dn.max()) <= 255 and int(dn.min()) >= 0
    # 単調(雑音があっても、この間隔なら順序は保たれる)
    assert np.all(np.diff(dn.ravel().astype(int)) >= 0)
    # 飽和は張り付き、折り返さない
    hot = OS.sensor_capture(np.full((4, 4), 200.0), exposure_ms=10.0, bit_depth=8, seed=0)
    assert int(hot.min()) == 255 and int(hot.max()) == 255
    print(f"    満杯の 10 倍を入れても DN は {int(hot.max())} で張り付く(折り返さない)")

    # --- 9) 実機を組む前に「その照明で見えるか」を見る -------------------------
    print("\n[9] 照明で見え方が桁で変わる(同じ加工目・同じ材質)")
    for illum in ("coaxial", "dome", "ring"):
        obs = OS.observe_surface(material="al", finish="hairline", pitch_um=90.0,
                                 illumination=illum, resolution=(64, 64),
                                 supersample=1, seed=0)
        img = obs["image"]
        span = float(np.percentile(img, 99) - np.percentile(img, 1))
        print(f"    {illum:8s} 平均 {float(img.mean()):.4f}  コントラスト(p99−p1) {span:.4f}")
        if illum == "coaxial":
            coax = span
        elif illum == "dome":
            dome_span = span
    # 加工目は方向性のある微細形状なので、拡散照明では消え、指向性の照明では出る
    assert coax > 10.0 * dome_span
    print(f"    → 同軸は拡散(ドーム)の {coax / dome_span:.0f} 倍のコントラスト。"
          "照明を選ぶのが仕事である理由がここ")

    print("\n" + "=" * 78)
    print("PASS: 覆えるか・分解できるか・運べるか・写るかを、すべて撮る前に数字で決めた")
    print("=" * 78)


if __name__ == "__main__":
    main()
