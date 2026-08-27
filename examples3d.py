"""examples3d — the worked-example gallery for Fullseye's 3-D vision toolkit.

The 3-D operators (``ops3d`` — 230 typed ops) solve real Physical-AI perception
problems, but an operator no one can *find or run* is invisible. This module is the
discoverable index: every entry is a **self-contained, self-asserting runnable
script** under ``examples_3d/`` that loads data, calls the toolkit, prints a
ground-truth check and asserts it. Studio's "3-D Examples" gallery and
``docs/EXAMPLES_3D.md`` both source their list from here, and :func:`validate`
runs every script so the gallery only ever advertises examples that actually work.

Three data provenances, so the examples run on genuine shapes, not just spheres:

  * ``synthetic``     — controllable synthetic data with exact ground truth.
  * ``skeleton_ct``   — a hand-skeleton X-ray-CT phantom voxelised from the real
                        MS-Human-700 anatomical bone meshes (volumetric / tomography).
  * ``itokawa``       — a decimated surface cloud of asteroid 25143 Itokawa from the
                        public-domain Gaskell shape model (JAXA Hayabusa; see
                        ``studio_assets/sample_3d/ATTRIBUTION.md``).

Usage::

    import examples3d
    examples3d.names()                      # every example id
    examples3d.by_task()["registration"]    # ids grouped by task
    print(examples3d.code("cad_to_scan"))   # the runnable source
    examples3d.validate()                   # run all; returns {id: (ok, note)}

Each script is also runnable directly::

    PYTHONPATH=<repo> py -3.11 examples_3d/cad_to_scan.py
"""
from __future__ import annotations

import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(_ROOT, "examples_3d")

# id -> metadata. `name`/`summary` are plain-language (what real problem it solves);
# `task` groups the gallery; `data` is the provenance (synthetic / skeleton_ct / itokawa).
# Every id maps to examples_3d/<id>.py. All entries are verified by :func:`validate`.
EXAMPLES = [
    # -- registration ------------------------------------------------------------ #
    {"id": "cad_to_scan", "task": "registration", "data": "synthetic",
     "name": "CADモデルをノイズ入り3Dスキャンに位置合わせ",
     "summary": "初期姿勢なしで CAD 設計形状を実物スキャン点群に合わせ、置かれた向きと位置を復元する(FPFH+RANSACで粗く→ICPでセンサノイズ床まで)。"},
    {"id": "auto_register", "task": "registration", "data": "synthetic",
     "name": "手法を自動選択する点群登録",
     "summary": "2点群の近さを見て、近ければ ICP・大きく離れていれば FPFH+ICP を自動選択する(手法指定不要)。"},
    {"id": "reg_eval", "task": "registration", "data": "synthetic",
     "name": "登録品質の評価(recall/RMSE/inlier)",
     "summary": "登録結果が成功か失敗かを inlier率・RMSE・recall で定量化。対応ゼロでは NaN を返し捏造しない。"},
    {"id": "two_view_pose", "task": "registration", "data": "synthetic",
     "name": "2視点からの相対カメラ姿勢(SfM初期化)",
     "summary": "2枚の画像の対応点から基礎/基本行列を解き、相対カメラ姿勢と3D点を復元する(単眼SfM/VOの初手)。"},
    {"id": "bundle_adjust", "task": "registration", "data": "synthetic",
     "name": "N視点バンドル調整による精緻化",
     "summary": "全カメラ姿勢と3D構造を再投影誤差最小で同時最適化し、摂動から機械精度へ回復する。"},
    {"id": "pose_graph_slam", "task": "registration", "data": "synthetic",
     "name": "ループ閉じ込みのポーズグラフSLAMバックエンド",
     "summary": "ノイズ入りオドメトリ+ループ閉じ辺を最適化し、蓄積したドリフトを低減する。"},
    # -- metrology --------------------------------------------------------------- #
    {"id": "plane_flatness", "task": "metrology", "data": "synthetic",
     "name": "平面度メトロロジー(基準面からの偏差)",
     "summary": "点群に平面を当て、基準面からの偏差=平面度を測る。既知の膨らみ高さと一致することで検証。"},
    {"id": "roundness", "task": "metrology", "data": "synthetic",
     "name": "真球度/丸さ検査",
     "summary": "点群に球を当て、真球からの偏差=真球度を測る。完全な球ほど偏差が小さいことを確認。"},
    {"id": "ransac_prim", "task": "metrology", "data": "synthetic",
     "name": "30%外れ値下での頑健プリミティブ適合",
     "summary": "平面/球/円柱を RANSAC で当て、外れ値30%が混じってもパラメータを正しく復元する。"},
    # -- depth ------------------------------------------------------------------- #
    {"id": "plane_sweep_depth", "task": "depth", "data": "synthetic",
     "name": "2視点プレーンスイープ・ステレオ深度",
     "summary": "既知カメラの2画像から、深度平面を掃引して photo-consistency 最小の深度を画素ごとに選ぶ。"},
    {"id": "depth_denoise", "task": "depth", "data": "synthetic",
     "name": "エッジ保存の深度デノイズ+穴埋め",
     "summary": "段差を跨がずにノイズを平滑化し、浅い穴を調和補間で埋める(深い穴はNaNのまま残す)。"},
    # -- reconstruction / modeling ---------------------------------------------- #
    {"id": "denoise_evolution", "task": "reconstruction", "data": "synthetic",
     "name": "進化探索で見つけた点群デノイズ・パイプライン",
     "summary": "外れ値除去・平滑化・間引きの順番を遺伝的アルゴリズムに探させ、無処理と人手の定番を上回る。"},
    {"id": "tsdf_fusion_demo", "task": "reconstruction", "data": "synthetic",
     "name": "複数深度フレームをTSDFで融合し表面抽出",
     "summary": "複数視点の深度観測を TSDF に融合し、単一観測よりノイズに頑健な表面を得る。"},
    {"id": "sdf_csg", "task": "modeling", "data": "synthetic",
     "name": "SDFのCSG合成(和/差)でソリッドを作りメッシュ化",
     "summary": "符号付き距離場の集合演算(球∪箱−小球)で陰関数ソリッドを作り、等値面をメッシュへ。"},
    # -- features ---------------------------------------------------------------- #
    {"id": "curvature_grasp", "task": "features", "data": "synthetic",
     "name": "主曲率・形状指数による把持アフォーダンス",
     "summary": "点群の主曲率と形状指数から、球・円柱・鞍点を識別する(把持面の当たり判定)。"},
    {"id": "symmetry", "task": "features", "data": "synthetic",
     "name": "反射・回転対称性の検出",
     "summary": "点群の反射面と回転対称の位数を chamfer 採点で検出する。"},
    {"id": "shape_retrieval", "task": "features", "data": "synthetic",
     "name": "大域記述子(D2/A3)による形状検索",
     "summary": "距離分布 D2・角分布 A3 の大域記述子で、回転しても同形状は近く・異形状は遠く照合する。"},
    {"id": "motion_seg", "task": "motion", "data": "synthetic",
     "name": "動的シーンの剛体運動セグメンテーション",
     "summary": "2時刻の点群から、別々に動く剛体ごとに分割する。無相関ノイズでは剛体を捏造しない。"},
    # -- skeleton CT (real anatomical bone geometry, volumetric) ----------------- #
    {"id": "ct_hand_radiograph", "task": "depth", "data": "skeleton_ct",
     "name": "骨格CTからX線ラジオグラフ(DRR)を合成",
     "summary": "手骨のCT密度ボリュームを厚み方向に積算し、2次元の手のX線像(DRR)を合成する。"},
    {"id": "ct_bone_segmentation", "task": "modeling", "data": "skeleton_ct",
     "name": "CTボリュームから骨をセグメンテーションし、接触骨を分離して計数・体積計測",
     "summary": "骨を閾値化し、関節で繋がる指骨を収縮で分離してから連結成分で数え、体積を測る(閾値内外の密度コントラストで検証)。"},
    {"id": "ct_surface_extraction", "task": "modeling", "data": "skeleton_ct",
     "name": "CTボリュームから骨表面メッシュを抽出(marching cubes)",
     "summary": "CTボリュームに marching cubes をかけ、骨表面を三角メッシュ化する(3Dプリント/FEA向け)。"},
    {"id": "ct_sparse_view_recon", "task": "depth", "data": "skeleton_ct",
     "name": "低線量スパースビューCT再構成(radon→SART)",
     "summary": "指の断面をX線投影し、SART(反復)とFBPで再構成する。低線量ゆえの控えめな品質を正直に評価。"},
    # -- Itokawa asteroid (real Gaskell shape model, public domain) -------------- #
    {"id": "itokawa_pose_canonical", "task": "registration", "data": "itokawa",
     "name": "小惑星の姿勢を主成分で正準化",
     "summary": "不明な向きで届いた小惑星形状を、慣性主軸で形状固有の正準姿勢へ整える(カタログ化・比較用)。"},
    {"id": "itokawa_self_register", "task": "registration", "data": "itokawa",
     "name": "未知姿勢で置かれた小惑星スキャンの位置合わせ",
     "summary": "未知の探査機姿勢で撮った小惑星スキャンを ICP で基準形状に戻す。不規則形状は球と違い登録できる。"},
    {"id": "itokawa_curvature", "task": "features", "data": "itokawa",
     "name": "小惑星表面の曲率解析(尾根・クレーターの検出)",
     "summary": "表面の主曲率・曲率度・形状指数を求め、平坦部と尾根/窪みを仕分ける(値が実在表面の幾何であることを近傍相関で確認)。"},
    {"id": "itokawa_shape_match", "task": "features", "data": "itokawa",
     "name": "chamfer距離による形状照合",
     "summary": "chamfer 距離で「同一の天体か別物か」を数値判定する(自身の回転コピーは近く・同大の球は遠い)。"},
    {"id": "itokawa_symmetry_honest", "task": "features", "data": "itokawa",
     "name": "対称性検出(正直な結果:小惑星は非対称)",
     "summary": "反射対称スコアを小惑星と対称な楕円体で比較。ラブルパイル小惑星は非対称=検出器が正しく低スコアを返す。"},
    # -- pose estimation --------------------------------------------------------- #
    {"id": "pose_estimation", "task": "pose_estimation", "data": "synthetic",
     "name": "外れ値ありの3D-2D対応からカメラ6自由度姿勢を推定(PnP+RANSAC)",
     "summary": "既知寸法の箱の3D-2D対応(30%外れ値・0.5px雑音)から pnp_ransac で姿勢復元。回転<2度・並進<2%で、恒等姿勢や素のDLTを明確に上回る。"},
    # -- segmentation ------------------------------------------------------------ #
    {"id": "object_segmentation", "task": "segmentation", "data": "synthetic",
     "name": "ビンピッキング: 台平面除去→物体クラスタリング",
     "summary": "地面平面を plane_segmentation で剥がし、残りを euclidean_cluster で3物体に分離。クラスタ数・重心が真値一致、全点1クラスタ扱いの零点を上回る。"},
    # -- mapping ----------------------------------------------------------------- #
    {"id": "occupancy_esdf", "task": "mapping", "data": "synthetic",
     "name": "占有格子+ESDFで連続クリアランスを問い合わせ",
     "summary": "部屋点群から occupancy_grid→esdf を作り、自由空間点で最近接障害物までの連続距離を query_distance。占有0/1のみの零点を約39倍上回る(衝突回避マージン判定)。"},
    # -- shape fitting ----------------------------------------------------------- #
    {"id": "superquadric_fit", "task": "shape_fitting", "data": "synthetic",
     "name": "点群から角丸ブロックをスーパー楕円体で当てはめ",
     "summary": "既知スーパー楕円体からの雑音点群を fit_superquadric で復元(半径5%以内・内外分類>95%)。球1個を当てた残差を大きく下回る(把持点判定向け)。"},
    # -- motion ------------------------------------------------------------------ #
    {"id": "scene_flow_rigid", "task": "motion", "data": "synthetic",
     "name": "剛体シーンフロー(既知R,tと密フィールドの復元)",
     "summary": "点群を既知剛体変換で動かし rigid_flow で復元(回転<1度・並進<1voxel)。smooth_flow が生NN流のEPEを約半分に、residual_flow は剛体部でノイズ床。"},
    # -- shape descriptors ------------------------------------------------------- #
    {"id": "moment_invariants", "task": "shape_descriptors", "data": "synthetic",
     "name": "3Dモーメント不変量(剛体+一様スケールに不変)",
     "summary": "点群に既知の平行移動・回転・一様スケールを掛けても moment_invariants はほぼ不変で、別形状とは明確に区別。生モーメントは同変換で大きく変動。"},
    # -- shape analysis ---------------------------------------------------------- #
    {"id": "medial_topology", "task": "shape_analysis", "data": "synthetic",
     "name": "中軸骨格と位相署名で形状を区別",
     "summary": "中実円柱の芯を skeletonize_vol/medial_axis_points で抽出(既知中心軸上)、topology_signature+medial_match でトーラス(genus1)を球/円柱と区別。ランダム署名の零点を上回る。"},
]

_BY_ID = {e["id"]: e for e in EXAMPLES}


def names() -> list[str]:
    """Every example id, in gallery order."""
    return [e["id"] for e in EXAMPLES]


def get(example_id: str) -> dict:
    """Metadata dict for an example id (KeyError if unknown)."""
    return _BY_ID[example_id]


def tasks() -> list[str]:
    """Distinct task categories, in first-seen order."""
    seen = []
    for e in EXAMPLES:
        if e["task"] not in seen:
            seen.append(e["task"])
    return seen


def by_task() -> dict:
    """``{task: [id, ...]}`` for grouping the gallery."""
    out: dict[str, list[str]] = {}
    for e in EXAMPLES:
        out.setdefault(e["task"], []).append(e["id"])
    return out


def by_data() -> dict:
    """``{provenance: [id, ...]}`` — synthetic / skeleton_ct / itokawa."""
    out: dict[str, list[str]] = {}
    for e in EXAMPLES:
        out.setdefault(e["data"], []).append(e["id"])
    return out


def path(example_id: str) -> str:
    """Absolute path to the runnable script for an example id."""
    return os.path.join(DIR, example_id + ".py")


def code(example_id: str) -> str:
    """The runnable source of an example (for the 'view code' gallery panel)."""
    with open(path(example_id), encoding="utf-8") as f:
        return f.read()


def discover() -> list[str]:
    """Every ``examples_3d/*.py`` on disk (superset check against EXAMPLES)."""
    if not os.path.isdir(DIR):
        return []
    return sorted(f[:-3] for f in os.listdir(DIR)
                  if f.endswith(".py") and not f.startswith("_"))


def run(example_id: str, timeout: int = 240) -> tuple[bool, str]:
    """Run one example as a subprocess (repo root on PYTHONPATH). -> (ok, tail_output)."""
    env = dict(os.environ)
    env["PYTHONPATH"] = _ROOT + os.pathsep + env.get("PYTHONPATH", "")
    env["PYTHONUTF8"] = "1"
    try:
        p = subprocess.run([sys.executable, path(example_id)], cwd=_ROOT, env=env,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return False, "timeout"
    tail = (p.stdout or "").strip().splitlines()
    note = tail[-1] if tail else (p.stderr or "").strip().splitlines()[-1:] or ""
    return p.returncode == 0, (note if isinstance(note, str) else " ".join(note))


def validate(ids=None) -> dict:
    """Run each example and report which are usable -> ``{id: (ok, note)}``.

    The gallery advertises only what passes here, so a broken example is surfaced,
    never silently shown. Pass ``ids`` to check a subset.
    """
    ids = ids or names()
    return {i: run(i) for i in ids}


if __name__ == "__main__":
    ok = 0
    for i, (name, (good, note)) in enumerate(validate().items(), 1):
        mark = "PASS" if good else "FAIL"
        print(f"[{i:2d}/{len(names())}] {mark}  {name}: {note}")
        ok += good
    print(f"\n{ok}/{len(names())} examples usable")
    sys.exit(0 if ok == len(names()) else 1)
