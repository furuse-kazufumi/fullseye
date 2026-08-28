"""事例: 校正済みステレオ対から異なる奥行きの平面パッチの奥行きを復元 (depth).

移動ロボットや3Dスキャナは、左右2台のカメラ(ステレオ)の見えのズレ(視差 disparity)から
シーンの奥行き(depth)を起こす。近い面ほど左右像でのズレが大きく、遠い面ほど小さい。
ここでは正対する(fronto-parallel)3枚のテクスチャ付きパッチを、既知の奥行き
(近 8m / 中 16m / 遠 32m)に置いた校正済みステレオ対を合成する。規約(stereo.py)は
「左像 列 c の特徴は右像 列 c-d に現れる(d>=0, 近い面ほど大)」なので、各パッチは奥行きに
応じた整数視差 d = focal*baseline/Z(近12 / 中6 / 遠3 px)だけ右像で左へずらして描く。
stereo.disparity_map で視差を推定し、stereo.depth_from_disparity で奥行きへ変換する。

検証(GT): 3枚のパッチは自分で既知の奥行きに置いたので真値がわかる。
  * パッチ内部(境界を block ぶん侵食し、窓が背景/オクルージョンに掛からない領域)で
    復元奥行きが各パッチの既知奥行きに一致する(相対誤差 < 5%)。
  * 近いパッチほど視差が大きい(near > mid > far)= 奥行きの単調順序が正しい。
  beat-null: 「全パッチ同一奥行き」の定数推定は、どのパッチも同時には当てられない。最も
  有利な単一定数(=真の奥行きの平均)を null に取っても、実 op のパッチ毎相対誤差はその
  null 誤差を桁で下回る(実誤差平均 < 5% × null 誤差平均)。視差ゼロ null は奥行き∞(全外れ)。
"""
import numpy as np
import stereo

RNG = np.random.default_rng(7)           # 決定的(テクスチャと計測ノイズの種)

# --- カメラ・シーンのパラメータ ---------------------------------------------
H, W = 180, 240                          # 画像サイズ [px]
FOCAL, BASELINE = 800.0, 0.12            # 焦点距離 [px] / 基線長 [m]
FB = FOCAL * BASELINE                     # f*B = 96 [px*m] → Z = FB / d
BLOCK, MAX_DISP = 7, 16                  # マッチング窓(奇数)/ 探索する最大視差
NOISE = 0.01                             # 左右独立のセンサノイズ(標準偏差, [0,1]スケール)
BG = 0.5                                 # 背景の一様輝度(テクスチャ無し=マッチ曖昧、内部のみ検証)

# 3枚のパッチ: (名前, 行範囲, 視差 d[px])。列範囲は全パッチ共通、行で分離(横ずらしで衝突しない)。
PX0, PX1 = 60, 180                        # 左像でのパッチ列範囲(全パッチ共通、幅120)
PATCHES = [
    ("near", (20, 60),  12),             # 近い → 視差 大 → Z = 96/12 =  8 m
    ("mid",  (80, 120),  6),             # 中   →            Z = 96/6  = 16 m
    ("far",  (140, 175),  3),            # 遠い → 視差 小 → Z = 96/3  = 32 m
]


def synth_stereo_pair():
    """既知視差の校正済みステレオ対 (left, right) を合成して返す。

    規約(stereo.py): 左像 列 c の特徴は右像 列 c-d に現れる(right[x] = left[x+d])。
    よって右像は各パッチのテクスチャを列方向へ d だけ左へずらして描く。
    """
    left = np.full((H, W), BG, np.float64)
    right = np.full((H, W), BG, np.float64)
    for _name, (y0, y1), d in PATCHES:
        tex = RNG.random((y1 - y0, PX1 - PX0))    # 高コントラストなランダムテクスチャ
        left[y0:y1, PX0:PX1] = tex                # 左像: そのまま配置
        right[y0:y1, PX0 - d:PX1 - d] = tex       # 右像: 列を d だけ左へずらして配置
    # 左右で独立のガウスノイズ(視差推定を「完全一致の当てっこ」でなく実測に近づける)
    left = left + RNG.normal(0.0, NOISE, left.shape)
    right = right + RNG.normal(0.0, NOISE, right.shape)
    return np.clip(left, 0.0, 1.0), np.clip(right, 0.0, 1.0)


# --- 1) 合成: 既知奥行きの3パッチを持つステレオ対 ---------------------------
left, right = synth_stereo_pair()

# --- 2) 視差推定(実 op)→ 奥行きへ変換 -------------------------------------
disp = stereo.disparity_map(left, right, max_disp=MAX_DISP, block=BLOCK, method="sad")
depth = stereo.depth_from_disparity(disp, focal=FOCAL, baseline=BASELINE)

# --- 3) 各パッチ内部で GT と突き合わせ ---------------------------------------
h = BLOCK // 2
z_true_list, z_real_list, d_true_list, d_real_list = [], [], [], []
print(f"f*B = {FB:.1f} px*m,  block={BLOCK},  max_disp={MAX_DISP},  noise sd={NOISE}")
print("パッチ  行範囲      既知Z[m]  真視差d  復元視差(中央値)  復元Z[m]  相対誤差")
for name, (y0, y1), d in PATCHES:
    # 内部 = 境界を block ぶん侵食(窓が背景/オクルージョンに掛からない領域だけ検証)
    iy0, iy1 = y0 + BLOCK, y1 - BLOCK
    ix0, ix1 = PX0 + BLOCK, PX1 - BLOCK
    d_med = float(np.median(disp[iy0:iy1, ix0:ix1]))
    z_med = float(np.median(depth[iy0:iy1, ix0:ix1]))
    z_true = FB / d
    rel = abs(z_med - z_true) / z_true
    z_true_list.append(z_true); z_real_list.append(z_med)
    d_true_list.append(float(d)); d_real_list.append(d_med)
    print(f"{name:5s}  [{y0:3d},{y1:3d})   {z_true:6.2f}    {d:5d}    {d_med:10.2f}      "
          f"{z_med:6.2f}   {rel*100:6.2f}%")

z_true_arr = np.array(z_true_list)
z_real_arr = np.array(z_real_list)
d_real_arr = np.array(d_real_list)
err_real = np.abs(z_real_arr - z_true_arr) / z_true_arr        # 実 op の相対誤差

# --- 4) beat-null: 全パッチ同一奥行きとみなす最も有利な単一定数 ---------------
z_null = float(z_true_arr.mean())                              # null: 真奥行きの平均(最良定数)
err_null = np.abs(z_null - z_true_arr) / z_true_arr
depth_zero_null = stereo.depth_from_disparity(np.zeros_like(disp),
                                              focal=FOCAL, baseline=BASELINE)
frac_inf_zero_null = float(np.isinf(depth_zero_null).mean())   # 視差ゼロ null は全画素∞
print(f"実 op   相対誤差: 各 {np.round(err_real*100, 2).tolist()} % / 平均 {err_real.mean()*100:.2f}%")
print(f"null(平均奥行き {z_null:.2f} m): 各 {np.round(err_null*100, 1).tolist()} % / 平均 {err_null.mean()*100:.1f}%")
print(f"null(視差ゼロ): 奥行き∞ の画素割合 {frac_inf_zero_null:.2f}(=全外れ)")

# ═══ GT 検証 ═══
# (a) 各パッチの復元奥行きが既知奥行きに一致(境界侵食した内部で相対誤差 < 5%)
assert err_real.max() < 0.05, f"あるパッチの奥行き誤差が大きすぎる: {err_real.tolist()}"
# (b) 近い→視差大 の単調(near > mid > far)。奥行きも単調増加(近→遠)
assert d_real_arr[0] > d_real_arr[1] > d_real_arr[2], f"視差の単調順序が崩れた: {d_real_arr.tolist()}"
assert np.all(z_real_arr[:-1] < z_real_arr[1:]), f"奥行きが単調増加でない: {z_real_arr.tolist()}"
# (c) beat-null: 実 op のパッチ毎誤差は、最良単一定数 null の誤差を桁で下回る
assert err_real.mean() < 0.05 * err_null.mean(), \
    f"実 op が最良定数 null を大きく下回っていない: {err_real.mean():.4f} vs {err_null.mean():.4f}"
assert err_null.max() > 0.05, "null が実は判別的でない(定数で全パッチを当てられてしまう)"
assert frac_inf_zero_null == 1.0, f"視差ゼロ null が∞にならない: {frac_inf_zero_null}"

print(f"PASS: 3パッチの奥行きを視差から復元(近{z_real_arr[0]:.1f}/中{z_real_arr[1]:.1f}/遠"
      f"{z_real_arr[2]:.1f} m, 相対誤差 max {err_real.max()*100:.2f}% < 5%)。視差順序 "
      f"near>mid>far 正、実誤差平均 {err_real.mean()*100:.2f}% << 最良定数null {err_null.mean()*100:.1f}%")
