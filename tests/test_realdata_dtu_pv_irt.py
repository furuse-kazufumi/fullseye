# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""realdata の DTU の PV 熱画像の取り口(2026-11-08): 置き場の解決と、読み手の fail-closed。データ本体は使わない。"""
from __future__ import annotations

import numpy as np
import pytest

import realdata


def test_cache_follows_the_environment_variable(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_PV_IRT_DATA", str(tmp_path))
    assert realdata.dtu_pv_irt_cache() == tmp_path


def test_missing_data_is_none_when_optional_and_an_error_when_required(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_PV_IRT_DATA", str(tmp_path))
    assert realdata.dtu_pv_irt_root(required=False) is None
    with pytest.raises(realdata.RealDataError):
        realdata.dtu_pv_irt_root(required=True)


def test_frame_refuses_conditions_outside_the_release(tmp_path, monkeypatch):
    monkeypatch.setenv("FULLSEYE_PV_IRT_DATA", str(tmp_path))
    with pytest.raises(ValueError):
        realdata.dtu_pv_irt_frame("Bypass diode", 1, 12, "800")
    with pytest.raises(ValueError):
        realdata.dtu_pv_irt_frame("Bypass diode", 1, 10, "1000")


def test_load_reads_a_well_formed_frame_and_refuses_bad_ones(tmp_path):
    h, w = realdata.DTU_PV_IRT_SHAPE
    good = tmp_path / "good.raw"
    a = np.linspace(10.0, 60.0, h * w, dtype="<f4").reshape(h, w)
    a.tofile(good)
    out = realdata.dtu_pv_irt_load(good)
    assert out.shape == (h, w) and np.allclose(out, a)
    short = tmp_path / "short.raw"
    a.ravel()[:-1].tofile(short)
    with pytest.raises(realdata.RealDataError):
        realdata.dtu_pv_irt_load(short)
    hot = tmp_path / "hot.raw"
    b = a.copy()
    b[0, 0] = 500.0
    b.tofile(hot)
    with pytest.raises(realdata.RealDataError):
        realdata.dtu_pv_irt_load(hot)


def test_credit_names_the_licence_and_doi():
    c = realdata.dtu_pv_irt_credit()
    assert "CC BY 4.0" in c and "10.11583/DTU.29665346.v1" in c


def test_frame_resolves_both_file_name_shapes(tmp_path, monkeypatch):
    """故障の 5 種(高さ → 日射)と汚れの 2 種(日射 → 高さ、後ろに飾り)の両方の形を 1 つだけ選ぶ。

    ★2026-11-08: 汚れの形が読み口に合わず、144 枚が集計から黙って外れていた(敵対的レビュー)。
    """
    monkeypatch.setenv("FULLSEYE_PV_IRT_DATA", str(tmp_path))
    root = tmp_path / "extracted" / "IRT DATASET"
    fault = root / "05_Short-circuited Bypass Diode" / "Module 1" / "IRT"
    soil = root / "06_Soiling 1" / "Module 1" / "IRT"
    fault.mkdir(parents=True)
    soil.mkdir(parents=True)
    for name in ("T10_10m_200_APV771.raw", "T10_14m_200_APV771.raw", "T10_10m_600_APV771.raw"):
        (fault / name).write_bytes(b"")
    for name in ("T_200_10m - Copy_PD.raw", "T_200_14m_PD.raw", "T_800_10m_PD.png_S1.raw", "T_800_8m - Copy_PD_B1.raw"):
        (soil / name).write_bytes(b"")
    f = realdata.dtu_pv_irt_frame
    assert f("05_Short-circuited Bypass Diode", 1, 10, "200").name == "T10_10m_200_APV771.raw"
    assert f("06_Soiling 1", 1, 10, "200").name == "T_200_10m - Copy_PD.raw"
    assert f("06_Soiling 1", 1, 14, "200").name == "T_200_14m_PD.raw"
    assert f("06_Soiling 1", 1, 10, "800").name == "T_800_10m_PD.png_S1.raw"
    assert f("06_Soiling 1", 1, 8, "800").name == "T_800_8m - Copy_PD_B1.raw"
    with pytest.raises(realdata.RealDataError):
        f("06_Soiling 1", 1, 20, "200")            # 無い組は 0 個 → 例外(黙って飛ばさない)
