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
                                          "ball", "balltrack", "ballworld", "racket", "roadjp"}
    assert len(opsdrive.OPSDRIVE) == 120
    # 台帳の op は実装モジュールの __all__ に在る(逆は要らない: 補助関数は台帳に載せない)
    import drivecourse, driveworld, lidarsim, drivettc, rsssafety, driveterrain, ballistics, balltrack, ballworld, racket
    import roadjp
    pub = (set(drivecourse.__all__) | set(driveworld.__all__) | set(lidarsim.__all__) | set(drivettc.__all__)
           | set(rsssafety.__all__) | set(driveterrain.__all__) | set(ballistics.__all__) | set(balltrack.__all__)
           | set(ballworld.__all__) | set(racket.__all__) | set(roadjp.__all__))
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
    assert len(rows) == 120
    assert {r[3] for r in rows} == {"table", "image2d", "signal", "matrix", "scalar", "any", "points", "rgba"}


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
