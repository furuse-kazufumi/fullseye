# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""live4d(生きている組織の 3D+t を古典手法だけで見る族)の門: 真値つきの合成系列で固定する。"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import live4d as L  # noqa: E402

_OPS = ["volseq_synth_beating", "volseq_synth_dividing", "volseq_mip_video", "volseq_cut_video",
        "vol_flow_3d", "volseq_speed", "volseq_pathline_render", "volseq_pathline_orbit",
        "video_interpolate_flow", "volseq_interpolate_flow", "volseq_magnify_motion",
        "volseq_render_orbit", "focus_sweep_height_video", "focus_sweep_surface_video"]
SHAPE = (16, 24, 24)


def _grids(shape):
    return np.meshgrid(*[np.arange(n) - (n - 1) / 2.0 for n in shape], indexing="ij")


def _radius(vol):
    zz, yy, xx = _grids(vol.shape)
    d = np.sqrt(zz ** 2 + yy ** 2 + xx ** 2)
    w = np.clip(vol, 0.0, None)
    return float((w * d).sum() / w.sum())


def _blob(shape, cx=0.0, cz=0.0, s=2.5):
    zz, yy, xx = _grids(shape)
    return np.exp(-((zz - cz) ** 2 + yy ** 2 + (xx - cx) ** 2) / (2 * s * s))


def _weighted_flow(d, a):
    g = np.linalg.norm(np.stack(np.gradient(a)), axis=0)
    w = g / g.sum()
    return np.array([(d[i] * w).sum() for i in range(3)])


def test_synthetic_series_carry_their_truth():
    s = L.volseq_synth_beating(SHAPE, n_frames=8, period=8.0, amplitude=1.0, radius=6.0)
    assert s.shape == (8,) + SHAPE
    r = np.array([_radius(s[t]) for t in range(8)])
    truth = 6.0 + 1.0 * np.sin(2 * np.pi * np.arange(8) / 8.0)
    # 重心半径は殻の内側を少し重く見るので一定の下駄がつく —— 差の形(振動)が真値に合えばよい
    assert np.abs((r - r.mean()) - (truth - truth.mean())).max() < 0.15
    d = L.volseq_synth_dividing(SHAPE, n_frames=6, split_frame=2, speed=1.0)
    assert d.shape == (6,) + SHAPE
    assert np.allclose(d[0], d[2])                              # 分かれる前は同じ
    xx = _grids(SHAPE)[2]
    cx = float((d[5] * xx)[..., 12:].sum() / d[5][..., 12:].sum())
    assert abs(cx - 3.0) < 0.3                                  # 3 フレームで +3 voxel
    with pytest.raises(ValueError, match="shape must be three integers"):
        L.volseq_synth_beating((24, 24))
    with pytest.raises(ValueError, match="shape must be three integers"):
        L.volseq_synth_beating((4.9, 8, 8))                         # 切り捨てて通さない
    with pytest.raises(ValueError, match="split_frame"):
        L.volseq_synth_dividing(SHAPE, n_frames=4, split_frame=9)


def test_flow_reads_a_known_translation_in_every_axis():
    for v in (0.5, 1.0, 2.5):
        a, b = _blob(SHAPE, cx=-v / 2), _blob(SHAPE, cx=v / 2)
        d = L.vol_flow_3d(a, b)
        assert d.shape == (3,) + SHAPE
        dz, dy, dx = _weighted_flow(d, a)
        assert abs(dx - v) < 0.05 * v + 0.03 and abs(dy) < 0.05 and abs(dz) < 0.05, (v, dz, dy, dx)
    d = L.vol_flow_3d(_blob(SHAPE), _blob(SHAPE, cz=1.0))
    assert abs(_weighted_flow(d, _blob(SHAPE))[0] - 1.0) < 0.08
    with pytest.raises(ValueError, match="share one shape"):
        L.vol_flow_3d(_blob(SHAPE), _blob((16, 24, 20)))
    with pytest.raises(ValueError, match="vol_flow_3d: win"):
        L.vol_flow_3d(_blob(SHAPE), _blob(SHAPE), win=0)
    with pytest.raises(ValueError, match="reg must be > 0"):          # 0 だと平坦部で特異(LinAlgError)になる
        L.vol_flow_3d(np.zeros(SHAPE), np.zeros(SHAPE), reg=0.0)


def test_speed_and_pathlines_follow_the_dividing_blob():
    s = L.volseq_synth_dividing(SHAPE, n_frames=6, split_frame=0, speed=1.0)
    sp = L.volseq_speed(s)
    assert sp.shape == (5,) + SHAPE
    # 0 → 1 は 1 つの塊が 2 つに割れる瞬間(並進ではない)、2 → 3 はまだ 2 つが重なっていて流れが
    # 曖昧(実測 +18 %)。4 → 5 は離れた 2 つの塊がそれぞれ ±1 の並進 —— そこで速さを読む
    g = np.linalg.norm(np.stack(np.gradient(s[4])), axis=0)
    assert abs((sp[4] * g).sum() / g.sum() - 1.0) < 0.1           # 勾配のある所の速さ = 1 voxel/frame
    img = L.volseq_pathline_render(s, n_seeds=40, size=48, seed=1)
    assert img.shape == (48, 48, 3) and img.min() >= 0.0 and img.max() <= 1.0
    assert img.max() > 0.3                                       # 軌跡が描かれている
    orb = L.volseq_pathline_orbit(s, n_frames=2, n_seeds=20, size=32)
    assert orb.shape == (2, 32, 32, 3)
    with pytest.raises(ValueError, match="nothing bright"):
        L.volseq_pathline_render(s, min_speed=50.0, size=16)


def test_interpolation_beats_a_linear_blend_on_a_translating_blob():
    # 2 倍のフレームレートで作って半分に間引き、抜いたフレームを補間と比べる
    fine = np.stack([_blob(SHAPE, cx=-4.0 + 0.8 * t) for t in range(11)], axis=0)
    coarse = fine[::2]
    out = L.volseq_interpolate_flow(coarse, factor=2)
    assert out.shape == fine.shape
    assert np.allclose(out[::2], coarse)                          # 端は元のフレームそのもの
    err_flow = float(np.sqrt(((out[1::2] - fine[1::2]) ** 2).mean()))
    blend = 0.5 * (coarse[:-1] + coarse[1:])
    err_blend = float(np.sqrt(((blend - fine[1::2]) ** 2).mean()))
    assert err_flow < 0.4 * err_blend, (err_flow, err_blend)
    v = L.volseq_mip_video(fine[::2])
    vi = L.video_interpolate_flow(v, factor=3)
    assert vi.shape == (16,) + v.shape[1:]
    assert np.array_equal(L.video_interpolate_flow(v, factor=1), v)
    with pytest.raises(ValueError, match="factor"):
        L.video_interpolate_flow(v, factor=0)
    with pytest.raises(ValueError, match="MAX_CUBE_ELEMENTS"):        # 補間後の大きさも見張る
        L.video_interpolate_flow(np.zeros((2, 2048, 4096)), factor=64)


def test_magnification_scales_the_in_band_motion_by_alpha_and_leaves_the_rest():
    T = 16
    s = L.volseq_synth_beating(SHAPE, n_frames=T, period=8.0, amplitude=0.1, radius=6.0)
    r0 = np.array([_radius(s[t]) for t in range(T)])
    amp0 = (r0.max() - r0.min()) / 2
    big = L.volseq_magnify_motion(s, alpha=6.0, f_lo=0.1, f_hi=0.15, fps=1.0, sigma=0.0)
    r1 = np.array([_radius(big[t]) for t in range(T)])
    gain = (r1.max() - r1.min()) / 2 / amp0
    assert 5.0 < gain < 7.0, gain                                # 変位の倍率 ≈ alpha(線形 Eulerian)
    assert abs(np.argmax(np.abs(np.fft.rfft(r1 - r1.mean()))[1:]) - np.argmax(np.abs(np.fft.rfft(r0 - r0.mean()))[1:])) == 0
    assert np.allclose(L.volseq_magnify_motion(s, alpha=1.0, f_lo=0.1, f_hi=0.15, fps=1.0), s)   # alpha = 1 は恒等
    # 帯域外は触らない —— 殻の半径則は正弦でも像は非線形なので倍音(0.25, 0.375)が立つ。倍音の無い
    # 3/16 = 0.1875 の 1 bin だけを通す帯域なら、増幅しても系列は変わらない
    off = L.volseq_magnify_motion(s, alpha=6.0, f_lo=0.16, f_hi=0.22, fps=1.0)
    assert np.abs(off - s).max() < 1e-6
    with pytest.raises(ValueError, match="f_lo < f_hi"):
        L.volseq_magnify_motion(s, alpha=2.0, f_lo=0.3, f_hi=0.2, fps=1.0)
    with pytest.raises(ValueError, match="no FFT bin"):
        L.volseq_magnify_motion(s, alpha=2.0, f_lo=0.13, f_hi=0.14, fps=1.0)


def test_orbit_renders_advance_time_and_colour_speed():
    s = L.volseq_synth_dividing(SHAPE, n_frames=4, split_frame=0, speed=1.0)
    fr = L.volseq_render_orbit(s, n_frames=3, size=32, depth_samples=12)
    assert fr.shape == (3, 32, 32, 3) and fr.min() >= 0.0 and fr.max() <= 1.0
    assert not np.allclose(fr[0], fr[1])                          # 視点も時刻も進む
    sp = L.volseq_render_orbit(s, n_frames=2, size=32, depth_samples=12, mode="speed")
    assert sp.shape == (2, 32, 32, 3)
    with pytest.raises(ValueError, match="mode must be"):
        L.volseq_render_orbit(s, mode="colour")
    with pytest.raises(ValueError, match="needs T >= 3"):
        L.volseq_render_orbit(s[:2], n_frames=1, size=16, mode="speed")


def test_focus_sweep_recovers_a_known_height_field():
    rng = np.random.default_rng(0)
    Z, Y, X = 9, 24, 24
    from scipy import ndimage as ndi
    tex = ndi.gaussian_filter(rng.random((Y, X)), 0.7)
    yy, xx = np.mgrid[0:Y, 0:X]
    series, truth = [], []
    for t in range(2):
        h = 2.0 + 4.0 * np.exp(-((yy - 12) ** 2 + (xx - 8 - 6 * t) ** 2) / (2 * 5.0 ** 2))
        blurred = [ndi.gaussian_filter(tex, 0.3 + 0.9 * k) for k in range(Z)]
        stack = np.empty((Z, Y, X))
        for z in range(Z):
            k = np.clip(np.rint(np.abs(z - h)).astype(int), 0, Z - 1)
            stack[z] = np.choose(k, blurred)
        series.append(stack)
        truth.append(h)
    h = L.focus_sweep_height_video(np.stack(series), window=3)
    assert h.shape == (2, Y, X)
    assert float(np.sqrt(((h - np.stack(truth)) ** 2).mean())) < 0.5      # 高さの誤差 < 半枚
    out = L.focus_sweep_surface_video(np.stack(series), window=3)
    assert out.shape == (2, Y, X, 3) and out.min() >= 0.0 and out.max() <= 1.0
    # 色は高さ(青 = 低い → 赤 = 高い): 山の上は赤成分が強く、裾は青成分が強い
    top, foot = out[0][12, 8], out[0][2, 20]
    assert top[0] > top[2] and foot[2] > foot[0]
    with pytest.raises(ValueError, match="Z >= 3"):
        L.focus_sweep_surface_video(np.stack(series)[:, :2])
    # 端の面が最大なら端の高さ(0 / Z − 1)をそのまま返す(内側へ寄せない)
    edge = np.zeros((1, 4, 8, 8))
    edge[0, 0] = np.indices((8, 8)).sum(0) % 2
    assert float(L.focus_sweep_height_video(edge, window=1)[0, 4, 4]) == 0.0
    edge2 = np.zeros((1, 4, 8, 8))
    edge2[0, 3] = np.indices((8, 8)).sum(0) % 2
    assert float(L.focus_sweep_height_video(edge2, window=1)[0, 4, 4]) == 3.0


def test_series_fold_into_videos_for_videocube():
    s = L.volseq_synth_beating(SHAPE, n_frames=4, period=4.0, amplitude=1.0)
    assert np.array_equal(L.volseq_mip_video(s, axis=1), s.max(axis=1))
    assert np.array_equal(L.volseq_cut_video(s, "xz", position=0.5), s[:, :, 12, :])
    assert L.volseq_cut_video(s, "yz", position=1.0).shape == (4, 16, 24)
    with pytest.raises(ValueError, match="plane must be"):
        L.volseq_cut_video(s, "tx")
    with pytest.raises(ValueError, match="volume series"):
        L.volseq_mip_video(s[0])


# --------------------------------------------------------------------------- #
# 登録面の門                                                                    #
# --------------------------------------------------------------------------- #
def test_the_ledger_lists_every_op_and_nothing_is_missing():
    import opslive4d

    assert opslive4d.missing() == []
    assert set(opslive4d.OPSLIVE4D) == set(_OPS) == set(L.__all__) - {"MAX_SERIES_ELEMENTS"}
    assert len(opslive4d.categories()) == 5


def test_every_op_is_reachable_from_the_public_tier():
    import fullseye as fs
    import opslive4d

    for name in opslive4d.OPSLIVE4D:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "live4d"]
    assert {r[0] for r in rows} == set(_OPS)
    assert {r[3] for r in rows} == {"volseq", "video", "flow_dense", "rgb", "rgbvideo"}


def test_the_fuzzer_has_predicates_and_seeds_for_every_sort():
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opslive4d

    gens = cf.make_generators()
    for name, meta in opslive4d.OPSLIVE4D.items():
        assert meta["out"] in cf.TYPE_CHECKS, name
        for s in meta["in"]:
            assert s in cf.TYPE_CHECKS and s in gens, (name, s)
    seq = gens["volseq"](np.random.default_rng(0))
    assert cf.TYPE_CHECKS["volseq"](seq) and not cf.TYPE_CHECKS["volseq"](seq[0])
    assert cf.TYPE_CHECKS["video"](L.volseq_mip_video(seq))
    assert cf.TYPE_CHECKS["flow_dense"](L.vol_flow_3d(seq[0], seq[1]))


def test_no_typed_bridge_is_built_for_the_video_op():
    import ops

    names = {o.name for o in ops.REGISTRY}
    assert "tb_video_interpolate_flow" not in names
    assert not any(n.startswith("tb_volseq") for n in names)


def test_op_run_works_for_every_op():
    import fullseye as fs

    run = lambda *a, **k: fs.op_run(*a, **k)[0]     # noqa: E731
    s = run("volseq_synth_dividing", SHAPE, n_frames=4, split_frame=0, speed=1.0)
    assert s.shape == (4,) + SHAPE
    assert run("volseq_synth_beating", SHAPE, n_frames=4).shape == (4,) + SHAPE
    assert run("volseq_mip_video", s).shape == (4, 24, 24)
    assert run("volseq_cut_video", s).shape == (4, 24, 24)
    assert run("vol_flow_3d", s[0], s[1]).shape == (3,) + SHAPE
    assert run("volseq_speed", s).shape == (3,) + SHAPE
    assert run("volseq_pathline_render", s, n_seeds=10, size=16).shape == (16, 16, 3)
    assert run("volseq_pathline_orbit", s, n_frames=2, n_seeds=10, size=16).shape == (2, 16, 16, 3)
    assert run("video_interpolate_flow", s.max(axis=1), factor=2).shape == (7, 24, 24)
    assert run("volseq_interpolate_flow", s, factor=2).shape == (7,) + SHAPE
    assert run("volseq_magnify_motion", s, alpha=2.0, f_lo=0.1, f_hi=0.3, fps=1.0).shape == (4,) + SHAPE
    assert run("volseq_render_orbit", s, n_frames=2, size=16, depth_samples=8).shape == (2, 16, 16, 3)
    assert run("focus_sweep_height_video", s, window=3).shape == (4, 24, 24)
    assert run("focus_sweep_surface_video", s, window=3).shape == (4, 24, 24, 3)


def test_the_family_guide_exists_and_names_its_ops():
    p = ROOT / "docs" / "ops" / "live4d" / "guides" / "live4d.md"
    assert p.exists()
    md = p.read_text(encoding="utf-8")
    assert "```mermaid" in md and "vol_flow_3d" in md and "volseq_magnify_motion" in md and "volseq_render_orbit" in md
    assert os.path.isdir(ROOT / "docs" / "ops" / "live4d")
