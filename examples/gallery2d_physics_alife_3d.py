# -*- coding: utf-8 -*-
"""事例: 物理PDE・人工生命・トモグラフィ・3Dボリューム・マクロ・バーコード op 一括ギャラリー (task: contract+GT gallery).

平たく言うと
------------
このファイルは Fullseye/imgevolve のレジストリのうち、カテゴリが
``physics`` / ``artificial-life`` / ``tomography`` / ``3d`` / ``macro`` / ``barcode``
に属する **すべての 2-D(+ボリューム)op** を 1 本の走る例で網羅する。それぞれの op が
「何をするものか」を平たく言うと:

  * physics (``ph_*``)        : 画像を PDE(熱拡散・Perona-Malik・平均曲率流・TV流など)の
                                初期条件とみなし数ステップ積分する物理フロー。ノイズ除去や
                                エッジ保存平滑の"教科書どおりの"実装。
  * artificial-life (``alife_*``): 画像を力学系の初期状態とみなす生成 op(反応拡散・
                                セルオートマトン・励起媒質・Lenia・砂山モデルなど)。
  * tomography (``tm_*``)     : 画像をサイノグラム(CT の生投影)とみなし、Radon 前方投影 /
                                フィルタ補正逆投影(FBP)/ 代数再構成(SART)などを行う。
  * 3d (``vol_*``)            : scipy.ndimage は N 次元なので、CT/MRI スタックのような
                                3-D ボリュームへの平滑・モルフォロジ・しきい値・投影。
  * macro                     : 進化探索(evolve.py)が発見したチャンピオン pipeline を 1 つの
                                再利用 op に凍結した"DNA op"(denoise / edge / binarize / vol）。
  * barcode                   : 中央走査線上の暗バー本数を数える簡易デコーダ(image -> feature)。

検証(GT = ground truth)
------------------------
本ファイルは「動く」だけでなく **落ちうる本物のアサーション** を持つ:

  A. 契約検査(全 op): 出力が (1) 有限(NaN/Inf なし)、(2) 宣言された out_sort に一致
     (image/region/volume -> その次元の float 配列で [0,1]、feature -> 有限スカラー)、
     (3) 決定的(同一入力 -> ビット一致)であることを 1 op ずつ検査する。例外を投げた op は
     握りつぶさず大声で失敗させる。
  B. 既知挙動 GT + beat-the-null(代表 6 op): 効果が既知の op には強い GT を追加する
     (熱拡散は分散を下げる / マクロ除去はノイズ画像の標準偏差を下げる / サイノグラム平滑は
      角度方向の隣接行差を下げる / バーコードは仕込んだ本数を返す / ボリュームしきい値と
      マクロエッジは二値になり両クラスを含む)。

`ops.REGISTRY` の当該カテゴリ全 op を走らせ、契約 + GT を満たせば最後に PASS 行を出して exit 0。

    py -3.11 examples/gallery2d_physics_alife_3d.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np  # noqa: E402
import ops  # noqa: E402


# --------------------------------------------------------------------------- #
# per-sort input factory (replicated from tests/conftest.py — examples must    #
# NOT import from tests/). Returns a FRESH, valid input for each in_sort.       #
# --------------------------------------------------------------------------- #
def input_for(sort: str):
    """A deterministic, valid input array matching ``sort``.

    Mirrors conftest's ``image_bank['normal']`` / ``volume_bank['normal']`` — a
    2-D float image in [0,1] with real spatial structure (gradient + bright disk
    + checker + a touch of fixed-seed noise), and an 8x24x24 float volume in
    [0,1]. A fresh array is built on every call, so the determinism check below
    compares outputs of two INDEPENDENT copies of the same input.
    """
    if sort == "image":
        n = 48
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
        grad = xx / (n - 1)
        disk = ((yy - n * 0.35) ** 2 + (xx - n * 0.4) ** 2) < (n * 0.18) ** 2
        checker = ((xx.astype(int) // 6 + yy.astype(int) // 6) % 2) * 0.15
        noise = 0.03 * np.random.default_rng(20260812).standard_normal((n, n))
        return np.clip(0.35 * grad + 0.45 * disk + checker + noise, 0.0, 1.0)
    if sort == "volume":
        zz, vy, vx = np.mgrid[0:8, 0:24, 0:24]
        return np.clip(0.5 + 0.3 * np.sin(vx / 3.0) * np.cos(vy / 4.0) * (zz / 8.0), 0.0, 1.0)
    raise ValueError(f"input_for: no factory for in_sort={sort!r} (extend me)")


# --------------------------------------------------------------------------- #
# TARGET set — EVERY op whose category is one of the six families, as explicit  #
# string literals so each name is greppable for the op->example index.          #
# (Computed once from ops.REGISTRY, then pinned here; the count is asserted      #
#  against the live registry at run time so the list can never silently drift.)  #
# --------------------------------------------------------------------------- #
OPS = [
    # barcode (image -> feature)
    "decode_barcode",
    # 3d volume ops (volume -> volume | image)
    "vol_gaussian", "vol_median", "vol_erode", "vol_dilate", "vol_threshold",
    "vol_mip", "vol_slice",
    # physics / PDE flows (image -> image)
    "ph_perona_malik", "ph_coherence_enhancing_diffusion", "ph_reaction_diffusion",
    "ph_heat_flow", "ph_mean_curvature_motion", "ph_total_variation_flow",
    # tomography (image[/sinogram] -> image)
    "tm_radon_forward", "tm_fbp_reconstruct", "tm_sart_reconstruct",
    "tm_backproject_unfiltered", "tm_sinogram_denoise",
    # artificial life — continuum + discrete (image -> image)
    "alife_gray_scott", "alife_turing", "alife_life_step", "alife_cyclic_ca",
    "alife_perona_malik", "alife_curvature_flow", "alife_dla", "alife_reaction_bz",
    "alife_wolfram1d", "alife_langton_ant", "alife_lenia", "alife_sandpile",
    # macro — frozen evolved-champion "DNA" ops
    "macro_denoise", "macro_edge", "macro_binarize", "macro_vol_denoise",
]

FAMILIES = ("physics", "artificial-life", "tomography", "3d", "macro", "barcode")

_TOL = 1e-9  # float slack for [0,1] range checks


def _is_finite(x) -> bool:
    return bool(np.isfinite(np.asarray(x, np.float64)).all())


def _check_contract(name: str, op, out, out2) -> None:
    """Assert (finite, correct out_sort/shape/range, deterministic) for one op.

    Raises AssertionError on any violation — no swallowing, no tautology.
    """
    sort = op.out_sort
    assert _is_finite(out), f"{name}: output not finite (NaN/Inf present)"

    if sort == "feature":
        arr = np.asarray(out)
        assert arr.ndim == 0, f"{name}: feature must be a scalar, got ndim={arr.ndim}"
        assert np.isfinite(float(arr)), f"{name}: feature scalar not finite"
    elif sort in ("image", "region", "volume"):
        assert isinstance(out, np.ndarray), f"{name}: {sort} must be an ndarray, got {type(out).__name__}"
        want_ndim = 3 if sort == "volume" else 2
        assert out.ndim == want_ndim, f"{name}: {sort} must be {want_ndim}-D, got shape {out.shape}"
        assert out.dtype.kind == "f", f"{name}: {sort} must be float, got dtype {out.dtype}"
        lo, hi = float(out.min()), float(out.max())
        assert -_TOL <= lo and hi <= 1.0 + _TOL, f"{name}: {sort} out of [0,1]: [{lo:.4f},{hi:.4f}]"
        if sort == "region":
            uniq = set(np.unique(out).tolist())
            assert uniq <= {0.0, 1.0}, f"{name}: region must be binary {{0,1}}, got {sorted(uniq)[:6]}"
    else:
        raise AssertionError(f"{name}: unexpected out_sort {sort!r} for this family")

    # determinism: same input (two independent fresh copies) -> bit-identical output
    if isinstance(out, np.ndarray):
        assert np.array_equal(out, out2), f"{name}: non-deterministic (outputs differ on identical input)"
    else:
        assert float(np.asarray(out)) == float(np.asarray(out2)), f"{name}: non-deterministic scalar"


# --------------------------------------------------------------------------- #
# Ground-truth / beat-the-null checks (representative ops, known effects).      #
# Each returns a one-line label; each assert can genuinely fail.                #
# --------------------------------------------------------------------------- #
def _gt_checks(BY) -> list[str]:
    logs: list[str] = []
    n = 48
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    grad = xx / (n - 1)
    img = input_for("image")

    # GT1 — ph_heat_flow is linear isotropic diffusion: it MUST lower variance
    # (a blur) versus the sharp input; null = "does nothing" would keep variance.
    heat = BY["ph_heat_flow"].fn(np.array(img, copy=True), 1.0, 0.0)
    assert heat.var() < img.var() * 0.9, f"ph_heat_flow did not reduce variance ({heat.var():.4f} vs {img.var():.4f})"
    logs.append(f"ph_heat_flow var {img.var():.4f} -> {heat.var():.4f} (diffusion lowers variance)")

    # GT2 — macro_denoise (3 evolved bilateral passes) on a NOISY smooth base
    # must both lower std and cut the MSE-to-clean-base vs the noisy input (null).
    base = np.clip(0.3 + 0.4 * grad, 0.0, 1.0)
    noisy = np.clip(base + 0.12 * np.random.default_rng(1).standard_normal((n, n)), 0.0, 1.0)
    den = BY["macro_denoise"].fn(np.array(noisy, copy=True), 0.5, 0.5)
    assert den.std() < noisy.std(), f"macro_denoise did not lower std ({den.std():.4f} vs {noisy.std():.4f})"
    mse_noisy = float(((noisy - base) ** 2).mean())
    mse_den = float(((den - base) ** 2).mean())
    assert mse_den < mse_noisy, f"macro_denoise did not beat the noisy null ({mse_den:.5f} vs {mse_noisy:.5f})"
    logs.append(f"macro_denoise MSE-to-clean {mse_noisy:.5f} -> {mse_den:.5f} (beats noisy input)")

    # GT3 — tm_sinogram_denoise smooths ALONG the angle axis (rows): mean adjacent
    # row difference must drop vs input (null = unchanged sinogram).
    sd = BY["tm_sinogram_denoise"].fn(np.array(img, copy=True), 1.0, 0.0)
    d_before = float(np.abs(np.diff(img, axis=0)).mean())
    d_after = float(np.abs(np.diff(sd, axis=0)).mean())
    assert d_after < d_before, f"tm_sinogram_denoise did not smooth rows ({d_after:.4f} vs {d_before:.4f})"
    logs.append(f"tm_sinogram_denoise row-diff {d_before:.4f} -> {d_after:.4f} (angle-axis smoothing)")

    # GT4 — decode_barcode counts dark bars on the mid scanline. Build a mid row
    # with exactly 5 dark bars on a bright field; the op must return 5.0
    # (null/blank would return 0). a=0.5 -> dark threshold 0.5.
    bar = np.ones((10, 40), np.float64)
    for k in range(5):
        s = 3 + k * 7
        bar[5, s:s + 3] = 0.0
    cnt = float(BY["decode_barcode"].fn(bar, 0.5, 0.0))
    assert cnt == 5.0, f"decode_barcode miscounted bars: {cnt} != 5"
    logs.append(f"decode_barcode counted {int(cnt)} of 5 planted bars (exact GT)")

    # GT5 — vol_threshold must produce a strictly binary volume containing BOTH
    # classes on structured input (null = a constant field would be one class).
    vol = input_for("volume")
    vt = BY["vol_threshold"].fn(np.array(vol, copy=True), 0.5, 0.5)
    assert set(np.unique(vt).tolist()) <= {0.0, 1.0}, "vol_threshold not binary"
    assert vt.min() == 0.0 and vt.max() == 1.0, "vol_threshold missing a class (all-0 or all-1)"
    logs.append("vol_threshold -> strictly binary volume with both 0 and 1")

    # GT6 — macro_edge ends in an Otsu segmentation: its region must be binary and
    # respond (have foreground edge pixels) on a structured image, not the flat null.
    me = BY["macro_edge"].fn(np.array(img, copy=True), 0.5, 0.5)
    assert set(np.unique(me).tolist()) <= {0.0, 1.0}, "macro_edge region not binary"
    assert me.min() == 0.0 and me.max() == 1.0, "macro_edge produced no edge foreground"
    flat = BY["macro_edge"].fn(np.full((n, n), 0.42), 0.5, 0.5)
    assert flat.sum() < me.sum(), "macro_edge fired MORE on a flat image than a structured one"
    logs.append(f"macro_edge edge px: structured {int(me.sum())} > flat {int(flat.sum())} (beats null)")

    return logs


# --------------------------------------------------------------------------- #
# main                                                                          #
# --------------------------------------------------------------------------- #
def main() -> int:
    BY = {o.name: o for o in ops.REGISTRY}  # name -> Op

    # The pinned OPS list must equal the LIVE registry's set for these families,
    # so this example can never silently under-cover a newly added op.
    live = sorted(o.name for o in ops.REGISTRY if o.category in FAMILIES)
    pinned = sorted(OPS)
    assert len(OPS) == len(set(OPS)), "OPS contains duplicates"
    assert pinned == live, (
        "OPS list is out of sync with the registry.\n"
        f"  missing from OPS : {sorted(set(live) - set(pinned))}\n"
        f"  extra in OPS     : {sorted(set(pinned) - set(live))}"
    )

    print(f"== gallery: {len(OPS)} ops across families {list(FAMILIES)} ==")
    per_family: dict[str, int] = {}
    for name in OPS:
        assert name in BY, f"{name}: not found in ops.REGISTRY"
        op = BY[name]
        x1 = input_for(op.in_sort)
        x2 = input_for(op.in_sort)  # independent identical copy for determinism
        try:
            out = op.fn(x1, 0.5, 0.5)
            out2 = op.fn(x2, 0.5, 0.5)
        except Exception as exc:  # loud failure — never silently skip a target op
            raise AssertionError(f"{name}: op raised {type(exc).__name__}: {exc}") from exc
        _check_contract(name, op, out, out2)
        per_family[op.category] = per_family.get(op.category, 0) + 1
        shape = "scalar" if not isinstance(out, np.ndarray) else str(out.shape)
        print(f"  ok  {name:34s} {op.in_sort:7s}-> {op.out_sort:7s} {shape}")

    print("== ground-truth / beat-the-null checks ==")
    gt = _gt_checks(BY)
    for line in gt:
        print(f"  GT  {line}")

    fam_summary = ", ".join(f"{k}:{per_family[k]}" for k in sorted(per_family))
    print(f"\nfamilies -> {fam_summary}")
    print(f"PASS: {len(OPS)} ops exercised, all finite/typed/deterministic; {len(gt)} GT checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
