"""imgevolve — problem definitions (multi-sort aware).

Four shared-DSL problems; the last exercises the full HALCON-shaped chain
image -> region -> feature:

  denoise  : recover clean from noise            (image target) -> PSNR
  edge     : detect edges vs gradient GT         (region target) -> F1
  binarize : segment foreground (clean>0.5)      (region target) -> IoU
  count    : count foreground blobs              (feature target) -> 1/(1+|err|)

A pipeline's final value may be an image/region (2-D) or a feature (scalar); each
problem coerces it to what its metric needs, so evolution is rewarded for landing
in the right sort.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
from scipy import ndimage

import ops


def _synth(rng, size):
    img = np.full((size, size), rng.uniform(0.1, 0.4), np.float64)
    for _ in range(rng.integers(3, 7)):
        v = rng.uniform(0.0, 1.0)
        x0, y0 = rng.integers(0, size, 2)
        w, h = rng.integers(size // 6, size // 2, 2)
        img[y0:y0 + h, x0:x0 + w] = v
    yy, xx = np.mgrid[0:size, 0:size]
    for _ in range(rng.integers(1, 3)):
        cx, cy = rng.integers(0, size, 2)
        r = rng.integers(size // 8, size // 4)
        img[(xx - cx) ** 2 + (yy - cy) ** 2 <= r * r] = rng.uniform(0.0, 1.0)
    return np.clip(img, 0.0, 1.0)


def _clean_stack(n, size, seed):
    rng = np.random.default_rng(seed)
    return np.stack([_synth(rng, size) for _ in range(n)]).astype(np.float64)


def _is_img(v):
    return isinstance(v, np.ndarray) and v.ndim == 2


def _as_image(final, shape):
    if _is_img(final):
        return np.clip(final, 0, 1)
    if isinstance(final, (int, float)) or (isinstance(final, np.ndarray) and final.ndim == 0):
        return np.full(shape, float(np.clip(final, 0, 1)), np.float64)
    return np.zeros(shape, np.float64)  # contour dict / match array -> penalise for image tasks


def _as_binary(final, shape):
    return (_as_image(final, shape) > 0.5).astype(np.float64)


def _as_count(final):
    if isinstance(final, np.ndarray) and final.ndim in (2, 3):
        return float(ndimage.label(final > 0.5)[1])
    if isinstance(final, dict) and "cs" in final:      # contour -> number of contours
        return float(len(final["cs"]))
    try:
        return float(np.asarray(final).ravel()[0])
    except Exception:
        return 0.0


def _f1(pred, gt):
    tp = float(np.sum(pred * gt)); fp = float(np.sum(pred * (1 - gt))); fn = float(np.sum((1 - pred) * gt))
    return tp / (tp + 0.5 * (fp + fn)) if (tp + fp + fn) > 0 else 1.0


def _iou(pred, gt):
    inter = float(np.sum(pred * gt)); union = float(np.sum(np.clip(pred + gt, 0, 1)))
    return inter / union if union > 0 else 1.0


@dataclass
class Problem:
    name: str
    unit: str
    make: Callable[[int, int, int], dict]
    score_value: Callable  # (final_value, item) -> float (higher better)
    hand_stages: Callable[[], list]
    in_sort: str = "image"  # pipeline start sort (image | volume | ...)

    def score(self, genome, data) -> float:
        inp, items = data["input"], data["items"]
        return float(np.mean([self.score_value(ops.run_genome(genome, inp[i], self.in_sort), items[i])
                              for i in range(len(inp))]))

    def score_stages(self, stages, data) -> float:
        inp, items = data["input"], data["items"]
        return float(np.mean([self.score_value(ops.run_stages(stages, inp[i]), items[i]) for i in range(len(inp))]))

    @classmethod
    def from_pairs(cls, inputs, targets, name="pairs", metric=None, unit=None,
                   in_sort="image", hand_stages=None) -> "Problem":
        """Build a Problem from explicit ``(input, target)`` arrays.

        This is the real-data counterpart to the synthetic ``_synth`` generator:
        drop in captured frames (``inputs``) and their desired outputs (``targets``)
        and evolution optimizes against them exactly like a built-in PROBLEM. Purely
        additive — it does not touch ``PROBLEMS`` or ``_synth``.

        Parameters
        ----------
        inputs, targets : array-likes of equal length; ``inputs[i]`` pairs with
            ``targets[i]``. Targets may be images (H x W) or scalars (counts).
        metric : ``(final_value, target) -> float`` (higher better). Defaults to
            PSNR when the target is a 2-D image, else ``1/(1+|count_err|)``.
        unit : label for reporting (defaults to a metric-appropriate string).
        in_sort : pipeline start sort (``"image"`` | ``"volume"`` | ...).
        hand_stages : optional ``() -> list`` baseline; defaults to trivial (identity).

        ``make(n, size, seed)`` returns a deterministic ``n``-item subset via a
        seed-dependent rotation over the pool, so evolve.run's train (seed) and
        holdout (seed+10000) splits draw different orderings. For a genuinely
        disjoint holdout, provide enough distinct pairs (an honest caveat: a tiny
        pool cannot yield a clean holdout).
        """
        inp = np.asarray(inputs, np.float64)
        tgt = np.asarray(targets)
        if inp.shape[0] == 0 or tgt.shape[0] == 0:
            raise ValueError("from_pairs needs at least one (input, target) pair")
        if inp.shape[0] != tgt.shape[0]:
            raise ValueError(f"inputs ({inp.shape[0]}) and targets ({tgt.shape[0]}) "
                             "must have equal length")

        def _default_metric(final, target):
            if np.ndim(target) == 2:                      # image / region target
                return ops.psnr(_as_image(final, np.shape(target)), target)
            return 1.0 / (1.0 + abs(_as_count(final) - float(np.asarray(target).ravel()[0])))

        m = metric or _default_metric
        if unit is None:
            unit = "dB PSNR" if tgt.ndim == 3 else "score"

        def _make(n, size, seed, _inp=inp, _tgt=tgt):
            pool = _inp.shape[0]
            n = int(n)
            # ★A deterministic global shuffle (fixed base, so train/holdout/locked
            # index the SAME permutation) split into three DISJOINT bands keyed by
            # the seed's role (evolve.run draws train=seed, holdout=seed+10000,
            # locked=seed+20000, so seed//10000 mod 3 picks the band).  The old
            # `off = seed % pool` collapsed all three windows to the SAME frames
            # whenever pool divided 10000 — a silent train↔holdout↔locked leak that
            # made a train-overfit champion look like it "beat hand on a pure
            # holdout".  A pure 3-way split needs pool >= 3n; a smaller pool cannot
            # yield a clean holdout, so we refuse rather than leak silently.
            third = pool // 3
            perm = np.random.default_rng(0xC0FFEE).permutation(pool)
            band = (int(seed) // 10000) % 3          # 0=train,1=holdout,2=locked
            if third >= n:
                idx = perm[band * third:band * third + n]      # fully disjoint splits
            else:
                # pool too small for a pure 3-way split — a tiny pool cannot yield an
                # untouched holdout.  Best effort: give each split a DISTINCT band
                # offset so holdout/locked are no longer IDENTICAL to train (the old
                # `off = seed % pool` collapsed all three to the same frames whenever
                # pool divided 10000).  Overlap is now partial and disclosed, not a
                # silent total leak.  A pure holdout needs pool >= 3*n.
                import warnings
                warnings.warn(
                    f"from_pairs pool={pool} < 3*n={3 * n}: train/holdout/locked "
                    f"cannot be fully disjoint; splits overlap partially (holdout is "
                    f"not pure). Supply >= {3 * n} frames for a clean split.",
                    stacklevel=2)
                start = (band * max(1, third)) % pool
                idx = perm[[(start + i) % pool for i in range(n)]]
            return {"input": _inp[idx], "items": _tgt[idx]}

        return cls(name=name, unit=unit, make=_make, score_value=m,
                   hand_stages=(hand_stages or (lambda: [])), in_sort=in_sort)


# --- denoise ----------------------------------------------------------------- #
def _make_denoise(n, size, seed, noise=0.2):
    clean = _clean_stack(n, size, seed)
    noisy = np.clip(clean + np.random.default_rng(seed + 1).normal(0, noise, clean.shape), 0, 1)
    return {"input": noisy, "items": clean}


# --- edge -------------------------------------------------------------------- #
def _make_edge(n, size, seed, noise=0.05):
    clean = _clean_stack(n, size, seed)
    inp = np.clip(clean + np.random.default_rng(seed + 2).normal(0, noise, clean.shape), 0, 1)
    gt = np.stack([(np.hypot(ndimage.sobel(c, 1), ndimage.sobel(c, 0)) > 0.5).astype(np.float64) for c in clean])
    return {"input": inp, "items": gt}


# --- binarize ---------------------------------------------------------------- #
def _make_binarize(n, size, seed, noise=0.15):
    clean = _clean_stack(n, size, seed)
    inp = np.clip(clean + np.random.default_rng(seed + 3).normal(0, noise, clean.shape), 0, 1)
    return {"input": inp, "items": (clean > 0.5).astype(np.float64)}


# --- count ------------------------------------------------------------------- #
def _make_count(n, size, seed, noise=0.12):
    clean = _clean_stack(n, size, seed)
    inp = np.clip(clean + np.random.default_rng(seed + 4).normal(0, noise, clean.shape), 0, 1)
    counts = np.array([float(ndimage.label(c > 0.5)[1]) for c in clean])
    return {"input": inp, "items": counts}


# --- locate (template matching) ---------------------------------------------- #
def _template(size=11):
    yy, xx = np.mgrid[0:size, 0:size]; c = size // 2
    return ((xx - c) ** 2 + (yy - c) ** 2 <= (size // 2 - 1) ** 2).astype(np.float64)


def _make_locate(n, size, seed):
    rng = np.random.default_rng(seed + 5)
    T = _template(11); ops.set_match_template(T); rr = T.shape[0] // 2
    imgs, locs = [], []
    for _ in range(n):
        base = _synth(rng, size) * 0.4
        r = int(rng.integers(rr + 1, size - rr - 1)); c = int(rng.integers(rr + 1, size - rr - 1))
        base[r - rr:r + rr + 1, c - rr:c + rr + 1] = np.maximum(base[r - rr:r + rr + 1, c - rr:c + rr + 1], T)
        imgs.append(np.clip(base + rng.normal(0, 0.1, base.shape), 0, 1)); locs.append([float(r), float(c)])
    return {"input": np.stack(imgs), "items": np.array(locs)}


def _score_locate(final, gt):
    if isinstance(final, np.ndarray) and final.ndim == 1 and final.size >= 3:
        return 1.0 / (1.0 + float(np.hypot(final[1] - gt[0], final[2] - gt[1])))
    return 0.0


# --- locate_rot (shape-based, rotation invariant) ---------------------------- #
def _template_L(size=11):
    t = np.zeros((size, size), np.float64); t[2:size - 2, 2:4] = 1.0; t[size - 4:size - 2, 2:size - 2] = 1.0
    return t


def _make_locate_rot(n, size, seed):
    rng = np.random.default_rng(seed + 8)
    T = _template_L(11); ops.set_match_template(T); rr = T.shape[0] // 2
    imgs, locs = [], []
    for _ in range(n):
        base = _synth(rng, size) * 0.4
        tr = ndimage.rotate(T, rng.uniform(0, 360), reshape=False)
        r = int(rng.integers(rr + 1, size - rr - 1)); c = int(rng.integers(rr + 1, size - rr - 1))
        base[r - rr:r + rr + 1, c - rr:c + rr + 1] = np.maximum(base[r - rr:r + rr + 1, c - rr:c + rr + 1], tr)
        imgs.append(np.clip(base + rng.normal(0, 0.1, base.shape), 0, 1)); locs.append([float(r), float(c)])
    return {"input": np.stack(imgs), "items": np.array(locs)}


# --- classify (round vs elongated; OCR/decision basis) ----------------------- #
def _make_classify(n, size, seed):
    rng = np.random.default_rng(seed + 6); imgs, labels = [], []
    for _ in range(n):
        img = np.full((size, size), 0.15, np.float64)
        cx, cy = rng.integers(size // 3, 2 * size // 3, 2)
        if rng.random() < 0.5:  # circle
            r = int(rng.integers(size // 6, size // 4)); yy, xx = np.mgrid[0:size, 0:size]
            img[(xx - cx) ** 2 + (yy - cy) ** 2 <= r * r] = 0.9; lab = 1.0
        else:                    # elongated rectangle
            h = int(rng.integers(size // 6, size // 4)); w = max(2, h // 4)
            if rng.random() < 0.5:
                w, h = h, w
            img[max(0, cy - h // 2):cy + h // 2, max(0, cx - w // 2):cx + w // 2] = 0.9; lab = 0.0
        imgs.append(np.clip(img + rng.normal(0, 0.08, img.shape), 0, 1)); labels.append(lab)
    return {"input": np.stack(imgs), "items": np.array(labels)}


def _score_classify(final, gt):
    if _is_img(final):
        circ = 0.5
    elif isinstance(final, dict):
        return 0.0
    else:
        try:
            circ = float(np.asarray(final, np.float64).ravel()[0])
        except Exception:
            return 0.0
    return 1.0 if (1.0 if circ > 0.8 else 0.0) == gt else 0.0


# --- barcode-lite (count vertical bars) -------------------------------------- #
def _make_barcode(n, size, seed):
    rng = np.random.default_rng(seed + 7); imgs, counts = [], []
    for _ in range(n):
        img = np.full((size, size), 0.85, np.float64)
        nb = int(rng.integers(2, 8))
        xs = sorted(rng.choice(range(4, size - 4, 3), size=nb, replace=False))
        for x in xs:
            img[:, x:x + int(rng.integers(1, 3))] = 0.1
        imgs.append(np.clip(img + rng.normal(0, 0.05, img.shape), 0, 1)); counts.append(float(nb))
    return {"input": np.stack(imgs), "items": np.array(counts)}


# --- 3D volumes (CT/MRI-like voxel blobs) ------------------------------------ #
def _vol_stack(n, size, seed):
    rng = np.random.default_rng(seed)
    vols = []
    for _ in range(n):
        vol = np.zeros((size, size, size), np.float64)
        zz, yy, xx = np.mgrid[0:size, 0:size, 0:size]
        for _ in range(rng.integers(2, 5)):
            cz, cy, cx = rng.integers(0, size, 3); r = rng.integers(size // 8, size // 4)
            vol[(xx - cx) ** 2 + (yy - cy) ** 2 + (zz - cz) ** 2 <= r * r] = rng.uniform(0.5, 1.0)
        vols.append(vol)
    return np.stack(vols)


def _make_vol_denoise(n, size, seed, noise=0.15):
    clean = _vol_stack(n, 24, seed)
    noisy = np.clip(clean + np.random.default_rng(seed + 1).normal(0, noise, clean.shape), 0, 1)
    return {"input": noisy, "items": clean}


def _make_vol_count(n, size, seed, noise=0.1):
    clean = _vol_stack(n, 24, seed)
    inp = np.clip(clean + np.random.default_rng(seed + 2).normal(0, noise, clean.shape), 0, 1)
    counts = np.array([float(ndimage.label(c > 0.5)[1]) for c in clean])
    return {"input": inp, "items": counts}


# --------------------------------------------------------------------------- #
# 新 sort の課題(2026-09-01)                                                   #
#                                                                             #
# 型付きカタログを進化語彙へ橋渡し(backends_typed)した結果、点群 24 op /       #
# 信号 22 op が探索できるようになった。**しかし課題が image / volume しか       #
# 無かったため、その語彙は一度も報酬を受け取れなかった** — 進化ループを本番      #
# 規模で回して実測した所見: 採掘 205 候補のうち 145 件が「課題が受け付けない     #
# 入力型」で落ちた。語彙を広げたら課題も広げないと、増えた op は評価不能な       #
# まま探索空間を薄めるだけになる。                                             #
# --------------------------------------------------------------------------- #
def _points_stack(n, size, seed):
    """球面 + 平面のきれいな点群(n 個)。size は 1 雲あたりの点数の目安。"""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        m = max(64, int(size))
        half = m // 2
        # 球面(法線が全方向を向く)+ 平面(法線が一定)= 曲率の異なる 2 領域
        v = rng.standard_normal((half, 3))
        v /= np.linalg.norm(v, axis=1, keepdims=True).clip(1e-12)
        sphere = v * 3.0 + np.array([5.0, 5.0, 5.0])
        plane = np.column_stack([rng.uniform(0, 10, m - half),
                                 rng.uniform(0, 10, m - half),
                                 np.zeros(m - half)])
        out.append(np.vstack([sphere, plane]))
    return out


def _make_points_denoise(n, size, seed, noise=0.25):
    """点群デノイズ: ガウスノイズ + 外れ値を載せた雲 → 元の雲に近づける。

    指標は clean への Chamfer 距離(小さいほど良い)を 1/(1+d) にしたもの。
    外れ値を入れるのは、平滑化だけでなく**除去**が要る課題にするため。
    """
    clean = _points_stack(n, size, seed)
    rng = np.random.default_rng(seed + 1)
    noisy = []
    for c in clean:
        p = c + rng.normal(0, noise, c.shape)
        k = max(1, len(c) // 20)                      # 5% を外れ値に
        p = np.vstack([p, rng.uniform(-5, 15, (k, 3))])
        noisy.append(p)
    return {"input": noisy, "items": clean}


def _score_points(final, clean):
    """点群の一致度。点群を返さなかった場合は 0(型を外したら報酬ゼロ)。"""
    import metrics3d
    p = np.asarray(final) if isinstance(final, np.ndarray) else None
    if p is None or p.ndim != 2 or p.shape[1] != 3 or len(p) < 1:
        return 0.0
    try:
        return 1.0 / (1.0 + float(metrics3d.chamfer_distance(p, clean)))
    except Exception:                                  # noqa: BLE001 - 空/非有限
        return 0.0


def _signal_stack(n, size, seed):
    """減衰振動 + 高調波のきれいな 1-D 信号。"""
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(n):
        m = max(64, int(size))
        t = np.linspace(0, 8 * np.pi, m)
        f1, f2 = rng.uniform(0.8, 1.2), rng.uniform(2.5, 3.5)
        y = (np.sin(f1 * t) * np.exp(-t / (6 * np.pi))
             + 0.3 * np.sin(f2 * t + rng.uniform(0, np.pi)))
        out.append(y)
    return out


def _make_signal_denoise(n, size, seed, noise=0.25):
    """1-D デノイズ: ノイズ付き信号 → 元の波形。指標は PSNR 相当。"""
    clean = _signal_stack(n, size, seed)
    rng = np.random.default_rng(seed + 1)
    return {"input": [c + rng.normal(0, noise, c.shape) for c in clean],
            "items": clean}


def _score_signal(final, clean):
    """1-D 波形の一致度。長さが変わった場合は比較可能な範囲だけで測る。

    間引き系 op が「短くして楽をする」のを防ぐため、長さが変わったら
    **その比率でペナルティ**を掛ける(黙って有利にしない)。
    """
    y = np.asarray(final, np.float64).ravel() if isinstance(final, np.ndarray) else None
    if y is None or y.size < 2 or not np.isfinite(y).all():
        return 0.0
    m = min(len(y), len(clean))
    err = float(np.mean((y[:m] - clean[:m]) ** 2))
    if not np.isfinite(err):
        return 0.0
    base = 1.0 / (1.0 + err)
    return base * (m / len(clean))                     # 短くしたら比例で減点



# --------------------------------------------------------------------------- #
# 新しい型の課題(2026-09-01)                                                   #
#                                                                             #
# 語彙は 742 -> 824 op へ広げたのに、**課題は 12 件すべてが古い型**のままだった。
# 実際 evolve_loop を回すと落選理由の筆頭が「課題が受け付けない入力型」で、
# 光子計数もライトフィールドも**進化が一度も使えない**状態だった。
# 「増やす経路(拡散)と通さない規律(ゲート)を同じループに置く」という設計は、
# **その語彙を使える仕事が無いと空回りする** — ここはその穴を塞ぐ。
#
# どちらも真値は閉形式で作れる(前方モデルから合成しているので、答えを
# 知ったうえで入力を作れる)。手の基準線も既存 op で用意する。
# --------------------------------------------------------------------------- #
def _make_photon_denoise(n, size, seed):
    """光子制限のヒストグラム → **信号成分だけ**の期待形。

    入力は「既知距離の復路 + 背景光」を Poisson 標本化した実データと同じ形。
    目標は背景を含まない雑音なしの信号成分なので、**背景の推定と除去が
    本質的に効く**課題になる(答えを知って作っているので真値は厳密)。
    """
    import photoncount
    rng = np.random.default_rng(seed)
    inp, tgt = [], []
    for i in range(n):
        d = float(rng.uniform(0.6, 3.2))
        sig = float(rng.uniform(200.0, 1500.0))
        amb = float(rng.uniform(50.0, 400.0))
        kw = dict(distance_m=d, bins=256, bin_ps=100.0, irf_fwhm_ps=500.0)
        inp.append(photoncount.tcspc_simulate(
            signal_photons=sig, ambient_photons=amb, seed=seed + i, **kw))
        tgt.append(photoncount.tcspc_simulate(
            signal_photons=sig, ambient_photons=0.0, noise=False, **kw))
    return {"input": inp, "items": tgt}


def _score_photon(final, clean):
    """形の一致だけを見る(全体のスケールは問わない)。

    カウントの絶対値は光量で動くので、**面積で正規化した形**で比べる。
    そうしないと「全部 0 にする」や「定数倍する」が得をする。長さを変える
    op が楽をするのを防ぐため、``_score_signal`` と同じ比例減点を掛ける。
    """
    y = np.asarray(final, np.float64).ravel() if isinstance(final, np.ndarray) else None
    if y is None or y.size < 2 or not np.isfinite(y).all():
        return 0.0
    m = min(len(y), len(clean))
    a, b = y[:m], np.asarray(clean, np.float64)[:m]
    sa, sb = float(a.sum()), float(b.sum())
    if not np.isfinite(sa) or sa <= 0.0 or sb <= 0.0:
        return 0.0
    err = float(np.mean((a / sa - b / sb) ** 2)) * float(m) ** 2
    if not np.isfinite(err):
        return 0.0
    return (1.0 / (1.0 + err)) * (m / len(clean))


def _make_lf_slope(n, size, seed):
    """ライトフィールド → **視差スロープ地図**(既知)。

    ``lf_synthesize`` は層ごとに既知のスロープを置いて合成するので、真値の
    スロープ地図がそのまま返る。深度推定の 2 経路(焦点掃引 / EPI 傾き)が
    どちらも語彙にあり、**偏りの違いが実測で出ている**題材でもある。
    """
    import lightfield
    rng = np.random.default_rng(seed)
    inp, tgt = [], []
    for i in range(n):
        lo = float(rng.uniform(-1.5, 0.0))
        hi = float(rng.uniform(0.5, 2.0))
        lf, slope = lightfield.lf_synthesize(
            (lo, hi), angular=(5, 5), shape=(32, 32), seed=seed + i)
        inp.append(lf)
        tgt.append(np.asarray(slope, np.float64))
    return {"input": inp, "items": tgt}


def _score_lf_slope(final, truth):
    """スロープ地図の一致度。**尺度と定数のずれは許す**(相関で測る)。

    経路によって単位が px/view だったり焦点位置だったりするので、絶対値を
    要求すると「正しい形を出しているのに 0 点」になる。形が合っているかを
    相関で測り、負の相関(符号が逆)は 0 に丸める。
    """
    a = np.asarray(final, np.float64) if isinstance(final, np.ndarray) else None
    if a is None or a.ndim != 2 or not np.isfinite(a).all():
        return 0.0
    b = np.asarray(truth, np.float64)
    if a.shape != b.shape:
        return 0.0
    a = a - a.mean()
    b = b - b.mean()
    da, db = float(np.sqrt((a * a).sum())), float(np.sqrt((b * b).sum()))
    if da <= 1e-12 or db <= 1e-12:            # 定数を返したら 0(相関が定義できない)
        return 0.0
    return max(0.0, float((a * b).sum() / (da * db)))



def _make_specular_removal(n, size, seed):
    """光沢のある色画像 → **鏡面成分を除いた拡散のみの画像**。

    同じ法線・同じアルベド・同じ光源で ``specular=0`` を描けば、それが
    「ハイライトが無かったら見えていたはずの絵」= 厳密な真値になる。
    光沢面の検査で「テカりを消してから測る」という現場の手順そのもの。

    **アルベドを場所で変える**のが要点。一様な材質なら二色性分離は機械精度で
    厳密に戻るので(実測 5.0e-16)、課題として頭打ちになり進化の余地が無い
    (最初にそう作って手が 0.9997 になった)。実際の部品はテクスチャを持ち、
    そこが分離の仮定が崩れる場所でもある ―― 難しさの出どころを本物に合わせる。
    """
    import photometric
    import specularity
    rng = np.random.default_rng(seed)
    inp, tgt = [], []
    for i in range(n):
        r = np.arange(32)
        zz = 6.0 * np.exp(-((r[:, None] - 16.0) ** 2 + (r[None, :] - 16.0) ** 2)
                          / float(rng.uniform(120.0, 320.0)))
        nrm = photometric.surface_normals(zz)
        # 場所で色が変わるアルベド(縞と斑)。一様色だと分離が厳密すぎる
        base = rng.uniform(0.25, 0.9, size=3)
        stripe = 0.5 + 0.5 * np.sin(r[None, :] * float(rng.uniform(0.3, 0.9)))
        blob = np.exp(-((r[:, None] - float(rng.uniform(8, 24))) ** 2
                        + (r[None, :] - float(rng.uniform(8, 24))) ** 2) / 60.0)
        tex = np.clip(0.55 + 0.45 * stripe - 0.3 * blob, 0.15, 1.0)
        alb = np.clip(base[None, None, :] * tex[:, :, None], 0.05, 1.0)
        lit = (float(rng.uniform(-0.4, 0.4)), float(rng.uniform(-0.4, 0.4)), 1.0)
        sh = float(rng.uniform(16.0, 64.0))
        kw = dict(albedo_rgb=alb, light=lit, shininess=sh)
        # 入力にだけセンサ雑音を載せる(目標は雑音なしの拡散画像)。実写には
        # 必ずあるものであり、かつ二色性分離の rank ガードが敏感な条件でもある
        # (実測: 雑音 1% で rank 比 0.0348 / 2% で 0.0694)。雑音が無いと手の
        # 基準線が 0.983 まで行って余地が無く、逆に 2% では手が恒等を
        # 下回った(0.5008 対 0.5103)。0.4% が「効くが壊れない」帯。
        img = specularity.dichromatic_render(
            nrm, specular=float(rng.uniform(0.3, 0.7)), **kw)
        img = np.clip(img + rng.normal(0.0, 0.004, img.shape), 0.0, None)
        inp.append(img)
        tgt.append(specularity.dichromatic_render(nrm, specular=0.0, **kw))
    return {"input": inp, "items": tgt}


def _score_diffuse(final, truth):
    """拡散画像との一致。色 (H,W,3) でも輝度 (H,W) でも比べられるようにする。

    経路によって色を保つ op と輝度へ落とす op があるので、輝度に揃えてから
    測る(色のまま返す方が情報は多いが、**輝度で合っていないものは色でも
    合っていない**ので下限としては正しい)。形が違えば 0。
    """
    a = np.asarray(final, np.float64) if isinstance(final, np.ndarray) else None
    if a is None or not np.isfinite(a).all():
        return 0.0
    b = np.asarray(truth, np.float64)
    if a.ndim == 3 and a.shape[2] == 3:
        a = a.mean(axis=2)
    if b.ndim == 3 and b.shape[2] == 3:
        b = b.mean(axis=2)
    if a.ndim != 2 or a.shape != b.shape:
        return 0.0
    return 1.0 / (1.0 + float(np.mean((a - b) ** 2)) * 100.0)


def _make_vibration_map(n, size, seed):
    """振動している場所の地図。**帯域内で揺れている領域**を当てる課題。

    振幅の違う 2 本のクリップを空間マスクで混ぜるので、真値のマスクが
    そのまま答えになる。回転機械の「どこが振れているか」に対応する。
    """
    import motionmag
    rng = np.random.default_rng(seed)
    inp, tgt = [], []
    for i in range(n):
        r0 = int(rng.integers(6, 14))
        c0 = int(rng.integers(6, 14))
        mask = np.zeros((32, 32))
        mask[r0:r0 + 14, c0:c0 + 14] = 1.0
        kw = dict(shape=(32, 32), frames=32, frequency_hz=4.0, fps=32.0,
                  direction_deg=float(rng.uniform(0, 180)), seed=seed + i)
        hot = motionmag.synthesize_translation(amplitude_px=0.45, **kw)
        cold = motionmag.synthesize_translation(amplitude_px=0.02, **kw)
        inp.append(hot * mask[None, :, :] + cold * (1.0 - mask[None, :, :]))
        tgt.append(mask)
    return {"input": inp, "items": tgt}


def _score_vibration_map(final, mask):
    """揺れている領域の当て具合。**尺度は問わず形だけ**を相関で測る。

    帯域パワーは単位が経路依存(振幅の 2 乗だったり dB だったり)なので、
    絶対値を要求すると正しい形を出しても 0 点になる。定数を返したら 0。
    """
    a = np.asarray(final, np.float64) if isinstance(final, np.ndarray) else None
    if a is None or a.ndim != 2 or not np.isfinite(a).all():
        return 0.0
    b = np.asarray(mask, np.float64)
    if a.shape != b.shape:
        return 0.0
    a = a - a.mean()
    b = b - b.mean()
    da, db = float(np.sqrt((a * a).sum())), float(np.sqrt((b * b).sum()))
    if da <= 1e-12 or db <= 1e-12:
        return 0.0
    return max(0.0, float((a * b).sum() / (da * db)))


PROBLEMS: dict[str, Problem] = {
    "denoise": Problem("denoise", "dB PSNR", _make_denoise,
                       lambda f, tgt: ops.psnr(_as_image(f, tgt.shape), tgt),
                       lambda: [ops.stage("gaussian", (1.0 - 0.3) / 2.7, 0.0)]),
    "edge": Problem("edge", "F1", _make_edge,
                    lambda f, gt: _f1(_as_binary(f, gt.shape), gt),
                    lambda: [ops.stage("sobel_mag", 0.0, 0.0), ops.stage("threshold", 0.2, 0.0)]),
    "binarize": Problem("binarize", "IoU", _make_binarize,
                        lambda f, gt: _iou(_as_binary(f, gt.shape), gt),
                        lambda: [ops.stage("gaussian", 0.3, 0.0), ops.stage("otsu", 0.0, 0.0)]),
    "count": Problem("count", "1/(1+err)", _make_count,
                     lambda f, gtc: 1.0 / (1.0 + abs(_as_count(f) - gtc)),
                     lambda: [ops.stage("gaussian", 0.3, 0.0), ops.stage("otsu", 0.0, 0.0),
                              ops.stage("remove_small", 0.2, 0.0), ops.stage("blob_count", 0.0, 0.0)]),
    "locate": Problem("locate", "1/(1+px)", _make_locate, _score_locate,
                      lambda: [ops.stage("gaussian", 0.2, 0.0), ops.stage("ncc_locate", 0.0, 0.0)]),
    "locate_rot": Problem("locate_rot", "1/(1+px)", _make_locate_rot, _score_locate,
                          lambda: [ops.stage("gaussian", 0.2, 0.0), ops.stage("shape_locate", 0.0, 0.0)]),
    "classify": Problem("classify", "accuracy", _make_classify, _score_classify,
                        lambda: [ops.stage("gaussian", 0.2, 0.0), ops.stage("otsu", 0.0, 0.0),
                                 ops.stage("select_largest", 0.0, 0.0), ops.stage("classify_shape", 0.0, 0.0)]),
    "barcode": Problem("barcode", "1/(1+err)", _make_barcode,
                       lambda f, gt: 1.0 / (1.0 + abs(_as_count(f) - gt)),
                       lambda: [ops.stage("decode_barcode", 0.5, 0.0)]),
    "vol_denoise": Problem("vol_denoise", "dB PSNR", _make_vol_denoise,
                           lambda f, tgt: ops.psnr(np.clip(f, 0, 1), tgt)
                           if isinstance(f, np.ndarray) and f.ndim == 3 else 0.0,
                           lambda: [ops.stage("vol_gaussian", 0.26, 0.0)], in_sort="volume"),
    "vol_count": Problem("vol_count", "1/(1+err)", _make_vol_count,
                         lambda f, gt: 1.0 / (1.0 + abs(_as_count(f) - gt)),
                         lambda: [ops.stage("vol_gaussian", 0.3, 0.0), ops.stage("vol_threshold", 0.4, 0.0),
                                  ops.stage("vol_count", 0.0, 0.0)], in_sort="volume"),
    # 橋渡しで開いた新 sort の課題。hand baseline は「その分野で標準的な 1 手」
    # (点群 = 統計的外れ値除去、信号 = ガウス平滑)であって最強手ではない。
    # ゲートはこれを超えることを要求するので、baseline が弱すぎると意味が無い
    # 一方、強すぎると正当な発見も落ちる。標準手に置くのが公平。
    "points_denoise": Problem(
        "points_denoise", "1/(1+chamfer)", _make_points_denoise, _score_points,
        lambda: [ops.stage("tb_statistical_outlier_removal", 0.5, 0.5)],
        in_sort="points"),
    "signal_denoise": Problem(
        "signal_denoise", "1/(1+mse)", _make_signal_denoise, _score_signal,
        lambda: [ops.stage("tb_smooth_funct_1d_gauss", 0.5, 0.5)],
        in_sort="signal"),
    # 光子計数: 背景光を含む Poisson ヒストグラム → 信号成分の形。
    # 手の基準線は背景除去 1 段(この課題で最も素直な一手)。
    "photon_denoise": Problem(
        "photon_denoise", "1/(1+mse of shape)", _make_photon_denoise, _score_photon,
        lambda: [ops.stage("tb_tcspc_background_subtract", 0.5, 0.5)],
        in_sort="counts"),
    # ライトフィールド: 4-D 光場 → 視差スロープ地図。
    #
    # 手の基準線は最初 ``tb_lf_depth_from_focus`` を置いたが、昇格ゲートが
    # 「既存 op 単体の最良」を全探索した結果 **``tb_lf_epi_slope`` が 0.4694 で
    # 焦点掃引法の 0.2127 を 2 倍以上上回る**と実測で示した。弱い方を手として
    # 置くと課題が実際より易しく見えるので、強い方へ差し替えた。
    # (EPI 傾き法には sigma によって最大 27% 過小に出るという別の実測があり、
    # 相関で測る本課題ではその尺度ずれが効かない ― 指標の選び方まで含めて
    # 「何を測っているか」が結果を決める例。)
    "lf_slope": Problem(
        "lf_slope", "corr", _make_lf_slope, _score_lf_slope,
        lambda: [ops.stage("tb_lf_epi_slope", 0.5, 0.5)],
        in_sort="lightfield"),
    # 鏡面分離: 光沢のある色画像 → 拡散のみの画像(ハイライトが無ければ
    # 見えていたはずの絵)。手の基準線は二色性分離 1 段。
    "specular_removal": Problem(
        "specular_removal", "1/(1+100*mse)", _make_specular_removal, _score_diffuse,
        lambda: [ops.stage("tb_specular_diffuse_split", 0.5, 0.5)],
        in_sort="rgbimage"),
    # 振動地図: 帯域内で揺れている領域を当てる。手の基準線は帯域パワー 1 段。
    "vibration_map": Problem(
        "vibration_map", "corr", _make_vibration_map, _score_vibration_map,
        lambda: [ops.stage("tb_temporal_band_power", 0.5, 0.5)],
        in_sort="video"),
}


def trivial_stages() -> list:
    return []
