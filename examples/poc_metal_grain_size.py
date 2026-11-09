# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""金属組織の結晶粒度を測る —— 面積法は途切れ 7 % で 1 段落ち、切片法は 41 % まで持つ。

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
   雑音だけなら -0.02、エッチングむら(粒ごとの明るさ σ 0.10)だけなら -0.40
   (暗い粒が 50 個消える)。ところが**両方が入ると +3.82** —— しきい値が
   「暗い粒 vs 明るい粒」の谷に落ち、しきい値付近の粒が雑音で粉々(種の無い欠片
   2,867 個)になって N_A が 14 倍に化ける。**要因を 1 つずつ止めた対照群でしか
   この相互作用は見えない**。
3. ★**粒界抽出でも正規化の仕方で差が出る**。ボトムハット(最大値で正規化)は
   むらのみで -0.38 —— 小さい暗い粒 1 個が最大値を決めて、しきい値が相対的に
   上がり弱い粒界を落とす。局所しきい値(``invert_image`` → ``dyn_threshold``、
   絶対オフセット 0.10)なら同じ条件で -0.08。**むらに強いのは「周りとの絶対差」**。
   粒界が完全でも見逃しが 28 件あるのは、粒界の幅(2 px + ぼけ)より短い弦
   (頂点の近く、真値で 22 本)が 1 本の黒線に溶けるから。
4. ★★**崖の位置が 6 倍違う**。粒界の途切れ率 f を 0 → 60 % で掃引すると、
   面積法(むらを止めた対照群)は **7.2 %** で 1 段落ち、切片法は **40.7 %**。
   ★切片法の予想は「横切りが (1−f) 倍 → ℓ が √2 倍になる f = 29.3 %」だったが
   **外れた**: マスク上で実際に消えている粒界画素は f の 0.76 倍しかない(ぼけが
   隙間の両端に隣の黒を漏らし、局所しきい値がそれを拾う)。その f_eff で引き直すと
   予測 37.8 %、実測曲線は引き直した予測と最大 0.11 段で並走する(素朴な予測とは
   0.64 段)。
5. ★面積法の予想は「1 本の途切れで 2 粒が融合 → 塊の数 N(1 − 3p)、p = 辺の
   途切れ率で 1/6 なら 1 段」。ところが p(1 画素でも隙間)は f の 3.7 倍で走る
   (中央値 18 px の隙間 1 塊が、平均 24 px の辺を 2〜3 本同時に触る)ので木近似の
   1 段は f = 3.8 % と**早すぎ**、実測は 7.2 % —— 短い隙間は二値化後もつながらないし、
   閉路もある。実測の融合で数え直すと f = 5 % で飲まれた粒 72 個(203 個中)= 塊 0.65 倍
   = ΔG -0.63 で、実測 -0.64 と合う。**融合は塊の数(f = 5 % を頂点に減る)ではなく
   飲まれた粒の数で効く**。
6. ★★**「隙間を閉じる」は何も買わない**。closing 9×9 で閉じられる隙間は 8 px 以下、
   隙間の中央値は 18 px。閉じた版は途切れ 0 % で偽横切りを 30 → 24 に減らすが
   小さい粒を塗り潰して見逃しを 26 → 86 に増やし、**掃引 13 点中 12 点で素の版より
   悪い**(崖 40.7 → 35.2 %)。
7. ★★**混粒(双峰)を 1 つの G に畳むと、その G の粒はどこにも無い**。左 45 % を
   細粒(真値 G 9.01)、右を粗粒(G 6.15)にした組織の全体 G は 7.82 ——
   切片数の重みで**細粒側に寄る**(調和平均の予測 7.79、面積で重みづけた G の平均
   なら 7.44)。64 px のタイルで局所 G を測ると全体 G ± 0.5 に入るタイルは
   **4 / 64**(単一組織では 41 / 64)。★個々の切片長の累積分布には双峰が**出ない**
   (対数ヒストグラムの山 1 個、ℓ/√2〜ℓ√2 に入る切片は 25.8 % で単一組織の 42.8 % より
   少ないだけ)—— Voronoi の弦長分布は広いので 3 倍違う 2 集団が 1 本の滑らかな曲線に
   溶ける。混粒は**地図**で見るしかない。
8. ★★**実写(公開の金相写真 TBM、CC BY 4.0、専門家が手でなぞった粒界 320 枚)**で 2 つを測る。
   (a) 画像処理を写真そのものに掛ける。1〜7 節の黒い線前提の道具は灰色化した写真でほぼ何も拾わない
   (切片法 ΔG -8.52、横切りの再現率 0.02)。この写真は色腐食で、粒界は黒い線ではなく色の境なので、
   色の境を取る経路は ΔG -0.46 になるが、★これは粒界を取れたという値ではない: 横切りの再現率 0.44、
   偽の横切り 0.37 本 / 真の 1 本で、取り逃し(横切りが減る)と偽(増える)が打ち消し合って 0 に寄った
   (横切りの合計は真の 0.82 倍。偽が無ければ ΔG -2.34)。言えるのは「黒い線の道具は色腐食の写真に
   向かない」までで、色の経路も 1 本試しただけ・再現率は半分。(b) 画像処理は通さず、専門家の粒界の
   マスクに直接途切れを入れると、1 段ずれる途切れ率は 面積法 7.8 %(Voronoi 6.1 %)/ 切片法 33.1 %
   (Voronoi 36.8 %、閉形式 1 − 1/√2 = 29.3 %)。★切片法の崖は 閉形式 < 実写 < Voronoi の順で、
   Voronoi と実写の差は粒界マスクの太さで説明できる —— 介入で確かめた: Voronoi の粒界を
   細線化すると崖 32.5 %(実写に寄る)、実写の粒界を 1 画素太らせると崖 40.7 %(4 枚に 1 枚の 80 枚、
   1 回だけ。門の余白 2.0 pt は実データを見てから置いた)。★ただし太さで閉形式との差は消えない:
   細線化した Voronoi でも閉形式から 3.2 pt(Voronoi)、実写(もとの太さ、走り 1.36 px)は 3.8 pt 残り、
   その原因は確かめていない。
   ★前の版は 128 px 角を貼り合わせて継ぎ目の人工の粒界を数に入れ、「実物のほうが 2 割早く
   落ちる」と書いた —— 誤りだったので、外周 1 画素を落としたタイル単位で数え直した。
   データは repo に入れない(``tools/fetch_tbm.py``)。無い環境では記録値を印字する。

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

import os
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
        print("   %4.0f %%      %+6.2f          %+6.2f      %+6.2f       %5.1f %%         %5.1f %%       %5.0f / %4.0f     %5.0f / %4.0f    %4.0f / %4.0f"
              % (100 * f, err["area"][-1], err["raw"][-1], err["closed"][-1],
                 100 * (fail["hole"][-1] - fail["hole"][0]),
                 100 * fail["p_edge"][-1], fail["missed_raw"][-1], fail["false_raw"][-1],
                 fail["missed_closed"][-1], fail["false_closed"][-1],
                 fail["merged"][-1], fail["swallowed"][-1]))

    # --- 予測 --------------------------------------------------------------- #
    # 切片法: 横切りが (1-f) 倍 → ΔG = 6.64 log10(1-f)。素朴な崖は f = 1 - 1/√2 = 29.3 %。
    #   ★実測はそれより遅い。マスク上で実際に消えている粒界画素の割合 f_eff は f より
    #   小さい(ぼけが隙間の両端 1 px に隣の黒を漏らし、局所しきい値がそれを拾う)ので、
    #   f_eff で引き直した予測 ΔG0 + 6.64 log10(1-f_eff) と突き合わせる。
    dg0 = err["raw"][0]
    f_eff = np.asarray(fail["hole"]) - fail["hole"][0]
    pred_raw_naive = 6.6439 * np.log10(1.0 - fracs)
    pred_raw = dg0 + 6.6439 * np.log10(np.clip(1.0 - f_eff, 1e-6, None))
    cliff_pred_raw_naive = 100 * (1.0 - 2 ** -0.5)
    f_eff_cliff = 1.0 - 10 ** ((-1.0 - dg0) / 6.6439)
    cliff_pred_raw = (float(np.interp(f_eff_cliff, f_eff, 100 * fracs))
                      if f_eff.max() > f_eff_cliff else float("nan"))
    feff_over_f = float(np.mean(f_eff[2:8] / fracs[2:8]))
    # 面積法: 木近似で塊の数は N(1 - 3p)(1 粒あたり辺 6 本 = 辺 3N 本、途切れた辺で 2 粒が 1 塊)。
    #   p は実測の「辺の途切れ率」(1 画素でも隙間があれば途切れ)。1 段 = 塊が半分 = p = 1/6。
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
    naive_dev = float(np.max(np.abs(np.asarray(err["raw"]) - dg0 - pred_raw_naive)))
    worse = [100 * f for f, a, b in zip(fracs, err["raw"], err["closed"]) if abs(b) > abs(a)]
    n_grain = int(np.mean([make_scene(sd)["seeds"].shape[0] for sd in SWEEP_SEEDS]))
    sw5 = fail["swallowed"][1]
    dg_area_from_merges = 3.3219 * np.log10(1.0 - sw5 / n_grain)
    print("\n  ★崖(|ΔG| >= 1 になる途切れ率): 面積法 %.1f %% / 切片法(素) %.1f %% / 切片法(閉) %.1f %%"
          % (cliff["area"], cliff["raw"], cliff["closed"]))
    print("     切片法の予想は %.1f %%(横切り (1-f) 倍)だったが**外れた**: マスク上で実際に消えて"
          "いる粒界は f の %.2f 倍\n     (ぼけが隙間の両端に隣の黒を漏らし、局所しきい値がそれを拾う)。"
          "f_eff で引き直した予測は %.1f %%、\n     実測曲線は引き直した予測と最大 %.2f 段で並走"
          "(素朴な予測とは %.2f 段)。"
          % (cliff_pred_raw_naive, feff_over_f, cliff_pred_raw, raw_dev, naive_dev))
    print("     面積法: 辺の途切れ率 p(1 画素でも隙間)は f の %.1f 倍で走る(隙間 1 塊が 2〜3 辺を"
          "同時に触る)。\n     木近似 N(1-3p) の 1 段は f = %.1f %% で実測 %.1f %% より早い —— "
          "短い隙間は二値化後もつながらないし、閉路もある。\n     実測の融合で数え直すと "
          "f = 5 %% で飲まれた粒 %.0f 個(粒 %d 個中)= 塊 %.2f 倍 = ΔG %+.2f(実測 %+.2f)。"
          % (p_over_f, cliff_pred_area, cliff["area"], sw5, n_grain, 1.0 - sw5 / n_grain,
             dg_area_from_merges, err["area"][1]))
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
                   ylim=(-7.0, 0.8),
                   caption="面積法は 1 本の途切れで 2 粒が融合するので、切片法の 6 分の 1 の途切れで 1 段落ちる。")
    ok = np.isfinite(pred_area)
    figs.save_plot("cliff_prediction",
                   [("切片法 実測", x, err["raw"]), ("切片法 予測 ΔG0 + 6.64 log10(1-f_eff)", x, pred_raw),
                    ("切片法 素朴な予測 6.64 log10(1-f)", x, pred_raw_naive),
                    ("面積法 実測", x, err["area"]), ("面積法 予測 3.32 log10(1-3p)", x[ok], pred_area[ok])],
                   xlabel="粒界の途切れ率 f [%]", ylabel="G の誤差 ΔG [段]",
                   title="幾何で先に立てた予測との突き合わせ", ylim=(-7.0, 0.8),
                   caption="切片法は f_eff で引き直せば並走する。面積法の木近似は早すぎる(短い隙間は二値化後もつながらない)。")
    figs.save_plot("failure_intercept",
                   [("見逃し(素)", x, fail["missed_raw"]), ("偽(素)", x, fail["false_raw"]),
                    ("見逃し(閉)", x, fail["missed_closed"]), ("偽(閉)", x, fail["false_closed"])],
                   xlabel="粒界の途切れ率 f [%]", ylabel="横切りの件数(3 種の平均)",
                   title="切片法の壊れ方: 見逃しは f に比例、偽は平ら")
    figs.save_plot("failure_area",
                   [("融合した塊", x, fail["merged"]), ("飲まれた粒", x, fail["swallowed"]),
                    ("辺の途切れ率 p [%]", x, 100 * p)],
                   xlabel="粒界の途切れ率 f [%]", ylabel="件数(3 種の平均)/ p [%]",
                   title="面積法の壊れ方: 融合は塊の数より飲まれた粒の数で効く",
                   caption="融合した塊の数は f = 5 % を頂点に減る(塊どうしがさらに融合して 1 つになる)が、飲まれた粒の数は増え続ける。")
    return {"fracs": fracs, "err": err, "fail": fail, "cliff": cliff, "dg0": dg0,
            "cliff_pred_area": cliff_pred_area, "cliff_pred_raw": cliff_pred_raw,
            "cliff_pred_raw_naive": cliff_pred_raw_naive, "raw_dev": raw_dev,
            "naive_dev": naive_dev, "n_worse": len(worse), "p_over_f": p_over_f,
            "feff_over_f": feff_over_f, "n_grain": n_grain, "sw5": sw5,
            "dg_area_from_merges": dg_area_from_merges}


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
# 8. 実写 —— 専門家が粒界をなぞった公開の金相写真                               #
# --------------------------------------------------------------------------- #
#: 実写データ: TBM(Texture Boundary in Metallography)、Zenodo record 8386997
#: (doi:10.5281/zenodo.8386997)、ライセンス "Creative Commons Attribution 4.0 International"。
#: 金相写真(README: 約 1.2 mm x 0.8 mm の視野)を 128 px 角に切った 320 枚と、材料の専門家が
#: 手でなぞった粒界(太い版 / 細い版)。取得は ``tools/fetch_tbm.py``(repo には入れない)。
TBM_CREDIT = ("TBM: Texture Boundary in Metallography, Zenodo 8386997 "
              "(doi:10.5281/zenodo.8386997), CC BY 4.0")
TBM_FIELD_MM = 1.2         # README の視野の幅(近似)。画素の大きさは元画像の幅で割って画像ごとに出す
TBM_TILE = 128             # 配布物の 1 枚の一辺 [px]
#: ★配布物の注記は 128 px 角ごとに描かれていて、**各タイルの外周 1 画素に人工の粒界**がある
#: (外周の行・列の粒界の画素密度 0.15、内側の 0.05 の 3 倍)。貼り合わせると継ぎ目に人工の粒界が
#: 並ぶので、この章は**タイル単位**で、外周 1 画素を落とした 126 px 角で数える。
TBM_CROP = 1
TBM_N = TBM_TILE - 2 * TBM_CROP
#: 途切れ率の掃引。崖の近く(面積法 5〜8 %、切片法 25〜35 %)は細かく刻む。
REAL_FRACS = (0.0, 0.025, 0.04, 0.05, 0.06, 0.07, 0.08, 0.10, 0.15, 0.20, 0.25, 0.275, 0.30,
              0.325, 0.35, 0.40, 0.50, 0.60)
REAL_SEEDS = (7, 19, 31)
REAL_BOOT = 200            # 崖の区間: 80 枚の元領域を単位に復元抽出する回数
REAL_SHOW = "10-0-768"     # 図に出す領域(配布物の名前の頭)
#: 切片法の閉形式: 途切れを粒界のマスクへ直接入れると横切りは (1 - f) 倍になり、
#: ΔG_L = 6.6439·log10(1 - f)、1 段ずれる f = 1 - 1/√2 = 29.3 %。
E112_L_SLOPE = 6.6439

#: 実データで出た数値(2026-11-08、Python 3.11。下の section_real の stdout から転記)。
#: データがあるときは実測とこの値を同じ丸めで照合し、無いときは中身と docstring の一致を見る。
RECORDED_REAL = {'tiles': 320, 'g_truth_median': 7.45, 'cliff_area_real': 7.8, 'cliff_intercept_real': 33.1,
                 'cliff_area_ci': [7.5, 8.0], 'cliff_intercept_ci': [32.9, 33.4], 'closed_form_max_dev': 0.21,
                 'voronoi_max_dev': 0.48, 'cliff_area_voronoi': 6.1, 'cliff_intercept_voronoi': 36.8,
                 'photo_err_area': 3.02, 'photo_err_intercept': -8.52, 'photo_recall': 0.02,
                 'run_px_real': 1.36, 'run_px_voronoi': 2.61, 'cliff_intercept_voronoi_thinned': 32.5,
                 'cliff_intercept_real_dilated': 40.7, 'photo_color_err_intercept': -0.46,
                 'photo_color_recall': 0.44, 'photo_color_false': 0.37, 'photo_color_count_ratio': 0.82,
                 'photo_color_dg_from_counts': -0.59, 'photo_color_dg_no_false': -2.34,
                 'thinned_minus_closed_voronoi': 3.2, 'thinned_minus_closed_real': 3.8}
#: docstring の 8 番の項に同じ書式で載っていなければならない値(記録と文の食い違いを止める)。
RECORDED_IN_DOC = {"cliff_area_real": "面積法 %.1f %%", "cliff_intercept_real": "切片法 %.1f %%",
                   "cliff_area_voronoi": "(Voronoi %.1f %%)", "cliff_intercept_voronoi": "(Voronoi %.1f %%、",
                   "cliff_intercept_voronoi_thinned": "細線化すると崖 %.1f %%",
                   "cliff_intercept_real_dilated": "太らせると崖 %.1f %%",
                   "photo_color_err_intercept": "色の境を取る経路は ΔG %.2f",
                   "photo_color_false": "偽の横切り %.2f 本 / 真の 1 本",
                   "photo_color_count_ratio": "横切りの合計は真の %.2f 倍",
                   "photo_color_dg_no_false": "偽が無ければ ΔG %.2f",
                   "thinned_minus_closed_voronoi": "閉形式から %.1f pt(Voronoi)",
                   "thinned_minus_closed_real": "走り 1.36 px)は %.1f pt 残り"}


def real_data_root() -> Path:
    """公開実データの置き場の根。

    ``FULLSEYE_POC_REAL_DATA`` があればそれ、無ければ開発の作業木(``<root>/projects/<checkout>``)
    の隣の ``<root>/data/fullseye_poc_real``、それ以外はユーザーキャッシュ。手元の絶対パスを
    ソースに書かないための分岐。
    """
    configured = os.environ.get("FULLSEYE_POC_REAL_DATA", "").strip()
    if configured:
        return Path(configured).expanduser()
    root = Path(__file__).resolve().parents[1]
    if root.parent.name.lower() == "projects":
        return root.parent.parent / "data" / "fullseye_poc_real"
    return Path.home() / ".cache" / "fullseye" / "poc_real"


def _tbm_dir():
    """TBM の展開先(``FULLSEYE_TBM_DATA`` が最優先)。CI(指定なし)やデータが無いときは ``None``。"""
    if os.environ.get("CI") and not (os.environ.get("FULLSEYE_POC_REAL_DATA")
                                     or os.environ.get("FULLSEYE_TBM_DATA")):
        return None
    tbm = os.environ.get("FULLSEYE_TBM_DATA", "").strip()
    base = Path(tbm).expanduser() if tbm else real_data_root() / "tbm"
    d = base / "TBM"
    return d if (d / "input_image").is_dir() else None


def load_tbm_tiles(d: Path) -> list[dict]:
    """配布物の 320 枚を、外周 1 画素を落とした 126 px 角のタイルとして返す。

    各タイル: ``rgb``(写真)・``thin``(専門家の細い粒界)・``region``(元領域の名前の頭)・
    ``pos``(元領域内の位置)・``px_mm``(元画像の幅で割った画素の大きさ、近似)。
    """
    from PIL import Image
    names = sorted(p.stem for p in (d / "input_image").glob("*.png"))
    if len(names) != 320:
        raise RuntimeError("TBM の写真が %d 枚(配布物は 320 枚): %s" % (len(names), d))
    widths = {}
    out = []
    c = TBM_CROP
    for n in names:
        head, r, col = n.rsplit("-", 2)
        img_id = head.split("-")[0]
        if img_id not in widths:
            with Image.open(d / "full_metallographic_images_for_reference" / (img_id + ".png")) as im:
                widths[img_id] = im.size[0]
        rgb = np.asarray(Image.open(d / "input_image" / (n + ".png")).convert("RGB"), np.float64) / 255.0
        tp = next((d / "expert_inv_label_thin").glob(n + ".*"))
        thin = np.asarray(Image.open(tp).convert("L")) > 127                      # JPEG なので 127 で切る
        out.append({"rgb": rgb[c:TBM_TILE - c, c:TBM_TILE - c], "thin": thin[c:TBM_TILE - c, c:TBM_TILE - c],
                    "region": head, "pos": (int(r), int(col)), "px_mm": TBM_FIELD_MM / widths[img_id]})
    return out


def _labels_from_boundary(bound: np.ndarray) -> np.ndarray:
    """粒界で区切られた粒の番号(4 近傍)を、粒界の画素は最寄りの粒に配って返す。"""
    lab, _ = nd_label(~bound)
    _, (iy, ix) = distance_transform_edt(lab == 0, return_indices=True)
    return lab[iy, ix]


def _count_g(grains: np.ndarray, n_cross: int, total_len: float, n_pix: int, px_mm: float):
    """粒の領域(bool)の連結成分と横切りの数から、面積法と切片法の G。"""
    lab, n = nd_label(grains)
    edge = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    n_touch = int(np.count_nonzero(edge > 0))
    n_eff = (n - n_touch) + 0.5 * n_touch
    g_a = g_from_area(max(n_eff, 0.5) / (n_pix * px_mm) ** 2)
    g_l = g_from_intercept(total_len / max(n_cross, 1) * px_mm)
    return g_a, g_l


def _mask_g(drawn: np.ndarray, lines: list[dict], n_pix: int, px_mm: float) -> tuple[float, float]:
    """粒界マスク(途切れ込み)から、面積法と切片法の G を同じ数え方で出す。

    面積法 = 粒界の外の連結成分(4 近傍、縁に触れる粒は 0.5 個)。切片法 = 試験線が粒界の
    走りを横切る回数。**画像処理は通さない** —— 違うのは粒界の形(Voronoi か実物か)だけ。
    """
    on = drawn > 0.0
    n_cross = sum(_run_centers(on.astype(np.float64), ln).size for ln in lines)
    return _count_g(~on, n_cross, sum(ln["len"] for ln in lines), n_pix, px_mm)


def _cliff(fracs, dg) -> float:
    """|ΔG| が初めて 1 段に届く途切れ率 [%](線形補間)。届かなければ最大の f を返す。"""
    dg = np.abs(np.asarray(dg))
    for i in range(1, len(fracs)):
        if dg[i] >= 1.0:
            f0, f1, d0, d1 = fracs[i - 1], fracs[i], dg[i - 1], dg[i]
            return float(100.0 * (f0 + (1.0 - d0) * (f1 - f0) / max(d1 - d0, 1e-12)))
    return float(100.0 * fracs[-1])


def _sweep_each(bounds, n_pix, px_mms) -> np.ndarray:
    """マスクごとに ΔG(面積法・切片法)を f で掃引する。戻り値 (マスク, 2, f)。"""
    lines = test_lines(n_pix=n_pix)
    out = np.zeros((len(bounds), 2, len(REAL_FRACS)))
    for j, (b, px) in enumerate(zip(bounds, px_mms)):
        soft = b.astype(np.float64)
        g0a, g0l = _mask_g(soft, lines, n_pix, px)
        for i, f in enumerate(REAL_FRACS):
            acc = []
            for sd in REAL_SEEDS:
                drawn, _ = _break_boundary(soft, float(f), np.random.default_rng(sd + 1000))
                ga, gl = _mask_g(drawn, lines, n_pix, px)
                acc.append((ga - g0a, gl - g0l))
            out[j, :, i] = np.mean(acc, axis=0)
    return out


def _run_length(bounds, n_pix) -> float:
    """試験線が粒界を横切るときの走りの長さ [px] の平均(横切り 1 本が何画素でできているか)。"""
    lines = test_lines(n_pix=n_pix)
    lens = []
    for b in bounds:
        for ln in lines:
            v = b[ln["r"], ln["c"]]
            d = np.diff(np.concatenate([[0], v.astype(np.int8), [0]]))
            lens.extend((np.nonzero(d == -1)[0] - np.nonzero(d == 1)[0]).tolist())
    return float(np.mean(lens))


def color_boundary(rgb: np.ndarray, sigma: float = 1.5) -> np.ndarray:
    """色の境を取る経路: ``rgb_to_lab`` → 3 チャネルを平滑して Sobel の勾配の大きさ → 99 % 分位で
    正規化 → 1〜7 節と同じ ``dyn_threshold``(明るい線 = 勾配の尾根)→ ``thinning``。

    色腐食の写真では粒界は暗い線ではなく**色が変わる所**なので、灰色化せずに色の差を取る。
    """
    from scipy.ndimage import gaussian_filter as _g, sobel as _sobel
    lab = np.asarray(fs.rgb_to_lab(rgb), np.float64)
    g2 = np.zeros(rgb.shape[:2])
    for c in range(3):
        sm = _g(lab[..., c], sigma)
        g2 += _sobel(sm, 0) ** 2 + _sobel(sm, 1) ** 2
    g = np.sqrt(g2)
    gn = np.clip(g / max(float(np.percentile(g, 99)), 1e-9), 0.0, 1.0)
    m = np.asarray(fs.apply(gn, "dyn_threshold", a=DYN_A, b=DYN_B)) > 0.5
    return np.asarray(fs.apply(m.astype(np.float64), "thinning")) > 0.5


def _detect_on_photo(tiles: list[dict]) -> dict:
    """1〜7 節の画像処理(面積法 = 大津 + 連結成分、切片法 = invert → dyn_threshold)と、色の境を
    取る経路(:func:`color_boundary`)を**実写の写真そのもの**に掛け、専門家の粒界から出した G と比べる。"""
    lines = test_lines(n_pix=TBM_N)
    total = sum(ln["len"] for ln in lines)
    rows = []
    for t in tiles:
        gray = t["rgb"] @ np.array([0.2125, 0.7154, 0.0721])
        lab_t = _labels_from_boundary(t["thin"])
        st_t = intercept_stats(lab_t, t["thin"].astype(np.float64), lines)
        g_a_t, g_l_t = _count_g(~t["thin"], st_t["n_est"], total, TBM_N, t["px_mm"])
        bm = boundary_masks(gray)
        st = intercept_stats(lab_t, bm["dyn"], lines)
        bw = np.asarray(fs.apply(gray, "bin_threshold")) > 0.5
        g_a, _ = _count_g(bw, 1, total, TBM_N, t["px_mm"])
        g_l = g_from_intercept(st["ell_est_px"] * t["px_mm"])
        cb = color_boundary(t["rgb"])
        st_c = intercept_stats(lab_t, cb.astype(np.float64), lines)
        rows.append({"g_a_true": g_a_t, "g_l_true": g_l_t, "g_a": g_a, "g_l": g_l,
                     "matched": st["matched"], "n_true": st["n_true"], "false": st["false"],
                     "dyn": bm["dyn"], "otsu": bw, "color": cb,
                     "g_l_color": g_from_intercept(st_c["ell_est_px"] * t["px_mm"]),
                     "matched_c": st_c["matched"], "false_c": st_c["false"]})
    return {"rows": rows,
            "err_a": float(np.median([r["g_a"] - r["g_a_true"] for r in rows])),
            "err_l": float(np.median([r["g_l"] - r["g_l_true"] for r in rows])),
            "recall_l": float(sum(r["matched"] for r in rows) / max(sum(r["n_true"] for r in rows), 1)),
            "false_per_true": float(sum(r["false"] for r in rows) / max(sum(r["n_true"] for r in rows), 1)),
            "err_l_color": float(np.median([r["g_l_color"] - r["g_l_true"] for r in rows])),
            "recall_color": float(sum(r["matched_c"] for r in rows) / max(sum(r["n_true"] for r in rows), 1)),
            "false_color": float(sum(r["false_c"] for r in rows) / max(sum(r["n_true"] for r in rows), 1))}


def _recorded_gate(measured) -> None:
    """記録値の門。データがあれば実測と記録値を同じ丸めで照合し、無ければ記録値の中身と
    docstring の一致を見る(「記録値の辞書が空でない」だけの門は常に真なので置かない)。"""
    need = {"tiles", "g_truth_median", "cliff_area_real", "cliff_intercept_real", "cliff_area_ci",
            "cliff_intercept_ci", "closed_form_max_dev", "voronoi_max_dev", "cliff_area_voronoi",
            "cliff_intercept_voronoi", "photo_err_area", "photo_err_intercept", "photo_recall",
            "run_px_real", "run_px_voronoi", "cliff_intercept_voronoi_thinned",
            "cliff_intercept_real_dilated", "photo_color_err_intercept", "photo_color_recall",
            "photo_color_false", "photo_color_count_ratio", "photo_color_dg_from_counts", "photo_color_dg_no_false",
            "thinned_minus_closed_voronoi", "thinned_minus_closed_real"}
    missing = need - set(RECORDED_REAL)
    assert not missing, "記録値の鍵が足りない: %s" % sorted(missing)
    for k, v in RECORDED_REAL.items():
        vals = v if isinstance(v, (list, tuple)) else [v]
        assert all(np.isfinite(float(x)) for x in vals), (k, v)
    doc = __doc__ or ""
    for k, fmt in RECORDED_IN_DOC.items():
        txt = fmt % RECORDED_REAL[k]
        assert txt in doc, "docstring に記録値 %s の文「%s」が無い" % (k, txt)
    if measured is not None:
        diff = {k: (measured[k], RECORDED_REAL[k]) for k in need if measured[k] != RECORDED_REAL[k]}
        assert not diff, "実測と記録値が違う(記録を実行ログから転記し直す): %s" % diff


def section_real():
    print("\n" + "=" * 78)
    print("8) 実写 —— 専門家が粒界をなぞった公開の金相写真")
    print("=" * 78)
    d = _tbm_dir()
    if d is None:
        print("  実データが無いので実データの章を飛ばす。取得は "
              "py -3.11 tools/fetch_tbm.py")
        print("  記録値(RECORDED_REAL): %s" % RECORDED_REAL)
        _recorded_gate(None)
        return None
    import realdata
    tiles = load_tbm_tiles(d)
    realdata.mark_read("zenodo:8386997/TBM")
    print("  データ: %s" % TBM_CREDIT)
    print("  真値 = 専門家が手でなぞった細い粒界。%d 枚(%d 領域)を、外周 1 画素(注記の人工の粒界)を"
          % (len(tiles), len({t["region"] for t in tiles})))
    print("  落とした %d px 角のタイル単位で数える(貼り合わせると継ぎ目に人工の粒界が並ぶため)。" % TBM_N)
    lines = test_lines(n_pix=TBM_N)
    g_true = [g_from_intercept(intercept_stats(_labels_from_boundary(t["thin"]), None, lines)["ell_true_px"]
                               * t["px_mm"]) for t in tiles]
    print("  専門家の粒界から出した G(切片法、画素の大きさは元画像の幅から): 中央値 %.2f(%.2f〜%.2f)"
          % (np.median(g_true), np.min(g_true), np.max(g_true)))

    # --- (a) 実写の写真に 1〜7 節の画像処理を掛ける ---
    det = _detect_on_photo(tiles)
    print("\n  (a) 1〜7 節の画像処理を**写真そのもの**に掛けて、専門家の G と比べる(%d 枚の中央値):"
          % len(tiles))
    print("      面積法(大津 + 連結成分) ΔG %+.2f / 切片法(局所しきい値) ΔG %+.2f、"
          "横切りの再現率 %.2f、偽の横切り %.2f 本 / 真の 1 本"
          % (det["err_a"], det["err_l"], det["recall_l"], det["false_per_true"]))
    print("      色の境を取る経路(rgb_to_lab の勾配 → dyn_threshold → 細線化): 切片法 ΔG %+.2f、"
          "横切りの再現率 %.2f、偽 %.2f 本 / 真の 1 本" % (det["err_l_color"], det["recall_color"], det["false_color"]))
    cnt = det["recall_color"] + det["false_color"]
    dg_cnt = E112_L_SLOPE * np.log10(cnt)
    dg_nf = E112_L_SLOPE * np.log10(max(det["recall_color"], 1e-9))
    print("      ★色の経路の ΔG %+.2f は**粒界を取れた値ではない**。内訳: 真の横切りの %.2f を拾い、偽を真の 1 本あたり"
          % (det["err_l_color"], det["recall_color"]))
    print("        %.2f 本足すので、横切りの合計は真の %.2f 倍(全タイルの合計から ΔG = %.4f·log10(%.2f) = %+.2f。"
          % (det["false_color"], cnt, E112_L_SLOPE, cnt, dg_cnt))
    print("        上の %+.2f はタイルごとの中央値)。偽が無ければ ΔG %+.2f —— 取り逃しと偽が打ち消し合って 0 に寄った。"
          % (det["err_l_color"], dg_nf))
    print("      ★この写真は色腐食で、粒界は**黒い線ではなく色の境**。「粒界 = 暗い線」を前提にした 1〜7 節の")
    print("        道具は灰色化した写真ではほぼ何も拾わない。色の差を取れば半分近くを拾うが、偽も同じくらい出る。")
    print("        言えるのは「黒い線の道具は色腐食の写真に向かない」まで —— 色の経路も再現率は半分で、")
    print("        実用の精度とは言えない(色の経路は 1 本だけ試した)。")

    # --- (b) 専門家の粒界に途切れを入れる(画像処理は通さない) ---
    print("\n  (b) 画像処理は通さず、**専門家の粒界のマスクに直接**途切れを入れる。比べる相手は同じ")
    print("      数え方の Voronoi(1〜7 節の組織)と、切片法の閉形式 ΔG_L = %.4f·log10(1 − f)。" % E112_L_SLOPE)
    each = _sweep_each([t["thin"] for t in tiles], TBM_N, [t["px_mm"] for t in tiles])
    real = each.mean(axis=0)
    vor = [_thin_boundary(make_scene(sd)["labels"]) for sd in SWEEP_SEEDS]
    syn = _sweep_each(vor, N_PIX, [PX_MM] * len(vor)).mean(axis=0)
    fr = np.asarray(REAL_FRACS)
    closed = E112_L_SLOPE * np.log10(1.0 - fr)
    print("\n   途切れ   面積法 ΔG(実写 / Voronoi)   切片法 ΔG(実写 / Voronoi / 閉形式)")
    for i, f in enumerate(REAL_FRACS):
        print("   %5.1f %%     %+6.2f / %+6.2f              %+6.2f / %+6.2f / %+6.2f"
              % (100 * f, real[0, i], syn[0, i], real[1, i], syn[1, i], closed[i]))
    dev_r = float(np.max(np.abs(real[1] - closed)))
    dev_s = float(np.max(np.abs(syn[1] - closed)))
    c_a, c_l = _cliff(REAL_FRACS, real[0]), _cliff(REAL_FRACS, real[1])
    s_a, s_l = _cliff(REAL_FRACS, syn[0]), _cliff(REAL_FRACS, syn[1])
    regions = sorted({t["region"] for t in tiles})
    idx = {r: [i for i, t in enumerate(tiles) if t["region"] == r] for r in regions}
    rng = np.random.default_rng(2026)
    boot = []
    for _ in range(REAL_BOOT):
        pick = np.concatenate([idx[r] for r in rng.choice(regions, len(regions))])
        m = each[pick].mean(axis=0)
        boot.append((_cliff(REAL_FRACS, m[0]), _cliff(REAL_FRACS, m[1])))
    boot = np.asarray(boot)
    ci_a = np.percentile(boot[:, 0], [2.5, 97.5])
    ci_l = np.percentile(boot[:, 1], [2.5, 97.5])
    print("\n  1 段ずれる途切れ率(95 %% 区間は 80 領域の復元抽出 %d 回):" % REAL_BOOT)
    print("    面積法  実写 %.1f %%(%.1f〜%.1f)/ Voronoi %.1f %%" % (c_a, ci_a[0], ci_a[1], s_a))
    print("    切片法  実写 %.1f %%(%.1f〜%.1f)/ Voronoi %.1f %% / 閉形式 %.1f %%"
          % (c_l, ci_l[0], ci_l[1], s_l, 100 * (1 - 1 / np.sqrt(2))))
    run_r = _run_length([t["thin"] for t in tiles], TBM_N)
    run_s = _run_length(vor, N_PIX)
    # 太さの介入: Voronoi の粒界を細線化し、実写の粒界を 1 画素太らせて、崖が動くかを見る
    from scipy.ndimage import binary_dilation as _dil
    vor_thin = [np.asarray(fs.apply(v.astype(np.float64), "thinning")) > 0.5 for v in vor]
    sub = [t for i, t in enumerate(tiles) if i % 4 == 0]               # 時間のため 4 枚に 1 枚(決定的)
    thick = [_dil(t["thin"]) for t in sub]
    s_thin = _sweep_each(vor_thin, N_PIX, [PX_MM] * len(vor_thin)).mean(axis=0)
    r_thick = _sweep_each(thick, TBM_N, [t["px_mm"] for t in sub]).mean(axis=0)
    c_vt, c_rt = _cliff(REAL_FRACS, s_thin[1]), _cliff(REAL_FRACS, r_thick[1])
    run_vt, run_rt = _run_length(vor_thin, N_PIX), _run_length(thick, TBM_N)
    print("  ★切片法の崖は 閉形式 29.3 %% < 実写 %.1f %% < Voronoi %.1f %% の順(閉形式からのずれの最大"
          % (c_l, s_l))
    print("    実写 %.2f 段 / Voronoi %.2f 段)。ずれの向きはどちらも「後ろ」。Voronoi と実写の差は**粒界マスクの太さ**で"
          % (dev_r, dev_s))
    print("    説明できる: 試験線が粒界を横切る走りの長さは 実写 %.2f px / Voronoi %.2f px。走りが複数画素だと、"
          % (run_r, run_s))
    print("    一部が消えても横切りが残る。閉形式は「横切り 1 本 = 1 画素」の極限。")
    print("  ★介入で確かめた: Voronoi の粒界を細線化すると走り %.2f px・崖 %.1f %%(実写 %.1f %% に寄る)、"
          % (run_vt, c_vt, c_l))
    print("    実写の粒界を 1 画素太らせると走り %.2f px・崖 %.1f %%(%d 枚、1 回だけ)。太さを変えると崖が動く。"
          % (run_rt, c_rt, len(sub)))
    cf = 100 * (1 - 1 / np.sqrt(2))
    print("  ★ただし太さで閉形式との差は消えない: 細線化した Voronoi(走り %.2f px)でも閉形式から %.1f pt、"
          % (run_vt, c_vt - cf))
    print("    実写(走り %.2f px)で %.1f pt 残る。この残りの原因は確かめていない(「太さで決まる」とは言わない)。"
          % (run_r, c_l - cf))
    print("  ★前の版(256 px に貼り合わせ)は「実物のほうが 2 割早く落ちる」と書いた —— 誤り。継ぎ目の")
    print("    人工の粒界(試験線と直交する長い直線、走り 1〜2 px)が実写を閉形式へ引き寄せていた。")
    print("  ★面積法の崖は 実写 %.1f %% / Voronoi %.1f %%。どちらも 1 割に届かず、切片法の 4 倍以上早い。"
          % (c_a, s_a))
    rec = {"tiles": len(tiles), "g_truth_median": round(float(np.median(g_true)), 2),
           "cliff_area_real": round(c_a, 1), "cliff_intercept_real": round(c_l, 1),
           "cliff_area_ci": [round(float(x), 1) for x in ci_a],
           "cliff_intercept_ci": [round(float(x), 1) for x in ci_l],
           "closed_form_max_dev": round(dev_r, 2), "voronoi_max_dev": round(dev_s, 2),
           "cliff_area_voronoi": round(s_a, 1), "cliff_intercept_voronoi": round(s_l, 1),
           "photo_err_area": round(det["err_a"], 2), "photo_err_intercept": round(det["err_l"], 2),
           "photo_recall": round(det["recall_l"], 2),
           "run_px_real": round(run_r, 2), "run_px_voronoi": round(run_s, 2),
           "cliff_intercept_voronoi_thinned": round(c_vt, 1), "cliff_intercept_real_dilated": round(c_rt, 1),
           "photo_color_err_intercept": round(det["err_l_color"], 2),
           "photo_color_recall": round(det["recall_color"], 2),
           "photo_color_false": round(det["false_color"], 2), "photo_color_count_ratio": round(cnt, 2),
           "photo_color_dg_from_counts": round(float(dg_cnt), 2), "photo_color_dg_no_false": round(float(dg_nf), 2),
           "thinned_minus_closed_voronoi": round(float(c_vt - cf), 1),
           "thinned_minus_closed_real": round(float(c_l - cf), 1)}
    print("\n  RECORDED_REAL = %s" % rec)
    _recorded_gate(rec)
    # --- 所見を固定する(実データがあるときだけ) ---
    assert len(tiles) == 320, len(tiles)
    # 閉形式(外の式)< 実写 < Voronoi の順を、崖の区間ごと固定する(この順は実データを見てから置いた)
    assert 100 * (1 - 1 / np.sqrt(2)) < ci_l[0] and ci_l[1] < s_l, (ci_l, s_l)
    # 太さの介入: 細くすると崖は前へ、太くすると後ろへ動く(主張「Voronoi と実写の差は太さで説明できる」の
    # 因果の向き)。余白 2.0 pt は実データを見てから置いた。太らせた側は 80 枚・1 回だけ。
    assert c_vt < s_l - 2.0 and c_rt > c_l + 2.0, (c_vt, s_l, c_rt, c_l)
    assert dev_r < dev_s and run_r < run_s, (dev_r, dev_s, run_r, run_s)
    # 面積法は切片法の 4 倍以上早い(4 倍と 10 % は実データを見て置いた値)
    assert ci_a[1] < 10.0 and ci_l[0] > 4.0 * ci_a[1], (ci_a, ci_l)
    _real_figure(tiles, det, real, syn, closed, (c_a, c_l), (ci_a, ci_l))
    return {"rec": rec}


def _overlay_edges(rgb, mask, color):
    out = rgb.copy()
    out[mask] = color
    return out


def _real_figure(tiles, det, real, syn, closed, cliffs, cis) -> None:
    """実写の図 4 枚: 写真と専門家の粒界 / 写真への画像処理 / 途切れ / 崖の折れ線。"""
    if not figs.enabled():
        return
    show = [i for i, t in enumerate(tiles) if t["region"] == REAL_SHOW] or [0, 1, 2, 3]
    gut = 4

    def mosaic(fn):
        """同じ領域の 4 枚を、白い溝を挟んで並べる(貼り合わせない = 継ぎ目を作らない)。
        さらに最近傍で 2 倍にする(双三次で拡大されてぼけるのを避ける)。"""
        tl = {tiles[i]["pos"]: fn(i) for i in show}
        n = TBM_N
        m = np.ones((2 * n + gut, 2 * n + gut, 3))
        for (r, c), a in tl.items():
            y, x = (0 if r == 0 else n + gut), (0 if c == 0 else n + gut)
            m[y:y + n, x:x + n] = a
        return np.kron(m, np.ones((2, 2, 1)))

    black, red, orange, cyan = (0.05, 0.05, 0.05), (0.95, 0.15, 0.1), (1.0, 0.55, 0.0), (0.1, 0.8, 0.95)
    r_by = {i: det["rows"][i] for i in show}
    figs.save_grid(
        "real_tbm_input",
        [mosaic(lambda i: tiles[i]["rgb"]), mosaic(lambda i: _overlay_edges(tiles[i]["rgb"], tiles[i]["thin"], black))],
        ["実写の金相写真(色腐食、128 px 角 4 枚)", "専門家が手でなぞった粒界(真値)"],
        ncols=2, title="公開の金相写真 TBM と、材料の専門家が手でなぞった粒界",
        caption="%s の 4 枚。白い溝は配布物のタイルの境(貼り合わせない)。%s" % (REAL_SHOW, TBM_CREDIT))
    figs.save_grid(
        "real_tbm_detect",
        [mosaic(lambda i: _overlay_edges(tiles[i]["rgb"], r_by[i]["dyn"] > 0.5, orange)),
         mosaic(lambda i: _overlay_edges(_overlay_edges(tiles[i]["rgb"], ~r_by[i]["otsu"], cyan), tiles[i]["thin"], black))],
        ["暗い線の局所しきい値(橙): 切片法 ΔG %+.1f" % det["err_l"],
         "大津の暗い側(水色)と真値(黒): 面積法 ΔG %+.1f" % det["err_a"]],
        ncols=2,
        title="黒い粒界を前提にした画像処理は色腐食の実写で外れる(%d 枚の中央値)" % len(tiles),
        caption="1〜7 節の道具をそのまま写真に掛けた。切片法の横切りの再現率 %.2f、偽 %.2f 本 / 真の 1 本。%s"
                % (det["recall_l"], det["false_per_true"], TBM_CREDIT))
    figs.save_grid(
        "real_tbm_color_detect",
        [mosaic(lambda i: _overlay_edges(tiles[i]["rgb"], tiles[i]["thin"], black)),
         mosaic(lambda i: _overlay_edges(tiles[i]["rgb"], r_by[i]["color"], orange))],
        ["専門家の粒界(真値)", "色の境を取る経路(橙): 再現率 %.2f、偽 %.2f 本 / 真の 1 本"
         % (det["recall_color"], det["false_color"])],
        ncols=2,
        title="色の差で取る経路: 再現率 %.2f と偽 %.2f 本 / 真の 1 本が打ち消し合い ΔG %+.2f(%d 枚)"
              % (det["recall_color"], det["false_color"], det["err_l_color"], len(tiles)),
        caption="rgb_to_lab の勾配の尾根を 1〜7 節と同じ局所しきい値で取り、細線化した。ΔG が 0 に近いのは粒界を"
                "取れたからではなく、取り逃し(横切りが減る)と偽(増える)が打ち消し合ったから。色の経路は 1 本だけ"
                "試した。%s" % TBM_CREDIT)
    f_show = 0.05

    def broken(i):
        b = tiles[i]["thin"]
        drawn, _ = _break_boundary(b.astype(np.float64), f_show, np.random.default_rng(REAL_SEEDS[0] + 1000))
        on = drawn > 0
        lab0, _ = nd_label(~b)
        lab1, n1 = nd_label(~on)
        pair = np.unique(np.stack([lab0[lab0 > 0], lab1[lab0 > 0]]), axis=1)
        cnt = np.bincount(pair[1], minlength=n1 + 1)
        merged = np.isin(lab1, np.nonzero(cnt >= 2)[0]) & (lab1 > 0)
        a = tiles[i]["rgb"].copy()
        a[merged] = 0.55 * a[merged] + 0.45 * np.array([1.0, 0.85, 0.2])
        a[on] = black
        a[b & ~on] = red
        return a
    i5 = list(REAL_FRACS).index(f_show)
    figs.save_grid(
        "real_tbm_breaks",
        [mosaic(lambda i: _overlay_edges(tiles[i]["rgb"], tiles[i]["thin"], black)), mosaic(broken)],
        ["専門家の粒界(途切れ無し)", "粒界の %.0f %% を消す(赤)と粒がつながる(黄)" % (100 * f_show)],
        ncols=2,
        title="画像処理は通さず真値の粒界を %.0f %% 消す: 面積法 %+.1f 段、切片法 %+.1f 段(%d 枚の平均)"
              % (100 * f_show, real[0, i5], real[1, i5], len(tiles)),
        caption="途切れは人工(相関長 %.0f px)。粒界は専門家の手描きで、写真から検出したものではない。%s"
                % (GAP_LEN, TBM_CREDIT))
    fr = 100.0 * np.asarray(REAL_FRACS)
    figs.save_plot("real_tbm_cliff",
                   [("切片法(実写)", fr, real[1]), ("切片法の閉形式", fr, closed),
                    ("切片法(Voronoi)", fr, syn[1]), ("面積法(実写)", fr, real[0]),
                    ("面積法(Voronoi)", fr, syn[0])],
                   xlabel="粒界の途切れ率 [%]", ylabel="ΔG(途切れ無しとの差)",
                   title="1 段ずれる途切れ率: 切片法 実写 %.1f %%(閉形式 29.3 %%)、面積法 %.1f %%"
                         % (cliffs[1], cliffs[0]),
                   caption="専門家の粒界 %d 枚と Voronoi に同じ途切れを入れて数えた。崖の 95 %% 区間"
                           "(80 領域の復元抽出): 面積法 %.1f〜%.1f %%、切片法 %.1f〜%.1f %%。"
                           % (len(tiles), cis[0][0], cis[0][1], cis[1][0], cis[1][1]))



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
    real = section_real()

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
    rec = real["rec"] if real else RECORDED_REAL
    print("  * 実写(専門家の粒界 %d 枚): 1 段ずれる途切れ率は 面積法 %.1f %% / 切片法 %.1f %%"
          "(閉形式 29.3 %%、Voronoi %.1f %%)。写真への画像処理は 面積法 ΔG %+.2f / 切片法 ΔG %+.2f%s。"
          % (rec["tiles"], rec["cliff_area_real"], rec["cliff_intercept_real"], rec["cliff_intercept_voronoi"],
             rec["photo_err_area"], rec["photo_err_intercept"], "" if real else "(記録値)"))
    print("  * 色の境を取る経路は ΔG %+.2f だが、再現率 %.2f と偽 %.2f 本 / 真の 1 本が打ち消し合った値"
          "(偽が無ければ ΔG %+.2f)。粒界を取れてはいない。"
          % (rec["photo_color_err_intercept"], rec["photo_color_recall"], rec["photo_color_false"],
             rec["photo_color_dg_no_false"]))
    print("\n  所要 %.1f 秒" % (time.perf_counter() - t0))

    # --- 所見を固定する(壊れたら鳴る) --------------------------------------- #
    assert abs(tr["dev"]) < 6.0, tr["dev"]
    assert abs(tr["offset"] - tr["offset_pred"]) < 0.20, (tr["offset"], tr["offset_pred"])
    assert abs(ctrl["完全・むら無し・雑音無し"]["err_dyn"]) < 0.30
    assert abs(ctrl["+ 雑音のみ"]["err_area"]) < 0.30, ctrl["+ 雑音のみ"]["err_area"]
    assert ctrl["+ むら + 雑音"]["err_area"] > 2.0, ctrl["+ むら + 雑音"]["err_area"]
    assert ctrl["+ むらのみ"]["err_area"] < -0.2, ctrl["+ むらのみ"]["err_area"]
    assert abs(ctrl["+ むらのみ"]["err_dyn"]) < 0.25, ctrl["+ むらのみ"]["err_dyn"]
    assert ctrl["+ むらのみ"]["err_bothat"] < ctrl["+ むらのみ"]["err_dyn"] - 0.2
    assert cliff["cliff"]["area"] < 12.0, cliff["cliff"]["area"]
    assert 30.0 < cliff["cliff"]["raw"] < 55.0, cliff["cliff"]["raw"]
    assert cliff["cliff"]["raw"] > cliff["cliff_pred_raw_naive"] + 5.0, cliff["cliff"]
    assert abs(cliff["cliff"]["raw"] - cliff["cliff_pred_raw"]) < 6.0, cliff["cliff"]
    assert cliff["raw_dev"] < 0.30, cliff["raw_dev"]
    assert 0.4 < cliff["feff_over_f"] < 0.9, cliff["feff_over_f"]
    assert abs(cliff["dg_area_from_merges"] - cliff["err"]["area"][1]) < 0.25, cliff["dg_area_from_merges"]
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
