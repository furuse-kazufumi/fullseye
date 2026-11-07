# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""実写の金属組織の顕微鏡写真で、影響圏の骨格(SKIZ)から粒界を出し、粒の大きさを専門家の手描きと比べる。

Grain boundaries from the skeleton by zones of influence (SKIZ) on real metallographic micrographs
(TBM, CC BY 4.0, expert hand-drawn boundaries): score the boundaries, measure grain size by the
ASTM E112 lineal-intercept (Heyn) method against the expert drawing, and compare Golay thinning with
scikit-image's skeletonize on the expert's own thick and thin drawings.

主役の op(opsmv の新しい op): ``morph_skiz``(連結成分の影響圏の境界)、``opening_seg``
(くびれで切り離して種にする)、``golay_elements`` / ``hit_or_miss_golay``(Golay の L による逐次の
細線化)、``hit_or_miss_seq``(Golay の E の 8 回転で端点を拾う)。

データ: TBM = Texture Boundary in Metallography(Zenodo record 8386997、doi:10.5281/zenodo.8386997、
CC BY 4.0)。色で腐食した多結晶の金属組織(約 1.2 mm × 0.8 mm、1328 × 872 画素なので約 0.9 µm/画素)
から切り出した 128 × 128 画素の 320 枚と、材料の専門家が手で描いた粒界(太い線と細い線の 2 版)。
32 枚の元画像から 10 枚ずつ切り出してある。原本は repo に入れず ``tools/fetch_tbm.py`` で
repo 外へ取得する(書庫の SHA-256 を固定)。この PoC は使う 4 つのフォルダの全ファイルの
SHA-256 も固定する(:data:`TBM_DIGEST`)。

手順と照合:

1. **種と SKIZ**: Lab 色空間の勾配がこの分位点より低い画素を「粒の内側」とし、``opening_seg`` で
   くびれを切って種にし、``morph_skiz`` で種の影響圏の境界を引く。パラメータ(平滑の幅・分位点・
   構造要素の半径)は元画像の番号が偶数の 152 枚だけで選び、奇数の 168 枚で採点する。
2. **粒界の位置**: 専門家の細い線との境界 F 値(許容 3 画素、BSDS と同じ数え方)。比べる相手は
   同じ種から scikit-image の watershed(勾配に沿って境界を引く)。SKIZ は種の真ん中に線を引き
   画像を見ないので、どれだけ負けるかを数える。
3. **粒の大きさ**: ASTM E112 の切断法(Heyn): 16 画素おきの縦横の試験線が粒界と交わる数 P から
   平均切片長 ℓ = L / P。専門家の線と SKIZ の ℓ の比を、評価の全枚数を合わせた値と 1 枚ずつで出し、
   粒度番号の差 ΔG = −6.644 log10(ℓ_SKIZ / ℓ_専門家) にする(画素の大きさが約しか分からなくても
   ΔG は比だけで決まる)。
4. **op の確かめ**: ``morph_skiz`` の境界が scikit-image の ``expand_labels`` の影響圏の境界と画素で
   一致すること、区画(4 連結)が種の数を下回らない = 2 つの影響圏がつながらないこと。
   ``hit_or_miss_seq`` の E で線の端点を拾い、縁と種から離れた端点(1 画素のひげ)を数える。
5. **細線化**: 専門家の太い線を Golay の L の 8 回転で細線化し、scikit-image の ``skeletonize`` と
   専門家自身の細い線と比べる(位置の F 値、画素数、粒の数が太い線と同じか、線が画像の縁まで届くか)。

結果(2026-11-08、この機械で実測。``RECORDED`` と同じ値):

* 粒界の位置: 評価の 168 枚で SKIZ の境界 F 0.697(適合率 0.655、再現率 0.772)。同じ種からの
  watershed は 0.704 で、68 % の枚数で SKIZ より上。SKIZ は種と種の真ん中に線を引き、画像の境を見ない。
* 粒の大きさ: 合わせた平均切片長は専門家 26.2 画素、SKIZ 21.1 画素(比 0.805、ΔG +0.63)。
  ところが 1 枚ずつは順位が合わない(Spearman ρ −0.16)。SKIZ の切片長は画像ごとにほとんど
  変わらない(変動係数 0.145、専門家は 0.311): 種を勾配の分位点で決めるので、種の密度が粒の大きさに
  追従しない。粒の数は専門家の 3 倍(中央値 57 対 18)。合わせた値が 1 に近いのは偶然の側にある。
* op の確かめ: ``morph_skiz`` は 168 枚すべてで ``expand_labels`` の影響圏の境界と画素で一致し、
  区画は種の数を下回らない。ただし右か下の隣で境界を決める規則から、1 画素のひげが 82 % の枚数に出る。
* 細線化: Golay の線は skeletonize と同じ場所を通る(F 0.991)が、4 連結の階段なので画素が 1.4 倍。
  太い線が画像の縁に触れる 5,072 箇所のうち、Golay は 96 % で縁まで届き、skeletonize は 66 %。
  skeletonize が残した 1 画素の隙間から縁の粒が隣とつながり、縁に触れる粒が 1 枚あたり 12.9 → 8.2 個に
  減る(Golay は 13.0 個)。縁に触れない粒はどちらも減らさない。

データが無い環境(CI)では取得せず ``RECORDED`` を印字し、op の契約の門(合成でない
scikit-image 同梱の実写 ``coins`` で SKIZ と ``expand_labels`` の一致、Golay の細線化の
1 画素幅と連結の保存)だけを回す。

実行例::

    py -3.11 tools/fetch_tbm.py
    py -3.11 examples/poc_real_grain_skiz.py

図(``FULLSEYE_FIGURE_DIR`` があるときだけ): 顕微鏡写真に専門家の粒界と SKIZ を重ねた見本(代表図)、
細線化の比較、切片長の散布、数値の表。
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import examplefig as figs  # noqa: E402
import fullseye as fs  # noqa: E402
import realdata  # noqa: E402

L = fs.ledger

SOURCE = ("TBM: Texture Boundary in Metallography (Zenodo record 8386997, doi:10.5281/zenodo.8386997), "
          "CC BY 4.0. Micrograph crops and expert boundary drawings shown unmodified except for "
          "nearest-neighbour enlargement and drawn overlays")

#: 使う 4 つのフォルダ(入力の写真、専門家の太い線・細い線、粒を白にした版)。
FOLDERS = ("input_image", "expert_inv_label", "expert_inv_label_thin", "expert_label")
N_IMAGES = 320
#: 4 フォルダの全ファイルを (フォルダ, 名前) の順に並べ、名前とバイト列を連結した SHA-256(2026-11-08)。
TBM_DIGEST = "31e79d054ddf1d94cbb019e36d3bc9a9e5b07eea26ec9fb2b0191173c7e51761"

#: 種のパラメータの候補(偶数の元画像で選ぶ)。
SIGMAS = (1.5, 2.0, 3.0)
PERCENTILES = (50, 60, 70)
RADII = (2, 3, 4)
#: 境界の F 値の許容[画素]。
BOUNDARY_TOL = 3.0
#: 切断法の試験線の間隔[画素]。
LINE_STEP = 16
#: 画素の大きさ(約): README の「約 1.2 mm × 0.8 mm」を元画像の 1328 × 872 画素で割った値[mm]。
PIXEL_MM_APPROX = 1.2 / 1328.0
#: 粒として数える最小の面積[画素]。
MIN_GRAIN_PX = 5

RECORDED: dict = {'G_approx': [7.51143, 8.13867],
 'contract': {'coins_objects': 51.0,
              'golay_iters': 24.0,
              'golay_over_skeletonize_px': 1.55123,
              'skiz_agree': 1.0},
 'cv': [0.310725, 0.145288],
 'dG': 0.627232,
 'date': '2026-11-08',
 'digest': '31e79d054ddf1d94cbb019e36d3bc9a9e5b07eea26ec9fb2b0191173c7e51761',
 'ell_pool': [26.2144, 21.0927],
 'ends_thin': 171,
 'extra_cells': 192,
 'f_skiz': [0.6551, 0.771528, 0.696948],
 'f_ws': [0.662309, 0.777825, 0.703875],
 'grain_counts_median': [18.0, 57.0],
 'n_split': [152, 168],
 'params': {'percentile': 60, 'radius': 2, 'sigma': 2.0},
 'ratio_pool': 0.804622,
 'ratio_quartiles': [0.674576, 0.83875, 1.0],
 'rho': -0.159246,
 'spur_images': 0.815476,
 'spurs': 265,
 'thin': {'border_reach': [0.962539, 0.65832],
          'f': [0.991144, 0.998321, 0.996663],
          'golay_4conn': 0.928125,
          'iters_max': 7,
          'keep_inner': [0.934375, 0.85],
          'outer_mean': [12.875, 12.975, 8.20312],
          'px_median': [1218.5, 857.5, 886.0]},
 'train_F': 0.707245,
 'ws_wins': 0.678571}


class GrainGateError(AssertionError):
    """門を通らなかった。"""


class Gates:
    def __init__(self) -> None:
        self.rows: list[tuple[str, bool, str]] = []

    def check(self, name: str, ok, detail: str = "") -> bool:
        ok = bool(ok)
        self.rows.append((name, ok, detail))
        print("  [%s] %s%s" % ("OK" if ok else "NG", name, (" — " + detail) if detail else ""))
        return ok

    def failed(self):
        return [r for r in self.rows if not r[1]]


# --------------------------------------------------------------------------- #
# データ
# --------------------------------------------------------------------------- #
def tbm_cache() -> Path:
    """TBM の repo 外の置き場(``FULLSEYE_TBM_DATA`` で上書き。規則は ``realdata.sem_metal_layer_cache`` と同じ形)。"""
    configured = os.environ.get("FULLSEYE_TBM_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    if ROOT.parent.name.lower() == "projects":
        return ROOT.parent.parent / "data" / "fullseye_poc_real" / "tbm"
    return Path.home() / ".cache" / "fullseye" / "tbm"


def load_tbm(root: Path, check_digest: bool = True) -> dict:
    """320 枚を読み、SHA-256 を照合して返す(名前 → 写真・太い線・細い線・粒)。"""
    base = root / "TBM"
    names = sorted(p.stem for p in (base / "input_image").glob("*.png"))
    if len(names) != N_IMAGES:
        raise realdata.RealDataError("TBM の写真が %d 枚(台帳は %d 枚): %s" % (len(names), N_IMAGES, base))
    h = hashlib.sha256()
    out = {}
    for folder in FOLDERS:
        files = sorted((base / folder).iterdir())
        if len(files) != N_IMAGES or sorted(p.stem for p in files) != names:
            raise realdata.RealDataError("TBM の %s の中身が写真と対応しない" % folder)
        for p in files:
            h.update(("%s/%s" % (folder, p.name)).encode())
            h.update(p.read_bytes())
    got = h.hexdigest()
    if check_digest and got != TBM_DIGEST:
        raise realdata.RealDataError("TBM の SHA-256 %s が台帳と違う" % got)
    for n in names:
        thin_path = next((base / "expert_inv_label_thin").glob(n + ".*"))
        out[n] = {
            "rgb": np.asarray(Image.open(base / "input_image" / (n + ".png")).convert("RGB")).astype(np.float64) / 255.0,
            "thick": np.asarray(Image.open(base / "expert_inv_label" / (n + ".png")).convert("L")) > 127,
            "thin": np.asarray(Image.open(thin_path).convert("L")) > 127,       # JPEG なので 127 で切る
            "grains": np.asarray(Image.open(base / "expert_label" / (n + ".png")).convert("L")) > 127,
            "source_image": int(n.split("-")[0]),
        }
    realdata.mark_read("tbm:TBM.zip")
    return {"images": out, "digest": got}


# --------------------------------------------------------------------------- #
# 計測
# --------------------------------------------------------------------------- #
def _disk(r: int) -> np.ndarray:
    y, x = np.mgrid[-r:r + 1, -r:r + 1]
    return x * x + y * y <= r * r


def lab_gradient(rgb: np.ndarray, sigma: float) -> np.ndarray:
    """Lab 色空間の 3 チャネルを平滑してから足した Sobel の勾配の大きさ(色で腐食した組織の境の強さ)。"""
    from skimage import color
    lab = color.rgb2lab(rgb)
    g2 = np.zeros(rgb.shape[:2])
    for k in range(3):
        s = ndi.gaussian_filter(lab[..., k], sigma)
        g2 += ndi.sobel(s, 0) ** 2 + ndi.sobel(s, 1) ** 2
    return np.sqrt(g2)


def seeds(grad: np.ndarray, percentile: float, radius: int) -> np.ndarray:
    """勾配の低い画素 → ``opening_seg`` でくびれを切る → ラベルどうしの接触を外した種(bool)。"""
    flat = grad < np.percentile(grad, percentile)
    labels = L.opening_seg(flat, _disk(radius))
    touch = np.zeros(labels.shape, bool)
    for axis in (0, 1):
        a = np.moveaxis(labels, axis, 0)
        diff = (a[1:] != a[:-1]) & (a[1:] > 0) & (a[:-1] > 0)
        t = np.moveaxis(touch, axis, 0)
        t[1:] |= diff
        t[:-1] |= diff
    return (labels > 0) & ~touch


def boundary_f(pred: np.ndarray, truth: np.ndarray, tol: float) -> tuple[float, float, float]:
    """境界の適合率・再現率・F 値(相手の線から ``tol`` 画素以内なら当たり)。"""
    if not pred.any() or not truth.any():
        return 0.0, 0.0, 0.0
    p = float((ndi.distance_transform_edt(~truth)[pred] <= tol).mean())
    r = float((ndi.distance_transform_edt(~pred)[truth] <= tol).mean())
    return p, r, 2 * p * r / max(1e-12, p + r)


def intercepts(boundary: np.ndarray, step: int = LINE_STEP) -> tuple[int, int]:
    """縦横の試験線が粒界の線に入る回数 P と、試験線の長さの合計 L[画素](ASTM E112 の Heyn 法)。"""
    P = Ltot = 0
    for line in [boundary[r] for r in range(step // 2, boundary.shape[0], step)] + \
                [boundary[:, c] for c in range(step // 2, boundary.shape[1], step)]:
        P += int(line[0]) + int(np.sum(line[1:] & ~line[:-1]))
        Ltot += line.size
    return P, Ltot


def grain_count(boundary: np.ndarray, conn8_background: bool = False) -> int:
    lab, _ = ndi.label(~boundary, structure=np.ones((3, 3), bool) if conn8_background else None)
    sizes = np.bincount(lab.ravel())[1:]
    return int((sizes >= MIN_GRAIN_PX).sum())


def grain_split(boundary: np.ndarray) -> tuple[int, int]:
    """(画像の縁に触れない粒の数, 縁に触れる粒の数)。背景は 4 連結、``MIN_GRAIN_PX`` 未満は数えない。"""
    lab, n = ndi.label(~boundary)
    sizes = np.bincount(lab.ravel(), minlength=n + 1)
    edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]]).tolist()) - {0}
    inner = sum(1 for i in range(1, n + 1) if i not in edge and sizes[i] >= MIN_GRAIN_PX)
    outer = sum(1 for i in edge if sizes[i] >= MIN_GRAIN_PX)
    return inner, outer


def border_contacts(thick: np.ndarray, thin: np.ndarray) -> tuple[int, int]:
    """太い線が画像の縁に触れる箇所(8 連結の塊)の数と、そのうち細い線が縁の画素まで届いている数。"""
    segs, k = ndi.label(thick & _border(thick.shape), structure=np.ones((3, 3), bool))
    reached = sum(1 for i in range(1, k + 1) if (thin & (segs == i)).any())
    return k, reached


def astm_g(mean_intercept_mm: float) -> float:
    """ASTM E112 の平均切片長[mm]からの粒度番号 G = −6.643856 log10(ℓ) − 3.288。"""
    return -6.643856 * math.log10(mean_intercept_mm) - 3.288


def golay_thin(region: np.ndarray, max_iter: int = 500) -> tuple[np.ndarray, int]:
    """Golay の L の 8 回転を順に引く逐次の細線化を、変化が止まるまで続ける。"""
    a = region.copy()
    for it in range(1, max_iter + 1):
        before = a.copy()
        for rot in range(8):
            a &= ~L.hit_or_miss_golay(a, "l", rot)
        if np.array_equal(a, before):
            return a, it
    raise GrainGateError("Golay の細線化が %d 周で止まらない" % max_iter)


def skiz_reference(seed: np.ndarray) -> np.ndarray:
    """scikit-image の ``expand_labels`` で影響圏を作り、右か下の隣と違う種の外の画素を境界にする。"""
    from skimage.segmentation import expand_labels
    labels, _ = ndi.label(seed, structure=np.ones((3, 3), bool))
    zone = expand_labels(labels, distance=float(sum(seed.shape)))
    edge = np.zeros(seed.shape, bool)
    edge[:-1] |= zone[:-1] != zone[1:]
    edge[:, :-1] |= zone[:, :-1] != zone[:, 1:]
    return edge & ~seed


# --------------------------------------------------------------------------- #
# CI でも回す op の契約の門
# --------------------------------------------------------------------------- #
def contract_gates(g: Gates) -> dict:
    print("\n== op の契約(scikit-image 同梱の実写 coins で、実データなしでも回る)")
    from skimage.morphology import skeletonize
    coins = realdata.sample_photo("coins")
    blobs = coins > np.percentile(coins, 70)
    blobs = ndi.binary_opening(blobs, structure=_disk(2))
    n_obj = ndi.label(blobs, structure=np.ones((3, 3), bool))[1]
    sk = L.morph_skiz(blobs)
    ref = skiz_reference(blobs)
    agree = float((sk == ref).mean())
    g.check("morph_skiz の境界 = expand_labels の影響圏の境界(coins の %d 個)" % n_obj, agree == 1.0,
            "一致 %.6f、境界 %d 画素" % (agree, int(sk.sum())))
    g.check("SKIZ は種に重ならず、種の数 ≥ 2 で空でない", sk.any() and not (sk & blobs).any())
    cells = ndi.label(~sk & ~blobs | blobs, structure=None)[1]
    g.check("SKIZ が作る区画の数 = 種の数", cells == n_obj, "%d 対 %d" % (cells, n_obj))
    thin, iters = golay_thin(blobs)
    n_before = ndi.label(blobs, structure=np.ones((3, 3), bool))[1]
    n_after = ndi.label(thin, structure=np.ones((3, 3), bool))[1]
    g.check("Golay の L の細線化は成分の数を保つ", n_before == n_after, "%d → %d(%d 周)" % (n_before, n_after, iters))
    g.check("Golay の細線化はもう L で削れない(収束)",
            not any(L.hit_or_miss_golay(thin, "l", r).any() for r in range(8)))
    holes_before = grain_split(blobs)[0]
    holes_after = grain_split(thin)[0]
    g.check("Golay の細線化は縁に触れない穴を減らさない", holes_after >= holes_before > 0,
            "%d → %d(細い線の間に隠れていた小さい穴が出てくる分だけ増える)" % (holes_before, holes_after))
    ratio = float(thin.sum() / max(1, skeletonize(blobs).sum()))
    return {"skiz_agree": agree, "coins_objects": int(n_obj), "golay_iters": int(iters),
            "golay_over_skeletonize_px": ratio}


# --------------------------------------------------------------------------- #
# 本体
# --------------------------------------------------------------------------- #
def run_set(images: dict, names: list[str], sigma: float, pct: float, rad: int, with_ws: bool = False) -> dict:
    from skimage.segmentation import watershed
    rows = []
    for n in names:
        im = images[n]
        grad = lab_gradient(im["rgb"], sigma)
        seed = seeds(grad, pct, rad)
        sk = L.morph_skiz(seed)
        row = {"name": n, "skiz": sk, "seed": seed, "f_skiz": boundary_f(sk, im["thin"], BOUNDARY_TOL)}
        if with_ws:
            markers, _ = ndi.label(seed, structure=np.ones((3, 3), bool))
            ws = watershed(grad, markers, watershed_line=True) == 0
            row["ws"] = ws
            row["f_ws"] = boundary_f(ws, im["thin"], BOUNDARY_TOL)
        rows.append(row)
    return {"rows": rows, "F": float(np.mean([r["f_skiz"][2] for r in rows]))}


def real_chapter(g: Gates, root: Path) -> dict:
    print("\n== 実データ: %s" % SOURCE)
    print("置き場: %s" % root)
    data = load_tbm(root)
    images = data["images"]
    print("  %d 枚、SHA-256 %s…" % (len(images), data["digest"][:16]))
    g.check("4 フォルダ × 320 枚の SHA-256 が台帳と一致", True)
    train = [n for n in images if images[n]["source_image"] % 2 == 0]
    test = [n for n in images if images[n]["source_image"] % 2 == 1]
    print("  学習 %d 枚(元画像 %d 枚)/ 評価 %d 枚(元画像 %d 枚)" % (
        len(train), len({images[n]["source_image"] for n in train}), len(test),
        len({images[n]["source_image"] for n in test})))

    print("\n-- 1. 種のパラメータを学習の %d 枚だけで選ぶ(専門家の細い線との境界 F 値、許容 %.0f 画素)" % (len(train), BOUNDARY_TOL))
    grid = []
    for sigma in SIGMAS:
        for pct in PERCENTILES:
            for rad in RADII:
                f = run_set(images, train, sigma, pct, rad)["F"]
                grid.append((f, sigma, pct, rad))
                print("   平滑 %.1f 分位 %d 半径 %d: F %.3f" % (sigma, pct, rad, f))
    best = max(grid)
    sigma, pct, rad = best[1:]
    print("   選んだ: 平滑 %.1f 分位 %d 半径 %d(学習の F %.3f)" % (sigma, pct, rad, best[0]))

    print("\n-- 2. 評価の %d 枚: SKIZ と watershed(同じ種)" % len(test))
    res = run_set(images, test, sigma, pct, rad, with_ws=True)
    rows = res["rows"]
    f_sk = np.array([r["f_skiz"] for r in rows])
    f_ws = np.array([r["f_ws"] for r in rows])
    print("   SKIZ      適合率 %.3f 再現率 %.3f F %.3f" % tuple(f_sk.mean(0)))
    print("   watershed 適合率 %.3f 再現率 %.3f F %.3f" % tuple(f_ws.mean(0)))
    wins = float((f_ws[:, 2] > f_sk[:, 2]).mean())
    print("   watershed が上の枚数の割合 %.3f" % wins)
    g.check("評価の SKIZ の境界 F ≥ 0.60(許容 3 画素)", f_sk[:, 2].mean() >= 0.60, "%.3f" % f_sk[:, 2].mean())
    g.check("所見: 同じ種なら画像の勾配に沿う watershed が SKIZ より上", f_ws[:, 2].mean() > f_sk[:, 2].mean(),
            "%.3f 対 %.3f(%.0f %% の枚数で上)" % (f_ws[:, 2].mean(), f_sk[:, 2].mean(), 100 * wins))

    # op の確かめ(実写の種で)
    agree = min(float((r["skiz"] == skiz_reference(r["seed"])).mean()) for r in rows)
    g.check("評価の全枚数で morph_skiz = expand_labels の影響圏の境界", agree == 1.0, "最小の一致 %.6f" % agree)
    eight = np.ones((3, 3), bool)
    extra = np.array([ndi.label(~r["skiz"])[1] - ndi.label(r["seed"], structure=eight)[1] for r in rows])
    g.check("評価の全枚数で SKIZ の区画(4 連結)は種の数以上 = 2 つの影響圏がつながらない", (extra >= 0).all(),
            "最小の差 %d" % extra.min())
    print("   種を含まない小さい区画(線とひげで切り取られた欠片): 合計 %d、%.0f %% の枚数に在る" %
          (extra.sum(), 100 * (extra > 0).mean()))
    # Golay の E(端点)で、縁から 3 画素より内側で種にも触れない端点 = 線から生えた 1 画素のひげを数える。
    spurs = []
    for r in rows:
        e = L.hit_or_miss_seq(r["skiz"], "e") & ~_border(r["skiz"].shape, 3)
        spurs.append(int((e & ~ndi.binary_dilation(r["seed"], structure=eight)).sum()))
    spurs = np.array(spurs)
    ends_thin = np.array([int((L.hit_or_miss_seq(images[r["name"]]["thin"], "e") & ~_border(r["skiz"].shape, 3)).sum())
                          for r in rows])
    print("   SKIZ の線から生えた 1 画素のひげ(hit_or_miss_seq の E): 合計 %d、%.0f %% の枚数に在る" %
          (spurs.sum(), 100 * (spurs > 0).mean()))
    print("   専門家の細い線の内側の端点: 合計 %d(閉じていない線、1 枚あたり中央値 %.0f)" % (ends_thin.sum(), np.median(ends_thin)))
    g.check("記録した癖: morph_skiz の線には 1 画素のひげが出る(右か下の隣で境界を決める規則)", spurs.sum() > 0,
            "合計 %d" % spurs.sum())

    print("\n-- 3. 粒の大きさ(ASTM E112 の切断法、試験線 %d 画素おき)" % LINE_STEP)
    P_sk = P_ex = Ltot = 0
    ratios, ell_sk, ell_ex = [], [], []
    for r in rows:
        ps, lt = intercepts(r["skiz"])
        pe, _ = intercepts(images[r["name"]]["thin"])
        P_sk += ps
        P_ex += pe
        Ltot += lt
        if ps and pe:
            ell_sk.append(lt / ps)
            ell_ex.append(lt / pe)
            ratios.append((lt / ps) / (lt / pe))
    ell_pool_sk, ell_pool_ex = Ltot / P_sk, Ltot / P_ex
    ratio_pool = ell_pool_sk / ell_pool_ex
    dG = -6.643856 * math.log10(ratio_pool)
    rho = float(spearmanr(ell_ex, ell_sk)[0])
    cv = [float(np.std(v) / np.mean(v)) for v in (ell_ex, ell_sk)]
    g_ex = astm_g(ell_pool_ex * PIXEL_MM_APPROX)
    g_sk = astm_g(ell_pool_sk * PIXEL_MM_APPROX)
    print("   平均切片長(評価の全枚数を合わせて): 専門家 %.2f 画素 / SKIZ %.2f 画素、比 %.3f、ΔG %+.2f" %
          (ell_pool_ex, ell_pool_sk, ratio_pool, dG))
    print("   粒度番号(画素 ≈ %.2f µm と仮定): 専門家 G %.2f / SKIZ G %.2f" % (PIXEL_MM_APPROX * 1000, g_ex, g_sk))
    print("   1 枚ずつの比: 中央値 %.3f、四分位 %.3f〜%.3f、Spearman ρ %.3f(n=%d)" %
          (np.median(ratios), np.percentile(ratios, 25), np.percentile(ratios, 75), rho, len(ratios)))
    gc_sk = np.array([grain_count(r["skiz"]) for r in rows])
    gc_ex = np.array([grain_count(~images[r["name"]]["grains"]) for r in rows])
    print("   粒の数(1 枚あたり): 専門家 中央値 %.0f / SKIZ 中央値 %.0f" % (np.median(gc_ex), np.median(gc_sk)))
    print("   1 枚ずつの切片長の変動係数: 専門家 %.3f / SKIZ %.3f(種を勾配の分位点で決めるので種の密度が画像によらない)"
          % tuple(cv))
    g.check("切片長の比(合わせた値)が 1 ± 0.25(|ΔG| ≤ 0.83)", abs(ratio_pool - 1) <= 0.25, "%.3f(ΔG %+.2f)" % (ratio_pool, dG))
    # 所見(変わったら書き換える): 合わせた値は 1 に近いが、粒の数は 3 倍で、1 枚ずつは順位も合わない。
    g.check("所見: 1 枚ずつの切片長は専門家と順位が合わない(Spearman ρ < 0.3)", rho < 0.3, "%.3f" % rho)
    g.check("所見: SKIZ の切片長は画像ごとの変化が専門家の半分以下(変動係数)", cv[1] <= 0.5 * cv[0],
            "%.3f 対 %.3f" % (cv[1], cv[0]))
    g.check("所見: SKIZ の粒の数は専門家の 2 倍以上(小さい種が粒になる)", np.median(gc_sk) >= 2 * np.median(gc_ex),
            "中央値 %.0f 対 %.0f" % (np.median(gc_sk), np.median(gc_ex)))
    g.check("切片長の数値が全部有限で正", all(math.isfinite(v) and v > 0 for v in ell_sk + ell_ex))

    print("\n-- 4. 細線化: 専門家の太い線を Golay の L で細くし、skeletonize と専門家の細い線と比べる(全 320 枚)")
    from skimage.morphology import skeletonize
    th_rows = []
    for n, im in images.items():
        gt, iters = golay_thin(im["thick"])
        sk = skeletonize(im["thick"])
        th_rows.append({
            "iters": iters, "px_golay": int(gt.sum()), "px_skel": int(sk.sum()), "px_thin": int(im["thin"].sum()),
            "f_golay_skel": boundary_f(gt, sk, 1.0)[2], "f_golay_thin": boundary_f(gt, im["thin"], 2.0)[2],
            "f_skel_thin": boundary_f(sk, im["thin"], 2.0)[2],
            "inner_thick": grain_split(im["thick"])[0], "inner_golay": grain_split(gt)[0], "inner_skel": grain_split(sk)[0],
            "outer_thick": grain_split(im["thick"])[1], "outer_golay": grain_split(gt)[1], "outer_skel": grain_split(sk)[1],
            "golay_4conn": ndi.label(gt)[1] == ndi.label(gt, structure=np.ones((3, 3), bool))[1],
            "contacts": border_contacts(im["thick"], gt)[0], "reach_golay": border_contacts(im["thick"], gt)[1],
            "reach_skel": border_contacts(im["thick"], sk)[1],
        })
    t = {k: np.array([r[k] for r in th_rows]) for k in th_rows[0]}
    keep_golay = float((t["inner_golay"] == t["inner_thick"]).mean())
    keep_skel = float((t["inner_skel"] == t["inner_thick"]).mean())
    lost_inner = int(((t["inner_golay"] < t["inner_thick"]) | (t["inner_skel"] < t["inner_thick"])).sum())
    outer = [float(t[k].mean()) for k in ("outer_thick", "outer_golay", "outer_skel")]
    reach = [float(t["reach_golay"].sum() / t["contacts"].sum()), float(t["reach_skel"].sum() / t["contacts"].sum())]
    print("   画素数(中央値): Golay %d / skeletonize %d / 専門家の細い線 %d" %
          (np.median(t["px_golay"]), np.median(t["px_skel"]), np.median(t["px_thin"])))
    print("   位置の F(平均): Golay 対 skeletonize %.3f(許容 1)/ Golay 対 専門家 %.3f / skeletonize 対 専門家 %.3f(許容 2)"
          % (t["f_golay_skel"].mean(), t["f_golay_thin"].mean(), t["f_skel_thin"].mean()))
    print("   縁に触れない粒の数が太い線と同じ枚数の割合: Golay %.3f / skeletonize %.3f(減った枚数 %d)"
          % (keep_golay, keep_skel, lost_inner))
    print("   縁に触れる粒の数(1 枚あたり平均): 太い線 %.2f / Golay %.2f / skeletonize %.2f" % tuple(outer))
    print("   太い線が画像の縁に触れる %d 箇所のうち、細い線が縁の画素まで届く割合: Golay %.3f / skeletonize %.3f"
          % (int(t["contacts"].sum()), reach[0], reach[1]))
    print("   Golay の線が 4 連結(斜めだけのつながりが無い)の割合 %.3f" % t["golay_4conn"].mean())
    g.check("Golay の線は skeletonize と同じ場所を通る(F ≥ 0.95、許容 1 画素)", t["f_golay_skel"].mean() >= 0.95,
            "%.3f" % t["f_golay_skel"].mean())
    g.check("Golay の線は専門家の細い線と重なる(F ≥ 0.95、許容 2 画素)", t["f_golay_thin"].mean() >= 0.95,
            "%.3f" % t["f_golay_thin"].mean())
    g.check("所見: Golay の線は skeletonize より画素が多い(4 連結の階段)",
            np.median(t["px_golay"]) > 1.2 * np.median(t["px_skel"]),
            "%d 対 %d" % (np.median(t["px_golay"]), np.median(t["px_skel"])))
    g.check("どちらの細線化も縁に触れない粒を減らさない(増えるのは太い線に埋もれた小さい粒)", lost_inner == 0,
            "減った枚数 %d、同じ割合 Golay %.3f / skeletonize %.3f" % (lost_inner, keep_golay, keep_skel))
    g.check("Golay は縁に触れる粒の数を保つ(平均の差 < 0.5)", abs(outer[1] - outer[0]) < 0.5,
            "%.2f 対 %.2f" % (outer[1], outer[0]))
    g.check("Golay の線は太い線が縁に触れる箇所の 9 割以上で縁まで届く", reach[0] >= 0.9, "%.3f" % reach[0])
    g.check("所見: skeletonize は 2 割以上の箇所で線の端を縁から 1 画素引き離す", reach[1] <= 0.8, "%.3f" % reach[1])
    g.check("所見: その隙間から縁の粒が隣とつながり、skeletonize では 1 枚あたり 3 個以上減る",
            outer[0] - outer[2] >= 3.0, "%.2f → %.2f" % (outer[0], outer[2]))
    return {"data": data, "images": images, "params": {"sigma": sigma, "percentile": pct, "radius": rad},
            "train_F": best[0], "rows": rows, "f_skiz": f_sk.mean(0).tolist(), "f_ws": f_ws.mean(0).tolist(),
            "ws_wins": wins, "extra_cells": int(extra.sum()), "n_train": len(train), "n_test": len(test),
            "spurs": int(spurs.sum()), "spur_images": float((spurs > 0).mean()),
            "ends_thin": int(ends_thin.sum()),
            "ell_pool": [ell_pool_ex, ell_pool_sk], "ratio_pool": ratio_pool, "dG": dG, "G": [g_ex, g_sk],
            "rho": rho, "cv": cv, "ratio_quartiles": [float(np.percentile(ratios, q)) for q in (25, 50, 75)],
            "ell_each": (ell_ex, ell_sk), "grain_counts": [float(np.median(gc_ex)), float(np.median(gc_sk))],
            "thin": {"px_median": [float(np.median(t[k])) for k in ("px_golay", "px_skel", "px_thin")],
                     "f": [float(t[k].mean()) for k in ("f_golay_skel", "f_golay_thin", "f_skel_thin")],
                     "keep_inner": [keep_golay, keep_skel], "outer_mean": outer, "border_reach": reach,
                     "golay_4conn": float(t["golay_4conn"].mean()),
                     "iters_max": int(t["iters"].max())}}


def _border(shape, w: int = 1) -> np.ndarray:
    b = np.zeros(shape, bool)
    b[:w] = b[-w:] = True
    b[:, :w] = b[:, -w:] = True
    return b


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def _enlarge(rgb8: np.ndarray, s: int) -> np.ndarray:
    return np.asarray(Image.fromarray(rgb8).resize((rgb8.shape[1] * s, rgb8.shape[0] * s), Image.NEAREST))


def render_overlay(im: dict, skiz: np.ndarray, scale: int = 3) -> np.ndarray:
    """写真(左)と、専門家の線(白)と SKIZ(空色)を重ねた写真(右)。重なった画素は白で上書きしない。"""
    base = (im["rgb"] * 255).astype(np.uint8)
    over = base.copy()
    over[im["thin"]] = (255, 255, 255)
    over[skiz] = fs.role_rgb8("right")
    gap = np.full((base.shape[0] * scale, 4, 3), 255, np.uint8)
    return np.hstack([_enlarge(base, scale), gap, _enlarge(over, scale)])


def write_figures(res: dict) -> None:
    if not figs.enabled():
        return
    rows = sorted(res["rows"], key=lambda r: r["f_skiz"][2])
    pick = [rows[len(rows) // 2], rows[int(len(rows) * 0.9)], rows[int(len(rows) * 0.1)]]
    tiles = [render_overlay(res["images"][r["name"]], r["skiz"]) for r in pick]
    gap = np.full((8, tiles[0].shape[1], 3), 255, np.uint8)
    sheet = np.vstack([x for t in tiles for x in (t, gap)][:-1])
    figs.save("grain_boundaries", sheet,
              caption="TBM の評価の 3 枚(上から F の中央値・上位 10 %%・下位 10 %%: %.2f / %.2f / %.2f)。左 = 実写の顕微鏡写真"
                      "(色で腐食した金属組織、128 × 128 画素 ≈ 115 µm 角を 3 倍)、右 = 白が専門家の手描きの粒界、空色が "
                      "morph_skiz の粒界(勾配の低い画素を opening_seg で種にした影響圏の境界)。"
                      % tuple(r["f_skiz"][2] for r in pick), source=SOURCE)
    from skimage.morphology import skeletonize
    # 画像の上の縁で Golay は届き skeletonize は届かない箇所を、評価の代表の写真から順に探して切り出す
    for r in [pick[0]] + rows:
        im = res["images"][r["name"]]
        gt, _ = golay_thin(im["thick"])
        sk = skeletonize(im["thick"])
        top = im["thick"][0] & gt[0] & ~sk[0]
        if top.any():
            c = int(np.nonzero(top)[0][0])
            c0 = min(max(0, c - 16), im["thick"].shape[1] - 32)
            crop = (slice(0, 32), slice(c0, c0 + 32))
            name = r["name"]
            break
    else:
        raise GrainGateError("縁で差の出る箇所が見つからない")
    panels = []
    for m in (im["thick"], gt, sk, im["thin"]):
        a = np.where(m[crop], 0, 255).astype(np.uint8)
        panels.append(_enlarge(np.repeat(a[:, :, None], 3, 2), 12))
    gap = np.full((panels[0].shape[0], 6, 3), 160, np.uint8)
    figs.save("thinning", np.hstack([x for p in panels for x in (p, gap)][:-1]),
              caption="%s の左上の隅の 32 × 32 画素(12 倍、黒 = 線、上端と左端 = 画像の縁)。左から 専門家の太い線 / Golay の L の 8 回転の逐次細線化 / "
                      "scikit-image の skeletonize / 専門家自身の細い線。Golay の線は 4 連結の階段なので画素が多く、"
                      "画像の縁まで届く(skeletonize は線の端を縁から 1 画素引き離す)。" % name,
              source=SOURCE)
    ell_ex, ell_sk = res["ell_each"]
    lo, hi = 0.0, float(max(max(ell_ex), max(ell_sk))) * 1.05
    figs.save_plot("intercepts", [("1 枚ずつ(評価の %d 枚)" % res["n_test"], list(ell_ex), list(ell_sk)), ("y = x", [lo, hi], [lo, hi])],
                   kinds=["scatter", "line"], styles=[None, "dashed"], colors=["emphasis", "reference"],
                   xlabel="専門家の線の平均切片長 [画素]", ylabel="SKIZ の平均切片長 [画素]",
                   title="ASTM E112 の切断法: 合わせた比 %.3f(ΔG %+.2f)、Spearman ρ %.2f" %
                         (res["ratio_pool"], res["dG"], res["rho"]),
                   caption="16 画素おきの縦横の試験線。1 画素 ≈ 0.9 µm(README の約 1.2 mm を 1328 画素で割った値)。",
                   source=SOURCE)
    header = ["量", "値"]
    rows_t = [
        ["種のパラメータ(学習の %d 枚で選んだ)" % res["n_train"], "平滑 %.1f / 分位 %d / 半径 %d" % (res["params"]["sigma"], res["params"]["percentile"], res["params"]["radius"])],
        ["境界の F(評価、許容 3 画素): SKIZ", "%.3f" % res["f_skiz"][2]],
        ["境界の F: watershed(同じ種)", "%.3f" % res["f_ws"][2]],
        ["平均切片長 専門家 / SKIZ [画素]", "%.2f / %.2f" % tuple(res["ell_pool"])],
        ["粒度番号の差 ΔG", "%+.2f" % res["dG"]],
        ["SKIZ の 1 画素のひげ(評価の %d 枚の合計)" % res["n_test"], "%d" % res["spurs"]],
        ["細線化の画素数 Golay / skeletonize / 専門家", "%.0f / %.0f / %.0f" % tuple(res["thin"]["px_median"])],
        ["縁に触れる粒(1 枚平均)太い線 / Golay / skeletonize", "%.2f / %.2f / %.2f" % tuple(res["thin"]["outer_mean"])],
        ["線が画像の縁まで届く割合 Golay / skeletonize", "%.3f / %.3f" % tuple(res["thin"]["border_reach"])],
    ]
    figs.save_table("numbers", header, rows_t, title="TBM(実写の金属組織 320 枚)での SKIZ と細線化",
                    caption="学習 = 元画像の番号が偶数の %d 枚、評価 = 奇数の %d 枚。" % (res["n_train"], res["n_test"]))


def _record(res: dict, contract: dict) -> dict:
    r6 = lambda v: float("%.6g" % v)  # noqa: E731
    return {"date": "2026-11-08", "digest": res["data"]["digest"], "params": res["params"],
            "train_F": r6(res["train_F"]), "f_skiz": [r6(v) for v in res["f_skiz"]], "f_ws": [r6(v) for v in res["f_ws"]],
            "ws_wins": r6(res["ws_wins"]), "extra_cells": res["extra_cells"], "n_split": [res["n_train"], res["n_test"]],
            "spurs": res["spurs"], "spur_images": r6(res["spur_images"]),
            "ends_thin": res["ends_thin"],
            "ell_pool": [r6(v) for v in res["ell_pool"]], "ratio_pool": r6(res["ratio_pool"]), "dG": r6(res["dG"]),
            "G_approx": [r6(v) for v in res["G"]], "rho": r6(res["rho"]), "cv": [r6(v) for v in res["cv"]],
            "ratio_quartiles": [r6(v) for v in res["ratio_quartiles"]], "grain_counts_median": res["grain_counts"],
            "thin": {k: ([r6(x) for x in v] if isinstance(v, list) else (r6(v) if isinstance(v, float) else v))
                     for k, v in res["thin"].items()},
            "contract": {k: r6(v) for k, v in contract.items()}}


def main() -> None:
    t0 = time.perf_counter()
    g = Gates()
    contract = contract_gates(g)
    root = tbm_cache()
    have = (root / "TBM" / "input_image").is_dir()
    if (os.environ.get("CI") and not os.environ.get("FULLSEYE_TBM_DATA")) or not have:
        print("\n実データ(TBM)が無いので実データの章を飛ばす。取得は py -3.11 tools/fetch_tbm.py")
        print("記録値(RECORDED): " + json.dumps(RECORDED, ensure_ascii=False, sort_keys=True))
        g.check("記録値が空でない", bool(RECORDED) and RECORDED.get("spurs", 0) > 0)
    else:
        res = real_chapter(g, root)
        print("\nRECORDED_JSON=" + json.dumps(_record(res, contract), ensure_ascii=False, sort_keys=True))
        write_figures(res)
    errors = figs.errors()
    if errors:
        raise SystemExit("図の書き出しで失敗: " + "; ".join(errors))
    bad = g.failed()
    if bad:
        raise GrainGateError("門が %d 本外れた: %s" % (len(bad), "; ".join(r[0] for r in bad)))
    print("門 %d 本すべて通過(%.1f s)\nPASS" % (len(g.rows), time.perf_counter() - t0))


if __name__ == "__main__":
    main()
