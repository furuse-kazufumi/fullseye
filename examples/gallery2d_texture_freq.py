# -*- coding: utf-8 -*-
"""gallery2d_texture_freq — テクスチャ/周波数/分解オペレータ一族の総なめギャラリー (contract-verify task)。

    py -3.11 examples/gallery2d_texture_freq.py

【平たく言うと(この一族は何のためのものか)】
このギャラリーは Fullseye の 2-D オペレータ登録簿(ops.REGISTRY)のうち、カテゴリが
"texture"(テクスチャ記述: Gabor/LBP/Laws/エントロピ/共起行列/census・rank 変換 …)、
"frequency"(周波数領域: FFT パワー・位相スペクトル、ローパス/ハイパス/バンドパス、
DCT、Hilbert 包絡 …)、"decomposition"(構造+テクスチャ分解、RPCA 低ランク/疎、Retinex、
homomorphic、局所コントラスト正規化 …)に属する **すべて** のオペを 1 本で走らせる。
用途は画像の「模様・周期・照明/反射の分離」を測る前処理群で、進化パイプラインの部品になる。

【グラウンドトゥルース(GT: 嘘を数値で弾く)】
まず一族の全オペに対する普遍契約を検査する:
  (1) 例外なく走る  (2) 出力は有限(退化入力=定数/微小でも NaN/Inf を出さない)
  (3) 宣言した out_sort と一致(image → 2-D float 配列 / feature → 有限スカラ・配列)
  (4) 決定的(同じ入力 → ビット一致。進化の holdout スコアリングが依存する)
※ image 出力の値域は [0,1] に限定しない — ハイパス/バンドパス/逆FFT は負値の
  ディテールを持つのが正しい(登録簿契約でも [0,1] 制約は region だけ)。ゆえに強制せず、
  代わりに下記の効果既知オペに **beat-the-null 付きの強い GT** を追加する:
  - lowpass    : 高周波エネルギ(ラプラシアン分散)が半減以下 = ぼかしが高周波を落とす
  - highpass   : ステップエッジ上のディテール応答 >> 平坦部応答(エッジ検出)
  - std_filter : 平坦部の局所標準偏差 ≈ 0、テクスチャ部で大(> 0.1)
  - rank_transform : 正のゲイン倍で出力ビット一致(順序不変=照明ゲイン頑健)、
                     コントラスト反転では変化(検査が非自明であることの裏取り)
  - entropy_image  : 定数画像はエントロピ ≈ 0、ノイズ/テクスチャで高い
  - xsp_dct_lowpass: DCT ローパスで高周波エネルギが半減以下

一族の全オペを走らせ、上記契約と GT で検証する(silent skip 無し、raise は loud fail)。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import ops  # noqa: E402


# --------------------------------------------------------------------------- #
# Valid input factory per sort — replicated from tests/conftest.py            #
# (examples must NOT import from tests/). Every op here is in_sort='image',    #
# but we cover the other sorts too so the factory is honest and reusable.     #
# --------------------------------------------------------------------------- #
def _rng():
    return np.random.default_rng(20260812)


def input_for(sort: str, n: int = 48):
    """Return one valid input value for the given in_sort (conftest 'normal' bank)."""
    if sort in ("image", "any"):
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
        grad = xx / (n - 1)
        disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
        checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
        return np.clip(0.35 * grad + 0.45 * disk + checker
                       + 0.03 * _rng().standard_normal((n, n)), 0, 1)
    if sort == "region":
        yy, xx = np.mgrid[0:n, 0:n]
        return (((yy - n // 2) ** 2 + (xx - n // 2) ** 2) < (n * 0.25) ** 2).astype(np.float64)
    if sort == "color":
        g = input_for("image", n)
        return np.clip(np.stack([g, 0.7 * g + 0.1, 1 - g], -1), 0, 1)
    if sort == "volume":
        zz, vy, vx = np.mgrid[0:8, 0:24, 0:24]
        return np.clip(0.5 + 0.3 * np.sin(vx / 3.0) * np.cos(vy / 4.0) * (zz / 8.0), 0, 1)
    if sort == "contour":
        sq = np.array([[6.0, 6.0], [6.0, 20.0], [20.0, 20.0], [20.0, 6.0], [6.0, 6.0]])
        return {"shape": (32, 32), "cs": [sq]}
    if sort == "feature":
        return np.linspace(0.0, 1.0, 16, dtype=np.float64)
    raise ValueError(f"input_for: unknown sort {sort!r}")


def image_battery(n: int = 48):
    """A small edge-input battery (like conftest.image_bank) for the finite/determinism sweep."""
    normal = input_for("image", n)
    single = np.zeros((n, n)); single[n // 2, n // 2] = 1.0
    return {
        "normal": normal,
        "const0": np.zeros((n, n)),
        "const1": np.ones((n, n)),
        "const_mid": np.full((n, n), 0.42),
        "tiny4": (np.arange(16, dtype=np.float64) / 15.0).reshape(4, 4),
        "single_bright": single,
    }


# The TARGET set: every op whose category is texture/frequency/decomposition.
# Written as explicit string literals so each op name appears in the source
# (needed for the op -> example index). Length MUST equal the registry count.
OPS = [
    "lowpass", "highpass", "std_filter", "gabor", "sk_frangi", "sk_meijering",
    "sk_hessian", "sk_gabor", "sk_butterworth", "sk_lbp", "sk_entropy",
    "sk_shape_index", "fft_image", "power_real", "power_byte", "phase_rad",
    "highpass_image", "bandpass_image", "deviation_image", "texture_laws",
    "entropy_image", "gen_gabor", "cooc_feature_matrix", "fft_image_inv",
    "fft_generic", "power_ln", "rft_generic", "phase_deg", "xsk_struct_coherence",
    "xsk_meijering", "xsk_sato", "xsp_hilbert_env", "xsp_dct", "xsp_dct_lowpass",
    "xsk2_hog", "xsk2_radon", "xwt_subband_tile", "xwt_mra_component",
    "f2_symmetry", "dc_structure_texture", "dc_texture_residual", "dc_rpca_lowrank",
    "dc_rpca_sparse", "dc_retinex", "dc_local_contrast_norm", "dc_homomorphic",
    "tf_census_transform", "tf_rank_transform",
]

KNOBS = [(0.0, 0.0), (0.5, 0.5), (1.0, 1.0), (0.15, 0.85)]

BY = {o.name: o for o in ops.REGISTRY}


def _finite(x) -> bool:
    return bool(np.all(np.isfinite(np.asarray(x, np.float64))))


def _equal(x, y) -> bool:
    return (isinstance(x, np.ndarray) and isinstance(y, np.ndarray)
            and x.shape == y.shape and np.array_equal(x, y, equal_nan=True)) or \
           bool(np.all(np.asarray(x) == np.asarray(y)))


def _lapvar(z: np.ndarray) -> float:
    """High-frequency energy proxy: variance of the 4-neighbour Laplacian."""
    lap = (z[2:, 1:-1] + z[:-2, 1:-1] + z[1:-1, 2:] + z[1:-1, :-2] - 4 * z[1:-1, 1:-1])
    return float((lap ** 2).mean())


def _check_out_sort(name: str, out, out_sort: str) -> None:
    if out_sort in ("image", "region"):
        assert isinstance(out, np.ndarray) and out.ndim == 2, \
            f"{name}: {out_sort} output is not a 2-D ndarray (got {type(out).__name__})"
        assert _finite(out), f"{name}: {out_sort} output not finite"
    elif out_sort == "feature":
        f = np.asarray(out, np.float64).reshape(-1)
        assert f.size >= 1 and np.all(np.isfinite(f)), \
            f"{name}: feature output empty or non-finite"
    else:
        raise AssertionError(f"{name}: unexpected out_sort {out_sort!r} in this family")


def run_contracts() -> int:
    """Contract (1)-(4) over every op in the family. Returns number of ops exercised."""
    battery = image_battery()
    for name in OPS:
        assert name in BY, f"op {name!r} vanished from the registry"
        op = BY[name]

        # (1) runs + (2) finite, over the whole edge battery x knobs. raise = loud fail.
        for iname, iv in battery.items():
            for a, b in KNOBS:
                try:
                    out = op.fn(np.array(iv, copy=True), float(a), float(b))
                except Exception as exc:  # noqa: BLE001 - re-raise loudly with context
                    raise AssertionError(
                        f"{name} raised on input '{iname}' (a={a}, b={b}): "
                        f"{type(exc).__name__}: {exc}") from exc
                for arr in ([out] if isinstance(out, np.ndarray) else [np.asarray(out)]):
                    bad = ~np.isfinite(np.asarray(arr, np.float64))
                    assert not bad.any(), (
                        f"{name} produced {int(bad.sum())} non-finite value(s) "
                        f"on input '{iname}' (a={a}, b={b})")

        # (3) declared out_sort on the primary input
        primary = input_for(op.in_sort)
        out = op.fn(np.array(primary, copy=True)
                    if isinstance(primary, np.ndarray) else primary, 0.5, 0.5)
        _check_out_sort(name, out, op.out_sort)

        # (4) determinism: bit-identical on repeated calls, across the battery
        for iname, iv in battery.items():
            ref = op.fn(np.array(iv, copy=True), 0.5, 0.5)
            for _ in range(2):
                again = op.fn(np.array(iv, copy=True), 0.5, 0.5)
                assert _equal(ref, again), \
                    f"{name} is nondeterministic on input '{iname}'"
    return len(OPS)


def run_ground_truth() -> int:
    """Stronger, effect-specific GT + beat-the-null on representative ops. Returns count."""
    n = 64
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    rng = np.random.default_rng(20260812)
    grad = xx / (n - 1)
    disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
    checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
    img = np.clip(0.35 * grad + 0.45 * disk + checker + 0.03 * rng.standard_normal((n, n)), 0, 1)
    step = np.where(xx < n / 2, 0.2, 0.8)          # sharp vertical edge at column n/2
    flat = np.full((n, n), 0.4)
    tex = np.clip(0.4 + 0.25 * rng.standard_normal((n, n)), 0, 1)

    checks = 0

    # GT1: lowpass attenuates high-frequency energy (blur). beat-the-null: must drop >2x.
    lp = BY["lowpass"].fn(img.copy(), 0.5, 0.5)
    hf_before, hf_after = _lapvar(img), _lapvar(lp)
    assert hf_after < 0.5 * hf_before, \
        f"lowpass did not attenuate high-freq energy: {hf_before:.4g} -> {hf_after:.4g}"
    checks += 1

    # GT2: highpass responds at an edge far more than in a flat region.
    hp = BY["highpass"].fn(step.copy(), 0.5, 0.5)   # _signed01: 0.5 == "no detail"
    col = n // 2
    edge_energy = float(np.abs(hp[:, col - 1:col + 1] - 0.5).mean())
    flat_energy = float(np.abs(hp[:, 2:6] - 0.5).mean())
    assert edge_energy > 3.0 * flat_energy, \
        f"highpass edge/flat ratio too small: edge={edge_energy:.4g} flat={flat_energy:.4g}"
    checks += 1

    # GT3: std_filter ~ 0 on a flat field, large on texture. beat-the-null both sides.
    sf_flat = BY["std_filter"].fn(flat.copy(), 0.5, 0.5)
    sf_tex = BY["std_filter"].fn(tex.copy(), 0.5, 0.5)
    assert float(sf_flat.mean()) < 1e-3, f"std_filter not ~0 on flat: {sf_flat.mean():.4g}"
    assert float(sf_tex.mean()) > 0.1, f"std_filter too small on texture: {sf_tex.mean():.4g}"
    checks += 1

    # GT4: rank_transform is invariant to a positive gain (ordinal), but NOT to
    #      contrast inversion — the "not" half proves the check is non-trivial.
    r1 = BY["tf_rank_transform"].fn(img.copy(), 0.5, 0.0)
    r_gain = BY["tf_rank_transform"].fn((0.6 * img).copy(), 0.5, 0.0)
    r_inv = BY["tf_rank_transform"].fn((1.0 - img).copy(), 0.5, 0.0)
    assert np.array_equal(r1, r_gain), "rank_transform not gain-invariant"
    assert not np.array_equal(r1, r_inv), "rank_transform unchanged under contrast inversion (null not beaten)"
    checks += 1

    # GT5: entropy_image ~ 0 on a constant field, high on noise/texture.
    e_const = BY["entropy_image"].fn(flat.copy(), 0.5, 0.5)
    e_noise = BY["entropy_image"].fn(tex.copy(), 0.5, 0.5)
    assert float(e_const.mean()) < 1e-6, f"entropy not ~0 on constant: {e_const.mean():.4g}"
    assert float(e_noise.mean()) > 0.3, f"entropy too low on texture: {e_noise.mean():.4g}"
    checks += 1

    # GT6: DCT low-pass attenuates high-frequency energy (frequency-domain blur).
    dl = BY["xsp_dct_lowpass"].fn(img.copy(), 0.5, 0.5)
    assert _lapvar(dl) < 0.5 * _lapvar(img), \
        f"xsp_dct_lowpass did not attenuate high-freq energy: {_lapvar(img):.4g} -> {_lapvar(dl):.4g}"
    checks += 1

    return checks


def main() -> int:
    # Guard: the explicit OPS literal list must still equal the live registry set.
    cats = ("texture", "frequency", "decomposition")
    live = [o.name for o in ops.REGISTRY if o.category in cats]
    missing = sorted(set(live) - set(OPS))
    extra = sorted(set(OPS) - set(live))
    assert not missing and not extra, \
        f"OPS list drifted from registry: missing={missing} extra={extra}"
    assert len(OPS) == len(live) == len(set(OPS)), \
        f"count/uniqueness mismatch: OPS={len(OPS)} live={len(live)} unique={len(set(OPS))}"

    n = run_contracts()
    k = run_ground_truth()
    print(f"PASS: {n} ops exercised, all finite/typed/deterministic; {k} GT checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
