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


def test_discover_is_superset_of_registry():
    disk = set(EX.discover())
    assert set(EX.names()) <= disk                       # every registered id exists on disk
