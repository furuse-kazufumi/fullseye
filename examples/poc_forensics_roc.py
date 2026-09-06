# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""改竄検出を ROC で語る —— 「見つかった 1 枚」ではなく、偽陽性を固定したときの検出率。

EXTEND: 公開データに差し替えるなら、``build_case()`` が返す ``(画像, 真値マスク)``
の対を、データセット側の改竄画像と付属マスクに置き換えるだけでよい。CASIA v2
(改竄 5123 枚)・Columbia Uncompressed Image Splicing(180 枚、TIFF)・
DEFACTO(12 万枚、COCO 由来)・IMD2020(実際に web で拾われた改竄 2010 枚)が
よく使われる。**データはこのリポジトリに同梱しない** —— 容量の問題ではなく、
CASIA は再配布条件が明示されておらず、Columbia は研究利用の申請が要り、DEFACTO は
元画像の COCO ライセンスを継承する、というように **1 つずつ条件が違う**ため。
使う前に各データセットの配布条件を個別に確認し、成果物には出典を明記すること。

**倫理**: これは **検出側(防御)** の PoC である。ここで改竄を自分で作るのは、
検出器を測るのに **真値(どこを、どこから、どの品質で持ってきたか)が要る**ため
だけで、作り方そのものは 8x8 の格子に貼る矩形という、実際の改竄としては最も稚拙な
ものに留めてある。逆に、この PoC がいちばん強く示すのは「**後処理を 1 回かけると
どの手掛かりも消える**」という、検出側にとって不利な事実のほうである。改竄を
うまく作る方法を探しているなら、ここには無い。

この PoC が示すこと:

1. **1 枚の閾値での成功例は証拠にならない** —— ELA の平均は貼付部 0.2210 /
   背景 0.3794 = **0.58 倍**で、しかも向きが教科書と逆(強く圧縮された素材を
   貼ると貼付部のほうが *小さく* なる)。この 1 つの数字からは「効く」とも
   「効かない」とも書けてしまう。画素ごとの ROC はそれを許さない。
2. **ゼロ点(改竄していない画像 + 同じ場所の偽マスク)を必ず置く** —— 置かないと、
   画像の構造そのものや **画像内の場所** に反応しているだけの検出器を
   「効いている」と読んでしまう。実際 4-c では、貼っても 1 画素も変わらない
   条件で AUC 0.797 が出る(検出ではなく場所への偏り)。
3. **後処理でどこまで落ちるかを数で言う** —— 全体の再圧縮・縮小・平滑化は、
   どれも改竄者が保存ボタンを押すだけでかかる。そこで AUC が 0.5 に落ちるなら、
   その検出器は「実運用では効かない」と書くしかない。

主な実測(256x256 を 10 枚、貼付 64x64 = 6.25 %、画素ごとの ROC。ゴーストA =
``jpeg_ghost_quality`` の argmin 読み出し / ゴーストV = 品質ごとに標準化して
谷の深さを取る PoC 側の読み出し):

  ==================================== ======= ======= ========= =========
  条件                                 ELA     雑音 σ  ゴーストA ゴーストV
  ==================================== ======= ======= ========= =========
  **AUC**(改竄あり)                   0.961   0.764   0.500     0.997
  **偽陽性率 1 % での検出率**          0.659   0.000   0.001     0.944
  ゼロ点(改竄なし)の AUC              0.494   0.447   0.500     0.509
  全体を q75 で再圧縮                  0.789   0.690   0.500     0.975
  全体を q60 で再圧縮                  0.592   0.668   0.500     0.475
  0.75 倍に縮小して戻す                0.814   0.745   0.500     0.770
  ぼかし sigma=1.0                     0.775   0.851   0.500     0.469
  16x16 の改竄(0.39 %)                0.848   0.630   0.500     0.984
  平坦な帯(貼っても画素が変わらない)  0.535   0.345   0.798     0.797
  素材も背景と同じ q92(品質差なし)    0.627   0.698   0.500     0.554
  乱数で答える(零点の下限)            —       —       —         0.500
  ==================================== ======= ======= ========= =========

読み方: **いちばん強い ゴーストV でさえ、全体を q60 で再圧縮しただけで 0.475 =
乱数以下になる**。ELA は 0.961 → 0.592。「平坦な帯」の行は貼付前後で画像が
1 ビットも違わない条件なので、そこに出ている 0.5 からの隔たりは全部
**場所への偏り**であり、ゼロ点を置かなければ「検出できた」と読めてしまう。

★ この PoC が出した道具の穴(4 件。op 本体には手を入れていない):

  (a) **``jpeg_ghost_quality`` の argmin 読み出しは、貼り付け後に 1 度でも保存すると
      定数地図になる**。残差は品質に対して単調減少するので、全画素の argmin が
      掃引の最大品質に張り付く。``tests/...::test_jpeg_ghost_finds_the_pasted_quality``
      が通るのは **合成後に一度も保存していない**からで、実際の改竄は必ず保存を
      経る。実測: 貼付部の最頻品質は再保存なし 60(真値 60)→ 再保存 q95 で **95**
      (= 背景と同じ = 何も言っていない)。掃引から最終保存品質を外しても直らない
      (残差の単調性は掃引範囲に依らないため)。
  (b) **同じ argmin 読み出しは、貼り付け位置が 8 の倍数でないだけで死ぬ**。
      複製元と複製先のオフセットの差が 8 の倍数のときだけ品質 60 を言い当て、
      それ以外は 95(背景と同じ)。テストは ``[40:104]`` → ``[64:128]`` という
      差 24 = 8 の倍数の配置しか見ていない。docstring にこの条件が書かれていない。
  (c) **``noise_inconsistency_map`` は画像の縁に固定の偽陽性源を作る**。改竄が
      1 画素も無い画像で、``|σ - 中央値|`` は最外周のブロックが中心の **1.50 倍**
      (実測 0.0924 / 0.0616)。σ そのものは逆に最外周がいちばん低く
      (0.6546 / 中心 0.6658)、境界を reflect で折り返して Immerkær のマスクを
      畳み込むと高周波が減るためである。**生成器の側には場所の偏りが無い**
      (生画像の局所 std は環によらず 0.0357〜0.0375 で平ら)ので、これは
      PoC の作りではなく op の性質。結果として **ゼロ点の AUC が 0.5 ではなく
      0.447** になる。docstring の「言えないこと」に場所依存の偏りが載っていない。
      なお ``H % block != 0`` のときは ``full[out.shape[0]:] = out[-1:]`` が最終
      ブロックを引き伸ばす経路が別にあるが、本 PoC は 256 / 16 が割り切れるので
      そちらは踏んでいない。
  (d) **``null_distribution`` / ``evidence_quantile`` は「証拠量 1 個」を清浄分布に
      置く道具で、画素ごとの地図には掛けられない**。ROC を引くには結局 PoC 側で
      順位計算を書くことになる。この族に「地図 + 真値マスク → ROC」の op が無い。

実行時間(この機械、Windows 11 / py 3.11 / numpy 2.4.6 / scipy 1.15.2 /
Pillow 12.3.0)は全体で約 15 秒。256x256 の 1 枚あたり ELA 1.0 ms / 雑音 σ 0.6 ms /
ゴーストA 15 ms / ゴーストV 20 ms / コピー&ムーブ(keypoint)4.0 ms。ゴーストだけ
1 桁遅いのは掃引した品質の本数ぶん(12 本)JPEG 符号化を回すためで、上の表の
とおり効き目に見合っていない。乱数の種は画像のバイト列から引くので、この PoC は
**同じ環境で何度走らせても同じ数字を出す**。
"""
from __future__ import annotations

import hashlib
import io
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
from scipy import ndimage
from scipy.stats import rankdata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import examplefig as figs                                        # noqa: E402
import imgforensics as F                                         # noqa: E402

try:
    from PIL import Image
except ImportError as exc:                                # pragma: no cover
    raise SystemExit("この PoC は Pillow が要る(pip install Pillow): " + str(exc))

N = 256
BLOCK = 16


def _dw(s):
    """全角を 2 桁と数えた表示幅。表の桁を合わせるため(str.format は文字数で数える)。"""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in str(s))


def pad(s, n, right=True):
    """表示幅 ``n`` に詰める。``right`` なら右寄せ。"""
    s = str(s)
    sp = " " * max(0, n - _dw(s))
    return sp + s if right else s + sp


def _mode(a):
    """地図の最頻値(float の 2-D でも動く)。"""
    v, c = np.unique(np.asarray(a).ravel(), return_counts=True)
    return float(v[int(np.argmax(c))])


# --------------------------------------------------------------------------- #
# 素材 —— 真値つきの改竄をこちらで作る                                           #
# --------------------------------------------------------------------------- #
def natural(n=N, seed=0, beta=1.6):
    """1/f^beta の自然画像風の場。seed を変えると構造そのものが変わる。"""
    r = np.random.default_rng(seed)
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    f = np.sqrt(fy ** 2 + fx ** 2)
    f[0, 0] = 1.0
    spec = np.fft.fft2(r.standard_normal((n, n))) / (f ** beta)
    spec[0, 0] = 0
    img = np.real(np.fft.ifft2(spec))
    return 0.15 + 0.7 * (img - img.min()) / (np.ptp(img) + 1e-12)


def textured(n=N, seed=4):
    """低周波の地 + 細かいテクスチャ。コーナーが立つのでコピー&ムーブ向き。"""
    r = np.random.default_rng(seed)
    tex = ndimage.gaussian_filter(r.standard_normal((n, n)), 1.0)
    tex = (tex - tex.min()) / (np.ptp(tex) + 1e-12)
    return np.clip(0.55 * natural(n, seed) + 0.45 * tex, 0, 1)


def jpeg(img, q):
    """本物の JPEG を通して戻す(近似ではない)。"""
    buf = io.BytesIO()
    Image.fromarray((np.clip(img, 0, 1) * 255).round().astype(np.uint8), "L").save(
        buf, "JPEG", quality=int(q), subsampling=0)
    buf.seek(0)
    return np.asarray(Image.open(buf).convert("L"), np.float64) / 255.0


def flatten_band(img, r0=64, r1=192, value=0.5):
    """帯状に平坦化する。**値は画像に依らない定数**にする。

    画像ごとの平均で埋めると、貼付部と背景で明るさが違ってしまい、
    「平坦だから見えない」ではなく「段差があるから見える」を測ることになる。
    """
    out = img.copy()
    out[r0:r1] = float(value)
    return out


def build_case(seed, *, tampered=True, size=64, dst=(96, 96), src=(40, 40),
               bg_q=92, donor_q=60, save_q=95, post=None, flat=False):
    """改竄画像と真値マスクを作る。``tampered=False`` がゼロ点(偽マスクだけ返す)。

    工程は実際の改竄と同じ順:カメラが JPEG で吐く → 別品質の素材を貼る →
    もう一度保存する → (任意で)後処理。``post`` は ``("recompress", q)`` /
    ``("resize", 倍率)`` / ``("blur", sigma)``。
    """
    scene = natural(N, seed)
    if flat:
        scene = flatten_band(scene)
    bg = jpeg(scene, bg_q)
    comp = bg.copy()
    mask = np.zeros((N, N), bool)
    r, c = dst
    mask[r:r + size, c:c + size] = True
    donor_scene = natural(N, seed + 5000)
    if flat:
        donor_scene = flatten_band(donor_scene)
    if tampered:
        donor = jpeg(donor_scene, donor_q)
        comp[r:r + size, c:c + size] = donor[src[0]:src[0] + size, src[1]:src[1] + size]
    img = comp if save_q is None else jpeg(comp, save_q)
    if post is not None:
        kind, val = post
        if kind == "recompress":
            img = jpeg(img, val)
        elif kind == "resize":
            m = max(8, int(round(N * val)))
            small = np.asarray(
                Image.fromarray((img * 255).round().astype(np.uint8), "L").resize(
                    (m, m), Image.BILINEAR).resize((N, N), Image.BILINEAR),
                np.float64) / 255.0
            img = small
        elif kind == "blur":
            img = np.clip(ndimage.gaussian_filter(img, val), 0, 1)
        else:
            raise ValueError(f"未知の後処理 {kind!r}")
    return np.clip(img, 0, 1), mask


# --------------------------------------------------------------------------- #
# 検出器 —— どれも「大きいほど怪しい」向きの画素ごとのスコア地図                  #
# --------------------------------------------------------------------------- #
def score_ela(img):
    """ELA(誤差レベル解析)を箱平均で領域化し、画像中央値からの隔たりを取る。

    **絶対値を取る向きは意図的**。ELA は「貼付部のほうが誤差が大きい」と説明される
    ことが多いが、それは貼った素材が無圧縮のときの話で、**強く圧縮された素材を
    貼ると逆に貼付部のほうが誤差が小さくなる**(この PoC の既定 q60 の素材では
    貼付部 / 背景 = 0.58 倍)。片側だけ見る検出器は、その半分を取り逃がす。
    """
    m = ndimage.uniform_filter(
        F.error_level_map(img, quality=90, normalize=False), BLOCK, mode="reflect")
    return np.abs(m - float(np.median(m)))


def score_noise(img):
    """ブロックごとの雑音 σ の、画像中央値からの隔たり。"""
    m = F.noise_inconsistency_map(img, block=BLOCK)
    return np.abs(m - float(np.median(m)))


GHOST_QS = list(range(40, 100, 5))


def score_ghost_argmin(img):
    """op の読み出しそのまま:画素ごとの最小残差品質の、最頻値からの隔たり。"""
    q = F.jpeg_ghost_quality(F.jpeg_ghost_map(img, GHOST_QS, block=BLOCK), GHOST_QS)
    return np.abs(q - _mode(q))


def score_ghost_contrast(img):
    """PoC 側の読み出し:品質ごとに地図を標準化し、**谷の深さ**の最大値を取る。

    argmin が定数に張り付くのは残差が品質に対して単調減少するからなので、
    「どの品質で、まわりに比べて残差が落ち込むか」を空間コントラストで見る。
    """
    st = np.stack(F.jpeg_ghost_map(img, GHOST_QS, block=BLOCK), 0)
    mu = st.mean(axis=(1, 2), keepdims=True)
    sd = st.std(axis=(1, 2), keepdims=True) + 1e-12
    return np.max((mu - st) / sd, axis=0)


def score_random(img):
    """零点の下限:画像の**中身に依存しない**乱数場。ROC は必ず 0.5 に行くはず。

    種は画像のバイト列から引く。**実行のたびに変える誘惑に負けないこと** ——
    同じ画像に同じスコアが出ないと、下の「貼っても画素が変わらないなら AUC も
    1 ビットも変わらないはず」という検算ができなくなる。
    """
    h = hashlib.blake2b(np.ascontiguousarray(img, np.float64).tobytes(),
                        digest_size=8).digest()
    return np.random.default_rng(int.from_bytes(h, "little")).random(img.shape)


DETECTORS = (
    ("ELA", score_ela),
    ("雑音σ", score_noise),
    ("ゴーストA", score_ghost_argmin),
    ("ゴーストV", score_ghost_contrast),
    ("乱数", score_random),
)
#: 表の見出しは狭いので、意味は一度ここに書いておく。
#:   ELA       = 誤差レベル解析(``error_level_map``)
#:   雑音σ     = 雑音整合性(``noise_inconsistency_map``)
#:   ゴーストA = JPEG ゴーストの **op の読み出し**(``jpeg_ghost_quality`` = argmin)
#:   ゴーストV = JPEG ゴーストの **PoC 側の読み出し**(品質ごとに標準化して谷の深さ)
#:   乱数      = 画像を見ない対照(零点の下限)


def standardize(m):
    """画像ごとの水準差を抜く(中央値と四分位範囲)。複数枚をまとめて数えるため。"""
    med = float(np.median(m))
    iqr = float(np.percentile(m, 75) - np.percentile(m, 25))
    return (m - med) / (iqr if iqr > 0 else 1.0)


# --------------------------------------------------------------------------- #
# ROC —— 順位で AUC、閾値掃引で偽陽性率固定の検出率                              #
# --------------------------------------------------------------------------- #
def auc_and_tpr(scores, labels, fpr_target=0.01):
    """(AUC, 指定偽陽性率での検出率, 実際に届いた偽陽性率) を返す。

    AUC は Mann-Whitney の U 統計量(同点は平均順位)。検出率は閾値を下げながら
    偽陽性率が ``fpr_target`` を **超えない**最後の点で読む —— 同点だらけの地図
    (定数地図など)では偽陽性率が飛ぶので、届いた値も一緒に返す。
    """
    s = np.asarray(scores, np.float64).ravel()
    y = np.asarray(labels, bool).ravel()
    n1 = int(y.sum())
    n0 = int(y.size - n1)
    if n1 == 0 or n0 == 0:
        raise ValueError("陽性と陰性が両方要る")
    ranks = rankdata(s)
    auc = (ranks[y].sum() - n1 * (n1 + 1) / 2.0) / (n1 * n0)
    order = np.argsort(-s, kind="mergesort")
    ss, yy = s[order], y[order]
    tp = np.cumsum(yy)
    fp = np.cumsum(~yy)
    last = np.r_[np.flatnonzero(np.diff(ss) != 0), ss.size - 1]
    fpr = fp[last] / n0
    tpr = tp[last] / n1
    i = int(np.searchsorted(fpr, fpr_target, side="right")) - 1
    if i < 0:
        return float(auc), 0.0, 0.0
    return float(auc), float(tpr[i]), float(fpr[i])


def roc_points(detector, cases, n_pts=240):
    """図のための ROC 点列(``(fpr, tpr)``)。AUC の数字は :func:`auc_and_tpr` が正本。

    65 万点をそのまま折れ線にはできないので **等間隔に間引く**。曲線の形を見る
    ための道具で、面積を測り直すためのものではない。
    """
    sc = np.concatenate([standardize(detector(im)).ravel() for im, _ in cases])
    lb = np.concatenate([np.asarray(mk, bool).ravel() for _, mk in cases])
    y = lb[np.argsort(-sc, kind="mergesort")]
    tpr = np.cumsum(y) / max(int(y.sum()), 1)
    fpr = np.cumsum(~y) / max(int((~y).sum()), 1)
    k = np.unique(np.linspace(0, y.size - 1, n_pts).astype(int))
    return np.r_[0.0, fpr[k]], np.r_[0.0, tpr[k]]


def evaluate(detector, cases):
    """画素をまとめて 1 本の ROC にする。``cases`` = [(画像, マスク), ...]。"""
    sc, lb = [], []
    for img, mask in cases:
        sc.append(standardize(detector(img)).ravel())
        lb.append(mask.ravel())
    return auc_and_tpr(np.concatenate(sc), np.concatenate(lb))


def make_cases(n_img, **kw):
    return [build_case(seed, **kw) for seed in range(n_img)]


W_LABEL = 24
W_COL = 11


def header():
    print("  " + pad("条件", W_LABEL, right=False)
          + "".join(pad(n, W_COL) for n, _ in DETECTORS))
    print("  " + "-" * (W_LABEL + W_COL * len(DETECTORS)))


def row(label, cases, detectors=DETECTORS):
    """1 条件ぶんの AUC を全検出器で出して 1 行に印字する。"""
    out = {name: evaluate(fn, cases) for name, fn in detectors}
    print("  " + pad(label, W_LABEL, right=False)
          + "".join(pad(f"{out[n][0]:.3f}", W_COL) for n, _ in detectors))
    return out


# --------------------------------------------------------------------------- #
def main():
    n_img = 10

    print("=== 1. 何を作ったか(真値は自分で入れたので分かっている)===")
    img, mask = build_case(0)
    print(f"  画像 {N}x{N} / 背景は JPEG q92 / 貼付素材は別画像を JPEG q60 で圧縮したもの")
    print("  貼付 64x64 を (96, 96) へ(素材の切り出しは (40, 40) = 差 56 で 8 の倍数)")
    print("  合成後にもう一度 q95 で保存(**実際の改竄は必ず保存を経る**)")
    print(f"  改竄画素は {int(mask.sum())} / {mask.size} = {100 * mask.mean():.2f} %")
    raw = ndimage.uniform_filter(
        F.error_level_map(img, quality=90, normalize=False), BLOCK, mode="reflect")
    print(f"  片側の ELA 平均 貼付部 {raw[mask].mean():.4f} / 背景 {raw[~mask].mean():.4f}"
          f" = {raw[mask].mean() / raw[~mask].mean():.2f} 倍")
    print("  → **向きが教科書と逆である**。ELA は「貼付部のほうが誤差が大きい」と")
    print("     説明されるが、それは無圧縮の素材を貼ったときの話で、強く圧縮された")
    print("     素材を貼ると逆に小さくなる。片側だけ見る検出器はここで取り逃がす。")
    print("     以下はすべて『画像中央値からの隔たり』= 両側で測る。")
    if figs.enabled():
        # ★穴 (a) は「定数地図」なので、絵にすれば数字を読むまでもない。
        figs.save_grid("score_maps",
                       [img, mask.astype(float), score_ela(img),
                        score_ghost_contrast(img), score_ghost_argmin(img)],
                       ["改竄画像(q95 保存後)", "真値マスク", "ELA", "ゴーストV",
                        "ゴーストA(op の読み出し)"],
                       title="同じ 1 枚に対する 3 つのスコア地図", ncols=3,
                       caption="ゴーストA は全画素が同じ値 = 何も言っていない"
                               "(AUC ちょうど 0.500)。ELA と ゴーストV は貼付部が立つ。")

    print(f"\n=== 2. 画素ごとの ROC({n_img} 枚をまとめて 1 本)===")
    base = make_cases(n_img)
    header()
    res_pos = row("改竄あり AUC", base)
    null = make_cases(n_img, tampered=False)
    res_null = row("ゼロ点 AUC", null)
    print()
    print("  " + pad("検出器", W_LABEL, right=False) + pad("AUC", 10)
          + pad("FPR 1% の検出率", 18) + pad("実 FPR", 10) + pad("ゼロ点 AUC", 12))
    for name, _ in DETECTORS:
        a, t, f = res_pos[name]
        print("  " + pad(name, W_LABEL, right=False) + pad(f"{a:.3f}", 10)
              + pad(f"{t:.3f}", 18) + pad(f"{f:.4f}", 10)
              + pad(f"{res_null[name][0]:.3f}", 12))
    print("  → 乱数の AUC が 0.500 に乗ることで、この測り方自体に偏りが無いことが言える。")
    print("     ゼロ点(改竄していない画像に同じ場所の偽マスク)も 0.5 付近にいるべきで、")
    print("     ここが 0.5 から離れる検出器は『画像の構造』でなく『場所』に反応している。")
    if figs.enabled():
        # 表の AUC だけだと「左端(低偽陽性率)でどう振る舞うか」が消える。
        # 運用で効くのはそこなので、曲線そのものを残す。
        figs.save_plot("roc_tampered",
                       [("%s %.3f" % (n, res_pos[n][0]), *roc_points(fn, base))
                        for n, fn in DETECTORS],
                       xlabel="偽陽性率", ylabel="検出率", xlim=(0.0, 1.0), ylim=(0.0, 1.0),
                       title="画素ごとの ROC(改竄あり %d 枚)" % n_img,
                       caption="凡例の数字は AUC。乱数が対角線に乗ることで測り方に"
                               "偏りが無いと言える。ゴーストA は乱数と重なる。")

    print("\n=== 3. ゼロ点のスコア分布(改竄していない画像、偽マスクの内と外)===")
    print("  " + pad("検出器", W_LABEL, right=False) + pad("偽マスク内 平均", 18)
          + pad("外 平均", 12) + pad("内/外", 10) + pad("z", 10))
    for name, fn in DETECTORS:
        ins, outs = [], []
        for im, mk in null:
            s = standardize(fn(im))
            ins.append(s[mk])
            outs.append(s[~mk])
        a = np.concatenate(ins)
        b = np.concatenate(outs)
        ratio = a.mean() / b.mean() if abs(b.mean()) > 1e-12 else float("nan")
        z = (a.mean() - b.mean()) / (b.std() / np.sqrt(a.size) + 1e-12)
        print("  " + pad(name, W_LABEL, right=False) + pad(f"{a.mean():.4f}", 18)
              + pad(f"{b.mean():.4f}", 12) + pad(f"{ratio:.3f}", 10)
              + pad(f"{z:.1f}", 10))
    print("  → 内/外の比は 1 から離れ、z は 2 桁になる。**それでも AUC は 0.5 付近**")
    print("     である(改竄していないのだから当然)。**z が大きいことと検出できること**")
    print("     **は別**で、それを分けて言えるのが AUC と FPR 固定の検出率のほうである。")
    # 場所への偏りを、ブロック格子の「中心からの環」で測る。
    nb = N // BLOCK
    yy, xx = np.mgrid[0:nb, 0:nb]
    ring = np.maximum(np.abs(yy - (nb - 1) / 2), np.abs(xx - (nb - 1) / 2)).astype(int)
    dev = np.zeros((nb, nb))      # |σ - 中央値| の環ごとの平均
    sig = np.zeros((nb, nb))      # σ そのもの
    gen = np.zeros((nb, nb))      # 生画像の局所標準偏差(生成器側の偏りの検査)
    for k, (im, _) in enumerate(null):
        m = F.noise_inconsistency_map(im, block=BLOCK)
        dev += np.abs(m - float(np.median(m)))[::BLOCK, ::BLOCK]
        sig += m[::BLOCK, ::BLOCK]
        raw = natural(N, k)
        loc = np.sqrt(np.maximum(ndimage.uniform_filter(raw ** 2, BLOCK)
                                 - ndimage.uniform_filter(raw, BLOCK) ** 2, 0))
        gen += loc[BLOCK // 2::BLOCK, BLOCK // 2::BLOCK]
    dev, sig, gen = dev / len(null), sig / len(null), gen / len(null)
    ctr, out = ring == 0, ring == ring.max()
    print(f"     雑音 σ のゼロ点 AUC は {res_null['雑音σ'][0]:.3f} で、0.5 から離れている。")
    print("     " + pad("ブロック格子の環", 22, right=False)
          + pad("中心", 10) + pad("最外周", 10) + pad("外/中", 10))
    for lbl, arr in (("|σ - 中央値|", dev), ("σ そのもの", sig),
                     ("生画像の局所 std", gen)):
        print("     " + pad(lbl, 22, right=False) + pad(f"{arr[ctr].mean():.4f}", 10)
              + pad(f"{arr[out].mean():.4f}", 10)
              + pad(f"{arr[out].mean() / arr[ctr].mean():.2f}", 10))
    print("     → σ そのものは最外周がいちばん **低い**(境界を reflect で折り返すと")
    print("       高周波が減る)。そのぶん中央値からの隔たりが大きくなり、**改竄が**")
    print("       **無くても縁が固定の偽陽性源になる**。3 行目のとおり生成器の側には")
    print("       場所の偏りが無い(生画像の局所 std は環によらず平ら)ので、これは")
    print("       この PoC の作りではなく op の性質である。★道具の穴 (c)。")

    print("\n=== 4-a. 効かなくなる境界:改竄領域の大きさ ===")
    header()
    size_rows = {}
    for size in (96, 64, 48, 32, 16):
        size_rows[size] = row(f"{size}x{size}"
                              f"({100.0 * size * size / (N * N):.2f} %)",
                              make_cases(n_img, size=size))
    print("  ↓ 同じ条件を FPR 1 % での検出率で見る(AUC より落ち方がはっきりする)")
    header()
    for size in (96, 64, 48, 32, 16):
        print("  " + pad(f"{size}x{size}", W_LABEL, right=False)
              + "".join(pad(f"{size_rows[size][n][1]:.3f}", W_COL) for n, _ in DETECTORS))
    print("  → AUC は面積に鈍い(陽性画素の数で正規化されるので、小さくしても")
    print("     ELA は 0.97 → 0.85 程度にしか落ちない)。**落ちるのは FPR 1 % の検出率**")
    print("     **のほう**で、こちらは同じ範囲でずっと大きく動く。AUC だけを見て")
    print("     『小さい改竄でも効く』と書くのは、この差を隠すことになる。")

    print("\n=== 4-b. 効かなくなる境界:あとから全体にかけた後処理 ===")
    header()
    post_rows = {}
    post_cases = {}                 # 図で ROC 曲線を引くために取っておく
    for label, post in (("後処理なし", None),
                        ("全体を q75 で再圧縮", ("recompress", 75)),
                        ("全体を q60 で再圧縮", ("recompress", 60)),
                        ("0.75 倍に縮小して戻す", ("resize", 0.75)),
                        ("ぼかし sigma=1.0", ("blur", 1.0))):
        post_cases[label] = make_cases(n_img, post=post)
        post_rows[label] = row(label, post_cases[label])
    print("  ↓ 同じ条件を FPR 1 % での検出率で見る")
    header()
    for label in post_rows:
        print("  " + pad(label, W_LABEL, right=False)
              + "".join(pad(f"{post_rows[label][n][1]:.3f}", W_COL) for n, _ in DETECTORS))
    print("  → **フォレンジックは後処理で消える**。改竄者が保存し直すだけでよい。")
    print("     再圧縮は貼付部と背景の量子化履歴を同じものに塗り替え、縮小は 8x8 の")
    print("     格子そのものを壊す。どちらも『改竄を隠す意図』が無くても起きる。")
    print("     ゴーストは q60 再圧縮とぼかしで **0.5 を下回る** —— これは『効かない』")
    print("     を通り越して、符号を逆に読ませる方向に壊れているということである。")
    if figs.enabled():
        # ★この PoC の見出し。いちばん強い検出器の曲線が、保存ボタン 1 回で
        #   対角線まで(そして下まで)落ちる。
        figs.save_plot("roc_postprocess",
                       [("%s %.3f" % (lb.replace("全体を", "").replace("して戻す", ""),
                                      post_rows[lb]["ゴーストV"][0]),
                         *roc_points(score_ghost_contrast, post_cases[lb]))
                        for lb in post_cases],
                       xlabel="偽陽性率", ylabel="検出率", xlim=(0.0, 1.0), ylim=(0.0, 1.0),
                       title="いちばん強い ゴーストV も後処理 1 回で消える",
                       caption="凡例の数字は AUC。対角線が乱数。q60 再圧縮とぼかしでは"
                               "曲線が下側へ回り、符号が逆に読める状態になる。")

    print("\n=== 4-c. 効かなくなる境界:平坦な領域(貼っても画素が変わらない)===")
    FLAT_KW = dict(flat=True, src=(80, 80))     # 切り出し元も平坦帯 (64..191) の中
    fim, fmk = build_case(0, **FLAT_KW)
    fnull, _ = build_case(0, tampered=False, **FLAT_KW)
    changed = int(np.count_nonzero(np.abs(fim - fnull)[fmk] > 0.5 / 255.0))
    print("  平坦な帯(値 0.5 一定)に別画像の平坦部を貼ると、実際に変わった画素は")
    print(f"  {changed} / {int(fmk.sum())}。JPEG は平坦な 8x8 を同じ定数に量子化するので、")
    print("  **貼るという操作が画素の上に痕跡を一切残さない**。")
    print("  (切り出し元も帯の中に取ること —— 帯の外にはみ出すと、そこだけ模様が")
    print("   入って『平坦だから見えない』ではなく『模様が見える』を測ってしまう。")
    print("   最初にそれで 1532 / 4096 画素が変わり、ゴーストが 0.728 と高く出た。)")
    header()
    flat_rows = {"平坦": row("平坦・改竄あり", make_cases(n_img, **FLAT_KW)),
                 "平坦ゼロ点": row("平坦・改竄なし",
                                   make_cases(n_img, tampered=False, **FLAT_KW))}
    print("  " + pad("通常(構造あり)= 2 節の再掲", W_LABEL, right=False)
          + "".join(pad(f"{res_pos[n][0]:.3f}", W_COL) for n, _ in DETECTORS))
    print("  → 上 2 行は **1 ビットも違わない**(改竄ありと改竄なしで画像が同一)。")
    print("     つまりここで見えている 0.5 からの隔たりは、検出ではなく")
    print("     **場所への偏り**である —— 偽マスクは平坦な帯の中にあり、帯の外の")
    print("     模様がある所のほうがスコアが高いので、そのぶん 0.5 からずれる。")
    print("     ゴーストV の 0.8 前後がいちばん大きい。**同じ数字が『検出できた』**")
    print("     **として報告されうる**ことに注意 —— 分けられるのはゼロ点があるから。")

    print("\n=== 4-e. 対照:品質差が無い貼り付け(素材も背景と同じ q92)===")
    header()
    same_rows = row("素材も q92", make_cases(n_img, donor_q=92))
    print("  → 圧縮履歴の差が無くなると、圧縮を手掛かりにする検出器は落ちる。")
    print("     ここが落ちずに残る検出器は、圧縮履歴ではなく **貼った素材の中身**")
    print("     (別画像なので統計が違う)に反応している。切り分けにこの行が要る。")

    print("\n=== 4-d. 効かなくなる境界:貼り付け位置の 8 画素格子 ===")
    print("  " + pad("配置", 20, right=False) + pad("差 mod 8", 12)
          + pad("貼付部の最頻品質", 20) + pad("背景", 10))
    for (sr, dr) in ((40, 96), (40, 99), (43, 96), (43, 99)):
        im, mk = build_case(0, src=(sr, sr), dst=(dr, dr), save_q=None)
        q = F.jpeg_ghost_quality(F.jpeg_ghost_map(im, GHOST_QS, block=BLOCK), GHOST_QS)
        inner = np.zeros((N, N), bool)
        inner[dr + 8:dr + 56, dr + 8:dr + 56] = True
        mi, mo = int(_mode(q[inner])), int(_mode(q[8:56, 8:56]))
        print("  " + pad(f"src {sr} → dst {dr}", 20, right=False)
              + pad((dr - sr) % 8, 12) + pad(mi, 20) + pad(mo, 10))
    print("  → 真値は 60。差が 8 の倍数のときだけ言い当てる。★道具の穴 (b)。")
    print("     しかも上は **合成後に保存していない**場合で、q95 で 1 度保存すると:")
    for (sr, dr) in ((40, 96), (43, 99)):
        im, mk = build_case(0, src=(sr, sr), dst=(dr, dr), save_q=95)
        q = F.jpeg_ghost_quality(F.jpeg_ghost_map(im, GHOST_QS, block=BLOCK), GHOST_QS)
        inner = np.zeros((N, N), bool)
        inner[dr + 8:dr + 56, dr + 8:dr + 56] = True
        print(f"     src {sr} → dst {dr}: 貼付部 {int(_mode(q[inner]))}"
              f" / 背景 {int(_mode(q[8:56, 8:56]))}"
              f" / 地図の相異なる値 {np.unique(q).size} 個")
    print("     ★道具の穴 (a)。定数地図 = 何も言っていない(AUC もちょうど 0.500)。")

    print("\n=== 5. コピー&ムーブは画像ごとの ROC で語れる(画素地図ではない)===")
    n_cm = 16
    cm_scores, cm_labels = [], []
    t0 = time.perf_counter()
    for seed in range(n_cm):
        img = textured(N, seed)
        forged = img.copy()
        forged[150:214, 160:224] = img[40:104, 32:96]
        for pic, lab in ((jpeg(forged, 95), True), (jpeg(img, 95), False)):
            g = F.copy_move_regions(pic, method="keypoint")
            cm_scores.append(float(g[0]["n_matches"]) if g else 0.0)
            cm_labels.append(lab)
    dt = time.perf_counter() - t0
    cm_scores = np.asarray(cm_scores)
    cm_labels = np.asarray(cm_labels)
    cm_auc = auc_and_tpr(cm_scores, cm_labels, fpr_target=0.01)[0]
    tpr_at0 = auc_and_tpr(cm_scores, cm_labels, fpr_target=0.0)[1]
    print(f"  改竄 {n_cm} 枚 / 清浄 {n_cm} 枚、スコア = 第 1 群の対応数(群が無ければ 0)")
    print(f"  AUC {cm_auc:.3f} / 清浄側の最大スコア {cm_scores[~cm_labels].max():.0f}"
          f" / 改竄側の中央値 {np.median(cm_scores[cm_labels]):.0f}")
    print(f"  偽陽性率 0 % での検出率 {tpr_at0:.3f}(清浄 {n_cm} 枚では 1 % は刻めない ——")
    print(f"  1 枚が {100.0 / n_cm:.1f} % なので、1 % を主張するには清浄が 100 枚以上要る)")
    print(f"  所要 {dt:.2f} 秒 / {2 * n_cm} 枚 = {1e3 * dt / (2 * n_cm):.1f} ms/枚")

    print("\n=== 6. 速度(この機械での実測、256x256 の 1 枚あたり)===")
    probe, _ = build_case(0)
    for name, fn in DETECTORS[:4]:
        fn(probe)
        t0 = time.perf_counter()
        for _ in range(5):
            fn(probe)
        print("  " + pad(name, W_LABEL, right=False)
              + pad(f"{1e3 * (time.perf_counter() - t0) / 5:.2f}", 9) + " ms")
    print("  " + pad("コピー&ムーブ(keypoint)", W_LABEL, right=False), end="")
    t0 = time.perf_counter()
    for _ in range(5):
        F.copy_move_regions(probe, method="keypoint")
    print(pad(f"{1e3 * (time.perf_counter() - t0) / 5:.2f}", 9) + " ms")
    print("  → ゴーストだけ 1 桁遅い。品質の本数ぶん JPEG 符号化を回すので、")
    print("     掃引 12 本なら符号化 12 回。効き目は上の表のとおり乏しい。")

    print("\n=== 7. まとめ ===")
    print(f"  この条件でいちばん強いのは ゴーストV(AUC {res_pos['ゴーストV'][0]:.3f}、"
          f"FPR 1 % の検出率 {res_pos['ゴーストV'][1]:.3f})、")
    print(f"  次が ELA(AUC {res_pos['ELA'][0]:.3f} / {res_pos['ELA'][1]:.3f})。ただし ゴーストV は")
    print("  **op の読み出しではなく PoC 側で書いた読み出し**で、op が提供する")
    print(f"  argmin の読み出し(ゴーストA)は AUC {res_pos['ゴーストA'][0]:.3f} = 乱数と同じである。")
    print("  そして上の数字はすべて『背景が JPEG・素材が別品質・後処理なし・64x64』")
    print("  という、検出側にいちばん都合のよい条件のもの。境界は下のとおり:")
    print("  " + pad("崩れる条件", 26, right=False) + pad("ELA", 10) + pad("ゴーストV", 12))
    break_rows = []
    for label, key in (("後処理なし", post_rows["後処理なし"]),
                       ("全体を q75 で再圧縮", post_rows["全体を q75 で再圧縮"]),
                       ("全体を q60 で再圧縮", post_rows["全体を q60 で再圧縮"]),
                       ("0.75 倍に縮小して戻す", post_rows["0.75 倍に縮小して戻す"]),
                       ("ぼかし sigma=1.0", post_rows["ぼかし sigma=1.0"]),
                       ("16x16 の小さい改竄", size_rows[16]),
                       ("平坦な帯(実体は場所の偏り)", flat_rows["平坦"]),
                       ("素材も背景と同じ q92", same_rows)):
        print("  " + pad(label, 26, right=False)
              + pad(f"{key['ELA'][0]:.3f}", 10) + pad(f"{key['ゴーストV'][0]:.3f}", 12))
        break_rows.append([label, "%.3f" % key["ELA"][0], "%.3f" % key["ゴーストV"][0],
                           "%.3f" % key["ELA"][1], "%.3f" % key["ゴーストV"][1]])
    # AUC だけの表にしない —— FPR 1 % の検出率のほうが先に落ちる(4-a 参照)。
    figs.save_table("breaking_conditions",
                    ["条件", "ELA AUC", "ゴーストV AUC",
                     "ELA FPR1%", "ゴーストV FPR1%"],
                    break_rows, col_w=145,
                    title="どこで崩れるか(乱数の AUC は 0.500)",
                    caption="保存ボタン 1 回(q60 再圧縮)で ゴーストV は乱数以下。"
                            "『平坦な帯』の行は実体が場所への偏り。")
    print("  **ゼロ点と後処理を置かずに『検出できた』と書くのは、この差を隠すことに**")
    print("  **等しい**。実運用で相手が保存ボタンを 1 回押せば、上の表の 3 行目まで")
    print("  落ちる。それが画像フォレンジックの正直な現在地である。")

    # ---- 自己検査(速さは assert しない)------------------------------------
    # (1) 測り方に偏りが無い:乱数検出器は改竄ありでもゼロ点でも 0.5 付近
    assert abs(res_pos["乱数"][0] - 0.5) < 0.01, res_pos["乱数"]
    assert abs(res_null["乱数"][0] - 0.5) < 0.01, res_null["乱数"]
    # (2) ゼロ点はどの検出器でも 0.5 付近(改竄が無いのだから当たってはいけない)。
    #     許容 0.10 は緩いが、雑音 σ が縁の偽陽性で 0.45 付近に座るのを **通す**
    #     ためではなく **記録する**ため。締めると穴 (c) が assert で潰れて見えなくなる。
    for name, _ in DETECTORS:
        assert abs(res_null[name][0] - 0.5) < 0.10, (name, res_null[name])
    # (3) 効いている検出器は零点を上回る
    assert res_pos["ELA"][0] > 0.80, res_pos["ELA"]
    assert res_pos["雑音σ"][0] > 0.65, res_pos["雑音σ"]
    assert res_pos["ゴーストV"][0] > 0.90, res_pos["ゴーストV"]
    # (4) ★穴 (a): op の argmin 読み出しは、再保存した画像では実質定数地図。
    #     AUC はちょうど 0.5 = 乱数と区別できない。
    assert abs(res_pos["ゴーストA"][0] - 0.5) < 1e-3, res_pos["ゴーストA"]
    q = F.jpeg_ghost_quality(F.jpeg_ghost_map(build_case(0)[0], GHOST_QS, block=BLOCK),
                             GHOST_QS)
    assert float(np.mean(q == _mode(q))) > 0.999, (np.unique(q), np.mean(q == _mode(q)))
    # (5) 大きさを下げると FPR 1 % の検出率が落ちる(AUC は面積に鈍いのでそちらでは
    #     assert しない —— 実測で AUC は 0.97 → 0.85 としか動かない)
    assert size_rows[16]["ELA"][1] < size_rows[96]["ELA"][1] - 0.05, (
        size_rows[16]["ELA"], size_rows[96]["ELA"])
    # (6) 後処理で落ちる —— これがこの PoC のいちばんの主張
    assert post_rows["全体を q60 で再圧縮"]["ELA"][0] < post_rows["後処理なし"]["ELA"][0] - 0.10
    assert post_rows["0.75 倍に縮小して戻す"]["ELA"][0] < post_rows["後処理なし"]["ELA"][0] - 0.10
    assert post_rows["全体を q60 で再圧縮"]["ゴーストV"][0] < 0.60
    assert post_rows["ぼかし sigma=1.0"]["ゴーストV"][0] < 0.60
    # (7) 平坦な帯では貼っても画素が 1 つも変わらない。したがって「改竄あり」と
    #     「改竄なし」の AUC は **完全に一致**しなければならない。一致するなら、
    #     そこに出ている 0.5 からの隔たりは検出ではなく場所への偏りだと確定する。
    assert changed == 0, f"平坦な帯で {changed} 画素が変わっている(対照が成立していない)"
    for name, _ in DETECTORS:
        a1 = flat_rows["平坦"][name][0]
        a2 = flat_rows["平坦ゼロ点"][name][0]
        assert abs(a1 - a2) < 1e-12, (name, a1, a2)
    assert flat_rows["平坦"]["ELA"][0] < res_pos["ELA"][0] - 0.30
    # (8) 品質差が無ければ、圧縮履歴を見る検出器は落ちる
    assert same_rows["ゴーストV"][0] < res_pos["ゴーストV"][0] - 0.05, (
        same_rows["ゴーストV"], res_pos["ゴーストV"])
    # (9) ★穴 (b): 8 画素格子。差が 8 の倍数のときだけ言い当てる(再保存なし)
    im_a, _ = build_case(0, src=(40, 40), dst=(96, 96), save_q=None)
    im_b, _ = build_case(0, src=(40, 40), dst=(99, 99), save_q=None)
    qa = F.jpeg_ghost_quality(F.jpeg_ghost_map(im_a, GHOST_QS, block=BLOCK), GHOST_QS)
    qb = F.jpeg_ghost_quality(F.jpeg_ghost_map(im_b, GHOST_QS, block=BLOCK), GHOST_QS)
    assert int(_mode(qa[104:152, 104:152])) == 60, _mode(qa[104:152, 104:152])
    assert int(_mode(qb[107:155, 107:155])) == max(GHOST_QS), _mode(qb[107:155, 107:155])
    # (10) ROC の実装が端で正しい:完全分離は 1.0、逆向きは 0.0、全同点は 0.5
    lab = np.r_[np.ones(50, bool), np.zeros(50, bool)]
    assert auc_and_tpr(np.r_[np.ones(50), np.zeros(50)], lab)[0] == 1.0
    assert auc_and_tpr(np.r_[np.zeros(50), np.ones(50)], lab)[0] == 0.0
    assert auc_and_tpr(np.zeros(100), lab)[0] == 0.5
    # (11) コピー&ムーブは清浄画像で群を作らない(偽陽性 0)
    assert cm_scores[~cm_labels].max() == 0.0, cm_scores[~cm_labels]
    assert cm_auc > 0.9, cm_auc
    if figs.errors():
        print("図の書き出しで失敗:", "; ".join(figs.errors()))
    print("\nPASS")


if __name__ == "__main__":
    main()
