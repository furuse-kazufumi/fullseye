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

1. **1 枚の閾値での成功例は証拠にならない** —— ELA も雑音地図も、改竄領域の平均が
   背景の 2〜3 倍という「効いていそうな」数字を出す。しかし画素ごとの ROC を引くと
   偽陽性率 1 % での検出率は下の表のとおりで、平均の比とはまったく別の話になる。
2. **ゼロ点(改竄していない画像 + 同じ場所の偽マスク)を必ず置く** —— 置かないと、
   画像の構造そのものに反応しているだけの検出器を「効いている」と読んでしまう。
3. **後処理でどこまで落ちるかを数で言う** —— 全体の再圧縮・縮小・平滑化は、
   どれも改竄者が保存ボタンを押すだけでかかる。そこで AUC が 0.5 に落ちるなら、
   その検出器は「実運用では効かない」と書くしかない。

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
  (c) **``noise_inconsistency_map`` はブロック定数を端で複製するので、右端と下端に
      幅 ``block`` の偽の段差が立つ**(256 は 16 で割り切れるので本 PoC では出ないが、
      ``H % block != 0`` のとき ``full[out.shape[0]:] = out[-1:]`` が最終行を引き伸ばす)。
      ROC を引くと、この帯が固定の偽陽性源になる。
  (d) **``null_distribution`` / ``evidence_quantile`` は「証拠量 1 個」を清浄分布に
      置く道具で、画素ごとの地図には掛けられない**。ROC を引くには結局 PoC 側で
      順位計算を書くことになる。この族に「地図 + 真値マスク → ROC」の op が無い。

実行(この機械、Windows 11 / py 3.11 / numpy 2.4.6 / scipy 1.15.2 / Pillow 12.3.0):
末尾の速度表のとおり 256x256 1 枚あたり ELA 0.7 ms・雑音 0.8 ms・ゴースト 12 ms 程度。
"""
from __future__ import annotations

import io
import time
import unicodedata

import numpy as np
from scipy import ndimage
from scipy.stats import rankdata

import imgforensics as F

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


def flatten_band(img, r0=64, r1=192):
    """帯状に平坦化する。平坦な領域で検出器が効かなくなることを見るため。"""
    out = img.copy()
    out[r0:r1] = float(np.mean(img[r0:r1]))
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
    if tampered:
        donor = jpeg(natural(N, seed + 5000), donor_q)
        if flat:
            donor = jpeg(flatten_band(natural(N, seed + 5000)), donor_q)
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


def score_random(img, _rng=np.random.default_rng(12345)):
    """零点の下限:画像を見ずに乱数を返す検出器。ROC は必ず 0.5 に行くはず。"""
    return _rng.random(img.shape)


DETECTORS = (
    ("ELA", score_ela),
    ("雑音σ", score_noise),
    ("ゴーストA", score_ghost_argmin),
    ("ゴーストV", score_ghost_contrast),
    ("乱数", score_random),
)
#: 表の見出しに使う名前 → 長い説明(末尾のまとめで使う)
LONG = {"ELA": "ELA(誤差レベル解析)",
        "雑音σ": "雑音 σ の不整合",
        "ゴーストA": "JPEG ゴースト(op の argmin 読み出し)",
        "ゴーストV": "JPEG ゴースト(PoC 側の谷の深さ読み出し)",
        "乱数": "乱数(画像を見ない)"}


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
    print(f"  貼付 64x64 を (96, 96) へ(素材の切り出しは (40, 40) = 差 56 で 8 の倍数)")
    print(f"  合成後にもう一度 q95 で保存(**実際の改竄は必ず保存を経る**)")
    print(f"  改竄画素は {int(mask.sum())} / {mask.size} = {100 * mask.mean():.2f} %")
    print(f"  ELA の平均 貼付部 {score_ela(img)[mask].mean():.4f} / 背景 {score_ela(img)[~mask].mean():.4f}"
          f" = {score_ela(img)[mask].mean() / score_ela(img)[~mask].mean():.2f} 倍")
    print("  → この『2〜3 倍』が、1 枚の閾値で成功例を作れてしまう数字である。")
    print("     以下はこの数字を信用せず、偽陽性率を固定して測り直す。")

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
    print("  → 内/外の比は 1 付近だが、画素数が多いので z は大きく出る。**z が大きいこと**")
    print("     **と検出できることは別**で、それを分けて言えるのが AUC のほうである。")

    print("\n=== 4-a. 効かなくなる境界:改竄領域の大きさ ===")
    header()
    size_rows = {}
    for size in (96, 64, 48, 32, 16):
        size_rows[size] = row(f"{size}x{size}"
                              f"({100.0 * size * size / (N * N):.2f} %)",
                              make_cases(n_img, size=size))
    print("  → 小さいほど落ちる。ELA と雑音は箱平均 / ブロックが 16 画素なので、")
    print("     16x16 の改竄は 1 ブロックに収まり、まわりと混ざって消える。")

    print("\n=== 4-b. 効かなくなる境界:あとから全体にかけた後処理 ===")
    header()
    post_rows = {}
    for label, post in (("後処理なし", None),
                        ("全体を q75 で再圧縮", ("recompress", 75)),
                        ("全体を q60 で再圧縮", ("recompress", 60)),
                        ("0.75 倍に縮小して戻す", ("resize", 0.75)),
                        ("ぼかし sigma=1.0", ("blur", 1.0))):
        post_rows[label] = row(label, make_cases(n_img, post=post))
    print("  → **フォレンジックは後処理で消える**。改竄者が保存し直すだけでよい。")
    print("     再圧縮は貼付部と背景の量子化履歴を同じものに塗り替え、縮小は 8x8 の")
    print("     格子そのものを壊す。どちらも『改竄を隠す意図』が無くても起きる。")

    print("\n=== 4-c. 効かなくなる境界:平坦な領域 ===")
    header()
    flat_rows = {"通常": row("通常(構造あり)", base),
                 "平坦": row("平坦な帯に貼る", make_cases(n_img, flat=True))}
    print("  → 平坦な所は圧縮しても誤差が出ず、雑音も乗らない。**手掛かりの素**が")
    print("     無いので、貼ってあっても言えることが無い。")

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
    a, t, f = auc_and_tpr(cm_scores, cm_labels, fpr_target=0.01)
    a0, t0f, f0 = auc_and_tpr(cm_scores, cm_labels, fpr_target=0.0)
    print(f"  改竄 {n_cm} 枚 / 清浄 {n_cm} 枚、スコア = 第 1 群の対応数(群が無ければ 0)")
    print(f"  AUC {a:.3f} / 清浄側の最大スコア {cm_scores[~cm_labels].max():.0f}"
          f" / 改竄側の中央値 {np.median(cm_scores[cm_labels]):.0f}")
    print(f"  偽陽性率 0 % での検出率 {t0f:.3f}(清浄 {n_cm} 枚では 1 % は刻めない ——")
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
    print(f"  最良は ELA(AUC {res_pos['ELA'][0]:.3f}、偽陽性率 1 % での検出率"
          f" {res_pos['ELA'][1]:.3f})。ただしこれは")
    print("  『背景が JPEG・貼付素材が別品質・後処理なし・領域 64x64』という、")
    print("  検出側にいちばん都合のよい条件での数字である。上の 4-b のとおり、")
    print(f"  全体を q60 で再圧縮しただけで ELA は AUC {post_rows['全体を q60 で再圧縮']['ELA'][0]:.3f} まで落ちる。")
    print("  **ゼロ点と後処理を置かずに『検出できた』と書くのは、この差を隠すこと**")
    print("  **に等しい**。")

    # ---- 自己検査(速さは assert しない)------------------------------------
    # (1) 測り方に偏りが無い:乱数検出器は改竄ありでもゼロ点でも 0.5 付近
    assert abs(res_pos["乱数"][0] - 0.5) < 0.01, res_pos["乱数"]
    assert abs(res_null["乱数"][0] - 0.5) < 0.01, res_null["乱数"]
    # (2) ゼロ点はどの検出器でも 0.5 付近(改竄が無いのだから当たってはいけない)
    for name, _ in DETECTORS:
        assert abs(res_null[name][0] - 0.5) < 0.10, (name, res_null[name])
    # (3) 効いている検出器は零点を上回る
    assert res_pos["ELA"][0] > 0.80, res_pos["ELA"]
    assert res_pos["雑音 σ"][0] > 0.65, res_pos["雑音 σ"]
    # (4) op の argmin 読み出しは、再保存した画像では定数地図 = ちょうど 0.5
    assert abs(res_pos["ゴースト(op の argmin)"][0] - 0.5) < 1e-9, \
        res_pos["ゴースト(op の argmin)"]
    q = F.jpeg_ghost_quality(F.jpeg_ghost_map(build_case(0)[0], GHOST_QS, block=BLOCK),
                             GHOST_QS)
    assert np.unique(q).size == 1, f"再保存後も定数でない: {np.unique(q)}"
    # (5) 大きさを下げると落ちる(単調とまでは言わない。端どうしを比べる)
    assert size_rows[16]["ELA"][0] < size_rows[96]["ELA"][0], (
        size_rows[16]["ELA"], size_rows[96]["ELA"])
    # (6) 後処理で落ちる —— これがこの PoC のいちばんの主張
    assert post_rows["全体を q60 で再圧縮"]["ELA"][0] < post_rows["後処理なし"]["ELA"][0] - 0.10
    assert post_rows["0.75 倍に縮小して戻す"]["ELA"][0] < post_rows["後処理なし"]["ELA"][0] - 0.10
    # (7) 平坦な帯では落ちる
    assert flat_rows["平坦"]["ELA"][0] < flat_rows["通常"]["ELA"][0]
    # (8) 8 画素格子:差が 8 の倍数のときだけ言い当てる(再保存なし)
    im_a, _ = build_case(0, src=(40, 40), dst=(96, 96), save_q=None)
    im_b, _ = build_case(0, src=(40, 40), dst=(99, 99), save_q=None)
    qa = F.jpeg_ghost_quality(F.jpeg_ghost_map(im_a, GHOST_QS, block=BLOCK), GHOST_QS)
    qb = F.jpeg_ghost_quality(F.jpeg_ghost_map(im_b, GHOST_QS, block=BLOCK), GHOST_QS)
    assert int(_mode(qa[104:152, 104:152])) == 60
    assert int(_mode(qb[107:155, 107:155])) == max(GHOST_QS)
    # (9) ROC の実装が端で正しい:完全分離は 1.0、逆向きは 0.0
    lab = np.r_[np.ones(50, bool), np.zeros(50, bool)]
    assert auc_and_tpr(np.r_[np.ones(50), np.zeros(50)], lab)[0] == 1.0
    assert auc_and_tpr(np.r_[np.zeros(50), np.ones(50)], lab)[0] == 0.0
    assert auc_and_tpr(np.zeros(100), lab)[0] == 0.5          # 全同点 = 0.5
    # (10) コピー&ムーブは清浄画像で群を作らない(偽陽性 0)
    assert cm_scores[~cm_labels].max() == 0.0, cm_scores[~cm_labels]
    assert a > 0.9, a
    print("\nPASS")


if __name__ == "__main__":
    main()
