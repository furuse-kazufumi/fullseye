---
id: one-stroke-drawing
title: 写真を 1 本の線にする(点描 → 巡回路 → 回る円)
title_en: Turn a photograph into a single line (stipple, tour, rotating circles)
category: 描く
ops: [stipple_points_from_image, stipple_energy, stroke_tour_closed, mst_length, stroke_resample_closed, stroke_tone_error, contour_fourier_complex, contour_epicycle_chain, contour_fourier_truncation_energy]
examples: [poc_one_stroke_epicycles]
version: 0.2.3
---

# 写真を 1 本の線にする(点描 → 巡回路 → 回る円)

## できること

写真の**濃淡**を、紙から鉛筆を離さずに引ける**1 本の閉じた線**に変えます。濃いところで線が密になるので、離れて見ると元の絵の階調が戻ります。巡回路は閉じているので、そのまま**複素フーリエ級数**に載り、**回る円の連鎖**として描き直せます。出口は既存の G-code op なので、ペンプロッタで実際に引けます。自分の写真で走らせる口も付いています::

```bash
py -3.11 examples/poc_one_stroke_epicycles.py --image my_photo.jpg \
    --points 12000 --out out/mine
```

★**「絵が似ている」を人の目に任せません。** 各段が何を保って何を捨てたかを数で返します(北斎「神奈川沖浪裏」202×300、点 9,000 での実測):

- 点の密度が濃淡を追うこと —— ランプ画像で相関 **0.9946**。対照群の一様画像では点が等間隔に散る(最近傍距離の変動係数 0.13 対 0.37)。
- ★★**しかし相関だけでは指数が見えません。** 重みつき Lloyd が作るのは重心ボロノイで、最適な点密度は重み ρ に対し **√ρ** に比例します(Gersho の予想、2 次元で ρ^(d/(d+2)))。実測の指数は **0.61** —— 相関 0.99 でも密度は暗さに**比例していません**。重みを二乗して初めて 0.77 まで上がります。
- 巡回路の質 —— **閉じた巡回路は最小全域木より短くなれない**ので、その比で言います。実測 **1.146**(素朴に座標順で繋ぐと **41.4**)。2-opt は長さを単調に縮めます。
- 濃淡の再現 —— 相関 **0.984**。同じ本数のランダムな線を引いた対照群は **+0.013**。
- ★ペン幅は**閉形式で解けます**: 線が重ならない範囲で `インク率 ≈ 線長 × ペン幅 / 面積`。解いた 0.900 px でインク率は目標の **0.890 倍** —— 不足の 11 % が**線の重なりの量**そのものです(合併は和より小さいので、実測は必ず予言以下になります)。
- ★★**ナイキストを先に確かめます。** 等弧長の打ち直しは、標本間隔が線分より粗いと角を切って線そのものが短くなり、フーリエに載せる**前**に情報が落ちます。実測: 16,384 点(間隔 1.14 px)で長さ保持 **0.935**、32,768 点で **0.967**、65,536 点で **0.984** —— 誤差はきれいに **1/N** で落ちます(6.5 → 3.3 → 1.6 %)。線分の中央値は 1.57 px なので、間隔がそれを下回るまで増やす必要があります。
- ★★円の本数は**描く前に**決められます: 次数 K で打ち切った誤差はパーセバルにより「|k| > K の係数の二乗和」に厳密に等しいので、**K=16 で 95.9 %、K=64 で 99.0 %、K=600 で 99.97 %** と先に言えます(予言と実測の差は機械精度)。

## What it does

Turn the tone of a picture into a single closed line a pen could draw without lifting: points are placed by darkness (weighted Lloyd), ordered into a closed tour, resampled at equal arc length, and rewritten as a chain of rotating circles via the complex Fourier series. Nothing is judged by eye. The stipple is checked against a ramp (correlation 0.9946) with a flat image as the control — and the *exponent* is measured too, because a centroidal Voronoi tessellation puts density at sqrt(rho), not rho (Gersho): 0.61 measured, 0.77 with the weight squared. The tour is checked against the minimum spanning tree, which no closed tour can beat (1.146, against 41.4 for coordinate order); the tone is measured (0.984, against +0.013 for random points); the pen width that reproduces the mean tone is solved in closed form and falls 11 % short, which *is* the stroke overlap; the resampling is checked against Nyquist (the error falls as 1/N: 6.5, 3.3, 1.6 % of the stroke length); and Parseval turns the number of circles into a prediction made before the drawing exists.

## 向くところ / 向かないところ

**向く**: ペンプロッタ・レーザー・刺繍のように**線でしか描けない**機械への変換。形状記述(閉じた輪郭を少ない係数で表す)。様式化の効きを数で比べたいとき。

**向かない**: 点描は画素数 × 点数で効くので**大きな画像は遅い**(実測: 202×300・9,000 点で点描 101 秒)。巡回路は最近傍 + 2-opt で、**最適解ではありません**(下界との比で質を言うのはそのため)。色は扱いません。★**線画には向きません** —— 重心ボロノイは必ず画面全体を埋めるので、暗い画素が数 % しかない墨の線画では点の大半が白地に配られます。線画は細線化して線そのものを辿るべきで、それは別の道具です。

## 最初の 1 本

```python
import fullseye as fs

img = fs.read_image("photo.png")
pts = fs.ledger.stipple_points_from_image(img, 9000, gamma=1.6)  # 濃いところに点
tour = fs.ledger.stroke_tour_closed(pts)                          # 1 本の閉じた線
err = fs.ledger.stroke_tone_error(img, tour)                      # 何を保ったかを数で
print(err["corr"], err["length_px"])
```

## 裏づけ

- op: `stipple_points_from_image` / `stipple_energy` / `stroke_tour_closed` / `mst_length` / `stroke_resample_closed` / `stroke_tone_error` / `contour_fourier_complex` / `contour_epicycle_chain` / `contour_fourier_truncation_energy`
- 例: [`poc_one_stroke_epicycles`](../../examples/poc_one_stroke_epicycles.py)
- 先行研究: Kaplan & Bosch, "TSP Art", *Computational Aesthetics* (2005)。点密度の指数は A. Gersho, "Asymptotically optimal block quantization", *IEEE Trans. Inform. Theory* (1979)。
- 画像の出所: 葛飾北斎「神奈川沖浪裏」(富嶽三十六景、1830-32 年頃)。メトロポリタン美術館 Open Access が `isPublicDomain: true`(CC0)で公開している版(object 45434、画像 DP130155)を輝度化して 202×300 に縮めたもの。
