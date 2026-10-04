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
                                          "motion_io", "humanoid", "agv", "carla", "town", "japan", "commonroad", "pegsim", "tacsim", "tacslip", "tactorque"}
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
    assert len(opsdrive.OPSDRIVE) == 445
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
    pub = (set(drivecourse.__all__) | set(driveworld.__all__) | set(lidarsim.__all__) | set(drivettc.__all__)
           | set(rsssafety.__all__) | set(driveterrain.__all__) | set(ballistics.__all__) | set(balltrack.__all__)
           | set(ballworld.__all__) | set(racket.__all__) | set(roadjp.__all__)
           | set(kendama.__all__) | set(kendamaworld.__all__) | set(gsplatnp.__all__) | set(drivelong.__all__)
           | set(driveenv.__all__) | set(driveinf.__all__) | set(drivetraffic.__all__)
           | set(drivedecide.__all__) | set(drivelateral.__all__)
           | set(drivecrossing.__all__) | set(drivepass.__all__) | set(motionio.__all__)
           | set(drivehumanoid.__all__) | set(agvfleet.__all__) | set(carlabridge.__all__) | set(drivetown.__all__) | set(drivejapan.__all__) | set(driveplateau.__all__) | set(drivecommonroad.__all__) | set(pegsim.__all__) | set(tacsim.__all__) | set(tacslip.__all__) | set(tactorque.__all__))
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
    assert len(rows) == 445
    assert {r[3] for r in rows} == {"table", "image2d", "signal", "matrix", "scalar", "any", "points", "rgba", "rgb", "voxel"}


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
