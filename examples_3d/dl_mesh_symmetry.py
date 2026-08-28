"""事例: 実在の恐竜骨格(スミソニアン Triceratops)の左右対称面を復元する (shape_analysis).

生き物はほぼ例外なく**左右対称(bilateral / mirror symmetry)**で、その対称面(矢状面)は
形状補完・姿勢の正準化・左右差検査(片側だけの欠損や変形=異常)の基準になる。ここでは CC0 で
公開された実物の三角竜(Triceratops horridus)骨格スキャンを読み込み、姿勢の当てずっぽうを一切
与えずに symmetry3d.detect_reflection_symmetry へ渡す。この op は重心を通る PCA 主軸を候補法線と
し、点群を各候補面で鏡映して元と重なるか(chamfer 残差 / 中央値最近傍間隔)を採点する。四足で
立った骨格は左右方向が最も薄いので、最良の鏡映面(=最小残差)は左右方向を法線に持つ矢状面に
なる — これが解剖学的な左右対称面である。

検証(GT): 骨格は本当に左右対称なので、真の矢状面は「1つだけ」低残差になり、残り2つの主平面
(体長方向・体高方向)は生き物として対称でないから高残差になる。beat-null: 骨格の片側の点だけを
体幅の 20% ぶん法線方向へ押し出して左右対称を壊すと、同じ矢状面での鏡映残差が跳ね上がる。よって
「無傷の矢状面残差 << 片側破壊の残差」かつ「矢状面残差 << 他2主平面」を要求すれば、低残差が
metric のまぐれでなく本物の左右対称の検出であることを判別的に示せる。
"""
import os
import sys

import numpy as np

import sample_data
import symmetry3d


def load_mesh_vertices(path):
    """メッシュファイル → 頂点 (N,3)。.glb/.gltf は optional な glTF ローダ経由。"""
    ext = os.path.splitext(str(path))[1].lower()
    if ext in (".glb", ".gltf"):
        import meshio_opt                       # optional extra(pygltflib)
        V, _F = meshio_opt.read_gltf_merged(path)
    else:
        import mesh                             # numpy ネイティブ(.ply/.stl/.obj/.off)
        V, _F = mesh.read_mesh(path)
    return np.asarray(V, float)


# --- 0) データ解決(opt-in ダウンロード、実行時はネットワーク非依存)-------------
#   Triceratops(第一候補・CC0)→ 無ければ Stanford Armadillo(第二候補)。
path = sample_data.local_path("triceratops") or sample_data.local_path("armadillo")
if path is None:
    print("SKIP: サンプル未取得。次を実行してから再試行してください: "
          "py -3.11 imgevolve.py samples download triceratops --yes")
    sys.exit(0)

try:
    V = load_mesh_vertices(path)
except RuntimeError as ex:                       # glTF バックエンド(pygltflib)未導入など
    print("SKIP: メッシュを読めません(%s)。'pip install pygltflib' 後に再試行してください。" % ex)
    sys.exit(0)

# --- 1) 高速化のため頂点を決定的な stride で数千点に間引く ------------------------
stride = max(1, len(V) // 4000)
P = V[::stride].copy()

# --- 2) スケール正規化(重心へ移動 + RMS 半径で割り単位化)------------------------
#   対称スコア自体は中央値間隔で正規化されスケール不変だが、破壊の大きさ(体幅の割合)を
#   定義するため点群を正規化しておく。
c0 = P.mean(axis=0)
Pc = P - c0
rms = float(np.sqrt(np.mean(np.sum(Pc ** 2, axis=1))))
assert rms > 0.0, "退化した点群(全点一致)"
Pn = Pc / rms

# --- 3) 反射対称面の復元(初期姿勢の推定なし)-----------------------------------
res = symmetry3d.detect_reflection_symmetry(Pn)
normal = np.asarray(res["plane_normal"], float)
plane_pt = np.asarray(res["plane_point"], float)
all_scores = list(res["all_scores"])              # 3 主平面それぞれの鏡映残差(重心通過)
best_idx = int(np.argmin(all_scores))
s_sag = float(all_scores[best_idx])               # 復元された対称面(=矢状面)の残差
other = [all_scores[i] for i in range(3) if i != best_idx]
s_second = float(min(other))                      # 非対称な残り2主平面のうち良い方

# 復元法線が「最も薄い主軸(=左右方向)」に一致するかを確認(解剖学的な裏付け)。
_w, _vec = np.linalg.eigh(Pn.T @ Pn)              # eigh は昇順 → 列0 が最小固有値=最も薄い軸
narrow_axis = _vec[:, 0]
narrow_align = abs(float(normal @ narrow_axis))   # 1.0 に近ければ矢状面=最薄軸
axis_rank = {0: "体長方向", 1: "体高方向", 2: "左右方向(最薄)"}
# PCA 主軸(降順)での best_idx のランク名
pca_desc_rank = 2 - best_idx if False else best_idx  # all_scores は _pca_axes(降順)順

# --- 4) beat-null: 片側だけを体幅の 20% 押し出して左右対称を壊す --------------------
signed = (Pn - plane_pt) @ normal                 # 矢状面からの符号付き距離
side = signed > 0.0                                # 片側(例: 右半身)
extent = float(np.linalg.norm(Pn.max(axis=0) - Pn.min(axis=0)))
K = 0.20                                           # 破壊量 = 体幅(全体スパン)の 20%
Ppert = Pn.copy()
Ppert[side] += K * extent * normal                 # 片側を法線方向へ押し出す
# 破壊した骨格を「同じ矢状面」で鏡映採点(=左右がもう重ならない)
s_pert = symmetry3d.reflection_symmetry_score(Ppert, plane_pt, normal)

# --- 5) GT レポート --------------------------------------------------------------
print("メッシュ頂点              : %d (%s)" % (len(V), os.path.basename(str(path))))
print("対称性採点に用いた点数    : %d (stride=%d)" % (len(Pn), stride))
print("復元した対称面の法線      : [%.3f, %.3f, %.3f]" % tuple(normal))
print("最薄主軸との一致度|dot|   : %.4f  (1.0=左右方向=矢状面)" % narrow_align)
print("矢状面 鏡映残差           : %.4f  (中央値間隔の倍数, 小さいほど対称)" % s_sag)
print("他2主平面(体長/体高)の残差: %.4f, %.4f  (生き物なので非対称=高い)"
      % (other[0], other[1]))
print("beat-null 片側20%%破壊 残差 : %.4f  (同じ矢状面 / 無傷比 %.1f倍)"
      % (s_pert, s_pert / s_sag))

# ═══ GT 検証 ═══════════════════════════════════════════════════════════════════
# (a) 復元面は最も薄い主軸(左右方向)を法線に持つ=解剖学的な矢状面である。
assert narrow_align > 0.98, \
    "復元した対称面が最薄主軸(左右方向)に一致しない: |dot|=%.4f" % narrow_align
# (b) 左右対称な骨格は「1つの主平面だけ」が低残差(矢状面)、残り2つは明確に高い。
#     まぐれの低残差なら3面が同程度になるはず。ここで判別する。
assert s_sag < s_second / 1.4, \
    "矢状面が他主平面より突出して対称でない: %.4f vs %.4f" % (s_sag, s_second)
# (c) 絶対値でも矢状面残差は数点間隔しかない=本当に左右対称。
assert s_sag < 3.5, "矢状面残差が対称と呼ぶには大きすぎる: %.4f" % s_sag
# (d) beat-null: 片側を破壊すると同じ矢状面での残差が跳ね上がる(無傷 << 破壊)。
assert s_pert > 3.0 * s_sag, \
    "片側破壊が対称性を十分に壊せていない: 破壊 %.4f vs 無傷 %.4f" % (s_pert, s_sag)
# (e) 破壊後は「無傷の非対称面」よりも悪い=破壊が本物であることの念押し。
assert s_pert > s_second, \
    "破壊残差が無傷の非対称面すら超えない: %.4f vs %.4f" % (s_pert, s_second)

print("PASS: 三角竜骨格は矢状面で自己鏡映(残差 %.2f 中央値間隔・最薄軸一致 %.2f)= 左右対称。"
      "他2主平面 %.2f/%.2f と明確に区別、片側20%%破壊で %.2f(%.1f倍)= 判別的"
      % (s_sag, narrow_align, other[0], other[1], s_pert, s_pert / s_sag))
