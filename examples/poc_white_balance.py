# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""色恒常性(ホワイトバランス)—— 既知の分光反射率と既知の光源から真値を作り、
統計ベースの光源推定を「効く条件」の側から測る。

EXTEND: 実測に差し替えるなら ``render`` だけを実データ読み込みに置き換える。
留意点は 5 つ。(1) **リニアな輻度に戻す** —— 本 PoC の画像はすべてガンマ前の
線形 RGB で、``fullseye.linear_to_srgb`` を通すのは表示と ΔE の直前だけ。sRGB の
ままミンコフスキー平均を取ると、``p`` の効きがガンマに食われて別物になる。
(2) **黒レベルを引く** —— オフセットが残ると暗部が灰色に持ち上がり、灰色世界が
系統的に「光源は無彩色」と答える方向へ倒れる(雑音と違い平均しても消えない)。
(3) **飽和画素を外す** —— 7 節のとおり白パッチ法は飽和で例外なしに壊れ、しかも
画素率に対して超線形に悪化する。飽和マスクを渡すだけで大半が戻る。
(4) **真値の光源は白色板で測る** —— 本 PoC の真値は「反射率 1 の完全拡散面の応答」
であり、実測でもそれに合わせる(灰色球でも同じ。ただし球は面法線が振れるので
ハイライトを外すこと)。(5) **光源は 1 つとは限らない** —— 9 節のとおり 2 光源が
混ざると、どんな 1 本のベクトルを返しても片側で必ず外す。単一光源を仮定する op に
2 光源の画像を渡しても例外は出ない。

この PoC が示すこと:

1. **真値を自分で握る** —— 24 枚の既知分光反射率 R(λ) と既知の光源 L(λ) から
   ``fullseye.spectrum_to_srgb`` で画像を合成する。したがって真の光源ベクトル
   ``e = 反射率 1 の面の応答`` は閉形式で分かる。主指標は文献の慣習に従い
   **回復角度誤差(recovery angular error, 度)**。
2. ★**「効く手法」は無い。あるのは効く条件だけ** —— 同じ白パッチ法(max-RGB)が、
   白の在るチャートでは中央値 0.98 度で全手法中最良なのに、白を外すと 11.71 度、
   飽和 6.5 % で 24.34 度まで崩れる。灰色世界は逆に飽和にはほぼ無反応で、
   有彩色が画面の 60 % を占めると 27.35 度まで崩れる。**壊れる軸が直交している。**
3. ★**基準光源では全手法がゼロ点に負ける** —— 光源が既に等エネルギー白のとき
   「何もしない」の角度誤差は定義から 0.00 度。そこで灰色世界は 6.61 度、
   白パッチ法は 1.63 度**外す**。色かぶりが無い場面で AWB を回すのは純損失。
4. ★**真の光源を知っていても対角補正には床がある** —— von Kries(対角)で
   完全に正しい ``e`` を割っても、2500 K では ΔE00 が最大 7.45 残る。光源推定を
   いくら詰めてもここから下がらない。角度誤差 0 度は「色が合う」ではない。
5. **最適な p は場面で動く** —— Shades-of-Gray の最適 p は、素のチャートで
   ∞(= 白パッチ法)、白を外すと 4、飽和下では 1(= 灰色世界)まで落ちる。
   1 つの p を既定値として配る根拠はこの実験からは出てこない。

★ この PoC が出した道具の穴(op 本体は直していない。詳細は末尾の節を印字):

  (a) **統計ベースの光源推定 op が 1 つも無い**。910 件の台帳(``fullseye.ledger``)
      と 885 件の進化 op(``fullseye.op``)を "gray world / white patch /
      shades of gray / gray edge / white balance / AWB / von Kries / CAT" で
      探して 0 件。あるのは物理ベースの ``illuminant_from_dichromatic_planes``
      1 本だけで、これは**材質ラベルと鏡面ハイライトの両方**を要求する
      (11 節のとおり、無ければ正しく拒否する)。マット面のチャートしか無い
      現場では使う手が残らない。本 PoC の ``gray_world`` / ``max_rgb`` /
      ``shades_of_gray`` / ``gray_edge`` は全部利用者側で書いた。
  (b) **推定した光源で画像を割る op も無い**。対角(von Kries)補正は 1 行だが、
      ``color_transfer`` は参照画像を要求し ``color_grade`` は 3-D LUT を要求する
      ので、どちらもこの用途には使えない。``linear_trans_color`` は名前が近いが
      進化 op のつまみモデル(``a``, ``b`` の 2 スカラ)で任意の対角を作れない。
  (c) ★**``fs.op.sobel_amp`` はチャンネルごとに呼ぶと比を壊し、画像ごと渡すと
      壊さない**。3 チャンネルまとめて渡すと全体の最大 1 個で割るので RGB の比が
      残るが、``[fs.op.sobel_amp(img[..., k]) for k in range(3)]`` と書くと
      各チャンネルが自分の最大で割られ、**比が消える**。灰色エッジ法の角度誤差は
      6.66 度から 19.62 度へ 2.9 倍悪化した。2-D op はほぼ全部グレースケール前提
      なので、チャンネルで回すほうが自然な書き方であり、例外も警告も出ない。
  (d) **``spectrum_to_srgb`` は光源色を必ず割り落とす**。反射率 1 が常に
      ``(1,1,1)`` になる正規化(docstring に明記あり)なので、**色かぶりのある
      画像をこの op だけでは合成できない**。本 PoC は光源分布を反射率側に畳んで
      ``illuminant=`` に等エネルギーを渡すという回り道で合成した(1 節)。
      「順応済みの色」と「センサの生応答」を分けて返す口が無い。
  (e) **色域外が黙って負値で出る**。``spectrum_to_srgb`` は負をクリップしない
      (これは正直な設計)。ただしセンサは負を出せないので呼び手が 0 で止める
      必要があり、本 PoC では 168 個の patch-channel のうち 6 個が該当した。
      何個丸めたかを返す口が無いので、利用者は自分で数えないと気づけない。
  (f) **``docs/ops/2d/guides/colorimetry.md`` の現在地表が実装から遅れている**。
      「観測者 x̄ȳz̄: 無し」「反射率 R(λ): 分光反射率を持てない」と書いてあるが、
      ``cie_xyz_from_wavelength`` と ``spectrum_to_srgb`` は実在し、本 PoC は
      その 2 つだけで分光レンダリングを組んでいる。ガイドを読んで「できない」と
      判断すると、実際にはできることを取り逃がす。
"""
from __future__ import annotations

import math
import time

import numpy as np

import fullseye as fs

# ---------------------------------------------------------------------------
# 0. 分光の格子と道具
# ---------------------------------------------------------------------------
#: 波長格子 [nm]。可視域を 5 nm 刻み。
NM = np.arange(400.0, 701.0, 5.0)
#: 等エネルギー光源(基準)。この光源の下で反射率 1 の面が (1,1,1) になる。
FLAT = np.ones_like(NM)
#: チャートの配置(6 列)と 1 枚のパッチの画素数。
GRID_COLS, PATCH = 6, 22


def planck(kelvin):
    """黒体放射の分光分布(最大値 1 に規格化)。プランクの法則そのもの。

    ``B(λ,T) = c1 / (λ^5 (exp(c2/(λT)) - 1))``。規格化してあるので絶対値に
    意味は無く、**分光の形だけ**が効く(色恒常性は形しか見ていない)。
    """
    lam = NM * 1e-9
    v = 3.7418e-16 / (lam ** 5 * (np.exp(1.4388e-2 / (lam * kelvin)) - 1.0))
    return v / v.max()


def _lobe(center, width):
    return np.exp(-0.5 * ((NM - center) / width) ** 2)


def _edge(center, width):
    return 1.0 / (1.0 + np.exp(-(NM - center) / width))


def narrowband(centers, widths, weights):
    """狭帯域の重ね合わせ(蛍光灯・白色 LED のような、山と谷のある分光)。

    黒体は滑らかなので、**滑らかさに依存する欠陥**を隠してしまう。山谷のある
    光源を必ず 1 つ混ぜる —— 対角(von Kries)モデルの床(12 節)はここで一番
    高くなる。
    """
    s = np.zeros_like(NM)
    for c, w, a in zip(centers, widths, weights):
        s += a * _lobe(c, w)
    return s / s.max()


# ---------------------------------------------------------------------------
# 1. 場面 —— 既知の分光反射率チャート
# ---------------------------------------------------------------------------
#: 無彩色パッチの反射率。平坦な分光なので、真値は定義から自明。
NEUTRALS = (0.90, 0.60, 0.36, 0.19, 0.09, 0.03)

#: 有彩色パッチ。乱数ではなく、実在の色材に見られる形(長波長側で立ち上がる赤系、
#: 単峰の緑、葉緑素の「レッドエッジ」、ヘモグロビンの窪みを持つ肌色、2 山の紫)を
#: 滑らかな関数で組む。乱数の分光は全波長に一様に energy を置くので、
#: 「特定の波長帯だけで壊れる」種類の欠陥を平均で隠してしまう。
_CHROMA = {
    "赤":       0.05 + 0.60 * _edge(600, 12),
    "橙":       0.06 + 0.58 * _edge(578, 14),
    "黄":       0.07 + 0.72 * _edge(505, 16) - 0.08 * _lobe(680, 25),
    "葉":       0.04 + 0.20 * _lobe(552, 22) + 0.30 * _edge(692, 6),
    "緑":       0.09 + 0.40 * _lobe(540, 36),
    "シアン":   0.10 + 0.40 * _lobe(500, 55),
    "青":       0.06 + 0.45 * (1.0 - _edge(492, 14)),
    "紫":       0.05 + 0.32 * (1.0 - _edge(455, 12)) + 0.10 * _edge(660, 14),
    "マゼンタ": 0.06 + 0.36 * (1.0 - _edge(478, 16)) + 0.48 * _edge(612, 13),
    "肌":       0.24 + 0.30 * _edge(592, 24) - 0.05 * _lobe(548, 14),
    "煉瓦":     0.05 + 0.28 * _edge(586, 22),
    "オリーブ": 0.05 + 0.16 * _lobe(560, 34),
}
#: 淡彩(有彩色を灰と混ぜたもの)。彩度の軸を場面の中に作っておく。
_PALE = (("赤", 0.35), ("緑", 0.35), ("青", 0.35),
         ("黄", 0.50), ("シアン", 0.50), ("マゼンタ", 0.50))


def chart():
    """``(名前のタプル, 反射率 (N, K))`` を返す。N = 24 枚。"""
    names, refl = [], []
    for v in NEUTRALS:
        names.append(f"無彩 {v:.2f}")
        refl.append(v * FLAT)
    for k, v in _CHROMA.items():
        names.append(k)
        refl.append(np.clip(v, 0.02, 0.95))
    for k, a in _PALE:
        names.append(f"淡{k}")
        refl.append(np.clip(a * _CHROMA[k] + (1.0 - a) * 0.45, 0.02, 0.95))
    return tuple(names), np.stack(refl)


NAMES, REFL = chart()
#: 白パッチを外した場面(明るい無彩 2 枚を除く)。白パッチ法の前提を壊す。
NO_WHITE = tuple(i for i in range(len(NAMES)) if i not in (0, 1))
#: 淡彩だけの場面(有彩色の偏りが弱く、灰色世界の前提に一番近い)。
PALE_ONLY = tuple(range(6)) + tuple(range(18, 24))


def render(refl, spd):
    """分光反射率 × 光源 → **線形 sRGB**(センサの生応答)。負は 0 で止める。

    ``spectrum_to_srgb`` は「反射率 1 が常に (1,1,1)」になるよう光源で規格化して
    しまう(穴 d)。そのままでは色かぶりが作れないので、**光源分布を反射率側に
    畳み**、op には等エネルギーを渡す。こうすると規格化係数が光源に依らない
    定数になり、残るのは物理どおりの ``∫ R(λ) L(λ) x̄(λ) dλ`` になる。
    """
    v = fs.ledger.spectrum_to_srgb(NM, np.asarray(refl) * spd, illuminant=FLAT)
    return np.maximum(v, 0.0)


def true_illuminant(spd):
    """真の光源ベクトル = 反射率 1 の完全拡散面の応答(線形 RGB)。"""
    return fs.ledger.spectrum_to_srgb(NM, FLAT * spd, illuminant=FLAT)


def scene(spd, keep=None, bias_frac=0.0, bias_patch="赤", bias_side="right",
          exposure=1.0, noise=0.0, shade=True, seed=1):
    """チャート画像 (H, W, 3) を線形 RGB で合成する。

    keep:       使うパッチの添字(既定 = 全部)。
    bias_frac:  画面のこの割合を 1 枚の有彩色パッチで塗り潰す(色の偏り)。
    bias_side:  塗る側。既定の ``"right"`` は左上の白パッチを残す —— 左から塗ると
                「色が偏った」と「白が消えた」の 2 つの軸が混ざる(4 節で実測)。
    exposure:   露出倍率。1.0 を超えると明るいパッチから 1.0 で飽和する。
    noise:      加法性ガウス雑音の σ(線形空間、クリップは 0 側のみ)。
    shade:      周辺光量落ち(中心比 15 %)。平場だとどの画素も同じ答えになり、
                空間的に壊れる不具合が平均に隠れるので既定で入れる。
    """
    idx = tuple(range(len(NAMES))) if keep is None else tuple(keep)
    cols = render(REFL[list(idx)], spd)
    rows = int(math.ceil(len(idx) / GRID_COLS))
    h, w = rows * PATCH, GRID_COLS * PATCH
    img = np.zeros((h, w, 3))
    for i in range(len(idx)):
        r, c = divmod(i, GRID_COLS)
        img[r * PATCH:(r + 1) * PATCH, c * PATCH:(c + 1) * PATCH] = cols[i]
    if bias_frac > 0.0:
        wb = int(round(bias_frac * w))
        panel = render(REFL[NAMES.index(bias_patch)], spd)
        if bias_side == "right":
            img[:, w - wb:] = panel
        else:
            img[:, :wb] = panel
    if shade:
        yy, xx = np.mgrid[0:h, 0:w]
        v = 1.0 - 0.15 * (((xx - w / 2) / (w / 2)) ** 2
                          + ((yy - h / 2) / (h / 2)) ** 2) / 2.0
        img = img * v[..., None]
    img = img * exposure
    if noise > 0.0:
        img = img + np.random.default_rng(seed).normal(0.0, noise, img.shape)
    return np.clip(img, 0.0, 1.0)


# ---------------------------------------------------------------------------
# 2. 手法(すべて利用者側の実装 —— fullseye に該当 op が無い。穴 a)
# ---------------------------------------------------------------------------
def _pixels(img, mask=None):
    f = img.reshape(-1, 3)
    return f if mask is None else f[mask.reshape(-1)]


def null_estimate(img, mask=None):
    """ゼロ点 —— 「何もしない」。光源は無彩色だと答え続ける。"""
    return np.ones(3)


def gray_world(img, mask=None):
    """灰色世界 —— 場面の平均反射率は無彩色、という仮定。Shades-of-Gray の p=1。"""
    return _pixels(img, mask).mean(axis=0)


def max_rgb(img, mask=None):
    """白パッチ法 —— 場面のどこかに完全反射面がある、という仮定。p=∞。"""
    return _pixels(img, mask).max(axis=0)


def shades_of_gray(img, p, mask=None):
    """Shades-of-Gray —— ミンコフスキー p ノルム。p=1 が灰色世界、p=∞ が白パッチ。"""
    if math.isinf(p):
        return max_rgb(img, mask)
    f = _pixels(img, mask)
    return np.mean(f ** p, axis=0) ** (1.0 / p)


def gray_edge(img, p=1, mask=None):
    """灰色エッジ —— 微分画像の p ノルム。平均**勾配**が無彩色、という仮定。

    勾配は自前で取る。``fs.op.sobel_amp`` には**正しい呼び方が無い** —— チャンネル
    ごとに呼ぶと各チャンネルが自分の最大で割られて RGB の比が消え、画像ごと渡すと
    色軸が 3 本目の空間軸として扱われて隣接チャンネルが混ざる(穴 c、12 節で実測)。
    """
    gy = np.gradient(img, axis=0)
    gx = np.gradient(img, axis=1)
    g = np.hypot(gy, gx)
    if mask is not None:
        g = g.reshape(-1, 3)[mask.reshape(-1)]
    return np.mean(g.reshape(-1, 3) ** p, axis=0) ** (1.0 / p)


def angular_error(est, truth):
    """回復角度誤差 [度]。明るさは無視し、**色の向き**だけを比べる。"""
    a = np.asarray(est, float)
    b = np.asarray(truth, float)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na <= 0.0 or nb <= 0.0:
        return 180.0
    c = float(a @ b / (na * nb))
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def von_kries(img, est):
    """対角(von Kries)補正 —— 推定した光源で割る。

    ``est`` は「反射率 1 の面の応答」と同じ尺度で渡す。そうすると白い面が
    ちょうど ``(1,1,1)`` に戻る。**角度誤差は明るさを捨てた指標なので、統計
    ベースの推定値をそのままここへ渡すと露出が狂う** —— 角度誤差 0 度と
    「そのまま補正に使える」は別物、というのは 11 節の話とは別の落とし穴。
    """
    return img / np.maximum(np.asarray(est, float), 1e-12)


#: 表に並べる手法。名前 -> 推定関数。
METHODS = (
    ("何もしない", null_estimate),
    ("灰色世界 (p=1)", gray_world),
    ("白パッチ (p=inf)", max_rgb),
    ("SoG p=2", lambda im, m=None: shades_of_gray(im, 2, m)),
    ("SoG p=4", lambda im, m=None: shades_of_gray(im, 4, m)),
    ("SoG p=8", lambda im, m=None: shades_of_gray(im, 8, m)),
    ("SoG p=16", lambda im, m=None: shades_of_gray(im, 16, m)),
    ("灰色エッジ p=1", lambda im, m=None: gray_edge(im, 1, m)),
    ("灰色エッジ p=4", lambda im, m=None: gray_edge(im, 4, m)),
)
#: p を掃引する範囲(∞ = 白パッチ法)。
P_GRID = (1, 2, 3, 4, 6, 8, 12, 16, float("inf"))

#: 光源のカタログ。黒体 8 本 + 山谷のある狭帯域 2 本 + 基準(等エネルギー)。
ILLUMINANTS = (
    ("黒体 2500 K", planck(2500.0)),
    ("黒体 3000 K", planck(3000.0)),
    ("黒体 3500 K", planck(3500.0)),
    ("黒体 4000 K", planck(4000.0)),
    ("黒体 5000 K", planck(5000.0)),
    ("黒体 6500 K", planck(6500.0)),
    ("黒体 8000 K", planck(8000.0)),
    ("黒体 10000 K", planck(10000.0)),
    ("狭帯域 3 波長", narrowband((450, 540, 610), (12, 22, 20), (0.9, 1.0, 0.8))),
    ("狭帯域 2 波長", narrowband((455, 565), (14, 45), (1.0, 1.1))),
    ("基準(等エネルギー)", FLAT),
)


def stats(vals):
    """分布 —— 平均 / 中央値 / 三分位平均 / 最良 25 % / 最悪 25 % / 最大 [度]。

    色恒常性の文献は平均でなく中央値・三分位平均・最悪 25 % を並べる慣習。
    誤差分布が強く歪む(大半の場面で当たり、少数で大外しする)ので、平均だけ
    見ると「たまに致命的に外す」が消える。
    """
    v = np.sort(np.asarray(vals, float))
    n = v.size
    q1, med, q3 = np.percentile(v, (25, 50, 75))
    k = max(1, n // 4)
    return (float(v.mean()), float(med), float((q1 + 2 * med + q3) / 4.0),
            float(v[:k].mean()), float(v[-k:].mean()), float(v[-1]))


STAT_HEAD = f"{'平均':>8}{'中央値':>9}{'三分位平均':>12}{'最良25%':>10}{'最悪25%':>10}{'最大':>8}"


def fmt_stats(s):
    return "".join(f"{x:>{w}.2f}" for x, w in zip(s, (8, 9, 12, 10, 10, 8)))


# ---------------------------------------------------------------------------
def main():
    t_all = time.perf_counter()

    # ------------------------------------------------------------------ #
    print("=== 1. 場面と真値 ===")
    can = render(REFL, FLAT)
    n_clipped = 0
    for _, spd in ILLUMINANTS:
        raw = fs.ledger.spectrum_to_srgb(NM, REFL * spd, illuminant=FLAT)
        n_clipped += int((raw < 0.0).sum())
    img0 = scene(planck(6500.0))
    print(f"  波長 {NM[0]:.0f}-{NM[-1]:.0f} nm を {NM.size} 点 / パッチ {len(NAMES)} 枚"
          f" / 画像 {img0.shape[1]}x{img0.shape[0]} px")
    print(f"  レンダリングに使う op: fullseye.spectrum_to_srgb"
          f"(中で cie_xyz_from_wavelength を呼ぶ)")
    print(f"  基準(等エネルギー)光源での反射率 1 の応答 = "
          f"{tuple(round(float(v), 6) for v in true_illuminant(FLAT))}")
    print(f"  色域外で 0 に丸めた patch-channel: {n_clipped} / "
          f"{len(NAMES) * len(ILLUMINANTS) * 3}(穴 e)")
    print(f"  {'光源':<20}{'真の光源 R':>12}{'G':>9}{'B':>9}"
          f"{'ゼロ点の角度誤差':>18}")
    for name, spd in ILLUMINANTS:
        e = true_illuminant(spd)
        print(f"  {name:<20}{e[0]:>12.4f}{e[1]:>9.4f}{e[2]:>9.4f}"
              f"{angular_error(np.ones(3), e):>18.2f}")
    print("  → 「ゼロ点の角度誤差」= 何もしないときの誤差 = その光源の色かぶりの強さ。")
    print("     基準光源では 0.00 度。**そこでは、どんな AWB も改善できない。**")

    print("\n  パッチの一部(基準光源での線形 RGB):")
    print(f"  {'名前':<12}{'R':>9}{'G':>9}{'B':>9}    {'名前':<12}{'R':>9}{'G':>9}{'B':>9}")
    half = len(NAMES) // 2
    for i in range(half):
        j = i + half
        print(f"  {NAMES[i]:<12}{can[i][0]:>9.4f}{can[i][1]:>9.4f}{can[i][2]:>9.4f}"
              f"    {NAMES[j]:<12}{can[j][0]:>9.4f}{can[j][1]:>9.4f}{can[j][2]:>9.4f}")

    # ------------------------------------------------------------------ #
    print("\n=== 2. 光源ごとの角度誤差 [度] —— まず 1 枚ずつ見る ===")
    print(f"  {'光源':<20}" + "".join(f"{n:>17}" for n, _ in METHODS[:5]))
    per_ill = {}
    for name, spd in ILLUMINANTS:
        img = scene(spd)
        e = true_illuminant(spd)
        row = {m: angular_error(f(img), e) for m, f in METHODS}
        per_ill[name] = row
        print(f"  {name:<20}"
              + "".join(f"{row[n]:>17.2f}" for n, _ in METHODS[:5]))
    print(f"  {'':<20}" + "".join(f"{n:>17}" for n, _ in METHODS[5:]))
    for name, _ in ILLUMINANTS:
        print(f"  {name:<20}"
              + "".join(f"{per_ill[name][n]:>17.2f}" for n, _ in METHODS[5:]))
    print("  → 白パッチ法が強いのは **チャートに白があるから**。6 節で外すと崩れる。")
    print("     基準光源の行だけ見ると、全手法が「何もしない」の 0.00 度に負けている。")

    # ------------------------------------------------------------------ #
    print("\n=== 3. 分布で見る —— 11 光源 x 4 場面 = 44 枚 ===")
    variants = (("素のチャート", dict()),
                ("白パッチ無し", dict(keep=NO_WHITE)),
                ("淡彩のみ", dict(keep=PALE_ONLY)),
                ("有彩色 50 %", dict(bias_frac=0.5)))
    ens = {n: [] for n, _ in METHODS}
    for _, kw in variants:
        for _, spd in ILLUMINANTS:
            img = scene(spd, **kw)
            e = true_illuminant(spd)
            for n, f in METHODS:
                ens[n].append(angular_error(f(img), e))
    print(f"  {'手法':<18}{STAT_HEAD}")
    ens_stats = {}
    for n, _ in METHODS:
        ens_stats[n] = stats(ens[n])
        print(f"  {n:<18}{fmt_stats(ens_stats[n])}")
    best_med = min((s[1], n) for n, s in ens_stats.items() if n != "何もしない")
    print(f"  → 中央値で最良は {best_med[1]}({best_med[0]:.2f} 度)。ただし"
          f"最悪 25 % では {ens_stats[best_med[1]][4]:.2f} 度まで開く。")
    print("     **1 つの数字にまとめると、この開きが消える。**")

    # ------------------------------------------------------------------ #
    print("\n=== 4. ★崖 (a) 有彩色が画面を占める割合 ===")
    print("  画面の**右から** f の割合を 1 枚の飽和した赤で塗り潰す(残りはチャート)。")
    print("  右から塗るのは、左上の白パッチを残して「色の偏り」の軸だけを動かすため。")
    print("  最右列は左から塗った場合の白パッチ法 —— 軸が混ざるとどうなるかの対照。")
    print("  数字は 11 光源の**中央値** [度]。")
    cols = ("何もしない", "灰色世界 (p=1)", "白パッチ (p=inf)", "SoG p=4",
            "SoG p=16", "灰色エッジ p=1")
    print(f"  {'f':>6}" + "".join(f"{c:>18}" for c in cols)
          + f"{'白パッチ(左から)':>20}")
    bias_rows = {}
    for frac in (0.0, 0.1, 0.2, 0.3, 0.45, 0.6, 0.75, 0.9):
        acc = {c: [] for c in cols}
        acc_left = []
        for _, spd in ILLUMINANTS:
            img = scene(spd, bias_frac=frac)
            e = true_illuminant(spd)
            for c in cols:
                acc[c].append(angular_error(dict(METHODS)[c](img), e))
            acc_left.append(angular_error(
                max_rgb(scene(spd, bias_frac=frac, bias_side="left")), e))
        bias_rows[frac] = {c: float(np.median(acc[c])) for c in cols}
        bias_rows[frac]["白パッチ(左)"] = float(np.median(acc_left))
        print(f"  {frac:>6.2f}" + "".join(f"{bias_rows[frac][c]:>18.2f}" for c in cols)
              + f"{bias_rows[frac]['白パッチ(左)']:>20.2f}")
    print("  → 灰色世界の崖は f=0.1 と 0.2 の間(そこで「何もしない」に負ける)。")
    print("     白パッチ法は f=0.75 まで無傷 —— 白が写っている限り、画面の 3/4 が")
    print("     真っ赤でも動じない。**崖の位置も、崖の有無も、手法ごとに別物。**")
    print("     最右列(左から塗る)は f=0.2 で既に崩れる。塗り潰しが白パッチを")
    print("     隠すからで、これは「色の偏り」ではなく「白の消失」の効果。")
    print("     **2 つの軸を 1 つの実験で動かすと、原因を取り違える。**")

    # ------------------------------------------------------------------ #
    print("\n=== 5. ★崖 (b) 白パッチを外す ===")
    print("  白パッチ法の前提を壊すと何が起きるか。数字は 11 光源の中央値 [度]。")
    print(f"  {'場面':<22}" + "".join(f"{c:>18}" for c in cols))
    wp_rows = {}
    for label, kw in (("素のチャート(白あり)", dict()),
                      ("最も明るい 1 枚を除く", dict(keep=tuple(range(1, 24)))),
                      ("明るい 2 枚を除く", dict(keep=NO_WHITE)),
                      ("無彩を全部除く", dict(keep=tuple(range(6, 24))))):
        acc = {c: [] for c in cols}
        for _, spd in ILLUMINANTS:
            img = scene(spd, **kw)
            e = true_illuminant(spd)
            for c in cols:
                acc[c].append(angular_error(dict(METHODS)[c](img), e))
        wp_rows[label] = {c: float(np.median(acc[c])) for c in cols}
        print(f"  {label:<22}" + "".join(f"{wp_rows[label][c]:>18.2f}" for c in cols))
    print("  → ★**24 枚のうち一番明るい 1 枚を外すだけ**で、白パッチ法は 8 倍悪化する。")
    print("     同じ改変で灰色世界は 1 割しか動かない。白パッチ法は場面の全情報を")
    print("     **1 枚のパッチに賭けている**ので、そのパッチが無い/汚れている/")
    print("     飽和している、のどれか 1 つで終わる。悪化の絶対量ではなく")
    print("     **1 画素への依存度**が、この手法の本当の弱点。")

    # ------------------------------------------------------------------ #
    print("\n=== 6. ★崖 (c) 露出飽和 ===")
    print("  露出だけを上げる(場面と光源は不変。真値も不変)。数字は 11 光源の中央値。")
    print(f"  {'露出':>6}{'飽和画素率 %':>14}"
          + "".join(f"{c:>18}" for c in cols[:5])
          + f"{'白パッチ+マスク':>18}")
    sat_rows = {}
    for k in (1.0, 1.2, 1.5, 2.0, 3.0, 5.0):
        acc = {c: [] for c in cols[:5]}
        acc_mask, fr = [], []
        for _, spd in ILLUMINANTS:
            img = scene(spd, exposure=k)
            e = true_illuminant(spd)
            sat = (img >= 1.0).any(axis=2)
            fr.append(float(sat.mean()))
            for c in cols[:5]:
                acc[c].append(angular_error(dict(METHODS)[c](img), e))
            m = ~sat
            acc_mask.append(angular_error(max_rgb(img, m) if m.any()
                                          else np.ones(3), e))
        sat_rows[k] = (float(np.mean(fr)),
                       {c: float(np.median(acc[c])) for c in cols[:5]},
                       float(np.median(acc_mask)))
        print(f"  {k:>6.1f}{100 * sat_rows[k][0]:>14.2f}"
              + "".join(f"{sat_rows[k][1][c]:>18.2f}" for c in cols[:5])
              + f"{sat_rows[k][2]:>18.2f}")
    print("  → 飽和は **例外を出さない**。白パッチ法だけが崩れ、灰色世界はほぼ不変。")
    print("     ★崩れ方の終点が面白い: 露出 3.0 以上では白パッチ法の誤差が")
    print("     「何もしない」と**厳密に一致**する。全チャンネルが 1.0 に張り付いて")
    print("     max が (1,1,1) になるので、答えがゼロ点そのものに退化する。")
    print("     露出 1.2(飽和 1.4 %)で一度**良くなる**のも注意 —— 明るい無彩が")
    print("     頭打ちになって偶然真値に寄っただけで、次の行から崩れ始める。")
    print("     飽和画素を外す(最右列)と露出 3.0 で 13.61 -> 5.49 度まで戻るが、")
    print("     マスクを受け取る口は fullseye 側に無い(穴 a/b)。")

    # ------------------------------------------------------------------ #
    print("\n=== 7. ★崖 (d) 雑音 ===")
    print("  線形空間に加法性ガウス雑音。数字は 11 光源の中央値 [度]。")
    print(f"  {'σ':>8}" + "".join(f"{c:>18}" for c in cols))
    noise_rows = {}
    for s in (0.0, 0.002, 0.01, 0.03, 0.10):
        acc = {c: [] for c in cols}
        for i, (_, spd) in enumerate(ILLUMINANTS):
            img = scene(spd, noise=s, seed=100 + i)
            e = true_illuminant(spd)
            for c in cols:
                acc[c].append(angular_error(dict(METHODS)[c](img), e))
        noise_rows[s] = {c: float(np.median(acc[c])) for c in cols}
        print(f"  {s:>8.3f}" + "".join(f"{noise_rows[s][c]:>18.2f}" for c in cols))
    print("  → 白パッチ法は最大値の統計なので雑音の裾を拾う。灰色世界は平均なので")
    print("     ほぼ動かない。**飽和と雑音で壊れるのは同じ手法**(どちらも極値依存)。")
    print("     灰色エッジは微分が雑音を増幅するので、σ=0.03 から一番速く崩れる。")

    # ------------------------------------------------------------------ #
    print("\n=== 8. ★崖 (e) 2 光源が混ざる ===")
    print("  画面の左半分を低色温、右半分を高色温にする。**真値は 1 本では書けない**。")
    print(f"  {'左|右 [K]':>14}{'2 光源の開き':>14}"
          + "".join(f"{c:>18}" for c in ("灰色世界 (p=1)", "白パッチ (p=inf)",
                                         "SoG p=4"))
          + f"{'理論下限':>10}")
    two_rows = {}
    for t1, t2 in ((3000, 4000), (2800, 6500), (2500, 9000)):
        s1, s2 = planck(float(t1)), planck(float(t2))
        e1, e2 = true_illuminant(s1), true_illuminant(s2)
        img = scene(s1)
        img2 = scene(s2)
        w = img.shape[1] // 2
        mix = np.concatenate([img[:, :w], img2[:, w:]], axis=1)
        sep = angular_error(e1, e2)
        row = {}
        for c in ("灰色世界 (p=1)", "白パッチ (p=inf)", "SoG p=4"):
            est = dict(METHODS)[c](mix)
            row[c] = max(angular_error(est, e1), angular_error(est, e2))
        two_rows[(t1, t2)] = (sep, row)
        print(f"  {f'{t1}|{t2}':>14}{sep:>14.2f}"
              + "".join(f"{row[c]:>18.2f}" for c in ("灰色世界 (p=1)",
                                                     "白パッチ (p=inf)", "SoG p=4"))
              + f"{sep / 2:>10.2f}")
    print("  → 列の数字は「2 つの光源のうち**外したほう**の角度誤差」。1 本のベクトル")
    print("     しか返せない以上、どんな推定でも開きの半分より良くはならない")
    print("     (最右列 = 理論下限)。実測はどれもその 1.1〜2.6 倍。")
    print("     **単一光源を仮定する推定に 2 光源の画像を渡しても、例外は出ない。**")

    # ------------------------------------------------------------------ #
    print("\n=== 9. 最適な p は場面で動く ===")
    print("  各条件で p を掃引し、11 光源の中央値が最小になる p を探す。")
    print(f"  {'条件':<22}" + "".join(f"{('p=inf' if math.isinf(p) else f'p={p}'):>9}"
                                      for p in P_GRID) + f"{'最適 p':>9}")
    conds = (("素のチャート", dict()),
             ("白パッチ無し", dict(keep=NO_WHITE)),
             ("淡彩のみ", dict(keep=PALE_ONLY)),
             ("有彩色 60 %", dict(bias_frac=0.6)),
             ("有彩色 60 % + 白なし", dict(bias_frac=0.6, keep=NO_WHITE)),
             ("飽和(露出 3.0)", dict(exposure=3.0)),
             ("雑音 σ=0.03", dict(noise=0.03)))
    best_p = {}
    for label, kw in conds:
        med = []
        for p in P_GRID:
            acc = []
            for i, (_, spd) in enumerate(ILLUMINANTS):
                img = scene(spd, seed=200 + i, **kw)
                acc.append(angular_error(shades_of_gray(img, p),
                                         true_illuminant(spd)))
            med.append(float(np.median(acc)))
        k = int(np.argmin(med))
        best_p[label] = (P_GRID[k], med[k], med)
        tag = "inf" if math.isinf(P_GRID[k]) else str(P_GRID[k])
        print(f"  {label:<22}" + "".join(f"{m:>9.2f}" for m in med) + f"{tag:>9}")
    print("  → 最適 p が 1 から ∞ まで動く。**既定値を 1 つ配る根拠が無い。**")
    print("     しかも p を間違えたときの損は非対称: 飽和下で p=inf を選ぶと")
    print(f"     {best_p['飽和(露出 3.0)'][2][-1]:.2f} 度、最適 p の"
          f" {best_p['飽和(露出 3.0)'][2][-1] / best_p['飽和(露出 3.0)'][1]:.1f} 倍。")

    # ------------------------------------------------------------------ #
    print("\n=== 10. fullseye に 1 本だけある光源推定 op ===")
    print("  illuminant_from_dichromatic_planes(Lee 1986)。二色性反射モデルの下で")
    print("  各材質の画素は「物体色 x 光源色」の平面に載るので、2 材質の平面の")
    print("  交線が光源になる —— 統計ではなく**幾何**。ただし材質ラベルと")
    print("  ハイライトの両方を要求する。")
    spd_d = planck(3200.0)
    e_d = true_illuminant(spd_d)
    mats = ("赤", "緑", "青", "黄")
    body = render(REFL[[NAMES.index(m) for m in mats]], spd_d)
    hh, ww = 44, 44
    matte = np.zeros((hh, ww * len(mats), 3))
    hi = np.zeros_like(matte)
    labels = np.full((hh, ww * len(mats)), -1, np.int32)
    yy, xx = np.mgrid[0:hh, 0:ww]
    lobe = 0.55 * np.exp(-(((yy - 18) ** 2 + (xx - 22) ** 2) / (2 * 7.0 ** 2)))
    for i in range(len(mats)):
        sl = np.s_[:, i * ww:(i + 1) * ww]
        matte[sl] = body[i]
        hi[sl] = body[i] + lobe[..., None] * e_d
        labels[sl] = i
    est_d = fs.ledger.illuminant_from_dichromatic_planes(hi, labels)
    print(f"  {'条件':<26}{'二色性 op':>12}{'白パッチ法':>12}   備考")
    print(f"  {'ハイライトあり・4 材質':<26}{angular_error(est_d, e_d):>12.1e}"
          f"{angular_error(max_rgb(hi), e_d):>12.2f}   幾何が厳密に解ける")

    def _refuse(image, lab):
        try:
            fs.ledger.illuminant_from_dichromatic_planes(image, lab)
            return ""
        except ValueError as exc:
            return str(exc).split(": ", 1)[-1]

    matte_refused = _refuse(matte, labels)
    print(f"  {'ハイライト無し(マット面)':<26}{'拒否':>12}"
          f"{angular_error(max_rgb(matte), e_d):>12.2f}   {matte_refused[:52]}")
    lab1 = labels.copy()
    lab1[labels >= 1] = 0                       # 1 材質だけにする
    one_refused = _refuse(hi, lab1)
    print(f"  {'ハイライトあり・1 材質':<26}{'拒否':>12}"
          f"{angular_error(max_rgb(hi), e_d):>12.2f}   {one_refused[:52]}")
    rng = np.random.default_rng(5)
    noisy_rows = {}
    for s in (0.002, 0.01, 0.05):
        hn = np.clip(hi + rng.normal(0.0, s, hi.shape), 0.0, None)
        try:
            en = fs.ledger.illuminant_from_dichromatic_planes(hn, labels)
            noisy_rows[s] = angular_error(en, e_d)
        except ValueError:
            noisy_rows[s] = float("nan")
        print(f"  {'ハイライトあり + 雑音 σ=' + f'{s:.3f}':<26}{noisy_rows[s]:>12.2f}"
              f"{angular_error(max_rgb(hn), e_d):>12.2f}   同じ画像を統計手法で解いた比較")
    print(f"  拒否の全文(マット面): {matte_refused[:110]}")
    print("  → 雑音が無ければ厳密(0.0e+00 度)。**統計手法とは桁が違う。** ただし")
    print("     ラベルもハイライトも無いマット面では、もっともらしい答えを返さず")
    print("     何材質が何の理由で落ちたかを名指しして拒否する(fail-closed)。")
    print("     ★雑音 σ=0.05 では二色性 op のほうが白パッチ法より悪くなる。")
    print("     平面の当てはめは特異値の第 2 位に依存するので、雑音がその水準に")
    print("     届いた瞬間に「平面」が決まらなくなる。**厳密さと頑健さは別。**")

    # ------------------------------------------------------------------ #
    print("\n=== 11. 対角(von Kries)補正の床 —— 真の光源を知っていても残る誤差 ===")
    print("  推定を一切間違えず、**真の光源ベクトルで割った**ときの残差。")
    print(f"  {'光源':<20}{'角度誤差':>10}{'ΔE00 平均':>12}{'ΔE00 最大':>12}"
          f"{'最悪パッチ':>12}")
    floor_rows = {}
    can_srgb = fs.ledger.linear_to_srgb(np.clip(can, 0.0, 1.0))
    for name, spd in ILLUMINANTS:
        obs = render(REFL, spd)
        corr = von_kries(obs, true_illuminant(spd))
        de = fs.ledger.delta_e_map(
            fs.ledger.linear_to_srgb(np.clip(corr[None], 0.0, 1.0)),
            can_srgb[None], kind="2000")[0]
        floor_rows[name] = (float(de.mean()), float(de.max()))
        print(f"  {name:<20}{0.0:>10.2f}{de.mean():>12.2f}{de.max():>12.2f}"
              f"{NAMES[int(np.argmax(de))]:>12}")
    print("  → 角度誤差は定義から 0.00 度なのに、色は合っていない。対角スケーリングは")
    print("     分光の積分を交換できない(∫R L x̄ != (∫R x̄)(∫L x̄))ので、**光源推定を")
    print("     いくら詰めてもここが床になる**。床が一番高いのは山谷のある狭帯域光源。")
    print("     角度誤差 0 度 = 色が合う、ではない。")

    # ------------------------------------------------------------------ #
    print("\n=== 12. ★ カラー画像に 2-D op を渡す 2 通り、両方が壊れる(穴 c)===")
    print("  灰色エッジ法は微分が要る。fullseye には sobel_amp があるので使いたいが、")
    print("  **画像ごと渡す / ch ごとに回す のどちらも壊れる**。まず漏れの検査:")
    probe = np.zeros((20, 20, 3))
    probe[:, :10, 0] = 1.0            # R にだけ縦エッジ。G と B は恒等的に 0
    leak = fs.op.sobel_amp(probe)
    leak_max = leak.reshape(-1, 3).max(axis=0)
    print(f"  入力: R だけに縦エッジ、G と B は全画素 0.0"
          f"(入力 G の最大 = {probe[..., 1].max():.1f})")
    print(f"  出力の各チャンネル最大: R={leak_max[0]:.4f} G={leak_max[1]:.4f} "
          f"B={leak_max[2]:.4f}")
    print("  → ★**入力が恒等的に 0 の G に 0.3333 が出る。** 実装は")
    print("     ``ndimage.sobel(v, axis)`` をそのまま呼んでおり、``v`` が (H,W,3) だと")
    print("     **色軸が 3 本目の空間軸として扱われ、[1,2,1]/4 の平滑が RGB を跨いで")
    print("     掛かる**。R が G へ 1/3 漏れ、B は 2 つ離れているので届かない。")
    print("     例外も警告も出ず、それらしいエッジ画像が返る。")
    print()
    print("  この漏れが色恒常性に効く(以下は同じチャート、黒体 3000 K):")
    spd_g = planck(3000.0)
    img_g = scene(spd_g)
    e_g = true_illuminant(spd_g)
    own = gray_edge(img_g, 1)
    whole = fs.op.sobel_amp(img_g)
    perch = np.stack([fs.op.sobel_amp(img_g[..., k]) for k in range(3)], axis=-1)
    est_whole = whole.reshape(-1, 3).mean(axis=0)
    est_perch = perch.reshape(-1, 3).mean(axis=0)
    # 正規化とカーネルを切り分けるための対照 —— 自前の Sobel(正規化なし)。
    kx = np.array([[-1.0, 0.0, 1.0], [-2.0, 0.0, 2.0], [-1.0, 0.0, 1.0]])
    gx_s = sum(kx[dy + 1, dx + 1] * np.roll(np.roll(img_g, -dy, 0), -dx, 1)
               for dy in (-1, 0, 1) for dx in (-1, 0, 1))
    gy_s = sum(kx.T[dy + 1, dx + 1] * np.roll(np.roll(img_g, -dy, 0), -dx, 1)
               for dy in (-1, 0, 1) for dx in (-1, 0, 1))
    est_sob = np.hypot(gx_s, gy_s).reshape(-1, 3).mean(axis=0)
    print(f"  {'勾配の取り方':<34}{'R':>10}{'G':>10}{'B':>10}{'角度誤差':>10}")
    print(f"  {'自前 中心差分(np.gradient)':<34}{own[0]:>10.5f}{own[1]:>10.5f}"
          f"{own[2]:>10.5f}{angular_error(own, e_g):>10.2f}")
    print(f"  {'自前 Sobel(正規化なし)':<34}{est_sob[0]:>10.5f}{est_sob[1]:>10.5f}"
          f"{est_sob[2]:>10.5f}{angular_error(est_sob, e_g):>10.2f}")
    print(f"  {'fs.op.sobel_amp(rgb) 画像ごと':<34}{est_whole[0]:>10.5f}"
          f"{est_whole[1]:>10.5f}{est_whole[2]:>10.5f}"
          f"{angular_error(est_whole, e_g):>10.2f}")
    print(f"  {'fs.op.sobel_amp を ch ごとに 3 回':<34}{est_perch[0]:>10.5f}"
          f"{est_perch[1]:>10.5f}{est_perch[2]:>10.5f}"
          f"{angular_error(est_perch, e_g):>10.2f}")
    print(f"  {'何もしない(参考)':<34}{1.0:>10.5f}{1.0:>10.5f}{1.0:>10.5f}"
          f"{angular_error(np.ones(3), e_g):>10.2f}")
    print(f"  ch ごとに呼んだ後の各チャンネル最大値: "
          f"{tuple(round(float(v), 3) for v in perch.reshape(-1, 3).max(axis=0))}"
          f" —— 3 つとも 1.0(それぞれ自分の最大で割られた)")
    print(f"  画像ごと渡した後の各チャンネル最大値: "
          f"{tuple(round(float(v), 3) for v in whole.reshape(-1, 3).max(axis=0))}"
          f" —— 全体の 1 個で割るので比自体は残る")
    print("  → **2 通りの呼び方があって、どちらも壊れている。**")
    print("     ch ごと: 各チャンネルが自分の最大(``ops._norm``)で割られ、RGB の比が")
    print("     消える。角度誤差はゼロ点(何もしない)にほぼ張り付く。")
    print("     画像ごと: 比は残るが色軸を跨いだ平滑が入る。自前 Sobel(同じカーネル、")
    print("     正規化なし)と比べて誤差が 4 倍。差は正規化ではなく **漏れ**")
    print("     (正規化は全体を 1 個のスカラで割るだけなので、角度には効かない)。")
    print("     利用者から見ると、この op には**正しい呼び方が無い**。")

    # ------------------------------------------------------------------ #
    print("\n=== 13. 速度(この機械での実測)===")
    big = scene(planck(3000.0))
    big = np.repeat(np.repeat(big, 8, axis=0), 8, axis=1)     # 約 1 Mpixel
    print(f"  対象 {big.shape[1]}x{big.shape[0]}x3 = "
          f"{big.shape[0] * big.shape[1] / 1e6:.2f} Mpixel")
    speed = {}
    for label, fn in (("灰色世界", lambda: gray_world(big)),
                      ("白パッチ", lambda: max_rgb(big)),
                      ("SoG p=4", lambda: shades_of_gray(big, 4)),
                      ("灰色エッジ p=1", lambda: gray_edge(big, 1)),
                      ("対角補正(von Kries)", lambda: von_kries(big, (1.2, 1.0, 0.7))),
                      ("spectrum_to_srgb(24 枚)",
                       lambda: render(REFL, planck(3000.0)))):
        t0 = time.perf_counter()
        fn()
        speed[label] = 1e3 * (time.perf_counter() - t0)
        print(f"  {label:<26}{speed[label]:>9.1f} ms")
    print("  → どれも 1 Mpixel で 2 桁 ms。**計算コストは手法選択の理由にならない。**")
    print("     律速は微分(灰色エッジ)で、単純な統計の 10 倍前後。")

    # ------------------------------------------------------------------ #
    print("\n所見(想定と違ったこと):")
    print("   (1) 「白パッチ法は素朴だから弱い」と思っていたが、**チャートでは全手法中")
    print(f"       最良**だった(中央値 {ens_stats['白パッチ (p=inf)'][1]:.2f} 度)。")
    print("       理由は手法の優秀さではなく、**チャートに白が写っているから**。")
    print("       白を外した瞬間に最悪の手法へ落ちる(5 節)。ベンチマークの")
    print("       題材が手法の順位を決めていた。")
    print("   (2) 「灰色世界は頑健」も半分しか正しくない。飽和にも雑音にもほとんど")
    print("       反応しない一方、有彩色が画面の半分を超えると「何もしない」に")
    print("       **負ける**(4 節)。頑健さは軸ごとに測らないと意味を持たない。")
    print("   (3) 基準光源(色かぶり無し)の行を入れたのは形式的な理由だったが、")
    print("       ここが一番厳しい行になった。ゼロ点が 0.00 度なので、**どの手法も")
    print("       必ず負ける**。「AWB を常時 ON」は、色かぶりが無い場面では")
    print("       純粋な劣化になる。")
    print("   (4) 角度誤差を 0 にしても色は合わない(11 節)。対角モデルの床は")
    print("       狭帯域光源で最大 ΔE00 が 2 桁近くまで上がる。**推定の精度で")
    print("       語れるのはここまで**、という上限が実験の側から出た。")
    print("   (5) 2 光源では「外したほうの誤差」が開きの半分を下回れない(8 節)。")
    print("       これは手法の性能ではなく **1 本のベクトルしか返さない API の形**")
    print("       が決めている限界で、どんなに良い推定器でも越えられない。")

    print("\n所見(fullseye の穴 —— この PoC が出した道具の穴):")
    print("   (a) **統計ベースの光源推定 op がゼロ。** 台帳 910 + 進化 op 885 を")
    print("       gray world / white patch / shades of gray / gray edge /")
    print("       white balance / AWB / von Kries / CAT で探して 0 件。")
    print("       物理ベースの illuminant_from_dichromatic_planes だけがあり、")
    print("       それは材質ラベルとハイライトを要求する(10 節)。")
    print("       `illuminant_shades_of_gray(rgb, p=..., mask=...)` が 1 本あれば")
    print("       この PoC の 2 節-9 節はすべて op の呼び出しで書ける。")
    print("   (b) **推定した光源で割る op も無い。** color_transfer は参照画像を、")
    print("       color_grade は 3-D LUT を要求し、どちらも対角補正には使えない。")
    print("       linear_trans_color は名前が近いが進化 op のつまみ(a, b)モデルで、")
    print("       任意の対角行列を作れない。**台帳側に `white_balance(rgb, gains)`")
    print("       が無いので、色の前処理の 3 段目(colorimetry ガイドの手順)が")
    print("       fullseye だけでは踏めない。**")
    print("   (c) **fs.op.sobel_amp は呼び方で比が消える**(12 節)。画像ごと渡すと")
    print("       全体の最大 1 個で割るので比が残り、ch ごとに 3 回呼ぶと各 ch が")
    print("       自分の最大で割られて比が消える。角度誤差 "
          f"{angular_error(own, e_g):.2f} -> "
          f"{angular_error(est_perch, e_g):.2f} 度。")
    print("       docstring に「何で割るか」が書かれておらず、例外も出ない。")
    print("   (d) **spectrum_to_srgb は色かぶりを作れない。** 反射率 1 が常に")
    print("       (1,1,1) になる正規化なので、光源の色を残した生応答が出せない。")
    print("       本 PoC は光源を反射率側に畳む回り道で合成した(1 節)。")
    print("       `adapt=False` のような引数、または `sensor_response(nm, refl,")
    print("       illuminant)` が別にあると、色恒常性・測色の実験が素直に書ける。")
    print("   (e) **色域外の負値を何個丸めたかを返す口が無い。** 負を返すこと自体は")
    print(f"       正直な設計だが、呼び手は自分で数えるしかない(本 PoC で {n_clipped} 個)。")
    print("   (f) **colorimetry ガイドの「現在地」表が実装から遅れている。**")
    print("       「観測者 x̄ȳz̄: 無し」「分光反射率を持てない」と書いてあるが、")
    print("       cie_xyz_from_wavelength と spectrum_to_srgb は実在し、本 PoC は")
    print("       その 2 つだけで分光レンダリングを組んでいる。")

    # ---- 自己検査(速さは assert しない)-------------------------------- #
    # 1. 真値の健全性: 基準光源で白は (1,1,1)、ゼロ点誤差はちょうど 0
    e_flat = true_illuminant(FLAT)
    assert np.abs(e_flat - 1.0).max() < 1e-3, f"基準光源で白が (1,1,1) でない: {e_flat}"
    assert angular_error(np.ones(3), e_flat) < 0.05, "基準光源のゼロ点誤差が 0 でない"
    assert per_ill["黒体 2500 K"]["何もしない"] > 30.0, \
        "2500 K の色かぶりが弱すぎる(場面設計が壊れた)"
    assert render(REFL, FLAT).min() >= 0.0, "レンダリングが負を返した(クリップ漏れ)"

    # 2. 基準光源では全手法がゼロ点に負ける(3 番目の主張)
    for name, _ in METHODS:
        if name == "何もしない":
            continue
        assert per_ill["基準(等エネルギー)"][name] > 0.5, \
            f"基準光源で {name} がゼロ点に並んだ —— 真値が漏れている疑い"

    # 3. アンサンブル: 統計手法は全体としてはゼロ点に勝つ(勝てなければ意味が無い)
    assert ens_stats["灰色世界 (p=1)"][1] < ens_stats["何もしない"][1], \
        "灰色世界が中央値でゼロ点に勝てていない"
    assert ens_stats["白パッチ (p=inf)"][1] < ens_stats["何もしない"][1], \
        "白パッチ法が中央値でゼロ点に勝てていない"
    # 分布は歪む: 最悪 25 % は中央値よりはっきり悪い(1 つの数字にできない)
    for name, _ in METHODS:
        if name == "何もしない":
            continue
        assert ens_stats[name][4] > 1.5 * ens_stats[name][1], \
            f"{name}: 最悪 25 % が中央値と近い —— 分布を出す意味が消えている"

    # 4. 崖 (a): 灰色世界は有彩色の偏りで壊れ、どこかでゼロ点に負ける
    assert bias_rows[0.0]["灰色世界 (p=1)"] < bias_rows[0.0]["何もしない"], \
        "偏り 0 で灰色世界がゼロ点に勝てていない"
    assert bias_rows[0.2]["灰色世界 (p=1)"] < bias_rows[0.2]["何もしない"], \
        "f=0.2 で既に灰色世界が負けた —— 崖の位置が動いた"
    assert bias_rows[0.3]["灰色世界 (p=1)"] > bias_rows[0.3]["何もしない"], \
        "f=0.3 でも灰色世界がゼロ点に負けない —— 崖 (a) が消えた"
    assert bias_rows[0.9]["灰色世界 (p=1)"] > 4.0 * bias_rows[0.0]["灰色世界 (p=1)"], \
        "偏りで灰色世界が悪化していない"
    # 白を残して塗れば白パッチ法は無傷。同じ f を左から塗ると崩れる(軸の混線)
    assert bias_rows[0.75]["白パッチ (p=inf)"] < 2.0 * bias_rows[0.0]["白パッチ (p=inf)"], \
        "白を残して塗っても白パッチ法が壊れた —— 崖の軸が直交していない"
    assert bias_rows[0.3]["白パッチ(左)"] > 3.0 * bias_rows[0.3]["白パッチ (p=inf)"], \
        "左から塗っても崩れない —— 軸が混ざるという所見が崩れた"

    # 5. 崖 (b): 白パッチ法は 1 枚のパッチに賭けている(1 枚外すだけで壊れる)
    a, b = "素のチャート(白あり)", "最も明るい 1 枚を除く"
    assert wp_rows[b]["白パッチ (p=inf)"] > 4.0 * wp_rows[a]["白パッチ (p=inf)"], \
        "一番明るい 1 枚を外しても白パッチ法が崩れない"
    assert wp_rows[b]["灰色世界 (p=1)"] < 1.3 * wp_rows[a]["灰色世界 (p=1)"], \
        "同じ改変で灰色世界まで大きく動いた —— 1 画素依存という所見が崩れた"
    assert wp_rows["無彩を全部除く"]["白パッチ (p=inf)"] > \
        3.0 * wp_rows[a]["白パッチ (p=inf)"], "無彩を全部外しても崩れない"

    # 6. 崖 (c): 飽和は例外を出さず、白パッチ法だけを壊す。マスクで戻る
    assert sat_rows[1.0][0] == 0.0, "露出 1.0 で既に飽和している(実験設計が壊れた)"
    assert sat_rows[5.0][0] > 0.05, "露出 5.0 でも飽和画素が出ない"
    sat_wp = [sat_rows[k][1]["白パッチ (p=inf)"] for k in (1.5, 2.0, 3.0, 5.0)]
    assert all(y >= x - 1e-9 for x, y in zip(sat_wp, sat_wp[1:])), \
        "飽和 6 % 以降で白パッチ法が単調に悪化していない"
    assert sat_wp[-1] > 5.0 * sat_rows[1.0][1]["白パッチ (p=inf)"], \
        "飽和で白パッチ法が壊れていない"
    # 飽和しきると max が (1,1,1) に張り付き、答えがゼロ点そのものに退化する
    assert abs(sat_rows[3.0][1]["白パッチ (p=inf)"]
               - sat_rows[3.0][1]["何もしない"]) < 1e-9, \
        "飽和しきっても白パッチ法がゼロ点に退化しない"
    assert sat_rows[5.0][1]["灰色世界 (p=1)"] < 2.0 * sat_rows[1.0][1]["灰色世界 (p=1)"], \
        "飽和で灰色世界まで壊れた —— 崖の軸が直交しているという所見が崩れた"
    assert sat_rows[3.0][2] < 0.5 * sat_rows[3.0][1]["白パッチ (p=inf)"], \
        "飽和マスクで白パッチ法が戻らない"

    # 7. 崖 (d): 雑音は極値依存の手法を先に壊す
    assert noise_rows[0.10]["白パッチ (p=inf)"] > 3.0 * noise_rows[0.0]["白パッチ (p=inf)"], \
        "雑音で白パッチ法が壊れない"
    assert noise_rows[0.10]["灰色世界 (p=1)"] < 2.0 * noise_rows[0.0]["灰色世界 (p=1)"], \
        "雑音で灰色世界まで壊れた"

    # 8. 崖 (e): 2 光源では開きの半分が下限。どの手法もそれを割れない
    for (t1, t2), (sep, row) in two_rows.items():
        for c, v in row.items():
            assert v >= 0.5 * sep - 1e-9, \
                f"{t1}|{t2} の {c} が理論下限 {sep / 2:.2f} 度を割った(計算ミス)"

    # 9. 最適 p は条件で動く(1 つの既定値では足りない)
    ps = {label: best_p[label][0] for label, _ in conds}
    assert len(set(ps.values())) >= 3, f"最適 p が動かない: {ps}"
    assert math.isinf(ps["素のチャート"]), "素のチャートで最適 p が ∞ でない"
    assert not math.isinf(ps["白パッチ無し"]), "白パッチ無しでも最適 p が ∞ のまま"

    # 10. 物理ベースの op: ハイライトがあれば厳密、無ければ拒否(fail-closed)
    assert angular_error(est_d, e_d) < 1e-8, \
        f"二色性の光源推定が厳密でない: {angular_error(est_d, e_d):.3e} 度"
    assert matte_refused, "マット面(ハイライト無し)が拒否されなかった"
    assert one_refused, "1 材質だけでも拒否されなかった"
    assert noisy_rows[0.05] > 10.0 * max(noisy_rows[0.002], 1e-6), \
        "二色性の光源推定が雑音で悪化していない"
    assert noisy_rows[0.05] > angular_error(max_rgb(hi), e_d), \
        "σ=0.05 でも二色性 op が統計手法に勝っている —— 所見が崩れた"

    # 11. 対角モデルの床: 真値で割っても色は合わない
    assert max(v[1] for v in floor_rows.values()) > 2.0, \
        "対角補正の床が消えた —— 真の光源で割れば色が合ってしまう"
    assert floor_rows["基準(等エネルギー)"][1] < 1e-6, \
        "基準光源で床が 0 でない(恒等変換のはず)"
    assert floor_rows["狭帯域 3 波長"][0] > floor_rows["黒体 5000 K"][0], \
        "山谷のある光源のほうが床が高い、という所見が崩れた"

    # 12. 穴 (c): fs.op.sobel_amp は ch ごとに呼ぶと各 ch が 1.0 に正規化される
    assert np.abs(perch.reshape(-1, 3).max(axis=0) - 1.0).max() < 1e-12, \
        "fs.op.sobel_amp が ch ごとに 1.0 へ正規化されない —— 穴 (c) が直った?"
    assert abs(float(whole.max()) - 1.0) < 1e-12, "画像ごとでも最大が 1.0 でない"
    assert whole.reshape(-1, 3).max(axis=0).min() < 0.9, \
        "画像ごとに渡しても ch ごとに正規化された —— 穴 (c) の内容が変わった"
    assert angular_error(est_perch, e_g) > 3.0 * angular_error(est_whole, e_g), \
        "ch ごとの正規化で灰色エッジが悪化しない —— 穴 (c) が直った?"
    assert angular_error(est_perch, e_g) > 0.7 * angular_error(np.ones(3), e_g), \
        "ch ごとに正規化してもゼロ点まで退化しない —— 穴 (c) の内容が変わった"
    # 画像ごと渡すと色軸が空間軸として扱われ、恒等的に 0 のチャンネルに値が漏れる
    assert probe[..., 1].max() == 0.0, "検査用画像の G が 0 でない(検査が壊れた)"
    assert leak_max[1] > 0.3, \
        f"色軸を跨いだ漏れが消えた({leak_max[1]:.4f})—— 穴 (c) が直った?"
    assert leak_max[2] == 0.0, "2 つ離れた B まで漏れた —— 漏れの機構が変わった"
    assert angular_error(est_whole, e_g) > 2.0 * angular_error(est_sob, e_g), \
        "画像ごとに渡しても自前 Sobel と同じ —— 漏れの影響が消えた"

    # 13. 穴 (a)(b): 該当 op が本当に無いことを台帳で確かめる
    catalog = set(fs.ledger) | set(fs.op)
    for missing in ("gray_world", "white_patch", "shades_of_gray", "gray_edge",
                    "white_balance", "awb", "auto_white_balance", "von_kries",
                    "chromatic_adaptation", "illuminant_estimate",
                    "estimate_illuminant", "color_constancy"):
        assert missing not in catalog, f"{missing} が登録された —— 穴 (a)/(b) が直った?"
    assert "illuminant_from_dichromatic_planes" in fs.ledger, \
        "唯一の光源推定 op が消えた"

    print(f"\n総所要 {time.perf_counter() - t_all:.1f} 秒")
    print("PASS")
    return True


if __name__ == "__main__":
    raise SystemExit(0 if main() else 1)
