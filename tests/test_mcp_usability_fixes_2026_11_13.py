# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""AI の役で MCP を使った検証(2026-11-13)の報告 2〜13 番と C の回帰試験。

報告の現象を 1 件ずつ再現してから直した。各試験の docstring に、直す前に何が起きていたかを書く。
"""
import json
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fullseye.mcp import server as S                              # noqa: E402
from fullseye.mcp.catalog import Catalog                          # noqa: E402
from fullseye.mcp.handles import HandleStore                      # noqa: E402
from fullseye.mcp.opworker import close_worker                    # noqa: E402


@pytest.fixture(scope="module")
def cat():
    return Catalog.load()


@pytest.fixture()
def store(tmp_path):
    return HandleStore(thumb_dir=str(tmp_path / "thumb"))


@pytest.fixture(scope="module", autouse=True)
def _close_shared_worker():
    yield
    close_worker()


def _text(result):
    return result["content"][0]["text"]


# --------------------------------------------------------------------------- 2: 失敗の本文に段番号と理由
def test_validation_failure_text_names_every_stage_and_reason(cat, store):
    """直す前: fullseye_validate_pipeline の不合格の本文は「error」と「stages=0」だけで、理由は structuredContent にしか無かった。"""
    r = S.call_tool("fullseye_validate_pipeline", {"stages": [
        {"op": "lockin_thermal_wave"}, {"op": "no_such_op_xyz"}]}, cat, store)
    text = _text(r)
    lines = text.splitlines()
    assert lines[0].startswith("検証: 不合格(誤り 2 件")
    assert lines[1].startswith("段 1 lockin_thermal_wave: not_executable_in_mcp") and "代わりに" in lines[1]
    assert lines[2].startswith("段 2 no_such_op_xyz: unknown_op")
    ok = S.call_tool("fullseye_validate_pipeline", {"start_sort": "image", "stages": [{"op": "otsu"}]}, cat, store)
    assert _text(ok).startswith("検証: 合格(1 段") and "段 1 otsu: image -> region" in _text(ok)


def test_pipeline_type_error_message_lists_stage_and_fix(cat, store):
    """直す前: -32602 の本文は最初の誤りの JSON を 1 行に繋いだ物だった。"""
    h = S.call_tool("fullseye_load_image", {"path": "coins"}, cat, store)["structuredContent"]["handle"]
    with pytest.raises(S.ArgError) as err:
        S.call_tool("fullseye_pipeline", {"handle": h, "stages": [{"op": "otsu"}, {"op": "gaussian"}]}, cat, store)
    msg = str(err.value)
    assert "段 2 gaussian: sort_mismatch" in msg and "来たのは region、要るのは image" in msg
    assert "直し方の候補" in msg and "1 段も走らせていない" in msg and not msg.lstrip().startswith("{")


def test_strict_failure_text_has_one_line_per_stage(cat, store):
    """直す前: 段が失敗した時の本文は、結果の JSON を丸ごと 1 行に繋いでいた。"""
    r = S.call_tool("fullseye_pipeline", {"stages": [
        {"op": "illumination_design", "params": {"surface": "no such surface"}}]}, cat, store)
    assert r["isError"]
    lines = _text(r).splitlines()
    assert lines[0] == "段 1 illumination_design failed in strict mode: execution_failed"
    assert lines[1].startswith("段 1 illumination_design: 失敗 execution_failed — ValueError:")
    assert "動く見本" in _text(r) and "{\"completed\"" not in _text(r)


# --------------------------------------------------------------------------- 3: 入力を読まない op を提案と plan から外す
def test_fixes_and_plans_never_route_through_ops_that_ignore_their_input(cat, store):
    """直す前: image → region の直し方の候補が hx_gen_empty_region(入力の中身を見ない生成の op)で、
    従った gaussian → sobel_amp → hx_gen_empty_region → count_obj が 0.0 を判定 ok で返した。"""
    from fullseye.opsearch import _input_independent_names, plan
    blind = _input_independent_names()
    assert "hx_gen_empty_region" in blind and len(blind) >= 20
    checked = S.validate_pipeline([{"op": "gaussian"}, {"op": "otsu"}, {"op": "sobel_amp"}, {"op": "count_obj"}],
                                  "image", cat, store=store)
    fixes = [f for e in checked["errors"] for m in e.get("value", []) if isinstance(m, dict)
             for f in m.get("fixes", []) if f.get("kind") == "conversion"]
    assert fixes, checked["errors"]
    used = {op for f in fixes for op in f["ops"]}
    assert used and not (used & blind), used & blind
    routes = plan("image", "region", constraints={"k": 10, "max_depth": 3})
    assert routes.get("ok") and routes["plans"]
    ops_in_plans = {op for pl in routes["plans"] for op in pl["ops"]}
    assert ops_in_plans and not (ops_in_plans & blind), ops_in_plans & blind


# --------------------------------------------------------------------------- 4: 実行できない op の誤り文と「近い名前」
def test_alternatives_share_a_name_word_and_the_name_is_not_its_own_neighbour(cat, store):
    """直す前: fullseye_apply は台帳の op にも「registry 層に無い」とだけ返し、「近い名前」に同じ名前を出した。
    代わりの op は、同じ分類で名前の語を共有する物だけ(共有しなければ並べない)。"""
    from fullseye.opsearch import mcp_unavailable
    lens = mcp_unavailable("lens_file_read")["executable_alternatives"]
    assert len(lens) >= 3
    assert all(set(name.split("_")) & {"lens", "file", "read"} for name in lens)
    thermal = mcp_unavailable("lockin_thermal_wave")
    assert thermal["reason"] == "sample_run_failed"
    alternatives = thermal["executable_alternatives"]
    assert len(alternatives) <= 5
    assert not [n for n in alternatives if not set(n.split("_")) & {"lockin", "thermal", "wave"}]
    h = S.call_tool("fullseye_load_image", {"path": "coins"}, cat, store)["structuredContent"]["handle"]
    with pytest.raises(S.ArgError) as err:
        S.call_tool("fullseye_apply", {"handle": h, "op": "lockin_phase"}, cat, store)
    assert "'lockin_phase'(registry 層に無い)" in str(err.value)
    assert "近い名前: ['lockin_phase'" not in str(err.value) and "op_run('lockin_phase'" in str(err.value)


# --------------------------------------------------------------------------- 5: op_cards の missing と executable
def test_op_cards_report_names_dropped_for_budget_and_mean_mcp_by_executable(cat, store):
    """直す前: 上限で落とした名前はどこにも書かれず(missing は知らない名前だけ)、executable は
    「Python の関数として呼べるか」で、true のカードの op を pipeline に渡すと not_executable_in_mcp で断られた。"""
    from fullseye.opsearch import op_cards
    small = op_cards(["gaussian", "otsu", "lens_file_read", "no_such_op_q"], 60)
    names = [c["name"] for c in small["cards"]]
    dropped = [m["name"] for m in small["missing"] if m["reason"] == "budget_tokens"]
    assert small["truncated"] and dropped and set(names) | set(dropped) == {"gaussian", "otsu", "lens_file_read"}
    assert [m["name"] for m in small["missing"] if m["reason"] == "unknown_op"] == ["no_such_op_q"]
    assert small["omitted_for_budget"] == dropped
    r = S.call_tool("fullseye_op_cards", {"names": ["gaussian", "otsu", "lens_file_read", "no_such_op_q"],
                                          "budget_tokens": 60}, cat, store)
    first = _text(r).splitlines()[0]
    assert first.startswith("落とした名前: ") and "budget_tokens=60" in first and "no_such_op_q(知らない op" in first
    cards = {c["name"]: c for c in op_cards(["illumination_design", "lens_file_read", "gaussian"], 20000)["cards"]}
    assert len(cards) == 3
    assert cards["illumination_design"]["executable"] is True and cards["gaussian"]["executable"] is True
    assert cards["lens_file_read"]["executable"] is False and cards["lens_file_read"]["python_executable"] is True
    assert cards["lens_file_read"]["mcp_unavailable"]["reason"] == "io_parameter"


# --------------------------------------------------------------------------- 6: find_ops の重複と executable_only
def test_find_ops_proposals_are_references_and_executable_only_filters(cat, store):
    """直す前: proposals は ops / recipes の行を丸ごと写していて(検証の 1 回で ops 2.6 KB に proposals 4.3 KB)、
    MCP で走る op だけに絞る手が無かった。"""
    r = S.call_tool("fullseye_find_ops", {"query": "illumination design glossy metal"}, cat, store)
    sc = r["structuredContent"]
    assert len(sc["proposals"]) == 7
    assert all(set(p) == {"kind", "name", "executable"} for p in sc["proposals"])
    assert [p["name"] for p in sc["proposals"] if p["kind"] == "op"] == [o["name"] for o in sc["ops"]]
    assert len(json.dumps(sc["proposals"], ensure_ascii=False)) < len(json.dumps(sc["ops"], ensure_ascii=False)) / 3
    only = S.call_tool("fullseye_find_ops", {"query": "lens", "executable_only": True}, cat, store)["structuredContent"]
    assert only["executable_only"] is True and len(only["ops"]) >= 3
    assert all(p["executable"] for p in only["proposals"] if p["kind"] == "op")
    plain = S.call_tool("fullseye_find_ops", {"query": "lens"}, cat, store)["structuredContent"]
    assert "executable_only" not in plain and 3 <= len(plain["proposals"]) <= 7 and 3 <= len(only["proposals"]) <= 7
    assert any(not p["executable"] for p in plain["proposals"])     # 絞らなければ走らない op も混ざる
    assert not plain["proposals"][0]["executable"] or plain["proposals"][0]["name"] in {o["name"] for o in only["ops"]}


# --------------------------------------------------------------------------- 7: tools/list の引数の説明と言語
def test_tools_list_explains_stage_and_plan_arguments_in_one_language():
    """直す前: 段の a・b・inputs と plan の have・want に説明が無く、op_cards / validate_pipeline / load_stack の
    説明だけ英語だった(他は日本語)。minimal の予算(1,500 トークン)は守る。"""
    import re
    from fullseye.mcp.server import TOOLS, handle_tools_list
    for tool in ("fullseye_pipeline", "fullseye_validate_pipeline"):
        props = TOOLS[tool]["inputSchema"]["properties"]["stages"]["items"]["properties"]
        missing = [k for k in ("inputs", "params", "a") if not props[k].get("description")]
        assert missing == [], (tool, missing)
    plan = TOOLS["fullseye_plan"]["inputSchema"]["properties"]
    assert plan["have"]["description"] and plan["want"]["description"] and plan["goal"]["description"]
    english = [n for n, t in TOOLS.items() if not re.search(r"[぀-ヿ一-鿿]", t["description"])]
    assert len(TOOLS) >= 20 and english == []
    assert handle_tools_list({"profile": "minimal"})["estimated_tokens"] < 1500


# --------------------------------------------------------------------------- 8: 計測値に単位と意味
def test_measurements_carry_meaning_unit_and_the_largest_component_scope(cat, store):
    """直す前: otsu → diameter_region の 46.3 が単位も意味も無く返り、それが 10 片以上に切れた傷の
    最大の 1 片の弦だという事が結果から分からなかった。px→mm の値にも mm が付いていなかった。"""
    h = S.call_tool("fullseye_load_image", {"path": "metal_hairline_scratch"}, cat, store)["structuredContent"]["handle"]
    r = S.call_tool("fullseye_pipeline", {"handle": h, "stages": [{"op": "otsu"}, {"op": "diameter_region"}],
                                          "vision": "none"}, cat, store)
    rec = r["structuredContent"]["stages"][-1]
    assert rec["unit"] == "px" and "longest chord" in rec["meaning"]
    assert rec["measured"]["scope"] == "largest_connected_component" and rec["measured"]["components_in_input"] >= 2
    text = _text(r)
    assert "単位 px" in text and "最大の 1 つだけを測った" in text
    count = S.call_tool("fullseye_pipeline", {"handle": h, "stages": [{"op": "otsu"}, {"op": "count_obj"}],
                                              "vision": "none"}, cat, store)
    assert count["structuredContent"]["stages"][-1]["unit"] == "count"
    assert "measured" not in count["structuredContent"]["stages"][-1] and "最大の 1 つ" not in _text(count)
    mm = S.call_tool("fullseye_pipeline", {"stages": [{"op": "pixel_to_world",
                                                       "params": {"value_px": 46.3, "mm_per_px": 0.02}}]}, cat, store)
    assert mm["structuredContent"]["stages"][0]["units"] == {"value": "mm"} and "value = 0.926 mm" in _text(mm)


# --------------------------------------------------------------------------- 9: catalog_coverage
def test_catalog_coverage_defaults_to_counts_and_hides_host_paths(cat, store):
    """直す前: 既定で名前の一覧(数千件)とホストの絶対パス(利用者名を含む)を返していた。"""
    r = S.call_tool("fullseye_catalog_coverage", {}, cat, store)
    sc = r["structuredContent"]
    assert sc["detail"] is False and isinstance(sc["index_without_note"], int) and "note_only_names" not in sc
    dumped = json.dumps(r, ensure_ascii=False)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert root not in dumped and root.replace("\\", "/") not in dumped and len(dumped) < 4000
    full = S.call_tool("fullseye_catalog_coverage", {"detail": True}, cat, store)["structuredContent"]
    assert isinstance(full["index_not_in_registry"], list) and len(full["index_not_in_registry"]) ==         sc["index_not_in_registry"]


# --------------------------------------------------------------------------- 10: 読み込みの境界
def _link_dir(link, target):
    """根の中に、根の外を指すディレクトリのリンクを作る(Windows はジャンクション、他は symlink)。"""
    import subprocess
    if os.name == "nt":
        done = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture_output=True)
        return done.returncode == 0
    try:
        os.symlink(str(target), str(link), target_is_directory=True)
        return True
    except OSError:
        return False


def test_load_boundary_pixels_links_device_names_nan_and_temp_folder(cat, tmp_path):
    """直す前: 20,000×20,000 の PNG を全部復号してから断り(4 秒)、根の中のリンクの先(根の外)のファイル名を
    list_samples に出し、path=NUL で -32603、import_json が NaN / Infinity を受け、一時フォルダが終了後も残った。"""
    import fullseye
    import imgio
    root, outside = tmp_path / "root", tmp_path / "outside"
    root.mkdir(); outside.mkdir()
    imgio.save(str(root / "ok.png"), np.zeros((8, 8, 3)))
    imgio.save(str(outside / "secret_name.png"), np.zeros((8, 8, 3)))
    # 宣言だけが巨大な PNG(IHDR が 20,000 × 20,000)。中身は復号させない
    import struct
    import zlib
    ihdr = struct.pack(">IIBBBBB", 20000, 20000, 8, 0, 0, 0, 0)
    chunk = lambda kind, data: (struct.pack(">I", len(data)) + kind + data      # noqa: E731
                                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))
    (root / "huge.png").write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IEND", b""))
    linked = _link_dir(root / "jn", outside)
    store = HandleStore(roots=[str(root)])
    files = store.root_files()
    assert "ok.png" in files and not [f for f in files if "secret_name" in f], files
    if linked:
        with pytest.raises(S.ArgError, match="根の外"):
            S.call_tool("fullseye_load_image", {"path": "jn/secret_name.png"}, cat, store)
    with pytest.raises(S.ArgError, match="画素が多すぎる") as err:
        S.call_tool("fullseye_load_image", {"path": "huge.png"}, cat, store)
    assert "復号しない" in str(err.value) and str(tmp_path) not in str(err.value)
    with pytest.raises(S.ArgError) as err:
        S.call_tool("fullseye_load_image", {"path": "NUL"}, cat, store)
    assert "<outside>/" in str(err.value) and str(tmp_path) not in str(err.value)
    env = json.dumps(fullseye.to_jsonable(np.float64(1.5), "feature"))
    for bad in (env.replace("1.5", "NaN"), env.replace("1.5", "Infinity")):
        with pytest.raises(S.ArgError, match="非有限"):
            S.call_tool("fullseye_import_json", {"json": bad}, cat, store)
    with pytest.raises(S.ArgError, match="非有限"):
        S.call_tool("fullseye_import_json", {"envelope": fullseye.to_jsonable(np.array([1.0, np.nan]), "signal")},
                    cat, store)
    ok = S.call_tool("fullseye_import_json", {"json": env}, cat, store)
    assert not ok["isError"]
    folder = store.thumb_dir
    assert os.path.isdir(folder)
    store._cleanup()
    assert not os.path.exists(folder)
    given = tmp_path / "given"
    HandleStore(roots=[str(root)], thumb_dir=str(given))
    import gc
    gc.collect()
    assert given.is_dir()                                         # 渡されたフォルダは消さない


# --------------------------------------------------------------------------- 11: 型の門で落ちた試行を数えない
def test_type_gate_refusals_do_not_use_up_scoring_attempts(cat, store):
    """直す前: 型の門で落ちた試行(1 段も走らせず、真値に触れない)も 1 回に数え、型を直しているだけで
    32 回の枠を使い切った。走らせた試行(出力の型の検査から先)は従来どおり数える。"""
    made = S.call_tool("fullseye_make_task", {"kind": "blob_count", "seed": 3}, cat, store)["structuredContent"]
    tid, before = made["task_id"], made["attempts_used"]
    for _ in range(5):
        r = S.call_tool("fullseye_score_pipeline", {"task_id": tid, "stages": [{"op": "gaussian"}, {"op": "count_obj"}]},
                        cat, store)
        sc = r["structuredContent"]
        assert sc["reason"] == "type_gate" and sc["attempt_counted"] is False and sc["attempts_used"] == before
    counted = S.call_tool("fullseye_score_pipeline", {"task_id": tid, "stages": [{"op": "otsu"}]}, cat, store)
    sc = counted["structuredContent"]
    assert sc["reason"] == "output_sort_mismatch" and sc["attempt_counted"] is True and sc["attempts_used"] == before + 1


# --------------------------------------------------------------------------- 12: 日本語の検索
#: 検証(2026-11-13)の日本語の問い合わせと、上位 5 件に入るべき op の名前の型(依頼の意図から人が決めた)。
_JA_QUERIES = (
    ("光沢のある金属の表面の傷を見つけて長さを測りたい", r"illumin|lighting|solid_angle|defect_contrast|coaxial"),
    ("光沢のある金属 傷 照明の当て方", r"illumin|lighting|solid_angle|defect_contrast|coaxial"),
    ("透明な瓶の中の液面の高さを測りたい", r"bottle|fill_level|liquid|container"),
    ("印刷のかすれを見つけたい", r"print|grade_|char|ocr"),
    ("ムラのある背景から小さな欠陥を見つけたい", r"background|rolling_ball|tophat|bothat|adaptive|sauvola|niblack"),
    ("サーモグラフィ 欠陥 深さ", r"therm|lockin"),
)


@pytest.mark.parametrize("query, want", _JA_QUERIES)
def test_japanese_requests_find_the_operators_they_ask_for(cat, store, query, want):
    """直す前: 「見つけたい」の「見つ」「つけ」が「見つける」を含む要約(QR・PIV の外れ値 …)に当たり、照明・液面・
    サーモグラフィの op は英語に直さないと当たらなかった(サーモグラフィの「グラ」「ラフ」はホモグラフィに当たった)。"""
    import re
    ops = S.call_tool("fullseye_find_ops", {"query": query}, cat, store)["structuredContent"]["ops"]
    top5 = [o["name"] for o in ops[:5]]
    assert len(top5) == 5
    assert [n for n in top5 if re.search(want, n)], (query, top5)


def test_request_phrasing_is_not_a_search_term_and_katakana_is_not_split():
    from fullseye.opsearch import _ja_query
    body, bridged, drop = _ja_query("印刷のかすれを見つけたい")
    assert "見つけ" not in body and "print" in bridged
    _body, bridged, drop = _ja_query("サーモグラフィ 欠陥 深さ")
    assert {"thermo", "lockin"} <= set(bridged) and "グラ" in drop and "ラフ" in drop
    assert _ja_query("edge detection") == ("edge detection", [], set())


# --------------------------------------------------------------------------- 13: list_samples の来歴
def test_list_samples_says_what_each_sample_shows_its_source_and_licence(cat, store):
    """直す前: list_samples は名前だけで、来歴・ライセンス・何が写っているか・真値があるかが分からなかった。"""
    r = S.call_tool("fullseye_list_samples", {}, cat, store)
    sc = r["structuredContent"]
    details = {d["name"]: d for d in sc["sample_details"]}
    assert len(details) >= 10 and set(details) == set(sc["samples"])
    assert all(d["source"] and d["licence"] for d in details.values())
    weld = details["weld_xray_porosity"]
    assert weld["has_truth"] is True and "weld" in weld["what"].lower()
    assert "- weld_xray_porosity:" in _text(r) and "真値あり" in _text(r)
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assert root not in json.dumps(r, ensure_ascii=False)


# --------------------------------------------------------------------------- C: 判定 ok の意味
_SCRATCH_PIPELINES = (                                  # 同じ傷の画像に、別々の 4 通りの「長さ」
    [{"op": "invert"}, {"op": "otsu"}, {"op": "count_obj"}],
    [{"op": "gaussian", "a": 0.1}, {"op": "sk_rolling_ball", "a": 0.2}, {"op": "threshold", "a": 0.12},
     {"op": "select_shape", "a": 0.0}, {"op": "select_largest"}, {"op": "diameter_region"}],
    [{"op": "otsu"}, {"op": "distance_transform"}, {"op": "sobel_amp"}, {"op": "otsu"}, {"op": "diameter_region"}],
    [{"op": "invert"}, {"op": "otsu"}, {"op": "diameter_region"}],
)


def test_ok_says_it_only_checked_the_shape_and_flags_obvious_anomalies(cat, store):
    """直す前: 同じ画像に 4 通りの処理で 1.0 / 46.3 / 75.0 / 1285.0 が全部 判定=ok で返り、ok が「値が正しい」と
    読まれた。otsu → distance_transform → sobel_amp → otsu → diameter_region = 803.2(対角 804.6 px とほぼ同じ)も ok。
    判定は形だけを見る事を本文で言い、明らかな異常(対角とほぼ同じ長さ・入力を読まない段)に注意を付ける。"""
    h = S.call_tool("fullseye_load_image", {"path": "metal_hairline_scratch"}, cat, store)["structuredContent"]["handle"]
    values, cautions = [], []
    for stages in _SCRATCH_PIPELINES:
        r = S.call_tool("fullseye_pipeline", {"handle": h, "stages": stages, "vision": "none"}, cat, store)
        sc = r["structuredContent"]
        assert not r["isError"] and "判定=ok" in _text(r)
        assert "値の正しさではない" in _text(r) and sc["verdict_scope"] == "shape_only"
        values.append(round(float(sc["value"]), 1))
        cautions.append(sc.get("cautions", []))
    assert len(set(values)) == 4 and values[0] == 1.0 and values[1] == 46.3, values
    assert [bool(c) for c in cautions] == [False, False, False, True], cautions
    assert "画像の対角" in cautions[3][0]
    plate = S.call_tool("fullseye_load_image", {"path": "machined_plate_holes"}, cat, store)["structuredContent"]["handle"]
    r = S.call_tool("fullseye_pipeline", {"handle": plate, "stages": _SCRATCH_PIPELINES[2], "vision": "none"}, cat, store)
    assert round(r["structuredContent"]["value"], 1) == 803.2 and "画像の対角 804.5 px" in _text(r)
    blind = S.call_tool("fullseye_pipeline", {"handle": h, "stages": [
        {"op": "gaussian"}, {"op": "sobel_amp"}, {"op": "hx_gen_empty_region"}, {"op": "count_obj"}],
        "vision": "none"}, cat, store)
    assert "段 3 hx_gen_empty_region は入力の中身を読まない op" in _text(blind)


def test_largest_component_note_is_only_shown_when_other_components_were_left_out(cat, store):
    """再現の続き(2026-11-13): select_largest の後の diameter_region に「成分 1 個のうち最大の 1 つ」と出ていた。"""
    h = S.call_tool("fullseye_load_image", {"path": "metal_hairline_scratch"}, cat, store)["structuredContent"]["handle"]
    r = S.call_tool("fullseye_pipeline", {"handle": h, "stages": [{"op": "otsu"}, {"op": "select_largest"},
                                                                 {"op": "diameter_region"}], "vision": "none"}, cat, store)
    rec = r["structuredContent"]["stages"][-1]
    assert rec["measured"]["components_in_input"] == 1 and "最大の 1 つだけ" not in _text(r)
