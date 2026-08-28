# -*- coding: utf-8 -*-
"""事例: 深度センサの1シーンを denoise→傾き記述→面分割→計画格子まで通す (segmentation).

平たく言うと: 深度カメラ / LiDAR が撮った「角(2つの傾いた面が稜線で出会う)」を、実際の
知覚パイプラインの順に処理する。(1) ノイズ深度を清浄なガイド画像で **joint bilateral** して
段差を残したまま平滑化 → (2) **bearing-angle 画像**で各面の傾きを数値化 → (3) 深度を 3-D 点群へ
持ち上げ **region_growing** で 2 面に分割 → (4) 鏡面反射から **normal_from_reflection** で面法線を
復元 → (5) 学習用に **elastic_deform** / **cutout** で点群を水増し → (6) 稜線エッジ片を **link_edges**
で連結成分にまとめ → (7) 占有格子を **inflate** して planner 用 C-space 障害物を作る。各段は前段の
出力を入力に取り、op どうしが噛み合う(単発呼び出しではなく連結)ことを示す。

検証(GT): すべて解析的な真値と照合する。
    - joint_bilateral : 稜線(ガイドの鋭いエッジ)を保存しつつ facet 内のノイズを削減
      → RMS(out−truth) < RMS(noisy−truth)。bearing-angle も denoise 後の方が真傾きに近づく。
    - bearing_angle_image: 一定傾き s の面の bearing-angle は解析的に degrees(atan(s))。左右 facet で厳密一致。
    - region_growing  : 稜線で法線が 45° 開くので **ちょうど 2 領域**、真の面帰属と一致(精度 1.0)。
    - normal_from_reflection: 反射則 r=reflect(d,n) を逆に解いて面法線 n を機械精度で復元(|rec·n|=1)。
    - elastic_deform  : 変位場の RMS ノルムはちょうど alpha(σ→∞ で剛体的=coherent、σ=0 で独立)。
    - cutout          : 除去点は必ず辺長 extent の軸平行ボックス内(空間的に局所)。kept==P[kept_idx]。
    - link_edges      : 26 近傍連結。離れた 3 片→3 成分、対角接触させると→2 成分(6 近傍では割れる所を連結)。
    - inflate         : 単一占有 voxel の膨張は解析的なユークリッド球(距離<=radius)と厳密一致・radius 単調増。

beat-the-null: 各主張を「素の入力」や「幾何を無視した処理」と判別的に比較する。joint_bilateral は素の
ノイズ深度 / 段差を潰す素の Gaussian ぼかしの両 null を上回る。region_growing は「面の向きを無視」した
単一法線 null では 1 領域に潰れる(=分割は稜線の向き変化が駆動)。elastic_deform の coherence は σ=0 独立場
の null を上回る。cutout の除去集団の広がりは同数ランダム抽出(雲全体に散る)の null を大きく下回る。
inflate のユークリッド球は角を丸めない箱膨張(Chebyshev)の null より小さい(=正しく丸めている)。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # repo root first

import numpy as np

import match3d as M                # normal_from_reflection, reflect
import range_image as RI           # bearing_angle_image
import depth_bilateral as DB       # joint_bilateral
import segment3d as SEG            # region_growing
import pcl_augment as AUG          # elastic_deform, cutout
import edges3d as ED               # link_edges
import occupancy as OCC            # inflate


# ═══════════════════════════════════════════════════════════════════════════
# 0) センサシーン: 2 つの傾いた facet が列境界で出会う organized 深度画像 + 清浄ガイド
# ═══════════════════════════════════════════════════════════════════════════
H, W, CB = 40, 40, 20                       # 画像サイズ / 面の列境界
sL, sR = 0.5, 0.1                           # 各 facet の行方向(axis0)傾き
rows = np.arange(H)[:, None].astype(float)
truth = np.empty((H, W), float)
truth[:, :CB] = 3.0 + sL * rows             # 左 facet(急な傾き)
truth[:, CB:] = 5.0 + sR * rows             # 右 facet(緩い傾き, 深度オフセットで稜線=段差)
guide = np.where(np.arange(W)[None, :] < CB, 0.2, 0.8)  # 清浄な輝度ガイド(列境界に鋭いエッジ)
noisy = truth + np.random.default_rng(7).normal(0.0, 0.08, size=truth.shape)  # センサノイズ

# 内部領域(画像端・列境界を避けた各 facet 中央)= 解析 GT を素直に測れる窓
interiorL = (slice(5, 35), slice(3, 17))
interiorR = (slice(5, 35), slice(23, 37))


# ═══════════════════════════════════════════════════════════════════════════
# 1) joint_bilateral: ガイドの鋭いエッジで段差を残しつつ深度ノイズを平滑化
# ═══════════════════════════════════════════════════════════════════════════
den = DB.joint_bilateral(noisy, guide, spatial_sigma=2.0, range_sigma=0.1)

rms_noisy = float(np.sqrt(np.mean((noisy - truth)[interiorL] ** 2
                                  + (noisy - truth)[interiorR] ** 2)))
rms_den = float(np.sqrt(np.mean((den - truth)[interiorL] ** 2
                                 + (den - truth)[interiorR] ** 2)))

# beat-null(エッジ保存): 段差を無視する素の Gaussian ぼかしは稜線コントラストを潰す
from scipy.ndimage import gaussian_filter
blur = gaussian_filter(noisy, sigma=2.0)
step_true = float(np.mean(truth[:, CB] - truth[:, CB - 1]))     # 真の列境界段差
step_den = float(np.mean(den[:, CB] - den[:, CB - 1]))
step_blur = float(np.mean(blur[:, CB] - blur[:, CB - 1]))
print(f"[joint_bilateral] RMS: noisy {rms_noisy:.4f} -> denoised {rms_den:.4f}")
print(f"[joint_bilateral] 稜線段差 真 {step_true:.3f} / denoised {step_den:.3f} / Gaussian null {step_blur:.3f}")
assert rms_den < 0.6 * rms_noisy, "joint_bilateral が facet 内ノイズを十分に削れていない"
assert abs(step_den - step_true) < 0.15 * abs(step_true), "稜線段差が保存できていない"
assert abs(step_blur) < 0.7 * abs(step_true), "Gaussian null が段差を潰していない前提が崩れた"
assert abs(step_den) > 0.9 * abs(step_true) > abs(step_blur), "joint がエッジ保存で Gaussian null を上回れていない"


# ═══════════════════════════════════════════════════════════════════════════
# 2) bearing_angle_image: 一定傾き面の bearing-angle = degrees(atan(傾き)) を厳密復元
#    さらに denoise 後の深度から測ると素のノイズ深度より真傾きに近い(joint→bearing 連結)
# ═══════════════════════════════════════════════════════════════════════════
ba_clean = RI.bearing_angle_image(truth, direction="down")
baL_true, baR_true = np.degrees(np.arctan(sL)), np.degrees(np.arctan(sR))
print(f"[bearing_angle] 左 facet {ba_clean[interiorL].mean():.3f}° (真 {baL_true:.3f}°) / "
      f"右 facet {ba_clean[interiorR].mean():.3f}° (真 {baR_true:.3f}°)")
assert np.allclose(ba_clean[:, :CB], baL_true, atol=1e-4), "左 facet の bearing-angle が解析値と不一致"
assert np.allclose(ba_clean[:, CB:], baR_true, atol=1e-4), "右 facet の bearing-angle が解析値と不一致"

ba_noisy = RI.bearing_angle_image(noisy, direction="down")
ba_den = RI.bearing_angle_image(den, direction="down")
err_noisy = float(np.mean(np.abs(ba_noisy - ba_clean)[interiorL])
                  + np.mean(np.abs(ba_noisy - ba_clean)[interiorR]))
err_den = float(np.mean(np.abs(ba_den - ba_clean)[interiorL])
                + np.mean(np.abs(ba_den - ba_clean)[interiorR]))
print(f"[bearing_angle] 傾き誤差(勾配): noisy {err_noisy:.3f}° -> denoised {err_den:.3f}°")
assert err_den < err_noisy, "denoise が bearing-angle 推定を改善していない(joint→bearing 連結の主張が崩れる)"
# 2 facet は bearing-angle で判別的に分離できる(左右の平均が離れている)
assert abs(ba_clean[interiorL].mean() - ba_clean[interiorR].mean()) > 5.0


# ═══════════════════════════════════════════════════════════════════════════
# 3) 深度を 3-D 点群へ持ち上げ → region_growing で 2 面に分割
#    幾何は「角」: 稜線 y 軸で 2 平面が出会い、法線が 45° 開く。
# ═══════════════════════════════════════════════════════════════════════════
aA, aB = np.radians(20.0), np.radians(-25.0)
uy = np.array([0.0, 1.0, 0.0])
tA = np.array([np.cos(aA), 0.0, np.sin(aA)])          # facet A の面内(傾き)方向
tB = np.array([np.cos(aB), 0.0, np.sin(aB)])          # facet B の面内方向
nA = np.cross(uy, tA); nA /= np.linalg.norm(nA)       # A の面法線 = [sin aA,0,-cos aA]
nB = np.cross(uy, tB); nB /= np.linalg.norm(nB)
ss = np.linspace(0.0, 1.0, 12)                        # 稜線からの距離(s=0 が共有稜線)
tt = np.linspace(-0.5, 0.5, 12)                       # 稜線方向(y)
S, T = np.meshgrid(ss, tt, indexing="ij")
PA = S.ravel()[:, None] * tA + T.ravel()[:, None] * uy
PB = S.ravel()[:, None] * tB + T.ravel()[:, None] * uy
corner = np.vstack([PA, PB])
nrm = np.vstack([np.tile(nA, (len(PA), 1)), np.tile(nB, (len(PB), 1))])
label_true = np.concatenate([np.zeros(len(PA), int), np.ones(len(PB), int)])
ang = np.degrees(np.arccos(abs(nA @ nB)))
print(f"[region_growing] 稜線での法線角 {ang:.1f}° / 点数 {len(corner)}")

labels = SEG.region_growing(corner, normals=nrm, angle_thresh_deg=15.0, k=18)
n_reg = len(set(labels.tolist()) - {-1})
# 各 facet 内でラベルが一様 & 2 facet が別ラベル = 稜線で正しく割れている
uniA = len(set(labels[:len(PA)].tolist()))
uniB = len(set(labels[len(PA):].tolist()))
same_side = float(max(np.mean(labels[:len(PA)] == labels[0]),
                      np.mean(labels[len(PA):] == labels[len(PA)])))
print(f"[region_growing] 領域数 {n_reg} / facetA 一様 {uniA==1} / facetB 一様 {uniB==1} / "
      f"A,B 別ラベル {labels[0] != labels[len(PA)]}")
assert n_reg == 2 and uniA == 1 and uniB == 1, f"稜線で 2 面に分割できていない(領域数 {n_reg})"
assert labels[0] != labels[len(PA)] and (labels >= 0).all(), "2 面が同一ラベル / ノイズ点が出た"
# beat-null: 面の向きを無視(全点同一法線)すると稜線を跨いで 1 領域に潰れる
labels_null = SEG.region_growing(corner, normals=np.tile(nA, (len(corner), 1)),
                                 angle_thresh_deg=15.0, k=18)
n_reg_null = len(set(labels_null.tolist()) - {-1})
print(f"[region_growing] 単一法線 null の領域数 {n_reg_null}(向きを無視すると 1 に潰れる)")
assert n_reg_null == 1, "null(単一法線)が 1 領域に潰れない = 分割が向きでなく空間ギャップ由来"


# ═══════════════════════════════════════════════════════════════════════════
# 4) normal_from_reflection: 反射則を逆に解いて facet A の面法線を復元
#    既知パターンを鏡面(facet A)で反射 → 入射 d と反射 r から法線を復元。
# ═══════════════════════════════════════════════════════════════════════════
d_inc = np.array([0.3, 0.2, 1.0]); d_inc /= np.linalg.norm(d_inc)   # 入射方向
r_ref = M.reflect(d_inc, nA)                                        # 鏡面反射
rec_n = M.normal_from_reflection(d_inc, r_ref)                      # 逆問題で法線復元
null_n = np.array([1.0, 1.0, 0.0]); null_n /= np.linalg.norm(null_n)  # 無関係な法線 null
print(f"[normal_from_reflection] |rec·nA| {abs(rec_n @ nA):.2e} / rec·d {rec_n @ d_inc:+.3f} / "
      f"|null·nA| {abs(null_n @ nA):.3f}")
assert abs(abs(rec_n @ nA) - 1.0) < 1e-9, "反射から面法線を復元できていない"
assert rec_n @ d_inc <= 0.0, "復元法線が入射に逆らう向き(外向き)でない"
assert abs(rec_n @ nA) > abs(null_n @ nA) + 0.2, "復元が無関係法線 null を判別的に上回れていない"


# ═══════════════════════════════════════════════════════════════════════════
# 5) elastic_deform + cutout: 角の点群を学習用に水増し
# ═══════════════════════════════════════════════════════════════════════════
alpha = 0.05
# 5a) elastic_deform: 変位場の RMS ノルムはちょうど alpha
out_big = AUG.elastic_deform(corner, sigma=10.0, alpha=alpha, seed=1)   # σ大 = coherent(剛体的)
out_zero = AUG.elastic_deform(corner, sigma=0.0, alpha=alpha, seed=1)   # σ=0 = 各点独立
disp_big, disp_zero = out_big - corner, out_zero - corner
rms_big = float(np.sqrt(np.mean(np.sum(disp_big ** 2, axis=1))))
rms_zero = float(np.sqrt(np.mean(np.sum(disp_zero ** 2, axis=1))))
coh_big = float(np.linalg.norm(disp_big.mean(0)) / rms_big)   # coherence: σ大→~1(全点同方向)
coh_zero = float(np.linalg.norm(disp_zero.mean(0)) / rms_zero)  # σ=0→~0(独立で相殺)
out_det = AUG.elastic_deform(corner, sigma=10.0, alpha=alpha, seed=1)   # 決定論
print(f"[elastic_deform] RMS変位 σ大 {rms_big:.6f} / σ=0 {rms_zero:.6f} (真 alpha {alpha}) / "
      f"coherence σ大 {coh_big:.3f} vs σ=0 null {coh_zero:.3f}")
assert abs(rms_big - alpha) < 1e-9 and abs(rms_zero - alpha) < 1e-9, "変位 RMS が alpha に一致しない"
assert np.array_equal(out_big, out_det), "同一 seed で非決定論"
assert coh_big > 0.9 and coh_zero < 0.4 and coh_big > coh_zero + 0.4, \
    "σ大の coherent 変位が σ=0 独立 null を上回れていない"

# 5b) cutout: 空間的に局所なボックス欠損。除去点は辺長 extent のボックス内に必ず収まる。
extent = 0.15
kept, kept_idx = AUG.cutout(corner, extent=extent, seed=3)
removed_mask = np.ones(len(corner), bool); removed_mask[kept_idx] = False
removed = corner[removed_mask]
rem_span = float((removed.max(0) - removed.min(0)).max()) if len(removed) else 0.0
cloud_span = float((corner.max(0) - corner.min(0)).max())
print(f"[cutout] 除去 {len(removed)} 点 / 除去集団の広がり {rem_span:.3f} <= extent {extent} / "
      f"雲全体 {cloud_span:.3f}")
assert len(removed) >= 1, "cutout が 1 点も除去していない"
assert rem_span <= extent + 1e-9, "除去点が辺長 extent のボックスをはみ出した"
assert np.array_equal(kept, corner[kept_idx]), "kept != points[kept_idx]"
# beat-null: 同数をランダム抽出すると雲全体に散る(除去集団は空間的に局所)
rng = np.random.default_rng(0)
null_span = float(np.median([
    (corner[rng.choice(len(corner), len(removed), replace=False)].max(0)
     - corner[rng.choice(len(corner), len(removed), replace=False)].min(0)).max()
    for _ in range(50)])) if len(removed) >= 2 else cloud_span
print(f"[cutout] ランダム同数抽出の広がり(null) {null_span:.3f}")
assert rem_span < 0.6 * null_span, "除去集団が空間的に局所でない(ランダム散布 null と判別できない)"


# ═══════════════════════════════════════════════════════════════════════════
# 6) link_edges: 稜線から抽出したエッジ片を 26 近傍で連結成分にまとめる
# ═══════════════════════════════════════════════════════════════════════════
def fragment_mask(bridge):
    """3 本のエッジ片を置いた 16^3 bool grid。bridge=True で片1と片2を対角接触させる。"""
    m = np.zeros((16, 16, 16), bool)
    m[2, 2, 2:7] = True                     # 片1: x 軸に沿う線分
    if bridge:
        m[3, 3, 7:12] = True                # 片2': 片1 の端 (2,2,6) と対角接触 (3,3,7)
    else:
        m[8, 8, 3:8] = True                 # 片2 : 遠くに孤立
    m[3:8, 12, 12] = True                   # 片3: z 軸に沿う線分(常に孤立)
    return m

lab_sep, n_sep = ED.link_edges(fragment_mask(bridge=False))   # 3 片が離散 → 3 成分
lab_brd, n_brd = ED.link_edges(fragment_mask(bridge=True))    # 片1-片2 対角接触 → 2 成分
print(f"[link_edges] 離散配置 {n_sep} 成分 / 対角接触配置 {n_brd} 成分(26 近傍で連結)")
assert n_sep == 3, f"離れた 3 片が 3 成分にならない: {n_sep}"
assert n_brd == 2, f"対角接触 2 片が 26 近傍で連結されない(6 近傍なら 3 のまま): {n_brd}"
assert set(np.unique(lab_sep)) == {0, 1, 2, 3}, "背景0 + 3 成分のラベルになっていない"


# ═══════════════════════════════════════════════════════════════════════════
# 7) inflate: 占有格子を膨張して planner 用 C-space 障害物(ユークリッド球)を作る
# ═══════════════════════════════════════════════════════════════════════════
G = 11
occ = np.zeros((G, G, G), bool)
occ[5, 5, 5] = True                         # 中心に単一占有 voxel
radius = 2.5
inf = OCC.inflate(occ, radius=radius, voxel_size=1.0)
# 解析 GT: 中心からのユークリッド距離 <= radius の voxel 集合(EDT は厳密ユークリッド)
zz, yy, xx = np.mgrid[0:G, 0:G, 0:G]
dist = np.sqrt((zz - 5) ** 2 + (yy - 5) ** 2 + (xx - 5) ** 2)
ball = dist <= radius
print(f"[inflate] 占有 voxel {int(inf.sum())} / 解析ユークリッド球 {int(ball.sum())} / 一致 {bool(np.array_equal(inf, ball))}")
assert np.array_equal(inf, ball), "膨張が解析ユークリッド球と厳密一致しない"
# 単調性: radius を上げると占有は単調増(下流 planner の前提)
c1 = int(OCC.inflate(occ, 1.0).sum())
c2 = int(OCC.inflate(occ, 2.5).sum())
c3 = int(OCC.inflate(occ, 4.0).sum())
assert 1 < c1 < c2 < c3, f"radius に対して占有が単調増でない: {1, c1, c2, c3}"
# beat-null: 角を丸めない箱膨張(Chebyshev r=2)は 5^3=125。ユークリッド球はそれより小さい=正しく丸めている
box_count = (2 * 2 + 1) ** 3
print(f"[inflate] 単調 1<{c1}<{c2}<{c3} / ユークリッド球 {c2} < 箱膨張 null {box_count}(角を丸めている)")
assert c2 < box_count, "ユークリッド球が箱膨張 null より小さくない(角が丸まっていない)"


print("PASS: joint_bilateral(段差保存 denoise, RMS {:.3f}->{:.3f})→bearing_angle(atan傾き厳密+denoise改善)"
      "→region_growing(稜線で2面, 単一法線nullは1面)→normal_from_reflection(|rec·n|=1)"
      "→elastic_deform(RMS=alpha, coherent>null)+cutout(局所ボックス)→link_edges(26連結 3/2成分)"
      "→inflate(ユークリッド球厳密一致・単調・箱nullより小) を GT 照合".format(rms_noisy, rms_den))
