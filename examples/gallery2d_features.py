# -*- coding: utf-8 -*-
"""gallery2d_features — 特徴抽出/テクスチャ/形状記述/自己相似/分類オペレータ一家の作品集 (task: feature_gallery)

    py -3.11 examples/gallery2d_features.py

【平たく言うと(この一家は何のためのものか)】
画像・領域(region)・輪郭(XLD contour)・ボリューム・カラー画像を入力に取り、
「何個あるか」「どれだけ丸いか」「どれだけざらついているか」「明るさの平均・分散・
エントロピー」「モーメント不変量」「自己相似マップ」「ハフ変換の投票空間」といった
“数えて測る/形を言い当てる” 系のオペレータを一括で扱う。HALCON の
count_obj / circularity / moments_region_* / *_xld / gray feature 群と、
scikit-image・OpenCV・mahotas・PyWavelets 由来の blob/コーナー/ウェーブレット記述子を
同じ registry に載せた、Fullseye の「計測・分類」レイヤ一式である。

【グラウンドトゥルース(GT で嘘を弾く)】
1. 一家の全 op(下記 OPS)を実際に呼び、出力が
     - 有限(NaN/Inf 無し)、
     - 宣言 out_sort と一致(image → 2-D float 配列、feature → 有限スカラ/配列、
       contour → dict{'cs','shape'})、
     - 決定的(同じ入力なら bit 単位で同一)
   であることを 1 件ずつ assert する。例外を投げた op は握り潰さず即座に FAIL。
2. さらに効果が既知の代表 op には “beat-the-null”(零点を上回る)強い GT を課す:
     - 3 個に分かれた領域は count_obj / blob_count = ちょうど 3、
     - 円盤領域の circularity は細長い棒の circularity より桁違いに大きい、
     - intensity(平均)は明画像 > 暗画像、定数画像では厳密に一致、
     - entropy_gray / estimate_noise はノイズ画像 > 平坦画像、
     - count_channels(カラー)= 3、
     - 完全な円の総周長 total_length ≈ 2πR、円の circularity_xld ≈ 1 > 正方形。
3. OPS の集合は registry のカテゴリ集合と厳密一致することを assert(将来 op を
   足したらこの例が落ちて更新を促す)。

輪郭は dict{'shape':(H,W), 'cs':[ (N,2) 配列 ... ]}。region は {0,1} の 2-D float、
image は [0,1] の 2-D float、color は HxWx3、volume は Zx(H)x(W) の [0,1]。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import ops  # noqa: E402

# --------------------------------------------------------------------------- #
# TARGET: this feature/texture/shape/self-similarity/classification op family. #
# Written as explicit string literals so each op name is greppable for the     #
# op -> example index. Verified below to equal the registry's category set.    #
# --------------------------------------------------------------------------- #
CATS = ["features", "texture-feature", "texture/shape-feature",
        "self-similarity", "classification"]

OPS = [
    "blob_count", "area_frac", "count_contours", "total_length", "classify_shape",
    "vol_count", "sk_euler", "sk_entropy_feat", "sk_blur_effect", "cv_cc_count",
    "cv_hough_lines", "cv_hough_circles", "cv_good_features", "area_center", "count_obj",
    "circularity", "compactness", "convexity", "rectangularity", "eccentricity",
    "orientation_region", "roundness", "diameter_region", "euler_number", "min_max_gray",
    "intensity", "gray_histo_abs", "entropy_gray", "length_xld", "contlength",
    "area_holes", "height_width_ratio", "moments_region_2nd", "moments_region_2nd_invar",
    "area_center_xld", "circularity_xld", "compactness_xld", "convexity_xld",
    "moments_region_3rd", "moments_region_central", "moments_region_central_invar",
    "moments_region_2nd_rel_invar", "moments_region_3rd_invar", "estimate_noise",
    "eccentricity_xld", "orientation_xld", "elliptic_axis_xld", "diameter_xld",
    "rectangularity_xld", "moments_xld", "hough_line_trans", "hough_circle_trans",
    "get_region_thickness", "connect_and_holes", "elliptic_axis", "count_channels",
    "xsk_blob_log", "xsk_blob_dog", "xsk_blob_doh", "xsk_orb_count", "xcv_orb_count",
    "xcv2_lap_var", "xcv2_fast_count", "xmh_zernike", "xmh_pftas", "xmh_selfmatch",
    "xwt_detail_energy", "xwt_packet_entropy", "xsk3_is_low_contrast", "xsk3_estimate_sigma",
    "xcv3_gray_hu1", "xcv3_sift_count", "xcv3_brisk_count", "xcv3_agast_count",
    "xcv3_lsd_count",
]

BY = {o.name: o for o in ops.REGISTRY}
KNOBS = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.15, 0.85)]  # exercise both knobs at the corners


# --------------------------------------------------------------------------- #
# Per-sort valid-input factory (replicated from tests/conftest.py so examples  #
# never import from tests/). Each returns a fresh, deterministic input of the  #
# right shape/domain for an op's in_sort.                                      #
# --------------------------------------------------------------------------- #
def input_for(sort: str, n: int = 64):
    """Return a valid, non-degenerate input array/dict for the given in_sort."""
    if sort == "image":
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
        grad = xx / (n - 1)
        disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
        checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
        noise = 0.03 * np.random.default_rng(20260829).standard_normal((n, n))
        return np.clip(0.35 * grad + 0.45 * disk + checker + noise, 0, 1)
    if sort == "region":
        yy, xx = np.mgrid[0:n, 0:n]
        return (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)
    if sort == "contour":
        # a densely-sampled closed circle (>= 5 pts so ellipse-fit XLD ops are real)
        t = np.linspace(0, 2 * np.pi, 200, endpoint=False)
        c = np.column_stack([n / 2 + n * 0.28 * np.sin(t), n / 2 + n * 0.28 * np.cos(t)])
        return {"shape": (n, n), "cs": [c.astype(np.float64)]}
    if sort == "volume":
        zz, vy, vx = np.mgrid[0:8, 0:24, 0:24]
        return np.clip(0.5 + 0.3 * np.sin(vx / 3.0) * np.cos(vy / 4.0) * (zz / 8.0), 0, 1)
    if sort == "color":
        g = input_for("image", n)
        return np.clip(np.stack([g, 0.7 * g + 0.1, 1 - g], -1), 0, 1)
    raise ValueError(f"no input factory for sort {sort!r}")


def copy_input(x):
    if isinstance(x, dict):
        return {"shape": x["shape"], "cs": [c.copy() for c in x["cs"]]}
    return np.array(x, copy=True)


def _equal(x, y) -> bool:
    """Bit-identical comparison across ndarray / contour-dict / scalar outputs."""
    if isinstance(x, np.ndarray) and isinstance(y, np.ndarray):
        return x.shape == y.shape and np.array_equal(x, y, equal_nan=True)
    if isinstance(x, dict) and isinstance(y, dict):
        cs1, cs2 = x.get("cs", []), y.get("cs", [])
        return len(cs1) == len(cs2) and all(
            a.shape == b.shape and np.array_equal(a, b) for a, b in zip(cs1, cs2))
    return bool(np.all(np.asarray(x, np.float64) == np.asarray(y, np.float64)))


def check_output(name: str, out, out_sort: str) -> None:
    """Assert an op's output is finite and matches its declared out_sort."""
    if out_sort == "feature":
        f = np.asarray(out, np.float64).reshape(-1)
        assert f.size >= 1, f"{name}: feature output is empty"
        assert np.all(np.isfinite(f)), f"{name}: feature output has NaN/Inf -> {f[:4]}"
    elif out_sort in ("image", "region"):
        assert isinstance(out, np.ndarray) and out.ndim == 2, f"{name}: {out_sort} not 2-D ndarray"
        assert np.issubdtype(out.dtype, np.floating), f"{name}: {out_sort} not float dtype"
        assert np.all(np.isfinite(out)), f"{name}: {out_sort} has NaN/Inf"
        mn, mx = float(out.min()), float(out.max())
        assert -1e-6 <= mn and mx <= 1 + 1e-6, f"{name}: {out_sort} out of [0,1]: [{mn},{mx}]"
    elif out_sort == "contour":
        assert isinstance(out, dict) and "cs" in out and "shape" in out, f"{name}: bad contour dict"
        for c in out["cs"]:
            assert np.all(np.isfinite(c)), f"{name}: contour vertices have NaN/Inf"
    elif out_sort == "color":
        assert isinstance(out, np.ndarray) and out.ndim == 3 and out.shape[-1] == 3, f"{name}: bad color"
        assert np.all(np.isfinite(out)), f"{name}: color has NaN/Inf"
    else:  # volume / match / any — at least be finite where numeric
        if isinstance(out, np.ndarray):
            assert np.all(np.isfinite(out)), f"{name}: {out_sort} has NaN/Inf"


def _feat(name: str, inp, a: float = 0.5, b: float = 0.5) -> float:
    """Call a feature op and return its scalar value (first element)."""
    return float(np.asarray(BY[name].fn(copy_input(inp), a, b), np.float64).reshape(-1)[0])


# --------------------------------------------------------------------------- #
def main() -> int:
    # 0) OPS must be exactly the registry's category family — no more, no less.
    reg_family = {o.name for o in ops.REGISTRY if o.category in CATS}
    missing = reg_family - set(OPS)
    extra = set(OPS) - reg_family
    assert not missing and not extra, (
        f"OPS drifted from registry: missing={sorted(missing)} extra={sorted(extra)}")
    assert len(OPS) == len(set(OPS)) == len(reg_family), "OPS has duplicates or wrong count"

    # 1) Exercise EVERY op: finite, correctly typed, deterministic. Raises -> FAIL loudly.
    for name in OPS:
        op = BY[name]
        base = input_for(op.in_sort)
        for a, b in KNOBS:
            out = op.fn(copy_input(base), a, b)          # must not raise
            check_output(name, out, op.out_sort)
        ref = op.fn(copy_input(base), 0.5, 0.5)
        for _ in range(3):
            again = op.fn(copy_input(base), 0.5, 0.5)
            assert _equal(ref, again), f"{name}: nondeterministic (same input -> different output)"

    # 2) Strong ground-truth / beat-the-null checks on well-understood ops.
    n = 64
    yy, xx = np.mgrid[0:n, 0:n]
    gt = 0

    # (a) counting: exactly three separated blobs -> count 3 (region family)
    three = np.zeros((n, n), np.float64)
    for cy, cx in [(16, 16), (16, 48), (48, 32)]:
        three[((yy - cy) ** 2 + (xx - cx) ** 2) < 25] = 1.0
    assert _feat("count_obj", three) == 3.0, "count_obj must count 3 blobs"
    assert _feat("blob_count", three) == 3.0, "blob_count must count 3 blobs"
    gt += 1

    # (b) circularity: a disk is far rounder than a thin bar (beat-the-null)
    disk = (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.22) ** 2).astype(np.float64)
    bar = np.zeros((n, n), np.float64); bar[28:36, 6:58] = 1.0
    c_disk, c_bar = _feat("circularity", disk), _feat("circularity", bar)
    assert c_disk > 0.8 and c_disk > 2.0 * c_bar, f"disk {c_disk} vs bar {c_bar}"
    gt += 1

    # (c) intensity (mean): exact on a constant, and brighter image reads higher
    const = np.full((n, n), 0.42)
    assert abs(_feat("intensity", const) - 0.42) < 1e-6, "intensity of const 0.42 must be 0.42"
    assert _feat("intensity", np.full((n, n), 0.8)) > _feat("intensity", np.full((n, n), 0.1)) + 0.5
    gt += 1

    # (d) entropy_gray: a flat image has ~0 entropy, a noisy one much more
    rng = np.random.default_rng(1)
    noisy = np.clip(const + 0.15 * rng.standard_normal((n, n)), 0, 1)
    e_flat, e_noisy = _feat("entropy_gray", const), _feat("entropy_gray", noisy)
    assert e_flat < 1e-6 and e_noisy > e_flat + 0.3, f"entropy flat {e_flat} vs noisy {e_noisy}"
    gt += 1

    # (e) estimate_noise: 返すのは **ノイズ σ そのもの**([0,1] 階調)。
    #     2026-09-02 以前は σ の 3*1.4826*MAD 版で σ>=0.08 から 1.0 に張り付いていた
    #     ので閾値 0.3 で通っていた。いまは真値に追随する: σ=0.15 のガウス雑音を
    #     足した画像で 0.1486、平坦画像で 0.0(実測)。真値 ±20% を要求する。
    s_true = 0.15
    e_flat_n, e_noisy_n = _feat("estimate_noise", const), _feat("estimate_noise", noisy)
    assert e_flat_n < 1e-6, f"flat image must read ~0 noise, got {e_flat_n}"
    assert abs(e_noisy_n - s_true) < 0.2 * s_true, (
        f"estimate_noise must track the true sigma {s_true}: got {e_noisy_n:.4f}")
    gt += 1

    # (f) count_channels: an HxWx3 color image has exactly 3 channels
    assert _feat("count_channels", input_for("color")) == 3.0, "count_channels must be 3"
    gt += 1

    # (g) total_length: a full circle contour has perimeter ~= 2*pi*R (shape family)
    R = n * 0.28
    circ = input_for("contour")
    L = _feat("total_length", circ)
    assert abs(L - 2 * np.pi * R) < 0.02 * (2 * np.pi * R), f"circle length {L} vs 2piR {2*np.pi*R}"
    gt += 1

    # (h) circularity_xld: a circle contour is maximally circular; a square is lower
    t = np.linspace(0, 2 * np.pi, 200, endpoint=False)
    half = n * 0.28
    edge = np.linspace(-half, half, 60)
    sq = np.vstack([
        np.column_stack([np.full(60, n / 2 - half), n / 2 + edge]),
        np.column_stack([n / 2 + edge, np.full(60, n / 2 + half)]),
        np.column_stack([np.full(60, n / 2 + half), n / 2 - edge]),
        np.column_stack([n / 2 - edge, np.full(60, n / 2 - half)]),
    ]).astype(np.float64)
    sq_c = {"shape": (n, n), "cs": [sq]}
    circ_c = {"shape": (n, n),
              "cs": [np.column_stack([n / 2 + half * np.sin(t), n / 2 + half * np.cos(t)]).astype(np.float64)]}
    xc_circle, xc_square = _feat("circularity_xld", circ_c), _feat("circularity_xld", sq_c)
    assert xc_circle > 0.98 and xc_circle > xc_square + 0.1, f"circle {xc_circle} vs square {xc_square}"
    gt += 1

    print(f"PASS: {len(OPS)} ops exercised, all finite/typed/deterministic; {gt} GT checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
