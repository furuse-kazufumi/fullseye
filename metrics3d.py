# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""metrics3d — 3D 再構成 / 登録の評価メトリクス(進化探索の fitness 土台)。

点群・voxel・法線・姿勢の一致度を数値化する: chamfer / Hausdorff / F-score /
completeness・accuracy / normal consistency / voxel IoU / pose error / RMSE。

これらは **3D パイプラインの進化探索で fitness としてそのまま使える**。register_auto の
ヒューリスティック選択(近=ICP / 遠=FPFH+ICP)を、これらメトリクスを最小化/最大化する
fitness ベース選択へ引き上げる鍵。すべて閉形式・GT 検証可能(同一入力→完全一致、
既知オフセット→距離=オフセット)。scipy.spatial.cKDTree のみ依存。
"""
import numpy as np


def _kd(pts):
    from scipy.spatial import cKDTree
    return cKDTree(np.asarray(pts, float))


def _require_cloud(pts, name):
    """空でない (N,3) 点群であることを入口で保証(fail-closed)。

    空点群の平均は無言の NaN になり、進化探索の fitness に毒として流れ込む
    (連鎖ファザー wave-7 実測: radius_outlier_removal が雲を空にした直後の
    chamfer_distance が NaN。同クラスを accuracy/completeness/fscore/
    normal_consistency でも実測確認し一掃)。空になるのは上流フィルタの
    パラメータ事故なので、メトリクス側は数を返さず明示的に拒否する。
    """
    p = np.asarray(pts, float)
    if p.ndim != 2 or p.shape[1] != 3:
        raise ValueError("%s must be an (N, 3) point cloud, got shape %r"
                         % (name, p.shape))
    if len(p) == 0:
        raise ValueError("%s is empty — an upstream filter (outlier removal / "
                         "cropping / downsampling) probably removed every "
                         "point; the metric would be a silent NaN" % (name,))
    return p


def _nn_dist(a, b):
    """a の各点 → b への最近傍距離。→ (Na,)。"""
    d, _ = _kd(b).query(np.asarray(a, float), k=1)
    return d


def chamfer_distance(a, b, squared=False):
    """対称 Chamfer 距離 = 0.5*(mean_a min_b + mean_b min_a)。→ scalar。小さいほど一致。

    Raises ValueError: どちらかが空 or (N,3) でない場合(空の平均 = 無言 NaN)。

    計算: ``scipy.spatial.cKDTree`` で ``a`` の各点から ``b`` への最近傍距離 ``d_ab``
    (``(Na,)``)と ``b`` から ``a`` への ``d_ba`` を取り、``0.5 * (mean(d_ab) + mean(d_ba))``。
    ``squared=True`` なら各距離を 2 乗してから平均する(単位が距離^2 になる。
    勾配ベースの最適化で使う形)。既定は生の距離(単位 = 座標の単位)。

    入力: ``a``, ``b`` は ``(N, 3)`` / ``(M, 3)`` の点群(点数は違ってよい、対応は
    不要)。float に変換する。座標系・スケールは両者で揃えておくこと(登録前の
    2 雲を比べると単に姿勢の差を測ることになる)。

    返り値: Python ``float``。同一点群なら 0。値域は ``[0, inf)`` で正規化はしない
    (雲の大きさに比例するので、比較するときは bbox 対角などで割る)。

    注意: 平均なので外れ値の影響は Hausdorff より小さいが、点密度の偏りには敏感
    (密な側の平均が支配的)。密度を揃えるには ``pc_poisson_disk`` /
    ``voxel_grid_downsample`` を先に掛ける。閾値ベースの評価は ``fscore``、最悪値は
    ``hausdorff_distance``、対応既知なら ``rmse_correspondence``。"""
    a = _require_cloud(a, "a")
    b = _require_cloud(b, "b")
    dab = _nn_dist(a, b)
    dba = _nn_dist(b, a)
    if squared:
        dab, dba = dab ** 2, dba ** 2
    return float(0.5 * (dab.mean() + dba.mean()))


def hausdorff_distance(a, b):
    """対称 Hausdorff 距離 = max(max_a min_b, max_b min_a)。→ scalar。最悪ケースの乖離。

    計算: ``cKDTree`` で ``a`` の各点から ``b`` への最近傍距離と、``b`` から ``a`` への
    最近傍距離を取り、両方向の **最大値** のうち大きい方を返す。「一方の雲のどの点も、
    相手の雲からこの距離以内にある」を保証する最小の半径。単位は座標の単位。

    入力: ``a``, ``b`` は ``(N, 3)`` / ``(M, 3)`` の点群(点数は異なってよい、対応不要)。
    **この op は入口検査を持たない**(``_require_cloud`` を通らない): 空の点群を渡すと
    ``max()`` が numpy の ``ValueError``("zero-size array")で落ち、``(N, 2)`` など
    3 列でない入力は cKDTree の次元不一致で ``ValueError`` になる — いずれも
    メッセージはこの op のものではない。呼ぶ前に空でないことを確かめること。

    返り値: Python ``float``、``[0, inf)``。同一点群なら 0。正規化はしない。

    注意: 1 点の外れ値で値が決まる(平均ではなく最大)。ノイズを含むスキャンの
    評価には ``chamfer_distance`` か ``fscore``(閾値 ``tau`` 以内の割合)の方が
    安定で、Hausdorff は「最悪でもこの精度」を主張したいとき(公差検証、
    LOD の ``max_error`` と同じ性格)に使う。"""
    return float(max(_nn_dist(a, b).max(), _nn_dist(b, a).max()))


def accuracy(a, b, tau):
    """正確性 = a の点のうち b から tau 以内にある割合(precision)。→ [0,1]。

    Raises ValueError: どちらかが空 or (N,3) でない場合(空の平均 = 無言 NaN)。"""
    return float(np.mean(_nn_dist(_require_cloud(a, "a"),
                                  _require_cloud(b, "b")) < tau))


def completeness(a, b, tau):
    """完全性 = b の点のうち a から tau 以内にある割合(recall)。→ [0,1]。

    Raises ValueError: どちらかが空 or (N,3) でない場合(空の平均 = 無言 NaN)。"""
    return float(np.mean(_nn_dist(_require_cloud(b, "b"),
                                  _require_cloud(a, "a")) < tau))


def fscore(a, b, tau):
    """F-score @ tau = precision と recall の調和平均。→ (f, precision, recall)。再構成の標準指標。

    Raises ValueError: どちらかが空 or (N,3) でない場合(accuracy/completeness 経由)。

    計算(``a`` = 再構成/推定、``b`` = 参照/GT の慣習):
    - ``precision`` = ``a`` の点のうち、``b`` への最近傍距離が ``tau`` **未満**
      (``< tau``、等号は含まない)の割合。
    - ``recall`` = ``b`` の点のうち、``a`` への最近傍距離が ``tau`` 未満の割合。
    - ``f = 2 p r / (p + r)``、``p + r == 0`` なら ``0.0``(0 除算にしない)。

    引数: ``a``, ``b`` は ``(N, 3)`` / ``(M, 3)`` 点群(対応不要、点数は異なってよい)。
    ``tau`` は距離閾値(座標と同じ単位、正の値を想定。``tau <= 0`` だと距離 0 の点も
    ``< tau`` にならず precision = recall = 0 になる。検査はしない)。

    返り値: ``(f, precision, recall)`` の 3 つの ``float``、それぞれ ``[0, 1]``。
    1 が完全一致。

    注意: ``tau`` の選び方が結果を決める(voxel サイズ・スキャン分解能の 1〜2 倍が
    目安)。片方の雲だけ密だと precision と recall が乖離する — その非対称性を見る
    のがこの指標の価値で、1 数字で良ければ ``chamfer_distance``。"""
    p = accuracy(a, b, tau)
    r = completeness(a, b, tau)
    f = 0.0 if (p + r) == 0 else 2 * p * r / (p + r)
    return f, p, r


def rmse_correspondence(a, b):
    """対応既知(同 index)の RMSE = sqrt(mean |a_i - b_i|^2)。→ scalar。登録残差の評価。

    計算: ``a``, ``b`` を float 配列にし、行ごとのユークリッド距離の 2 乗
    ``sum((a - b)**2, axis=1)`` を平均して平方根を取る。**最近傍探索はしない** —
    ``a[i]`` と ``b[i]`` が同じ点の対応であることを呼び手が保証する(登録で変換した
    ``src @ R.T + t`` と、対応する ``dst`` の点列、合成データの GT 対応など)。

    引数と検証: ``a.shape != b.shape`` なら ``ValueError``。それ以外の検査はない:
    空の ``(0, 3)`` 同士は ``mean`` が空で NaN(警告付き)を返し、``(N, 3)`` 以外でも
    ``axis=1`` で足せる形なら値を返す。3 列の点群を渡すこと。

    返り値: Python ``float``、単位は座標の単位、``[0, inf)``。同一なら 0。

    注意: 対応がずれている(index が並び替わった)雲に使うと、姿勢が正しくても
    大きな値が出る。対応不明なら ``chamfer_distance`` / ``fscore``、姿勢そのものを
    GT と比べるなら ``pose_error``。"""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if a.shape != b.shape:
        raise ValueError("correspondence points must have equal count and shape")
    return float(np.sqrt(np.mean(np.sum((a - b) ** 2, axis=1))))


def normal_consistency(points_a, normals_a, points_b, normals_b):
    """最近傍対応での法線一致度 = mean|cos(na, nb)|(向き無視)。→ [0,1]。1=完全一致。

    Raises ValueError: 点群が空 or (N,3) でない/法線が点と 1 対 1 でない場合。

    計算: ``points_a`` の各点について ``points_b`` の最近傍(``cKDTree``、``k=1``)を
    取り、その点の法線 ``nb`` と自分の法線 ``na`` を単位化(ノルム + 1e-12 で割る)
    して ``|na · nb|`` を平均する。絶対値を取るので法線の向き(表裏)の不一致は
    無視される。**非対称**(``a`` → ``b`` の一方向のみ。逆向きが要るなら引数を入れ替えて
    もう一度呼ぶ)。

    引数: ``points_a`` ``(N, 3)``、``normals_a`` ``(N, 3)``、``points_b`` ``(M, 3)``、
    ``normals_b`` ``(M, 3)``。4 つとも空でない ``(*, 3)`` であること、法線の行数が
    対応する点群の行数と一致することを検査する(違反は ``ValueError``)。ゼロ法線は
    ``1e-12`` で割られてほぼ 0 の寄与になる(エラーにしない)。

    返り値: Python ``float``、``[0, 1]``。1 = 全対応で法線が平行。乱雑な法線対なら
    3-D では期待値 0.5 程度になる(cos の絶対値の平均)。

    注意: 位置の近さは見ない(遠い最近傍でも法線だけ比べる)。位置と合わせて評価する
    なら ``chamfer_distance`` / ``fscore`` と併用する。法線が無い雲は
    ``estimate_point_normals``(局所 PCA)で作ってから渡す。"""
    from scipy.spatial import cKDTree
    pa = _require_cloud(points_a, "points_a")
    pb = _require_cloud(points_b, "points_b")
    na = _require_cloud(normals_a, "normals_a")
    nb_all = _require_cloud(normals_b, "normals_b")
    if len(na) != len(pa) or len(nb_all) != len(pb):
        raise ValueError("normals must pair one normal with each point — "
                         "points_a %d/normals_a %d, points_b %d/normals_b %d"
                         % (len(pa), len(na), len(pb), len(nb_all)))
    _, idx = cKDTree(pb).query(pa, k=1)
    nb = nb_all[idx]
    na = na / (np.linalg.norm(na, axis=1, keepdims=True) + 1e-12)
    nb = nb / (np.linalg.norm(nb, axis=1, keepdims=True) + 1e-12)
    return float(np.mean(np.abs(np.sum(na * nb, axis=1))))


def voxel_iou(vol_a, vol_b, iso=0.5):
    """voxel 占有の IoU(intersection over union)。→ [0,1]。体積一致度。

    両 volume は同一 shape が必須。異形状は numpy broadcasting で見かけ上一致し
    誤った IoU(例: (10,1,10) vs (1,10,10) → 1.0)を静かに返すので、fail-closed で
    shape 不一致は ValueError で拒否する。

    計算: 両 volume を ``>= iso`` で二値化し(``iso`` 既定 0.5、等号を含む)、
    ``|A∩B| / |A∪B|``。和集合が空(両方とも占有ゼロ)なら ``1.0`` を返す
    (「どちらも空」は一致とみなす。エラーにしない)。

    引数: ``vol_a``, ``vol_b`` は同じ shape の配列(3-D に限らず、次元数は検査しない。
    bool / 0-1 / 密度 grid のいずれでもよい)。``iso`` は占有とみなす閾値で、
    ``fuse_to_voxel`` や ``points_to_voxel`` の密度 grid(値は点数)に使うなら
    ``iso=1`` 以上を明示する。NaN は ``>=`` で False(非占有)になる。

    返り値: Python ``float``、``[0, 1]``。1 = 完全一致、0 = 重なりなし。

    注意: 同じ格子(``bounds`` と ``size``)に載っていないと比較にならない —
    ``fuse_to_voxel`` / ``points_to_voxel`` には同じ ``bounds`` を渡す。薄い殻同士は
    1 voxel ずれるだけで IoU が大きく落ちるので、表面の評価には
    ``chamfer_distance`` / ``fscore`` の方が向く。体積が小さい対象は Dice
    (``voxel_dice``、同モジュールの関数)の方が慣習として使われる。"""
    a = np.asarray(vol_a)
    b = np.asarray(vol_b)
    if a.shape != b.shape:
        raise ValueError(
            f"voxel_iou: both volumes must have the same shape (got {a.shape} and {b.shape})")
    a = a >= iso
    b = b >= iso
    inter = int(np.logical_and(a, b).sum())
    union = int(np.logical_or(a, b).sum())
    return float(inter / union) if union > 0 else 1.0


def voxel_dice(vol_a, vol_b, iso=0.5):
    """voxel 占有の Dice 係数 = 2|A∩B|/(|A|+|B|)。→ [0,1]。医用でよく使う。

    voxel_iou と同じく、異形状は broadcasting で無意味な値(Dice>1 すら起こる)を
    返すため fail-closed で shape 不一致は ValueError。"""
    a = np.asarray(vol_a)
    b = np.asarray(vol_b)
    if a.shape != b.shape:
        raise ValueError(
            f"voxel_dice: both volumes must have the same shape (got {a.shape} and {b.shape})")
    a = a >= iso
    b = b >= iso
    sa, sb = int(a.sum()), int(b.sum())
    inter = int(np.logical_and(a, b).sum())
    return float(2 * inter / (sa + sb)) if (sa + sb) > 0 else 1.0


def pose_error(R_est, t_est, R_gt, t_gt):
    """姿勢誤差 = (回転角[度], 並進ノルム)。登録結果の GT 比較。→ (rot_deg, trans_err)。

    計算:
    - 回転: ``dR = R_est.T @ R_gt`` の回転角 ``arccos((trace(dR) - 1) / 2)`` を度に
      直す(``cos`` は ``[-1, 1]`` にクリップして丸め誤差で NaN にしない)。値域
      ``[0, 180]`` 度。``R_est == R_gt`` なら 0。
    - 並進: ``|t_est - t_gt|``(ユークリッドノルム、座標と同じ単位)。

    引数: ``R_est``, ``R_gt`` は ``(3, 3)``、``t_est``, ``t_gt`` は長さ 3。float に
    変換するだけで **形・直交性の検査はしない** — ``R`` が回転行列でない(反射・
    スケール入り)と ``trace`` の式は意味を失い、``(3, 3)`` 以外は行列積の
    ``ValueError`` か無意味な値になる。``register_fpfh`` / ``icp_point2point_3d`` /
    ``register_cross`` の返り値 ``(R, t)`` と GT の ``(R, t)`` を、同じ慣習
    (``dst ≈ src @ R.T + t``)で渡すこと。

    返り値: ``(rot_deg, trans_err)`` の 2 つの ``float``。

    注意: 並進誤差は回転誤差と結合している(原点から遠い対象では小さな回転誤差が
    大きな並進誤差として現れる)。点群上の実効誤差を見るなら、変換後の雲同士を
    ``rmse_correspondence``(対応既知)か ``chamfer_distance`` で比べる。"""
    Re = np.asarray(R_est, float)
    Rg = np.asarray(R_gt, float)
    dR = Re.T @ Rg
    cos = np.clip((np.trace(dR) - 1.0) / 2.0, -1.0, 1.0)
    rot = float(np.degrees(np.arccos(cos)))
    trans = float(np.linalg.norm(np.asarray(t_est, float) - np.asarray(t_gt, float)))
    return rot, trans


def m3c2_distance(a, b, cores, normals, radius, max_depth=None, min_points=4):
    """2 時点の点群の差を**法線方向に**測る(M3C2)。→ ``(distance, lod)`` の 2 つ。

    最近傍距離(chamfer / C2C)は「いちばん近い点までの距離」なので、**傾いた面では
    面に沿ったずれまで距離として数えてしまう**。地形・構造物の変化検出では、それが
    「測り直しただけで検出される偽の変化」の主因になる(`poc_structure_4d_deterioration`
    の実測: 劣化ゼロで測り返しただけで C2C の中央値 21.07 mm、法線方向なら 0.55 mm)。

    M3C2(Lague 2013)は core 点ごとに **法線 ``n`` を軸とする円筒**(半径 ``radius``、
    長さ ``max_depth``)で両方の雲を切り取り、各点を ``n`` に射影した平均の差を返す。
    向きは ``n`` の指す側が正 —— **符号がそのまま「増えた / 減った」**になる。

    Args:
        a: 時点 1 の点群 ``(Na,3)``。
        b: 時点 2 の点群 ``(Nb,3)``。
        cores: 測る場所 ``(M,3)``(a の部分集合でも、別に置いた格子でもよい)。
        normals: core ごとの法線 ``(M,3)``(未正規化でよい。**符号が結果の符号を決める**)。
        radius: 円筒の半径(core 周りで平均する範囲。面の粗さより大きく、測りたい
            構造より小さく取る)。
        max_depth: 円筒の長さの半分。``None`` なら軸方向を制限しない。
        min_points: 片側にこの数だけ点が無い core は ``nan`` を返す(既定 4)。

    Returns:
        ``(distance, lod)``: どちらも ``(M,)`` float64。``distance`` は法線方向の
        符号つき差、``lod``(level of detection)は
        ``1.96·sqrt(σa²/na + σb²/nb)`` —— **この値を超えない差は雑音と区別できない**。
        点が足りない core は両方 ``nan``。

        ★台帳経由(``fullseye.ledger.m3c2_distance``)は宣言 out 型の ``distance`` だけを
        返す。``lod`` も要るときは ``fullseye.ledger.m3c2_distance.raw(...)``。

    Raises:
        ValueError: 点群 / cores が ``(N,3)`` でない、空、``normals`` の数が cores と
        合わない、``radius <= 0``、``max_depth <= 0``、``min_points < 1`` のとき。

    **限界(honest)**: (1) 法線は呼び手が与える —— `estimate_normals` の符号は任意なので、
    向きを揃えないと符号が場所ごとに反転する。(2) ``lod`` は雑音だけを見ており、
    **位置合わせの残差は含まない**(Lague の原論文は登録誤差を別項として足す)。
    (3) 円筒に入る点が少ない縁では ``nan`` になる —— 0 を返して「変化なし」に
    見せない。

    Reference (public): D. Lague, N. Brodu, J. Leroux, "Accurate 3D comparison of
    complex topography with terrestrial laser scanner: application to the Rangitikei
    canyon (N-Z)", ISPRS Journal of Photogrammetry and Remote Sensing 82 (2013) 10-26.
    """
    from scipy.spatial import cKDTree

    A = _require_cloud(a, "a")
    B = _require_cloud(b, "b")
    C = _require_cloud(cores, "cores")
    N = np.asarray(normals, float)
    if N.ndim != 2 or N.shape[1] != 3 or len(N) != len(C):
        raise ValueError("normals must be (M, 3) pairing one normal with each core "
                         "point (got %r for %d cores)" % (N.shape, len(C)))
    r = float(radius)
    if not np.isfinite(r) or r <= 0:
        raise ValueError("radius must be a positive finite number")
    if max_depth is not None:
        md = float(max_depth)
        if not np.isfinite(md) or md <= 0:
            raise ValueError("max_depth must be a positive finite number or None")
    else:
        md = None
    mp = int(min_points)
    if mp < 1:
        raise ValueError("min_points must be at least 1")

    nn = np.linalg.norm(N, axis=1, keepdims=True)
    if np.any(nn <= 0) or not np.all(np.isfinite(nn)):
        raise ValueError("normals must be non-zero finite vectors")
    N = N / nn

    # 円筒に入りうる点は「半径 sqrt(r^2 + md^2) の球」の中にしかない。球で粗く絞って
    # から軸・半径で厳密に判定する(全点との内積を M 回やるより速い)。
    reach = r if md is None else float(np.hypot(r, md))
    ta, tb = cKDTree(A), cKDTree(B)
    ia = ta.query_ball_point(C, reach)
    ib = tb.query_ball_point(C, reach)

    dist = np.full(len(C), np.nan)
    lod = np.full(len(C), np.nan)
    for k in range(len(C)):
        c, n = C[k], N[k]
        stats = []
        for idx, P in ((ia[k], A), (ib[k], B)):
            if not idx:
                stats.append(None)
                continue
            d = P[idx] - c
            t = d @ n                            # 軸方向(符号つき)
            perp = np.linalg.norm(d - t[:, None] * n, axis=1)
            keep = perp <= r
            if md is not None:
                keep &= np.abs(t) <= md
            if int(keep.sum()) < mp:
                stats.append(None)
                continue
            tv = t[keep]
            stats.append((float(tv.mean()), float(tv.std(ddof=1)) if tv.size > 1 else 0.0,
                          int(tv.size)))
        if stats[0] is None or stats[1] is None:
            continue
        (ma, sa, na), (mb, sb, nb) = stats
        dist[k] = mb - ma
        lod[k] = 1.96 * float(np.sqrt(sa * sa / na + sb * sb / nb))
    return dist, lod
