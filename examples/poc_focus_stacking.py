# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""深度合成 —— 焦点をずらした画像列から、全焦点画像と深度地図の二つを取り出す。

EXTEND: 実際の顕微鏡 Z スタックに差し替えるには、``focal_stack`` が返す画像列を
実測フレームに、``focus_mm`` をステージの Z 座標(mm)に置き換えるだけでよい。
以降の焦点評価・融合・評価はすべてそのまま動く。ただし実データでは三つが変わる:
(1) 真値が無いので「深度の誤差」は測れず、測れるのは繰り返し再現性だけになる
(標準片を一枚入れておくと段差の真値が手に入る)。(2) ステージの Z が等間隔とは
限らない —— エンコーダ値を読むこと。等間隔だと思い込むと深度が一次で歪む。
(3) 対物レンズを動かすと像倍率が変わる(焦点ブリージング)。数 % でも段差の
境界で数画素ずれ、それは全部ハローとして深度誤差に化ける。フレーム間で
位置合わせしてから積むこと。

この PoC が示すこと:

1. **真値を自分で作れる** —— 深度地図(傾いた面 + 段差 + なだらかな丘)と
   テクスチャから、錯乱円の式で深さに応じたぼけを掛けて画像列を合成する。
   錯乱円の直径は幾何光学の閉形式 ``c = f^2 / (N (z_f - f)) * |z - z_f| / z``
   (f = 焦点距離、N = F 値、z_f = 合焦距離、z = 被写体距離)。これを画素ピッチで
   割って画素数にする。この式は ``fullseye.ledger.defocus_blur`` の中身そのもので、
   PoC は式を写経せずその op を呼ぶ。
2. ★**絵と深度は別物** —— 全焦点画像は 35.89 dB(ゼロ点 = 中央の 1 枚 20.98 dB)
   まで行くのに、**同じ融合が出した深度**はテクスチャのある所で 0.42 mm ずれ、
   無テクスチャ領域では **掃引全域にほぼ一様な乱数**を返す。領域ごとに
   「その領域では一つの深度と答え続ける」ゼロ点と比べると、テクスチャのある所
   では 7.11 倍勝つのに、無テクスチャでは **0.13 倍 = ゼロ点に 8 倍負ける**。
   絵の PSNR だけ見ていると、この負けは一切見えない。
3. ★**信頼度の作り方を間違えると、嘘の上に嘘が乗る** —— 焦点評価のピーク突出度
   ``(最大 - 中央値) / 最大`` は、無テクスチャ領域で **0.9923** と、有テクスチャ
   領域の 0.9630 より**高く**出た。相対量は絶対水準がゼロ近傍では意味を失う。
   絶対値で見ると両者は 23600 倍離れており、そちらで棄却すると全体 RMS が
   1.505 -> 0.878 mm に下がる(有テクスチャ側の誤棄却 0.0 %)。
4. **フレームを細かくしても、ある所から良くならない** —— 5 / 9 / 17 / 33 枚で
   量子化下限は 0.72 -> 0.09 mm と 8 倍下がるのに、テクスチャのある所の RMS は
   0.76 -> 0.48 mm で止まる。9 枚から先の誤差は標本化ではなく焦点評価が持っている。

★ この PoC が出した道具の穴(op 本体は直していない。詳細は末尾の節を印字):

  (a) **per-pixel の焦点評価 op が公開 API に一つも無い**。``lightfield`` は
      持っているが private ヘルパで、しかも 4-D ライトフィールド経由でしか
      呼べない。``reconstruction.depth_from_focus`` は関数として実在するのに
      **どの台帳にも登録されていない**(``fs.op`` / ``fs.ledger`` / ``fs.<名前>``
      のどれからも到達不能)。
  (b) **2-D op 層(``fs.op``)の微分系はフレームごとに自分の最大値で割る**
      (``ops._norm``)。同じ被写体でもフレームごとに割る数が違うので、
      **スタックを跨いで比較できない**。この場面での係数の振れ幅は 1.41 倍、
      鏡面ハイライトを 3x3 px 足すと 1.88 倍まで開き、テクスチャのある所の
      RMS が 0.422 -> 0.508 mm に悪化した。例外は出ないし、API のどこにも
      「割った」と書かれない。
  (c) **唯一の非正規化な合焦指標 ``xcv2_lap_var`` は 1.0 で飽和する**
      (``min(1.0, 分散 * 20)``)。高コントラストの被写体を 15 枚掃引すると
      **15 枚すべてが厳密に 1.000000** で並び、順位がまったく付かない
      (クリップ前の分散なら最良は一意に決まる)。
  (d) **``defocus_blur`` に遮蔽が無い**。docstring は「手前の層から合成する」と
      書いてあるが、実装は層ごとの加重和で**深度の順序に依存しない**。奥の
      大きなぼけが手前の合焦面へ被り、境界から 30 px 内側まで縞のコントラストが
      戻らなかった(実光学では不透明な手前が奥を遮るので 0 でなければならない)。

  拒否の側は正しく働いた: ``csi_height_map`` は (Z, H, W) という**同じ形**の
  焦点評価スタックを渡しても、もっともらしい高さを返さず、何画素がどの検査で
  落ちたかを名指しして拒否する。形が同じでも別の問題だと門が知っている。
"""
from __future__ import annotations

import time

import numpy as np

import fullseye as fs

# ---------------------------------------------------------------------------
# 場面と真値
# ---------------------------------------------------------------------------
#: 画像の一辺 [px]。
SIZE = 160
#: 無テクスチャ(一様な明るさ)の正方形。焦点評価が意味を失う場所。
FLAT_BOX = (slice(100, 140), slice(20, 60))
#: 段差ブロック。手前へ跳ぶので、境界にハローが出る。
STEP_BOX = (slice(25, 80), slice(95, 145))


def ground_truth(size=SIZE, seed=7):
    """既知の深度地図 [mm] とテクスチャを作る。返りは ``(depth, texture)``。

    深度は三つの成分の和 —— 列方向に 196 から 204 mm へ傾いた面、なだらかな
    ガウス丘(4 mm ぶん手前へ)、そして 194.5 mm の段差ブロック。傾いた面だけ
    だと「どのノブでも死なない」場面になってしまうので、微分不能な段差と、
    微分可能だが曲率のある丘を必ず混ぜる。

    テクスチャは乱数だけにしない。乱数は全周波数・全方位に等しく energy を
    置くので、方位や周波数に依存する欠陥を隠してしまう。ここでは半径方向の
    チャープ(周波数が場所で変わる)と市松(軸に揃った矩形波)を混ぜ、
    そのうえで一箇所だけ**完全に一様**な正方形を置く。
    """
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)

    depth = 196.0 + 8.0 * (xx / (size - 1))
    depth -= 4.0 * np.exp(-(((xx - 45.0) ** 2 + (yy - 110.0) ** 2) / (2 * 28.0 ** 2)))
    depth[STEP_BOX] = 194.5

    r = np.hypot(xx - size / 2.0, yy - size / 2.0)
    chirp = 0.5 + 0.5 * np.cos(2 * np.pi * r ** 2 / 900.0)
    checker = ((xx // 8).astype(int) + (yy // 8).astype(int)) % 2
    grain = fs.op.gauss_filter(rng.random((size, size)), a=0.12)
    tex = 0.45 * chirp + 0.25 * checker + 0.30 * (grain - grain.min()) / np.ptp(grain)
    tex = 0.12 + 0.76 * (tex - tex.min()) / np.ptp(tex)
    tex[FLAT_BOX] = 0.5                                   # 無テクスチャ
    return depth, tex


def masks(depth):
    """評価を分けるための領域 —— 無テクスチャ / 段差帯 / それ以外。"""
    flat = np.zeros(depth.shape, bool)
    flat[FLAT_BOX] = True
    gy, gx = np.gradient(depth)
    edge = (np.abs(gy) + np.abs(gx)) > 0.5
    band = fs.op.dilation_circle(edge.astype(np.float64), a=0.6) > 0.5
    return flat, band, (~flat) & (~band)


CAMERA = fs.ledger.optical_camera(focal_mm=25.0, pixel_um=3.45,
                                  resolution=(SIZE, SIZE), working_distance_mm=200.0)


def focal_stack(tex, depth, focus_mm, f_number=5.6, layers=24):
    """焦点位置ごとに 1 枚ずつ、被写界深度のぼけを掛けた画像列を作る。"""
    return np.stack([fs.ledger.defocus_blur(tex, depth, CAMERA, f_number=f_number,
                                            focus_mm=float(f), layers=layers)
                     for f in focus_mm])


# ---------------------------------------------------------------------------
# 焦点評価関数
# ---------------------------------------------------------------------------
# 点ごとの微分は自前で書いている。fullseye の 2-D op(fs.op.laplace / sobel_amp)は
# 自分の最大値で割ってから返すので、フレームを跨いで比較できないため(穴 b)。
# 局所プーリングだけは fs.op.mean_image が尺度を保つのでそちらを使う(a=0.25 = 5x5)。
_POOL = 0.25


def _laplacian(v):
    return np.abs(-4.0 * v + np.roll(v, 1, 0) + np.roll(v, -1, 0)
                  + np.roll(v, 1, 1) + np.roll(v, -1, 1))


def fm_laplacian(v):
    """ラプラシアン分散(局所窓のラプラシアン二乗和)。"""
    return fs.op.mean_image(_laplacian(v) ** 2, a=_POOL)


def fm_tenengrad(v):
    """Tenengrad(局所窓の勾配エネルギー)。"""
    gy, gx = np.gradient(v)
    return fs.op.mean_image(gx * gx + gy * gy, a=_POOL)


def fm_local_variance(v):
    """局所分散 E[x^2] - E[x]^2。"""
    m = fs.op.mean_image(v, a=_POOL)
    return np.maximum(fs.op.mean_image(v * v, a=_POOL) - m * m, 0.0)


def fm_op_laplace(v):
    """``fs.op.laplace`` 経由(**フレームごとに正規化される**)。"""
    return fs.op.mean_image(fs.op.laplace(v) ** 2, a=_POOL)


def fm_op_sobel(v):
    """``fs.op.sobel_amp`` 経由(**フレームごとに正規化される**)。"""
    return fs.op.mean_image(fs.op.sobel_amp(v) ** 2, a=_POOL)


MEASURES = (("ラプラシアン分散", fm_laplacian),
            ("Tenengrad", fm_tenengrad),
            ("局所分散", fm_local_variance),
            ("fs.op.laplace", fm_op_laplace),
            ("fs.op.sobel_amp", fm_op_sobel))


def measure_stack(stack, fn):
    """画像列 -> 焦点評価の (Z, H, W) 立方体。"""
    return np.stack([fn(s) for s in stack])


def fuse(stack, fm, focus_mm):
    """画素ごとに評価が最大のフレームを採る。

    返りは ``(全焦点画像, 深度地図, 峰の高さ, 選ばれたフレーム番号)``。
    """
    k = fm.argmax(axis=0)
    return np.take_along_axis(stack, k[None], 0)[0], focus_mm[k], fm.max(axis=0), k


def rms(x):
    return float(np.sqrt(np.mean(np.asarray(x, float) ** 2)))


def psnr(a, b):
    return float(fs.ledger.psnr(np.clip(a, 0.0, 1.0), b, data_range=1.0))


# ---------------------------------------------------------------------------
def main():
    depth, tex = ground_truth()
    flat, band, plain = masks(depth)
    n_frames = 15
    focus_mm = np.linspace(depth.min(), depth.max(), n_frames)

    t0 = time.perf_counter()
    stack = focal_stack(tex, depth, focus_mm)
    t_stack = 1e3 * (time.perf_counter() - t0)

    print("=== 1. 真値と画像列 ===")
    print(f"  深度 {depth.min():.2f} .. {depth.max():.2f} mm / 画像 {SIZE}x{SIZE}"
          f" / フレーム {n_frames} 枚(間隔 {focus_mm[1] - focus_mm[0]:.3f} mm)")
    print(f"  カメラ 焦点距離 {CAMERA['focal_mm']:.0f} mm / F 5.6 / 画素 "
          f"{1e3 * CAMERA['pixel_mm']:.2f} um / 作動距離 {CAMERA['working_distance_mm']:.0f} mm")
    f, N, zf = CAMERA["focal_mm"], 5.6, 200.0
    for dz in (1.0, 4.0, 8.0):
        coc = (f * f / (N * (zf - f))) * dz / (zf + dz)
        print(f"  合焦距離 200 mm、そこから {dz:>4.1f} mm 外れた面の錯乱円 = {coc:.4f} mm"
              f" = {coc / CAMERA['pixel_mm']:>5.2f} px")
    print(f"  領域の内訳: 無テクスチャ {int(flat.sum())} px / 段差帯 {int(band.sum())} px"
          f" / テクスチャ有 {int(plain.sum())} px")

    print("\n=== 2. 全焦点画像 —— 絵としての忠実度 ===")
    fm0 = measure_stack(stack, fm_laplacian)
    fused, dmap, peak, kmap = fuse(stack, fm0, focus_mm)
    p_single = [psnr(s, tex) for s in stack]
    print(f"  {'手法':<28}{'PSNR [dB]':>12}")
    print(f"  {'融合(ラプラシアン分散)':<28}{psnr(fused, tex):>12.2f}")
    print(f"  {'ゼロ点: 中央のフレーム 1 枚':<28}{p_single[n_frames // 2]:>12.2f}")
    print(f"  {'ゼロ点: 全フレームの平均':<28}{psnr(stack.mean(axis=0), tex):>12.2f}")
    print(f"  {'参考: 単独で最良のフレーム':<28}{max(p_single):>12.2f}")
    print(f"  → ゼロ点比 {psnr(fused, tex) - p_single[n_frames // 2]:+.2f} dB。"
          "絵の側は文句なく効いている。")

    print("\n=== 3. 深度地図 —— 同じ融合が出した、もう一つの答え ===")
    err = dmap - depth
    null_const = float(depth.mean())
    print(f"  {'領域':<14}{'RMS [mm]':>10}{'偏り':>9}{'散らばり':>10}"
          f"{'ゼロ点RMS':>11}{'ゼロ点比':>10}")
    ratios = {}
    for label, m in (("全体", np.ones_like(flat)), ("テクスチャ有", plain),
                     ("段差帯", band), ("無テクスチャ", flat)):
        e = err[m]
        # ゼロ点 = 「その領域では一つの深度と答え続ける」。最良の定数はその領域の平均な
        # ので、ゼロ点の RMS はその領域の標準偏差そのもの。これが勝てて当然の下限。
        null_rms = float(depth[m].std())
        ratios[label] = null_rms / rms(e)
        print(f"  {label:<14}{rms(e):>10.3f}{e.mean():>9.3f}{e.std():>10.3f}"
              f"{null_rms:>11.3f}{ratios[label]:>10.2f}")
    print(f"  (全体のゼロ点は {null_const:.2f} mm と答え続ける定数。領域ごとの行では"
          "その領域の最良の定数を使っている)")
    print(f"  → 全体では {ratios['全体']:.2f} 倍にしかならない。PSNR の圧勝とは別の話。")
    print(f"     テクスチャのある所だけなら {ratios['テクスチャ有']:.2f} 倍、"
          f"無テクスチャでは {ratios['無テクスチャ']:.2f} 倍 —— **ゼロ点に負けている**。")

    print("\n=== 4. 無テクスチャ領域は何を返すか ===")
    hist = np.bincount(kmap[flat].ravel(), minlength=n_frames)
    print(f"  真値 {depth[flat].min():.2f} .. {depth[flat].max():.2f} mm /"
          f" 推定 平均 {dmap[flat].mean():.2f} 標準偏差 {dmap[flat].std():.2f} mm")
    print(f"  推定の範囲 {dmap[flat].min():.2f} .. {dmap[flat].max():.2f} mm"
          f"(= 掃引の端から端まで)")
    print(f"  選ばれたフレームの度数 {hist.tolist()}")
    print(f"  一様なら 1 枚あたり {int(flat.sum()) / n_frames:.0f} 画素。"
          "つまり答えは掃引全域にばらまかれた乱数で、値そのものに意味は無い。")
    prom = (fm0.max(axis=0) - np.median(fm0, axis=0)) / np.maximum(fm0.max(axis=0), 1e-30)
    print(f"  ★ 峰の突出度 (最大 - 中央値) / 最大 の中央値:"
          f" 有テクスチャ {np.median(prom[plain]):.4f} / 無テクスチャ {np.median(prom[flat]):.4f}")
    print("     無テクスチャのほうが**高い**。相対量は絶対水準がゼロ近傍では意味を失う。")
    print(f"  ★ 峰の絶対値の中央値: 有テクスチャ {np.median(peak[plain]):.3e} /"
          f" 無テクスチャ {np.median(peak[flat]):.3e}"
          f"(比 {np.median(peak[plain]) / np.median(peak[flat]):.0f} 倍)")
    keep = peak >= 0.02 * np.median(peak[plain])
    print(f"     絶対値で棄却すると 無テクスチャの {100 * (1 - keep[flat].mean()):.1f} % を棄却、"
          f"有テクスチャの {100 * (1 - keep[plain].mean()):.1f} % を誤棄却。")
    print(f"     残った画素の全体 RMS {rms(err[keep]):.3f} mm(棄却前 {rms(err):.3f} mm)。")

    print("\n=== 5. 焦点評価関数を比べる ===")
    print(f"  {'焦点評価':<18}{'全体RMS':>9}{'テクスチャ有':>12}{'段差帯':>9}"
          f"{'無テクスチャ σ':>14}{'AIF PSNR':>10}")
    per_measure = {}
    for label, fn in MEASURES:
        fm = measure_stack(stack, fn)
        fu, dm, _pk, _k = fuse(stack, fm, focus_mm)
        e = dm - depth
        per_measure[label] = (rms(e), rms(e[plain]), psnr(fu, tex))
        print(f"  {label:<18}{rms(e):>9.3f}{rms(e[plain]):>12.3f}{rms(e[band]):>9.3f}"
              f"{dm[flat].std():>14.3f}{psnr(fu, tex):>10.2f}")
    print("  → 段差帯ではラプラシアンが一番悪い(二階微分はハローを一番強く拾う)。")
    print(f"     無テクスチャの散らばりはどの評価でも 3.2-3.7 mm。掃引幅 "
          f"{focus_mm[-1] - focus_mm[0]:.2f} mm の一様分布なら σ = "
          f"{(focus_mm[-1] - focus_mm[0]) / np.sqrt(12):.2f} mm —— つまり誰も救えていない。")

    print("\n=== 6. ★ フレームごとの正規化という穴 ===")
    scale = [float(np.max(_laplacian(s))) for s in stack]
    print("  fs.op.laplace が内部で割る数(そのフレームの最大値):")
    print("   " + " ".join(f"{v:.3f}" for v in scale))
    print(f"  最大 / 最小 = {max(scale) / min(scale):.3f}。"
          "同じ被写体なのにフレームごとに物差しが変わる。")
    tex_hi = tex.copy()
    tex_hi[60:63, 60:63] = 1.0                       # 鏡面ハイライト 1 点(実機では普通にある)
    stack_hi = focal_stack(tex_hi, depth, focus_mm)
    scale_hi = [float(np.max(_laplacian(s))) for s in stack_hi]
    print(f"  鏡面ハイライトを 3x3 px 足すと 最大 / 最小 = {max(scale_hi) / min(scale_hi):.3f} まで開く。")
    print(f"  {'焦点評価':<18}{'テクスチャ有RMS':>15}")
    for label, fn in (("ラプラシアン分散", fm_laplacian), ("fs.op.laplace", fm_op_laplace)):
        fm = measure_stack(stack_hi, fn)
        _fu, dm, _pk, _k = fuse(stack_hi, fm, focus_mm)
        print(f"  {label:<18}{rms((dm - depth)[plain]):>15.3f}")
    print("  → 正規化した側だけが悪化する。例外は出ず、割ったことも API から見えない。")

    print("\n=== 7. ★ 唯一の非正規化な合焦指標は 1.0 で飽和する ===")
    sharp = 0.1 + 0.8 * (np.random.default_rng(3).random((SIZE, SIZE)) > 0.5)
    stack_hc = focal_stack(sharp, depth, focus_mm)
    af = np.array([float(fs.op.xcv2_lap_var(s)) for s in stack_hc])
    ref = np.array([float(np.var(-4.0 * s + np.roll(s, 1, 0) + np.roll(s, -1, 0)
                                 + np.roll(s, 1, 1) + np.roll(s, -1, 1))) for s in stack_hc])
    n_tied = int((af >= 1.0).sum())
    print("  高コントラストの被写体で 15 枚を掃引し、フレームごとの合焦指標を見る:")
    print(f"  {'合焦距離 [mm]':>14}{'xcv2_lap_var':>14}{'クリップ前の分散':>18}")
    for f_mm, v, rv in zip(focus_mm, af, ref):
        mark = "  <- 同点" if v >= 1.0 else ""
        print(f"  {f_mm:>14.2f}{v:>14.6f}{rv:>18.6f}{mark}")
    print(f"  → 15 枚のうち {n_tied} 枚が厳密に 1.000000 で並ぶ"
          "(``min(1.0, 分散 * 20)`` のクリップ)。")
    print(f"     クリップ前の分散なら最良は {focus_mm[int(np.argmax(ref))]:.2f} mm と一意に決まる。")
    print("     オートフォーカスで順位が要るのはまさに鮮鋭な側なので、そこで使えない。")

    print("\n=== 8. フレーム間隔を粗くすると ===")
    print(f"  {'枚数':>5}{'間隔 [mm]':>11}{'量子化下限':>12}{'テクスチャ有RMS':>15}"
          f"{'全体RMS':>10}{'AIF PSNR':>10}")
    for nf in (5, 9, 17, 33):
        fmm = np.linspace(depth.min(), depth.max(), nf)
        st = focal_stack(tex, depth, fmm)
        fu, dm, _pk, _k = fuse(st, measure_stack(st, fm_laplacian), fmm)
        e = dm - depth
        step = fmm[1] - fmm[0]
        print(f"  {nf:>5}{step:>11.3f}{step / np.sqrt(12):>12.3f}{rms(e[plain]):>15.3f}"
              f"{rms(e):>10.3f}{psnr(fu, tex):>10.2f}")
    print("  → 量子化下限は 8 倍下がるのに RMS は 9 枚から先ほぼ動かない。")
    print("     つまり残りは標本化ではなく、焦点評価そのものが持っている誤差。")

    print("\n=== 9. 雑音 ===")
    print(f"  {'雑音 σ':>8}{'テクスチャ有RMS':>15}{'全体RMS':>10}{'無テクスチャ σ':>15}{'AIF PSNR':>10}")
    for s in (0.0, 0.005, 0.02, 0.05):
        g = np.random.default_rng(11)
        st = stack if s == 0.0 else stack + g.normal(0.0, s, stack.shape)
        fu, dm, _pk, _k = fuse(st, measure_stack(st, fm_laplacian), focus_mm)
        e = dm - depth
        print(f"  {s:>8.3f}{rms(e[plain]):>15.3f}{rms(e):>10.3f}{dm[flat].std():>15.3f}"
              f"{psnr(fu, tex):>10.2f}")
    print("  → σ 0.02 までは深度がほとんど動かない(局所窓の平均が効く)。")
    print("     σ 0.05 で 4 倍に崩れる。絵の PSNR は同じところでもっと早く落ちている。")

    print("\n=== 10. 段差の境界 —— 手前のぼけが奥に被る ===")
    prof_h, prof_w = 64, 240
    xx = np.mgrid[0:prof_h, 0:prof_w][1].astype(np.float64)
    d2 = np.where(xx < prof_w / 2, 190.0, 220.0)
    t2 = 0.2 + 0.6 * (((xx // 4).astype(int)) % 2)
    cam2 = fs.ledger.optical_camera(focal_mm=25.0, pixel_um=3.45,
                                    resolution=(prof_w, prof_h), working_distance_mm=200.0)
    near = fs.ledger.defocus_blur(t2, d2, cam2, f_number=5.6, focus_mm=190.0, layers=2)
    print("  手前(190 mm)に合焦。手前側は境界からどこまで汚染されるか:")
    print(f"  {'境界からの距離 [px]':>20}{'縞の σ 実測':>14}{'理想':>8}")
    for dpx in (5, 15, 30, 60):
        sl = np.s_[:, max(0, 120 - dpx - 8):120 - dpx]
        print(f"  {dpx:>20d}{near[sl].std():>14.4f}{t2[sl].std():>8.4f}")
    print("  → 実光学では不透明な手前が奥を遮るので、手前側の汚染は 0 のはず。")
    print("     ``defocus_blur`` は層を深度順に合成せず加重和にしているので被る(穴 d)。")

    print("\n=== 11. 干渉の同型問題 —— 形が同じでも通してはいけない ===")
    try:
        fs.ledger.csi_height_map(fm0, z_step_um=float(focus_mm[1] - focus_mm[0]),
                                 z_start_um=float(focus_mm[0]), wavelength_um=100.0)
        print("  通ってしまった(想定外)")
    except ValueError as e:
        head = str(e).split(" — ")[0]
        print(f"  拒否: {head}")
        print("  → (Z, H, W) という形は焦点評価スタックと同じだが、コヒーレンス包絡線を")
        print("     持たないので拒否される。何画素がどの検査で落ちたかまで言う fail-closed。")

    print("\n=== 12. 速度(この機械での実測)===")
    t1 = time.perf_counter(); fmz = measure_stack(stack, fm_laplacian)
    t_fm = 1e3 * (time.perf_counter() - t1)
    t1 = time.perf_counter(); fuse(stack, fmz, focus_mm)
    t_fuse = 1e3 * (time.perf_counter() - t1)
    print(f"  画像列の合成(15 枚 x {SIZE}x{SIZE}、24 層){t_stack:>9.1f} ms"
          f"  ({t_stack / n_frames:.1f} ms/枚)")
    print(f"  焦点評価(15 枚 x {SIZE}x{SIZE}、5x5 窓)   {t_fm:>9.1f} ms")
    print(f"  融合 + 深度                              {t_fuse:>9.1f} ms")
    print("  → 律速は合成側(層ごとにガウスを 2 回掛ける)。評価と融合は 1 桁安い。")

    # ---- 自己検査(速さは assert しない)---------------------------------
    # 1. 絵は効いている
    assert psnr(fused, tex) > p_single[n_frames // 2] + 10.0, "全焦点画像がゼロ点に勝てていない"
    assert psnr(fused, tex) > psnr(stack.mean(axis=0), tex) + 10.0, "平均のゼロ点に勝てていない"
    # 2. 深度はテクスチャのある所でだけゼロ点に勝つ
    assert rms(err[plain]) < 0.5 * rms(depth - null_const), "有テクスチャでも定数に勝てていない"
    assert rms(err[flat]) > 2.0 * float(depth[flat].std()), \
        "無テクスチャで領域内定数のゼロ点に勝ってしまった —— 真値が漏れている疑い"
    # 3. 無テクスチャの答えは掃引全域にばらけている(= 乱数)
    assert np.ptp(dmap[flat]) > 0.9 * (focus_mm[-1] - focus_mm[0]), "無テクスチャの散らばりが小さすぎる"
    assert int((np.bincount(kmap[flat].ravel(), minlength=n_frames) > 0).sum()) == n_frames, \
        "無テクスチャで一部のフレームしか選ばれていない"
    # 4. 相対の突出度は無テクスチャで嘘をつき、絶対値は嘘をつかない
    assert np.median(prom[flat]) > np.median(prom[plain]), \
        "突出度が無テクスチャで下がった —— 穴 (3) の前提が変わっている"
    assert np.median(peak[plain]) > 100.0 * np.median(peak[flat]), "峰の絶対値が分離していない"
    assert rms(err[keep]) < rms(err), "絶対値で棄却しても改善しない"
    # 5. 段差帯はそれ以外より必ず悪い(ハローは消えない)
    assert rms(err[band]) > 2.0 * rms(err[plain]), "段差帯が悪化していない —— 段差が効いていない"
    # 6. 穴 (b): fs.op の微分はフレームごとに 1.0 へ正規化される
    for name in ("laplace", "sobel_amp"):
        assert abs(float(np.max(fs.apply(stack[0], name))) - 1.0) < 1e-12, \
            f"fs.op.{name} が最大 1.0 に正規化されていない —— 穴 (b) が直った?"
    assert max(scale) / min(scale) > 1.2, "正規化係数がフレーム間で振れていない"
    # 7. 穴 (c): 非正規化の合焦指標は 1.0 で飽和する
    assert n_tied >= 3, "xcv2_lap_var が飽和しない —— 穴 (c) が直った?"
    # 8. 穴 (a): per-pixel の焦点評価 op は公開 API に無い
    assert "depth_from_focus" not in fs.ledger and "depth_from_focus" not in fs.op, \
        "depth_from_focus が登録された —— 穴 (a) が直った?"
    # 9. 穴 (d): defocus_blur に遮蔽が無い(手前の合焦面が奥のぼけに汚される)
    assert near[:, 100:112].std() < 0.97 * t2[:, 100:112].std(), \
        "手前の合焦面が汚染されていない —— 穴 (d) が直った?"
    # 10. 形が同じでも csi_height_map は焦点評価スタックを拒否する
    try:
        fs.ledger.csi_height_map(fm0, z_step_um=float(focus_mm[1] - focus_mm[0]),
                                 z_start_um=float(focus_mm[0]), wavelength_um=100.0)
        raise AssertionError("csi_height_map が焦点評価スタックを通した")
    except ValueError:
        pass
    print("\nPASS")


if __name__ == "__main__":
    main()
