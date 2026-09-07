# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""金属組織の結晶粒度を測る —— 面積法は途切れ数 % で 1 段落ち、切片法は 20 % まで持つ。

金相写真(エッチングして粒界を黒く出した金属の断面)から **ASTM E112 の粒度番号 G**
を出す仕事です。G は熱処理・強度の合否に直結する 1 つの数字で、**1 段(ΔG = 1)は
平均切片長 ℓ の √2 倍**に当たります。E112 には面積法(粒の数を数える)と
直線切断法(直線が粒界を横切る回数を数える)があり、教科書ではどちらでも
同じ G が出ることになっていますが、**エッチングむらと粒界の途切れ**が入ると
2 つの方法は**まるで違う壊れ方**をします。

EXTEND: 実写に差し替えるなら :func:`make_scene` が返す辞書の ``img`` を顕微鏡画像に、
``labels``(画素ごとの粒の番号)を EBSD の結晶方位マップなどの独立した真値に置き換えます。
**粒界を手でなぞった線だけでは足りません** —— この PoC の中心的な軸は「途切れた
粒界の向こうにも粒界はある」なので、真値は粒の**所属**(どの画素がどの粒か)で持つこと。
画素→mm の換算 :data:`PX_MM` は対物倍率とカメラ画素から**先に計算**して入れます。

この PoC が示すこと(数字はいずれも実行時に印字される実測値):

1. **真値の検算**: Poisson-Voronoi の閉形式 ℓ = π/(4√λ) は、真値粒界での切片数え上げと
   +1.5 % で一致する。ただし★**同じ真値組織で E112 の 2 つの式は一致しない**:
   切片法 G 6.96 / 面積法 G 6.64(差 +0.32)。E112 の換算は「標準的な粒の形」を
   仮定していて、Voronoi は ℓ/√A = π/4 = 0.785(E112 の暗黙値 0.891)なので
   **+0.36 段ずれる**と予測でき、実測と合う。★最初の版は種を 1.2 倍に水増しして
   間引き忘れ、閉形式と -10.7 % ずれて発覚した —— 検算が無ければ「狙い G = 7」の
   つもりで G 7.4 の組織を測っていた。
2. ★★**ゼロ点(大津の二値化 + 連結成分)は「むら × 雑音」の相互作用で死ぬ**。
   雑音だけなら +0.01、エッチングむら(粒ごとの明るさ σ 0.10)だけなら -0.36
   (暗い粒が 53 個消える)。ところが**両方が入ると +3.68** —— しきい値が
   「暗い粒 vs 明るい粒」の谷に落ち、しきい値付近の粒が雑音で粉々(種の無い塊
   2,600 個超)になって N_A が 13 倍に化ける。**要因を 1 つずつ止めた対照群でしか
   この相互作用は見えない**。
3. ★**粒界抽出でも正規化の仕方で差が出る**。ボトムハット(最大値で正規化)は
   むらのみで -0.57 —— 小さい暗い粒 1 個が最大値を決めて、しきい値が相対的に
   上がり弱い粒界を落とす。局所しきい値(``invert_image`` → ``dyn_threshold``、
   絶対オフセット 0.10)なら同じ条件で -0.02。**むらに強いのは「周りとの絶対差」**。
4. ★★**崖の位置が 1 桁違う**。粒界の途切れ率を 0 → 60 % で掃引すると、
   面積法(むらを止めた対照群)は **6.9 %** で 1 段落ち、切片法は **21.4 %**。
   切片法の予想は「横切りが (1−f) 倍 → ℓ が √2 倍になる f = 29.3 %」だったが
   **外れた**: 途切れ 0 % でも粒界の幅(2 px + ぼけ)より短い弦(頂点近く、
   真値で 22 本)が 1 本の黒線に溶けて ΔG = -0.09 から始まるので、そのぶん手前の
   20.4 % が正しい予測で、実測 21.4 % と合う。実測曲線は補正した予測と最大
   0.12 段で並走する。
5. ★面積法の予想は「1 本の途切れで 2 粒が融合 → 塊の数 N(1 − 3p)、p = 辺の
   途切れ率で 1/6 なら 1 段」。相関長 8 px の乱数場で消した隙間は中央値 16 px
   (辺の平均 24 px)なので p ≈ f と踏んだが、**隙間は頂点で 3 辺を同時に開く**
   ので p は f の 1.7 倍で走り(f 5 % で p 8.6 %)、木近似の予測 1 段の点は f 9.5 %、
   実測は 6.9 %(閉路の分だけ木近似より早い)。
6. ★★**「隙間を閉じる」は何も買わない**。closing 9×9 で閉じられる隙間は 8 px 以下、
   隙間の中央値は 16 px。閉じた版は途切れ 0 % で偽横切りを 33 → 20 に減らすが
   小さい粒を塗り潰して見逃しを 33 → 99 に増やし、**掃引の全域で素の版より悪い**
   (崖 21.4 → 17.7 %)。
7. ★★**混粒(双峰)を 1 つの G に畳むと、その G の粒はどこにも無い**。左 45 % を
   細粒(真値 G 9.01)、右を粗粒(G 6.15)にした組織の全体 G は 7.82 ——
   切片数の重みで**細粒側に寄る**(調和平均の予測 7.79、面積で重みづけた G の平均
   なら 7.44)。64 px のタイルで局所 G を測ると全体 G ± 0.5 に入るタイルは
   **8 / 64**(単一組織では 43 / 64)。★個々の切片長の累積分布には双峰が**出ない**
   (山 1 個)—— Voronoi の弦長分布は広いので 3 倍違う 2 集団が 1 本の滑らかな
   曲線に溶ける。混粒は**地図**で見るしかない。

【グラウンドトゥルース】
粒は 2-D Voronoi 分割(種は視野の外まで一様に撒く、Poisson 個数)。粒界は種の所属が
変わる画素で、幅 w = 2 px・コントラスト 0.35 で描き、粒ごとの明るさ(エッチングむら
σ 0.10)、光学ぼけ σ 0.6 px、撮像雑音 σ 0.03 を乗せる。途切れは相関長 8 px の乱数場で
粒界画素の f 割を消す(消えた割合は粒界画素で数えて f に合わせる)。真値 ℓ は**真値
ラベルの変化を同じ試験線で数え上げ**た値で、閉形式 π/(4√λ) は検算にだけ使う。
幾何の乱数列と描画(むら・途切れ・雑音)の乱数列は分けてあるので、同じ種で
「むらだけ止めた」対照群が**同じ粒・同じ途切れ**で作れる。

来歴(公開文献のみ): ASTM E112-13 *Standard Test Methods for Determining Average
Grain Size* / ASTM E1181 *Duplex Grain Sizes* / Underwood, *Quantitative
Stereology* (Addison-Wesley, 1970) —— P_L = (2/π) L_A / Møller, *Lectures on
Random Voronoi Tessellations* (Springer, 1994) —— Poisson-Voronoi の L_A = 2√λ、
辺の平均長 2/(3√λ)、1 粒あたり辺 6 本。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, label as nd_label
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import fullseye as fs                                            # noqa: E402

# --- 場面の諸元 -------------------------------------------------------------- #
N_PIX = 512                # 視野 [px]
PX_MM = 0.001              # 1 画素の大きさ [mm/px](1 µm/px = 対物 10x 級)
G_TARGET = 7.0             # 単一組織の狙いの粒度番号
BOUND_W = 2.0              # 粒界の描画幅 [px]
CONTRAST = 0.35            # 粒界のコントラスト(粒の明るさからの落ち込み)
GRAIN_LEVEL = 0.65         # 粒の平均の明るさ
ETCH_SIGMA = 0.10          # エッチングむら = 粒ごとの明るさの σ
NOISE = 0.03               # 撮像雑音 σ
BLUR = 0.6                 # 光学ぼけ σ [px]
GAP_LEN = 8.0              # 途切れの相関長 [px]
MARGIN = 8                 # 試験線を置かない縁 [px](closing が縁を 0 にするため)
N_LINES = 8                # 1 方向あたりの試験線の本数
TOL_PX = 4.0               # 横切りの真値と推定を「同じ」と見なす距離 [px]
SEED = 7
SWEEP_SEEDS = (7, 19, 31)
FINE_FRAC = 0.45           # 混粒: 左からこの割合が細粒
L_FINE_PX, L_COARSE_PX = 14.0, 40.0   # 混粒の 2 集団の平均切片長 [px]
DYN_A, DYN_B = 0.5, 0.75   # dyn_threshold: 窓 7 px、オフセット (b-0.5)*0.4 = +0.10

_LAB = fs.ledger           # blob 族の公開経路
_GEOM_CACHE: dict = {}     # (seed, duplex) -> (labels, seeds)


# --------------------------------------------------------------------------- #
# ASTM E112 の換算                                                              #
# --------------------------------------------------------------------------- #
def g_from_intercept(ell_mm: float) -> float:
    """直線切断法: G = -6.6439 log10(ℓ[mm]) - 3.288。"""
    return -6.6439 * np.log10(ell_mm) - 3.288


def ell_from_g(g: float) -> float:
    """逆変換 [mm]。"""
    return 10.0 ** (-(g + 3.288) / 6.6439)


def g_from_area(n_a_per_mm2: float) -> float:
    """面積法(Jeffries): G = 3.3219 log10(N_A[1/mm²]) - 2.955。"""
    return 3.3219 * np.log10(n_a_per_mm2) - 2.955


# --------------------------------------------------------------------------- #
# 場面を作る —— 真値は「画素ごとの粒の番号」                                     #
# --------------------------------------------------------------------------- #
def _voronoi(n_pix: int, lam_of_col, rng) -> tuple[np.ndarray, np.ndarray]:
    """種を視野の外まで撒き、画素ごとの最近傍の種番号を返す。

    ``lam_of_col(x)`` は列座標 x での種の密度 [1/px²]。混粒はこれで作る。
    ★候補は Poisson(λ_max·面積)個。最初の版は 1.2 倍に水増しして間引かずに使い、
    密度が 20 % 高い組織を「狙い G」だと思い込んだ(閉形式と -10.7 % ずれて発覚)。
    """
    pad = 3 * L_COARSE_PX
    lo, hi = -pad, n_pix + pad
    lam_max = max(lam_of_col(0.0), lam_of_col(float(n_pix)))
    n_cand = int(rng.poisson(lam_max * (hi - lo) ** 2))
    cand = rng.uniform(lo, hi, (n_cand, 2))                # (y, x)
    keep = rng.uniform(0, lam_max, n_cand) < np.asarray([lam_of_col(x) for x in cand[:, 1]])
    seeds = cand[keep]
    yy, xx = np.mgrid[0:n_pix, 0:n_pix]
    pts = np.column_stack([yy.ravel(), xx.ravel()]).astype(np.float64)
    _, idx = cKDTree(seeds).query(pts, k=1)
    return idx.reshape(n_pix, n_pix).astype(np.int32), seeds


def _thin_boundary(labels: np.ndarray) -> np.ndarray:
    """所属が変わる画素(右・下の隣と番号が違う画素、両側)。"""
    b = np.zeros(labels.shape, bool)
    d = labels[:, 1:] != labels[:, :-1]
    b[:, 1:] |= d
    b[:, :-1] |= d
    d = labels[1:, :] != labels[:-1, :]
    b[1:, :] |= d
    b[:-1, :] |= d
    return b


def _break_boundary(soft: np.ndarray, frac: float, rng, gap_len: float = GAP_LEN):
    """粒界画素の ``frac`` 割を、相関長 ``gap_len`` の塊で消す。実際に消した割合も返す。"""
    if frac <= 0.0:
        return soft, 0.0
    field = gaussian_filter(rng.standard_normal(soft.shape), gap_len / 2.0)
    on = soft > 0.0
    thr = np.quantile(field[on], frac)
    keep = field > thr
    out = soft * keep
    removed = 1.0 - float(np.count_nonzero(out > 0)) / float(np.count_nonzero(on))
    return out, removed


def _edge_break_fraction(labels: np.ndarray, thin: np.ndarray, drawn: np.ndarray) -> float:
    """隣り合う粒の対(= 粒界の辺)のうち、途切れを 1 画素でも含む対の割合 p。"""
    gap = thin & ~(drawn > 0)
    n = int(labels.max()) + 1
    pairs, broken = [], []
    for (a, b, ga, gb) in ((labels[:, :-1], labels[:, 1:], gap[:, :-1], gap[:, 1:]),
                           (labels[:-1, :], labels[1:, :], gap[:-1, :], gap[1:, :])):
        m = a != b
        lo, hi = np.minimum(a[m], b[m]), np.maximum(a[m], b[m])
        key = lo.astype(np.int64) * n + hi
        pairs.append(key)
        broken.append(key[ga[m] | gb[m]])
    n_pairs = np.unique(np.concatenate(pairs)).size
    n_broken = np.unique(np.concatenate(broken)).size
    return n_broken / max(n_pairs, 1)


def make_scene(seed: int = SEED, break_frac: float = 0.0, etch: float = ETCH_SIGMA,
               noise: float = NOISE, duplex: bool = False) -> dict:
    """Voronoi 組織を描き、真値(ラベル・種・粒界)と一緒に返す。

    幾何(種の配置)と描画(途切れ・むら・雑音)で乱数列を分けてあるので、同じ
    ``seed`` なら ``etch`` を変えても**同じ粒・同じ途切れ**になる(対照群のため)。
    """
    key = (seed, duplex)
    if key not in _GEOM_CACHE:
        rng_geo = np.random.default_rng(seed)
        if duplex:
            lam_f = (np.pi / (4.0 * L_FINE_PX)) ** 2
            lam_c = (np.pi / (4.0 * L_COARSE_PX)) ** 2
            lam_of_col = lambda x: lam_f if x < FINE_FRAC * N_PIX else lam_c   # noqa: E731
        else:
            ell_px = ell_from_g(G_TARGET) / PX_MM
            lam = (np.pi / (4.0 * ell_px)) ** 2
            lam_of_col = lambda x: lam                                        # noqa: E731
        labels, seeds = _voronoi(N_PIX, lam_of_col, rng_geo)
        thin = _thin_boundary(labels)
        dist = distance_transform_edt(~thin)
        soft = np.clip(BOUND_W / 2.0 + 0.5 - dist, 0.0, 1.0)   # 幅 w、縁 1 px で滑らか
        inside = ((seeds[:, 0] >= 0) & (seeds[:, 0] < N_PIX)
                  & (seeds[:, 1] >= 0) & (seeds[:, 1] < N_PIX))
        _GEOM_CACHE[key] = (labels, seeds[inside], thin, soft)
    labels, seeds, thin, soft = _GEOM_CACHE[key]

    rng = np.random.default_rng(seed + 1000)
    drawn, removed = _break_boundary(soft, break_frac, rng)
    n_lab = int(labels.max()) + 1
    offs = etch * rng.standard_normal(n_lab)
    grain = np.clip(GRAIN_LEVEL + offs, 0.35, 0.95)[labels]
    img = grain - CONTRAST * drawn
    img = gaussian_filter(img, BLUR)
    img = img + noise * rng.standard_normal(img.shape)
    return {"img": np.clip(img, 0.0, 1.0), "labels": labels, "thin": thin,
            "drawn": drawn, "seeds": seeds, "removed": removed}


def gap_lengths(scene: dict) -> np.ndarray:
    """途切れの塊ごとの画素数(8 近傍)。closing で閉じられる長さかを判断する材料。"""
    gap = scene["thin"] & ~(scene["drawn"] > 0)
    lab, n = nd_label(gap, structure=np.ones((3, 3)))
    return np.bincount(lab.ravel())[1:] if n else np.zeros(0)


# --------------------------------------------------------------------------- #
# 試験線 —— 4 方向、真値も推定も同じ線で数える                                  #
# --------------------------------------------------------------------------- #
def test_lines(n_pix: int = N_PIX, margin: int = MARGIN, n_lines: int = N_LINES,
               r0: int = 0, c0: int = 0, size: int | None = None) -> list[dict]:
    """``(rows, cols, length_px)`` の列。水平・垂直・2 本の対角線。"""
    size = n_pix if size is None else size
    a, b = margin, size - margin
    span = b - a
    lines = []
    pos = np.linspace(a + span / (2 * n_lines), b - span / (2 * n_lines), n_lines)
    for p in np.round(pos).astype(int):
        cc = np.arange(a, b)
        lines.append({"r": np.full_like(cc, p) + r0, "c": cc + c0, "len": float(span)})
        rr = np.arange(a, b)
        lines.append({"r": rr + r0, "c": np.full_like(rr, p) + c0, "len": float(span)})
    offs = np.linspace(-0.8 * span, 0.8 * span, n_lines)
    for o in np.round(offs).astype(int):
        t = np.arange(a, b)
        r1, c1 = t, t + o                         # 45°
        ok = (c1 >= a) & (c1 < b)
        lines.append({"r": r1[ok] + r0, "c": c1[ok] + c0, "len": float(ok.sum()) * np.sqrt(2)})
        r2, c2 = t, (b - 1) - (t - a) + o         # 135°
        ok = (c2 >= a) & (c2 < b)
        lines.append({"r": r2[ok] + r0, "c": c2[ok] + c0, "len": float(ok.sum()) * np.sqrt(2)})
    return [ln for ln in lines if ln["r"].size > 8]


def _clip_lines(lines: list[dict], c_lo: int, c_hi: int) -> list[dict]:
    """試験線を列の範囲 ``[c_lo, c_hi)`` に切り詰める(混粒の領域別 G 用)。"""
    out = []
    for ln in lines:
        ok = (ln["c"] >= c_lo) & (ln["c"] < c_hi)
        if ok.sum() < 5:
            continue
        step = np.sqrt(2) if (np.ptp(ln["r"][ok]) > 0 and np.ptp(ln["c"][ok]) > 0) else 1.0
        out.append({"r": ln["r"][ok], "c": ln["c"][ok], "len": float(ok.sum()) * step})
    return out


def _truth_crossings(labels: np.ndarray, ln: dict) -> np.ndarray:
    v = labels[ln["r"], ln["c"]]
    return np.nonzero(v[1:] != v[:-1])[0] + 0.5


def _run_centers(mask: np.ndarray, ln: dict) -> np.ndarray:
    v = mask[ln["r"], ln["c"]] > 0.5
    if v.size == 0:
        return np.zeros(0)
    d = np.diff(np.concatenate([[False], v, [False]]).astype(np.int8))
    starts = np.nonzero(d == 1)[0]
    ends = np.nonzero(d == -1)[0]
    return (starts + ends - 1) / 2.0


def _match_1d(truth: np.ndarray, est: np.ndarray, tol: float) -> tuple[int, int, int]:
    """並び順を保った貪欲対応。(一致, 見逃し, 偽) を返す。"""
    ti = ei = matched = 0
    while ti < truth.size and ei < est.size:
        d = est[ei] - truth[ti]
        if abs(d) <= tol:
            matched += 1
            ti += 1
            ei += 1
        elif d < 0:
            ei += 1
        else:
            ti += 1
    return matched, int(truth.size - matched), int(est.size - matched)


def intercept_stats(labels: np.ndarray, mask: np.ndarray | None, lines: list[dict]) -> dict:
    """真値(ラベル変化)と推定(黒線の走り)の横切りを同じ線で数える。"""
    total_len = sum(ln["len"] for ln in lines)
    n_true = n_est = matched = missed = false = 0
    seg_true = []
    for ln in lines:
        t = _truth_crossings(labels, ln)
        n_true += t.size
        seg_true.extend(np.diff(t).tolist())
        if mask is not None:
            e = _run_centers(mask, ln)
            n_est += e.size
            m, mi, fa = _match_1d(t, e, TOL_PX)
            matched += m
            missed += mi
            false += fa
    out = {"len_px": total_len, "n_true": n_true, "ell_true_px": total_len / max(n_true, 1),
           "seg_true": np.asarray(seg_true)}
    if mask is not None:
        out.update({"n_est": n_est, "ell_est_px": total_len / max(n_est, 1),
                    "matched": matched, "missed": missed, "false": false})
    return out


def g_intercept(labels: np.ndarray, mask: np.ndarray, lines: list[dict]) -> float:
    return g_from_intercept(intercept_stats(labels, mask, lines)["ell_est_px"] * PX_MM)


# --------------------------------------------------------------------------- #
# 推定器                                                                       #
# --------------------------------------------------------------------------- #
def boundary_masks(img: np.ndarray, close_b: float | None = None) -> dict:
    """fullseye の op で粒界を抜く 2 通り。

    * ``bothat``: ``gray_bothat``(7x7、**最大値で正規化**)→ ``threshold`` 0.5。
    * ``dyn``: ``invert_image`` → ``dyn_threshold``(窓 7 px、局所平均 + 0.10 を
      超えた画素 = 周りより **絶対値で** 0.10 以上暗い画素)。
    ``close_b`` を渡すと ``dyn`` に ``hx_close_edges`` を掛けた ``closed`` も返す。
    """
    bh = np.asarray(fs.apply(img, "gray_bothat", a=0.5))
    out = {"bothat_resp": bh, "bothat": np.asarray(fs.apply(bh, "threshold", a=0.5))}
    inv = np.asarray(fs.apply(img, "invert_image"))
    out["inv"] = inv
    out["dyn"] = np.asarray(fs.apply(inv, "dyn_threshold", a=DYN_A, b=DYN_B))
    if close_b is not None:
        out["closed"] = np.asarray(fs.apply(out["dyn"], "hx_close_edges", a=0.5, b=close_b))
    return out


def area_method(img: np.ndarray, scene: dict) -> dict:
    """ゼロ点: 大津の二値化 → 連結成分 → Jeffries の N_A → G。壊れ方も数える。"""
    bw = np.asarray(fs.apply(img, "bin_threshold")) > 0.5           # 明るい側 = 粒
    lab = _LAB.blob_label(bw, connectivity=4)
    f = _LAB.blob_features(lab, spacing=PX_MM)
    touch = np.asarray(f["touches_border"], bool)
    n_eff = float((~touch).sum()) + 0.5 * float(touch.sum())
    n_a = n_eff / (N_PIX * PX_MM) ** 2
    sr = np.clip(np.round(scene["seeds"][:, 0]).astype(int), 0, N_PIX - 1)
    sc = np.clip(np.round(scene["seeds"][:, 1]).astype(int), 0, N_PIX - 1)
    owner = lab[sr, sc]
    lost = int(np.count_nonzero(owner == 0))
    cnt = np.bincount(owner[owner > 0], minlength=int(lab.max()) + 1)[1:]
    merged = int(np.count_nonzero(cnt >= 2))
    swallowed = int(np.sum(cnt[cnt >= 2] - 1))
    # 種の無い塊 = 粉々になった欠片。縁の塊は種が視野の外にあるだけなので除く。
    fragments = int(np.count_nonzero((cnt == 0) & ~touch))
    return {"labels": lab, "n_blobs": int(f["n"]), "n_a": n_a, "g": g_from_area(n_a),
            "lost": lost, "merged": merged, "swallowed": swallowed, "fragments": fragments,
            "mask": bw}


def truth_summary(scene: dict, lines: list[dict]) -> dict:
    st = intercept_stats(scene["labels"], None, lines)
    n_a = scene["seeds"].shape[0] / (N_PIX * PX_MM) ** 2
    return {"ell_px": st["ell_true_px"], "g_l": g_from_intercept(st["ell_true_px"] * PX_MM),
            "g_a": g_from_area(n_a), "n_true": st["n_true"], "seg": st["seg_true"]}


# --------------------------------------------------------------------------- #
# 1. 真値の検算 —— 閉形式と数え上げ、E112 の 2 式のずれ                          #
# --------------------------------------------------------------------------- #
def section_truth() -> dict:
    print("\n" + "=" * 78)
    print("1) 真値の検算 —— Poisson-Voronoi の閉形式 vs 真値粒界での数え上げ")
    print("=" * 78)
    lines = test_lines()
    devs, gl, ga = [], [], []
    ell_pred = ell_from_g(G_TARGET) / PX_MM
    for sd in SWEEP_SEEDS:
        sc = make_scene(sd)
        tr = truth_summary(sc, lines)
        devs.append(100 * (tr["ell_px"] - ell_pred) / ell_pred)
        gl.append(tr["g_l"])
        ga.append(tr["g_a"])
        print("  種 %2d: 粒 %3d 個 / 横切り %4d 回 / ℓ 真値 %.2f px (閉形式 %.2f px, %+.1f %%)"
              "  G_L %.2f  G_A %.2f" % (sd, sc["seeds"].shape[0], tr["n_true"], tr["ell_px"],
                                       ell_pred, devs[-1], tr["g_l"], tr["g_a"]))
    offset_pred = -6.6439 * np.log10((np.pi / 4.0) / 0.8910)
    print("\n  閉形式との差 平均 %+.1f %% / E112 の 2 式の差 G_L - G_A = %+.2f(予測 %+.2f: "
          "ℓ/√A が Voronoi では π/4、E112 の暗黙値は 0.891)"
          % (np.mean(devs), np.mean(gl) - np.mean(ga), offset_pred))
    broken = make_scene(SEED, break_frac=0.30)
    gl_px = gap_lengths(broken)
    edge_mean = 2.0 / (3.0 * np.sqrt((np.pi / (4.0 * ell_pred)) ** 2))
    print("  途切れ 30 %% の隙間: %d 塊、中央値 %.0f px、平均 %.1f px(粒界の辺の平均長は "
          "2/(3√λ) = %.1f px)" % (gl_px.size, np.median(gl_px), gl_px.mean(), edge_mean))

    sc = make_scene(SEED)
    clean = make_scene(SEED, etch=0.0, noise=0.0)
    figs.save_grid("scene", [clean["img"], sc["img"], sc["thin"].astype(float), broken["img"]],
                   ["粒界完全・むら無し・雑音無し", "エッチングむら σ0.10 + 雑音 σ0.03",
                    "真値の粒界(所属が変わる画素)", "粒界の途切れ 30 %%(実測 %.1f %%)"
                    % (100 * broken["removed"])],
                   title="金相写真の合成場面(1 px = %.0f µm、狙い G = %.0f)"
                         % (PX_MM * 1000, G_TARGET))
    return {"dev": float(np.mean(devs)), "g_l": float(np.mean(gl)), "g_a": float(np.mean(ga)),
            "offset": float(np.mean(gl) - np.mean(ga)), "offset_pred": float(offset_pred),
            "gap_median": float(np.median(gl_px)), "edge_mean": float(edge_mean)}


# --------------------------------------------------------------------------- #
# 2-3. 対照群 —— むら / 雑音 / 途切れを 1 つずつ止める                            #
# --------------------------------------------------------------------------- #
def section_controls() -> dict:
    print("\n" + "=" * 78)
    print("2-3) 対照群 —— 面積法(ゼロ点)と切片法 2 通りを、要因を 1 つずつ止めて比べる")
    print("=" * 78)
    lines = test_lines()
    conds = [("完全・むら無し・雑音無し", dict(etch=0.0, noise=0.0)),
             ("+ 雑音のみ", dict(etch=0.0)),
             ("+ むらのみ", dict(noise=0.0)),
             ("+ むら + 雑音", dict()),
             ("+ むら + 雑音 + 途切れ 20 %", dict(break_frac=0.20))]
    rows, out = [], {}
    print("  条件                        真値G_L  面積法(誤差)   ボトムハット(誤差)  局所しきい値(誤差)  消えた粒/欠片  見逃し/偽(局所)")
    for name, kw in conds:
        sc = make_scene(SEED, **kw)
        tr = truth_summary(sc, lines)
        am = area_method(sc["img"], sc)
        bm = boundary_masks(sc["img"])
        s_bh = intercept_stats(sc["labels"], bm["bothat"], lines)
        s_dy = intercept_stats(sc["labels"], bm["dyn"], lines)
        g_bh = g_from_intercept(s_bh["ell_est_px"] * PX_MM)
        g_dy = g_from_intercept(s_dy["ell_est_px"] * PX_MM)
        e_a, e_b, e_d = am["g"] - tr["g_a"], g_bh - tr["g_l"], g_dy - tr["g_l"]
        short = int(np.count_nonzero(tr["seg"] < TOL_PX))
        out[name] = {"err_area": e_a, "err_bothat": e_b, "err_dyn": e_d, "lost": am["lost"],
                     "fragments": am["fragments"], "missed": s_dy["missed"],
                     "false": s_dy["false"], "short": short}
        rows.append([name, "%.2f" % tr["g_l"], "%.2f (%+.2f)" % (am["g"], e_a),
                     "%.2f (%+.2f)" % (g_bh, e_b), "%.2f (%+.2f)" % (g_dy, e_d),
                     "%d / %d" % (am["lost"], am["fragments"]),
                     "%d / %d" % (s_dy["missed"], s_dy["false"])])
        print("  %-26s  %.2f   %5.2f (%+.2f)   %5.2f (%+.2f)      %5.2f (%+.2f)       %3d / %4d      %3d / %3d"
              % (name, tr["g_l"], am["g"], e_a, g_bh, e_b, g_dy, e_d, am["lost"],
                 am["fragments"], s_dy["missed"], s_dy["false"]))
    c0 = out["完全・むら無し・雑音無し"]
    print("\n  ★面積法は「むら × 雑音」の相互作用で死ぬ: 雑音だけ %+.2f / むらだけ %+.2f / 両方 %+.2f。"
          % (out["+ 雑音のみ"]["err_area"], out["+ むらのみ"]["err_area"],
             out["+ むら + 雑音"]["err_area"]))
    print("     大津のしきい値が「暗い粒 vs 明るい粒」の谷に落ち、しきい値付近の粒が雑音で"
          "粉々になる(欠片 %d 個)。" % out["+ むら + 雑音"]["fragments"])
    print("  ★ボトムハットはむらだけで %+.2f、局所しきい値は %+.2f —— 最大値で正規化すると"
          "小さい暗い粒 1 個が\n     しきい値を決めて弱い粒界を落とす。むらに強いのは「周りとの絶対差」。"
          % (out["+ むらのみ"]["err_bothat"], out["+ むらのみ"]["err_dyn"]))
    print("  完全な粒界でも見逃し %d 件: 真値の弦のうち %d 本は %g px より短く、幅 %g px + ぼけの"
          "黒線 1 本に溶ける。" % (c0["missed"], c0["short"], TOL_PX, BOUND_W))
    figs.save_table("controls", ["条件", "真値 G_L", "面積法 G(誤差)", "切片・ボトムハット G(誤差)",
                                 "切片・局所しきい値 G(誤差)", "消えた粒 / 欠片", "見逃し / 偽"],
                    rows, title="対照群: 要因を 1 つずつ止めたときの G(面積法は G_A の真値と比較)")

    # 段階の図(むら + 雑音 + 途切れ 20 %)
    sc = make_scene(SEED, break_frac=0.20)
    bm = boundary_masks(sc["img"], close_b=1.0)
    am = area_method(sc["img"], sc)
    crop = (slice(64, 256), slice(64, 256))
    rgb = np.repeat(sc["img"][crop][..., None], 3, axis=-1)
    m = bm["dyn"][crop] > 0.5
    rgb[m] = (0.95, 0.35, 0.2)
    for ln in test_lines(size=192, margin=4, n_lines=3):
        rgb[ln["r"], ln["c"]] = (0.2, 0.4, 1.0)
        for p in _truth_crossings(sc["labels"][crop], ln):
            k = int(p)
            r, c = ln["r"][k], ln["c"][k]
            rgb[max(r - 1, 0):r + 2, max(c - 1, 0):c + 2] = (0.1, 0.9, 0.2)
    zoom = np.kron(rgb, np.ones((2, 2, 1)))
    figs.save_grid("stages_intercept",
                   [bm["bothat_resp"], bm["bothat"], bm["dyn"], zoom],
                   ["gray_bothat(7x7、最大値で正規化)", "bothat → threshold 0.5",
                    "invert_image → dyn_threshold(窓 7、+0.10)",
                    "試験線(青)・真値の横切り(緑)・抜いた粒界(赤)"],
                   title="切片法の段階(むら + 雑音 + 途切れ 20 %)")
    figs.save_grid("stages_area",
                   [am["mask"].astype(float), _LAB.blob_overlay(sc["img"], am["labels"])],
                   ["bin_threshold(大津)で明るい側 = 粒", "連結成分 %d 個(消えた粒 %d・欠片 %d)"
                    % (am["n_blobs"], am["lost"], am["fragments"])],
                   title="面積法(ゼロ点)の段階 —— しきい値付近の粒が粉々になる")
    return out


# --------------------------------------------------------------------------- #
# 4-6. 崖 —— 途切れ率を掃引し、壊れ方を種類ごとに数える                          #
# --------------------------------------------------------------------------- #
def section_cliff(gap_median: float, edge_mean: float) -> dict:
    print("\n" + "=" * 78)
    print("4-6) 崖 —— 粒界の途切れ率 0 → 60 % で G が 1 段ずれる点")
    print("=" * 78)
    lines = test_lines()
    fracs = np.arange(0.0, 0.601, 0.05)
    keys = ("area", "raw", "closed")
    err = {k: [] for k in keys}
    fail = {"missed_raw": [], "false_raw": [], "missed_closed": [], "false_closed": [],
            "merged": [], "swallowed": [], "lost": [], "p_edge": [], "hole": []}
    print("  途切れ  面積法ΔG(むら無し)  切片(素)ΔG  切片(閉)ΔG  マスク上の途切れ  辺の途切れ率p  見逃し/偽(素)  見逃し/偽(閉)  融合/飲まれ")
    for f in fracs:
        acc = {k: [] for k in list(err) + list(fail)}
        for sd in SWEEP_SEEDS:
            sc = make_scene(sd, break_frac=float(f))                # むら + 雑音(本番)
            sc0 = make_scene(sd, break_frac=float(f), etch=0.0)     # むらを止めた対照群
            tr = truth_summary(sc, lines)
            bm = boundary_masks(sc["img"], close_b=1.0)
            s_raw = intercept_stats(sc["labels"], bm["dyn"], lines)
            s_cl = intercept_stats(sc["labels"], bm["closed"], lines)
            am = area_method(sc0["img"], sc0)
            acc["area"].append(am["g"] - tr["g_a"])
            acc["raw"].append(g_from_intercept(s_raw["ell_est_px"] * PX_MM) - tr["g_l"])
            acc["closed"].append(g_from_intercept(s_cl["ell_est_px"] * PX_MM) - tr["g_l"])
            acc["missed_raw"].append(s_raw["missed"])
            acc["false_raw"].append(s_raw["false"])
            acc["missed_closed"].append(s_cl["missed"])
            acc["false_closed"].append(s_cl["false"])
            acc["merged"].append(am["merged"])
            acc["swallowed"].append(am["swallowed"])
            acc["lost"].append(am["lost"])
            acc["p_edge"].append(_edge_break_fraction(sc0["labels"], sc0["thin"], sc0["drawn"]))
            # マスク上の途切れ率: 真値粒界の画素のうち、抜いた粒界マスクが 0 の割合
            acc["hole"].append(1.0 - float(np.mean(bm["dyn"][sc["thin"]] > 0.5)))
        for k in err:
            err[k].append(float(np.mean(acc[k])))
        for k in fail:
            fail[k].append(float(np.mean(acc[k])))
        print("   %4.0f %%      %+6.2f          %+6.2f      %+6.2f        %5.1f %%       %5.0f / %4.0f     %5.0f / %4.0f    %4.0f / %4.0f"
              % (100 * f, err["area"][-1], err["raw"][-1], err["closed"][-1],
                 100 * fail["p_edge"][-1], fail["missed_raw"][-1], fail["false_raw"][-1],
                 fail["missed_closed"][-1], fail["false_closed"][-1],
                 fail["merged"][-1], fail["swallowed"][-1]))

    # --- 予測 --------------------------------------------------------------- #
    # 切片法: 横切りが (1-f) 倍 → ΔG = 6.64 log10(1-f)。素朴な崖は f = 1 - 1/√2。
    #   ただし f = 0 でも短い弦が溶けて ΔG0 から始まるので、そこを足した予測が正しい。
    dg0 = err["raw"][0]
    pred_raw_naive = 6.6439 * np.log10(1.0 - fracs)
    pred_raw = dg0 + pred_raw_naive
    cliff_pred_raw_naive = 100 * (1.0 - 2 ** -0.5)
    cliff_pred_raw = 100 * (1.0 - 10 ** ((-1.0 - dg0) / 6.6439))
    # 面積法: 木近似で塊の数は N(1 - 3p)(1 粒あたり辺 6 本 = 辺 3N 本、途切れた辺で 2 粒が 1 塊)。
    #   p は実測の「辺の途切れ率」。1 段 = 塊が半分 = p = 1/6。
    p = np.asarray(fail["p_edge"])
    pred_area = np.where(1.0 - 3.0 * p > 0.05, 3.3219 * np.log10(np.maximum(1.0 - 3.0 * p, 0.05)), np.nan)
    cliff_pred_area = float(np.interp(1.0 / 6.0, p, 100 * fracs)) if p.max() > 1 / 6 else float("nan")
    p_over_f = float(np.mean(p[1:4] / fracs[1:4]))

    def first_cliff(e):
        """|ΔG| が初めて 1 を超える途切れ率 [%](線形補間)。"""
        e = np.asarray(e)
        idx = np.nonzero(np.abs(e) >= 1.0)[0]
        if idx.size == 0:
            return float("nan")
        i = idx[0]
        if i == 0:
            return 0.0
        x0, x1 = 100 * fracs[i - 1], 100 * fracs[i]
        y0, y1 = abs(e[i - 1]), abs(e[i])
        return float(x0 + (1.0 - y0) / (y1 - y0) * (x1 - x0))

    cliff = {k: first_cliff(err[k]) for k in keys}
    raw_dev = float(np.max(np.abs(np.asarray(err["raw"]) - pred_raw)))
    worse = [100 * f for f, a, b in zip(fracs, err["raw"], err["closed"]) if abs(b) > abs(a)]
    print("\n  ★崖(|ΔG| >= 1 になる途切れ率): 面積法 %.1f %% / 切片法(素) %.1f %% / 切片法(閉) %.1f %%"
          % (cliff["area"], cliff["raw"], cliff["closed"]))
    print("     切片法の予想は %.1f %%(横切り (1-f) 倍)だったが、途切れ 0 %% で既に ΔG = %+.2f"
          "(短い弦が溶ける)なので\n     補正した予測は %.1f %%。実測曲線は補正した予測と最大 %.2f 段で並走。"
          % (cliff_pred_raw_naive, dg0, cliff_pred_raw, raw_dev))
    print("     面積法: 辺の途切れ率 p は f の %.1f 倍で走る(隙間 1 塊が頂点で 2〜3 辺を同時に開く)。"
          "木近似 N(1-3p) で 1 段の点は f = %.1f %%、実測 %.1f %%(閉路の分だけ木近似と違う)。"
          % (p_over_f, cliff_pred_area, cliff["area"]))
    print("  ★閉じる(closing 9x9、閉じられる隙間 8 px 以下)は隙間の中央値 %.0f px に届かず、"
          "小さい粒を塗り潰す:\n     途切れ 0 %% の見逃し %.0f → %.0f、偽 %.0f → %.0f。"
          "掃引 %d 点中 %d 点で素の版より悪い。"
          % (gap_median, fail["missed_raw"][0], fail["missed_closed"][0], fail["false_raw"][0],
             fail["false_closed"][0], len(fracs), len(worse)))

    x = 100 * fracs
    figs.save_plot("cliff_break_sweep",
                   [("面積法(大津 + 連結成分、むら無し)", x, err["area"]),
                    ("切片法(局所しきい値、素)", x, err["raw"]),
                    ("切片法(+ closing 9x9)", x, err["closed"]),
                    ("1 段 = -1", x, [-1.0] * len(x))],
                   xlabel="粒界の途切れ率 f [%]", ylabel="G の誤差 ΔG [段]",
                   title="崖: 面積法は %.0f %%、切片法は %.0f %% で 1 段落ちる"
                         % (cliff["area"], cliff["raw"]),
                   ylim=(-4.5, 0.5),
                   caption="面積法は 1 本の途切れで 2 粒が融合するので、切片法の 3 分の 1 の途切れで 1 段落ちる。")
    figs.save_plot("cliff_prediction",
                   [("切片法 実測", x, err["raw"]), ("切片法 予測 ΔG0 + 6.64 log10(1-f)", x, pred_raw),
                    ("面積法 実測", x, err["area"]), ("面積法 予測 3.32 log10(1-3p)", x, pred_area)],
                   xlabel="粒界の途切れ率 f [%]", ylabel="G の誤差 ΔG [段]",
                   title="幾何で先に立てた予測との突き合わせ", ylim=(-4.5, 0.5))
    figs.save_plot("failure_intercept",
                   [("見逃し(素)", x, fail["missed_raw"]), ("偽(素)", x, fail["false_raw"]),
                    ("見逃し(閉)", x, fail["missed_closed"]), ("偽(閉)", x, fail["false_closed"])],
                   xlabel="粒界の途切れ率 f [%]", ylabel="横切りの件数(3 種の平均)",
                   title="切片法の壊れ方: 見逃しは f に比例、偽は平ら")
    figs.save_plot("failure_area",
                   [("融合した塊", x, fail["merged"]), ("飲まれた粒", x, fail["swallowed"]),
                    ("辺の途切れ率 p [%]", x, 100 * p)],
                   xlabel="粒界の途切れ率 f [%]", ylabel="件数(3 種の平均)/ p [%]",
                   title="面積法の壊れ方: 融合は塊の数より飲まれた粒の数で効く")
    return {"fracs": fracs, "err": err, "fail": fail, "cliff": cliff, "dg0": dg0,
            "cliff_pred_area": cliff_pred_area, "cliff_pred_raw": cliff_pred_raw,
            "cliff_pred_raw_naive": cliff_pred_raw_naive, "raw_dev": raw_dev,
            "n_worse": len(worse), "p_over_f": p_over_f}


# --------------------------------------------------------------------------- #
# 7. 混粒 —— 1 つの G に畳むと消えるもの                                          #
# --------------------------------------------------------------------------- #
def _tile_map(labels: np.ndarray, mask: np.ndarray, tile: int = 64) -> np.ndarray:
    n = N_PIX // tile
    out = np.full((n, n), np.nan)
    for i in range(n):
        for j in range(n):
            lines = test_lines(size=tile, margin=2, n_lines=3, r0=i * tile, c0=j * tile)
            out[i, j] = g_intercept(labels, mask, lines)
    return out


def section_duplex() -> dict:
    print("\n" + "=" * 78)
    print("7) 混粒 —— 細粒 + 粗粒を 1 つの G に畳むと、その G の粒はどこにも無い")
    print("=" * 78)
    lines = test_lines()
    dup = make_scene(SEED, duplex=True)
    single = make_scene(SEED)
    tr = truth_summary(dup, lines)
    tr_s = truth_summary(single, lines)
    m_dup = boundary_masks(dup["img"])["dyn"]
    m_single = boundary_masks(single["img"])["dyn"]
    st = intercept_stats(dup["labels"], m_dup, lines)
    g_est = g_from_intercept(st["ell_est_px"] * PX_MM)
    g_single = g_intercept(single["labels"], m_single, lines)

    split = int(FINE_FRAC * N_PIX)
    g_f = g_from_intercept(intercept_stats(dup["labels"], None, _clip_lines(lines, 0, split))["ell_true_px"] * PX_MM)
    g_c = g_from_intercept(intercept_stats(dup["labels"], None, _clip_lines(lines, split, N_PIX))["ell_true_px"] * PX_MM)
    ell_f, ell_c = ell_from_g(g_f), ell_from_g(g_c)
    ell_mix_pred = 1.0 / (FINE_FRAC / ell_f + (1 - FINE_FRAC) / ell_c)
    g_mix_pred = g_from_intercept(ell_mix_pred)
    g_area_weighted = FINE_FRAC * g_f + (1 - FINE_FRAC) * g_c
    print("  真値: 細粒 G %.2f(左 %.0f %%)/ 粗粒 G %.2f / 全体 G_L %.2f(調和平均の予測 %.2f、"
          "面積で重みづけた G の平均 %.2f)" % (g_f, 100 * FINE_FRAC, g_c, tr["g_l"], g_mix_pred,
                                             g_area_weighted))
    print("  切片法(局所しきい値)の推定 G %.2f(誤差 %+.2f、単一組織では %+.2f)"
          % (g_est, g_est - tr["g_l"], g_single - tr_s["g_l"]))

    tm_dup = _tile_map(dup["labels"], m_dup)
    tm_single = _tile_map(single["labels"], m_single)
    in_dup = int(np.count_nonzero(np.abs(tm_dup - g_est) <= 0.5))
    in_single = int(np.count_nonzero(np.abs(tm_single - g_single) <= 0.5))
    n_tiles = tm_dup.size
    nf = int(FINE_FRAC * tm_dup.shape[1])
    print("  64 px タイルの局所 G が全体 G ± 0.5 に入る数: 混粒 %d / %d(単一組織 %d / %d)"
          % (in_dup, n_tiles, in_single, n_tiles))
    print("     混粒のタイル G: 左 %.2f ± %.2f / 右 %.2f ± %.2f"
          % (np.nanmean(tm_dup[:, :nf]), np.nanstd(tm_dup[:, :nf]),
             np.nanmean(tm_dup[:, nf + 1:]), np.nanstd(tm_dup[:, nf + 1:])))

    seg_d, seg_s = tr["seg"], tr_s["seg"]

    def band(seg, ell):
        return float(np.mean((seg >= ell / np.sqrt(2)) & (seg <= ell * np.sqrt(2))))

    def n_modes(seg):
        h, _ = np.histogram(np.log(seg[seg > 0]), bins=16)
        h = np.convolve(h, [1, 2, 1], mode="same")
        return int(np.count_nonzero((h[1:-1] > h[:-2]) & (h[1:-1] >= h[2:])))
    frac_d, frac_s = band(seg_d, tr["ell_px"]), band(seg_s, tr_s["ell_px"])
    modes_d, modes_s = n_modes(seg_d), n_modes(seg_s)
    print("  個々の切片長が ℓ/√2 〜 ℓ√2 に入る割合: 混粒 %.1f %% / 単一 %.1f %%、"
          "対数ヒストグラムの山の数: 混粒 %d / 単一 %d" % (100 * frac_d, 100 * frac_s,
                                                    modes_d, modes_s))

    lo, hi = min(g_f, g_c) - 0.5, max(g_f, g_c) + 0.5

    def norm(t):
        v = np.clip((np.nan_to_num(t, nan=lo) - lo) / (hi - lo), 0, 1)
        return np.kron(v, np.ones((N_PIX // t.shape[0], N_PIX // t.shape[1])))
    figs.save_grid("duplex_map",
                   [dup["img"], norm(tm_dup), _LAB.blob_overlay(dup["img"], dup["labels"] + 1),
                    norm(tm_single)],
                   ["混粒: 左 %.0f %% が細粒 G %.1f、右が粗粒 G %.1f" % (100 * FINE_FRAC, g_f, g_c),
                    "局所 G の地図(64 px タイル、暗 %.1f → 明 %.1f)、全体 G = %.2f" % (lo, hi, g_est),
                    "真値の粒の所属", "単一組織の局所 G(同じ色尺、全体 G = %.2f)" % g_single],
                   title="混粒を 1 つの G に畳むと消えるもの")
    sd, ss = np.sort(seg_d), np.sort(seg_s)
    figs.save_plot("intercept_cdf",
                   [("混粒(細 %.0f px + 粗 %.0f px)" % (ell_f / PX_MM, ell_c / PX_MM), sd,
                     np.linspace(0, 1, sd.size)),
                    ("単一組織(ℓ %.0f px)" % tr_s["ell_px"], ss, np.linspace(0, 1, ss.size))],
                   xlabel="個々の切片長 [px]", ylabel="累積割合",
                   title="切片長の累積分布に双峰は出ない(山 %d 個)" % modes_d)
    rows = [["細粒(左 %.0f %%)" % (100 * FINE_FRAC), "%.2f" % g_f, "%.1f" % (ell_f / PX_MM)],
            ["粗粒(右)", "%.2f" % g_c, "%.1f" % (ell_c / PX_MM)],
            ["全体(真値・切片法)", "%.2f" % tr["g_l"], "%.1f" % tr["ell_px"]],
            ["全体(調和平均の予測)", "%.2f" % g_mix_pred, "%.1f" % (ell_mix_pred / PX_MM)],
            ["全体(面積重みの G 平均)", "%.2f" % g_area_weighted, "-"],
            ["全体(推定・局所しきい値)", "%.2f" % g_est, "%.1f" % st["ell_est_px"]],
            ["全体 G ± 0.5 のタイル", "%d / %d" % (in_dup, n_tiles), "-"]]
    figs.save_table("duplex_table", ["量", "G", "ℓ [µm]"], rows, title="混粒の G の内訳")
    return {"g_f": g_f, "g_c": g_c, "g_mix": tr["g_l"], "g_mix_pred": g_mix_pred,
            "g_area_weighted": g_area_weighted, "g_est": g_est, "in_dup": in_dup,
            "in_single": in_single, "n_tiles": n_tiles, "frac_d": frac_d, "frac_s": frac_s,
            "modes_d": modes_d}


# --------------------------------------------------------------------------- #
# 8. 道具の穴 —— 使ってみて分かった残り                                          #
# --------------------------------------------------------------------------- #
def section_tool_gaps(ctrl: dict) -> None:
    print("\n" + "=" * 78)
    print("8) 道具の穴(この PoC で fullseye の op を使ってみて)")
    print("=" * 78)
    assert not hasattr(fs, "intercept_count") and not hasattr(fs.ledger, "intercept_count")
    print("  (a) 試験線に沿って横切りを数える op(E112 の直線切断法)が無い。"
          "この PoC は numpy で書いた。")
    img = np.full((64, 64), 0.7)
    img[30:32, :] = 0.3
    o = np.asarray(fs.apply(img, "otsu"))
    b = np.asarray(fs.apply(img, "bin_threshold"))
    print("  (b) `otsu` は 0.3/0.7 の 2 値画像で前景率 %.3f(`bin_threshold` は %.3f)。"
          "同じ大津法を名乗る 2 op で結果が違う(バグ疑い、この PoC は bin_threshold を使用)。"
          % (o.mean(), b.mean()))
    print("  (c) `gray_bothat` は最大値で正規化するので、しきい値が画像内の最大応答 1 点に"
          "依存する(むらのみで %+.2f 段、局所しきい値は %+.2f)。絶対値のまま返す口が無い。"
          % (ctrl["+ むらのみ"]["err_bothat"], ctrl["+ むらのみ"]["err_dyn"]))
    m = np.ones((20, 20))
    c = np.asarray(fs.apply(m, "hx_close_edges", a=0.5, b=1.0))
    print("  (d) hx_close_edges(9x9)は全面 1 の 20x20 で残るのが %d x %d —— 縁 4 px の帯が"
          "必ず 0 になる(文書どおり)。試験線を縁から %d px 離した理由。"
          % (int(c.sum(axis=0).max()), int(c.sum(axis=1).max()), MARGIN))
    assert "touches_border" in _LAB.blob_features(_LAB.blob_label(np.ones((4, 4), bool)))
    print("  (e) blob_features は touches_border を返すが、縁の粒を半分に数える(Jeffries)"
          "規約は呼び手が組む。")


# --------------------------------------------------------------------------- #
def main() -> int:
    t0 = time.perf_counter()
    print("=" * 78)
    print("金属組織の結晶粒度(ASTM E112)—— 面積法と切片法の壊れ方は違う")
    print("視野 %d px x %.0f µm/px = %.3f mm 角 / 狙い G = %.0f(ℓ = %.1f µm)" % (
        N_PIX, PX_MM * 1000, N_PIX * PX_MM, G_TARGET, ell_from_g(G_TARGET) * 1000))
    print("=" * 78)

    tr = section_truth()
    ctrl = section_controls()
    cliff = section_cliff(tr["gap_median"], tr["edge_mean"])
    dup = section_duplex()
    section_tool_gaps(ctrl)

    print("\n" + "=" * 78)
    print("まとめ")
    print("=" * 78)
    print("  * 真値の閉形式と数え上げは %+.1f %%。E112 の 2 式は同じ組織で %+.2f 段ずれる"
          "(予測 %+.2f)。" % (tr["dev"], tr["offset"], tr["offset_pred"]))
    print("  * 面積法(ゼロ点)は雑音だけ %+.2f / むらだけ %+.2f / 両方 %+.2f —— 相互作用。"
          % (ctrl["+ 雑音のみ"]["err_area"], ctrl["+ むらのみ"]["err_area"],
             ctrl["+ むら + 雑音"]["err_area"]))
    print("  * 崖: 面積法 %.1f %% / 切片法(素) %.1f %%(補正した予測 %.1f %%)/ 切片法(閉) %.1f %%。"
          % (cliff["cliff"]["area"], cliff["cliff"]["raw"], cliff["cliff_pred_raw"],
             cliff["cliff"]["closed"]))
    print("  * 混粒の全体 G %.2f は細粒 %.2f にも粗粒 %.2f にも無い(± 0.5 のタイル %d / %d)。"
          % (dup["g_mix"], dup["g_f"], dup["g_c"], dup["in_dup"], dup["n_tiles"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    # --- 所見を固定する(壊れたら鳴る) --------------------------------------- #
    assert abs(tr["dev"]) < 6.0, tr["dev"]
    assert abs(tr["offset"] - tr["offset_pred"]) < 0.20, (tr["offset"], tr["offset_pred"])
    assert abs(ctrl["完全・むら無し・雑音無し"]["err_dyn"]) < 0.30
    assert abs(ctrl["+ 雑音のみ"]["err_area"]) < 0.30, ctrl["+ 雑音のみ"]["err_area"]
    assert ctrl["+ むら + 雑音"]["err_area"] > 2.0, ctrl["+ むら + 雑音"]["err_area"]
    assert ctrl["+ むらのみ"]["err_area"] < -0.2, ctrl["+ むらのみ"]["err_area"]
    assert abs(ctrl["+ むらのみ"]["err_dyn"]) < 0.25, ctrl["+ むらのみ"]["err_dyn"]
    assert ctrl["+ むらのみ"]["err_bothat"] < ctrl["+ むらのみ"]["err_dyn"] - 0.3
    assert cliff["cliff"]["area"] < 12.0, cliff["cliff"]["area"]
    assert 15.0 < cliff["cliff"]["raw"] < 30.0, cliff["cliff"]["raw"]
    assert abs(cliff["cliff"]["raw"] - cliff["cliff_pred_raw"]) < 5.0, cliff["cliff"]
    assert cliff["raw_dev"] < 0.35, cliff["raw_dev"]
    assert cliff["n_worse"] >= len(cliff["fracs"]) - 2, cliff["n_worse"]
    assert dup["in_dup"] <= dup["n_tiles"] // 4, (dup["in_dup"], dup["n_tiles"])
    assert dup["in_single"] > dup["n_tiles"] // 2, (dup["in_single"], dup["n_tiles"])
    assert dup["g_f"] > dup["g_mix"] > dup["g_c"]
    assert abs(dup["g_mix"] - dup["g_mix_pred"]) < 0.15, (dup["g_mix"], dup["g_mix_pred"])
    assert dup["modes_d"] == 1, dup["modes_d"]

    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
