# -*- coding: utf-8 -*-
"""事例: 反射・回転対称性の検出 (Fullseye symmetry3d)。

実問題: 3D スキャンした部品が「左右対称か」「軸まわりに N 回対称か」を数値で判定したい。
対称性が分かると (1) 欠損した半分を鏡映で補完 (2) 姿勢の正準化 (3) 左右差=欠陥の検査 に使える。

ここでは合成点群で 2 つを検証する:
  A. x=0 平面について鏡映対称な点群 → detect_reflection_symmetry が対称面(法線=x軸)を当てる
  B. z軸まわり 4 回対称(C4)な点群 → detect_rotational_symmetry が位数 4 を返す
いずれも「対称スコア = 鏡映/回転した点群と元の chamfer 距離 / 点間隔」で採点(小さいほど対称)。
"""
import numpy as np
import symmetry3d as S

rng = np.random.default_rng(1)

# ============================================================
# A. 反射対称: x=0 平面について鏡映対称な点群を作る
# ============================================================
# まず「片側だけ」のいびつな塊(blob)を作る。これ自体は無対称。
blob = rng.uniform([-1.5, -1.0, -1.0], [1.5, 1.0, 1.0], size=(300, 3))
# x を反転したコピーと合わせると x=0 平面について厳密に鏡映対称になる。
# (y=0 / z=0 平面については無対称のまま=区別できるように)
mirror = blob.copy()
mirror[:, 0] = -mirror[:, 0]
sym_cloud = np.vstack([blob, mirror])           # x=0 で鏡映対称

refl = S.detect_reflection_symmetry(sym_cloud)
axis_alignment = abs(np.dot(refl["plane_normal"], [1.0, 0.0, 0.0]))  # 1 に近いほど x軸

print("[A] 反射対称の検出")
print(f"  best score              = {refl['score']:.4f}  (小さいほど対称)")
print(f"  detected plane_normal   = {np.round(refl['plane_normal'], 3)}")
print(f"  |normal . x-axis|       = {axis_alignment:.4f}  (1.0=x軸に一致)")
print(f"  all_scores (3 主軸平面) = {[round(s, 3) for s in refl['all_scores']]}")

# 対比: 鏡映相手のいない片側 blob だけ → 対称スコアは悪化するはず
asym = S.detect_reflection_symmetry(blob)
print(f"  片側のみ(無対称)score   = {asym['score']:.4f}  (対称版より大)")

# --- GT 検証 (A) ---
assert refl["score"] < 0.6, refl["score"]                # 鏡映対称 → 低スコア
assert axis_alignment > 0.95, axis_alignment             # 対称面の法線が x軸に一致
assert asym["score"] > 2.0 * refl["score"], (asym["score"], refl["score"])  # 無対称は明確に悪い

# ============================================================
# B. 回転対称: z軸まわり C4 (90度回転で不変) の点群を作る
# ============================================================
# z軸から離れた 1 個のいびつな房を作り、90度ずつ 4 回コピー → C4 対称。
patch = rng.uniform([0.8, -0.3, -1.0], [1.8, 0.3, 1.0], size=(150, 3))
copies = []
for a in (0.0, np.pi / 2, np.pi, 3 * np.pi / 2):
    c, s = np.cos(a), np.sin(a)
    R = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    copies.append(patch @ R.T)
c4_cloud = np.vstack(copies)                    # z軸まわり 4 回対称

# 「3回か? 4回か? 5回か? 6回か?」を問う → C4 なので位数 4 だけが低スコアで勝つ。
rot = S.detect_rotational_symmetry(c4_cloud, orders=(3, 4, 5, 6))
z_alignment = abs(rot["axis_dir"][2])           # 回転軸が z 軸か

print("\n[B] 回転対称の検出 (候補 order = 3,4,5,6)")
print(f"  detected order          = {rot['order']}")
print(f"  best score              = {rot['score']:.4f}")
print(f"  axis_dir                = {np.round(rot['axis_dir'], 3)}  |z成分|={z_alignment:.3f}")
# order ごとの最良スコア(全 PCA 軸中の最小)を並べて C4 らしさを見る
by_order = {}
for _ai, o, sc in rot["table"]:
    by_order[o] = min(sc, by_order.get(o, np.inf))
print("  order別 最良score       =", {o: round(v, 3) for o, v in sorted(by_order.items())})

# --- GT 検証 (B) ---
assert rot["order"] == 4, rot["order"]                   # C4 → 位数 4 が選ばれる
assert rot["score"] < 0.15, rot["score"]                 # 90度回転で(ほぼ)不変
assert z_alignment > 0.95, rot["axis_dir"]               # 回転軸が z 軸
assert by_order[4] < 0.3 * by_order[3], (by_order[4], by_order[3])   # 4回はOK, 3回はNG
assert by_order[4] < 0.3 * by_order[5], (by_order[4], by_order[5])   # 5回もNG
# 補足(honest): C4 は C2 を含むので、order=2 を候補に入れれば 2 も低スコアになる。
# ここでは「3/4/5/6 のどれか」を問い、生成折り数 4 が正しく当たることを示している。

print("\nALL GT CHECKS PASSED")