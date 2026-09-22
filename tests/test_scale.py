"""Large-image tiling (scale.py): local ops are bit-interior-identical under
haloed tiling, and scale_class flags the ops that need an algorithm change.
"""
from __future__ import annotations

import numpy as np
import pytest

import ops
import scale


def _img(n=200):
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float64)
    return np.clip(0.5 + 0.3 * np.sin(xx / 9.0) * np.cos(yy / 7.0), 0, 1)


# genuinely local ops with NO trailing global normalization -> bit-exact under tiling
@pytest.mark.parametrize("name,halo", [
    ("gaussian", 24), ("gerode", 8), ("gdilate", 8), ("mean_box", 8), ("median", 8),
])
def test_tiled_matches_whole_for_local_ops(name, halo):
    err = scale.tiling_error(ops.RT[name], _img(), a=0.4, b=0.5, tile=64, halo=halo)
    assert err < 1e-6, f"{name}: tiled result differs from whole-image by {err}"


def test_globally_normalized_op_tiles_spatially_but_not_in_scale():
    """sobel_mag ends in a global _norm, so tiling is structurally right but not
    bit-identical — documents the scale.py caveat rather than pretending otherwise."""
    err = scale.tiling_error(ops.RT["sobel_mag"], _img(), a=0.4, b=0.5, tile=64, halo=8)
    assert err > 0.0   # differs (per-tile normalization) — expected, not a tile-safe op


def test_process_tiled_handles_non_multiple_size():
    img = _img(150)                                   # 150 not a multiple of tile=64
    out = scale.process_tiled(ops.RT["gaussian"], img, a=0.5, tile=64, halo=16)
    assert out.shape == img.shape and np.all(np.isfinite(out))


def test_scale_class_flags_known_cases():
    by = {o.name: o for o in ops.REGISTRY}
    assert scale.scale_class(by["gaussian"])["tile_safe"] is True
    assert scale.scale_class(by["lowpass"])["class"] == "memory_bound"        # FFT
    assert scale.scale_class(by["polar_trans_image"])["class"] == "cv2_limited"
    assert scale.scale_class(by["otsu"])["tile_safe"] is False                # global threshold


# --- the tile-safe classification is measured, not guessed -------------------- #
# A category-only classifier called 141 non-local ops "tile_safe" (region skeleton /
# distance / shape, gray histogram, edge magnitude / corner / DoG, multiscale
# texture, TV / diffusion / transform smoothers). scale._NOT_TILE_SAFE lists them.
# These two tests keep that list honest against the actual haloed tiler, so the
# classifier can never again silently promise a tiling that gives a wrong answer.

def _probes():
    """Structured (non-random) images with a bright feature parked in ONE tile, so a
    whole-image normalization or a global region op diverges from the tiled result."""
    yy, xx = np.mgrid[:192, :192]
    a = (0.3 + 0.5 * xx / 192).astype(np.float64)
    a[20:60, 20:120] = 0.9; a[120:170, 60:150] = 0.1; a[:8, :8] = 1.0
    b = np.zeros((160, 160)); b[40:120, 40:120] = 1.0; b[70:90, 70:90] = 0.3; b[:6, -6:] = 0.8
    c = np.sin(np.mgrid[:176, :176][1] / 9.0) * 0.4 + 0.5; c[10:30, 10:30] = 1.0
    # ★d: **穴がタイル境界を跨ぐ**画像。これが無いと領域 op(fill_holes /
    #   select_shape / fill_up …)がタイル分割で壊れることを検出できない ——
    #   b の穴(70:90)はどのタイルにも収まっているので、埋めた結果が一致して
    #   しまう。2026-09-17 にこの探針を足して、tile_safe と宣言されていた
    #   6 本が誤差 1.0(全く別の結果)で割れることが分かった。
    #   穴は 45..95 にとり、tile=64 の境界(64)と tile=60 の境界(60)の両方を跨ぐ。
    d = np.zeros((192, 192)); d[20:170, 20:170] = 1.0; d[45:95, 45:95] = 0.0
    d[110:140, 50:150] = 0.0                     # 横長の穴 —— halo をいくら広げても届かない
    # ★e: **細かい周期**を持つ画像。変換ドメイン(ウェーブレット)・非局所平均・
    #   LBP はここで初めて割れる。乱数でなく決まった模様にしてあるのは、
    #   乱数だと対称性の破れが隠れるため。
    yy2, xx2 = np.mgrid[:192, :192]
    e = (((yy2 // 3 + xx2 // 3) % 2) * 0.6 + 0.2 + 0.2 * xx2 / 192.0)
    e[80:112, 80:112] = 1.0
    # ★f: **小さな粒と穴が多数**ある画像。面積で選ぶ op(remove_small_holes /
    #   select_shape / diameter_opening)は、粒がタイル境界で切られて面積が変わる
    #   ことでしか壊れない —— 大きな構造しか無い探針では 0.0 のまま通る。
    #   種を固定してあるので実行ごとに同じ(乱数そのものを検査対象にはしない)。
    #   ★種は 2 つ持つ。1 つの種は「構造の 1 標本」でしかない ——
    #   ``xsk2_isotropic_close`` は種 0 と 7 で誤差 1.0(全く別の結果)、種 1 と
    #   20260917 では 0.0 だった。半分の種で割れる op を「タイル安全」と呼ばない
    #   ために、当たり外れのある探針は複数枚そろえる。
    f = np.clip(np.random.default_rng(20260917).normal(0.5, 0.15, (192, 192)), 0.0, 1.0)
    f[30:60, 30:60] = 1.0
    g = np.clip(np.random.default_rng(0).normal(0.5, 0.15, (192, 192)), 0.0, 1.0)
    g[100:140, 20:60] = 1.0
    return [a, b, c, d, e, f, g]


#: (tile, halo) の組。★**64/16 だけで測ってはいけない** —— どちらも 8 の倍数なので、
#: 8x8 の周期を持つ処理(順序ディザの Bayer 行列など)はタイルの位相がそろって
#: たまたま一致する。実測で ``dither_ordered`` は 64/16 で誤差 0.0000、60/12 でも
#: 50/10 でも 37/7 でも 0.1429 だった。**整列していない幅を必ず 1 つ混ぜる。**
#: これを入れた 2026-09-17 に、tile_safe と宣言された 168 本のうち **16 本**が
#: 割れることが分かった(``fill_holes`` など 6 本は誤差 1.0 = 全く別の結果)。
#: 3 組目 ``(50, 8)`` は**ハローが狭い**設定。「支持長がハローを超えるか」で決まる
#: op(ウェーブレット再構成・大きな構造要素のモルフォロジー)は、広いハローでは
#: たまたま一致するので、狭い側も試さないと分類が甘くなる。halo は利用者が選ぶ値
#: なので、「ある halo でだけ安全」は tile_safe と呼べない。
_TILINGS = ((64, 16), (60, 12), (50, 8))


def _worst_tiling_error(op, stop_above=None):
    """Max tiling_error over the probes x two param settings x two tilings (-1.0 if it never ran).

    ★*stop_above* を渡すと、その値を**超えた時点で打ち切る**(2026-09-23)。
    呼び出し側はどちらも「閾値を超えるか」という**真偽**しか見ないので、
    打ち切っても判定は 1 件も変わらない —— 変わるのは「超えている op に
    対して、超えたあとも全組み合わせを回し続けていた」ぶんだけ。
    実測: `test_not_tile_safe_list_is_not_stale` は 166 op を全組み合わせで
    回して **143 秒**、その大半が最初の探針で既に発散していた。
    """
    mx, ran = 0.0, False
    for im in _probes():
        for a, b in ((0.5, 0.5), (0.3, 0.7)):
            for tile, halo in _TILINGS:
                try:
                    e = scale.tiling_error(op.fn, im, a, b, tile=tile, halo=halo)
                except Exception:                            # noqa: BLE001 - optional backend / shape
                    continue
                if np.isfinite(e):
                    mx, ran = max(mx, e), True
                    if stop_above is not None and mx > stop_above:
                        return mx
    return mx if ran else -1.0


def test_no_tile_safe_op_actually_breaks_under_tiling():
    """Completeness: every op scale_class marks tile_safe is bit-interior-identical
    under haloed tiling (the whole point of the class). Generous 1e-3 margin keeps
    the handful of borderline iterative smoothers — which ARE listed non-tileable —
    from making this flaky.
    """
    bad = []
    for op in ops.REGISTRY:
        if not scale.scale_class(op).get("tile_safe"):
            continue
        err = _worst_tiling_error(op)
        if err > 1e-3:
            bad.append((op.name, getattr(op, "category", ""), round(err, 4)))
    assert not bad, ("ops marked tile_safe that measurably break under tiling: %s\n"
                     "add them to scale._NOT_TILE_SAFE (with the right category "
                     "reason) or fix the op." % sorted(bad, key=lambda t: -t[2]))


def test_not_tile_safe_list_is_not_stale():
    """Staleness: every op in _NOT_TILE_SAFE really does diverge under tiling
    (> 1e-9). If an op became genuinely local, drop it from the set so the class
    stops under-reporting. Threshold is far below the completeness margin, so the
    two never contradict on a borderline op.
    """
    by = {o.name: o for o in ops.REGISTRY}
    stale = []
    for name in scale._NOT_TILE_SAFE:
        op = by.get(name)
        if op is None:
            continue                                         # optional backend absent
        err = _worst_tiling_error(op, stop_above=1e-9)
        if err >= 0.0 and err <= 1e-9:
            stale.append((name, err))
    assert not stale, ("_NOT_TILE_SAFE entries that are actually tileable now "
                       "(remove them): %s" % stale)


def test_reclassified_ops_report_actionable_class():
    """The measured non-tileable ops carry a real reason, not the tile_safe default."""
    by = {o.name: o for o in ops.REGISTRY}
    for name, cls in [("sobel_mag", "global_reduce"), ("sk_skeleton", "global"),
                      ("clahe", "global"), ("dist_transform", "global")]:
        if name in by:
            sc = scale.scale_class(by[name])
            assert sc["tile_safe"] is False and sc["class"] == cls, (name, sc)
