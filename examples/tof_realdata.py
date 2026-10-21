"""Read-only adapters and quantitative comparisons for local iToF datasets.

No frame is copied into the repository.  The source READMEs do not grant an
explicit redistribution licence, so public figures use curves and aggregate
numbers only.
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

C = 299_792_458.0
#: 実データの置き場は環境変数でだけ受ける(配布物に手元のパスを書かない)。未設定なら None で、読み口はすべて None を返す。
_ENV_ROOT = os.environ.get("FULLSEYE_ITOF_DATA", "").strip()
DATA_ROOT = Path(_ENV_ROOT) if _ENV_ROOT else None


def _h5py():
    try:
        import h5py
    except ImportError:
        return None
    return h5py


def unpack_11bit(raw, frames=10, height=424, width=512):
    """Unpack little-endian 11-bit samples from a raw phase-frame dump."""
    data = np.asarray(raw).view(np.uint8)
    bits = np.unpackbits(data, bitorder="little")
    need = frames * height * width * 11
    if bits.size < need:
        raise ValueError("raw phase dump is shorter than its declared grid")
    bits = bits[:need].reshape(frames, height, width, 11)
    return np.sum(bits.astype(np.uint16) * (1 << np.arange(11, dtype=np.uint16)), axis=-1)


def read_raw_phase_frame(index=0):
    """Read ten packed raw phase images from the ECCV 2016 HDF5 log."""
    h5py = _h5py()
    if DATA_ROOT is None:  # 実データの置き場が未設定なら「無い」と同じ扱い
        return None
    path = DATA_ROOT / "liu_kinect2_kde" / "library.h5"
    if h5py is None or not path.exists():
        return None
    with h5py.File(path, "r") as f:
        return unpack_11bit(f[f"Frame_{index}/Ir"][:])


def read_wall_capture(path=None):
    """Read amplitude, phase, and ten repeats from a wall/mesh capture."""
    h5py = _h5py()
    if DATA_ROOT is None:  # 実データの置き場が未設定なら「無い」と同じ扱い
        return None
    folder = DATA_ROOT / "zhaw_mpi_mesh" / "20221207_Mesh2m"
    files = sorted(folder.glob("*wall*.h5"))
    if h5py is None or not files:
        return None
    path = Path(path) if path else files[0]
    with h5py.File(path, "r") as f:
        return {key: np.asarray(f[key]) for key in ("amplitude", "phase", "rawamp", "rawphase", "f_led")}


def amplitude_spread_statistics(synthetic_amplitude):
    """Wasserstein gate against real scenes, normalized by each median."""
    from scipy.stats import wasserstein_distance
    h5py = _h5py()
    if DATA_ROOT is None:  # 実データの置き場が未設定なら「無い」と同じ扱い
        return None
    folder = DATA_ROOT / "zhaw_mpi_mesh" / "20221207_Mesh2m"
    files = sorted(folder.glob("*.h5"))
    if h5py is None or len(files) < 2:
        return None
    distributions = []
    for path in files:
        with h5py.File(path, "r") as f:
            values = np.asarray(f["amplitude"][:, :, 5], float)
        values = values[values > 10]
        distributions.append(np.clip(values / np.median(values), 0, 8))
    real_spread = max(wasserstein_distance(a, b) for i, a in enumerate(distributions) for b in distributions[i + 1:])
    syn = np.asarray(synthetic_amplitude, float)
    syn = np.clip((syn / np.median(syn)).ravel(), 0, 8)
    syn_real = min(wasserstein_distance(syn, real) for real in distributions)
    return {"synthetic_real_w1": float(syn_real), "real_real_w1": float(real_spread),
            "threshold": float(1.5 * real_spread)}


def _log_slope(amplitude, sigma, bins=12):
    amp = np.asarray(amplitude, float).ravel()
    sig = np.asarray(sigma, float).ravel()
    valid = (amp > 0) & (sig > 0) & np.isfinite(amp) & np.isfinite(sig)
    amp, sig = amp[valid], sig[valid]
    edges = np.quantile(amp, np.linspace(.1, .9, bins + 1))
    aa, ss = [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        take = (amp >= lo) & (amp < hi)
        if take.sum() > 20:
            aa.append(np.median(amp[take])); ss.append(np.median(sig[take]))
    return float(np.polyfit(np.log(aa), np.log(ss), 1)[0]), np.asarray(aa), np.asarray(ss)


def noise_exponents(synthetic_frames):
    """Fit depth standard deviation versus amplitude on real and synthetic flats."""
    real = read_wall_capture()
    if real is None:
        return None
    k = 12
    freq = float(real["f_led"][k])
    phase = real["rawphase"][:, :, k, :].astype(float) * (2 * np.pi / 30000.0)
    # Circular residual avoids the 0/2pi seam.
    residual = np.angle(np.exp(1j * (phase - np.angle(np.mean(np.exp(1j * phase), axis=-1))[..., None])))
    depth_std = np.std(residual, axis=-1) * C / (4 * np.pi * freq)
    real_exp, real_a, real_s = _log_slope(np.median(real["rawamp"][:, :, k, :], axis=-1), depth_std)
    depths = np.stack([f["depth"] for f in synthetic_frames])
    syn_std = np.std(depths, axis=0)
    syn_amp = np.median(np.stack([f["amplitude"] for f in synthetic_frames]), axis=0)
    syn_exp, syn_a, syn_s = _log_slope(syn_amp, syn_std)
    return {"real_exponent": real_exp, "synthetic_exponent": syn_exp,
            "real_curve": (real_a, real_s), "synthetic_curve": (syn_a, syn_s)}


def wall_corner_bias_mm():
    """Estimate near-junction bias relative to the central wall in real captures."""
    real = read_wall_capture()
    if real is None:
        return None
    k = 5
    depth = real["phase"][:, :, k].astype(float) / 30000 * C / (2 * float(real["f_led"][k]))
    # The mesh/wall junction is the strongest vertical phase gradient; compare
    # a 5-pixel strip at it with a central wall patch on the same rows.
    grad = np.nanmedian(np.abs(np.diff(depth, axis=0)), axis=1)
    edge = int(np.argmax(grad[20:-20]) + 20)
    rows = slice(60, 180)
    near = np.nanmedian(depth[edge - 2:edge + 3, rows])
    wall = np.nanmedian(depth[-45:-20, rows])
    return float(1000 * (near - wall))


def flying_pixel_fractions(synthetic_depth, synthetic_truth):
    """Compare the fraction of geometric edge pixels flagged by the public op."""
    import itof
    real = read_wall_capture()
    if real is None:
        return None
    k = 12
    real_depth = real["phase"][:, :, k].astype(float) / 30000 * C / (2 * float(real["f_led"][k]))
    threshold = .20
    real_edge = np.hypot(*np.gradient(real_depth)) > threshold
    syn_edge = np.hypot(*np.gradient(synthetic_truth)) > threshold
    real_mask = itof.itof_flying_pixel_mask(real_depth, threshold_m=threshold, radius=1).astype(bool)
    syn_mask = itof.itof_flying_pixel_mask(synthetic_depth, threshold_m=threshold, radius=1).astype(bool)
    return {"real_fraction": float(real_mask[real_edge].mean()),
            "synthetic_fraction": float(syn_mask[syn_edge].mean())}


def read_rgbe(path):
    """Minimal Radiance RGBE reader supporting modern scanline RLE."""
    path = Path(path)
    with path.open("rb") as stream:
        while stream.readline().strip():
            pass
        tokens = stream.readline().decode("ascii").split()
        height, width = int(tokens[1]), int(tokens[3])
        out = np.empty((height, width, 4), np.uint8)
        for y in range(height):
            head = stream.read(4)
            if len(head) != 4 or head[:2] != b"\x02\x02":
                raise ValueError("unsupported old RGBE scanline")
            if (head[2] << 8 | head[3]) != width:
                raise ValueError("RGBE scanline width mismatch")
            for channel in range(4):
                x = 0
                while x < width:
                    count = stream.read(1)[0]
                    if count > 128:
                        run = count - 128
                        out[y, x:x + run, channel] = stream.read(1)[0]
                    else:
                        run = count
                        out[y, x:x + run, channel] = np.frombuffer(stream.read(run), np.uint8)
                    x += run
    exponent = out[..., 3].astype(np.int16)
    scale = np.where(exponent > 0, np.ldexp(1.0, exponent - (128 + 8)), 0.0)
    return out[..., :3].astype(float) * scale[..., None]


def rendered_mpi_statistic():
    """Decode a rendered four-phase frame and compare it with ground truth."""
    if DATA_ROOT is None:  # 実データの置き場が未設定なら「無い」と同じ扱い
        return None
    folder = DATA_ROOT / "radu_cornellbox"
    paths = [folder / f"000_render_20MHz_phase{k}.hdr" for k in range(4)]
    truth_path = folder / "000_render_depth.hdr"
    if not truth_path.exists() or not all(p.exists() for p in paths):
        return None
    corr = np.stack([read_rgbe(p)[..., 0] for p in paths])
    phasor = (corr[0] - corr[2]) + 1j * (corr[3] - corr[1])
    decoded = np.mod(np.angle(phasor), 2*np.pi) * C / (4*np.pi*20e6)
    truth = read_rgbe(truth_path)[..., 0]
    valid = np.isfinite(truth) & (truth > 0) & (truth < 7.4)
    error = decoded[valid] - truth[valid]
    return {"median_error_mm": float(1000*np.median(error)),
            "corner_sign": float(np.sign(np.median(error[np.abs(error) > np.quantile(np.abs(error), .9)])))}
