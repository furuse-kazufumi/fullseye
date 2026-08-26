"""ops3d — fullseye 3D ビジョン op の統一レジストリ(全 op を一望・組み合わせ可能に)。

散らばった 3D op(match3d / feat_* / fuse3d)を 1 つのカタログに「対応」させ、カテゴリ・入出力の
種別・GPU 対応・一行説明を付ける。これにより **op × op の組み合わせ**(あるカテゴリの出力 = 別の
op の入力)を機械的に列挙・スコアリングでき、指数的な拡張候補を優先度づけできる(docs/OP_COMBINATION_MATRIX.md)。

使い方:
    import ops3d
    ops3d.list_ops("match_localize")        # カテゴリ内の op 名
    ops3d.get("match_shape_3d")(...)        # 実体を取得して呼ぶ
    ops3d.compatible("register_fpfh")       # 出力が別 op の入力になる後続候補
"""
import match3d
import feat_harris
import feat_spin
import feat_shot
import feat_fpfh
import fuse3d

_MOD = {"match3d": match3d, "feat_harris": feat_harris, "feat_spin": feat_spin,
        "feat_shot": feat_shot, "feat_fpfh": feat_fpfh, "fuse3d": fuse3d}

# 入出力の「種別」語彙(op 連結の型検査に使う):
#   voxel / points / mesh / depth / sdf / normals / gaussians / image2d /
#   pose(R,t) / transform-params(angle,scale,shift) / position / primitive(plane/sphere/...) /
#   descriptor / keypoints / flow / measurement(scalar) / render(image2d)

# カテゴリ → [(op 名, module, [入力種別], 出力種別, gpu)]
_CATALOG = {
    "transform": [  # データ形式の変換(構造 → 別構造/共通表現)
        ("points_to_voxel", "match3d", ["points"], "voxel", True),
        ("gaussians_to_voxel", "match3d", ["gaussians"], "voxel", True),
        ("mesh_to_voxel", "match3d", ["mesh"], "voxel", True),
        ("mesh_to_points", "match3d", ["mesh"], "points", False),
        ("depth_to_points", "match3d", ["depth"], "points", False),
        ("voxel_to_mips", "match3d", ["voxel"], "image2d", False),
        ("voxel_to_mesh", "match3d", ["voxel"], "mesh", False),
        ("tsdf_from_depth", "match3d", ["depth"], "sdf", False),
        ("signed_distance_field", "match3d", ["voxel"], "sdf", True),
        ("sdf_to_occupancy", "match3d", ["sdf"], "voxel", False),
        ("estimate_point_normals", "match3d", ["points"], "normals", False),
        ("to_points", "fuse3d", ["voxel", "points", "mesh", "depth", "gaussians"], "points", False),
    ],
    "feature": [  # 微分/曲率など局所特徴場
        ("sobel3d", "match3d", ["voxel"], "gradient", True),
        ("hessian3d", "match3d", ["voxel"], "hessian", True),
        ("curvature_maps", "match3d", ["voxel"], "curvature", True),
        ("edt_jfa", "match3d", ["voxel"], "sdf", True),
    ],
    "morphology": [  # 3D モルフォロジー(前処理/特徴抽出)
        ("morph_dilate3d", "match3d", ["voxel"], "voxel", True),
        ("morph_erode3d", "match3d", ["voxel"], "voxel", True),
        ("morph_gradient3d", "match3d", ["voxel"], "voxel", True),
        ("morph_tophat3d", "match3d", ["voxel"], "voxel", True),
        ("morph_blackhat3d", "match3d", ["voxel"], "voxel", True),
    ],
    "match_localize": [  # scene 内でテンプレ位置を出す
        ("match_shape_3d", "match3d", ["voxel", "voxel"], "position", True),
        ("match_chamfer_3d", "match3d", ["voxel", "voxel"], "position", True),
        ("match_curvature_3d", "match3d", ["voxel", "voxel"], "position", True),
        ("match_hough_3d", "match3d", ["voxel", "voxel"], "position", True),
        ("match_mip_2d", "match3d", ["voxel", "voxel"], "position", True),
        ("match_points_ncc", "match3d", ["points", "points"], "position", True),
    ],
    "match_pose": [  # 変換パラメータを出す
        ("match_phase_3d", "match3d", ["voxel", "voxel"], "shift", True),
        ("match_pca", "match3d", ["points", "points"], "pose", False),
        ("moment_axes", "match3d", ["points"], "axes", False),
        ("match_logpolar_z", "match3d", ["voxel", "voxel"], "rot_scale", True),
    ],
    "detect": [  # テンプレ不要の原始形状検出
        ("hough_plane_3d", "match3d", ["voxel"], "primitive", True),
        ("hough_sphere_3d", "match3d", ["voxel"], "primitive", True),
    ],
    "describe": [  # 回転不変な大域記述子/照合
        ("sh_descriptor", "match3d", ["voxel"], "descriptor", True),
        ("match_sh_descriptor", "match3d", ["voxel", "voxel"], "measurement", True),
    ],
    "refine": [  # 粗推定 → 高精度収束
        ("refine_peak_newton", "match3d", ["score", "position"], "position", True),
        ("refine_translation_lk", "match3d", ["voxel", "voxel", "position"], "position", True),
        ("refine_lm", "match3d", ["voxel", "voxel", "position"], "pose", True),
        ("refine_rotation_z", "match3d", ["voxel", "voxel", "angle"], "angle", True),
        ("icp_point2point_3d", "match3d", ["points", "points"], "pose", False),
        ("icp_point2plane", "match3d", ["points", "points", "normals"], "pose", False),
    ],
    "motion": [
        ("scene_flow_lk", "match3d", ["voxel", "voxel"], "flow", True),
    ],
    "feature_register": [  # 疎特徴 keypoint + 記述子 + RANSAC(初期推定なし大回転)
        ("harris3d_keypoints", "feat_harris", ["voxel"], "keypoints", True),
        ("iss_keypoints", "feat_shot", ["points"], "keypoints", False),
        ("compute_fpfh", "feat_fpfh", ["points", "normals"], "descriptor", False),
        ("shot_descriptor", "feat_shot", ["points", "normals"], "descriptor", False),
        ("register_spin", "feat_spin", ["points", "points"], "pose", False),
        ("register_fpfh", "feat_fpfh", ["points", "points"], "pose", False),
        ("register_shot", "feat_shot", ["points", "points"], "pose", False),
    ],
    "fusion": [  # 全5構造を組み合わせる(TRIZ 統合)
        ("register_cross", "fuse3d", ["any", "any"], "pose", False),
        ("fuse_to_voxel", "fuse3d", ["any"], "voxel", True),
    ],
    "geometry": [  # 幾何メトロロジー(2点→線・3点→面/角度)
        ("line_from_2points", "match3d", ["points"], "primitive", False),
        ("plane_from_3points", "match3d", ["points"], "primitive", False),
        ("angle_3points", "match3d", ["points"], "measurement", False),
        ("angle_between_lines", "match3d", ["primitive"], "measurement", False),
        ("angle_between_planes", "match3d", ["primitive"], "measurement", False),
        ("angle_line_plane", "match3d", ["primitive"], "measurement", False),
        ("distance_point_plane", "match3d", ["points", "primitive"], "measurement", False),
        ("distance_point_line", "match3d", ["points", "primitive"], "measurement", False),
        ("distance_line_line", "match3d", ["primitive"], "measurement", False),
        ("intersect_line_plane", "match3d", ["primitive"], "position", False),
        ("intersect_planes", "match3d", ["primitive"], "primitive", False),
        ("fit_line_3d", "match3d", ["points"], "primitive", False),
        ("fit_plane_3d", "match3d", ["points"], "primitive", False),
        ("fit_sphere_3d", "match3d", ["points"], "primitive", False),
        ("fit_circle_3d", "match3d", ["points"], "primitive", False),
    ],
    "surface_fit": [  # 曲面近似 z=f(x,y)
        ("fit_poly_surface", "match3d", ["image2d"], "surface", False),
        ("eval_poly_surface", "match3d", ["surface"], "image2d", False),
        ("surface_form_error", "match3d", ["image2d"], "measurement", False),
        ("background_flatten", "match3d", ["image2d"], "image2d", False),
    ],
    "curvilinear": [  # 曲座標系への展開
        ("polar_unwrap", "match3d", ["image2d"], "image2d", True),
        ("cylinder_unwrap", "match3d", ["voxel"], "image2d", True),
        ("fit_zernike", "match3d", ["image2d"], "descriptor", True),
    ],
    "optics": [  # 鏡面/透明体
        ("reflect", "match3d", ["vector", "normals"], "vector", False),
        ("refract", "match3d", ["vector", "normals"], "vector", False),
        ("fresnel_reflectance", "match3d", ["measurement"], "measurement", False),
        ("normal_from_reflection", "match3d", ["vector", "vector"], "normals", False),
        ("snell_angle", "match3d", ["measurement"], "measurement", False),
    ],
    "render": [  # 射影/レンダリング(3D → 2D 合成、ループを閉じる)
        ("project_points", "match3d", ["points"], "image2d", False),
        ("render_point_depth", "match3d", ["points"], "depth", False),
        ("render_volume_projection", "match3d", ["voxel"], "image2d", True),
        ("render_shaded", "match3d", ["normals"], "image2d", False),
    ],
}


def _build():
    reg = {}
    for cat, entries in _CATALOG.items():
        for name, mod, ins, out, gpu in entries:
            fn = getattr(_MOD[mod], name, None)
            doc = ""
            if fn is not None and fn.__doc__:
                doc = fn.__doc__.strip().splitlines()[0]
            reg[name] = {"category": cat, "module": mod, "in": ins, "out": out,
                         "gpu": gpu, "func": fn, "doc": doc}
    return reg


OPS3D = _build()


def list_ops(category=None):
    """op 名の一覧(category 指定で絞る)。"""
    return [n for n, m in OPS3D.items() if category is None or m["category"] == category]


def categories():
    """カテゴリ一覧。"""
    return list(_CATALOG.keys())


def get(name):
    """op 名 → 実体(callable)。"""
    return OPS3D[name]["func"]


def info(name):
    """op のメタ情報。"""
    return OPS3D[name]


def compatible(name):
    """name の出力種別を入力に取れる後続 op(op × op の連結候補)を列挙。"""
    out = OPS3D[name]["out"]
    return [n for n, m in OPS3D.items()
            if out in m["in"] or "any" in m["in"]]


def missing():
    """レジストリに載っているが実体が見つからない op(健全性チェック)。"""
    return [n for n, m in OPS3D.items() if m["func"] is None]


if __name__ == "__main__":
    print(f"ops3d: {len(OPS3D)} ops / {len(categories())} categories")
    miss = missing()
    print("missing:", miss if miss else "なし(全 op 実体あり)")
    for c in categories():
        print(f"  [{c}] {len(list_ops(c))} ops")
