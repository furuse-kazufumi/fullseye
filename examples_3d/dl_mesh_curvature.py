"""事例: 実スキャンメッシュから「特徴のある領域」を曲率で拾う (features).

3D スキャン/CAD のメッシュを検査・特徴点抽出・LOD(詳細度)制御・法線推定に回すとき、
各頂点の**平均曲率**は最も基本的な特徴量になる。曲率が高い頂点は角・稜線・襞(ひだ)・
鱗(うろこ)など「形の情報が詰まった場所」で、平らな胴体や滑らかな球面は曲率が低く一定。
ここでは実際にダウンロードした Stanford Dragon(鱗・爪・牙・巻いた尾を持つ高精細メッシュ、
約 87 万面)を ``mesh.read_mesh`` で読み、``mesh_props.vertex_curvature``(Meyer 2003 の
cotangent Laplace-Beltrami)で全頂点の平均曲率の大きさ H を求める。物体スケールに依らせない
ため、表面積から作った等価球半径 Rn=√(面積/4π) を掛けて無次元化する(Hn = H·Rn)。

比較対象(null)は「滑らかな球」。半径 R の球は解析的に H = 1/R が**全面で厳密に一定**なので、
同じ正規化をすると Hn ≡ 1、ばらつきはゼロになる。実物メッシュの曲率が本当に「詳細な形状」を
表しているなら、その分布は球よりずっと広いはずだ。

検証(GT): 曲率が「詳細な形状」と「滑らかな形状」を判別できることを二段で示す。
  (a) 解析 GT: 細分イコサ球(analytic sphere)に op を掛けると Hn の中央値が 1.0(=球の H·R)に
      一致し(|median-1|<0.02)、標準偏差 ~0(ばらつき無し)。op が既知の真値を厳密に再現する。
  (b) beat-null: 「対象は滑らかな球(曲率一定)」という null モデルは Hn>2 の頂点割合を 0 と予測する。
      実 Dragon は |Hn|>2 の頂点が過半(実測 ~88%)、中央値 ~9、robust なばらつき(MAD)が球の
      数十倍以上。滑らかさを仮定する null は実物の広い曲率分布を全く再現できず FAIL する=判別的。
決定的(乱数を使わない。イコサ球の細分は index 順で一意、メッシュ読込も決定的)。ネット不要
(未ダウンロード時は SKIP して exit 0。実データ取得は下記コマンドで opt-in)。
"""
import sys
from pathlib import Path

import numpy as np

# このファイルは examples_3d/ 内。ルートの mesh_props.py 等と同名の例ファイルがあるため、
# リポジトリルートを sys.path の**先頭**に置き、`import mesh_props` が例自身でなくルートの
# モジュールへ解決されるようにする(examples_3d/mesh_props.py の先取りを防ぐ)。
_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))

import sample_data  # noqa: E402  (sys.path 調整後に import)
import mesh  # noqa: E402
import mesh_props  # noqa: E402


# --- 0) 実データ取得(opt-in ダウンローダ)。無ければ SKIP して exit 0 -----------
#     検証環境(validate)はデータ無しで走るため、ここで必ずネットに触れず正常終了する。
path = sample_data.local_path("dragon") or sample_data.local_path("armadillo")
if path is None:
    print("SKIP: 実メッシュが未取得(dragon も armadillo も無い)。次で取得後に再実行:")
    print("  py -3.11 imgevolve.py samples download dragon --yes")
    print("  (研究用途 courtesy。~11MB を Stanford 3D Scanning Repository から取得)")
    sys.exit(0)                                  # データ無し = 正常(ネットに触れない)


def clean_mesh(V, F):
    """実スキャンメッシュの退化三角形を除去して曲率が計算できる形に整える。

    生の Dragon には (1) 同一頂点を重複参照する face、(2) ゼロ面積(sliver)face が混じる。
    どちらも cotangent 曲率の分母(面積)を壊すので落とし、残った face が参照する頂点だけに
    index を振り直す(孤立頂点を残すと混合面積 0 で ValueError になるため)。決定的な操作。
    """
    keep = ~((F[:, 0] == F[:, 1]) | (F[:, 1] == F[:, 2]) | (F[:, 0] == F[:, 2]))
    F = F[keep]
    tri = V[F]
    area = 0.5 * np.linalg.norm(np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]), axis=1)
    scale = float(np.median(area[area > 0]))     # 面積の代表スケール(無次元しきい値用)
    F = F[area > 1e-7 * scale]                    # ゼロ面積 face を除去
    used = np.unique(F)                           # 生き残った face が使う頂点
    remap = np.full(len(V), -1, dtype=np.int64)
    remap[used] = np.arange(len(used))
    return V[used], remap[F]


def icosphere(subdiv, radius):
    """半径 ``radius`` の細分イコサ球メッシュ (V, F) を作る(乱数なし=決定的)。

    正 20 面体の各辺を再帰的に中点分割し、頂点を球面へ射影する。三角形がほぼ均一で、
    どの頂点も H = 1/radius の滑らかな球面 = 曲率一定の理想 null になる。
    """
    t = (1.0 + 5.0 ** 0.5) / 2.0
    V = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0],
                  [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
                  [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], dtype=np.float64)
    F = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
                  [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
                  [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
                  [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]], dtype=np.int64)
    V = V / np.linalg.norm(V, axis=1, keepdims=True)
    for _ in range(subdiv):
        mid, nV, nF = {}, list(V), []

        def midpoint(a, b):
            key = (a, b) if a < b else (b, a)     # 辺 index は昇順キーで一意 = 決定的
            if key not in mid:
                p = V[a] + V[b]
                mid[key] = len(nV)
                nV.append(p / np.linalg.norm(p))  # 球面へ射影
            return mid[key]

        for a, b, c in F:
            ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
            nF += [[a, ab, ca], [b, bc, ab], [c, ca, bc], [ab, bc, ca]]
        V, F = np.array(nV), np.array(nF, dtype=np.int64)
    return V * radius, F


def normalized_curvature(V, F):
    """(V,F) の各頂点 平均曲率 H を等価球半径 Rn=√(面積/4π) で無次元化して返す。→ (N,)。

    Rn は物体スケール(1/長さの曲率をスケール不変にする)。半径 R の球なら H=1/R・Rn=R で
    Hn≡1 になるので、形状の違いだけが Hn のばらつきに残る。
    """
    Rn = (mesh_props.mesh_area((V, F)) / (4.0 * np.pi)) ** 0.5
    return mesh_props.vertex_curvature((V, F)) * Rn, Rn


def mad(x):
    """中央絶対偏差(median absolute deviation)= 外れ値に頑健なばらつき指標。"""
    return float(np.median(np.abs(x - np.median(x))))


# --- 1) 実メッシュ: 読み込み → 退化除去 → 正規化曲率 ------------------------------
name = "dragon" if sample_data.local_path("dragon") else "armadillo"
Vd_raw, Fd_raw = mesh.read_mesh(path)
Vd, Fd = clean_mesh(Vd_raw, Fd_raw)
Hn_d, Rn_d = normalized_curvature(Vd, Fd)

d_med = float(np.median(Hn_d))
d_mad = mad(Hn_d)
d_frac2 = float((Hn_d > 2.0).mean())             # 球曲率の 2 倍超 = 明確な特徴
d_frac3 = float((Hn_d > 3.0).mean())

print(f"実メッシュ({name})            : V{Vd_raw.shape[0]}→{Vd.shape[0]}  F{Fd_raw.shape[0]}→{Fd.shape[0]}"
      f"(退化除去後)  等価半径 Rn={Rn_d:.4f}")
print(f"  正規化曲率 Hn=H·Rn          : median {d_med:.2f}  MAD {d_mad:.2f}")
print(f"  特徴頂点の割合              : |Hn|>2 が {d_frac2 * 100:.1f}% / |Hn|>3 が {d_frac3 * 100:.1f}%")

# --- 2) null: 同スケールの滑らかな球(曲率一定)。同じ計測をする ------------------
Vs, Fs = icosphere(4, Rn_d)                      # 半径 = Dragon の等価球半径 = 同スケール
Hn_s, Rn_s = normalized_curvature(Vs, Fs)

s_med = float(np.median(Hn_s))
s_std = float(np.std(Hn_s))
s_mad = mad(Hn_s)
s_frac2 = float((Hn_s > 2.0).mean())

print(f"null 球(icosphere, 同スケール): V{Vs.shape[0]} F{Fs.shape[0]}  等価半径 Rn={Rn_s:.4f}")
print(f"  正規化曲率 Hn              : median {s_med:.4f}(解析値 1.0)  std {s_std:.2e}  MAD {s_mad:.2e}")
print(f"  特徴頂点の割合              : |Hn|>2 が {s_frac2 * 100:.1f}%")
print(f"beat-null: |Hn|>2 割合  実 {d_frac2 * 100:.1f}%  vs  球 {s_frac2 * 100:.1f}%   "
      f"MAD 比 実/球 = {d_mad / max(s_mad, 1e-9):.0f}×")

# ═══ GT 検証 ═══════════════════════════════════════════════════════════════════
# (a) 解析 GT: 球は H=1/R が厳密に一定 → 正規化曲率の中央値 1.0・ばらつき ~0。
#     op が既知形状の真値を再現していることの確認(緩い assert ではなく tight tolerance)。
assert abs(s_med - 1.0) < 0.02, f"球の正規化曲率中央値が解析値 1.0 と不一致: {s_med:.4f}"
assert s_std < 0.02, f"滑らかな球なのに曲率がばらついた: std={s_std:.2e}"
assert s_frac2 < 0.01, f"滑らかな球に |Hn|>2 の特徴頂点が出た: {s_frac2:.4f}"

# (b) beat-null: 「対象は滑らかな球(曲率一定)」という null は |Hn|>2 割合を 0 と予測する。
#     実 Dragon は過半が |Hn|>2、robust なばらつき(MAD)が球の数十倍以上 = null を大きく上回る。
assert d_frac2 > 0.5, f"実メッシュの曲率分布が広くない(特徴が拾えていない): {d_frac2:.3f}"
assert d_med > 2.0, f"実メッシュの曲率中央値が球並みに小さい: {d_med:.3f}"
assert d_frac2 - s_frac2 > 0.5, "実メッシュと球で特徴頂点割合の差が小さい(判別的でない)"
assert d_mad > 20.0 * max(s_mad, 1e-9), (
    f"実メッシュの曲率ばらつきが球を十分に上回らない: MAD 実 {d_mad:.3f} / 球 {s_mad:.2e}")

print(f"PASS: 実メッシュ({name} {Fd.shape[0]}面)の正規化曲率は median {d_med:.1f}・MAD {d_mad:.1f}・"
      f"|Hn|>2 が {d_frac2 * 100:.0f}% と広く分布。滑らかな球 null は median {s_med:.2f}(解析 1.0)・"
      f"std {s_std:.0e}・|Hn|>2 が {s_frac2 * 100:.0f}%。曲率が詳細形状を判別(MAD 比 {d_mad / max(s_mad, 1e-9):.0f}×)")
