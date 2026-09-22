---
id: complex-plane-fields
title: 複素平面を「面」で見る(位相彩色・吸引域・脱出時間・翼まわりの流れ)
title_en: Seeing the complex plane as an area (domain colouring, basins, escape time, flow)
category: 測る
ops: [cplx_plane_grid, cplx_rational_field, cplx_domain_colour, cplx_newton_basins, cplx_escape_time, mandelbrot_interior, potential_flow_joukowski, joukowski_circulation]
examples: [poc_complex_plane_fields]
version: 0.2.4
---

# 複素平面を「面」で見る(位相彩色・吸引域・脱出時間・翼まわりの流れ)

## できること

複素解析の図を描きます —— 有理関数の位相彩色、ニュートン法の吸引域、マンデルブロ/ジュリア集合の脱出時間、ジューコフスキー翼まわりのポテンシャル流。既存の複素解析 op が**閉曲線の上**(積分・巻き数・ローラン係数・等角写像)を扱うのに対して、この層は**領域の上**を扱います。

★**この種の図はきれいなので、合っているかを誰も確かめません。** ここでは1 枚ごとに「絵とは独立の真値」を当てて採点します(実測):

- **偏角の原理** —— 作った場を既存 op(`cplx_winding_number`)に数えさせると、零点 3 で +3、零点 2 極 1 で +1、極 2 で −2。窓の外の零点は数えません(対照群)。
- ★**絵そのものから定理が読めます** —— 位相彩色の**色相が回る回数**が零点の位数。場の値は一度も見ず、**画素の RGB だけ**から 1 / 2 / 3 / −2 を数えられます。
- ★★**Cayley (1879)** —— `z²−1` のニュートン吸引域は**2 つの半平面**という厳密解。512×512 = **262,144 画素すべてが一致**し、未収束は 0。3 次は Cayley が解けなかった側で、同じ格子で境界画素が **1,026 → 13,348(13 倍)** —— これが「フラクタルになった」の数値的な意味です。それでも**共役対称は厳密**(1 画素も外れない)。
- ★**閉形式の内部判定** —— 主カージオイドと周期 2 球は「固定点が吸引的」という式で**反復せずに**内側と言えます。その 85,624 画素は**反例 0 件**で残り、しかし実際に残った 95,078 画素の **90.1 %** でしかありません —— 下界であることまで数で出ます。
- **既存 op が真値** —— 翼まわりの場は翼の外で正則なので `cplx_cr_residual` が 2.06e-04。循環は経路に依らず(外周 −3.0263 / 内周 −3.0263、流束 1.3e-07)、後縁の速度が有限なのは**クッタ条件のおかげ**で、循環を 0 にすると発散します(対照群)。
- ★**揚力係数と薄翼理論の比は厳密に a/b** —— 迎角にも速さにもよらず、厚みの効果が 1 つの数に落ちます(実測 1.513 / 1.383 = 1.0940 = a/b)。

## What it does

Draw complex analysis as an area rather than a curve: the value field of a rational function, its domain colouring, Newton's basins, escape time, and potential flow past a Joukowski aerofoil. None of the pictures is judged by eye. The winding of the field is counted by this family's existing `cplx_winding_number` (+3, +1, -2 as the zeros and poles say); the hue winding in the *rendered image* recovers the order of a zero from pixels alone; Cayley's 1879 theorem gives the degree-2 basins in closed form and all 262,144 pixels agree; the main cardioid and period-2 bulb prove interiority without iterating (zero counterexamples, and honestly only 90.1 % of what actually stays); the flow field is holomorphic so `cplx_cr_residual` reads 2.06e-04; and the lift exceeds thin-aerofoil theory by exactly the thickness ratio a/b.

## 向くところ / 向かないところ

**向く**: 伝達関数の零点・極を**絵で**見る(制御・信号処理)。等角写像の教材。翼型の初期検討(非粘性・非圧縮の範囲)。反復法の収束域を見る。

**向かない**: 粘性・剥離・圧縮性は入っていません(ポテンシャル流なので**抗力は 0** = ダランベールのパラドックス)。脱出時間は倍精度なので深い拡大には耐えません。ニュートンの吸引域は境界がフラクタルなので、境界近くの 1 画素は**格子の細かさで答えが変わります**(変わらないのは対称性のほう)。

## 最初の 1 本

```python
import fullseye as fs

f = fs.ledger.cplx_rational_field([0.2 + 0.1j, -0.3 + 0.2j], [0.1 - 0.2j])
rgb = fs.ledger.cplx_domain_colour(f)          # 位相彩色
# 絵と独立に、同じ場から零点 − 極を数える(= +1)
ring = f[1, 1:-1]                               # 実際は輪郭を 1 周ぶん並べる
```

## 裏づけ

- op: `cplx_plane_grid` / `cplx_rational_field` / `cplx_domain_colour` / `cplx_newton_basins` / `cplx_escape_time` / `mandelbrot_interior` / `potential_flow_joukowski` / `joukowski_circulation`
- 例: [`poc_complex_plane_fields`](../../examples/poc_complex_plane_fields.py)
- 先行: A. Cayley, "The Newton-Fourier imaginary problem", *Amer. J. Math.* 2 (1879); N. Joukowsky (1910); M. Kutta (1902)。
