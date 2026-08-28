# -*- coding: utf-8 -*-
"""事例: N枚歯の平歯車(スパーギア)の回転対称位数 N を点群から復元する (shape_analysis).

機械部品のスキャン点群から「軸まわり何回対称か(fold order N)」を当てられると、歯数の同定・
姿勢の正準化・欠け歯検査に使える。ここでは歯数 N=6 の平歯車の外周(歯形リム)点群を手続き的に
生成し、symmetry3d で (1) 対称軸 (2) 位数 N を復元する。歯形リムは 1 セクタ(60度)を作って
N 回複製するので厳密に C6 対称になる。

要点(reflection を扱う symmetry.py、および SDF の角度ラン計数で歯数を数える gear_metrology.py
と区別): 本例は「本物の歯車形状」を使い、位数の **約数構造** を正面から扱う。C6 の歯車は C2・C3
も内包する —— 60度(位数6)・120度(位数3)・180度(位数2)のいずれの回転でも自己一致する
ため、これらの残差はすべて ~0 になる。したがって真の位数 N は「自己一致する回転のうち最大の
折り数」= chamfer 残差が低い order の **最大値** として復元するのが正しい。90度(位数4)・72度
(位数5)などの非約数回転は歯が谷に落ちるので残差は桁違いに大きい。

検証(GT):
  * (軸) detect_rotational_symmetry が復元した対称軸が真の軸(z軸)に一致(|z成分| > 0.99)。
  * (位数) 復元位数 == N = 6(= 低残差 order の最大)。約数 {2,3,6} は低残差、非約数 {4,5,7,9,12}
    は高残差、で判別的に分離する。
  * (beat-null) 同じ 60度回転(位数6)を無対称なランダム点群に掛けると残差は桁違いに大きい:
    歯車の位数6残差 << ランダムの位数6残差。約数ごとに歯車残差 << 同回転のランダム残差、を確認。
"""
import sys
from pathlib import Path

# リポジトリルートを sys.path の先頭に置く(examples_3d 内の同名ファイルが
# トップレベルモジュールを隠さないように、fullseye の import より前に行う)。
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

import symmetry3d as S

# ── 歯車の諸元(world 単位・対称軸は z)──────────────────────────────────
N_TEETH = 6         # 真の歯数 = 復元したい位数 N
R_ROOT = 0.85       # 歯溝の底(root circle)の半径
R_TIP = 1.20        # 歯先円の半径
THICK = 0.20        # 歯車の厚み(z 方向)
PITCH = 2 * np.pi / N_TEETH   # 1 歯あたりの角度ピッチ = 60度


def tooth_radius(phi):
    """1 ピッチ内(中心 phi=0)の境界半径。歯先(R_TIP)→歯面(線形)→谷(R_ROOT)。→ float。"""
    phi_tip = 0.22 * PITCH     # |phi|<=phi_tip: 歯先(平ら)
    phi_flank = 0.34 * PITCH   # phi_tip..phi_flank: 歯面(線形に落ちる)
    a = abs(phi)
    if a <= phi_tip:
        return R_TIP
    if a >= phi_flank:
        return R_ROOT
    t = (a - phi_tip) / (phi_flank - phi_tip)
    return R_TIP + t * (R_ROOT - R_TIP)


def build_gear():
    """歯数 N の平歯車の外周リム点群。基準セクタ(±30度)を作り z 回転で N 回複製 → 厳密 C_N。→ (M,3)。"""
    # 1 ピッチ内の角度サンプル(endpoint=False で複製時に境界重複を出さない = 厳密不変)
    phis = np.linspace(-PITCH / 2, PITCH / 2, 60, endpoint=False)
    zs = np.linspace(-THICK / 2, THICK / 2, 6)   # 厚み方向のリング帯
    base = []
    for phi in phis:
        r = tooth_radius(phi)
        for z in zs:
            base.append((r * np.cos(phi), r * np.sin(phi), z))
    base = np.asarray(base, float)               # 基準セクタ(1 歯分の歯形リム)
    pts = []
    for k in range(N_TEETH):
        ang = k * PITCH
        c, s = np.cos(ang), np.sin(ang)
        Rz = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        pts.append(base @ Rz.T)                  # k 番目のセクタ = 基準を k*60度 回転
    return np.vstack(pts)                         # 60度回転で厳密に不変な C6 点群


# --- 1) 歯車点群を組む + 検出 ------------------------------------------------
gear = build_gear()
AXIS_TRUE = np.array([0.0, 0.0, 1.0])            # 真の対称軸(z)

CAND = (2, 3, 4, 5, 6, 7, 9, 12)                 # 候補位数(6 の約数=2,3,6 / 非約数=4,5,7,9,12)
rot = S.detect_rotational_symmetry(gear, orders=CAND)
axis = np.asarray(rot["axis_dir"], float)
axis = axis / np.linalg.norm(axis)
axis_align = abs(float(np.dot(axis, AXIS_TRUE)))  # 復元軸が z 軸か(1 に近いほど一致)

# --- 2) 検出した軸まわりに各位数の残差を測る(位数の復元)-------------------
# 検出器は最小残差の (軸,order) を返すが、約数 {2,3,6} はすべて残差 ~0 なので order は
# その中のどれになるか一意でない。位数 N は「低残差 order の最大」として復元する。
axis_pt = np.asarray(rot["axis_point"], float)
gear_scores = {o: S.rotational_symmetry_score(gear, axis_pt, axis, o) for o in CAND}

# --- 3) beat-null: 同じ bbox の無対称ランダム点群 ---------------------------
rng = np.random.default_rng(0)
lo, hi = gear.min(0), gear.max(0)
null_cloud = rng.uniform(lo, hi, size=gear.shape)   # 歯車と同数・同 bbox のランダム点群(無対称)
null_pt = null_cloud.mean(0)
null_scores = {o: S.rotational_symmetry_score(null_cloud, null_pt, AXIS_TRUE, o) for o in CAND}

# ある回転 order が「真の対称」= 歯車の残差が、同じ回転をランダム点群に掛けたときの残差より
# 桁違いに小さい(< 30%)こと。約数 N を前提にせず like-for-like で判定 → その最大が位数 N。
def is_symmetry(o):
    return gear_scores[o] < 0.3 * null_scores[o]

symmetric_orders = [o for o in CAND if is_symmetry(o)]
recovered_fold = max(symmetric_orders)

# --- 出力 -------------------------------------------------------------------
print(f"歯車: 歯数 {N_TEETH}  点数 {len(gear)}  (root {R_ROOT} / tip {R_TIP} / 厚み {THICK})")
print(f"検出軸 axis_dir            = {np.round(axis, 3)}  |z成分| = {axis_align:.4f}")
print(f"検出器の最小残差 order     = {rot['order']}  score = {rot['score']:.2e}  (約数のどれか)")
print("order別 残差 (小さいほど対称):")
print(f"  {'order':>5} | {'歯車(gear)':>12} | {'ランダム(null)':>14} | {'約数?':>5} | 対称?")
for o in CAND:
    is_div = (N_TEETH % o == 0)
    print(f"  {o:>5} | {gear_scores[o]:>12.3e} | {null_scores[o]:>14.3e} | "
          f"{'yes' if is_div else 'no':>5} | {'symmetry' if is_symmetry(o) else '-'}")
print(f"低残差 order(対称)集合    = {symmetric_orders}")
print(f"復元した位数 N             = {recovered_fold}  (= 低残差 order の最大)")

null6 = null_scores[6]
gear6 = gear_scores[6]
print(f"beat-null(位数6の残差)    : 歯車 {gear6:.3e}  <<  ランダム {null6:.3e}  "
      f"(比 {null6 / max(gear6, 1e-12):.1e} 倍)")

# --- GT 検証 ----------------------------------------------------------------
# (軸) 復元した対称軸が真の z 軸に一致
assert axis_align > 0.99, f"復元軸が z 軸に一致しない: |z|={axis_align:.4f}"

# (位数) 復元位数が真の歯数 N に厳密一致。約数 {2,3,6} は低残差・非約数 {4,5,7,9,12} は高残差、
# の判別的な分離を確認(=「非約数回転では自己一致しない」)。
assert recovered_fold == N_TEETH, f"復元位数が歯数と一致しない: {recovered_fold} != {N_TEETH}"
assert symmetric_orders == [2, 3, 6], f"対称 order 集合が約数構造と一致しない: {symmetric_orders}"
for o in (2, 3, 6):                    # 約数 → 自己一致(残差 ~0)
    assert gear_scores[o] < 0.05, f"約数 {o} の残差が大きい: {gear_scores[o]:.3e}"
for o in (4, 5, 7, 9, 12):             # 非約数 → 自己一致しない(高残差)
    assert gear_scores[o] > 0.5, f"非約数 {o} の残差が小さすぎる: {gear_scores[o]:.3e}"

# (beat-null) 位数6の同一回転で、歯車残差 << ランダム残差。ランダムは絶対値でも高残差。
assert null6 > 1.0, f"ランダム点群の位数6残差が低すぎる(無対称のはず): {null6:.3e}"
assert gear6 < 0.05, f"歯車の位数6残差が高い(対称のはず): {gear6:.3e}"
assert null6 > 20.0 * max(gear6, 1e-9), f"歯車とランダムの位数6残差が分離しない: {gear6:.3e} vs {null6:.3e}"

print(f"PASS: 6枚歯スパーギアの対称軸を z(|z|={axis_align:.3f})、位数 N={recovered_fold} を復元 "
      f"— 約数{{2,3,6}}は残差<0.05・非約数{{4,5,7,9,12}}は>0.5、位数6残差 {gear6:.1e}<<ランダム {null6:.1e}")
