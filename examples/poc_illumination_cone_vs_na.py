# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""PoC: 照明の立体角と観察の NA —— 光の円錐の開き方を変えるだけで、同じ打痕・傷・ムラが消えたり出たりする。

【問い】鏡面に近い金属部品の外観検査では、浅い打痕(傾き 0.1〜0.5°)、ヘアライン仕上げの上の傷、梨地(ブラスト)の
ムラが「同軸落射で見えたり見えなかったりする」。光源の形を変えるより先に、**各点に届く光の円錐の開き(半角 α)と向き
(傾き ψ)**を、カメラが受け取る円錐(物体側 NA、半角 β = asin NA)に対してどう置くかで、明暗が設計できる。
顕微鏡のケーラー照明でいう「照明の NA と対物の NA」、シュリーレン法のナイフエッジと同じ幾何で、鏡面での反射は
方向の球の上の等長写像なので、明るさは **2 つの球冠の交わり**という閉形式になる。op 5 本(``illumdesign`` の
``solid_angle_*``)を使い、閉形式を先に印字してから、画像で測った値と突き合わせる。**場面はすべて合成**(一様な遠方場の
円錐の照明・テレセンの観察・回折と多重反射なし)で、光源の種類どうし(リング・ドーム・同軸の拡散板など)は比べていない。
実画像との突き合わせは未了(6 章)。6 章:

  1. **閉形式**: 面が θ 傾くと反射した光の円錐は 2θ 振れる。|2θ| ≤ |α − β| なら片方の円錐がもう片方に収まり、
     明るさは変わらない(傾きは見えない)。|2θ| ≥ α + β で暗。その間だけ明るさが傾きで変わる。
     門: 球冠の交わりの閉形式とレンズの瞳(方向余弦で一様 = 射影立体角)の数値積分の差、境界の外で明るさが一定。
  2. **3 つのワーク × 5 つの照明**: 鏡面のアルミの浅い打痕(深さ 2 µm)、ヘアライン仕上げのステンレスの V 溝の傷
     (斜面 4°、ヘアラインの微小面の広がりは 0.12° と置いた —— 広がりが 1° を越える面では 5 章のとおり円錐の設計の
     効きが落ちる)、梨地のアルミのムラ(微小面の傾きの広がり 0.8° と 1.3° の斑)を、物体側 NA 0.033 のテレセン
     レンズで、α = 0.5° / α = β / α = 4° / α = 7° / α = β を β だけ傾けた円錐、で撮る。門: 画像から測った打痕の
     明るさが閉形式と一致、「消える」照明では打痕のコントラストが 0(境界の内側)。★露光は円錐ごとに平らな地が 0.75 に
     なるよう合わせた(α = 0.5° の平らな地は 0.07 なので利得は約 11 倍 —— 実機では同じだけ露光を延ばす)。
  3. **傾きの帯を選ぶ**: ヘアラインの筋(傾き ±0.4° 程度)は消し、傷の斜面(4°)は真っ黒にする α を閉形式で選ぶ
     ((α − β)/2 > 筋の傾き、(α + β)/2 < 傷の斜面)。門: その α で筋の標準偏差が α = β の 1/5 以下、傷のコントラスト > 0.9。
  4. **向きをずらす(ナイフエッジ)**: α = β の円錐を β 傾けると平らな地が半分だけ明るく、傾きの**符号**が明暗で読める
     (打痕が浮き彫りに見える)。門: 打痕の左右の斜面の明るさが閉形式と一致し、符号が逆。
  5. **壊れる条件**: (a) 面のうねり(周期 1.5 mm、傾き ±0.25°)があると、α = β では地の明るさが打痕と同じ桁で揺れ、
     しきい値で打痕だけを拾えない。(b) 粗い面(微小面の傾きの広がり σ が (α + β)/2 を越える)では、α を 0.5〜3° の
     4 通りから選んでも打痕のコントラストが落ちる。門: うねりの地の揺れ / 打痕の深さの比、σ に対するコントラストの曲線。
  6. **実画像**: 照明の立体角だけを変えて同じワークを撮った比較写真を、再利用できるライセンス(CC BY / CC0)で
     探したが見つからなかった(2026-10-15)。この章は正直に「無い」と印字する。

【外部真値】球冠の交わりの面積(球面三角法の閉形式)と、円錐の境界 |α − β|/2・(α + β)/2。【学習】0。【較正】0。

【来歴】Born & Wolf, *Principles of Optics*(ケーラー照明と部分的コヒーレンス、照明と対物の開口)/
Settles, *Schlieren and Shadowgraph Techniques*, Springer (2001)(光源像とナイフエッジで傾きの符号を読む)/
Hopkins, "On the diffraction theory of optical images", Proc. R. Soc. A 217, 408 (1953)(照明の開口と結像の開口の比)。
球冠の交わりの面積は、2 つの小円の交わる球面多角形の面積(Girard の定理)から導いた式で、テストでモンテカルロと照合した。

EXTEND: 照明は「各点に同じ円錐」の遠方場の極限(レンズで光源を無限遠に置いた照明・ケーラー照明)。近接した拡散板の
同軸照明は場所ごとに円錐の向きが変わる(``light_source`` の ``"coaxial"`` と ``defect_contrast`` が扱う側。この PoC は呼ばない)。カメラもテレセン
(どの画素も真上から同じ円錐)を仮定した —— 通常のレンズでは主光線が傾くので、視野の端で ψ が実質的に変わる
(``telecentric`` の ``chief_ray_angle`` で傾きを求めて ψ に足せる)。Fresnel の反射率は小さい角では一定として扱い、
回折(瞳が小さいと 1.22λ/NA のぼけ)と多重反射は入れていない。円錐の中の放射輝度は一様とした(縁の減衰は無い)。

★2026-11-15(ViEW2026 の目玉に上げる前の独立レビュー): 見出しの数は ``HEADLINE`` に full と reduced の印字の値で持ち、
実行の値と照合する門を置いた。「α = β では見えない帯が 0」は閉形式 |α − β|/2 に α = β を入れただけ(定義どおり)なので
``check``(検算)にし、門の数に入れない。カードの表紙は 15 枚の図(02)ではなく、ヘアラインと打痕の 2 × 2(07)にした
(02 の打痕の段で α = 0.5°・4°・7° がほぼ無地なのは閉形式の予言どおりで、縮めると壊れた図に見えた)。
"""
from __future__ import annotations

import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import examplefig as figs  # noqa: E402
import glassmirror  # noqa: E402
import illumdesign as ID  # noqa: E402
import metalfinish  # noqa: E402

REDUCED = os.environ.get("FULLSEYE_POC_BUDGET",
                         "reduced" if os.environ.get("CI") else "full") == "reduced"

FAILS: list[str] = []
GATES: list[str] = []
CHECKS: list[str] = []
NUMBERS: dict[str, float] = {}
#: 見出しに載せる数を、印字と同じ丸めの文字列で集める(``check_headline`` が ``HEADLINE`` と照合する)。
SHOWN: dict[str, str] = {}

#: 見出しの数(台帳 poc_captions.json と ViEW2026 のカードに載せる値)。full は手元の full の実行、reduced は
#: CI(縮小)の実行の印字。符号は落として持つ(説明文の − と照合するため)。数が動いたら台帳を転記し直してから直す。
HEADLINE = {
    "full": {
        "cf_vs_numeric": "0.002", "dent_c_clean": "0.091", "dent_ring_worst": "0.0001", "dent_c_textured": "0.070",
        "hair_q99": "0.82", "band_lo": "3.5", "band_hi": "6.1", "hair_std_ratio": "0.014", "scratch_c_4": "1.00",
        "knife_flat": "0.39", "knife_left": "0.53", "knife_right": "0.25", "knife_left_cf": "0.54", "knife_right_cf": "0.25",
        "satin_c_matched": "0.20", "satin_c_wide": "0.02", "wavy_ratio": "1.6",
        "rough_c0": "0.091", "rough_c025": "0.031", "rough_c1": "0.012", "rough_c4": "0.001", "pin_gain": "10.7",
    },
    "reduced": {
        "cf_vs_numeric": "0.002", "dent_c_clean": "0.091", "dent_ring_worst": "0.0004", "dent_c_textured": "0.079",
        "hair_q99": "0.82", "band_lo": "3.5", "band_hi": "6.1", "hair_std_ratio": "0.006", "scratch_c_4": "1.00",
        "knife_flat": "0.39", "knife_left": "0.54", "knife_right": "0.26", "knife_left_cf": "0.54", "knife_right_cf": "0.25",
        "satin_c_matched": "0.19", "satin_c_wide": "0.02", "wavy_ratio": "2.1",
        "rough_c0": "0.091", "rough_c025": "0.031", "rough_c1": "0.012", "rough_c4": "0.001", "pin_gain": "10.7",
    },
}

NA = 0.033                                   # 物体側 NA(テレセンの検査レンズの代表的な桁)
BETA = math.degrees(math.asin(NA))           # 観察の円錐の半角 ≈ 1.89°
SIZE = 192 if REDUCED else 384               # 画素
PITCH_UM = 3072.0 / SIZE                     # 視野 3.07 mm
SAMPLES = 96 if REDUCED else 160             # 瞳(または光源)の標本数


def gate(name: str, ok: bool, detail: str = "") -> None:
    print("   [%s] %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    GATES.append(name)
    if not ok:
        FAILS.append(name)


def check(name: str, ok: bool, detail: str = "") -> None:
    """定義上成り立つ量の検算。落ちれば PoC は止まるが、門の数には数えない(2026-11-15 の独立レビュー)。"""
    print("   [%s] 検算(門に数えない): %s%s" % ("ok" if ok else "NG", name, (" — " + detail) if detail else ""))
    CHECKS.append(name)
    if not ok:
        FAILS.append(name)


def _abs(fmt: str, v: float) -> str:
    """見出しの照合用の文字列(符号を落とす —— 説明文は − を U+2212 で書くので、数字の並びだけを照合する)。"""
    return (fmt % v).lstrip("+-")


def check_headline() -> None:
    """見出しの数を守る門: 今の実行が印字した値(``SHOWN``)が、記録(``HEADLINE``、この予算のもの)と文字列で一致する。"""
    want = HEADLINE["reduced" if REDUCED else "full"]
    diff = {k: (want[k], SHOWN.get(k)) for k in want if SHOWN.get(k) != want[k]}
    print("   見出しの数(この実行): " + "  ".join("%s=%s" % (k, SHOWN.get(k)) for k in want))
    gate("見出しの数(%d 個)が記録 HEADLINE[%s] と一致する" % (len(want), "reduced" if REDUCED else "full"), not diff,
         "食い違い(記録, 実行): %s" % diff if diff else "")


# --------------------------------------------------------------------------- #
# ワーク(高さ [µm] と微小面の粗さ [deg])
# --------------------------------------------------------------------------- #
def _grid():
    c = (np.arange(SIZE) - (SIZE - 1) / 2.0) * PITCH_UM
    return np.meshgrid(c, c)


def _normals(h_um):
    gy, gx = np.gradient(h_um, PITCH_UM)
    n = np.dstack([-gx, -gy, np.ones_like(h_um)])
    return n / np.linalg.norm(n, axis=2, keepdims=True)


def _smooth_noise(shape, cell, seed):
    """セルの粗い乱数を三次で引き伸ばした、なめらかな斑。"""
    from scipy import ndimage
    rng = np.random.default_rng(seed)
    g = rng.standard_normal((max(shape[0] // cell, 2) + 3, max(shape[1] // cell, 2) + 3))
    z = ndimage.zoom(g, (shape[0] / (g.shape[0] - 3), shape[1] / (g.shape[1] - 3)), order=3)
    return z[:shape[0], :shape[1]]


DENT_DEPTH_UM = 2.0
DENT_SIGMA_UM = 280.0


def dent_height(X, Y, cx=0.0, cy=0.0):
    """ガウス形の浅い打痕(深さ 2 µm、σ 0.28 mm)。斜面の最大傾き = d/σ·e^{-1/2}。"""
    return -DENT_DEPTH_UM * np.exp(-((X - cx) ** 2 + (Y - cy) ** 2) / (2 * DENT_SIGMA_UM ** 2))


def dent_max_slope_deg():
    return math.degrees(math.atan(DENT_DEPTH_UM / DENT_SIGMA_UM * math.exp(-0.5)))


def work_dent(waviness_deg=0.0, clean=False):
    """鏡面研磨のアルミ: 打痕 1 つ + 研磨の微細な目(blast_normals、ごく弱い)と微小面の広がり 0.05°。

    *clean*: 質感を外した同じ打痕(門で閉形式と突き合わせる用 —— 粗さはコントラストを下げるので、閉形式(滑らかな
    鏡面)と比べるときは外す。粗さの効き方は 5 章)。
    """
    X, Y = _grid()
    h = dent_height(X, Y)
    if waviness_deg > 0:
        lam = 1500.0
        amp = math.tan(math.radians(waviness_deg)) * lam / (2 * math.pi)
        h = h + amp * np.sin(2 * math.pi * (X * 0.8 + Y * 0.6) / lam)
    if clean:
        return _normals(h), np.zeros(h.shape), h
    n = metalfinish.blast_normals(_normals(h), grain=0.0002, cell_px=2.0, seed=3)
    return n, np.full(h.shape, 0.05), h


SCRATCH_SLOPE_DEG = 4.0
SCRATCH_HALF_UM = 60.0


def work_hairline():
    """ヘアラインのステンレス(色はクロムの n,k で代用): x 方向の筋(乱数の線 + metalfinish の研磨目)と、斜めに走る V 溝の傷(斜面 4°)。"""
    from scipy import ndimage
    X, Y = _grid()
    rng = np.random.default_rng(11)
    lines = rng.standard_normal((SIZE, SIZE))
    lines = ndimage.gaussian_filter(lines, (0.9, 40.0))            # x に長く、y に細い筋
    lines *= 0.30 / max(np.std(np.gradient(lines, PITCH_UM)[0]) * 180 / math.pi, 1e-12) * 1.0
    # 傷: 中心線から距離 u、V 溝(半幅 30 µm、斜面 4°)、長さ方向に少し蛇行
    ang = math.radians(28.0)
    u = (X * math.sin(ang) - Y * math.cos(ang)) + 25.0 * np.sin(X / 380.0)
    v = X * math.cos(ang) + Y * math.sin(ang)
    groove = -np.clip(SCRATCH_HALF_UM - np.abs(u), 0, None) * math.tan(math.radians(SCRATCH_SLOPE_DEG))
    groove *= (np.abs(v) < 1250.0)
    h = lines + ndimage.gaussian_filter(groove, 0.6)
    n = metalfinish.micro_normals(_normals(h), kind="linear", pitch_px=3.0, depth=0.0025, angle_deg=0.0)
    scratch = (np.abs(u) < SCRATCH_HALF_UM - 1.5 * PITCH_UM) & (np.abs(u) > 1.5 * PITCH_UM) & (np.abs(v) < 1200.0)
    return n, np.full(h.shape, 0.12), scratch


def work_satin():
    """梨地のアルミ: 微小面の傾きの広がり σ が 0.8° の地に、1.3° の斑(ブラストのむら)。画素の凹凸は blast_normals。"""
    X, Y = _grid()
    m = _smooth_noise((SIZE, SIZE), max(SIZE // 6, 4), 21)
    patch = 1.0 / (1.0 + np.exp(-(m - 0.7) * 6.0))
    sig = 0.8 + 0.5 * patch
    n0 = np.dstack([np.zeros((SIZE, SIZE)), np.zeros((SIZE, SIZE)), np.ones((SIZE, SIZE))])
    n = metalfinish.blast_normals(n0, grain=0.006, cell_px=2.0, seed=5)
    return n, sig, patch > 0.5


# --------------------------------------------------------------------------- #
# 照明(円錐)と撮影
# --------------------------------------------------------------------------- #
LIGHTS = [("α=0.5°", 0.5, 0.0), ("α=β", BETA, 0.0), ("α=4°", 4.0, 0.0), ("α=7°", 7.0, 0.0),
          ("α=β・β傾け", BETA, BETA)]


def shoot(n, sig, alpha, psi, metal="al", seed=0, noise=True):
    """明るさ(放射輝度比)と、金属の色・センサの雑音を載せた線形 RGB を返す。露光は平らな地が 0.75 になるよう円錐ごとに合わせる。"""
    lt = ID.solid_angle_light(alpha, tilt_deg=psi)
    B = ID.solid_angle_render(n, lt, view_na=NA, roughness_deg=sig, f0=1.0, n_samples=SAMPLES, seed=seed)
    flat = ID.solid_angle_brightness(lt, view_na=NA, slopes_deg=[0.0], n_samples=4096)["rows"][0]["closed_form"]
    gain = 0.75 / max(flat, 1e-3)
    col = glassmirror.metal_mirror_rgb(metal, 1.0)
    # 実機らしさ: 照明の放射輝度のむら(中心から端へ 5 % 落ちる、わずかに偏心)。明るさ B(門が使う量)には掛けない。
    X, Y = _grid()
    r2 = ((X - 180.0) ** 2 + (Y + 120.0) ** 2) / (1536.0 ** 2)
    shade = 1.0 - 0.05 * r2 / 2.0
    rgb = (B * gain * shade)[..., None] * (col / col.max())[None, None, :]
    if noise:
        rng = np.random.default_rng(100 + seed)
        e = np.clip(rgb, 0, None) * 4000.0                   # 満杯 ≈ 5,300 e⁻
        rgb = (rng.poisson(e) + rng.normal(0, 6.0, e.shape)) / 4000.0
    return B, np.clip(rgb, 0, 1)


# --------------------------------------------------------------------------- #
# 1. 閉形式
# --------------------------------------------------------------------------- #
def chapter_closed_form():
    print("\n1. 閉形式: 球冠の交わり(観察の半角 β = %.3f°、NA %.3f)" % (BETA, NA))
    out = {}
    worst = 0.0
    for name, a, psi in LIGHTS:
        lt = ID.solid_angle_light(a, tilt_deg=psi)
        bd = ID.solid_angle_boundaries(lt, view_na=NA)
        print("   %-10s regime=%-12s 平らな地 %.4f  見えない傾き < %.3f°  暗くなる傾き > %.3f°"
              % (name, bd["regime"], bd["flat_brightness"], bd["invisible_below_deg"], bd["dark_beyond_deg"]))
        sl = list(np.linspace(-6.0, 6.0, 121))
        r = ID.solid_angle_brightness(lt, view_na=NA, slopes_deg=sl, n_samples=4096)["rows"]
        cf = np.array([x["closed_form"] for x in r])
        nu = np.array([x["numeric"] for x in r])
        out[name] = (np.array(sl), cf, nu, bd)
        worst = max(worst, float(np.max(np.abs(cf - nu))))
    NUMBERS["cf_vs_numeric_worst"] = worst
    gate("球冠の交わりの閉形式とレンズの瞳の数値積分の差 < 0.01(全照明 × 傾き −6〜6°、最大 %.4f)" % worst, worst < 0.01)
    SHOWN["cf_vs_numeric"] = _abs("%.3f", worst)
    # 境界の外では一定(浅い打痕は α = 0.5° と 7° で消える)
    s = dent_max_slope_deg()
    NUMBERS["dent_max_slope_deg"] = s
    flats = {}
    for name in ("α=0.5°", "α=7°"):
        bd = out[name][3]
        flats[name] = bd["invisible_below_deg"]
    gate("打痕の最大傾き %.3f° は α=0.5° の見えない帯 %.3f° と α=7° の %.3f° の内側(閉形式で「消える」と予言)"
         % (s, flats["α=0.5°"], flats["α=7°"]), s < flats["α=0.5°"] and s < flats["α=7°"])
    bm = out["α=β"][3]
    # ★見えない帯は閉形式 |α − β|/2。α = β を入れれば 0 になるのは定義どおり(門に数えない)。
    check("α = β では見えない帯が 0(どんな小さな傾きも暗くなる)", bm["invisible_below_deg"] == 0.0)
    # 高 NA では瞳の重み(射影立体角)と立体角の差が育つ: O(β²)
    diffs = []
    for na in (0.033, 0.1, 0.3):
        b = math.degrees(math.asin(na))
        r = ID.solid_angle_brightness(ID.solid_angle_light(b), view_na=na, slopes_deg=[b / 2], n_samples=16384)["rows"][0]
        diffs.append(abs(r["numeric"] - r["closed_form"]))
    NUMBERS["weight_diff_na03"] = diffs[-1]
    print("   瞳の重みの差(α = β、θ = β/2): NA 0.033 → %.4f、0.1 → %.4f、0.3 → %.4f" % tuple(diffs))
    gate("閉形式(立体角で一様)と瞳(射影立体角)の差は NA 0.3 まで 0.005 未満(この PoC の NA 0.033 では %.1e)" % diffs[0],
         max(diffs) < 0.005)
    return out


# --------------------------------------------------------------------------- #
# 2. 3 つのワーク × 5 つの照明
# --------------------------------------------------------------------------- #
def _contrast(img, mask, ref):
    a, b = float(img[mask].mean()), float(img[ref].mean())
    return (a - b) / (a + b) if (a + b) > 0 else 0.0


def chapter_works():
    print("\n2. 3 つのワーク × 5 つの照明(NA %.3f、%d 画素、%.1f µm/画素)" % (NA, SIZE, PITCH_UM))
    X, Y = _grid()
    R = np.hypot(X, Y)
    works = {"dent": work_dent(), "hairline": work_hairline(), "satin": work_satin()}
    shots = {}
    for wk, (n, sig, _m) in works.items():
        for i, (name, a, psi) in enumerate(LIGHTS):
            shots[(wk, name)] = shoot(n, sig, a, psi, metal="al" if wk != "hairline" else "cr", seed=i)
    # 打痕: 最大傾きの輪(r = σ)の明るさを閉形式と
    ring = np.abs(R - DENT_SIGMA_UM) < 1.5 * PITCH_UM
    bg = R > 4 * DENT_SIGMA_UM
    s = dent_max_slope_deg()
    nc, sc, _hc = work_dent(clean=True)
    clean = {name: shoot(nc, sc, a, psi, noise=False)[0] for name, a, psi in LIGHTS}
    rows = []
    for name, a, psi in LIGHTS[:4]:
        B = clean[name]
        lt = ID.solid_angle_light(a, tilt_deg=psi)
        cf = ID.solid_angle_brightness(lt, view_na=NA, slopes_deg=[0.0, s], n_samples=4096)["rows"]
        c_cf = (cf[1]["closed_form"] - cf[0]["closed_form"]) / (cf[1]["closed_form"] + cf[0]["closed_form"])
        c_im = _contrast(B, ring, bg)
        c_tx = _contrast(shots[("dent", name)][0], ring, bg)
        rows.append((name, c_cf, c_im))
        print("   打痕 %-8s 輪のコントラスト: 画像 %+.4f  閉形式 %+.4f  (質感つき %+.4f)" % (name, c_im, c_cf, c_tx))
        if name == "α=β":
            SHOWN["dent_c_textured"] = _abs("%.3f", c_tx)
    worst = max(abs(a - b) for _n, a, b in rows)
    NUMBERS["dent_ring_worst"] = worst
    gate("画像から測った打痕の輪(傾き %.2f°、質感なし)のコントラストは閉形式と 0.01 以内(4 照明、最大 %.4f)" % (s, worst),
         worst < 0.01)
    SHOWN["dent_ring_worst"] = _abs("%.4f", worst)
    cm = dict((n, c) for n, _c, c in rows)
    NUMBERS["dent_c_matched"] = cm["α=β"]
    NUMBERS["dent_c_wide"] = cm["α=7°"]
    NUMBERS["dent_c_pin"] = cm["α=0.5°"]
    SHOWN["dent_c_clean"] = _abs("%.3f", cm["α=β"])
    flat_pin = ID.solid_angle_brightness(ID.solid_angle_light(0.5), view_na=NA, slopes_deg=[0.0], n_samples=4096)["rows"][0]
    SHOWN["pin_gain"] = "%.1f" % (0.75 / max(flat_pin["closed_form"], 1e-3))
    print("   露光は円錐ごとに平らな地へ合わせる: α = 0.5° の平らな地 %.4f → 利得 %s 倍(実機ではその分だけ露光を延ばす)"
          % (flat_pin["closed_form"], SHOWN["pin_gain"]))
    gate("α = β では打痕が出る(|C| = %.3f > 0.05)、α = 7° と 0.5° では消える(|C| < 0.005: %.4f / %.4f)"
         % (abs(cm["α=β"]), abs(cm["α=7°"]), abs(cm["α=0.5°"])),
         abs(cm["α=β"]) > 0.05 and abs(cm["α=7°"]) < 0.005 and abs(cm["α=0.5°"]) < 0.005)
    # 梨地のムラ: 斑と地
    _n, sig, pm = works["satin"]
    ref = (sig < 0.85)
    cs = {}
    for name, _a, _p in LIGHTS:
        cs[name] = _contrast(shots[("satin", name)][0], pm, ref)
    NUMBERS["satin_c_matched"] = cs["α=β"]
    NUMBERS["satin_c_wide"] = cs["α=7°"]
    SHOWN.update(satin_c_matched=_abs("%.2f", cs["α=β"]), satin_c_wide=_abs("%.2f", cs["α=7°"]))
    print("   梨地の斑のコントラスト: " + "  ".join("%s %+.3f" % (k, v) for k, v in cs.items()))
    gate("梨地の斑(σ 1.3° 対 0.8°): α = β で |C| = %.3f、α = 7° で %.4f(広い円錐は微小面の広がりを呑み込む)"
         % (abs(cs["α=β"]), abs(cs["α=7°"])), abs(cs["α=β"]) > 0.1 and abs(cs["α=7°"]) < 0.2 * abs(cs["α=β"]))
    works["dent_clean"] = (nc, sc, None)
    shots.update({("dent_clean", k): (v, None) for k, v in clean.items()})
    return works, shots


# --------------------------------------------------------------------------- #
# 3. 傾きの帯を選ぶ(ヘアラインは消して傷は黒く)
# --------------------------------------------------------------------------- #
def chapter_band(works, shots):
    print("\n3. 傾きの帯を選ぶ: ヘアラインの筋を消し、傷の斜面(%.0f°)を黒く" % SCRATCH_SLOPE_DEG)
    n, _sig, scratch = works["hairline"]
    tilt = np.degrees(np.arccos(np.clip(n[..., 2], -1, 1)))
    from scipy import ndimage
    far = ~ndimage.binary_dilation(scratch, iterations=12)
    q99 = float(np.percentile(tilt[far], 99))
    NUMBERS["hairline_q99_deg"] = q99
    lo = BETA + 2 * q99
    hi = 2 * SCRATCH_SLOPE_DEG - BETA
    print("   筋の傾きの 99 %% 点 %.3f° → α > β + 2·%.3f = %.2f°、傷を黒くするには α < 2·%.0f − β = %.2f°"
          % (q99, q99, lo, SCRATCH_SLOPE_DEG, hi))
    gate("閉形式で選べる帯がある(%.2f° < α < %.2f°)、α = 4° はその中" % (lo, hi), lo < 4.0 < hi)
    SHOWN.update(hair_q99="%.2f" % q99, band_lo="%.1f" % lo, band_hi="%.1f" % hi)
    sd = {name: float(np.std(shots[("hairline", name)][0][far])) for name, _a, _p in LIGHTS}
    cs = {name: _contrast(shots[("hairline", name)][0], scratch, far) for name, _a, _p in LIGHTS}
    for name in sd:
        print("   %-10s 筋の揺れ(std/平均) %.4f  傷のコントラスト %+.3f"
              % (name, sd[name] / max(float(shots[("hairline", name)][0][far].mean()), 1e-12), cs[name]))
    NUMBERS["hair_std_ratio"] = sd["α=4°"] / max(sd["α=β"], 1e-12)
    NUMBERS["scratch_c_4"] = cs["α=4°"]
    NUMBERS["scratch_c_7"] = cs["α=7°"]
    SHOWN.update(hair_std_ratio="%.3f" % NUMBERS["hair_std_ratio"], scratch_c_4=_abs("%.2f", cs["α=4°"]))
    gate("α = 4° で筋の揺れは α = β の 1/5 以下(%.3f 倍)、傷のコントラスト %.3f < −0.9"
         % (NUMBERS["hair_std_ratio"], cs["α=4°"]), NUMBERS["hair_std_ratio"] < 0.2 and cs["α=4°"] < -0.9)
    gate("★広げすぎ(α = 7°: (α − β)/2 = %.2f° < 4° < (α + β)/2 = %.2f° なので斜面は一部だけ暗い)では傷が薄まる(%.3f)"
         % ((7.0 - BETA) / 2, (7.0 + BETA) / 2, cs["α=7°"]), abs(cs["α=7°"]) < abs(cs["α=4°"]))
    return sd, cs


# --------------------------------------------------------------------------- #
# 4. 向きをずらす
# --------------------------------------------------------------------------- #
def chapter_knife(shots):
    print("\n4. 円錐を β 傾ける(ナイフエッジ): 傾きの符号が明暗で読める")
    X, Y = _grid()
    R = np.hypot(X, Y)
    B = shots[("dent_clean", "α=β・β傾け")][0]
    ring = np.abs(R - DENT_SIGMA_UM) < 1.5 * PITCH_UM
    # 円錐は +x へ傾く。打痕の +x 側の斜面は法線が −x(中心向き)、−x 側は +x
    right = ring & (np.abs(Y) < 0.25 * DENT_SIGMA_UM) & (X > 0)
    left = ring & (np.abs(Y) < 0.25 * DENT_SIGMA_UM) & (X < 0)
    s = dent_max_slope_deg()
    lt = ID.solid_angle_light(BETA, tilt_deg=BETA)
    cf = ID.solid_angle_brightness(lt, view_na=NA, slopes_deg=[-s, 0.0, s], n_samples=4096)["rows"]
    bl, br = float(B[left].mean()), float(B[right].mean())
    print("   −x 側の斜面 %.4f(閉形式 %.4f)、平ら %.4f、+x 側 %.4f(閉形式 %.4f)"
          % (bl, cf[2]["closed_form"], cf[1]["closed_form"], br, cf[0]["closed_form"]))
    NUMBERS["knife_left"] = bl
    NUMBERS["knife_right"] = br
    SHOWN.update(knife_flat="%.2f" % cf[1]["closed_form"], knife_left="%.2f" % bl, knife_right="%.2f" % br,
                 knife_left_cf="%.2f" % cf[2]["closed_form"], knife_right_cf="%.2f" % cf[0]["closed_form"])
    ok = abs(bl - cf[2]["closed_form"]) < 0.02 and abs(br - cf[0]["closed_form"]) < 0.02
    gate("左右の斜面の明るさが閉形式と 0.02 以内、符号が逆(片側が地より明るく、片側が暗い)",
         ok and (bl - cf[1]["closed_form"]) * (br - cf[1]["closed_form"]) < 0)
    bd = ID.solid_angle_boundaries(lt, view_na=NA)
    NUMBERS["knife_sens"] = bd["sensitivity_per_deg"]
    gate("平らな地は境界の上(regime=edge、明るさ %.3f、感度 %.3f /deg)" % (bd["flat_brightness"], bd["sensitivity_per_deg"]),
         bd["regime"] == "edge" and bd["sensitivity_per_deg"] > 0.1)


# --------------------------------------------------------------------------- #
# 5. 壊れる条件
# --------------------------------------------------------------------------- #
def chapter_failure():
    print("\n5. 壊れる条件: うねりと粗さ")
    X, Y = _grid()
    R = np.hypot(X, Y)
    n, sig, _h = work_dent(waviness_deg=0.25)
    out = {}
    for name, a, psi in (("α=β", BETA, 0.0), ("α=7°", 7.0, 0.0)):
        B, rgb = shoot(n, sig, a, psi, seed=7)
        bg = R > 4 * DENT_SIGMA_UM
        ring = np.abs(R - DENT_SIGMA_UM) < 1.5 * PITCH_UM
        swing = float(np.percentile(B[bg], 99) - np.percentile(B[bg], 1))
        depth = float(np.median(B[bg]) - B[ring].mean())
        out[name] = (rgb, swing, depth)
        print("   %-6s 地の揺れ(1–99 %%)%.4f  打痕の沈み %.4f" % (name, swing, depth))
    NUMBERS["wavy_ratio"] = out["α=β"][1] / max(abs(out["α=β"][2]), 1e-12)
    gate("うねり ±0.25° があると、α = β では地の揺れが打痕の沈みの %.1f 倍(> 0.5: しきい値で打痕だけを拾えない)"
         % NUMBERS["wavy_ratio"], NUMBERS["wavy_ratio"] > 0.5)
    SHOWN["wavy_ratio"] = "%.1f" % NUMBERS["wavy_ratio"]
    gate("広い円錐(α = 7°)はうねりも打痕も消す(揺れ %.4f、沈み %.4f)" % (out["α=7°"][1], out["α=7°"][2]),
         out["α=7°"][1] < 0.01 and abs(out["α=7°"][2]) < 0.01)
    # 粗さ
    s = dent_max_slope_deg()
    sigmas = [0.0, 0.25, 0.5, 1.0, 2.0, 4.0]
    curve = []
    for sg in sigmas:
        best = 0.0
        for a in (0.5, 1.0, BETA, 3.0):
            r = ID.solid_angle_brightness(ID.solid_angle_light(a), view_na=NA, slopes_deg=[0.0, s], roughness_deg=sg,
                                          n_samples=8192)["rows"]
            b0, b1 = r[0]["closed_form"], r[1]["closed_form"]       # Gauss–Hermite: 標本の雑音が無い
            best = max(best, abs(b1 - b0) / (b1 + b0))
        curve.append(best)
    print("   粗さ σ に対する打痕の最良コントラスト(α を 0.5〜3° で選んだ最大): "
          + "  ".join("σ=%.2f° %.3f" % (a, b) for a, b in zip(sigmas, curve)))
    NUMBERS["rough_c0"] = curve[0]
    NUMBERS["rough_c4"] = curve[-1]
    SHOWN.update(rough_c0="%.3f" % curve[0], rough_c025="%.3f" % curve[1], rough_c1="%.3f" % curve[3],
                 rough_c4="%.3f" % curve[-1])
    gate("★粗い面(σ = 4° > (α + β)/2)では α を 0.5〜3° の 4 通りから選んでも打痕のコントラストが滑らかな面の 1/4 以下(%.3f → %.3f)"
         % (curve[0], curve[-1]), curve[-1] < 0.25 * curve[0])
    return out, (sigmas, curve)


# --------------------------------------------------------------------------- #
# 6. 実画像
# --------------------------------------------------------------------------- #
def chapter_real():
    print("\n6. 実画像")
    print("   照明の立体角だけを変えて同じワークを撮った比較写真を、CC BY / CC0 などの再利用できるライセンスで探したが、")
    print("   見つからなかった(2026-10-15)。学会誌の図は学会の著作権表示で、ここには入れない。実画像との突合は未了。")


# --------------------------------------------------------------------------- #
# 図
# --------------------------------------------------------------------------- #
def _tone(rgb):
    return np.clip(rgb, 0, 1) ** (1 / 2.2)


def make_figures(cf, works, shots, fail):
    import fullseye as fs
    # 1. 明るさと傾き
    ser, sty, col, kinds = [], [], [], []
    pal = {"α=0.5°": "neutral", "α=β": "emphasis", "α=4°": "right", "α=7°": "wrong", "α=β・β傾け": "reference"}
    for name, _a, _p in LIGHTS:
        sl, c, nu, _bd = cf[name]
        ser.append((name, sl, c))
        sty.append(None if name != "α=β・β傾け" else "dashed")
        col.append(pal[name])
        kinds.append("line")
    figs.save_plot("brightness_vs_slope", ser, xlabel="面の傾き θ [°]", ylabel="明るさ(瞳のうち光る割合)",
                   styles=sty, colors=col, kinds=kinds,
                   title="明るさは 2 つの円錐の重なり(観察の半角 β = %.2f°)" % BETA,
                   caption="鏡面の傾き θ と、カメラの瞳が反射した光の円錐で覆われる割合(閉形式)。α = 7° と 0.5° は傾き "
                           "|α − β|/2 まで平らで、そこまでの傾きは見えない。α = β は 0 から下がり始めるので最も小さな傾きが見える。"
                           "β だけ傾けた円錐は平らな地が半分の明るさで、傾きの向きで明るくも暗くもなる。")
    # 2. 3 ワーク × 5 照明
    rows_img = []
    labels = {"dent": "鏡面の打痕(深さ 2 µm)", "hairline": "ヘアラインの傷(斜面 4°)", "satin": "梨地のムラ"}
    for wk in ("dent", "hairline", "satin"):
        tiles = []
        for name, _a, _p in LIGHTS:
            t = _tone(shots[(wk, name)][1])
            t = np.asarray(fs.text_box(t, name, (6, 6), anchor="lt", font_size=15))
            if name == LIGHTS[0][0]:
                t = np.asarray(fs.text_box(t, labels[wk], (6, SIZE - 8), anchor="lb", font_size=15))
            tiles += [t, np.ones((SIZE, 6, 3))]
        rows_img += [np.concatenate(tiles[:-1], 1), np.ones((6, (SIZE + 6) * len(LIGHTS) - 6, 3))]
    grid = np.concatenate(rows_img[:-1], 0)
    figs.save("works_by_cone", grid,
              "合成: 同じ 3 つのワークを、物体側 NA %.3f(β = %.2f°)のテレセンで、照明の円錐だけを変えて撮った(3.07 mm 角)。"
              "打痕の段で α = 0.5°・4°・7° がほぼ無地なのは、閉形式の予言どおり打痕が消えるため(壊れた図ではない)。"
              "打痕は α = β でだけ輪になって見え、α = 0.5° と 7° では消える。ヘアラインは α = β で筋が目立つが、"
              "α = 4° で筋が消えて傷だけが黒く残る。梨地の斑は狭い円錐で浮き、広い円錐で消える。右端は α = β を β 傾けた"
              "円錐で、打痕の左右の斜面が明暗に分かれて浮き彫りに見える。" % (NA, BETA))
    # 3. 帯を選ぶ: α を掃いた曲線(打痕・筋・傷)
    als = [float(v) for v in np.linspace(0.3, 9.0, 30)]
    s = dent_max_slope_deg()
    sw_d = ID.solid_angle_sweep(slope_deg=s, view_na=NA, half_angles_deg=als)
    sw_h = ID.solid_angle_sweep(slope_deg=NUMBERS["hairline_q99_deg"], view_na=NA, half_angles_deg=als)
    sw_s = ID.solid_angle_sweep(slope_deg=SCRATCH_SLOPE_DEG, view_na=NA, half_angles_deg=als)
    figs.save_plot("contrast_vs_cone", [("打痕の斜面 %.2f°" % s, sw_d[:, 0], sw_d[:, 1]),
                                        ("ヘアラインの筋 %.2f°" % NUMBERS["hairline_q99_deg"], sw_h[:, 0], sw_h[:, 1]),
                                        ("傷の斜面 %.0f°" % SCRATCH_SLOPE_DEG, sw_s[:, 0], sw_s[:, 1])],
                   xlabel="照明の円錐の半角 α [°]", ylabel="平らな地とのコントラスト",
                   colors=["emphasis", "neutral", "wrong"],
                   title="α を選ぶと、見たい傾きの帯だけが残る(β = %.2f°)" % BETA,
                   caption="傾き θ の面と平らな地のコントラストを α に対して(微小面の粗さ 0)。どの曲線も α = β 付近で山になり、"
                           "|α − β| ≥ 2θ で 0 に落ちる。α = 4° は筋(0 に落ちた後)と傷(まだ 1 に近い)の間にある。")
    # 4. 失敗: うねり
    out, (sigmas, curve) = fail
    v = np.concatenate([_tone(out["α=β"][0]), np.ones((SIZE, 6, 3)), _tone(out["α=7°"][0])], 1)
    v = np.asarray(fs.text_box(v, "α=β", (6, 6), anchor="lt", font_size=15))
    v = np.asarray(fs.text_box(v, "α=7°", (SIZE + 12, 6), anchor="lt", font_size=15))
    figs.save("waviness_failure", v,
              "面のうねり(周期 1.5 mm、傾き ±0.25°)を足した鏡面の打痕。α = β では、うねりの縞が打痕と同じ濃さで"
              "地を覆う(しきい値で打痕だけを拾えない)。α = 7° ではうねりも打痕も消える。")
    figs.save_plot("roughness_failure", [("最良の α でのコントラスト", sigmas, curve)],
                   xlabel="微小面の傾きの広がり σ [°]", ylabel="打痕(%.2f°)のコントラスト" % s, kinds=["scatter"],
                   colors=["wrong"], title="粗い面では円錐の設計が効かない",
                   caption="α を 0.5〜3° から選んだ最大のコントラスト。σ が (α + β)/2 を越えると、どの円錐でも傾きの差は"
                           "微小面の広がりに埋もれる。")
    if figs.target_dir() is not None:
        gsz = SIZE
        n, sig, _m = works["hairline"]
        frames = []
        seq = list(np.linspace(0.4, 8.0, 16)) + list(np.linspace(8.0, 0.4, 16))[1:-1]
        for a in seq:
            _B, rgb = shoot(n, sig, float(a), 0.0, metal="cr", seed=1)
            t = _tone(rgb)
            t = np.asarray(fs.text_box(t, "α = %.1f°  (β = %.2f°)" % (a, BETA), (6, 6), anchor="lt", font_size=26))
            frames.append((np.clip(t[:gsz, :gsz], 0, 1) * 255).astype(np.uint8))
        figs.save_gif("hairline_cone_sweep", frames,
                      "ヘアラインの上の傷を、照明の円錐の半角 α だけを 0.4〜8° で往復させて撮る。α ≈ β で筋が最も目立ち、"
                      "α ≈ 4° で筋が消えて傷が黒く残り、広げすぎると傷も薄れる。", fps=6)
    # ★2026-11-15(独立レビュー): 15 枚の図(02)を縮めたカードでは α の札が読めず、打痕の段の無地が壊れた図に見えた。
    #   ヘアライン(α = β と α = 4°)と打痕(α = β と β 傾けた α = β)の 2 × 2 を、カードの幅(260 px)で札が 14 px 以上に
    #   なる大きさで組む(ViEW2026 のカード・サムネイル・物語の GIF の 1 コマ目)。英語のページにも同じ GIF が出るので、
    #   札は記号だけ、段の名前は日英を併記する。
    figs.save("cone_cover", _cover(shots), "合成(一様な遠方場の円錐・テレセン NA %.3f、β = %.2f°)。上: ヘアラインの上の傷。"
              "α = β では筋が目立ち、α = 4° では筋が消えて傷だけが黒く残る。下: 鏡面の打痕(深さ 2 µm、中央を 2 倍に拡大)。"
              "α = β で輪、円錐を β 傾ける(ψ = β)と左右の斜面が明暗に分かれる。" % (NA, BETA))


def _zoom_rgb(rgb, k):
    """RGB を双三次で k 倍にする(最近傍の画素複製は発表図で使わない)。"""
    from PIL import Image
    ch = [np.asarray(Image.fromarray(np.asarray(rgb[..., c], np.float32), mode="F").resize(
        (rgb.shape[1] * k, rgb.shape[0] * k), Image.Resampling.BICUBIC)) for c in range(3)]
    return np.clip(np.dstack(ch), 0, 1)


def _cover(shots):
    """表紙の 2 × 2(720 × 720)。札は 38 px の板つき(カードの 260 px で約 14 px)、段の名前は日英を併記。"""
    import fullseye as fs
    tw, th, gap, band = 350, 280, 20, 76
    W = 2 * tw + gap
    H = 2 * (band + th) + 8
    canvas = np.ones((H, W, 3))
    rows = [("ヘアラインの傷 / hairline scratch", [("hairline", "α=β", "α = β"), ("hairline", "α=4°", "α = 4°")]),
            ("鏡面の打痕 / mirror dent", [("dent", "α=β", "α = β"), ("dent", "α=β・β傾け", "α = β, ψ = β")])]
    zoom = 1.6
    ch, cw = int(round(th / zoom)), int(round(tw / zoom))
    y = 0
    for title, tiles in rows:
        canvas = np.asarray(fs.text_box(canvas, title, (W // 2, y + band // 2), anchor="cm", font_size=28, box_alpha=0.0))
        y += band
        for j, (wk, light, tag) in enumerate(tiles):
            x = j * (tw + gap)
            t = _tone(shots[(wk, light)][1])
            if wk == "hairline":
                r0, c0 = (SIZE - th) // 2, (SIZE - tw) // 2
                tile = t[r0:r0 + th, c0:c0 + tw]
            else:
                # 打痕の中心を札の下(タイルの縦 160 px)へ置き、1.6 倍に拡大する(輪の半径 35 画素 → 56 px)
                r0 = SIZE // 2 - int(round(160 / zoom))
                c0 = SIZE // 2 - cw // 2
                tile = _zoom_rgb(t[r0:r0 + ch, c0:c0 + cw], 1)
                from PIL import Image
                tile = np.clip(np.dstack([np.asarray(Image.fromarray(np.asarray(tile[..., k], np.float32), mode="F").resize(
                    (tw, th), Image.Resampling.BICUBIC)) for k in range(3)]), 0, 1)
            canvas[y:y + th, x:x + tw] = tile[:th, :tw]
            canvas = np.asarray(fs.text_box(canvas, tag, (x + 4, y + 4), anchor="lt", font_size=38))
        y += th + 8
    return np.clip(canvas, 0, 1)


def main():
    t0 = time.time()
    print("PoC 照明の立体角と観察の NA(予算 %s)" % ("reduced" if REDUCED else "full"))
    cf = chapter_closed_form()
    works, shots = chapter_works()
    chapter_band(works, shots)
    chapter_knife(shots)
    fail = chapter_failure()
    chapter_real()
    print("\n7. 見出しの数")
    check_headline()
    if not REDUCED and figs.target_dir() is not None:
        make_figures(cf, works, shots, fail)
    print("\n所要 %.1f s、門 %d 件中 NG %d 件(ほかに門に数えない検算 %d 件)" % (time.time() - t0, len(GATES), len(FAILS),
                                                                     len(CHECKS)))
    if FAILS:
        print("FAIL: " + ", ".join(FAILS))
        sys.exit(1)
    assert not figs.errors(), figs.errors()
    print("PASS")


if __name__ == "__main__":
    main()
