---
id: what-a-picture-cannot-check
title: 絵では確かめられないもの(積分器の次数・リアプノフ指数・分岐・相関次元・極小曲面)
title_en: What a picture cannot check (integrator order, Lyapunov spectrum, bifurcations, correlation dimension, minimal surfaces)
category: 測る
ops: [ode_flow_states, ode_vector_field_grid, dynsys_poincare_section, dynsys_lyapunov_spectrum, dynsys_bifurcation_map, dynsys_correlation_dimension, minimal_surface, minimal_surface_bend, gyroid_isosurface, gyroid_solid_mask, curve3d_tube_mesh]
examples: [poc_what_a_picture_cannot_check]
version: 0.2.4
---

# 絵では確かめられないもの(積分器の次数・リアプノフ指数・分岐・相関次元・極小曲面)

## できること

力学系(軌道・ベクトル場・ポアンカレ断面・リアプノフ指数・分岐図・相関次元)と極小曲面(カテノイド・ヘリコイド・エンネパー・シェルク・ジャイロイド)を作り、**恒等式と定義だけで採点します**。軌道は管メッシュにして立体で見られます。

★**この族は「見て分かる」が一切効きません。** ローレンツ・アトラクタの図は積分器が 1 次でも 4 次でも蝶に見え、極小曲面の図は平均曲率が 0 でなくてもきれいな曲面に見えます。ですから採点は全部絵の外から取ります(実測):

- ★**行列指数関数** —— 線形系 `x' = Ax` の厳密解は `expm(At)x₀`。刻みを半分にすると RK4 の誤差は**比 16.0 / 16.0 / 16.0**(4 次)、対照群のオイラー法は 2.08 / 2.04 / 2.02(1 次)。同じ `dt = 0.01` で 2.02e-02 対 3.33e-10 と桁が違います。**次数そのもの**を測るので「それらしい軌道」では通りません。
- ★★**トレース恒等式** —— リアプノフ指数の**和**は接流のトレースの時間平均に等しく、ローレンツでは厳密に `−(σ+1+β) = −13.666667`。実測 −13.666664(差 2.57e-06)。指数を出す手続き(接流 + QR 分解)とはまったく独立な恒等式なので、片方が壊れれば一致しません。λ₁ = 0.9142(公表値 0.906)、λ₂ = −0.008(理論 0)、保存系の対照群(調和振動子)は和 4.87e-15。
- ★**厳密な分岐点** —— ロジスティック写像の周期倍分岐は `r = 3` と `r = 1+√6` が厳密値で、実測 2.999401 / 3.449260。ファイゲンバウム定数は δ = 4.7485(文献値 4.6692)。
- ★★**残差を隠しません** —— 分岐点での収束は幾何的でなく**代数的**なので、有限の burn-in では分岐点が必ず少し手前に見えます。したがって門は「誤差が小さい」ではなく **「burn-in を伸ばすと置いていった分だけ縮む」**で置きました: burn 2,000 → 20,000 で誤差が **10.9 倍縮む** —— 残差の正体が写像でなく測り方であることの証拠はそれです。
- ★★**相関次元の偏りは、正体を探し当ててから書きました** —— 円 1.0061・カントール 0.6408(真値 log2/log3 = 0.6309)は合いますが、平面は 1.8789(真値 2)と低く出ます。最初に疑った「点数が足りない」は**外れ**でした(400 → 3,000 点で 1.8825 / 1.8789 / 1.8709 と、むしろ下がる)。正体は**べき乗則を見る半径の窓**で、既定は対距離の 1〜25 パーセンタイル —— 有界な集合ではその上端が境界に当たり、相関和が飽和して傾きが寝ます。窓を小さい `r` 側に寄せると 1.887 → 1.947 → 2.050 と真値に寄ります。**答えが要るときは `r_lo` / `r_hi` を明示し、窓と一緒に数を報告してください。**
- ★★**場の発散と渦度を測るのは PIV 族の既存 op です** —— `ode_vector_field_grid` は `flow2d`((2, H, W) の (dy, dx))を返すので、既存 `piv_divergence` / `piv_vorticity` / `piv_flow_magnitude` がそのまま食います。線形系では発散が厳密に `tr(A)`、渦度が `A₁₀ − A₀₁` で、4 通りすべて 1e-6 未満。ローレンツの xy 断面は `−σ−1 = −11.000000`。あちらはこの族の実装を何も知らないので、独立した採点者になります。
- ★**トーラスの解析解** —— 円を中心線にした管は体積 `2π²Rr²`・表面積 `4π²Rr` が解析解で、既存 `mesh_volume` / `mesh_area` が比 0.997 / 0.999。掃くのは**平行移動フレーム**で、まっすぐな区間を含む曲線でも半径が 0.150000000000 で崩れません(フレネ枠は直線部で法線が定義できず、変曲点で従法線が反転して管がねじれます)。
- ★★**極小曲面は定義そのものが門になります** —— 平均曲率 `H` が至るところ 0 という定義を、**作り方を知らない既存 `vertex_curvature`** が採点します。カテノイド・ヘリコイド・エンネパー・シェルクの `|H|` 中央値は 0.00002〜0.00014 で、対照群の単位球は 1.00004・半径 1 の円柱は 0.50000 —— 門が素通しでないことの証拠です。
- ★**ガウス曲率の一致は必要条件にすぎません** —— カテノイドとヘリコイドは等長なのでガウス曲率 `K` が一致します(中央値 −0.617 / −0.641)が、`K` が一致しても極小とは限りません。門にするのは `H` のほうです。等長な曲げの族は面積 17.6738〜17.6756 で不変。
- ★**ジャイロイドは節面近似であることを明記します** —— `level = 0` で場は体心反転に対し奇なので体積比は対称性からちょうど 1/2(実測 0.499928 / 0.499981 / 0.499991、格子に依らない)。ただし Schoen のジャイロイドは `H = 0` で、**節面近似には残差が残ります**(`|H|` / 主曲率スケール = 0.1250)。足場と絵として使うもので、極小性の主張ではありません。

## What it does

Integrate named dynamical systems (Lorenz, Rossler, harmonic, arbitrary linear `A`), sample their fields, take Poincare sections, compute Lyapunov spectra, bifurcation maps and correlation dimensions; build minimal surfaces (catenoid, helicoid, Enneper, Scherk, gyroid) and sweep a curve into a tube mesh — and score all of it with identities and definitions rather than by eye, because a Lorenz plot looks the same whether the integrator is 1st or 4th order and a surface looks smooth whether or not its mean curvature vanishes. RK4's error falls by exactly 16 per halving against `expm(At)x0` (Euler, the control, falls by 2); the *sum* of the Lyapunov exponents equals the trace identity `-(sigma+1+beta)` to 2.6e-06, independently of the tangent-flow/QR procedure that produced them; the logistic period-doubling points are the exact 3 and `1+sqrt(6)`, and the residual is attributed — the gate is not "the error is small" but "lengthening the burn-in shrinks it by 10.9x", because convergence at a bifurcation is algebraic; the correlation-dimension bias on a bounded set is traced to the **radius window**, not the sample count (400 to 3,000 points does not move it; narrowing `r_lo`/`r_hi` moves 1.887 to 2.050); the field's divergence equals `tr(A)` and its vorticity `A10 - A01` as measured by the **existing PIV ops**, which know nothing about this family; a tube swept along a circle is a torus whose analytic volume `2*pi^2*R*r^2` and area `4*pi^2*R*r` the existing `mesh_volume` / `mesh_area` confirm to 0.3 %; and the minimal surfaces have `|H|` medians of 1e-4 against controls of 1.00004 (unit sphere) and 0.50000 (unit cylinder), with the gyroid's nodal-approximation residual reported rather than hidden.

## 向くところ / 向かないところ

**向く**: 数値解法の**次数を実証する**(教材・検証レポート)。カオス系の指標(最大指数・次元・分岐)を根拠つきで出す。制御・振動の線形系の位相図と発散・渦度を既存 PIV op で測る。軌道や曲線を管メッシュにして 3-D で見せる・印刷する。極小曲面を構造の下地にする(膜構造・格子・TPMS の足場)。ジャイロイドの固体マスクを 3-D プリント用のスキャフォールドにする(`gyroid_solid_mask` は numpy だけで動きます)。

**向かない**: **系は族名か係数配列で受けます** —— `callable` を引数に取りません(型付き台帳は入力を sort で登録し、連鎖ファザーがデータから引数を組むので callable は載りません)。任意の常微分方程式を渡す口ではないので、独自の系は `DYNSYS_SYSTEMS` に足す側の仕事です。リアプノフ指数は**接流の解ける系**(解析的なヤコビアンを持つ 4 族)だけで、写像の指数や遅延埋め込みからの推定は入りません。分岐図はロジスティック・正弦・テントの 1 次元写像だけです。相関次元は `max_points` に間引くので(対の数が二乗で増える)、**答えが要るときは半径の窓を明示**してください —— 上の「できること」のとおり既定の窓は有界集合で低く出ます。`gyroid_isosurface`(メッシュ形)は **scikit-image が要ります**(固体形 `gyroid_solid_mask` は要りません) —— 引数で mesh か voxel が変わる関数には宣言 out 型を 1 つ与えられないので、**別の op に分けてあります**。極小曲面は**閉形式の 4 族 + ジャイロイド**で、任意の境界に張るプラトー問題は解きません。管メッシュは**自己交差を検出しません**(曲率半径より太い管を作れば管は自分を貫きます)。

## 最初の 1 本

```python
import numpy as np
import fullseye as fs

# 積分器の次数を実証する(厳密解は expm(At)x0)
A, x0, T = np.array([0.0, 1.0, -1.0, 0.0]), np.array([1.0, 0.0]), 4.0
exact = np.array([np.cos(T), -np.sin(T)])
for dt in (0.04, 0.02, 0.01):
    st = fs.ode_flow_states("linear", A, x0, T, dt, "rk4")
    end = np.array([st["x0"][-1], st["x1"][-1]])
    print("dt = %.3f  誤差 %.3e" % (dt, np.linalg.norm(end - exact)))   # 刻み半分で 1/16

# リアプノフ指数の和はトレース恒等式に一致する(出し方と独立)
lam = fs.dynsys_lyapunov_spectrum("lorenz", t_end=120.0, dt=0.004, burn_in=20.0)
print("Sum lambda = %.6f / -(sigma+1+beta) = %.6f" % (lam.sum(), -(10.0 + 1.0 + 8.0 / 3.0)))

# 「これは極小曲面だ」を、作り方を知らない op が採点する
V, F = fs.ledger.minimal_surface("catenoid", nu=90, nv=140, extent=1.2)
H = np.abs(np.asarray(fs.ledger.vertex_curvature((V, F))))
print("|H| 中央値 %.5f(対照群の単位球は 1.0)" % np.median(H[np.isfinite(H)]))
```

## 裏づけ

- op: `ode_flow_states` / `ode_vector_field_grid` / `dynsys_poincare_section` / `dynsys_lyapunov_spectrum` / `dynsys_bifurcation_map` / `dynsys_correlation_dimension` / `minimal_surface` / `minimal_surface_bend` / `gyroid_isosurface` / `gyroid_solid_mask` / `curve3d_tube_mesh`
- 例: [`poc_what_a_picture_cannot_check`](../../examples/poc_what_a_picture_cannot_check.py)
- 既存 op と組む: `piv_divergence` / `piv_vorticity` / `piv_flow_magnitude`(場を測る)・`vertex_curvature` と `principal_curvatures`(極小性を採点)・`mesh_volume` と `mesh_area`(トーラスの解析解)・`fractal_dimension`(箱数え = 相関次元と独立の測り方)
- 先行: E. N. Lorenz, "Deterministic nonperiodic flow", *J. Atmos. Sci.* 20 (1963); O. E. Rössler, "An equation for continuous chaos", *Phys. Lett. A* 57 (1976); M. J. Feigenbaum, "Quantitative universality for a class of nonlinear transformations", *J. Stat. Phys.* 19 (1978); P. Grassberger と I. Procaccia, "Characterization of strange attractors", *Phys. Rev. Lett.* 50 (1983); G. Benettin ら, "Lyapunov characteristic exponents for smooth dynamical systems", *Meccanica* 15 (1980); A. H. Schoen, "Infinite periodic minimal surfaces without self-intersections", *NASA TN D-5541* (1970); H. A. Schwarz, *Gesammelte Mathematische Abhandlungen* (1890); W. Lorensen と H. Cline, "Marching cubes", *SIGGRAPH 1987*; R. L. Bishop, "There is more than one way to frame a curve", *Amer. Math. Monthly* 82 (1975)(平行移動フレーム)。
