"""事例: 平歯車(スパーギア)の歯数をジオメトリから逆計測する (metrology).

工場の受入検査では、CAD 図面が無い実物の歯車から「歯数 N」を数え直す必要がある。歯数は
歯車の最も基本的な諸元(モジュール・伝達比を決める)で、1 枚でも数え間違えると噛み合わない。
ここでは歯車そのものを ``sdf_ops`` の CSG(構成的立体幾何)で手続き的に組む —— ハブ円板を
球SDF(``sphere_sdf``)∩ z 方向スラブ箱(``box_sdf``)で作り、N 本の歯を **半径方向に向けた
箱**(座標を回してから ``box_sdf``)として円周上に配置し ``sdf_union`` で融合する。歯数の逆計測は
歯先の半径 ``r_sample`` に沿って占有を角度サンプルし、連続する「歯の弧」の数(角度ラン)を
数える計測学的手法。決定的(RNG は種固定)・ネット不要・新規ファイルは本 .py のみ。

検証(GT): 復元歯数が真値 N と厳密一致するか。
  * ハブ半径 R_disc < r_sample < 歯先半径 R_tip となる歯先帯では占有は歯のある角度だけ True。
    その角度ラン数 = 歯数。N=12 と N=20 の 2 種で測り、どちらも厳密一致(ハードコード否定)。
  * 計測学らしさ: サンプル点に種固定のジッタ(角度/半径)を載せても歯数は不変(ノイズ頑健)。
  beat-null: 歯を外した **ツルツル円板**(``with_teeth=False``)を同じ半径で測ると弧は 0 本。
  さらに **誤った半径** で測ると誤計数する —— ハブ内側(r<R_disc)は全周占有で 1 本、歯先の外
  (r>R_tip)は 0 本。「歯車=N / 円板 null=0 / 誤半径=1 or 0」で判別的に歯車の歯数を同定する。
"""
import numpy as np
import sdf_ops  # grid_coords / sphere_sdf / box_sdf / sdf_union / sdf_intersect(CSG op)

# ── 歯車の諸元(world 単位・すべて mid-z=0 の平面で意味を持つ)───────────────
R_DISC = 0.35      # ハブ(根元)円板の半径 = 歯溝の底(root circle)
R_C = 0.42         # 歯(箱)の半径方向中心
HR = 0.11          # 歯の半径方向の半長 → 歯は半径 [0.31, 0.53] を占める
R_TIP = R_C + HR   # 歯先円半径 = 0.53
HZ = 0.06          # 歯車の半厚(z)
R_SAMPLE = 0.44    # 計測リング半径(R_DISC=0.35 < 0.44 < R_TIP=0.53 の歯先帯)
BIG = 2.0          # z スラブ箱の x,y 半辺(歯車全体を覆う)


def rotate_z(coords, theta):
    """座標を z 軸まわりに -theta 回転(剛体変換 = numpy)。歯を半径方向へ向けるための前処理。"""
    ct, st = np.cos(theta), np.sin(theta)
    x, y, z = coords[..., 0], coords[..., 1], coords[..., 2]
    return np.stack([ct * x + st * y, -st * x + ct * y, z], axis=-1)


def tooth_sdf(coords, theta, tw):
    """角度 theta を向いた 1 本の歯(半径方向の箱)の SDF。座標を回してから軸平行 box_sdf。"""
    rc = rotate_z(coords, theta)                       # 歯のローカル系へ(半径方向 = +x)
    return sdf_ops.box_sdf(rc, (R_C, 0.0, 0.0), (HR, tw, HZ))


def gear_sdf(coords, n_teeth, with_teeth=True):
    """平歯車の符号付き距離場を CSG で組む: ハブ円板 ∪ (N 本の半径方向の歯)。

    ハブ円板 = 球SDF(半径 R_DISC)∩ z スラブ箱(半厚 HZ)。mid-z=0 断面はちょうど半径
    R_DISC の円になる。歯は歯溝底 R_DISC の内側(0.31)まで食い込ませてハブと連結させる。"""
    disc = sdf_ops.sdf_intersect(
        sdf_ops.sphere_sdf(coords, (0.0, 0.0, 0.0), R_DISC),   # 球
        sdf_ops.box_sdf(coords, (0.0, 0.0, 0.0), (BIG, BIG, HZ)),  # z スラブ
    )
    sdf = disc
    if with_teeth:
        # 歯の接線半幅 tw を「歯がピッチ(2π/N)の約 50% を占める」ように決める。
        tw = np.pi * R_SAMPLE / (2.0 * n_teeth)        # 歯先帯での角半幅 ≈ π/(2N)
        for k in range(n_teeth):
            theta = 2.0 * np.pi * k / n_teeth
            sdf = sdf_ops.sdf_union(sdf, tooth_sdf(coords, theta, tw))
    return sdf


def count_angular_runs(occ):
    """円周上の bool 列で、連続する True の弧(角度ラン)の本数を数える計測学ルーチン。

    立ち上がり(False→True)の回数 = 連続弧の本数。全 False=0 本、全 True=1 本(円環は
    途切れない)。歯車なら歯の本数に一致する。"""
    if not occ.any():
        return 0
    if occ.all():
        return 1
    prev = np.roll(occ, 1)                              # 円環シフト(ラップを正しく扱う)
    return int(np.count_nonzero(occ & ~prev))           # 立ち上がりエッジ数 = 弧の本数


def ring_occupancy(n_teeth, r, M=720, jitter=0.0, seed=0, with_teeth=True):
    """半径 r のリングを M 点で角度サンプルし、歯車 SDF の占有(sdf<0)を返す。

    jitter>0 で各サンプル点の角度(rad)と半径に種固定 Gaussian ノイズを載せる(計測ノイズ模擬)。"""
    rng = np.random.RandomState(seed)
    ang = np.linspace(0.0, 2.0 * np.pi, M, endpoint=False)
    if jitter > 0.0:
        ang = ang + rng.normal(0.0, jitter, M)          # 角度ジッタ(rad)
        r = r + rng.normal(0.0, jitter * 0.01, M)        # 半径ジッタ(小さめ)
    ring = np.stack([r * np.cos(ang), r * np.sin(ang), np.zeros(M)], axis=-1)  # (M,3) @ mid-z
    return gear_sdf(ring, n_teeth, with_teeth=with_teeth) < 0.0


# ── 1) 歯数の逆計測: N=12 と N=20 の 2 種(ジッタ有りでも不変)────────────────
results = {}
for N in (12, 20):
    occ_clean = ring_occupancy(N, R_SAMPLE)                       # ノイズ無し
    occ_noisy = ring_occupancy(N, R_SAMPLE, jitter=np.radians(0.20), seed=N)  # 0.2度ジッタ
    n_clean = count_angular_runs(occ_clean)
    n_noisy = count_angular_runs(occ_noisy)
    duty = float(occ_clean.mean())                               # 歯先帯の占有率 ≈ 0.5(50% duty)
    results[N] = (n_clean, n_noisy, duty)
    print(f"N={N:2d}: 復元歯数(clean)={n_clean:2d}  (jitter 0.2度)={n_noisy:2d}  占有率={duty:.3f}")

# ── 2) beat-null(A): 歯を外したツルツル円板を同じ半径で測る → 弧 0 本 ────────
null_disc = count_angular_runs(ring_occupancy(12, R_SAMPLE, with_teeth=False))
print(f"null 円板(歯なし)を r={R_SAMPLE} で計測 : {null_disc} 本")

# ── 3) beat-null(B): 誤った半径で測ると誤計数する(半径感度)───────────────
wrong_inside = count_angular_runs(ring_occupancy(12, 0.20))       # ハブ内側 → 全周占有 = 1
wrong_outside = count_angular_runs(ring_occupancy(12, 0.62))      # 歯先の外 → 空 = 0
print(f"誤半径: 内側 r=0.20 → {wrong_inside} 本 / 外側 r=0.62 → {wrong_outside} 本(いずれも != 12)")

# ── 4) 参考: 密グリッドで歯車を占有化し体積/厚みを報告(形が本当に板状の歯車か)──
coords, _ = sdf_ops.grid_coords(((-0.6, 0.6), (-0.6, 0.6), (-0.1, 0.1)), (200, 200, 20))
occ_vol = gear_sdf(coords, 12) < 0.0
ext = np.ptp(np.argwhere(occ_vol), axis=0) + 1                    # (x,y,z) voxel 範囲
print(f"密グリッド占有(N=12): voxels={int(occ_vol.sum())}  範囲(x,y,z)={ext.tolist()} = 薄い円板状")

# ═══ GT 検証(厳密一致 + null との判別)═══════════════════════════════════════
for N in (12, 20):
    n_clean, n_noisy, duty = results[N]
    # (1) 復元歯数が真値 N と厳密一致(ノイズ有無どちらも)
    assert n_clean == N, f"歯数の復元が真値と不一致: N={N} 復元={n_clean}"
    assert n_noisy == N, f"ジッタで歯数がずれた(計測が頑健でない): N={N} 復元={n_noisy}"
    # 歯先帯は約 50% duty(歯と歯溝がほぼ半々)
    assert 0.40 < duty < 0.60, f"歯先帯の占有率が 0.5 付近でない: {duty:.3f}"
# (2) beat-null: ツルツル円板は歯先帯で弧 0 本(歯車 N > 円板 0 で判別的)
assert null_disc == 0, f"歯なし円板が弧を持ってしまった: {null_disc}"
assert results[12][0] > null_disc and results[20][0] > null_disc, "歯車が null 円板を上回らない"
# (3) 誤半径は N を復元しない(半径感度): 内側=1・外側=0
assert wrong_inside == 1, f"ハブ内側で全周占有(1 本)にならない: {wrong_inside}"
assert wrong_outside == 0, f"歯先の外で空(0 本)にならない: {wrong_outside}"
assert wrong_inside != 12 and wrong_outside != 12, "誤半径なのに真値 12 を復元してしまった"
# (4) 形が薄い円板状の歯車か(z 厚み < x,y 径)
assert ext[2] < ext[0] and ext[2] < ext[1], f"板状の歯車になっていない: 範囲 {ext.tolist()}"

print(f"PASS: 歯先帯 r={R_SAMPLE} の角度ランから歯数 N=12→{results[12][0]}・N=20→{results[20][0]} を"
      f"厳密復元(0.2度ジッタでも不変)。歯なし円板 null={null_disc} 本・誤半径 内{wrong_inside}/外"
      f"{wrong_outside} 本で判別的(占有率 {results[12][2]:.2f}=50% duty の平歯車)")
