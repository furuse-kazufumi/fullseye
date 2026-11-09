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
4. **op の確かめ**: ``morph_skiz`` の境界が、成分ごとに距離変換を取る厳密な影響圏から作った境界と
   画素で一致すること、区画(4 連結)が種の数を下回らない = 2 つの影響圏がつながらないこと。
   ``hit_or_miss_seq`` の E で線の端点を拾い、縁と種から離れた端点(1 画素のひげ)を数える。
5. **細線化**: 専門家の太い線を Golay の L の 8 回転で細線化し、scikit-image の ``skeletonize`` と
   専門家自身の細い線と比べる(位置の F 値、画素数、粒の数が太い線と同じか、線が画像の縁まで届くか)。

結果(2026-11-09、この機械で実測。``RECORDED`` と同じ値):

* 粒界の位置: 評価の 168 枚で SKIZ の境界 F 0.633(適合率 0.630、再現率 0.662)。同じ種からの
  watershed は 0.677 で、168 枚すべてで SKIZ より上。SKIZ は種と種の真ん中に線を引き、画像の境を見ない。
* 粒の大きさ: 合わせた平均切片長は専門家 26.2 画素、SKIZ 25.6 画素(比 0.977、ΔG +0.07)。
  ところが 1 枚ずつは順位が合わない(Spearman ρ −0.17、これは門)。SKIZ の切片長は画像ごとの変化が
  専門家より小さく(変動係数 0.176 対 0.311)、粒の数は専門家より多い(中央値 31 対 18)。種を勾配の分位点で
  決めるので、種の密度が粒の大きさに追従しない。合わせた値が 1 に近いのは偶然の側にある。
  (2026-11-08 の版はこの 2 つを「半分以下」「2 倍以上」の門にしていたが、opening_seg の修正の後は成り立たない
  ので門から外した。)
* op の確かめ: ``morph_skiz`` は 168 枚すべてで厳密な影響圏の境界と画素で一致し、区画は種の数を
  下回らない。1 画素のひげは 99 % の枚数に出る(同距離の画素と、偶数幅の隙間で 2 画素になる線の端)。
* 2026-11-09 に op を 2 つ直して数値が動いた(``opening_seg`` が背景を跨いで種を配らなくなった・
  ``morph_skiz`` の境界が上・左へ寄らなくなった)。片方ずつ戻して分けると、動いたのはほぼ
  ``opening_seg`` の側: 種を失った小さな塊が隣の番号をもらって種になっていたのが 0 になり、粒の数
  57 → 31、切片長の比 0.80 → 0.98、境界 F 0.697 → 0.633(再現率 0.77 → 0.66)。``morph_skiz`` の
  対称化だけでは F 0.697 → 0.687、ひげ 265 → 1,116(線が対称になった分、端点が増えた)。
* 細線化: Golay の線は skeletonize と同じ場所を通る(F 0.991)が、4 連結の階段なので画素が 1.4 倍。
  太い線が画像の縁に触れる 5,072 箇所のうち、Golay は 96 % で縁まで届き、skeletonize は 66 %。
  skeletonize が残した 1 画素の隙間から縁の粒が隣とつながり、縁に触れる粒が 1 枚あたり 12.9 → 8.2 個に
  減る(Golay は 13.0 個)。縁に触れない粒はどちらも減らさない。

データが無い環境(CI)では取得せず ``RECORDED`` を印字し、op の契約の門(合成でない
scikit-image 同梱の実写 ``coins`` で SKIZ と厳密な影響圏の一致、Golay の細線化の
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
from PIL import Image, ImageDraw, ImageFont
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

RECORDED: dict = {'G_approx': [7.51143, 7.57858],
 'contract': {'coins_objects': 51.0,
              'golay_iters': 24.0,
              'golay_over_skeletonize_px': 1.55123,
              'skiz_agree': 1.0},
 'cv': [0.310725, 0.176411],
 'dG': 0.067143,
 'date': '2026-11-09',
 'digest': '31e79d054ddf1d94cbb019e36d3bc9a9e5b07eea26ec9fb2b0191173c7e51761',
 'ell_pool': [26.2144, 25.6114],
 'ends_thin': 171,
 'extra_cells': 143,
 'f_skiz': [0.630484, 0.662037, 0.63269],
 'f_ws': [0.682253, 0.69836, 0.677421],
 'grain_counts_median': [18.0, 31.0],
 'n_split': [152, 168],
 'params': {'percentile': 60, 'radius': 2, 'sigma': 2.0},
 'ratio_pool': 0.976999,
 'ratio_quartiles': [0.823828, 1.02767, 1.22679],
 'rho': -0.168963,
 'spur_images': 0.994048,
 'spurs': 865,
 'thin': {'border_reach': [0.962539, 0.65832],
          'f': [0.991144, 0.998321, 0.996663],
          'golay_4conn': 0.928125,
          'iters_max': 7,
          'keep_inner': [0.934375, 0.85],
          'outer_mean': [12.875, 12.975, 8.20312],
          'px_median': [1218.5, 857.5, 886.0]},
 'train_F': 0.653131,
 'ws_wins': 1.0}


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
    """成分ごとに距離変換を取る**厳密な**影響圏から SKIZ を作る(op とは別の作り方の参照)。

    各成分 k への距離 D_k を 1 枚ずつ求め、最も近い成分の集合 S = {k : D_k = min D} を正確に出す。
    境界 = 同距離の成分が 2 つ以上ある画素 + 4 近傍の隣と S が重ならない対の、自分の成分から遠い側
    (等しければ両方)。op は 8 通りの走査の向きから集合を集めるので作り方が違う。
    ★2026-11-09: 以前は ``expand_labels`` の影響圏に「右か下の隣と違う画素」の規則を当てた参照で、
    op の片寄り(上・左へ 1 画素)まで写していた。
    """
    labels, n = ndi.label(seed, structure=np.ones((3, 3), bool))
    if n < 2:
        return np.zeros(seed.shape, bool)
    D = np.stack([ndi.distance_transform_edt(labels != k) for k in range(1, n + 1)])
    d = D.min(axis=0)
    S = D == d[None]                                     # 最も近い成分の集合(n, H, W)
    del D
    edge = S.sum(axis=0) >= 2
    for sl_a, sl_b in (((slice(None, -1), slice(None)), (slice(1, None), slice(None))),
                       ((slice(None), slice(None, -1)), (slice(None), slice(1, None)))):
        dj = ~(S[(slice(None),) + sl_a] & S[(slice(None),) + sl_b]).any(axis=0)
        da, db = d[sl_a], d[sl_b]
        edge[sl_a] |= dj & (da >= db)
        edge[sl_b] |= dj & (db >= da)
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
    g.check("morph_skiz の境界 = 厳密な影響圏の境界(coins の %d 個)" % n_obj, agree == 1.0,
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
    g.check("4 フォルダ × 320 枚の SHA-256 が台帳(TBM_DIGEST)と一致",
            data["digest"] == TBM_DIGEST and len(images) == N_IMAGES, "%s…(%d 枚)" % (data["digest"][:16], len(images)))
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
    g.check("評価の全枚数で morph_skiz = 厳密な影響圏の境界", agree == 1.0, "最小の一致 %.6f" % agree)
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
    g.check("記録した癖: morph_skiz の線には 1 画素のひげが出る(同距離の画素と偶数幅の 2 画素の線の端)", spurs.sum() > 0,
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
    # 所見(変わったら書き換える): 合わせた値は 1 に近いが、粒の数は 1.7 倍で、1 枚ずつは順位も合わない。
    # ★2026-11-09: opening_seg の修正で粒の数が 57 → 31(専門家 18)、変動係数が 0.145 → 0.176 に動き、
    #   門「SKIZ の粒の数は専門家の 2 倍以上」「変動係数は専門家の半分以下」が成り立たなくなった。門の値を実測の
    #   直上へ動かすのは緩めになるので、2 本とも門から外し、数値は印字と RECORDED にだけ残す(主張は本文で縮めた)。
    g.check("所見: 1 枚ずつの切片長は専門家と順位が合わない(Spearman ρ < 0.3)", rho < 0.3, "%.3f" % rho)
    print("   (門なし)切片長の変動係数 SKIZ %.3f 対 専門家 %.3f、粒の数の中央値 SKIZ %.0f 対 専門家 %.0f"
          % (cv[1], cv[0], np.median(gc_sk), np.median(gc_ex)))
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


def _font(size: int):
    path = figs._japanese_font_path(fail_closed=False)
    return ImageFont.truetype(str(path), size) if path else ImageFont.load_default()


def _text_strip(width: int, lines: list[tuple[str, int]], legend: list[tuple[tuple, str]] | None = None,
                bg=(32, 32, 32), fg=(255, 255, 255)) -> np.ndarray:
    """文字の帯(暗い地に白い字)。``lines`` は (文, 字の大きさ)、``legend`` は (色, 説明) の並び。"""
    pad = 8
    h = pad + sum(sz + 6 for _, sz in lines) + (26 if legend else 0) + pad
    im = Image.new("RGB", (width, h), bg)
    dr = ImageDraw.Draw(im)
    y = pad
    for text, sz in lines:
        dr.text((pad, y), text, fill=fg, font=_font(sz))
        y += sz + 6
    if legend:
        x = pad
        f = _font(17)
        for col, text in legend:
            dr.rectangle([x, y + 4, x + 26, y + 18], fill=tuple(int(v) for v in col), outline=(160, 160, 160))
            x += 34
            dr.text((x, y), text, fill=fg, font=f)
            x += int(dr.textlength(text, font=f)) + 24
    return np.asarray(im)


def write_figures(res: dict) -> None:
    if not figs.enabled():
        return
    # 代表図は「粒の大きさに追従しない」が 10 秒で見える 2 枚: 専門家の線で粒が大きい 1 枚と小さい 1 枚
    # (評価の 168 枚を専門家の平均切片長で並べた 90 % 点と 10 % 点)。どちらも SKIZ の切片長はほぼ同じになる。
    ell = []
    for r in res["rows"]:
        ps, lt = intercepts(r["skiz"])
        pe, _ = intercepts(res["images"][r["name"]]["thin"])
        if ps and pe:
            ell.append((lt / pe, lt / ps, r))
    ell.sort(key=lambda t: t[0])
    pick = [ell[int(len(ell) * 0.9)], ell[int(len(ell) * 0.1)]]
    width = render_overlay(res["images"][pick[0][2]["name"]], pick[0][2]["skiz"]).shape[1]
    parts = [_text_strip(width, [
        ("失敗の報告: SKIZ の粒界は粒の大きさに追従しない", 22),
        ("評価 %d 枚で 1 枚ずつの平均切片長の順位 Spearman ρ %.2f(専門家と合わない)" % (res["n_test"], res["rho"]), 17),
        ("粒界の位置 F %.3f は同じ種の watershed %.3f に負け、粒の数は専門家の %.1f 倍"
         % (res["f_skiz"][2], res["f_ws"][2], res["grain_counts"][1] / res["grain_counts"][0]), 17),
    ], legend=[((255, 255, 255), "専門家の手描きの粒界"), (fs.role_rgb8("right"), "morph_skiz の粒界(右)。左 = 写真")])]
    gap = np.full((8, width, 3), 255, np.uint8)
    for (le, ls, r), what in zip(pick, ("専門家の粒が大きい 1 枚", "専門家の粒が小さい 1 枚")):
        gc_ex = grain_count(~res["images"][r["name"]]["grains"])
        gc_sk = grain_count(r["skiz"])
        parts += [gap, _text_strip(width, [
            ("%s: 平均切片長 専門家 %.1f 画素 → SKIZ %.1f 画素" % (what, le, ls), 18),
            ("粒の数 専門家 %d・SKIZ %d / 境界 F SKIZ %.2f・watershed %.2f" % (gc_ex, gc_sk, r["f_skiz"][2], r["f_ws"][2]), 16),
        ], bg=(235, 235, 235), fg=(20, 20, 20)), render_overlay(res["images"][r["name"]], r["skiz"])]
    sheet = np.vstack(parts)
    figs.save("grain_boundaries", sheet,
              caption="失敗の報告。TBM の評価の 168 枚を専門家の線の平均切片長で並べた 90 %% 点(粒が大きい)と 10 %% 点"
                      "(粒が小さい)の 2 枚。専門家の切片長は %.1f と %.1f 画素で %.1f 倍違うのに、SKIZ は %.1f と %.1f 画素。"
                      "左 = 実写の顕微鏡写真(色で腐食した金属組織、128 × 128 画素 ≈ 115 µm 角を 3 倍)、右 = 白が専門家の"
                      "手描きの粒界、空色が morph_skiz の粒界(勾配の低い画素を opening_seg で種にした影響圏の境界)。"
                      % (pick[0][0], pick[1][0], pick[0][0] / pick[1][0], pick[0][1], pick[1][1]), source=SOURCE)
    from skimage.morphology import skeletonize
    # 画像の上の縁で Golay は届き skeletonize は届かない箇所を、評価の代表の写真から順に探して切り出す
    rows = sorted(res["rows"], key=lambda r: r["f_skiz"][2])
    for r in [rows[len(rows) // 2]] + rows:
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
    # 下地は同じ場所の顕微鏡写真を白へ寄せて薄くしたもの(線がどこを通っているかを写真の上で見せる)
    faded = (255 - 0.45 * (255 - im["rgb"][crop] * 255)).astype(np.uint8)
    for m in (im["thick"], gt, sk, im["thin"]):
        a = faded.copy()
        a[m[crop]] = (0, 0, 0)
        panels.append(_enlarge(a, 12))
    gap = np.full((panels[0].shape[0], 6, 3), 160, np.uint8)
    figs.save("thinning", np.hstack([x for p in panels for x in (p, gap)][:-1]),
              caption="%s の左上の隅の 32 × 32 画素(12 倍、黒 = 線、下地 = 同じ場所の写真を薄くしたもの、上端と左端 = 画像の縁)。左から 専門家の太い線 / Golay の L の 8 回転の逐次細線化 / "
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
    return {"date": "2026-11-09", "digest": res["data"]["digest"], "params": res["params"],
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
