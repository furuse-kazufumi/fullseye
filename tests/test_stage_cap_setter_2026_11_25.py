"""段数の上限を、Studio のモデルの入口と MCP の検査の両方で確かめる。

Every Studio loader funnels through ``PipelineModel.stages``; MCP checks the
``stages`` array against the same cap and must name the observed count.
"""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_model_setter_refuses_more_than_the_cap_before_normalising():
    studio = pytest.importorskip("studio")
    model = studio.PipelineModel()
    with pytest.raises(ValueError) as err:
        model.stages = [["identity", 0, 0]] * (studio.MAX_PROGRAM_STAGES + 1)
    text = str(err.value)
    assert str(studio.MAX_PROGRAM_STAGES + 1) in text and str(studio.MAX_PROGRAM_STAGES) in text
    model.stages = [["identity", 0, 0]] * 2
    assert len(model.stages) == 2


def test_model_setter_reads_a_generator_only_one_past_the_cap():
    studio = pytest.importorskip("studio")
    pulled = []

    def endless():
        while True:
            pulled.append(1)
            yield ["identity", 0, 0]

    with pytest.raises(ValueError):
        studio.PipelineModel().stages = endless()
    assert len(pulled) == studio.MAX_PROGRAM_STAGES + 1


def test_mcp_stage_array_refusal_names_the_count_and_the_fix():
    server = pytest.importorskip("fullseye.mcp.server")
    from fssystem import MAX_PROGRAM_STAGES, pipeline_stage_limit_message
    assert "513" in pipeline_stage_limit_message(513)
    src = open(server.__file__, encoding="utf-8").read()
    assert "pipeline_stage_limit_message(len(value))" in src
