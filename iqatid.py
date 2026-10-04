# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""画質評価の公開の正解で指標を門にする(iqatid、2026-10-04)。

TID2013(Ponomarenko ほか、Tampere Image Database 2013)は 25 枚の参照画像 × 24 種の歪み × 5 段 = 3,000 枚の歪み画像に、
971 人の観察者の対比較から得た MOS(平均意見スコア、0〜9)を付けた公開データで、配布物には作者が計算した PSNR / SSIM /
MS-SSIM / FSIM / VIF ほか 14 指標の値と、公表の順位相関表(Spearman / Kendall)が同梱されている。本モジュールはそれを
**Fullseye の指標(imgmetrics.psnr / ssim / ms_ssim)の門**にする:

1. :func:`luma_limited_u8` —— 作者の「輝度」= BT.601 の limited range Y′(16〜235、整数)。作者値 psnr.txt / ssim.txt が
   この規約で 4 桁一致した(ページにも readme にも明記は無く、2026-10-04 に実測で特定)。
2. :func:`rank_data` / :func:`rank_spearman` / :func:`rank_kendall_b` —— 順位相関。同順位は平均順位、Kendall は τ_b。
   公表表 14 本がこの定義で全て 3 桁一致(τ_a だと FSIM・MSSIM・SSIM・FSIMc で 3 桁目が外れる)。
3. :func:`tid2013_published` —— 公表表(14 指標 × SROCC/KROCC)をそのまま持つ。
4. :func:`tid2013_index` / :func:`tid2013_metric_values` —— 配布物を読む(件数・名前集合を検証、違えば ValueError)。
5. :func:`tid2013_evaluate` / :func:`tid2013_compare` / :func:`tid2013_by_distortion` —— 自前の指標を 3,000 組に当て、
   作者値との行ごとの差と、MOS との順位相関を公表値と比べ、歪み種ごとに割る。

正直に: Fullseye の SSIM が作者値と 4 桁一致するのは、**作者と同じ原実装(Wang 2004 の ssim_index.m: 11×11 ガウス σ1.5、縁を落とす、
ダウンサンプル無し)の規約を踏んでいる**からで、SSIM の性能(SROCC 0.637、14 本中 10 位)の話ではない。画像と MOS は
**repo に入れない**(配布条件は教育・研究目的のみ、改変版の再配布は著者許可)—— 実データの門は環境変数 ``FULLSEYE_TID2013_DATA``
があるときだけ走り、CI では合成の門だけ。FSIM / FSIMc / VIF / PSNR-HVS 系は Fullseye に未実装で、公表値だけを表に載せる。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

import numpy as np

__all__ = [
    "TID2013_URL", "TID2013_DISTORTIONS", "TID2013_SUBSETS", "TID2013_N_REF", "TID2013_N_TYPES", "TID2013_N_LEVELS",
    "luma_limited_u8", "rank_data", "rank_spearman", "rank_kendall_b", "tid2013_published", "tid2013_root",
    "tid2013_index", "tid2013_metric_values", "tid2013_evaluate", "tid2013_compare", "tid2013_by_distortion",
]

TID2013_URL = "https://www.ponomarenko.info/tid2013.htm"
TID2013_N_REF, TID2013_N_TYPES, TID2013_N_LEVELS = 25, 24, 5
#: 歪み種 24(配布物 readme の TABLE I の文言をそのまま。番号 = ファイル名の YY)
TID2013_DISTORTIONS = (
    "Additive Gaussian noise",
    "Additive noise in color components is more intensive than additive noise in the luminance component",
    "Spatially correlated noise", "Masked noise", "High frequency noise", "Impulse noise", "Quantization noise",
    "Gaussian blur", "Image denoising", "JPEG compression", "JPEG2000 compression", "JPEG transmission errors",
    "JPEG2000 transmission errors", "Non eccentricity pattern noise", "Local block-wise distortions of different intensity",
    "Mean shift (intensity shift)", "Contrast change", "Change of color saturation", "Multiplicative Gaussian noise",
    "Comfort noise", "Lossy compression of noisy images", "Image color quantization with dither", "Chromatic aberrations",
    "Sparse sampling and reconstruction",
)
#: spearman.exe / kendall.exe の既定の部分集合(readme TABLE II、歪み種の番号 1 始まり)
TID2013_SUBSETS: Dict[str, Tuple[int, ...]] = {
    "Noise": (1, 2, 3, 4, 5, 6, 7, 8, 9, 19, 21),
    "Actual": (1, 3, 4, 5, 6, 8, 9, 10, 11, 19, 21),
    "Simple": (1, 8, 10),
    "Exotic": (12, 13, 14, 15, 16, 17, 20, 23, 24),
    "New": (18, 19, 20, 21, 22, 23, 24),
    "Color": (2, 7, 10, 18, 22, 23),
    "Full": tuple(range(1, 25)),
}
_ENV_DATA = "FULLSEYE_TID2013_DATA"


# ----------------------------------------------------------------------------------------------------------------------
# 1. 作者の輝度規約
def luma_limited_u8(rgb) -> np.ndarray:
    """RGB (H, W, 3) uint8 → Y′ = round(16 + (65.481 R + 128.553 G + 24.966 B) / 255) の uint8 (H, W)。

    ITU-R BT.601 の **limited range**(studio swing)の輝度。黒 (0,0,0) → 16、白 (255,255,255) → 235。full range の
    Y = 0.299 R + 0.587 G + 0.114 B(黒 0・白 255)とは**別の量**で、PSNR(peak 255 のまま)は 20 log10(255/219) = 1.321 dB
    低く出る。TID2013 の作者値 psnr.txt(「luminance component」)と ssim.txt は **この規約で 4 桁一致**した(10 組、2026-10-04。
    full range だと PSNR −1.3 dB・SSIM 最大 0.05 ずれ、丸めないと PSNR が +0.002〜0.07 dB ずれる)。ページにも readme にも
    どの輝度かは書かれておらず、実測で特定した規約。丸めは ``np.round``(半偶数)。輝度が **ちょうど k.5** に落ちる画素は丸めの向きが
    算術の順序で変わり、作者と 1 LSB 食い違うことがある(TID2013 では参照 I12 の 28 画素。彩度変化 5 組で作者 = 完全一致、ここでは 86.6 dB。
    半切り上げでも float32 でも揃わない)。PSNR が 60 dB を超える領域だけの話で、それ以外の 2,995 組は 0.0005 dB 以内。
    **Raises** ``ValueError``: 形が (H, W, 3) でない、dtype が uint8 でない。"""
    a = np.asarray(rgb)
    if a.ndim != 3 or a.shape[2] != 3:
        raise ValueError("luma_limited_u8: rgb must be (H, W, 3), got %r" % (a.shape,))
    if a.dtype != np.uint8:
        raise ValueError("luma_limited_u8: rgb must be uint8 (8-bit BMP/PNG pixels), got %s" % a.dtype)
    r, g, b = (a[..., i].astype(np.float64) for i in range(3))
    y = 16.0 + (65.481 * r + 128.553 * g + 24.966 * b) / 255.0
    return np.round(y).astype(np.uint8)        # 16 ≤ y ≤ 235 なので丸めても 8 bit に収まる


# ----------------------------------------------------------------------------------------------------------------------
# 2. 順位相関(scipy を使わない)
def _vec(x, name: str, allow_inf: bool = False) -> np.ndarray:
    v = np.asarray(x, dtype=np.float64).ravel()
    if v.size < 2:
        raise ValueError("%s: need at least 2 values, got %d" % (name, v.size))
    if np.any(np.isnan(v)) or (not allow_inf and not np.all(np.isfinite(v))):
        raise ValueError("%s: values must be finite%s" % (name, " (±inf allowed, nan not)" if allow_inf else ""))
    return v


def _ordinal(v: np.ndarray) -> np.ndarray:
    """±inf を「有限の最大 + 1 / 最小 − 1」に置く(順位は変わらない)。inf − inf = nan が同順位の数え落ちになるのを防ぐ。
    PSNR の完全一致(inf、TID2013 では輝度が変わらない彩度変化の 106 組)を順位相関に乗せるため。"""
    if np.all(np.isfinite(v)):
        return v
    fin = v[np.isfinite(v)]
    hi = float(fin.max()) + 1.0 if fin.size else 1.0
    lo = float(fin.min()) - 1.0 if fin.size else -1.0
    return np.where(v == np.inf, hi, np.where(v == -np.inf, lo, v))


def rank_data(x) -> np.ndarray:
    """平均順位(1 始まり)。同順位は同じ値の順位の平均(scipy.stats.rankdata の 'average' と同じ定義)。

    例: [10, 20, 20, 30] → [1, 2.5, 2.5, 4]。±inf は最大 / 最小の順位(互いに同順位)。**Raises** ``ValueError``: 長さ 2 未満・nan。"""
    v = _ordinal(_vec(x, "rank_data", allow_inf=True))
    order = np.argsort(v, kind="stable")
    ranks = np.empty(v.size, dtype=np.float64)
    ranks[order] = np.arange(1, v.size + 1, dtype=np.float64)
    _u, inv, cnt = np.unique(v, return_inverse=True, return_counts=True)
    sums = np.bincount(inv.ravel(), weights=ranks)
    return sums[inv.ravel()] / cnt[inv.ravel()]


def rank_spearman(x, y) -> float:
    """Spearman の順位相関 ρ = 平均順位どうしの Pearson 相関(同順位があっても正しい形。古典式 1 − 6Σd²/(n(n²−1)) は
    同順位が無いときだけ一致)。単調増加で 1、反転で −1。どちらかが定数なら ``nan``(順位の分散が 0、相関は定義されない)。
    ±inf は順序だけ使う(完全一致の PSNR = inf を落とさない)。**Raises** ``ValueError``: 長さ不一致・2 未満・nan。"""
    a, b = _vec(x, "rank_spearman", allow_inf=True), _vec(y, "rank_spearman", allow_inf=True)
    if a.size != b.size:
        raise ValueError("rank_spearman: x and y must have the same length, got %d and %d" % (a.size, b.size))
    ra, rb = rank_data(a), rank_data(b)
    ra -= ra.mean()
    rb -= rb.mean()
    d = float(np.sqrt((ra * ra).sum() * (rb * rb).sum()))
    return float("nan") if d == 0.0 else float((ra * rb).sum() / d)


def rank_kendall_b(x, y, chunk: int = 512) -> float:
    """Kendall の τ_b(同順位補正あり)= (C − D) / sqrt((n0 − n1)(n0 − n2))。

    C / D = 一致 / 不一致の対の数、n0 = n(n−1)/2、n1 / n2 = x 側 / y 側で同順位の対の数。O(n²) を ``chunk`` 行ずつの
    放送で数える(n = 3000 で 4.5e6 対、数秒)。単調増加で 1、反転で −1。どちらかが定数なら ``nan``。TID2013 の公表 Kendall は
    τ_b(14 本が 3 桁一致、τ_a だと 4 本外れる)。±inf は順序だけ使う。**Raises** ``ValueError``: 長さ不一致・2 未満・nan。"""
    a, b = _vec(x, "rank_kendall_b", allow_inf=True), _vec(y, "rank_kendall_b", allow_inf=True)
    if a.size != b.size:
        raise ValueError("rank_kendall_b: x and y must have the same length, got %d and %d" % (a.size, b.size))
    a, b = _ordinal(a), _ordinal(b)
    n = a.size
    conc = disc = tx = ty = 0
    idx = np.arange(n)
    for s in range(0, n, max(1, int(chunk))):
        e = min(n, s + max(1, int(chunk)))
        sx = np.sign(a[s:e, None] - a[None, :])
        sy = np.sign(b[s:e, None] - b[None, :])
        upper = idx[s:e, None] < idx[None, :]              # 対 (i, j), i < j だけ数える
        prod = sx * sy
        conc += int(np.count_nonzero((prod > 0) & upper))
        disc += int(np.count_nonzero((prod < 0) & upper))
        tx += int(np.count_nonzero((sx == 0) & upper))     # x 側の同順位の対(xy 同時同順位も含む)
        ty += int(np.count_nonzero((sy == 0) & upper))
    n0 = n * (n - 1) // 2
    den = float(np.sqrt(float(n0 - tx) * float(n0 - ty)))
    return float("nan") if den == 0.0 else float((conc - disc) / den)


# ----------------------------------------------------------------------------------------------------------------------
# 3. 公表値
def tid2013_published() -> Dict[str, Tuple[float, float]]:
    """公表の順位相関表 {metric: (SROCC, KROCC)}(14 本)。

    出典: https://www.ponomarenko.info/tid2013.htm(Last changed 2015-03-23)の「Ranking of compared metrics in accordance with
    Spearman / Kendall correlation with MOS」、配布物 readme の TABLE III / IV と同一。鍵は配布物 ``metrics_values/<鍵>.txt`` の
    ファイル名(小文字)。**同梱の作者値と mos.txt から、Spearman = 平均順位・Kendall = τ_b で 14 本すべて 3 桁一致**
    (|差| ≤ 0.0005 / 0.00044、2026-10-04)。ページ冒頭の「PSNR … is 0.69」と使用例の「FSIMc Full : 0.666」は表と食い違う
    (前者は TID2008 の名残、後者は τ_a 0.66626 に一致 —— どちらも推測)ので門には使わない。"""
    return {
        "fsimc": (0.851, 0.667), "psnrha": (0.819, 0.643), "psnrhma": (0.813, 0.632), "fsim": (0.801, 0.630),
        "mssim": (0.787, 0.608), "psnrc": (0.687, 0.496), "vsnr": (0.681, 0.508), "psnrhvs": (0.654, 0.508),
        "psnr": (0.640, 0.470), "ssim": (0.637, 0.464), "nqm": (0.635, 0.466), "psnrhvsm": (0.625, 0.482),
        "vifp": (0.608, 0.457), "wsnr": (0.580, 0.446),
    }


# ----------------------------------------------------------------------------------------------------------------------
# 4. 配布物を読む
def tid2013_root(root=None) -> Optional[Path]:
    """配布物の展開先。``root`` が無ければ環境変数 ``FULLSEYE_TID2013_DATA``。どちらも無い・``mos_with_names.txt`` が無ければ ``None``
    (呼び手は skip する —— データは repo に無い)。"""
    r = root if root is not None else os.environ.get(_ENV_DATA, "").strip()
    if not r:
        return None
    p = Path(r)
    return p if (p / "mos_with_names.txt").is_file() else None


def _ci_file(d: Path, name: str) -> Optional[Path]:
    """大文字小文字を無視して d/name を探す(配布物は I01.BMP / i25.bmp / PSNR.txt / FSIMc.txt と不揃い)。"""
    if not d.is_dir():
        return None
    low = name.lower()
    for p in d.iterdir():
        if p.name.lower() == low:
            return p
    return None


def tid2013_index(root) -> dict:
    """``mos_with_names.txt`` を読んで組の台帳を返す。

    返り値: ``names``(3000、配布物の綴りのまま)、``mos`` (3000,)、``ref`` / ``dist_type`` / ``level``(各 int 配列、1 始まり)、
    ``ref_files``(参照 25 枚のパス、番号順)、``dist_files``(歪み 3000 枚のパス、台帳の順)、``root``。
    作者値 ``metrics_values/*.txt`` には名前が無く **この台帳の順**(i01_01_1 … i25_24_5)で並ぶので、順序はこの関数が握る。
    **Raises** ``ValueError``: 行数 ≠ 3000、名前が iXX_YY_Z.bmp の形でない、名前集合が ``distorted_images/`` の BMP と一致しない
    (大文字小文字無視)、参照 25 枚が揃わない、MOS が [0, 9] の外。"""
    rt = Path(root)
    f = rt / "mos_with_names.txt"
    if not f.is_file():
        raise ValueError("tid2013_index: %s not found (FULLSEYE_TID2013_DATA should point at the extracted tid2013/ folder)" % f)
    names: List[str] = []
    mos: List[float] = []
    for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
        if not ln.strip():
            continue
        parts = ln.split()
        if len(parts) != 2:
            raise ValueError("tid2013_index: expected '<mos> <name>' per line, got %r" % ln)
        mos.append(float(parts[0]))
        names.append(parts[1])
    n_exp = TID2013_N_REF * TID2013_N_TYPES * TID2013_N_LEVELS
    if len(names) != n_exp:
        raise ValueError("tid2013_index: expected %d lines, got %d" % (n_exp, len(names)))
    ref = np.zeros(n_exp, np.int64)
    typ = np.zeros(n_exp, np.int64)
    lev = np.zeros(n_exp, np.int64)
    for k, nm in enumerate(names):
        s = nm.lower()
        ok = (len(s) == len("ixx_yy_z.bmp") and s[0] == "i" and s[3] == "_" and s[6] == "_" and s.endswith(".bmp")
              and s[1:3].isdigit() and s[4:6].isdigit() and s[7].isdigit())
        if not ok:
            raise ValueError("tid2013_index: name %r is not of the form iXX_YY_Z.bmp" % nm)
        ref[k], typ[k], lev[k] = int(s[1:3]), int(s[4:6]), int(s[7])
    if not (ref.min() >= 1 and ref.max() <= TID2013_N_REF and typ.min() >= 1 and typ.max() <= TID2013_N_TYPES
            and lev.min() >= 1 and lev.max() <= TID2013_N_LEVELS):
        raise ValueError("tid2013_index: reference/type/level out of range")
    m = np.asarray(mos, np.float64)
    if not (np.all(np.isfinite(m)) and m.min() >= 0.0 and m.max() <= 9.0):
        raise ValueError("tid2013_index: MOS must lie in [0, 9]")
    ddir = rt / "distorted_images"
    disk = {p.name.lower(): p for p in ddir.iterdir() if p.suffix.lower() == ".bmp"} if ddir.is_dir() else {}
    want = {nm.lower() for nm in names}
    if set(disk) != want:
        raise ValueError("tid2013_index: distorted_images/ holds %d BMPs, index names %d; sets differ (missing %d, extra %d)"
                         % (len(disk), len(want), len(want - set(disk)), len(set(disk) - want)))
    rdir = rt / "reference_images"
    ref_files = []
    for i in range(1, TID2013_N_REF + 1):
        p = _ci_file(rdir, "i%02d.bmp" % i)
        if p is None:
            raise ValueError("tid2013_index: reference image i%02d.bmp missing in %s" % (i, rdir))
        ref_files.append(p)
    return {"names": names, "mos": m, "ref": ref, "dist_type": typ, "level": lev, "ref_files": ref_files,
            "dist_files": [disk[nm.lower()] for nm in names], "root": rt}


def tid2013_metric_values(root, metric: str) -> np.ndarray:
    """作者の計算値 ``metrics_values/<metric>.txt``(大文字小文字無視、3000 行、名前なし)を (3000,) float で返す。
    行の順は :func:`tid2013_index` の ``names`` と同じ。``metric`` は :func:`tid2013_published` の鍵(psnr / psnrc / ssim / mssim …)。
    **Raises** ``ValueError``: ファイルが無い、行数 ≠ 3000、非数。"""
    rt = Path(root)
    d = rt / "metrics_values"
    p = _ci_file(d, "%s.txt" % metric)
    if p is None:
        raise ValueError("tid2013_metric_values: %s/%s.txt not found (known: %s)" % (d, metric, ", ".join(sorted(tid2013_published()))))
    vals = []
    for ln in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if ln.strip():
            try:
                vals.append(float(ln.split()[0].replace(",", ".")))
            except ValueError:
                raise ValueError("tid2013_metric_values: non-numeric line %r in %s" % (ln, p.name)) from None
    n_exp = TID2013_N_REF * TID2013_N_TYPES * TID2013_N_LEVELS
    if len(vals) != n_exp:
        raise ValueError("tid2013_metric_values: %s has %d lines, expected %d" % (p.name, len(vals), n_exp))
    v = np.asarray(vals, np.float64)
    if not np.all(np.isfinite(v)):
        raise ValueError("tid2013_metric_values: %s holds non-finite values" % p.name)
    return v


# ----------------------------------------------------------------------------------------------------------------------
# 5. 評価
def _load_rgb(path: Path) -> np.ndarray:
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGB"))
    if a.dtype != np.uint8 or a.ndim != 3:
        raise ValueError("tid2013: %s did not decode to uint8 RGB" % path)
    return a


def _select(index: dict, subset) -> np.ndarray:
    n = len(index["names"])
    if subset is None:
        return np.arange(n)
    if isinstance(subset, (int, np.integer)):
        k = int(subset)
        if not 1 <= k <= n:
            raise ValueError("tid2013_evaluate: subset count must be in [1, %d], got %d" % (n, k))
        return np.arange(k)
    pos = {nm.lower(): i for i, nm in enumerate(index["names"])}
    out = []
    for s in subset:
        key = str(s).lower()
        if not key.endswith(".bmp"):
            key += ".bmp"
        if key not in pos:
            raise ValueError("tid2013_evaluate: %r is not a TID2013 image name" % (s,))
        out.append(pos[key])
    if not out:
        raise ValueError("tid2013_evaluate: subset is empty")
    return np.asarray(out, np.int64)


def tid2013_evaluate(root, fn: Callable[[np.ndarray, np.ndarray], float], *, subset=None, luma: str = "limited_u8",
                     index: Optional[dict] = None) -> dict:
    """自前の指標 ``fn(ref, dist) -> float`` を TID2013 の組に当て、MOS との順位相関を返す。

    ``luma`` = ``"limited_u8"``(作者規約の Y′ uint8 (H, W) を渡す、psnr.txt / ssim.txt と比べるとき)/ ``"rgb"``(uint8 (H, W, 3) を
    そのまま渡す、psnrc.txt と比べるとき)。``subset`` = ``None``(3000 組全部)/ 個数(台帳の先頭 n)/ 名前の列(大文字小文字無視、
    拡張子は任意)。参照画像は 25 枚を一度だけ読む。
    返り値: ``values`` (n,)、``mos`` (n,)、``idx``(台帳の行番号)、``names``、``srocc``、``krocc``(τ_b)、``n``、``n_inf``、``luma``、``seconds``。
    ``fn`` が ``inf`` を返すのは**正当**(PSNR の完全一致)。TID2013 では歪み 18「彩度変化」の 125 組のうち **106 組で Y′ が参照と
    1 画素も変わらず**、作者は psnr.txt にその行を **100000.0** と書き、ssim.txt は 1.0(:func:`tid2013_compare` の ``inf_as``)。
    順位相関では inf を最大の順位として扱う。**Raises** ``ValueError``: ``luma`` が未知、``fn`` が数か ±inf を返さない(nan は拒否)、subset が不正。"""
    import time
    if luma not in ("limited_u8", "rgb"):
        raise ValueError("tid2013_evaluate: luma must be 'limited_u8' or 'rgb', got %r" % (luma,))
    ix = index if index is not None else tid2013_index(root)
    sel = _select(ix, subset)
    t0 = time.perf_counter()
    refs: Dict[int, np.ndarray] = {}
    vals = np.empty(sel.size, np.float64)
    for k, i in enumerate(sel):
        r = int(ix["ref"][i])
        if r not in refs:
            rgb = _load_rgb(ix["ref_files"][r - 1])
            refs[r] = luma_limited_u8(rgb) if luma == "limited_u8" else rgb
        d = _load_rgb(ix["dist_files"][i])
        d = luma_limited_u8(d) if luma == "limited_u8" else d
        v = fn(refs[r], d)
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise ValueError("tid2013_evaluate: fn returned %r for %s, not a number" % (v, ix["names"][i])) from None
        if np.isnan(v):
            raise ValueError("tid2013_evaluate: fn returned nan for %s" % ix["names"][i])
        vals[k] = v
    mos = ix["mos"][sel]
    return {"values": vals, "mos": mos, "idx": sel, "names": [ix["names"][i] for i in sel], "n": int(sel.size), "luma": luma,
            "n_inf": int(np.count_nonzero(np.isinf(vals))),
            "srocc": rank_spearman(mos, vals) if sel.size >= 2 else float("nan"),
            "krocc": rank_kendall_b(mos, vals) if sel.size >= 2 else float("nan"),
            "seconds": time.perf_counter() - t0}


def tid2013_compare(values, author_values, mos, published: Optional[Tuple[float, float]] = None,
                    inf_as: Optional[float] = None) -> dict:
    """自前の値と作者の値(同じ組、同じ順)の行ごとの差と、MOS との順位相関を比べる。

    ``inf_as`` = 自前の ``inf`` を差を取る前に置き換える値。作者は PSNR の完全一致を **100000.0** と書く(psnr.txt の 106 行、歪み 18)ので
    ``inf_as=100000.0`` で行ごとの差が 0 になる。省略時に ``inf`` があれば ``ValueError``(黙って落とさない)。順位相関は inf を順序として使う。
    作者の印は psnr.txt に **111 行**あるが、BT.601 の式で Y′ が参照と一致するのは 106 行 —— 残り 5 行(参照 I12 の彩度変化 5 段)は
    28 画素の輝度が **ちょうど k.5** に落ち、丸めの向きが作者の算術と食い違って 1 LSB 差 → 86.6 dB(半偶数・半切り上げ・float32・整数式を
    試しても 111 にはならない、2026-10-04)。そこで ``diff_max_finite``(作者も自分も完全一致でない行だけの最大差)と
    ``sentinel_mismatch_idx`` / ``sentinel_mismatch_values``(作者が印・自分は有限の行とその値)を**別に返す**。門は両方を見る。
    返り値: ``n``、``n_inf``、``n_sentinel_author``、``diff_max``(|自前 − 作者| の最大、印の行も含む)、``diff_max_finite`` / ``argmax_finite``、
    ``sentinel_mismatch_idx`` / ``sentinel_mismatch_values``、``inf_not_sentinel_idx``(自分が inf・作者は数値)、``diff_mean``(符号つき平均)、``diff_rms``、``argmax``(最大差の行)、
    ``srocc`` / ``krocc``(自前 vs MOS)、``srocc_author`` / ``krocc_author``(作者値 vs MOS)、``published`` を渡せば
    ``d_srocc_published`` / ``d_krocc_published``(自前 − 公表)と ``d_srocc_author_published`` / ``d_krocc_author_published``。
    **Raises** ``ValueError``: 長さ不一致・nan・``inf_as`` 無しの inf。"""
    v = _vec(values, "tid2013_compare", allow_inf=True)
    a = _vec(author_values, "tid2013_compare")
    m = _vec(mos, "tid2013_compare")
    if not (v.size == a.size == m.size):
        raise ValueError("tid2013_compare: values, author_values and mos must have the same length, got %d / %d / %d"
                         % (v.size, a.size, m.size))
    n_inf = int(np.count_nonzero(np.isinf(v)))
    vd = v
    sentinel = np.zeros(v.size, bool)
    if n_inf:
        if inf_as is None:
            raise ValueError("tid2013_compare: %d values are inf (perfect match); pass inf_as= (TID2013 authors write 100000.0)" % n_inf)
        vd = np.where(np.isinf(v), float(inf_as), v)
    if inf_as is not None:
        sentinel = a == float(inf_as)
    d = vd - a
    fin = ~sentinel & ~np.isinf(v)                    # 作者も自分も「完全一致」でない行 = 数値として比べられる行
    d_fin = d[fin] if fin.any() else np.zeros(1)
    # 作者が完全一致の印を書いたのに自分は有限(逆も): 件数と自分の値を返す。黙って除外しない。
    mism = np.where(sentinel & ~np.isinf(v))[0]
    out = {"n": int(v.size), "n_inf": n_inf, "n_sentinel_author": int(sentinel.sum()),
           "diff_max": float(np.abs(d).max()), "diff_mean": float(d.mean()),
           "diff_rms": float(np.sqrt((d * d).mean())), "argmax": int(np.abs(d).argmax()),
           "diff_max_finite": float(np.abs(d_fin).max()), "argmax_finite": int(np.where(fin)[0][np.abs(d_fin).argmax()]) if fin.any() else -1,
           "sentinel_mismatch_idx": mism.tolist(), "sentinel_mismatch_values": v[mism].tolist(),
           "inf_not_sentinel_idx": np.where(np.isinf(v) & ~sentinel)[0].tolist(),
           "srocc": rank_spearman(m, v), "krocc": rank_kendall_b(m, v),
           "srocc_author": rank_spearman(m, a), "krocc_author": rank_kendall_b(m, a)}
    if published is not None:
        ps, pk = float(published[0]), float(published[1])
        out.update({"published": (ps, pk), "d_srocc_published": out["srocc"] - ps, "d_krocc_published": out["krocc"] - pk,
                    "d_srocc_author_published": out["srocc_author"] - ps, "d_krocc_author_published": out["krocc_author"] - pk})
    return out


def tid2013_by_distortion(values, index: dict, idx=None) -> List[dict]:
    """歪み種(24)ごとの、指標と MOS の順位相関。

    ``values`` は ``idx``(台帳の行番号、省略 = 3000 行全部)に対応する値。各行: ``type``(1 始まり)、``name``(readme TABLE I)、
    ``n``、``n_inf``、``srocc``、``krocc``(τ_b)。1 種 = 25 参照 × 5 段 = 125 組。組が 2 未満の種は nan。歪み 18(彩度変化)は
    Y′ の PSNR が 106 / 125 組で inf(同順位)なので、その種の順位相関は低く出る —— 指標の欠陥でなく輝度だけを見る指標の限界。
    **Raises** ``ValueError``: 長さ不一致・nan。"""
    v = _vec(values, "tid2013_by_distortion", allow_inf=True)
    sel = np.arange(len(index["names"])) if idx is None else np.asarray(idx, np.int64).ravel()
    if sel.size != v.size:
        raise ValueError("tid2013_by_distortion: values (%d) and idx (%d) must have the same length" % (v.size, sel.size))
    typ = index["dist_type"][sel]
    mos = index["mos"][sel]
    rows = []
    for t in range(1, TID2013_N_TYPES + 1):
        m = typ == t
        n = int(m.sum())
        rows.append({"type": t, "name": TID2013_DISTORTIONS[t - 1], "n": n, "n_inf": int(np.count_nonzero(np.isinf(v[m]))),
                     "srocc": rank_spearman(mos[m], v[m]) if n >= 2 else float("nan"),
                     "krocc": rank_kendall_b(mos[m], v[m]) if n >= 2 else float("nan")})
    return rows
