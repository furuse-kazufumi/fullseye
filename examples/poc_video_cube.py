# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 動画を空間 × 時間の立方体として見る ―― 何が・どこを・いつ通ったかが 1 枚の立体に出る(Video Summagator の再実装)

Nguyen・Niu・Liu「Video Summagator」(ACM CHI 2012)は、動画 (T, H, W) を (x, y, t) の立方体にして、動かない
背景を薄く・動く物体を濃く描き、切ったり回したりして目当ての場面へ飛ぶ道具。この PoC は同じことを Fullseye の
5 op(族 ``videocube``、numpy + scipy のみ)でやり、**軌跡から読める「いつ・どこを・どちらへ」が真値と合う**ことを
数字で確かめる。

**主張は 1 つだけ**: 監視カメラ風の合成クリップ(通過の行・時刻・速度が既知の物体 3 つ)で、
``video_cube_cut(plane="xt")`` のスリットスキャンから読んだ通過時刻と速度(筋の位置と傾き)が真値に合い、
``video_summary_keyframes`` が各物体の出現の直後を代表フレームに選ぶ。乱数のフレーム選びは選ばない。

図:
1. ``cube_time_coloured``: 立方体を斜めから(軌跡は時刻の色: 青 = 始め → 赤 = 終わり、背景は薄い灰)。
2. ``cube_orbit``: 立方体を回す GIF。
3. ``slit_scans``: 3 つの行のスリットスキャン(x–t)と、真値の通過時刻・速度の重ね書き。
4. ``keyframes``: 代表フレーム 4 枚と、正面(t を奥行きに)から見た立方体。
5. 実クリップ: repo 内の回転台の GIF(``examples_3d/_gallery/showcase_turntable_pod.gif``、imageio で読める場合)
   を同じ経路に通す —— 回る物体は立方体の中でらせんになる。
6. ``em_stack_cube``: ハエの脳の EM 連続断面(手元の CREMI sample A、無ければ合成の細胞断面)を**同じ op**で
   立方体にする(``mode="dark"``: 膜 = 暗い所を不透明に)。先頭軸を時刻でなく奥行きと読むだけで、断面の
   切り直し(x–z)も回転も同じ道具で動く。回転の GIF は ``video_write_gif`` でも書き出す(使い回しの出口)。

走らせ方: ``py -3.11 examples/poc_video_cube.py``(図は ``out/figures/poc_video_cube/``)。Studio では
Tools ▸ Video cube が同じ部品で対話的に動く(ドラッグで回転、断面のスライダ、断面をクリックでそのフレームへ)。
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import fullseye as fs  # noqa: E402
import examplefig as figs  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET", "reduced" if os.environ.get("CI") else "full") == "reduced"
T, H, W = (40, 72, 96) if REDUCED else (64, 120, 160)
#: 真値: (行, 出現フレーム, 速度 px/frame(正 = 右へ), 半径)
OBJECTS = [(int(H * 0.25), int(T * 0.10), 2.0, 5), (int(H * 0.55), int(T * 0.40), -1.5, 6), (int(H * 0.80), int(T * 0.65), 1.0, 4)]
GALLERY_GIF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "examples_3d", "_gallery", "showcase_turntable_pod.gif")


def surveillance_clip(seed: int = 0) -> np.ndarray:
    """静止した背景(縞と斑)の上を 3 つの物体が既知の行・時刻・速度で横切る + センサ雑音。"""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W]
    bg = 0.45 + 0.08 * np.sin(xx / 7.0) * np.cos(yy / 9.0) + 0.05 * rng.random((H, W))
    out = np.empty((T, H, W))
    for t in range(T):
        f = bg.copy()
        for row, t0, vx, r in OBJECTS:
            if t >= t0:
                x = (W - 1 - 4 if vx < 0 else 4) + (t - t0) * vx
                f[np.hypot(yy - row, xx - x) < r] = 0.95 if vx > 0 else 0.05
        out[t] = f + 0.015 * rng.standard_normal((H, W))
    return np.clip(out, 0.0, 1.0)


def em_stack():
    """ハエの脳の EM 断面のスタック(手元の CREMI sample A、無ければ合成の細胞断面)。生データは commit しない。"""
    path = os.environ.get("FULLSEYE_CREMI") or os.path.join(
        os.environ.get("FULLSEYE_DATA_DIR", os.path.join(os.path.expanduser("~"), ".cache", "fullseye")),
        "cremi", "sample_A_20160501.hdf")
    if not REDUCED and os.path.isfile(path):
        try:
            import h5py
            with h5py.File(path, "r") as f:
                raw = f["volumes/raw"][40:72, 300:556, 300:556].astype(np.float64) / 255.0
            return raw, "CREMI sample A, 32 sections of 256^2 (adult Drosophila FAFB)", 4
        except ImportError:
            pass
    rng = np.random.default_rng(1)
    Z, S = 16, 96
    seeds = rng.random((14, 2)) * S
    drift = rng.normal(size=(14, 2)) * 1.2
    yy, xx = np.mgrid[0:S, 0:S]
    out = np.empty((Z, S, S))
    for z in range(Z):
        s = seeds + drift * z
        lab = np.argmin((yy[..., None] - s[:, 0]) ** 2 + (xx[..., None] - s[:, 1]) ** 2, -1)
        edge = np.zeros((S, S), bool)
        edge[:, :-1] |= lab[:, :-1] != lab[:, 1:]
        edge[:-1, :] |= lab[:-1, :] != lab[1:, :]
        out[z] = 0.75 - 0.6 * np.clip(__import__("scipy.ndimage").ndimage.gaussian_filter(edge.astype(float), 0.8) / 0.4, 0, 1) \
            + 0.04 * rng.standard_normal((S, S))
    return np.clip(out, 0, 1), "synthetic cell sections (%d x %d^2)" % (Z, S), 2


def read_from_slits(clip: np.ndarray) -> list[dict]:
    """スリットスキャンから「いつ現れて、どちらへ、どの速さで」を読む(筋の最初の列と傾き)。"""
    L = fs.ledger
    found = []
    for row, t0, vx, r in OBJECTS:
        xt = L.video_cube_cut(clip, "xt", position=row / (H - 1))
        dev = np.abs(xt - np.median(xt, axis=0, keepdims=True))            # 背景(時間の中央値)からのずれ
        present = dev.max(axis=1) > 0.25
        ts = np.nonzero(present)[0]
        if len(ts) < 3:
            found.append({"row": row, "t_first": None, "speed": None})
            continue
        # 筋の中心 = 背景からずれた画素の重心(argmax は平坦な円盤の中で暴れる)。縁に掛かるフレームは外す
        xs = np.arange(W, dtype=np.float64)
        cent, tt = [], []
        for t in ts:
            m = dev[t] > 0.25
            c = float((xs[m] * dev[t][m]).sum() / dev[t][m].sum())
            if r + 1 <= c <= W - 2 - r:
                cent.append(c)
                tt.append(int(t))
        if len(cent) < 3:
            found.append({"row": row, "t_first": int(ts[0]), "speed": None})
            continue
        slope = float(np.polyfit(np.array(tt), np.array(cent), 1)[0])
        found.append({"row": row, "t_first": int(ts[0]), "speed": slope})
    return found


def main() -> int:
    t0 = time.time()
    L = fs.ledger
    clip = surveillance_clip()
    print("DATA: synthetic surveillance clip (T, H, W) = %s, %d objects with known row / onset / speed" % ((T, H, W), len(OBJECTS)))
    read = read_from_slits(clip)
    for (row, t_on, vx, r), got in zip(OBJECTS, read):
        print("row %3d  truth: onset t=%2d speed %+.2f   read from x-t slit: onset t=%s speed %s" % (
            row, t_on, vx, got["t_first"], "%+.2f" % got["speed"] if got["speed"] is not None else "-"))
        assert got["t_first"] is not None and abs(got["t_first"] - t_on) <= 1, (row, got)
        assert abs(got["speed"] - vx) < 0.25 * abs(vx) + 0.1, (row, got)
    k = len(OBJECTS) + 1
    idx = L.video_summary_keyframes(clip, k=k)
    hit = [any(t_on <= int(i) <= t_on + 3 for i in idx) for _row, t_on, _vx, _r in OBJECTS]
    rng = np.random.default_rng(0)
    rand_hits = np.mean([np.mean([any(t_on <= int(i) <= t_on + 3 for i in rng.choice(T, k, replace=False)) for _r, t_on, _v, _rr in OBJECTS])
                         for _ in range(200)])
    print("keyframes %s  -> onsets caught %d / %d (random choice of %d frames catches %.2f on average)" % (idx.tolist(), sum(hit), len(hit), k, rand_hits))
    assert sum(hit) == len(OBJECTS), (idx, OBJECTS)
    assert rand_hits < 0.6

    if figs.enabled():
        A = L.video_spacetime_cube(clip)
        C = L.video_spacetime_cube(clip, "intensity")
        size = 300 if REDUCED else 400
        figs.save("cube_time_coloured", L.vol_render_transfer(A, yaw=35.0, pitch=22.0, size=size, static_alpha=0.12, depth_samples=96),
                  caption="the clip as a space-time cube (time = depth to the right): moving objects leave trails coloured by time (blue = start, red = end); the static background is a faint grey")
        orbit = L.video_cube_orbit(clip, n_frames=18 if REDUCED else 30, size=size, static_alpha=0.12, depth_samples=80)
        figs.save_gif("cube_orbit", orbit, fps=10.0,
                      caption="the same cube rotating: three objects, three trails, direction and timing readable from colour and slope")
        # 使い回しの出口: 同じ回転を video_write_gif でファイルに(figures と同じ場所、展示の手順を op だけで再現できる)
        try:
            gif_path = L.video_write_gif(orbit, str(figs.target_dir() / "cube_orbit_by_op.gif"), fps=10.0)
            print("GIF: video_write_gif ->", os.path.basename(gif_path))
        except ImportError as e:                                              # Pillow が無い環境
            print("GIF: skipped (%s)" % e)
        panels, caps = [], []
        for (row, t_on, vx, r), got in zip(OBJECTS, read):
            xt = L.video_cube_cut(clip, "xt", position=row / (H - 1))
            rgb = np.repeat(np.clip(xt, 0, 1)[..., None], 3, axis=-1)
            rgb[t_on, :] = np.maximum(rgb[t_on, :], np.array([1.0, 0.85, 0.2]) * 0.9)   # 真値の出現時刻(黄の横線)
            panels.append(rgb)
            caps.append("row %d slit scan (x-t): truth onset t=%d, speed %+.1f px/frame; read t=%s, %+.2f" % (row, t_on, vx, got["t_first"], got["speed"]))
        figs.save_grid("slit_scans", panels, captions=caps, ncols=3,
                       caption="x-t slit scans of the three rows: a streak's first row is the onset, its slope is the speed (yellow line = injected onset)")
        front = L.vol_render_transfer(A, C, yaw=0.0, pitch=0.0, size=size, static_alpha=0.5)
        figs.save_grid("keyframes", [clip[int(i)] for i in idx] + [front],
                       captions=["keyframe t=%d" % int(i) for i in idx] + ["cube seen head-on (all trails at once)"], ncols=3,
                       gray=[True] * len(idx) + [False],
                       caption="video_summary_keyframes picks the frames right after each object appears; the head-on cube is the whole clip in one image")
        # 実クリップ: 回転台の GIF(repo 内)
        try:
            import imageio.v3 as iio
            frames = iio.imread(os.path.abspath(GALLERY_GIF))
            g = frames[..., :3].mean(axis=-1) / 255.0 if frames.ndim == 4 else frames.astype(np.float64) / 255.0
            step = max(1, g.shape[1] // 160)
            g = g[:64, ::step, ::step]
            Ag = L.video_spacetime_cube(g, sigma=1.0)
            figs.save("turntable_cube", L.vol_render_transfer(Ag, yaw=40.0, pitch=20.0, size=size, static_alpha=0.1),
                      caption="a real clip from this repo (a turntable GIF, %d frames of %dx%d): a rotating object becomes a helix in the space-time cube" % g.shape)
            print("REAL: %s -> %s" % (os.path.basename(GALLERY_GIF), g.shape))
        except Exception as e:                                                # noqa: BLE001
            print("REAL: gallery gif skipped (%s)" % e)
        # ハエの脳の断面を積む: 同じ op で z スタック(EM の連続断面、膜 = 暗い)を立方体として見る
        stack, src, zstretch = em_stack()
        thick = np.repeat(stack, zstretch, axis=0)                              # z は xy より粗い(CREMI は 10 倍)→ 絵では伸ばす
        Ad = L.video_spacetime_cube(thick, "dark", sigma=1.0, floor=0.5)
        figs.save_grid("em_stack_cube",
                       [L.vol_render_transfer(Ad, None, yaw=20.0, pitch=15.0, size=size, alpha_gain=0.25, depth_samples=96),
                        L.video_cube_cut(stack, "xy", 0.5), np.repeat(L.video_cube_cut(stack, "xt", 0.5), zstretch, axis=0)],
                       captions=["sections stacked as a cube: membranes opaque, coloured by depth (blue = first section, red = last)",
                                 "one section (x-y)", "re-slice across the stack (x-z, z stretched %dx)" % zstretch],
                       gray=[False, True, True], ncols=3,
                       caption="the same cube operators on a z-stack of EM sections (%s): membranes become tubes running through the stack, and the x-z re-slice shows neurites crossing the sections" % src)
        if not REDUCED:
            em_orbit = L.video_cube_orbit(thick, n_frames=24, size=size, mode="dark", color="time", static_alpha=0.0,
                                          alpha_gain=0.25, depth_samples=80, floor=0.5, pitch=15.0)
            figs.save_gif("em_stack_orbit", em_orbit, fps=8.0,
                          caption="the EM stack rotating: neurites are the tubes, coloured by depth; the same operator that rotated the surveillance clip")
        print("EM: %s -> %s" % (src, stack.shape))
        assert not figs.errors(), figs.errors()
    print("elapsed %.0fs" % (time.time() - t0))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
