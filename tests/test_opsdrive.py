"""opsdrive 台帳の門(tests/test_blob2d.py の 6 と同型): 欠けなし / 台帳と __all__ / 公開経路 / typed_catalog / fuzzer の種。"""
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def test_the_ledger_lists_every_op_and_nothing_is_missing():
    import opsdrive

    assert opsdrive.missing() == []
    assert set(opsdrive.categories()) == {"course", "world", "lidar", "ttc", "rss", "terrain",
                                          "ball", "balltrack", "ballworld", "racket", "roadjp",
                                          "kendama", "kendamaworld", "gsplat", "long", "env", "inf", "traffic", "decide", "lateral", "crossing", "pass",
                                          "motion_io", "humanoid", "agv", "carla", "town", "japan", "commonroad", "pegsim", "tacsim", "tacslip", "tactorque", "puck", "pegfail", "granular", "tacscalib", "pegtactile", "cutting", "diabolo", "tacdome", "pegsym", "polish", "scoop", "grind", "ozaki", "swarmflow", "pxrd", "doseunif", "cuttouch", "roverslip"}
    # 288 → 292: gs_read_file + 動きのデータの入口 3(read_bvh / read_events / events_to_frames、2026-10-03)
    # 292 → 296: 歩くヒューマノイド 4(humanoid_clip_mesh / world_pose_humanoid / humanoid_impostors / world_camera_impostors)
    # 296 → 309: 工場・倉庫の AGV の群れ 13(agvfleet: 格子・CBS / 焦点探索 / 結合 A* / 優先度付き・ADG・VDA 5050)
    # 309 → 334: CARLA の橋 25(carlabridge: 規約の写し 16・場面記録 6・採点 3、2026-10-04)
    # 334 → 344: 町を 1 つに組む 10(drivetown: 継ぐ・既定の町・世界・中心線・停止線・法規パック・踏切の状態・通し走行・採点・教則台帳、2026-10-04)
    # 344 → 366: 実在の日本の町 22(drivejapan 15: OSM の読み込み・道路網・ラスタ和集合・境界ループ・最短路・世界・内訳・等距円筒・道具立て 6、
    #            driveplateau 7: CityGML の合成・読み込み・箱で選ぶ・柱・三角形分割・面積、2026-10-04)
    # 366 → 376: 他人の場面 × 自分の運転手 × 他人の採点器 10(drivecommonroad: 合成・読み・経路・KS・運転・sweep・実現可能性・衝突・solution XML・公式 JSON、2026-10-04)
    # 376 → 394: 柔らかい手首のペグ挿入 18(pegsim: Whitney の量 6・幾何の第 2 実装・既知半径の円と円柱・副画素の縁・RGB-D の計測 3・重ね図・カメラ規約・合成 RGB-D・格子の集計・MJCF、2026-10-04。mujoco の 9 本は facade のみ)
    # 394 → 408: 視触覚センサ 14(tacsim: 複合弾性率・Hertz 球 / 線接触・表面変位・圧力・膜の押し込み 2・照明・合成 RGB・逆算・接触半径 2 経路・δ、2026-10-04。全部 numpy)
    # 408 → 428: マーカー配列のせん断 20(tacslip: Cattaneo–Mindlin 4・Cerruti 畳み込み 3・マーカー合成 3・検出/対応/追跡 4・相似則の逆算 2・指標 2・有限要素 2、2026-10-04。全部 numpy + scipy)
    # 428 → 445: 触覚双極子 → 把持内トルク 17(tactorque: 閉形式の圧 5・Boussinesq 核 4・ねじり 1・マーカー場の微分と双極子 7、2026-10-04。全部 numpy + scipy)
    # 445 → 471: エアホッケーのパック追跡・予測・打ち返し 26(puck: 台と閉形式の滑り 7・合成カメラと針穴 6・検出と追跡 2・速度 / μ / e の推定 3・5 節リンクと計画 7・MJCF 1、2026-10-04。全部 numpy)
    # 471 → 487: ペグ挿入の失敗検出と回復 16(pegfail: 表と署名と分類 5・Whitney の量 3・停滞と手首荷重 3・集計 3・既定 1・MJCF 1、2026-10-04。全部 numpy)
    # 487 → 510: 粉体の山を画像で測る 23(granular: 閉形式と Beverloo 5・排出の合成と計測 3・スプーン 2・流動性 1・合成と計測(側面像 / 高さ図 / 基準面 / 容器)7・球の山の選別と描画 4・MJCF 1、2026-10-05。全部 numpy)
    # 510 → 520: 視触覚センサの照明の較正 10(tacscalib: 読み込みと真値 2・照明の較正と順方向 2・勾配 LUT と逆引き 2・評価 3・外部 LUT のアダプタ 1、2026-10-05。全部 numpy)
    # 520 → 541: ペグ挿入を 2 本指の膜で読む 21(pegtactile 19: パッドと静力学 5・膜の合成と読み 3・接触状態 6・手首 2・対称性 3 + 既存へ 2: tacsim.contact_radius_fit_pixelwise / tacslip.mindlin_fit_vector、2026-10-05。全部 numpy + scipy)
    # 541 → 557: 食材の切断を画像で測る 16(cutting: 合成世界 5・刃と深さ 2・厚みと粗さ 2・力 6・CSV 1、2026-10-05。全部 numpy + scipy)
    # 557 → 573: ディアボロの解析模型と視覚 16(diabolo: 寸法と楕円体 3・論文の 1 ステップと走行と状態 3・投げの真値 1・張力 2・合成映像と軸と回転と追跡 6・MJCF 1、2026-10-05。numpy + scipy.ndimage)
    # 573 → 585: ドーム状の柔らかい指先の大変形接触 12(tacdome: 線形解 1・式 (3) の係数と補正と半径比と普遍形 4・順と逆 2・ばね列 1・
    #            円柱の厳密解 1・Hertz の誤差 1・接触像と半径 2、2026-10-05。全部 numpy)
    # 585 → 600: ペグの対称性で回転の探索を 1/n に絞る 15(pegsym: 多角形と穴と線形計画 3・回転の窓 1・二点接触 1・合成と打ち直しと向きの読み 4・畳み込みと探索 5・MJCF 1、2026-10-05。numpy だけ、向きの読みは fourierdesc と pegtactile の輪郭)
    # 600 → 613: 研削・研磨・拭き取りを画像で測る 13(polish: 圧力の窓と除去の地図 2・閉形式 3(断面・帯の幅・面積)・膜の画像と読み 4・高さ図と Preston 係数 2・弾性床 1・MJCF 1、2026-10-05。numpy だけ、Hertz は tacsim、2 値化は detect)
    # 613 → 628: 粉体のすくいと注ぎを画像で測る 15(scoop: 椀の閉形式と合成と読み 5・粒の数と秤の規則 2・傾けの導出と像 3・流れの合成と Boolean 模型と流量 3・MJCF 2、2026-10-05。numpy だけ、速さは pivops、山の角は granular)
    # 628 → 641: 乳鉢の粉砕を測る 13(grind: 粒度分布の読み・Dq・篩上・合成 4・粉砕則の閉形式と当てはめ 2・一次の破砕速度 1・独立試行の比較 1・AE の読み・帯域電力・D50 との対応 3・合成画像と D50 2、2026-10-05。numpy + scipy)
    # 641 → 647: 点の順に依らない FP64 の縮約 6(ozaki: Ozaki-I / II の積 2・上界 1・相互共分散と Kabsch 2・GPU の FP64 エミュレーションの探針 1、2026-10-05。numpy だけ、探針は ctypes)
    # 647 → 659: 群れが見えない障害物を速度場の乱れで察知する 12(swarmflow: SPH の核と密度 2・群れの模擬と俯瞰映像 2・速度場(追跡 / PIV)2・ポテンシャル流と欠損 2・衝突点と障害物 2・Ritter と SPH の浅水 2、2026-10-05。numpy + scipy、検出は blob2d、PIV は pivops)
    # 659 → 673: 粉末 X 線回折を測る 14(pxrd: CIF の読み・立方晶の原型・反射の一覧・Scherrer 4・デバイ環の合成・画素の 2θ・較正・方位積分 4・山・立方晶の指数付け 2・参照の辞書・NNLS の分率・残差の未知相・相を剥がす 4、2026-10-05。numpy + scipy)
    # 673 → 676: 粉の粒径から含量の CV と粉砕時間 3(doseunif: 対数正規の閉形式と Monte Carlo・測った粒径(画像の標本 / 粒度分布の表)からの CV と区間・粉砕則での逆算と合格の確率、2026-10-06。numpy + scipy)
    # 676 → 679: 包丁を指先の視触覚で持って切る 3(cuttouch: 部分滑りのねじりの数値解・2 パッドの読みから V・H・M_x と当たり位置・靱性、2026-10-06。numpy + scipy)
    # 679 → 694: 惑星ローバーの車輪の滑り 15(roverslip: Bekker の圧力・沈下の近似 2・Wong–Reece の力・沈下・牽引–滑り 3・斜面の滑り・視覚オドメトリ 2・ガウス過程・分位点回帰・予測・CVaR 4・コスト地図・経路・経路の評価 3、2026-10-06。numpy)
    assert len(opsdrive.OPSDRIVE) == 694
    # 台帳の op は実装モジュールの __all__ に在る(逆は要らない: 補助関数は台帳に載せない)
    import drivecourse, driveworld, lidarsim, drivettc, rsssafety, driveterrain, ballistics, balltrack, ballworld, racket
    import roadjp
    import kendama, kendamaworld
    import gsplatnp
    import drivelong
    import driveenv
    import driveinf
    import drivetraffic
    import drivedecide
    import drivelateral
    import drivecrossing
    import drivepass
    import motionio
    import drivehumanoid
    import agvfleet
    import carlabridge
    import drivetown
    import drivejapan
    import driveplateau
    import drivecommonroad
    import pegsim
    import tacsim
    import tacslip
    import tactorque
    import puck
    import pegfail
    import granular
    import tacscalib
    import pegtactile
    import cutting
    import diabolo
    import tacdome
    import pegsym
    import polish
    import scoop
    import grind
    import ozakimm
    import swarmflow
    import pxrd
    import doseunif
    import cuttouch
    import roverslip
    pub = (set(drivecourse.__all__) | set(driveworld.__all__) | set(lidarsim.__all__) | set(drivettc.__all__)
           | set(rsssafety.__all__) | set(driveterrain.__all__) | set(ballistics.__all__) | set(balltrack.__all__)
           | set(ballworld.__all__) | set(racket.__all__) | set(roadjp.__all__)
           | set(kendama.__all__) | set(kendamaworld.__all__) | set(gsplatnp.__all__) | set(drivelong.__all__)
           | set(driveenv.__all__) | set(driveinf.__all__) | set(drivetraffic.__all__)
           | set(drivedecide.__all__) | set(drivelateral.__all__)
           | set(drivecrossing.__all__) | set(drivepass.__all__) | set(motionio.__all__)
           | set(drivehumanoid.__all__) | set(agvfleet.__all__) | set(carlabridge.__all__) | set(drivetown.__all__) | set(drivejapan.__all__) | set(driveplateau.__all__) | set(drivecommonroad.__all__) | set(pegsim.__all__) | set(tacsim.__all__) | set(tacslip.__all__) | set(tactorque.__all__) | set(puck.__all__) | set(pegfail.__all__) | set(granular.__all__) | set(tacscalib.__all__) | set(pegtactile.__all__) | set(cutting.__all__) | set(diabolo.__all__) | set(tacdome.__all__) | set(pegsym.__all__) | set(polish.__all__) | set(scoop.__all__) | set(grind.__all__) | set(ozakimm.__all__) | set(swarmflow.__all__) | set(pxrd.__all__) | set(doseunif.__all__) | set(cuttouch.__all__) | set(roverslip.__all__))
    assert set(opsdrive.OPSDRIVE) <= pub, set(opsdrive.OPSDRIVE) - pub


def test_every_op_is_reachable_from_the_public_tier():
    """``fullseye.ledger.<名前>`` から呼べること(登録面を 1 つ落とすと静かに消える)。"""
    import fullseye as fs
    import opsdrive

    for name in opsdrive.OPSDRIVE:
        assert hasattr(fs.ledger, name), name


def test_the_typed_catalog_declares_the_family():
    import typed_catalog as tc

    rows = [r for r in tc.catalog() if r[1] == "drive"]
    assert len(rows) == 694
    assert {r[3] for r in rows} == {"table", "image2d", "signal", "matrix", "scalar", "any", "points", "rgba", "rgb", "voxel", "normalmap"}


def test_the_fuzzer_has_a_builder_for_every_op_and_they_run():
    """引数なしの op も、種を作る builder が無いとファザーからは永久に未実行。"""
    sys.path.insert(0, str(ROOT / "tools"))
    import chain_fuzz as cf
    import opsdrive

    rng = np.random.default_rng(0)
    for name, m in opsdrive.OPSDRIVE.items():
        assert name in cf.OP_ARG_BUILDERS, name
        args, kw = cf.OP_ARG_BUILDERS[name](None, rng)
        out = opsdrive.RESULT_ADAPTERS.get(name, lambda r: r)(m["func"](*args, **kw))
        assert cf.TYPE_CHECKS[m["out"]](out), (name, type(out))


def test_vendored_assets_ship_with_their_licence():
    import driveworld as DW

    d = DW.asset_dir() if not os.environ.get("FULLSEYE_KENNEY_DIR") else ROOT / "studio_assets" / "sample_3d" / "kenney"
    for kit in ("car-kit", "city-kit-roads"):
        lic = (Path(d) / kit / "License.txt").read_text(encoding="utf-8", errors="replace")
        assert "Creative Commons Zero" in lic and "CC0" in lic, kit
    for name, (kit, fname, _dims, _label) in DW.ASSETS.items():
        assert (Path(d) / {"cars": "car-kit", "roads": "city-kit-roads"}[kit] / fname).is_file(), name
