"""2026-10-31 に公開から外した anim3d 展示の復元可能性を守る。"""
from __future__ import annotations

import json
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "docs" / "view2026"
WITHDRAWN_IDS = {
    "satellite_gsd", "multibeam_bathymetry", "ultrasound_bmode",
    "rail_light_section", "particle_dissolution", "borescope",
    "gauss_bonnet", "oct_retina", "laser_diffraction", "organ_volume",
    "pulseox", "poc_star_tracker", "bridge_dic", "hypercentric_lens",
    "kelvin_wake", "ship_stability", "thermo_delamination", "venue_shadow",
    "shack-hartmann", "tablet_inspection", "catenary_wear",
    "insar_subsidence", "tunnel_crack", "photoelastic",
    "salt_xrd_anim3d", "interactive_anim3d_viewer",
}
KEPT_IDS: set[str] = set()
NON_FULLSEYE_IDS = {"poc_settlement_significance", "poc_gravitational_lens_invariants"}


def load(name: str) -> dict:
    return json.loads((VIEW / name).read_text(encoding="utf-8"))


def test_only_reviewed_anim3d_exhibits_remain_public() -> None:
    public = load("exhibits.json")
    anim3d = {item["id"] for item in public["exhibits"]
              if item["category"] == "anim3d"}
    assert anim3d == KEPT_IDS
    assert not (WITHDRAWN_IDS & {item["id"] for item in public["exhibits"]})


def test_withdrawn_catalog_is_complete_and_recoverable() -> None:
    archive = load("withdrawn_2026_10_31.json")
    items = archive["exhibits"]
    assert len(items) == 26
    assert {item["id"] for item in items} == WITHDRAWN_IDS
    assert sum(item["withdrawn_reason"].startswith("rework:") for item in items) == 13
    assert sum(item["withdrawn_reason"].startswith("hold:") for item in items) == 13
    for item in items:
        assert (ROOT / "docs" / item["media_path"]).is_file(), item["id"]


def test_non_fullseye_catalog_is_complete_and_not_public() -> None:
    archive = load("withdrawn_2026_11_01.json")
    items = archive["exhibits"]
    assert len(items) == 2
    assert {item["id"] for item in items} == NON_FULLSEYE_IDS
    assert {item["id"]: item["withdrawn_reason"] for item in items} == {
        "poc_settlement_significance":
            "no-fullseye: Fullseye の呼び出しは fs.ledger だけ。計算は scipy",
        "poc_gravitational_lens_invariants":
            "no-fullseye: Fullseye の呼び出しは fs.ledger だけ",
    }
    public = load("exhibits.json")
    assert not (NON_FULLSEYE_IDS & {item["id"] for item in public["exhibits"]})


def test_featured_batch_does_not_revive_any_withdrawn_id_in_a_temporary_catalog(tmp_path) -> None:
    spec = importlib.util.spec_from_file_location(
        "build_view2026_featured_batch", ROOT / "tools" / "build_view2026_featured_batch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    temporary = tmp_path / "exhibits.json"
    temporary.write_text((VIEW / "exhibits.json").read_text(encoding="utf-8"), encoding="utf-8")
    module.DATA = temporary
    module.main()
    rebuilt = json.loads(temporary.read_text(encoding="utf-8"))
    all_withdrawn = WITHDRAWN_IDS | NON_FULLSEYE_IDS
    assert not (all_withdrawn & {item["id"] for item in rebuilt["exhibits"]})


def test_withdrawn_exhibits_are_not_in_featured_thumbnail_spec() -> None:
    source = (ROOT / "tools" / "gen_view2026_thumbs.py").read_text(encoding="utf-8")
    spec = source.split("SPEC = [", 1)[1].split("]", 1)[0]
    assert all(f'("{item_id}",' not in spec for item_id in WITHDRAWN_IDS)
