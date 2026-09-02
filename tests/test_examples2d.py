# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""examples2d 登録の整合性(実行そのものは各 example の直接実行 + モジュール単体テストで担保)。"""
import os

import examples2d as EX


def test_registry_ids_map_to_runnable_scripts():
    names = EX.names()
    assert len(names) >= 3
    for i in ("image_morph", "contour_fourier", "draw_annotate"):
        assert i in names
        assert os.path.exists(EX.path(i)), i
        src = EX.code(i)
        assert "PASS" in src and "assert" in src        # self-asserting runnable script


def test_by_task_groups_all_entries():
    grouped = sum(len(v) for v in EX.by_task().values())
    assert grouped == len(EX.names())
    assert "morphing" in EX.by_task() and "drawing" in EX.by_task()


def test_registry_and_disk_agree_both_ways():
    """Two-way reconciliation: every file is registered or explicitly excluded, and every
    registered/excluded id exists on disk. A one-way superset check let ~40 scripts sit
    unlisted (2026-09-02 audit); this closes that hole in both directions."""
    disk = set(EX.discover())
    reg = set(EX.names())
    exc = set(EX.EXCLUDED)
    assert reg <= disk, sorted(reg - disk)                # registered id without a script
    assert exc <= disk, sorted(exc - disk)                # stale exclusion (file gone)
    assert not (reg & exc), sorted(reg & exc)             # cannot be both
    assert disk - reg - exc == set(), sorted(disk - reg - exc)   # unlisted script on disk
    gaps = EX.registry_gaps()
    assert gaps == {"unregistered": [], "missing": [], "overlap": []}, gaps
    assert len(reg) >= 57 and len(disk) == len(reg) + len(exc)


def test_exclusions_carry_an_honest_reason():
    for i, why in EX.EXCLUDED.items():
        assert isinstance(why, str) and len(why) >= 20, i
        assert "need" in why or "requires" in why or "cannot" in why, (i, why)


def test_every_entry_is_well_formed_and_unique():
    ids = EX.names()
    assert len(ids) == len(set(ids)), "duplicate example id"
    for e in EX.EXAMPLES:
        assert set(e) >= {"id", "task", "data", "name", "summary"}, e.get("id")
        assert e["name"].strip() and len(e["summary"].strip()) >= 20, e["id"]
        assert e["task"] in EX.tasks()
        src = EX.code(e["id"])
        assert '__main__' in src or e["id"] == "quickstart", e["id"]   # runnable as a script


def test_registry_gaps_reports_an_unlisted_file(tmp_path, monkeypatch):
    """The reconciliation must actually fire on a stray script (not just pass today)."""
    real = EX.DIR
    stray = tmp_path / "examples"
    stray.mkdir()
    for i in list(EX.names()) + list(EX.EXCLUDED):
        (stray / (i + ".py")).write_text("# copy\n", encoding="utf-8")
    (stray / "not_registered_yet.py").write_text("print('hi')\n", encoding="utf-8")
    monkeypatch.setattr(EX, "DIR", str(stray))
    try:
        gaps = EX.registry_gaps()
    finally:
        monkeypatch.setattr(EX, "DIR", real)
    assert gaps["unregistered"] == ["not_registered_yet"]
    assert gaps["missing"] == [] and gaps["overlap"] == []
