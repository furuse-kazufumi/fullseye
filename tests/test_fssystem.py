# -*- coding: utf-8 -*-
"""システムパラメータ層の検査。

守りたいのは 2 つ:

1. **可変グローバルではない** —— スレッド/タスクごとに独立し、例外経路でも
   必ず戻る。共有された可変既定は、並行に走る生成器のあいだでレースになり、
   **例外にならず「もっともらしく間違った図」**として出てくる(``drawstyle``
   が同じ判断をした理由)。
2. **緩められない** —— 登録できるのは「厳しくする方向のみ」か「数値に一切
   影響しない」パラメータだけ。``data_range`` の既定を隠れた設定で供給できると、
   呼び出し側のコードが 1 文字も変わらないまま PSNR が 48.13 dB ずれる。
"""
from __future__ import annotations

import concurrent.futures

import numpy as np
import pytest

import colortransport as CT
import fssystem as S
import imgmetrics as M


@pytest.fixture(autouse=True)
def _clean_system():
    S.reset_system()
    yield
    S.reset_system()


# =========================================================================
# 1. 表そのものの規律
# =========================================================================

def test_every_parameter_declares_whether_it_can_loosen_anything():
    """**「検査を切って速くする」パラメータはこの表に載せられない。**

    宣言が無いものを足すとここが落ちる ―― 黙って緩い設定が増えないように。
    """
    for name, spec in S.SYSTEM_PARAMS.items():
        assert set(spec) >= {"values", "default", "tightens_only", "affects_numbers", "doc"}, name
        assert spec["default"] in spec["values"], name
        assert isinstance(spec["tightens_only"], bool), name
        # 数値に影響するなら、厳しくする方向でなければならない
        if spec["affects_numbers"]:
            assert spec["tightens_only"], f"{name} は数値に影響するのに緩められる"
        assert spec["doc"].strip(), name


def test_no_registered_parameter_changes_a_number_today():
    """今のところ数値に影響するパラメータは 1 つも無い(それが望ましい状態)。"""
    assert not any(s["affects_numbers"] for s in S.SYSTEM_PARAMS.values())


def test_defaults_are_the_safe_side():
    assert S.get_system("metric_contract") == "strict"
    assert S.get_system("extra_checks") == "off"
    assert S.get_system("unmeasurable_policy") == "worst"


def test_unknown_names_and_values_fail_closed():
    """誤字が『効いたように見える』のを防ぐ。"""
    with pytest.raises(ValueError, match="unknown system parameter"):
        S.set_system("metrics_contract", "tolerant")        # s が 1 つ多い
    with pytest.raises(ValueError, match="unknown system parameter"):
        S.get_system("nope")
    with pytest.raises(ValueError, match="takes one of"):
        S.set_system("extra_checks", "yes")
    with pytest.raises(ValueError, match="unknown system parameter"):
        with S.system(nope="on"):
            pass


# =========================================================================
# 2. 文脈のふるまい
# =========================================================================

def test_set_system_returns_the_previous_value():
    assert S.set_system("extra_checks", "on") == "off"
    assert S.get_system("extra_checks") == "on"
    assert S.set_system("extra_checks", "off") == "on"


def test_the_context_manager_restores_even_when_the_body_raises():
    with pytest.raises(RuntimeError):
        with S.system(extra_checks="on", metric_contract="tolerant"):
            assert S.get_system("extra_checks") == "on"
            raise RuntimeError("boom")
    assert S.get_system("extra_checks") == "off"
    assert S.get_system("metric_contract") == "strict"


def test_nesting_unwinds_in_order():
    with S.system(extra_checks="on"):
        with S.system(extra_checks="off"):
            assert S.get_system("extra_checks") == "off"
        assert S.get_system("extra_checks") == "on"
    assert S.get_system("extra_checks") == "off"


def test_one_thread_does_not_see_another_thread_setting():
    """これが可変グローバルを避けた理由 —— 並行に走る生成器がレースしない。"""
    def worker(value):
        with S.system(extra_checks=value):
            # 相手が書き換えていれば、ここで違う値が見える
            return [S.get_system("extra_checks") for _ in range(200)]

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        a = ex.submit(worker, "on")
        b = ex.submit(worker, "off")
        assert set(a.result()) == {"on"}
        assert set(b.result()) == {"off"}
    assert S.get_system("extra_checks") == "off"


def test_snapshot_carries_the_settings_so_a_report_can_state_them():
    with S.system(metric_contract="tolerant"):
        snap = S.system_snapshot()
    assert snap["metric_contract"] == "tolerant"
    assert set(snap) == set(S.SYSTEM_PARAMS)


def test_query_system_describes_a_parameter():
    assert "extra_checks" in S.query_system()
    spec = S.query_system("extra_checks")
    assert spec["values"] == ("off", "on")
    with pytest.raises(ValueError, match="unknown system parameter"):
        S.query_system("nope")


def test_reset_puts_everything_back():
    S.set_system("extra_checks", "on")
    S.set_system("metric_contract", "tolerant")
    S.reset_system()
    assert S.system_snapshot() == {n: s["default"] for n, s in S.SYSTEM_PARAMS.items()}


# =========================================================================
# 3. extra_checks が**実際に効く**こと(効かない設定は嘘なので)
# =========================================================================

_GRATING_A = np.tile(np.arange(64, dtype=np.uint8), (64, 1))
_GRATING_B = np.repeat(np.arange(64, dtype=np.uint8), 64).reshape(64, 64)
_TIED = np.array([[3, 3, 3, 1, 1, 2, 2, 2, 2, 5]], dtype=np.uint8)
_REF = np.linspace(0.0, 1.0, 10)


def test_off_by_default_so_existing_callers_are_untouched():
    assert M.ncd(_GRATING_A, _GRATING_B, symmetric=False) == pytest.approx(0.571429, abs=1e-5)
    assert len(np.unique(CT.histogram_match(_TIED, _REF, ties="break"))) == 10


def test_extra_checks_refuses_an_asymmetric_distance():
    with S.system(extra_checks="on"):
        with pytest.raises(ValueError, match="not a distance"):
            M.ncd(_GRATING_A, _GRATING_B, symmetric=False)


def test_extra_checks_refuses_splitting_tied_pixels():
    with S.system(extra_checks="on"):
        with pytest.raises(ValueError, match="tied pixel"):
            CT.histogram_match(_TIED, _REF, ties="break")


def test_extra_checks_leaves_the_correct_calls_alone():
    """厳しくするだけ ―― 正しい呼び出しは同じ値を返す。"""
    before_ncd = M.ncd(_GRATING_A, _GRATING_B)
    before_hm = CT.histogram_match(_TIED, _REF)
    with S.system(extra_checks="on"):
        assert M.ncd(_GRATING_A, _GRATING_B) == before_ncd
        assert np.array_equal(CT.histogram_match(_TIED, _REF), before_hm)


def test_extra_checks_does_not_fire_when_there_is_nothing_to_object_to():
    """同値が無ければ ties='break' は無害なので、on でも通る。"""
    rng = np.random.default_rng(0)
    continuous = rng.random((16, 16))
    with S.system(extra_checks="on"):
        out = CT.histogram_match(continuous, rng.normal(0.5, 0.2, 256), ties="break")
    assert out.shape == continuous.shape
