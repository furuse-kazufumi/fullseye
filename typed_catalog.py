# -*- coding: utf-8 -*-
"""型付きカタログ —— 進化レジストリへ橋渡しする op の**単一の真実源**(出荷モジュール)。

``ops3d`` / ``ops1d`` / ``opsmath`` / ``opsoptics`` … の台帳を 1 つの一覧
``catalog()`` に集め、束縛に必要な引数の既定(``PARAM_HINTS`` / ``OP_PARAM_HINTS``)と
返り値の型合わせ(``ADAPTERS``)を添える。``backends_typed`` がここを読んで
``tb_*`` 143 op を登録し、``tools/chain_fuzz`` もここを読んでファザーを回す。

★**なぜ独立したモジュールなのか(2026-09-05)**: これらは以前 ``tools/chain_fuzz.py``
(2,800 行の開発用ファザー、**wheel には同梱しない**)の中に住んでいた。
``backends_typed`` は ``sys.path`` に ``tools/`` を足して import し、失敗すると
``build()`` が ``return []`` で**黙って**いた —— ``FAILED_BACKENDS`` にも残らない。
その結果、``pip install fullseye`` した環境では **tb_* 143 op が一度も存在した
ことがなく**、しかも台帳は沈黙していた。0.1.9 のレビュー(Fable)が、
「wheel を建てて空の cwd から数える」ことで初めて捕まえた。

**出荷コードが開発道具に依存してはいけない。** 依存の向きは
``tools/chain_fuzz`` → ``typed_catalog`` であって、逆ではない。
"""
from __future__ import annotations

import numpy as np   # noqa: F401  (ヒント表の値に使う)

PARAM_HINTS = {
    # --- 2026-09-02: annotate / gfx2d / colortransport の必須引数 ------------
    # これが無いと束縛に失敗して op が**永久にスキップ**される。実測で
    # text_box / legend_box / scale_bar / crosshair がその状態だった
    # (annotate 25 op のうち 3 op しか到達していなかった原因)。
    # 値は「絵の中に確実に収まる」側へ寄せる —— 外に出ると fail-closed して
    # CONTRACT になり、結局その先の経路が走らない。
    "xy": lambda rng: (12.0, 12.0),
    "length": lambda rng: 20.0,
    "units_per_pixel": lambda rng: 0.5,
    "rect": lambda rng: (4, 4, 60, 40),
    "xlim": lambda rng: (0.0, 10.0), "ylim": lambda rng: (0.0, 5.0),
    "font_size": lambda rng: 12,
    # ここに "radius": 6.0 があったが、下の 1.5 に上書きされて死んでいた。
    # 現行の挙動は 1.5 なので、死んでいる側を消す(ruff F601)。
    "offset": lambda rng: (2, 2),
    "reg": lambda rng: 0.1,
    "levels": lambda rng: 256,
    "data_range": lambda rng: 1.0,
    "center": lambda rng: 0.5, "width": lambda rng: 0.5,
    "gamma": lambda rng: float(rng.uniform(0.5, 2.0)),
    "cutoff": lambda rng: 0.1, "low": lambda rng: 0.05, "high": lambda rng: 0.2,
    "sigma": lambda rng: 1.0, "scale": lambda rng: 2.0,
    "angle_deg": lambda rng: float(rng.uniform(-90, 90)),
    "factor": lambda rng: 2, "matrix": lambda rng: np.eye(3),
    "p0": lambda rng: (2.0, 2.0, 2.0), "p1": lambda rng: (13.0, 13.0, 13.0),
    "iterations": lambda rng: 3, "psf": lambda rng: None,   # None -> skip op
    "markers": lambda rng: None,
    "rate": lambda rng: 100.0, "new_rate": lambda rng: 50.0,
    "x": lambda rng: 1.0, "step": lambda rng: 2,
    "radius": lambda rng: 1.5, "ratio": lambda rng: 0.2,
    # 励起サイクル数(パイルアップ補正の分母)。tcspc_simulate 既定の総カウント
    # ~87 に対して十分大きくないと Coates 逆変換が定義域を外れる
    "cycles": lambda rng: 1_000_000,
    # 角度分解能。既定の (5,5) はファザーの 32x32 image2d を割り切れず
    # lf_from_mla が必ず ValueError になるので、割り切れる (4,4) を渡す
    "angular": lambda rng: (4, 4),
    "extent": lambda rng: 1.0, "lo": lambda rng: 0.8, "hi": lambda rng: 1.2,
    "strength": lambda rng: 0.5, "voxel": lambda rng: 0.5,
    "lights": lambda rng: (lambda L: L / np.linalg.norm(L, axis=1, keepdims=True))(
        np.array([[0.3, 0.3, 1.0], [-0.3, 0.3, 1.0], [0.3, -0.3, 1.0],
                  [-0.2, -0.2, 1.0]])),
    "k": lambda rng: 8, "n": lambda rng: 64, "size": lambda rng: 8,

    # --- 幾何・カメラ系(2026-09-01 追加)----------------------------------- #
    # 未到達 op の内訳を実測したところ、100 件中 **70 件が「必須引数を束縛でき
    # ず黙ってスキップ」**だった。記録も残らないので、外からは「頑健だから
    # 発見が無い」のと区別できない ―― カバレッジが数だけだった件と同じ形の
    # 見落としである。頻度順に不足していた引数へ、**プールの寸法と辻褄の合う**
    # 値を与える(points は [0,10]^3、image2d は 32x32、voxel は 16^3)。
    #
    # これは既に到達している op の挙動を変えない: 名前ヒントは**必須引数**に
    # しか効かず、これまで該当 op は丸ごとスキップされていたので、変わるのは
    # 「一度も実行されない」から「実行される」への一方向だけである。
    "K": lambda rng: np.array([[32.0, 0.0, 16.0],
                               [0.0, 32.0, 16.0],
                               [0.0, 0.0, 1.0]]),          # 32x32 画像の内部行列
    "K1": lambda rng: np.array([[32.0, 0.0, 16.0], [0.0, 32.0, 16.0], [0.0, 0.0, 1.0]]),
    "K2": lambda rng: np.array([[32.0, 0.0, 16.0], [0.0, 32.0, 16.0], [0.0, 0.0, 1.0]]),
    "fx": lambda rng: 32.0, "fy": lambda rng: 32.0,
    "cx": lambda rng: 16.0, "cy": lambda rng: 16.0,
    "R": lambda rng: np.eye(3), "t": lambda rng: np.array([0.0, 0.0, 12.0]),
    # 多視点(carve / visual_hull / fuse)。3 視点を Z 軸まわりに配置する
    "Ks": lambda rng: [np.array([[32.0, 0.0, 16.0], [0.0, 32.0, 16.0],
                                 [0.0, 0.0, 1.0]])] * 3,
    "Rs": lambda rng: [np.eye(3)] * 3,
    "ts": lambda rng: [np.array([0.0, 0.0, 12.0 + 2.0 * i]) for i in range(3)],
    # RANSAC の内れ値許容。points プールは [0,10]^3 なのでその 2% 相当
    "thresh": lambda rng: 0.2,
    # voxel 化の対象領域と解像度。points プールを丸ごと含む箱にする。
    #
    # **``bounds`` はこのライブラリ内で 3 つの流儀がある**(2026-09-02 実測):
    #   match3d          … ``(lo, hi)`` = 3 次元ベクトル 2 本
    #   tsdf_fusion / occupancy(3-D) … ``((xmin,xmax),(ymin,ymax),(zmin,zmax))``
    #   occupancy(2-D)   … ``(xmin, xmax, ymin, ymax)`` の平坦 4 要素
    # 取り違えは**両方向とも例外**になるので黙って違う体積が出ることは無い
    # (確認済み)が、名前ヒント 1 つでは全部を満たせない。既定は match3d 流に
    # 置き、((xmin,xmax),...) を要る op は下の OP_PARAM_HINTS で名指しする。
    # それまでの平坦 6 要素はどの流儀にも当たらず、4 op が毎回拒否されていた。
    "bounds": lambda rng: ((0.0, 0.0, 0.0), (10.0, 10.0, 10.0)),
    "res": lambda rng: 16,
    "alpha": lambda rng: 1.0,
    # 3 点から線・面を作る系の 2 番目・3 番目の点(1 番目は型プールから来る)
    "b": lambda rng: np.array([1.0, 0.0, 0.0]),
    "c": lambda rng: np.array([0.0, 1.0, 0.0]),
    # 曲面フィットの座標軸(x は型プールから来る)
    "y": lambda rng: np.linspace(0.0, 1.0, 64),
    "z": lambda rng: np.linspace(0.0, 1.0, 64),
    "a": lambda rng: 1.0,
    # 時間軸の単位。T=32 / fps=32 なので 4 Hz はちょうど bin に乗り、
    # 3-5 Hz の通過帯域が空にならない
    "fps": lambda rng: 32.0, "f_lo": lambda rng: 3.0, "f_hi": lambda rng: 5.0,
    # 回転数。既定 rate=100 Hz・samples_per_rev=64 では 60 rpm が 32 Hz で
    # Nyquist 50 Hz に収まる。1800 rpm だとエイリアス検査で毎回弾かれ、
    # 次数比分析 2 op が一度も実行されない
    "rpm": lambda rng: 60.0,
    # 四元数の積は**非可換**なので、左右は既定に頼らせず必ず引く
    "side": lambda rng: "left" if rng.random() < 0.5 else "right",
    "axis_rgb": lambda rng: (lambda v: v / np.linalg.norm(v))(
        rng.standard_normal(3)),
    "direction_rgb": lambda rng: (lambda v: v / np.linalg.norm(v))(
        rng.standard_normal(3)),
    "angle_rad": lambda rng: float(rng.uniform(-np.pi, np.pi)),

    # --- 2026-09-02: 網羅パスで「束縛できない」と挙がった 58 op の残り ------- #
    # 値はプールの寸法に合わせる(points は [0,10]^3 / voxel・sdf は 16^3 /
    # image2d と depth は 32x32)。名前ヒントは**必須引数にしか効かない**ので、
    # これまで丸ごとスキップされていた op が走るようになるだけで、既に到達
    # している op の挙動は変わらない。
    "tau": lambda rng: 0.5,               # fscore の一致許容(点群スケールの 5%)
    "trunc": lambda rng: 0.5,             # TSDF の切り詰め幅
    "tol": lambda rng: 0.5,               # クラスタリングの連結許容
    "min_voxels": lambda rng: 4,
    "min_inliers": lambda rng: 8,
    "min_distance": lambda rng: 2,
    "voxel_size": lambda rng: 0.5,
    "max_radius": lambda rng: 2.0,
    "spatial_sigma": lambda rng: 2.0, "range_sigma": lambda rng: 0.5,
    "ss": lambda rng: 2,                  # antialias の超解像倍率
    "r": lambda rng: 0.5,                 # sdf_offset のオフセット量
    "degree": lambda rng: 3,
    "n_bits": lambda rng: 8,
    "n_labels": lambda rng: 6,
    "count": lambda rng: 64, "seed": lambda rng: 0, "dt": lambda rng: 0.05,
    "rvec": lambda rng: np.zeros(3),
    # 反射・対称性の平面。点群 [0,10]^3 の中心を通る水平面
    "plane_point": lambda rng: np.array([5.0, 5.0, 5.0]),
    "plane_normal": lambda rng: np.array([0.0, 0.0, 1.0]),
    # 平面掃引の深度候補。カメラを z=20 に置いているので点群を挟む範囲
    "depth_candidates": lambda rng: np.linspace(8.0, 26.0, 12),
    # 射影変換。恒等に近い微小変形(恒等そのものだと op が仕事をしない)
    "H": lambda rng: np.array([[1.0, 0.02, 1.0], [0.0, 1.0, -1.0], [0.0, 0.0, 1.0]]),
    # 位置合わせの 4x4。恒等 = 「完全に合っている」側の端で、内れ値率 1.0 が
    # 出るのが正しい —— 端の値が出ることを確かめるのも検査のうち
    "transform": lambda rng: np.eye(4),
    "gt_transform": lambda rng: np.eye(4), "est_transform": lambda rng: np.eye(4),
}


OP_PARAM_HINTS = {
    # raytrace.glass(nd, vd) は必須引数が 2 つで名前ヒントに無い(束縛できず永久
    # スキップ = 「発見ゼロ」に化ける)。BK7 近傍の実在硝材域で束縛する
    ("glass", "nd"): lambda rng: float(rng.uniform(1.45, 1.90)),
    ("glass", "vd"): lambda rng: float(rng.uniform(20.0, 95.0)),
    # raytrace.glass_catalog(name) / sellmeier(B1..C3): 実在硝材名 / N-BK7 近傍の定数で束縛
    ("glass_catalog", "name"): lambda rng: str(rng.choice(["N-BK7", "N-SF2", "N-SK16", "SILICA", "CAF2"])),
    ("sellmeier", "B1"): lambda rng: float(rng.uniform(0.9, 1.8)),
    ("sellmeier", "B2"): lambda rng: float(rng.uniform(0.1, 0.4)),
    ("sellmeier", "B3"): lambda rng: float(rng.uniform(0.9, 2.0)),
    ("sellmeier", "C1"): lambda rng: float(rng.uniform(0.005, 0.013)),
    ("sellmeier", "C2"): lambda rng: float(rng.uniform(0.02, 0.06)),
    ("sellmeier", "C3"): lambda rng: float(rng.uniform(90.0, 170.0)),
    # lensopt.optimize_lens は既定 30 反復 × 有限差分で 1 呼び数秒になりうる。
    # 連鎖では 2 反復・2 リングで実経路(残差→ヤコビアン→LM 更新→再検証)だけ通す
    ("optimize_lens", "iterations"): lambda rng: 2,
    ("optimize_lens", "rings"): lambda rng: 2,
    ("merit_function", "rings"): lambda rng: 2,
    # lensimage.defect_dataset は既定 n=8 / 256x256 を雑音つきで描くと 1 呼び
    # 数秒になり連鎖全体を遅らせる。1 枚・32x32 で実経路(欠陥描画 → レンズ
    # 越し描画 → マスク歪曲 → bbox)だけを通す
    ("defect_dataset", "n"): lambda rng: 1,
    ("defect_dataset", "size"): lambda rng: (32, 32),
    ("defect_dataset", "zones"): lambda rng: 1,
    # 既定 (5,5) はプールの 32x32 を割り切れず毎回 ValueError になり、この op が
    # 一度も実行されないまま「発見ゼロ」に見えていた。32 を割り切る (4,4) にする
    ("lf_from_mla", "angular"): lambda rng: (4, 4),
    # 描画系の size は (H, W)。名前ヒントの "size"(=8、近傍サイズ等のスカラ)を
    # そのまま渡すと生の TypeError になり、**op の契約の穴なのか入力が悪いのか**
    # 区別がつかなくなる。まず正しい形を渡してから判定する
    ("render_point_depth", "size"): lambda rng: (32, 32),
    ("synthesize_silhouette", "size"): lambda rng: (32, 32),
    # PARAM_HINTS["alpha"] は 1.0(= 恒等利得)なので、そのままだと
    # motion_magnify は毎回実行されるのに**一度も増幅しない**。狙いは
    # 増幅経路を通すことなので op 名で上書きする
    ("motion_magnify", "alpha"): lambda rng: 2.0,

    # --- 2026-09-03: 学術図の図注(annotate "paper" 族 / ops3d "annotate3d") -- #
    # プールの image2d は 32x32 なので、文字・板・矢印が**その中に収まる**寸法に
    # 寄せる(外に出れば fail-closed して CONTRACT になり、op の本体は走らない)。
    # 引き出し線・番号は points プールの 160 点だと「置き場が無い」で毎回
    # 拒否されるため、in は image2d だけにして点をここで 2-3 個束縛する。
    ("annotate_leader", "points"): lambda rng: [(6.0, 6.0), (22.0, 24.0)],
    ("annotate_leader", "font_size"): lambda rng: 7, ("annotate_leader", "gap"): lambda rng: 5.0,
    ("annotate_leader", "pad"): lambda rng: 2,
    ("annotate_leader_layout", "shape"): lambda rng: (32, 32),
    ("annotate_leader_layout", "points"): lambda rng: [(6.0, 6.0), (22.0, 24.0)],
    ("annotate_leader_layout", "font_size"): lambda rng: 7,
    ("annotate_leader_layout", "gap"): lambda rng: 5.0,
    ("annotate_leader_layout", "pad"): lambda rng: 2,
    ("annotate_markers", "points"): lambda rng: [(10.0, 10.0), (22.0, 20.0)],
    ("annotate_markers", "radius"): lambda rng: 6.0, ("annotate_markers", "font_size"): lambda rng: 7,
    ("annotate_legend", "labels"): lambda rng: ["A"], ("annotate_legend", "xy"): lambda rng: (1.0, 1.0),
    ("annotate_legend", "pad"): lambda rng: 2, ("annotate_legend", "radius"): lambda rng: 5.0,
    ("annotate_legend", "font_size"): lambda rng: 8,
    ("annotate_dimension", "p0"): lambda rng: (4.0, 31.0), ("annotate_dimension", "p1"): lambda rng: (27.0, 31.0),
    ("annotate_dimension", "offset"): lambda rng: -3.0, ("annotate_dimension", "font_size"): lambda rng: 7,
    ("annotate_dimension_layout", "p0"): lambda rng: (4.0, 31.0),
    ("annotate_dimension_layout", "p1"): lambda rng: (27.0, 31.0),
    ("annotate_angle", "a"): lambda rng: (4.0, 4.0), ("annotate_angle", "vertex"): lambda rng: (4.0, 26.0),
    ("annotate_angle", "b"): lambda rng: (26.0, 26.0), ("annotate_angle", "radius"): lambda rng: 8.0,
    ("annotate_angle", "font_size"): lambda rng: 7,
    ("annotate_angle_layout", "a"): lambda rng: (4.0, 4.0),
    ("annotate_angle_layout", "vertex"): lambda rng: (4.0, 26.0),
    ("annotate_angle_layout", "b"): lambda rng: (26.0, 26.0),
    ("annotate_scale_bar", "target_fraction"): lambda rng: 0.9, ("annotate_scale_bar", "margin"): lambda rng: 2,
    ("annotate_scale_bar", "font_size"): lambda rng: 5, ("annotate_scale_bar", "corner"): lambda rng: "lb",
    ("annotate_scale_bar_layout", "shape"): lambda rng: (32, 32),
    ("annotate_scale_bar_layout", "target_fraction"): lambda rng: 0.9,
    ("annotate_scale_bar_layout", "margin"): lambda rng: 2,
    ("annotate_orientation", "size"): lambda rng: 10.0, ("annotate_orientation", "margin"): lambda rng: 1,
    ("annotate_orientation", "font_size"): lambda rng: 6,
    ("annotate_inset", "src_rect"): lambda rng: (2, 2, 6, 6), ("annotate_inset", "margin"): lambda rng: 2,
    ("annotate_inset_layout", "shape"): lambda rng: (32, 32),
    ("annotate_inset_layout", "src_rect"): lambda rng: (2, 2, 6, 6),
    ("annotate_inset_layout", "margin"): lambda rng: 2,
    ("annotate_text_path", "path"): lambda rng: [(7.0, 25.0), (27.0, 7.0)],
    ("annotate_text_path", "font_size"): lambda rng: 5,
    ("annotate_text_path_layout", "path"): lambda rng: [(7.0, 25.0), (27.0, 7.0)],
    ("annotate_text_path_layout", "font_size"): lambda rng: 5,
    ("annotate_colorbar", "rect"): lambda rng: (3, 2, 20, 3),
    ("annotate_colorbar", "orientation"): lambda rng: "horizontal",
    ("annotate_colorbar", "font_size"): lambda rng: 6,
    ("annotate_panel_label", "font_size"): lambda rng: 8, ("annotate_panel_label", "margin"): lambda rng: 2,
    ("annotate_figure_grid", "font_size"): lambda rng: 8,
    ("annotate_figure_grid_layout", "shapes"): lambda rng: [(32, 32), (24, 32)],
    # annotate3d: points プールは [0,10]^3。(5,5,45) から (5,5,5) を見下ろす姿勢と
    # PARAM_HINTS の K(fx=32, cx=16)で、点は 32x32 の中央 ±4 px に射影される
    ("annotate3d_project", "pose"): lambda rng: __import__("render3d").look_at(
        (5.0, 5.0, 45.0), (5.0, 5.0, 5.0), (0.0, 1.0, 0.0)),
    ("annotate3d_arrow", "pose"): lambda rng: __import__("render3d").look_at(
        (5.0, 5.0, 45.0), (5.0, 5.0, 5.0), (0.0, 1.0, 0.0)),
    ("annotate3d_label", "pose"): lambda rng: __import__("render3d").look_at(
        (5.0, 5.0, 45.0), (5.0, 5.0, 5.0), (0.0, 1.0, 0.0)),
    ("annotate3d_label", "anchor"): lambda rng: (5.0, 5.0, 5.0),
    ("annotate3d_label", "offset"): lambda rng: (0.0, -4.0),
    ("annotate3d_label", "font_size"): lambda rng: 5, ("annotate3d_label", "pad"): lambda rng: 1,
    ("annotate3d_scale_bar", "pose"): lambda rng: __import__("render3d").look_at(
        (5.0, 5.0, 45.0), (5.0, 5.0, 5.0), (0.0, 1.0, 0.0)),
    ("annotate3d_scale_bar", "origin"): lambda rng: (2.0, 0.0, 5.0),
    ("annotate3d_scale_bar", "tick"): lambda rng: 0.0,
    ("annotate3d_scale_bar", "direction"): lambda rng: (1.0, 0.0, 0.0),
    ("annotate3d_scale_bar", "length"): lambda rng: 6.0,
    ("annotate3d_scale_bar", "font_size"): lambda rng: 5,
    ("annotate3d_axes", "pose"): lambda rng: __import__("render3d").look_at(
        (5.0, 5.0, 45.0), (5.0, 5.0, 5.0), (0.0, 1.0, 0.0)),
    ("annotate3d_axes", "origin"): lambda rng: (5.0, 5.0, 5.0),
    ("annotate3d_axes", "length"): lambda rng: 3.0, ("annotate3d_axes", "font_size"): lambda rng: 6,
    ("annotate3d_bbox", "pose"): lambda rng: __import__("render3d").look_at(
        (5.0, 5.0, 45.0), (5.0, 5.0, 5.0), (0.0, 1.0, 0.0)),
    ("annotate3d_measure", "pose"): lambda rng: __import__("render3d").look_at(
        (5.0, 5.0, 45.0), (5.0, 5.0, 5.0), (0.0, 1.0, 0.0)),
    ("annotate3d_measure", "font_size"): lambda rng: 5,
    ("annotate3d_measure", "p0"): lambda rng: (2.0, 0.0, 2.0),
    ("annotate3d_measure", "p1"): lambda rng: (8.0, 0.0, 2.0),
    ("annotate3d_measure", "tick"): lambda rng: 0.0,

    # --- 2026-09-02: 形が結びついていて名前ヒントでは足りないもの ----------- #
    # 名前ヒントは同名の引数を持つ**全 op**に効くので、寸法が入力と噛み合う
    # 必要があるものはここで op を名指しする。既存の名前ヒントと衝突する
    # ものが実際にあった: PARAM_HINTS["center"] は 0.5(窓関数の中心)なので、
    # 描画系の center(画素座標の 2 つ組)には使えない。
    ("arc", "center"): lambda rng: (16.0, 16.0),
    ("arc", "radius"): lambda rng: 8.0,
    ("arc", "start_deg"): lambda rng: 0.0, ("arc", "end_deg"): lambda rng: 120.0,
    ("ellipse", "center"): lambda rng: (16.0, 16.0),
    ("ellipse", "radii"): lambda rng: (8.0, 5.0),
    ("zoom_inset", "src_rect"): lambda rng: (4, 4, 10, 10),
    ("zoom_inset", "dst_xy"): lambda rng: (18, 18),
    # gfx2d。rgba プールは 24x32、sprites は 8x8 が 3 枚
    ("sprite_sheet_slice", "tile_height"): lambda rng: 8,
    ("sprite_sheet_slice", "tile_width"): lambda rng: 8,
    ("nine_slice", "left"): lambda rng: 6, ("nine_slice", "right"): lambda rng: 6,
    ("nine_slice", "top"): lambda rng: 6, ("nine_slice", "bottom"): lambda rng: 6,
    ("nine_slice", "out_height"): lambda rng: 48,
    ("nine_slice", "out_width"): lambda rng: 64,
    ("particle_render", "height"): lambda rng: 32,
    ("particle_render", "width"): lambda rng: 32,
    ("radial_light", "height"): lambda rng: 32, ("radial_light", "width"): lambda rng: 32,
    ("radial_light", "x"): lambda rng: 16.0, ("radial_light", "y"): lambda rng: 16.0,
    ("radial_light", "radius"): lambda rng: 8.0,
    ("viewport", "x"): lambda rng: 4, ("viewport", "y"): lambda rng: 4,
    ("viewport", "width"): lambda rng: 16, ("viewport", "height"): lambda rng: 12,
    # volcolor。rgbvolume プールは (8,16,16,3) なので index < 8
    ("vol_label_slice_rgb", "index"): lambda rng: 4,
    # 3-D。voxel / sdf プールは 16^3
    ("vol_uncrop", "offset"): lambda rng: (2, 2, 2),
    ("vol_uncrop", "shape"): lambda rng: (20, 20, 20),
    ("vol_tiled_map", "fn"): lambda rng: (lambda s: s * 0.5),
    ("vol_tiled_map", "tile"): lambda rng: 8, ("vol_tiled_map", "overlap"): lambda rng: 2,
    ("vol_watershed", "markers"): lambda rng: (lambda m: (
        m.__setitem__((4, 4, 4), 1), m.__setitem__((11, 11, 11), 2), m)[2])(
            np.zeros((16, 16, 16), dtype=np.int32)),
    ("vol_local_maxima", "min_distance"): lambda rng: 2,
    ("extract_surface_points", "weight"): lambda rng: np.ones((16, 16, 16)),
    # tsdf_fusion / occupancy(3-D)流の bounds(軸ごとの (min, max) の 3 つ組)
    ("extract_surface_points", "bounds"): lambda rng: ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0)),
    ("grid_coords", "bounds"): lambda rng: ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0)),
    ("grid_coords", "res"): lambda rng: 16,
    ("integrate", "bounds"): lambda rng: ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0)),
    ("query_distance", "bounds"): lambda rng: ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0)),
    ("fuse", "bounds"): lambda rng: ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0)),
    ("geodesic_distances", "source"): lambda rng: 0,
    ("box_sdf", "center"): lambda rng: np.array([5.0, 5.0, 5.0]),
    ("box_sdf", "half_extents"): lambda rng: np.array([2.0, 2.0, 2.0]),
    # sphere_sdf(grid, center, R) の R は**半径のスカラ**。名前ヒントの "R" は
    # 回転行列 eye(3) なので、そのままだと op 側の番人
    #(「R must be a scalar radius」)に毎回弾かれていた。番人が正しく働いて
    # いたおかげで壊れた値が下流へ流れずに済んでいたが、この op は一度も
    # 仕事をしていなかった(進化側の tb_sphere_sdf は 40/40 で定数ゼロ)。
    ("sphere_sdf", "center"): lambda rng: np.array([5.0, 5.0, 5.0]),
    # ("sphere_sdf","R"): 3.0 はここにあったが下の 2.0 に上書きされて死んでいた

    ("render_lambertian", "albedo"): lambda rng: 0.7,
    ("render_lambertian", "light"): lambda rng: (lambda v: v / np.linalg.norm(v))(
        np.array([0.3, 0.3, 1.0])),
    # 超二次曲面 3 op。PARAM_HINTS["a"] は 1.0(スカラ)だが、ここでの a は
    # **3 軸の半径**、eps は 2 つの丸み指数。名前ヒントのままだと形が違う
    ("sample_surface", "a"): lambda rng: np.array([2.0, 1.5, 1.0]),
    ("sample_surface", "eps"): lambda rng: np.array([1.0, 1.0]),
    ("inside_outside", "a"): lambda rng: np.array([2.0, 1.5, 1.0]),
    ("inside_outside", "eps"): lambda rng: np.array([1.0, 1.0]),
    ("superquadric_residual", "a"): lambda rng: np.array([2.0, 1.5, 1.0]),
    ("superquadric_residual", "eps"): lambda rng: np.array([1.0, 1.0]),
    # bounds という 1 つの名前に 3 通りの形が要求されている(平坦 6-tuple /
    # ((min,max)x3) / (lo(3,), hi(3,)))。名前ヒントは平坦形のままにして、
    # 別形を要求する op だけ狙い撃つ ― さもないと毎回 ValueError で
    # **一度も実行されない**まま「発見ゼロ」に数えられる
    ("occupancy_grid", "bounds"): lambda rng: ((0.0, 10.0), (0.0, 10.0), (0.0, 10.0)),
    # sphere_sdf の R は**回転行列ではなく半径**。名前ヒントの np.eye(3) が
    # そのまま渡ると生の TypeError になる(名前の衝突であって op の罪ではない)
    ("sphere_sdf", "R"): lambda rng: 2.0,
    ("quat_color_filter", "mode"): lambda rng: "remove" if rng.random() < 0.5 else "keep",
    # PARAM_HINTS["alpha"] は 1.0(恒等利得)。motion_magnify と同じ理由で上書き
    ("riesz_motion_magnify", "alpha"): lambda rng: 2.0,
    # 既定 n_antennas=1 だとプールに 1 素子の立方体が入り、ビームフォーミング
    # 2 op が毎回「開口が無い」で弾かれて一度も実行されない
    ("fmcw_beat_simulate", "n_antennas"): lambda rng: 4,
    # 生成器の走査範囲と辻褄を合わせる(既定 2.8 でも動くが端切れが増える)
    ("csi_stack_simulate", "envelope_fwhm_um"): lambda rng: 2.8258,
    # 構造化光の三角測量。名前ヒントの "K"/"R"/"t" と綴りが違う(k_cam/k_proj/rot/
    # trans)ので、書かないと必須引数が組めず **一度も実行されない**まま
    # 「発見ゼロ」に化ける。基線は x 方向 60 mm 相当(実機の投影機オフセット)。
    ("triangulate_column", "k_cam"): lambda rng: np.array([[32.0, 0.0, 16.0],
                                                           [0.0, 32.0, 16.0],
                                                           [0.0, 0.0, 1.0]]),
    ("triangulate_column", "k_proj"): lambda rng: np.array([[32.0, 0.0, 16.0],
                                                            [0.0, 32.0, 16.0],
                                                            [0.0, 0.0, 1.0]]),
    ("triangulate_column", "rot"): lambda rng: np.eye(3),
    ("triangulate_column", "trans"): lambda rng: np.array([-6.0, 0.0, 0.0]),
    ("vol_richardson_lucy", "psf"): lambda rng: __import__("volrestore").vol_gaussian_psf(1.0),
    ("cx_wiener_deconvolve", "psf"): lambda rng: (lambda k: k / k.sum())(
        np.outer(*(np.exp(-np.linspace(-2, 2, 5) ** 2),) * 2)),
    ("cx_apply_transfer_function", "H"): lambda rng: rng.random((32, 32)),
    # tier2 複素解析: w = 輪郭の内側にありそうな点(外・線上なら fail-closed
    # の CONTRACT が出るのが正しい)。Möbius の 4 係数は ad-bc≠0 の実例
    ("cplx_cauchy_value", "w"): lambda rng: 0.1 + 0.1j,
    ("cplx_mobius", "a"): lambda rng: 1.0,
    ("cplx_mobius", "b"): lambda rng: -1j,
    ("cplx_mobius", "c"): lambda rng: 1.0,
    ("cplx_mobius", "d"): lambda rng: 1j,
    # mesh を (V, F) に割る 8 op のうち、残る必須引数がこの 2 つ。名前
    # ("target_faces" / "source")は他の op と衝突しないが**汎用の意味も無い**
    # ので、名前ヒントに置かず op 名で狙い撃つ。8 は種の最小メッシュ(平面
    # パッチ 2 面)より大きいが、実測でこの op は目標超過を例外にせず現状を
    # 返す(nf=2 / target=8 で (4,3),(2,3) が返る)ので毎回 CONTRACT にはならない
    ("decimate_qem", "target_faces"): lambda rng: 8,
    # terrain(2026-09-03): 種メッシュ([0,10]^3 の凸包 / 直方体 / 平面パッチ)の寸法に合わせる
    ("mesh_displace_fbm", "amplitude"): lambda rng: float(rng.uniform(0.05, 0.3)),
    ("mesh_scatter_boulders", "density"): lambda rng: 0.05,     # 面積 ~10²〜10³ → 数個〜数十個
    ("mesh_scatter_boulders", "d_min"): lambda rng: 0.3,
    ("mesh_subdivide", "target_edge"): lambda rng: float(rng.uniform(1.5, 4.0)),
    ("mesh_displace_spectrum", "wavelengths"): lambda rng: (8.0, 4.0, 2.0),
    ("mesh_displace_spectrum", "amplitudes"): lambda rng: (0.3, 0.15, 0.08),
    ("displacement_band_weights", "wavelengths"): lambda rng: (8.0, 4.0, 2.0),
    ("render_regolith", "size"): lambda rng: 32,
    ("render_regolith", "ss"): lambda rng: 1,
    ("render_regolith", "ao_samples"): lambda rng: 8,
    ("render_regolith", "shadow_samples"): lambda rng: 1,
    ("shadow_raycast", "width"): lambda rng: 32,
    ("shadow_raycast", "height"): lambda rng: 32,
    # meshres: 目標辺長/間隔は種メッシュ(単位球級)の辺長域、面数は小さく
    ("mesh_split_long_edges", "max_edge"): lambda rng: float(rng.uniform(0.3, 1.0)),
    ("mesh_isotropic_remesh", "target_edge"): lambda rng: float(rng.uniform(0.3, 0.8)),
    ("mesh_isotropic_remesh", "iterations"): lambda rng: 2,
    ("mesh_sample_points", "spacing"): lambda rng: float(rng.uniform(0.2, 0.6)),
    ("mesh_decimate_preserving", "target_faces"): lambda rng: 8,
    ("mesh_select_lod", "distance"): lambda rng: float(rng.uniform(1.0, 50.0)),
    ("mesh_select_lod", "focal_px"): lambda rng: 500.0,
    ("pc_poisson_disk", "radius"): lambda rng: float(rng.uniform(0.05, 0.3)),
    ("pc_fill_sparse", "spacing"): lambda rng: float(rng.uniform(0.1, 0.4)),
    ("pc_density_equalize", "spacing"): lambda rng: float(rng.uniform(0.1, 0.4)),
    ("pc_lod_chain", "spacing"): lambda rng: float(rng.uniform(0.1, 0.4)),
    ("pc_lod_chain", "levels"): lambda rng: 2,
    # 測地距離の起点は頂点添字。種の最小メッシュでも 0 は必ず存在する
    ("geodesic_mesh", "source"): lambda rng: 0,
}


def _registry_adapters():
    import ops1d
    import ops3d
    import opsmath
    d = dict(ops3d.RESULT_ADAPTERS)
    d.update(ops1d.RESULT_ADAPTERS)
    d.update(opsmath.RESULT_ADAPTERS)
    import opsoptics
    d.update(opsoptics.RESULT_ADAPTERS)
    import opslightfield
    d.update(opslightfield.RESULT_ADAPTERS)
    import opsphoton
    d.update(opsphoton.RESULT_ADAPTERS)     # 現状は空(全 op が宣言型を素で返す)
    import opsspecular
    d.update(opsspecular.RESULT_ADAPTERS)
    import opsmotionmag
    d.update(opsmotionmag.RESULT_ADAPTERS)  # 意図的に空(下の理由を参照)
    import opsquat
    d.update(opsquat.RESULT_ADAPTERS)       # 空: 19 op とも宣言型を素で返す
    import opsrangedoppler
    d.update(opsrangedoppler.RESULT_ADAPTERS)   # 空(意図的)
    import opsacoustics
    d.update(opsacoustics.RESULT_ADAPTERS)      # 空(意図的)
    import opsinterferometry
    d.update(opsinterferometry.RESULT_ADAPTERS)  # 空(意図的)
    import opscadmap
    d.update(opscadmap.RESULT_ADAPTERS)          # 空(意図的): 素の返りが宣言型
    for _mod in ("opstomography", "opsvolcolor", "opsreprconv", "opsannotate",
                 "opsgfx2d", "opsimgmetrics", "opscolortransport",
                 "opsimgforensics", "opsastrostack"):
        try:
            d.update(getattr(__import__(_mod), "RESULT_ADAPTERS", {}))
        except Exception as _e:                       # 台帳が無い環境でも動く
            print(f"  ({_mod} adapters unavailable: {_e})")
    d["vol_rle_components"] = lambda r: r[0] if r else None
    d["label_components"] = lambda r: r[0] if isinstance(r, tuple) else r
    return d


ADAPTERS = _registry_adapters()


def catalog():
    """(name, module, in_types, out_type, fn) を ops3d + ops1d から集める。"""
    import ops1d
    import ops3d
    ops = []
    for n, m in ops3d.OPS3D.items():
        if m["func"] is not None:
            ops.append((n, "3d", list(m["in"]), m["out"], m["func"]))
    for n, m in ops1d.OPS1D.items():
        if m["func"] is not None and m["category"] != "io":   # ファイル I/O は除外
            ops.append((n, "1d", list(m["in"]), m["out"], m["func"]))
    # complexops = HALCON の complex 画像形式(2-D)。image2d <-> cimage の橋
    import complexops as cx
    for name, ins, out in [
        ("cx_fft", ["image2d"], "cimage"),
        ("cx_ifft", ["cimage"], "image2d"),
        ("cx_magnitude", ["cimage"], "image2d"),
        ("cx_phase", ["cimage"], "image2d"),
        ("cx_real", ["cimage"], "image2d"),
        ("cx_imag", ["cimage"], "image2d"),
        ("cx_log_magnitude", ["cimage"], "image2d"),
        ("cx_from_mag_phase", ["image2d", "image2d"], "cimage"),
        ("phase_unwrap", ["image2d"], "image2d"),
        ("cx_apply_transfer_function", ["cimage"], "cimage"),
        ("cx_bandpass", ["image2d"], "image2d"),
        ("cx_wiener_deconvolve", ["image2d"], "image2d"),
    ]:
        ops.append((name, "2d", ins, out, getattr(cx, name)))
    # 数学ファミリ(opsmath 台帳)。adapter 層を持たない=素の返りが宣言型で
    # あることを TYPEMISS 検査がそのまま機械検証する
    import opsmath
    for n, m in opsmath.OPSMATH.items():
        if m["func"] is not None:
            ops.append((n, "math", list(m["in"]), m["out"], m["func"]))
    # 光学ファミリ(opsoptics 台帳)。opsmath と同じく adapter 層を持たない=
    # 素の返りが宣言型であることを TYPEMISS 検査がそのまま機械検証する
    import opsoptics
    for n, m in opsoptics.OPSOPTICS.items():
        if m["func"] is not None:
            ops.append((n, "optics", list(m["in"]), m["out"], m["func"]))
    # ライトフィールドファミリ(opslightfield 台帳)。4-D (V,U,H,W) の新語彙
    # `lightfield` を持ち込む唯一の族で、`images` へ潰すと「どの視点か」が
    # 消えて refocus も EPI も定義できなくなるため型を分けている
    import opslightfield
    for n, m in opslightfield.OPSLIGHTFIELD.items():
        if m["func"] is not None:
            ops.append((n, "lightfield", list(m["in"]), m["out"], m["func"]))
    # 光子計数・時間分解(opsphoton 台帳)。新語彙 `histcube` は (H,W,T) で
    # **時間軸が最後**。voxel と ndim==3 の構造は同じだが軸の意味が違い、
    # (D,H,W) を渡すと例外ではなく「もっともらしく間違った深度」が出るため
    # 型を分ける(pointmap / normalmap を分けたのと同じ判断)
    import opsphoton
    for n, m in opsphoton.OPSPHOTON.items():
        if m["func"] is not None:
            ops.append((n, "photon", list(m["in"]), m["out"], m["func"]))
    # 鏡面反射の分離 / 反射モデル(opsspecular 台帳)。新語彙 `rgbimage` は
    # (H,W,3) で pointmap / normalmap と**構造は同じだが意味が違う**。実測で
    # normalmap を分離 op に渡すと例外なく「分離結果」が返ることを確認済み
    import opsspecular
    for n, m in opsspecular.OPSSPECULAR.items():
        if m["func"] is not None:
            ops.append((n, "specular", list(m["in"]), m["out"], m["func"]))
    # 位相ベースのモーション増幅(opsmotionmag 台帳)。新語彙 `video` は (T,H,W)。
    # voxel と ndim は同じだが**先頭が時間軸**で、voxel を渡しても例外も NaN も
    # 出ないまま z を時間として読む(実測確認済み)= histcube を voxel から
    # 分けたのと同じ判断
    import opsmotionmag
    for n, m in opsmotionmag.OPSMOTIONMAG.items():
        if m["func"] is not None:
            ops.append((n, "motionmag", list(m["in"]), m["out"], m["func"]))
    # 四元数画像(opsquat 台帳)。新語彙 `qimage` は (H,W,4)。色の四元数と
    # モノジェニック信号という**意味の違う 2 種類が同じ形**なので、生成器は
    # 必ず両方を出す(片方だけだと相手側の op が永久に fail-closed になる)
    import opsquat
    for n, m in opsquat.OPSQUAT.items():
        if m["func"] is not None:
            ops.append((n, "quat", list(m["in"]), m["out"], m["func"]))
    # FMCW レンジ-ドップラー(opsrangedoppler 台帳)。新語彙 `beatcube` は
    # (アンテナ, チャープ, サンプル) の**複素** 3-D。histcube (非負の光子カウント)
    # と形は一致するが dtype だけが違い、**キャスト 1 回で相互に通ってしまう**
    # (実測: np.abs(beatcube) を dtof_cube_depth に渡すと例外なく深度が返り、
    # histcube.astype(complex) を range_doppler_map に渡すとマップが返る)ので
    # 宣言型のレベルで分ける
    import opsrangedoppler
    for n, m in opsrangedoppler.OPSRANGEDOPPLER.items():
        if m["func"] is not None:
            ops.append((n, "rangedoppler", list(m["in"]), m["out"], m["func"]))
    # 音響・振動診断(opsacoustics 台帳)。**新しい型語彙を作らない**判断:
    # 任意の実 1-D 配列は本当に妥当な音響信号なので、専用型を宣言しても嘘に
    # ならない代わりに守るものが無い(counts と違って破る制約が無い)。危険は
    # 配列でなく **rate スカラ**の側にある — 同じ録音を 25600 でなく 48000 Hz
    # として読むと欠陥周波数が 107 Hz でなく 200.625 Hz と報告され、例外は
    # 出ない。よって防御はスカラ検証に置き、既存 dsp / funct1d との接続を保つ
    import opsacoustics
    for n, m in opsacoustics.OPSACOUSTICS.items():
        if m["func"] is not None:
            ops.append((n, "acoustics", list(m["in"]), m["out"], m["func"]))
    # コヒーレンス走査干渉(opsinterferometry 台帳)。型語彙 2 つ:
    # `zscan` = (Z,H,W) の走査スタック(**走査軸が先頭**)、`sweep` = 1-D の
    # 非負掃引。zscan を分けたのは実測で**片側だけが黙って通る**から —
    # zscan を video / histcube へ渡すと 4 op すべてが例外も NaN も出さずに
    # 「増幅結果」「深度」を返すが、逆向きは fail-closed する。実行時検査に
    # 頼れないので宣言型で分ける
    import opsinterferometry
    for n, m in opsinterferometry.OPSINTERFEROMETRY.items():
        if m["func"] is not None:
            ops.append((n, "interferometry", list(m["in"]), m["out"], m["func"]))
    # 欠陥 → CAD 面の逆写像(opscadmap 台帳)。**新しい型語彙を 1 つも作らない**
    # 判断: 4 op の入出力は既存の mesh / keypoints / points / labels / table /
    # indices にそのまま収まる。代わりにこの族が持ち込んだのは
    # **`mesh` 型の述語と種**で、2026-09-02 まで mesh は TYPE_CHECKS に述語が
    # 無く(宣言 out=mesh の op が何を返しても TYPEMISS にならない穴)、
    # make_generators にも種が無かった(実測。dead な _mesh ヘルパだけがあった)。
    # mesh を 1 引数で受ける形にしてあるので、`mesh_to_voxel(vertices, faces)`
    # のように (V,F) を 2 位置引数へ割る既存 op が「2 つ目が束縛できず永久に
    # スキップ」になる罠は踏まない。
    import opscadmap
    for n, m in opscadmap.OPSCADMAP.items():
        if m["func"] is not None:
            ops.append((n, "cadmap", list(m["in"]), m["out"], m["func"]))

    # --- 2026-09-02 に登録した 9 台帳 ---------------------------------------
    # ここに載っていなかったあいだ、これらの **192 op はファザーが一度も
    # 実行していなかった**。「発見ゼロ」が頑健さの証拠ではなく、単に走って
    # いなかっただけ、という状態(この repo が何度も踏んできた形)。
    # 台帳が種や述語を提案しているもの(opsreprconv / opsimgforensics)は
    # 下の TYPE_CHECKS / make_generators へ合流させる。
    for _mod, _tbl, _dim in (
        ("opstomography", "OPSTOMOGRAPHY", "tomography"),
        ("opsvolcolor", "OPSVOLCOLOR", "volcolor"),
        ("opsreprconv", "OPSREPRCONV", "reprconv"),
        ("opsannotate", "OPSANNOTATE", "annotate"),
        ("opsgfx2d", "OPSGFX2D", "gfx2d"),
        ("opsimgmetrics", "OPSIMGMETRICS", "imgmetrics"),
        ("opscolortransport", "OPSCOLORTRANSPORT", "colortransport"),
        ("opsimgforensics", "OPSIMGFORENSICS", "imgforensics"),
        ("opsastrostack", "OPSASTROSTACK", "astrostack"),
        # 2026-09-03: ストリーミング動画処理。入力は既存の `video` 種
        # (_motion_clip = (32,32,32) の並進格子)をそのまま使う
        ("opsvideostream", "OPSVIDEOSTREAM", "videostream"),
    ):
        _m = __import__(_mod)
        for n, m in getattr(_m, _tbl).items():
            if m["func"] is not None:
                ops.append((n, _dim, list(m["in"]), m["out"], m["func"]))
    return ops
