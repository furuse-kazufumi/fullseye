"""Perception on a real clip: video -> optical flow -> motion energy / events ->
global-motion removal -> moving-region segmentation -> multi-frame point tracking.

Unlike ``motion_analysis.py`` (synthetic pair, known ground truth) this runs the
v14 perception stack on an *actual rendered clip* — an onocollo physics video, an
evis / hillco motion capture, a driving rollout — and reports **honest measured**
results. Real footage has no ground-truth flow, so correctness is judged by a
*photometric self-consistency* check: warp ``prev`` by the estimated flow and see
how much closer it gets to ``nxt`` than the raw frame difference
(``recon_gain = 1 - mean|nxt - warp(prev)| / mean|nxt - prev|``; > 0 means the
flow explains real motion).

    py -3.11 examples/perception_on_video.py <clip.mp4|clip.gif> [--save out_dir]
                                             [--max-frames N] [--step K]

With no clip it runs on a synthetic moving-blob sequence (so the example is
self-testing with no external files).
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import fullseye as fs


# --------------------------------------------------------------------------- #
# synthetic fallback clip (a blob that translates, with two speed bursts)
# --------------------------------------------------------------------------- #
def synthetic_clip(t=16, h=96, w=128, seed=0):
    rng = np.random.default_rng(seed)
    base = np.clip(ndimage.gaussian_filter(rng.random((h, w)), 1.3), 0, 1)
    yy, xx = np.mgrid[0:h, 0:w]
    frames = []
    cx, cy = 24.0, 48.0
    for i in range(t):
        speed = 6.0 if i in (5, 6, 11, 12) else 1.5   # two bursts -> two events
        cx += speed
        blob = 0.8 * np.exp(-((yy - cy) ** 2 + (xx - cx) ** 2) / (2 * 7.0 ** 2))
        frames.append(np.clip(base + blob, 0, 1))
    return np.stack(frames)


# --------------------------------------------------------------------------- #
# core analysis — takes frames (T, H, W) in [0, 1], returns measured results
# --------------------------------------------------------------------------- #
def analyze(frames, flow_kwargs=None, event_k=2.0, track_grid=6, save_dir=None):
    frames = np.asarray(frames, np.float64)
    T = len(frames)
    if T < 2:
        raise ValueError("need at least 2 frames")
    fk = dict(window=15, levels=3, iters=5)
    if flow_kwargs:
        fk.update(flow_kwargs)

    # 1) motion energy across the clip + event peaks
    energy = fs.motion_energy_series(frames, **fk)
    events = fs.detect_events(energy, k=event_k)
    peak = int(np.argmax(energy)) if energy.size else 0

    # 2) flow on the peak-motion pair + photometric self-consistency
    a, b = frames[peak], frames[peak + 1]
    u, v = fs.optical_flow_lk(a, b, **fk)
    warped = fs.warp_by_flow(a, u, v)
    base_err = float(np.mean(np.abs(b - a)))
    warp_err = float(np.mean(np.abs(b - warped)))
    recon_gain = (1.0 - warp_err / base_err) if base_err > 1e-9 else 0.0

    # 3) global (camera) motion + independent movers
    M = fs.dominant_motion(u, v)
    global_uv = (float(M[0, 0]), float(M[1, 0]))
    ru, rv = fs.residual_motion(u, v, model=M)
    rmag = fs.flow_magnitude(ru, rv)
    thr = max(1.0, float(np.nanmean(rmag) + 2.0 * np.nanstd(rmag)))
    mask, segs = fs.motion_segments(u, v, threshold=thr, min_area=max(20, a.size // 400))

    # 4) multi-frame sparse tracking over a window around the peak
    lo = max(0, peak - 4)
    hi = min(T - 1, peak + 4)
    H, W = a.shape
    gy = np.linspace(H * 0.15, H * 0.85, track_grid)
    gx = np.linspace(W * 0.15, W * 0.85, track_grid)
    pts0 = np.array([[x, y] for y in gy for x in gx], np.float64)   # (N, 2) as (x, y)
    pts = pts0.copy()
    alive = np.ones(len(pts), bool)
    for i in range(lo, hi):
        nxt, ok = fs.track_points(frames[i], frames[i + 1], pts, **fk)
        alive &= ok
        pts = nxt
    disp = np.linalg.norm(pts - pts0, axis=1)
    n_alive = int(alive.sum())
    mean_path = float(disp[alive].mean()) if n_alive else 0.0

    result = {
        "n_frames": T,
        "energy_mean": round(float(energy.mean()), 4) if energy.size else 0.0,
        "energy_max": round(float(energy.max()), 4) if energy.size else 0.0,
        "peak_pair": peak,
        "n_events": int(events.size),
        "event_pairs": events.tolist(),
        "recon_gain": round(recon_gain, 4),
        "global_translation_px": (round(global_uv[0], 3), round(global_uv[1], 3)),
        "n_moving_segments": len(segs),
        "largest_segment_area": segs[0]["area"] if segs else 0,
        "tracked_points": len(pts0),
        "tracked_survived": n_alive,
        "mean_track_path_px": round(mean_path, 3),
        "track_window": (lo, hi),
    }

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        fs.save(os.path.join(save_dir, "flow_peak.png"), fs.colorize_flow(u, v))
        fs.save(os.path.join(save_dir, "residual_peak.png"), fs.colorize_flow(ru, rv))
        fs.save(os.path.join(save_dir, "moving_mask.png"), mask.astype(float))
        _save_energy(energy, events, os.path.join(save_dir, "energy.csv"),
                     os.path.join(save_dir, "energy.png"))
        _save_tracks(frames[hi], pts0, pts, alive,
                     os.path.join(save_dir, "tracks.png"))
        print(f"[perception] wrote flow/residual/mask/energy/tracks -> {save_dir}")

    return result


def _save_energy(energy, events, csv_path, png_path):
    with open(csv_path, "w", encoding="ascii") as f:
        f.write("frame_pair,motion_energy,is_event\n")
        ev = set(int(e) for e in events)
        for i, e in enumerate(energy):
            f.write("%d,%.6f,%d\n" % (i, e, 1 if i in ev else 0))
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(7, 3))
        ax.plot(energy, "-o", ms=3, lw=1, label="motion energy")
        if len(events):
            ax.plot(events, energy[events], "rx", ms=9, label="event")
        ax.set_xlabel("frame pair")
        ax.set_ylabel("RMS speed (px)")
        ax.legend()
        fig.tight_layout()
        fig.savefig(png_path, dpi=110)
        plt.close(fig)
    except Exception:
        pass   # matplotlib optional; the CSV is always written


def _save_tracks(frame, pts0, pts1, alive, png_path):
    """Overlay start (blue) -> end (green) point tracks on a frame."""
    rgb = np.repeat(np.asarray(frame, np.float64)[:, :, None], 3, axis=2).copy()
    H, W = frame.shape

    def _dot(img, x, y, color, r=2):
        xi, yi = int(round(x)), int(round(y))
        y0, y1 = max(0, yi - r), min(H, yi + r + 1)
        x0, x1 = max(0, xi - r), min(W, xi + r + 1)
        if y1 > y0 and x1 > x0:
            img[y0:y1, x0:x1] = color

    for (x0, y0), (x1, y1), ok in zip(pts0, pts1, alive):
        if not ok:
            continue
        _dot(rgb, x0, y0, (0.1, 0.3, 1.0))       # start = blue
        _dot(rgb, x1, y1, (0.1, 1.0, 0.2))       # end   = green
    fs.save(png_path, np.clip(rgb, 0, 1))


# --------------------------------------------------------------------------- #
def run(clip_path=None, save_dir=None, max_frames=None, step=1):
    if clip_path:
        frames = fs.read_frames(clip_path, gray=True, step=step, max_frames=max_frames)
        meta = fs.video.probe(clip_path)
        print(f"[perception] {os.path.basename(clip_path)}  "
              f"frames={len(frames)} size={frames.shape[2]}x{frames.shape[1]} "
              f"fps={meta.get('fps')}")
    else:
        frames = synthetic_clip()
        print(f"[perception] synthetic clip  frames={len(frames)} "
              f"size={frames.shape[2]}x{frames.shape[1]}")
    result = analyze(frames, save_dir=save_dir)
    print("[perception] " + "  ".join(f"{k}={v}" for k, v in result.items()))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("clip", nargs="?", default=None, help="path to an mp4/gif clip")
    ap.add_argument("--save", default=None, help="directory to write visual outputs")
    ap.add_argument("--max-frames", type=int, default=None)
    ap.add_argument("--step", type=int, default=1)
    a = ap.parse_args()
    run(clip_path=a.clip, save_dir=a.save, max_frames=a.max_frames, step=a.step)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
