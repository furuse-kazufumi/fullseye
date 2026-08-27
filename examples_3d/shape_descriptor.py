"""事例: 3D 形状を「向きに関係なく」種類で照合する (回転不変な形状検索).

やりたいこと(平たい言葉で): 部品や物体を 3D スキャンすると、毎回バラバラの
向きで置かれている。同じ種類の物体は、たとえ回転していても「同じ形」として
拾いたい。逆に別の種類(球と箱など)はきちんと区別したい。素朴にボクセルの
占有(どのマスが埋まっているか)をそのまま並べて比べると、少し回すだけで
埋まるマスが総入れ替わりになり、同じ形なのに「全然違う」と判定してしまう。

手法: sh_descriptor は物体を中心まわりの同心球シェルに分け、各シェルの模様を
球面調和(SH)に展開して「帯域(周波数)ごとのエネルギー」を記述子にする。
帯域エネルギーは回転しても帯域の中で成分が混ざるだけなので値が変わらない
(= 回転不変, Kazhdan 2003)。match_sh_descriptor はその記述子どうしの
コサイン類似度を返す(1 に近いほど同形状)。ここでは距離 = 1 - 類似度 として扱う。

検証(GT): 球・箱・円柱を作り(正解ラベル既知)、各形状を大きく回転したコピーを
クエリにする。SH 距離で最近傍の正準形状を選ばせ、回した本人と同じ種類が
選ばれるか(=検索成功)を確かめる。beat-the-null: 素のボクセル占有ベクトルの
距離を同条件で計算し、回転で同形状を近接と判定できず検索を外す(または SH ほど
分離できない)ことを対比して示す。SH が null を明確に上回ることを assert する。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from scipy import ndimage

import match3d as X


def sphere_volume(n, radius, soft=1.0):
    """半径 radius の充実球(中心配置)。soft でエッジを少しぼかし bilinear 標本化を安定化。"""
    c = (n - 1) / 2.0
    z, y, x = np.ogrid[:n, :n, :n]
    dist = np.sqrt((z - c) ** 2 + (y - c) ** 2 + (x - c) ** 2)
    return 1.0 / (1.0 + np.exp((dist - radius) / soft))


def box_volume(n, half_dims, soft=1.0):
    """辺の異なる直方体(中心配置)。half_dims=(hz,hy,hx) は各軸の半径。"""
    c = (n - 1) / 2.0
    hz, hy, hx = half_dims
    z, y, x = np.ogrid[:n, :n, :n]
    # 各軸のはみ出し量の最大 = 直方体表面からの符号付き距離(外側で正)の近似
    d = np.maximum.reduce([
        np.abs(z - c) - hz + 0 * y + 0 * x,
        np.abs(y - c) - hy + 0 * z + 0 * x,
        np.abs(x - c) - hx + 0 * z + 0 * y,
    ])
    return 1.0 / (1.0 + np.exp(d / soft))


def cylinder_volume(n, radius, half_height, soft=1.0):
    """z 軸まわりの円柱(中心配置)。半径 radius・高さ 2*half_height。"""
    c = (n - 1) / 2.0
    z, y, x = np.ogrid[:n, :n, :n]
    r = np.sqrt((y - c) ** 2 + (x - c) ** 2) + 0 * z
    d = np.maximum(r - radius, np.abs(z - c) - half_height + 0 * y + 0 * x)
    return 1.0 / (1.0 + np.exp(d / soft))


def rotate_volume(vol, angles_deg):
    """(a1,a2,a3) 度で 3 平面の連続回転。reshape=False で格子サイズ維持、order=1。"""
    a1, a2, a3 = angles_deg
    v = ndimage.rotate(vol, a1, axes=(1, 2), reshape=False, order=1, mode="constant")
    v = ndimage.rotate(v, a2, axes=(0, 2), reshape=False, order=1, mode="constant")
    v = ndimage.rotate(v, a3, axes=(0, 1), reshape=False, order=1, mode="constant")
    return np.clip(v, 0.0, 1.0)


def raw_voxel_distance(a, b):
    """null ベースライン: 素のボクセル占有ベクトルのコサイン距離 (1 - cos)。

    回転不変性を一切持たない素朴法。同形状でも回すと埋まるマスが替わるため
    距離が大きく出る想定(=これが SH に負けることを示すための比較対象)。
    """
    fa = np.asarray(a, np.float64).reshape(-1)
    fb = np.asarray(b, np.float64).reshape(-1)
    na = np.linalg.norm(fa)
    nb = np.linalg.norm(fb)
    if na < 1e-9 or nb < 1e-9:
        raise ValueError("空(占有ゼロ)のボリュームは比較できない")
    return 1.0 - float((fa * fb).sum() / (na * nb))


def sh_distance(a, b):
    """SH 記述子のコサイン距離 (1 - 類似度)。match_sh_descriptor は 1=同形状。"""
    sim = X.match_sh_descriptor(a, b)
    return 1.0 - sim


def validate_volume(name, vol, n):
    """形状(立方格子)と非退化(占有あり)を検証。ごまかさず degenerate は弾く。"""
    v = np.asarray(vol, np.float64)
    if v.shape != (n, n, n):
        raise ValueError(f"{name}: 形状が {v.shape}、期待は {(n, n, n)}")
    if not np.isfinite(v).all():
        raise ValueError(f"{name}: 非有限値を含む")
    if float(v.sum()) < 1.0:
        raise ValueError(f"{name}: 占有がほぼゼロ(退化) sum={float(v.sum()):.3e}")


def nearest_label(query, database, distance_fn):
    """query に対し database(名前→ボリューム)の中で最小距離のラベルと距離表を返す。"""
    dists = {name: distance_fn(query, vol) for name, vol in database.items()}
    best = min(dists, key=dists.get)
    return best, dists


def main():
    n = 44
    soft = 1.2

    # --- 1) 正準(向き既定)の 3 形状 = 検索データベース。正解ラベル既知 ---
    canon = {
        "sphere": sphere_volume(n, radius=12.0, soft=soft),
        "box": box_volume(n, half_dims=(13.0, 8.0, 6.0), soft=soft),
        "cylinder": cylinder_volume(n, radius=8.0, half_height=14.0, soft=soft),
    }
    for name, vol in canon.items():
        validate_volume(f"canon/{name}", vol, n)

    # --- 2) 各形状を大きく回転したコピー = クエリ(向き未知の 3D スキャン相当) ---
    query_angles = {
        "sphere": (37.0, 24.0, 51.0),
        "box": (40.0, 25.0, 33.0),
        "cylinder": (35.0, 48.0, 22.0),
    }
    queries = {}
    for name in canon:
        q = rotate_volume(canon[name], query_angles[name])
        validate_volume(f"query/{name}", q, n)
        queries[name] = q

    # --- 3) 検索: 各クエリの最近傍ラベルを SH と null(素ボクセル)でそれぞれ判定 ---
    print("形状記述子による回転不変検索 (格子 %d^3, L=8, nradii=12)" % n)
    print("-" * 68)
    sh_correct = 0
    null_correct = 0
    sh_same_max = 0.0     # 同形状(回転)ペアの SH 距離の最大(小さいほど良い)
    sh_cross_min = 1e9    # 異形状ペアの SH 距離の最小(大きいほど良い)

    for true_label in canon:
        q = queries[true_label]
        sh_pick, sh_d = nearest_label(q, canon, sh_distance)
        null_pick, null_d = nearest_label(q, canon, raw_voxel_distance)
        sh_correct += int(sh_pick == true_label)
        null_correct += int(null_pick == true_label)

        sh_same_max = max(sh_same_max, sh_d[true_label])
        for other in canon:
            if other != true_label:
                sh_cross_min = min(sh_cross_min, sh_d[other])

        print(f"クエリ={true_label:8s} (回転コピー)")
        print("  SH   距離: " + "  ".join(f"{k}={sh_d[k]:.4f}" for k in canon)
              + f"  -> 最近傍={sh_pick}"
              + ("  [正解]" if sh_pick == true_label else "  [誤り]"))
        print("  null 距離: " + "  ".join(f"{k}={null_d[k]:.4f}" for k in canon)
              + f"  -> 最近傍={null_pick}"
              + ("  [正解]" if null_pick == true_label else "  [誤り]"))

    n_shapes = len(canon)
    margin = sh_cross_min - sh_same_max
    print("-" * 68)
    print(f"SH   検索正解数 : {sh_correct}/{n_shapes}")
    print(f"null 検索正解数 : {null_correct}/{n_shapes}")
    print(f"SH 同形状距離の最大   : {sh_same_max:.4f} (小さいほど良い)")
    print(f"SH 異形状距離の最小   : {sh_cross_min:.4f} (大きいほど良い)")
    print(f"SH 分離マージン       : {margin:.4f} (>0 なら回転コピーを最近傍に選べる)")

    # --- 4) GT 検証(beat-the-null) ---
    # (a) SH は全クエリで正しい種類を最近傍に選ぶ(回転不変な検索が成立)。
    assert sh_correct == n_shapes, \
        f"SH 検索が全問正解でない: {sh_correct}/{n_shapes}"
    # (b) 同形状(回転)距離 < 異形状距離。マージン>0 = 判別的に分離できている。
    assert margin > 0.0, \
        f"SH の同形状/異形状が分離できていない: margin={margin:.4f}"
    # (c) beat-the-null: 素ボクセル法は SH より劣る(検索を外す、
    #     または SH ほど全問を当てられない)。SH の優位を明示的に要求。
    assert sh_correct > null_correct, \
        (f"SH が null を上回っていない: SH={sh_correct} null={null_correct} "
         f"(素ボクセルが偶然全問当たると beat-the-null が成立しない)")

    print(f"PASS: SH 検索 {sh_correct}/{n_shapes} 正解・分離マージン {margin:.4f}>0、"
          f"素ボクセル null は {null_correct}/{n_shapes} で SH が上回る")


if __name__ == "__main__":
    main()
