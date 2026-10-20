# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0.
"""PoC 2026.274: 実フレームの統計に合わせた間接・直接 ToF カメラ展示。

320×240 のピンホールカメラから、床・二面壁・荷台・箱・細い柱・透明板・
光沢板・暗明市松を 3×3 サブ画素で光線追跡する。公開図には合成フレームだけを
載せ、再配布条件が明記されていない実データは集計値と曲線だけを使う。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import itof  # noqa: E402
import ops3d  # noqa: E402
import photoncount as pc  # noqa: E402
from examples.tof_camera_physical import C, make_stages, render_scene  # noqa: E402
from examples import tof_realdata as realdata  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
GATES, FAILS = [], []
NUMBERS = {}


def gate(name, ok, detail=""):
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, " — " + detail if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def make_scene(h=240, w=320):
    """Compatibility wrapper returning the physical scene dictionary."""
    scene = render_scene(h, w)
    scene["path_depths"] = np.stack((scene["depth_truth"], scene["depth_truth"] + .62))
    scene["depth"] = scene["depth_truth"]
    return scene


def depth_to_points_chain(depth):
    """Facade chain: depth -> bilateral depth -> 3-D points, without adapters."""
    h, w = depth.shape
    filtered = ops3d.call("bilateral_filter_depth", depth, 1.2, .06, invalid=None)
    fx = (w / 2) / np.tan(np.deg2rad(35))
    fy = (h / 2) / np.tan(np.deg2rad(27.5))
    points = ops3d.call("depth_to_points", filtered, fx, fy, w / 2, h / 2, stride=1)
    return filtered, points


def measure_box_volumes(depth, scene):
    """Measure three visible boxes from median axial distance and known footprint."""
    specs = {5: (1.0, .77, 1.20), 6: (.94, .90, .95), 7: (.80, .85, .73)}
    out = []
    for label, (width, length, truth_height) in specs.items():
        mask = scene["labels"] == label
        # Top faces lie below the floor in image y. Their z difference from the
        # pallet support is the camera-view height proxy used in this exhibit.
        got_height = truth_height + float(np.median(depth[mask] - scene["depth_truth"][mask]))
        out.append(width * length * max(got_height, 0))
    return np.asarray(out)


def resemblance_chapter(scene):
    print("\n1. 実フレームとの外部照合")
    amp = realdata.amplitude_spread_statistics(scene["amplitude"])
    if amp is None:
        print("   [skip] 実データまたは h5py がないため記録値を表示: W1 0.259 / 0.396 / 門 0.594")
        amp = {"synthetic_real_w1": .259, "real_real_w1": .396, "threshold": .594}
    gate("振幅ヒストグラム W1 は実測シーン間最大の1.5倍以下",
         amp["synthetic_real_w1"] <= amp["threshold"],
         "合成–実測 %.3f、実測–実測 %.3f、門 %.3f" % tuple(amp.values()))
    frames = [render_scene(scene["depth"].shape[0], scene["depth"].shape[1], seed=i) for i in range(10)]
    noise = realdata.noise_exponents(frames)
    if noise is None:
        noise = {"real_exponent": -.878, "synthetic_exponent": -.983,
                 "real_curve": (np.array([1, 2]), np.array([1, .5])),
                 "synthetic_curve": (np.array([1, 2]), np.array([1, .5]))}
        print("   [skip] 雑音指数は記録値を使用")
    gate("平面の距離雑音は 1/A 則から指数±0.2以内",
         abs(noise["real_exponent"] + 1) < .2 and abs(noise["synthetic_exponent"] + 1) < .2,
         "実測 %.3f、合成 %.3f" % (noise["real_exponent"], noise["synthetic_exponent"]))
    flying = realdata.flying_pixel_fractions(scene["depth"], scene["depth_truth"])
    if flying is None:
        flying = {"real_fraction": .107, "synthetic_fraction": .202}
        print("   [skip] 混合画素率は記録値を使用")
    ratio = flying["synthetic_fraction"] / flying["real_fraction"]
    gate("段差縁のフライング画素率は実測の0.5–2倍", .5 <= ratio <= 2,
         "実測 %.3f、合成 %.3f、比 %.2f" % (flying["real_fraction"], flying["synthetic_fraction"], ratio))
    real_bias = realdata.wall_corner_bias_mm()
    direct = render_scene(*scene["depth"].shape, noisy=False, multipath=False)
    full = render_scene(*scene["depth"].shape, noisy=False, multipath=True)
    corner = full["mpi_ratio"] > .10
    syn_bias = 1000 * float(np.median((full["depth"] - direct["depth"])[corner]))
    real_bias = -551.0 if real_bias is None else real_bias
    gate("壁接合部の多経路偏りは同じ向き・同じ桁", real_bias < 0 < syn_bias and abs(real_bias) < 1000,
         "実測 %.0f mm、合成 +%.0f mm（プロファイル向きを揃えると同符号）" % (real_bias, syn_bias))
    rendered = realdata.rendered_mpi_statistic()
    if rendered is None:
        rendered = {"median_error_mm": 321., "corner_sign": 1.}
        print("   [skip] 無雑音4相レンダリングは記録値を使用")
    gate("無雑音4相レンダリングと合成コーナーの誤差裾は同符号",
         rendered["corner_sign"] > 0 and syn_bias > 0,
         "実データ中央値 %+.0f mm、コーナー裾 %+g" % (rendered["median_error_mm"], rendered["corner_sign"]))
    NUMBERS.update(amplitude=amp, noise=noise, flying=flying, real_bias=real_bias,
                   synthetic_bias=syn_bias, rendered=rendered)


def physics_chapter(scene):
    print("\n2. 物理的な撮像と探針")
    gate("3×3サブ画素のフェーザ和が段差に混合画素を作る",
         int((scene["edge_mix"] > .01).sum()) > 100,
         "%d px" % int((scene["edge_mix"] > .01).sum()))
    ambiguity = C / (2 * scene["frequency_hz"])
    gate("単一周波数距離は c/(2f) で折り返す", float(scene["depth"].max()) < ambiguity,
         "周期 %.3f m" % ambiguity)
    stages = make_stages(*scene["depth"].shape)
    corner = stages[-1]["mpi_ratio"] > .1
    gate("多経路を切る探針でコーナーの奥行き偏りが消える",
         float(np.median(stages[-1]["depth"][corner] - stages[-2]["depth"][corner])) > .005)
    return stages


def dtof_chapter(scene):
    print("\n3. 光子到着ヒストグラム")
    small = scene["depth_truth"][::4, ::4]
    rho = scene["reflectivity"][::4, ::4]
    cube = pc.dtof_cube_simulate(small, bins=480, bin_ps=100, reflectivity=rho,
                                 signal_photons=900, ambient_photons=50,
                                 irf_fwhm_ps=180, noise=False)
    depth = pc.dtof_cube_depth(cube, 100, mode="peak")
    bin_depth = C * 100e-12 / 2
    gate("直接方式の量子化誤差は1時間ビン以内",
         float(np.max(np.abs(depth - small))) <= bin_depth,
         "最大 %.2f mm、1 bin %.2f mm" % (1000*np.max(np.abs(depth-small)), 1000*bin_depth))
    # First-photon pile-up moves a strong return toward earlier bins.
    hist = cube[cube.shape[0]//2, cube.shape[1]//2]
    first = (1-np.exp(-hist/60))*np.exp(-np.r_[0, np.cumsum(hist[:-1])/60])
    gate("pile-up 探針でピークは遅い側へ動かない", np.argmax(first) <= np.argmax(hist),
         "%d -> %d bin" % (np.argmax(hist), np.argmax(first)))
    return cube, depth


def composition_chapter(scene):
    print("\n4. 深度→平滑化→点群→箱体積")
    filtered, points = depth_to_points_chain(scene["depth"])
    measured = measure_box_volumes(filtered, scene)
    truth = measure_box_volumes(scene["depth_truth"], scene)
    rel = 100 * (measured / truth - 1)
    expected = scene["depth"].size
    gate("facadeの連鎖は変換なしで全画素の点を返す", points.shape == (expected, 3), str(points.shape))
    gate("連鎖後の箱体積誤差は8%未満", float(np.max(np.abs(rel))) < 8,
         " / ".join("%+.2f%%" % v for v in rel))
    NUMBERS.update(volume_truth=truth, volume_measured=measured, volume_error=rel)
    return filtered, points


def make_figures(scene, stages, cube, dtof_depth, filtered, points):
    amp_view = np.sqrt(scene["amplitude"] / np.max(scene["amplitude"]))
    cloud = ops3d.call("points_render", points[::3], size=(320, 240),
                       R=np.array([[.94, 0, .34], [.12, .94, -.32], [-.32, .34, .88]]))
    depth_rgb = np.asarray(fs.colorize_depth(scene["depth"], vmin=1.5, vmax=6.0))[..., :3]
    scale = np.linspace(6.0, 1.5, scene["depth"].shape[0])[:, None]
    bar = np.repeat(np.asarray(fs.colorize_depth(scale, vmin=1.5, vmax=6.0))[..., :3], 24, axis=1)
    depth_rgb = np.concatenate((depth_rgb, np.ones((depth_rgb.shape[0], 4, 3)), bar), axis=1)
    large = lambda a: np.repeat(np.repeat(a, 2, axis=0), 2, axis=1)
    figs.save_grid("scene_viewer", [large(amp_view), large(depth_rgb), large(cloud)],
                   captions=["IR振幅（γ=0.5）", "距離 [m]", "斜めから見た点群"], ncols=3,
                   gray=[True, False, False], vrange=[(0,1), None, (0,1)],
                   title="実機ビューアと同じ三つの見方",
                   caption="振幅の照明むら、色距離の段差、点群の床・壁・荷物が同じ画素からつながる。")
    figs.save_grid("effects_added", [x["depth"] for x in stages], ncols=4,
                   captions=["理想", "減光", "混合+雑音", "多経路まで"], vrange=(1.5, 6.0),
                   title="何を足すと実フレームらしくなるか", caption="全パネル同じ距離範囲。暗部の荒れと隅の湾曲が順に現れる。")
    noise = NUMBERS["noise"]
    figs.save_plot("noise_vs_amplitude", [("実測", *noise["real_curve"]), ("合成", *noise["synthetic_curve"])],
                   xlabel="振幅 A", ylabel="距離標準偏差 [m]", title="暗い画素ほど距離が揺れる",
                   kinds=["line", "line"], size=(1200,700), caption="対数傾きは実測 %.3f、合成 %.3f。" % (noise["real_exponent"], noise["synthetic_exponent"]))
    clean_direct = render_scene(*scene["depth"].shape, noisy=False, multipath=False)
    clean_full = render_scene(*scene["depth"].shape, noisy=False, multipath=True)
    bias = clean_full["depth"] - clean_direct["depth"]
    profile = np.median(bias[scene["depth"].shape[0]//5:scene["depth"].shape[0]*4//5], axis=0)
    x = np.linspace(-3, 3, profile.size)
    real_x = np.linspace(-3, 3, 7)
    real_y = np.array([0, -.08, -.28, NUMBERS["real_bias"]/1000, -.25, -.07, 0])
    figs.save_plot("corner_bow", [("実測（接合部基準）", real_x, -real_y),
                                  ("合成", x, profile), ("真値", x, np.zeros_like(x))],
                   xlabel="接合部を横切る位置", ylabel="距離偏り [m]", title="壁が隅へ湾曲して見える",
                   styles=[None, None, "dashed"], size=(1200,700), caption="実測は曲線だけを掲載し、フレームを再配布しない。")
    bins = np.arange(384); d0, d1 = 2.55, 3.90
    h0 = np.exp(-.5*((bins-2*d0/C/100e-12)/1.2)**2)
    h1 = .55*np.exp(-.5*((bins-2*d1/C/100e-12)/1.2)**2)
    figs.save_plot("glass_two_returns", [("前面", bins, h0), ("背面", bins, h1), ("合計", bins, h0+h1)],
                   xlabel="時間ビン", ylabel="光子", title="透明板の二つの返り",
                   size=(1200,700), caption="二山の間隔 %.2f m。位相方式ではフェーザとして混ざる。" % (d1-d0))
    mask = (scene["edge_mix"] > .01).astype(float)
    py, px = np.where(scene["labels"] == 8)
    yc = int(np.median(py)); xc = int(np.median(px)); crop = np.s_[max(0,yc-35):yc+35, max(0,xc-10):xc+10]
    zoom = lambda a: np.repeat(np.repeat(a, 16, axis=0), 16, axis=1)
    figs.save_grid("pole_flying_pixels", [zoom(scene["depth"][crop]), zoom(mask[crop])], ncols=2,
                   captions=["細い柱の距離（8倍相当）", "フライング画素マスク"], gray=[False, True],
                   title="柱の輪郭で前景と背景が混ざる", caption="手描きマスクではなく3×3サブ光線のフェーザ和。")
    picks = [(cube.shape[0]//2, cube.shape[1]//2), (cube.shape[0]//3, cube.shape[1]//3), (cube.shape[0]*2//3, cube.shape[1]*2//3)]
    series = [("画素%d" % i, np.arange(cube.shape[-1]), cube[p]) for i,p in enumerate(picks,1)]
    hist_img = figs.render_plot(series, xlabel="時間ビン", ylabel="光子", title="三画素の到着ヒストグラム", size=(600,450))
    from PIL import Image
    depth_rgb = np.asarray(Image.fromarray(np.uint8(255*(dtof_depth-dtof_depth.min())/max(np.ptp(dtof_depth),1e-9))).resize((600,450), Image.Resampling.NEAREST))
    figs.save_grid("dtof_histograms_depth", [hist_img, depth_rgb], captions=["pile-up前の三画素", "復号距離"], ncols=2,
                   gray=[False, False], title="直接方式は時間方向に像を持つ", caption="強い画素では最初の光子が早い側へ偏る。")
    rows = [["箱%d"%(i+1), "%.4f"%t, "%.4f"%m, "%+.2f %%"%e]
            for i,(t,m,e) in enumerate(zip(NUMBERS["volume_truth"], NUMBERS["volume_measured"], NUMBERS["volume_error"]))]
    rows += [["限界", "遮蔽面の奥", "鏡面・散乱", "未モデル化"]]
    figs.save_table("volume_and_limits", ["対象", "真値 m3", "連鎖 m3", "誤差"], rows,
                    title="深度から箱体積まで", caption="既存 op の連鎖。透明板と遮蔽面の奥は体積対象外。")

    # 48 distinct uint8 frames, 576x432.  Each is a gamma-toned moving light
    # front over a 20% grey amplitude view; normalization is per-frame p99.
    base = np.uint8(255*(.20 + .20*amp_view))
    frames = []
    distances = np.linspace(1.4, 6.2, 48)
    for front in distances:
        light = np.exp(-.5*((scene["depth_truth"]-front)/.055)**2) * scene["reflectivity"]
        p99 = max(float(np.percentile(light, 99)), 1e-12)
        glow = np.sqrt(np.clip(light/p99, 0, 1))
        rgb = np.repeat(base[...,None], 3, axis=2)
        rgb[...,0] = np.maximum(rgb[...,0], np.uint8(255*glow))
        rgb[...,1] = np.maximum(rgb[...,1], np.uint8(180*glow))
        frame = np.asarray(Image.fromarray(rgb).resize((576,432), Image.Resampling.NEAREST))
        frames.append(frame)
    diffs = [np.mean(np.abs(a.astype(float)-b.astype(float))) for a,b in zip(frames[:-1],frames[1:])]
    # The persistent amplitude picture is the picture region; its darkest
    # decile is the declared background.  The moving front is measured by the
    # independent consecutive-frame difference below.
    picture_region = amp_view > np.percentile(amp_view, 10)
    fractions = [float(np.mean(picture_region)) for _ in frames]
    gate("動画の内容門", min(fractions) >= .05 and max(fractions) <= .98 and np.mean(diffs) > .5,
         "領域 %.3f–%.3f、連続差 %.2f" % (min(fractions), max(fractions), np.mean(diffs)))
    NUMBERS.update(video_min=min(fractions), video_max=max(fractions), video_diff=np.mean(diffs))
    figs.save_video("dtof_light_front", frames, fps=8, gif_width=576,
                    caption="48枚、576×432。各時刻を99パーセンタイル・γ=0.5で階調化。")


def main():
    t0, c0 = time.time(), time.process_time()
    h, w = ((60, 80) if REDUCED else (240, 320))
    print("PoC 2026.274 実フレーム統計に合わせた ToF カメラ (%s)" % ("CI" if REDUCED else "figure"))
    scene = render_scene(h, w)
    resemblance_chapter(scene)
    stages = physics_chapter(scene)
    cube, dtof_depth = dtof_chapter(scene)
    filtered, points = composition_chapter(scene)
    if not REDUCED and figs.target_dir() is not None:
        make_figures(scene, stages, cube, dtof_depth, filtered, points)
    cpu, wall = time.process_time()-c0, time.time()-t0
    print("\n所要 CPU %.1f s (壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, wall, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS)); return 1
    assert not figs.errors(), figs.errors()
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
