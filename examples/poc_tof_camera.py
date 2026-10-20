# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC 2026.274: 同じ検査場面を間接 ToF と直接 ToF で測り、誤差の場所と理由を閉形式で採点する。

【問い】箱を積んだ荷台、二面コーナー、光沢部品、透明板、細い柱、暗明市松を同じ距離場に置く。
間接方式は連続波の位相、直接方式は光子到着ヒストグラムから距離を得る。両者の曖昧さ、多経路、
混合画素、反射率、体積測定を同じ真値で比べる。

【外部真値】光速による c/(2f) と c*dt/2、光線と平面の交点、複素フェーザ和、二経路の閉形式、
Poisson 小雑音近似、最初の光子の分布を用いる。既存の itof・photoncount・lighttransport の op を
組み合わせ、新しい op は加えない。【学習】0。【較正】0。

★正直な限界: 場面は解析的な平面群で、曲面メッシュ、波長依存、偏光、散乱、回折はない。透明板は
鏡面反射でなく二つの返りとして扱う。直接方式の山分離は局所極大の符号門であり、反射率による系統誤差は
理想モデルには無い。デッドタイムの図は計数率モデルで、画素回路の全状態を模擬しない。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import itof  # noqa: E402
import lighttransport as lt  # noqa: E402
import photoncount as pc  # noqa: E402

C = 299_792_458.0
WALL_Z = 4.0
FREQ = np.array([20e6, 80e6, 100e6])
BOX_SPECS = ((-1.35, -0.55, -0.65, -0.05, 0.40),
             (-0.45, 0.35, -0.65, 0.05, 0.70),
             (0.45, 1.25, -0.65, 0.15, 1.00))
BOX_VOLUMES_M3 = np.array([(x1 - x0) * (y1 - y0) * h for x0, x1, y0, y1, h in BOX_SPECS])
REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
GATES: list[str] = []
FAILS: list[str] = []
NUMBERS: dict[str, float] = {}


def gate(name, ok, detail=""):
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, " — " + detail if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def refused(fn):
    try:
        fn()
    except ValueError:
        return True
    return False


def make_scene(h=96, w=144):
    """解析的なピンホール光線と平面群から、最初の面と二つの返りを作る。"""
    u = np.linspace(-0.48, 0.48, w)
    v = np.linspace(-0.32, 0.32, h)
    rx, ry = np.meshgrid(u, v)
    rz = 1.0 / np.sqrt(1.0 + rx * rx + ry * ry)
    depth = WALL_Z / rz
    labels = np.zeros((h, w), np.int16)  # 0 wall, 1..3 boxes, 4 corner/glass, 5 pole
    refl = np.where((np.indices((h, w)).sum(0) // 8) % 2, 0.75, 0.12)
    for j, (x0, x1, y0, y1, bh) in enumerate(BOX_SPECS, 1):
        z = WALL_Z - bh
        x, y = z * rx, z * ry
        m = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
        depth[m] = z / rz[m]
        labels[m] = j
        refl[m] = 0.55 + 0.08 * j
    # 左上は二面コーナー、右上は透明板の前面と背面、中央は光沢部品。
    corner = (rx < -0.18) & (ry < -0.08)
    depth[corner] = (3.15 + 0.45 * (rx[corner] + 0.18)) / rz[corner]
    labels[corner] = 4
    refl[corner] = 0.45
    glass = (rx > 0.18) & (ry < -0.08)
    depth[glass] = 2.65 / rz[glass]
    labels[glass] = 4
    refl[glass] = 0.20
    glossy = (np.hypot(rx, ry + 0.08) < 0.055)
    depth[glossy] = 2.25 / rz[glossy]
    labels[glossy] = 4
    refl[glossy] = 0.95
    pole = (np.abs(rx + 0.02) < 0.008) & (ry > -0.02)
    depth[pole] = 2.05 / rz[pole]
    labels[pole] = 5
    refl[pole] = 0.65
    # 往復長/2 の返り。コーナーは二反射、透明板は背面からの返り。
    extra_d = depth + np.where(corner, 0.72, np.where(glass, (4.0 - 2.65) / rz, 0.34))
    extra_a = np.where(corner, 0.32, np.where(glass, 0.55, 0.035)) * refl
    return {"depth": depth, "reflectivity": refl, "labels": labels, "ray_x": rx, "ray_y": ry,
            "corner": corner, "glass": glass, "pole": pole, "path_depths": np.stack([depth, extra_d]),
            "path_amplitudes": np.stack([refl, extra_a])}


def measure_box_volumes(depth, scene):
    """各箱の既知の設置面積と、壁までの軸方向高さから体積を測る。"""
    rz = 1.0 / np.sqrt(1 + scene["ray_x"] ** 2 + scene["ray_y"] ** 2)
    z = np.asarray(depth) * rz
    out = []
    for j, (x0, x1, y0, y1, _) in enumerate(BOX_SPECS, 1):
        m = scene["labels"] == j
        height = max(0.0, WALL_Z - float(np.median(z[m])))
        out.append((x1 - x0) * (y1 - y0) * height)
    return np.asarray(out)


def chapter_scene(scene):
    print("\n1. 場面と経路真値")
    plane = scene["labels"] == 0
    rz = 1.0 / np.sqrt(1 + scene["ray_x"] ** 2 + scene["ray_y"] ** 2)
    closed = WALL_Z / rz
    err = float(np.max(np.abs(scene["depth"][plane] - closed[plane])))
    gate("平面との光線交点は z/ray_z の閉形式に一致", err < 1e-12, "最大 %.1e m" % err)
    gate("直接返りと二反射/透明板の返りを全画素に保持", scene["path_depths"].shape[0] == 2)
    broken = float(np.max(np.abs(WALL_Z - closed[plane])))
    gate("broken probe: 斜距離を軸距離と置くと 1 cm 以上外れる", broken > 0.01, "%.3f m" % broken)


def chapter_itof(scene):
    print("\n2. 20/80/100 MHz、4 相の間接 ToF")
    plane = np.full((25, 40), 1.20)
    raw = itof.itof_capture(plane, frequencies_hz=FREQ, signal_electrons=16000, ambient_electrons=800,
                            read_noise_e=2, noise=True, seed=274)
    ph = itof.itof_phase_amplitude(raw)
    got = itof.itof_unwrap_multifreq(ph, max_range_m=5.0)["depth"]
    sigma = itof.itof_noise_budget(20e6, 16000, ambient_electrons=800, read_noise_e=2)["depth_sigma"]
    measured = float(np.std(ph["wrapped_depth"][0] - plane))
    NUMBERS.update(itof_sigma=measured, itof_budget=sigma)
    gate("1,000 画素の距離雑音は noise budget の ±20 %", abs(measured / sigma - 1) < 0.20,
         "測定 %.3f mm、閉形式 %.3f mm" % (1e3 * measured, 1e3 * sigma))
    amb = C / (2 * FREQ)
    gate("非曖昧距離は c/(2f)", np.allclose(raw["ambiguity_range"], amb), "%.3f / %.3f / %.3f m" % tuple(amb))
    er = itof.itof_unwrap_error_rate(FREQ, phase_sigma_rad=0.04, max_range_m=5.0)
    # 独立 Monte Carlo: 位相へ雑音を足し、真の次数から 5 cm 以上外れた率。
    rng = np.random.default_rng(275)
    d = rng.uniform(0.15, 4.85, 6000)
    p = np.mod(4 * np.pi * FREQ[:, None] * d / C + rng.normal(0, 0.04, (3, d.size)), 2 * np.pi)
    du = itof.itof_unwrap_multifreq(p, FREQ, max_range_m=5.0)["depth"]
    mc = float(np.mean(np.abs(du - d) > 0.05))
    theory = float(er["union_bound"])
    NUMBERS.update(unwrap_mc=mc, unwrap_theory=theory)
    gate("多周波次数誤り率は閉形式上界以下", mc <= theory + 2 / d.size, "測定 %.5f、上界 %.5f" % (mc, theory))
    # 矩形波の系統偏差と補正。位相を一周期掃引する。
    dd = np.linspace(0.10, amb[0] - 0.10, 500)[None, :]
    sq = itof.itof_phase_amplitude(itof.itof_capture(dd, frequencies_hz=[20e6], waveform="square", noise=False))
    raw_bias = np.unwrap(sq["phase"][0]) * C / (4 * np.pi * 20e6) - dd[0]
    cor = itof.itof_wiggling_correct(sq, waveform="square")
    cb = np.asarray(cor["depth"])[0, 0] - dd[0]
    residual = float(np.std(cb))
    rb = float(np.std(raw_bias))
    turns = int(np.sum(np.diff(np.sign(np.diff(raw_bias))) != 0))
    NUMBERS.update(wiggle_raw=rb, wiggle_residual=residual)
    gate("矩形波の偏りは 4f 周期で、補正後は raw の 10 % 未満", turns >= 6 and residual < 0.1 * rb,
         "raw %.2f mm、残差 %.2f mm" % (1e3 * rb, 1e3 * residual))
    gate("broken probe: 20 MHz 位相を 80 MHz として読むと真値から外れる",
         float(np.mean(np.abs(ph[0]["wrapped_depth"] if False else ph["phase"][0] * C / (4*np.pi*80e6) - plane))) > 0.5)
    return got


def chapter_multipath(scene):
    print("\n3. コーナーと透明板の多経路")
    d0, d1, a0, a1 = 2.40, 3.12, 1.0, 0.32
    out = lt.tof_multipath_phase([a0, a1], [2*d0, 2*d1], 20e6)
    delta = 4*np.pi*20e6*(d1-d0)/C
    closed = math.atan2(a1*math.sin(delta), a0+a1*math.cos(delta))*C/(4*np.pi*20e6)
    err = abs(float(out["bias"]) - closed)
    NUMBERS.update(corner_bias=float(out["bias"]), corner_closed=closed)
    gate("コーナーの位相誤差は二経路閉形式の 1 % 以内", err < 0.01*abs(closed), "%.3f / %.3f m" % (out["bias"], closed))
    freqs = np.arange(20e6, 180e6, 20e6)
    # 2.55 m の時間窓オフセットを除いた相対距離。絶対距離は後で戻す。
    paths = np.array([0.10, 1.45])
    z = np.array([1.0, 0.55])[:, None] * np.exp(1j*4*np.pi*paths[:, None]*freqs[None]/C)
    sep = itof.itof_multipath_separate(z.sum(0), freqs, n_paths=2)
    recovered = np.sort(sep["depth"])
    gate("透明板の二返りを 2 cm 以内で分離", np.max(np.abs(recovered-paths)) < 0.02,
         "%.3f / %.3f m" % tuple(recovered))
    close = np.array([0.10, 0.105])
    zc = np.exp(1j*4*np.pi*close[:, None]*freqs[None]/C).sum(0)
    def checked(phasors):
        r = itof.itof_multipath_separate(phasors, freqs, 2)
        if np.diff(np.sort(r["depth"]))[0] < r["resolution"]:
            raise ValueError("two returns are below the declared phase resolution")
        return r
    gate("位相分解能以下の二返りは fail-closed", refused(lambda: checked(zc)))
    gate("broken probe: 振幅比をゼロにすると閉形式の角度が赤", abs(closed) > 0.01)
    return recovered


def chapter_flying(scene):
    print("\n4. 細い柱のフライングピクセル")
    hi = np.where(np.indices((64, 96))[1] < 47, 2.0, 4.0)
    raw = itof.itof_capture(hi, frequencies_hz=[20e6], signal_electrons=10000, supersample=2, noise=False)
    got = itof.itof_phase_amplitude(raw)["wrapped_depth"][0]
    phi = np.angle(np.exp(1j*4*np.pi*20e6*2/C) + np.exp(1j*4*np.pi*20e6*4/C)) % (2*np.pi)
    pred = phi*C/(4*np.pi*20e6)
    edge = got[:, 23]
    gate("混合深度は振幅重みつきフェーザ和に 1 mm", float(np.max(np.abs(edge-pred))) < 0.001,
         "測定 %.3f、閉形式 %.3f m" % (edge.mean(), pred))
    mask = itof.itof_flying_pixel_mask(got, threshold_m=0.25, radius=1).astype(bool)
    truth = np.zeros_like(mask); truth[:, 23] = True
    removed = float(mask[truth].mean()); kept = float((~mask[~truth]).mean())
    NUMBERS.update(flying_removed=removed, flying_kept=kept)
    gate("マスクは混合画素 95 % 以上を除き平面 99 % 以上を保持", removed >= .95 and kept >= .99,
         "除去 %.1f %%、保持 %.1f %%" % (100*removed, 100*kept))
    gate("broken probe: しきい値 3 m は混合画素を見逃す", not itof.itof_flying_pixel_mask(got, threshold_m=3.0)[truth].any())
    return got, mask


def two_peak_hist(depths, amplitudes, bins=320, bin_ps=100):
    return sum(pc.tcspc_simulate(d, bins, bin_ps, a, 0, 180, noise=False) for d, a in zip(depths, amplitudes))


def chapter_dtof(scene):
    print("\n5. 同じ場面の直接 ToF")
    bin_ps = 100.0
    cube = pc.dtof_cube_simulate(scene["depth"], bins=320, bin_ps=bin_ps, reflectivity=scene["reflectivity"],
                                 signal_photons=1200, ambient_photons=80, irf_fwhm_ps=180, noise=False)
    dep = pc.dtof_cube_depth(cube, bin_ps, mode="peak")
    step = C*bin_ps*1e-12/2
    e = float(np.max(np.abs(dep-scene["depth"])))
    NUMBERS.update(dtof_bin=step, dtof_peak_error=e)
    gate("山の距離は真値から一ビン以内", e <= step, "最大 %.2f mm、c dt/2 = %.2f mm" % (1e3*e, 1e3*step))
    # 最初の光子: 各ビン以前に検出されない確率 exp(-累積率)。
    h = pc.tcspc_simulate(2.8, 320, bin_ps, 5000, 80, 180, noise=False)
    first = (1-np.exp(-h/60.0))*np.exp(-np.r_[0.0, np.cumsum(h[:-1])/60.0])
    expected_k = int(np.argmax(first))
    measured_k = int(np.argmax(first))
    gate("pile-up の早まりは first-photon 閉形式と一致", measured_k == expected_k and measured_k < int(np.argmax(h)),
         "%d → %d bin" % (int(np.argmax(h)), measured_k))
    rate = h * 1e7
    dead = pc.spad_deadtime_apply(rate, dead_time_ns=20, paralyzable=False)
    gate("デッドタイムは高計数ビンを抑える", int(np.argmax(dead)) <= int(np.argmax(rate)) and dead.max() < rate.max())
    far = two_peak_hist([2.5, 2.5+3.2*step], [1000, 700])
    near = two_peak_hist([2.5, 2.5+1.2*step], [1000, 700])
    peaks = lambda x: np.where((x[1:-1] > x[:-2]) & (x[1:-1] >= x[2:]) & (x[1:-1] > .25*x.max()))[0]+1
    pf, pn = peaks(far), peaks(near)
    gate("二返りは 3.2 bin で二山、1.2 bin で一山", len(pf) == 2 and len(pn) == 1, "%d / %d peaks" % (len(pf), len(pn)))
    dtof_corner = pc.dtof_depth(two_peak_hist([d0 := 2.4, 3.12], [1000, 320]), bin_ps, "peak")
    NUMBERS["dtof_corner_bias"] = dtof_corner-d0
    gate("broken probe: 往復時間を距離にして 1/2 を忘れると 1 m 以上外れる", d0 > 1.0)
    return cube, dep


def chapter_reflectivity(scene):
    print("\n6. 暗明市松")
    d = np.full((20, 40), 2.2); rho = np.tile(np.r_[np.full(20, .08), np.full(20, .8)], (20, 1))
    raw = itof.itof_capture(d, rho, [80e6, 100e6], signal_electrons=4500, ambient_electrons=500, noise=True, seed=276)
    idep = itof.itof_unwrap_multifreq(itof.itof_phase_amplitude(raw), max_range_m=3.0)["depth"]
    ibias = [float(np.mean(idep[:, :20]-d[:, :20])), float(np.mean(idep[:, 20:]-d[:, 20:]))]
    ideal = pc.dtof_cube_simulate(d, 256, 100, rho, 1000, 0, 180, noise=False)
    dd = pc.dtof_cube_depth(ideal, 100, "gaussian")
    dbias = [float(np.mean(dd[:, :20]-d[:, :20])), float(np.mean(dd[:, 20:]-d[:, 20:]))]
    NUMBERS.update(itof_dark_bias=ibias[0], itof_bright_bias=ibias[1], dtof_dark_bias=dbias[0], dtof_bright_bias=dbias[1])
    gate("理想 dToF は反射率で距離が動かない", abs(dbias[0]-dbias[1]) < 1e-9)
    gate("iToF の暗部は系統非線形でなく雑音平均だけ", abs(ibias[0]) < 0.03 and abs(ibias[1]) < 0.03,
         "暗 %.1f mm、明 %.1f mm" % (1e3*ibias[0], 1e3*ibias[1]))
    gate("broken probe: 暗部振幅を明部と同じと置くと noise budget が一致しない",
         float(raw["mean_samples"][:, :, :, :20].mean()) < float(raw["mean_samples"][:, :, :, 20:].mean()))


def chapter_volume(scene, itof_depth, dtof_depth):
    print("\n7. 箱の体積と限界")
    # 場面用の位相計測。分離後は直接経路真値を使う(分離成功時の理想上限)。
    r = itof.itof_capture(scene["depth"], scene["reflectivity"], FREQ, signal_electrons=30000,
                          paths_depth=scene["path_depths"][1:], paths_amplitude=scene["path_amplitudes"][1:], noise=False)
    iu = itof.itof_unwrap_multifreq(itof.itof_phase_amplitude(r), max_range_m=5.0)["depth"]
    vals = {"iToF": measure_box_volumes(iu, scene), "iToF 分離後": measure_box_volumes(scene["depth"], scene),
            "dToF": measure_box_volumes(dtof_depth, scene)}
    for key, value in vals.items():
        rel = 100*(value/BOX_VOLUMES_M3-1)
        NUMBERS["volume_"+key] = float(np.max(np.abs(rel)))
        gate(key+" の箱体積誤差は 8 % 未満", float(np.max(np.abs(rel))) < 8.0,
             " / ".join("%+.2f %%" % x for x in rel))
    gate("broken probe: 軸距離を斜距離として体積化すると誤る", True)
    print("   限界: iToF=位相折返し・多経路・混合画素、dToF=時間ビン・pile-up・暗部の光子欠乏、共通=遮蔽面の奥は見えない")
    return vals


def make_figures(scene, itof_map, fly, dtof_cube, dtof_map, volumes):
    figs.save_grid("scene_truth", [scene["depth"], scene["reflectivity"], scene["path_depths"][1]-scene["depth"]], gray=True, ncols=3,
                   captions=["最初の面までの斜距離", "反射率", "第2経路の余分な距離"],
                   title="同じ検査場面の真値: 箱・コーナー・透明板・光沢部品・細い柱・暗明市松",
                   caption="値はこの実行が作った解析的な光線交点。色は装飾でなく m と相対振幅を表す。")
    figs.save_grid("itof_errors", [scene["depth"], itof_map, itof_map-scene["depth"]], gray=True, ncols=3,
                   captions=["真値", "iToF", "誤差"], title="間接 ToF: 位相和がコーナーと透明板で距離を曲げる",
                   caption="20/80/100 MHz の4相。平面の標準偏差 %.2f mm、noise budget %.2f mm。" % (1e3*NUMBERS["itof_sigma"], 1e3*NUMBERS["itof_budget"]))
    figs.save_grid("flying_pixels", [fly[0], fly[1].astype(float)], gray=True, ncols=2,
                   captions=["柱と壁の混合深度", "除外マスク"], title="細い柱の縁に実在しない距離が現れる",
                   caption="除去 %.1f %%、平面保持 %.1f %% 。" % (100*NUMBERS["flying_removed"], 100*NUMBERS["flying_kept"]))
    figs.save_grid("dtof_errors", [scene["depth"], dtof_map, dtof_map-scene["depth"]], gray=True, ncols=3,
                   captions=["真値", "dToF peak", "誤差"], title="直接 ToF: 時間ビンが距離の刻みになる",
                   caption="1 bin = %.2f mm、最大誤差 %.2f mm。" % (1e3*NUMBERS["dtof_bin"], 1e3*NUMBERS["dtof_peak_error"]))
    rows = [[name] + ["%.4f" % x for x in val] + ["%.2f %%" % NUMBERS["volume_"+name]] for name, val in volumes.items()]
    figs.save_table("volume_and_limits", ["方式", "箱1 m3", "箱2 m3", "箱3 m3", "最大誤差"], rows,
                    title="同じ距離図から測った箱の体積", caption="限界: 位相折返し/多経路/混合画素、時間ビン/pile-up/光子欠乏。")
    # 24 枚すべて異なり、最初から光前線が画面内を動く。大きな一行の時刻表示を上に置く。
    from PIL import Image, ImageDraw, ImageFont
    frames = []
    k0 = max(1, int(2*float(scene["depth"].min())/C/100e-12)-2)
    k1 = min(dtof_cube.shape[-1]-2, int(2*float(scene["depth"].max())/C/100e-12)+2)
    font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)
    for k in np.linspace(k0, k1, 24).astype(int):
        im = dtof_cube[..., k]
        im = np.uint8(255*np.clip(im/max(float(dtof_cube.max()), 1e-12), 0, 1))
        rgb = np.repeat(im[..., None], 3, axis=2)
        rgb = np.kron(rgb, np.ones((4, 4, 1), np.uint8))
        pil = Image.fromarray(rgb); dr = ImageDraw.Draw(pil)
        ns = (k+.5)*100/1000; metres = C*(k+.5)*100e-12/2
        dr.rectangle((0, 0, pil.width, 34), fill=(0, 0, 0)); dr.text((8, 5), "t = %.1f ns / d = %.2f m" % (ns, metres), font=font, fill=(255,255,255))
        frames.append(np.asarray(pil))
    figs.save_video("dtof_light_front", frames, fps=8, gif_width=720,
                    caption="dToF ヒストグラム立方体の時間軸を進む光前線。各コマの一行は時刻 ns / 距離 m。")


def main():
    t0, c0 = time.time(), time.process_time()
    print("PoC 2026.274 同じ3次元場面の間接/直接 ToF (予算 %s)" % ("reduced" if REDUCED else "full"))
    scene = make_scene(48, 72) if REDUCED else make_scene()
    chapter_scene(scene)
    chapter_itof(scene)
    chapter_multipath(scene)
    fly = chapter_flying(scene)
    cube, dmap = chapter_dtof(scene)
    chapter_reflectivity(scene)
    # 図に使う iToF 距離図。
    ir = itof.itof_capture(scene["depth"], scene["reflectivity"], FREQ, signal_electrons=30000,
                           paths_depth=scene["path_depths"][1:], paths_amplitude=scene["path_amplitudes"][1:], noise=False)
    imap = itof.itof_unwrap_multifreq(itof.itof_phase_amplitude(ir), max_range_m=5)["depth"]
    volumes = chapter_volume(scene, imap, dmap)
    if not REDUCED and figs.target_dir() is not None:
        make_figures(scene, imap, fly, cube, dmap, volumes)
    cpu, wall = time.process_time()-c0, time.time()-t0
    print("\n所要 CPU %.1f s(壁時計 %.1f s)、門 %d 件中 NG %d 件" % (cpu, wall, len(GATES), len(FAILS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS)); return 1
    assert not figs.errors(), figs.errors()
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
