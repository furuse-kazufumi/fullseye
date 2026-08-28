"""事例: ダウンロードした実測3Dスキャンを衝突判定用の多段LOD(詳細度)へ間引く (mesh_process).

ゲームの遠景描画やロボットの衝突判定では、フル解像度メッシュ(Stanford Bunny = 6.9万面)を
そのまま使うと重い。QEM(二次誤差計量, Garland-Heckbert)エッジ collapse で面数を
50% / 25% / 10% へ段階的に落とし、各段で「形が保たれているか」を実測する。データは
opt-in ダウンローダで取得した実物スキャン(bunny、無ければ dragon)を使う。

未ダウンロード時はグレースフルに SKIP して exit 0 する(検証環境はデータ無しで走るため必須)。
取得するには:  py -3.11 imgevolve.py samples download bunny --yes

検証(GT): 面数は各ターゲットへ単調減少し(実測 34725->17361->6944、ほぼ厳密)、形は
面積重みで撒いた表面サンプル同士の距離で測る。
  * QEM の表面 Hausdorff / 対角長 < 0.04 = worst-case の乖離が狭い帯に収まる。
  * QEM の Chamfer(平均誤差)/ 対角長 は面数を 1/10 に落としても ~0.0024 でほぼ一定。
    面数が 10 倍減っても平均誤差が保たれる = LOD の要件そのもの。
判別性(honest disclosure): この密で均一な bunny では、同じ面数の「一様ランダム面ドロップ」は
残った三角形が原表面の"上"に載る(幾何ずれ 0、穴だけ)ため worst-case の Hausdorff では
QEM と拮抗する — QEM はここで圧勝しない。意味のある差は平均誤差に出る:ランダムドロップは
被覆の穴で Chamfer が QEM の 1.3 倍に悪化し、面数を減らすほど差が開く(A5)。加えて、面数は
同じでも「形状を捨てる」ナル(片側だけ残す偏りドロップ)は Hausdorff が QEM の ~30 倍に
破綻し、形状保存の帯(A3)を明確に踏み外す(A6)。=「面数を合わせる」だけでは GT を
満たせず、表面を実際に保つ QEM が要る、を判別的に示す。
"""
import sys
import numpy as np

import sample_data
import mesh
import meshrepair
import metrics3d


def sample_surface(V, F, n, rng):
    """三角形の面積に比例して表面から n 点を一様サンプル(面積重み + 重心座標)。

    大きい面ほど多くの点が落ちるので、間引きで三角形の大きさが不均一になっても
    表面全体を偏りなく代表できる。Hausdorff/Chamfer の GT 計測に使う。
    """
    tri = V[F]                                   # (nf,3,3)
    e1 = tri[:, 1] - tri[:, 0]
    e2 = tri[:, 2] - tri[:, 0]
    area = 0.5 * np.linalg.norm(np.cross(e1, e2), axis=1)
    p = area / area.sum()
    fi = rng.choice(len(F), size=n, p=p)         # 面積重みで面を選ぶ
    u = rng.random(n)
    v = rng.random(n)
    over = u + v > 1.0                           # 三角形の外に出た点は折り返す
    u[over] = 1.0 - u[over]
    v[over] = 1.0 - v[over]
    a = V[F[fi, 0]]
    b = V[F[fi, 1]]
    c = V[F[fi, 2]]
    return a + u[:, None] * (b - a) + v[:, None] * (c - a)


# --- 0) データ取得(opt-in ダウンローダ)。無ければ SKIP して exit 0 -------------
path = sample_data.local_path("bunny") or sample_data.local_path("dragon")
if path is None:
    print("SKIP: ダウンロード済みメッシュが無い(bunny も dragon も未取得)。")
    print("  先にサンプルを取得してから再実行してください:")
    print("    py -3.11 imgevolve.py samples download bunny --yes")
    print("  (fullseye の samples フローで data_dir に .ply が置かれる)")
    sys.exit(0)                                  # 検証環境はデータ無しで走る = 正常終了が必須

V, F = mesh.read_mesh(path)                      # (nv,3) float64, (nf,3) int64
diag = float(np.linalg.norm(V.max(0) - V.min(0)))   # 物体の対角長(正規化スケール)
N_SAMPLES = 40000
rng = np.random.default_rng(0)                   # 全 RNG を固定(決定的)
S0 = sample_surface(V, F, N_SAMPLES, rng)        # 原メッシュ(GT)の表面サンプル
print(f"メッシュ         : {path}")
print(f"原メッシュ       : V{V.shape} F{F.shape}  対角長 {diag:.4f}")

# --- 1) QEM で 50% / 25% / 10% の LOD を作り、面数と表面誤差を測る ----------------
fracs = [0.50, 0.25, 0.10]
nf_lods, haus_lods, cham_lods = [], [], []
for frac in fracs:
    target = int(frac * len(F))
    Vd, Fd = meshrepair.decimate_qem(V, F, target)          # ★ 実 op: QEM 間引き
    Sd = sample_surface(Vd, Fd, N_SAMPLES, rng)
    h = metrics3d.hausdorff_distance(S0, Sd) / diag         # worst-case / 対角長
    c = metrics3d.chamfer_distance(S0, Sd) / diag           # 平均誤差 / 対角長
    nf_lods.append(len(Fd)); haus_lods.append(h); cham_lods.append(c)
    print(f"LOD {int(frac*100):>2}%  target F{target:>6}  実 F{len(Fd):>6}  "
          f"Hausdorff/diag {h:.4f}  Chamfer/diag {c:.5f}")

# --- 2) null-1: 同じ面数の「一様ランダム面ドロップ」(最小 LOD で比較)-------------
# 残る三角形は原表面の上に載るので worst-case Hausdorff では QEM と拮抗する。
# 差が出るのは平均誤差 = 被覆の穴。面数を減らすほど Chamfer が悪化する。
n_small = nf_lods[-1]
keep = rng.choice(len(F), size=n_small, replace=False)
S_rand = sample_surface(V, F[keep], N_SAMPLES, rng)
cham_rand = metrics3d.chamfer_distance(S0, S_rand) / diag
haus_rand = metrics3d.hausdorff_distance(S0, S_rand) / diag
print(f"null ランダムドロップ (F{n_small}): Chamfer/diag {cham_rand:.5f}  "
      f"Hausdorff/diag {haus_rand:.4f}  (Hausdorff は QEM と拮抗 = 圧勝せず, honest)")

# --- 3) null-2: 面数は同じでも「形状を捨てる」偏りドロップ(片側だけ残す)---------
# 面数を合わせただけの「ゴミ間引き」。半分の形状が欠けるので Hausdorff が破綻する。
cy = V[F].mean(1)[:, 1]                           # 各面重心の y
crop = np.argsort(cy)[:n_small]                  # y 下側だけ n_small 面残す(上半分を捨てる)
S_crop = sample_surface(V, F[crop], N_SAMPLES, rng)
haus_crop = metrics3d.hausdorff_distance(S0, S_crop) / diag
print(f"null 偏りクロップ   (F{n_small}): Hausdorff/diag {haus_crop:.4f}  "
      f"(QEM 最小LOD の {haus_crop/haus_lods[-1]:.0f} 倍 = 形状保存の帯を踏み外す)")

# --- 4) GT 検証 ------------------------------------------------------------------
# A1: 面数が各ターゲットへ単調減少(「無変更で返す」ナルを弾く)
assert nf_lods[0] > nf_lods[1] > nf_lods[2], f"面数が単調減少していない: {nf_lods}"
# A2: 各 LOD がターゲット面数の近くに着地(±10%)。過少/過多の破綻を弾く
for frac, nf in zip(fracs, nf_lods):
    target = int(frac * len(F))
    assert abs(nf / target - 1.0) < 0.10, f"LOD {frac}: 面数 {nf} が target {target} から外れすぎ"
# A3: 形状保存(worst-case)— どの LOD も Hausdorff/diag が狭い帯に収まる
assert max(haus_lods) < 0.04, f"QEM の worst-case 乖離が大きすぎる: {haus_lods}"
# A4: 形状保存(平均)— 面数を 1/10 にしても Chamfer/diag がほぼ一定 = LOD の要件
assert max(cham_lods) < 0.0035, f"QEM の平均誤差が LOD で保たれていない: {cham_lods}"
# A5: beat-null-1 — 最小 LOD の平均誤差が同面数ランダムドロップに明確に勝つ(被覆の差)
assert cham_lods[-1] < 0.85 * cham_rand, \
    f"QEM の Chamfer {cham_lods[-1]:.5f} がランダムドロップ {cham_rand:.5f} に勝てていない"
# A6: beat-null-2 — 面数を合わせただけの形状破壊ナルは Hausdorff の帯を大きく踏み外す
assert haus_crop > 10.0 * haus_lods[-1], \
    f"偏りクロップ {haus_crop:.4f} が QEM {haus_lods[-1]:.4f} を十分に上回らない"

print(f"PASS: QEM LOD 50/25/10% = F{nf_lods}(単調減少), Hausdorff/diag<={max(haus_lods):.4f}<0.04, "
      f"Chamfer/diag<={max(cham_lods):.5f}<0.0035(1/10面でも平均誤差一定); "
      f"最小LODの平均誤差 {cham_lods[-1]:.5f} < ランダムドロップ {cham_rand:.5f}(x{cham_rand/cham_lods[-1]:.2f}), "
      f"形状破壊クロップは Hausdorff {haus_crop:.3f} = QEM の {haus_crop/haus_lods[-1]:.0f} 倍で帯外")
