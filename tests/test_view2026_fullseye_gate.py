"""ViEW2026 の Fullseye 使用門と ja/en のページ分割を守る。"""
from __future__ import annotations

import copy
import importlib.util
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "docs" / "view2026"

_gen_spec = importlib.util.spec_from_file_location("gen_view2026_pages_gate", ROOT / "tools" / "gen_view2026_pages.py")
G = importlib.util.module_from_spec(_gen_spec)
_gen_spec.loader.exec_module(G)

_gate_spec = importlib.util.spec_from_file_location("view2026_fullseye_gate_test", ROOT / "tools" / "view2026_fullseye_gate.py")
F = importlib.util.module_from_spec(_gate_spec)
import sys
sys.modules[_gate_spec.name] = F
_gate_spec.loader.exec_module(F)


def test_gate_counts_all_four_supported_call_forms(tmp_path) -> None:
    source = tmp_path / "calls.py"
    source.write_text(
        "import fullseye as fs\n"
        "import fringe\n"
        "from fullseye import blob_label as label\n"
        "fs.threshold_binary(x, 1)\n"              # (a), (b)
        "fs.some_future_compute(x)\n"              # (b)
        "fs.apply(x, 'sk_lbp')\n"                  # (c)
        "fringe.wrapped_phase(x)\n"                # (d)
        "label(x)\n",                              # (a), direct import
        encoding="utf-8",
    )
    calls = F.count_calls(source)
    assert len(calls) == 5
    assert any("apply:sk_lbp" in call for call in calls)
    assert any("module:fringe.wrapped_phase" in call for call in calls)


def test_non_compute_exclusions_have_reasons_and_do_not_open_the_gate(tmp_path) -> None:
    assert {"ledger", "op_find", "op_search", "write_viewer", "apply"} <= set(F.NON_COMPUTE_FS_CALLS)
    assert all(reason.strip() for reason in F.NON_COMPUTE_FS_CALLS.values())
    assert all(reason.strip() for reason in F.NON_COMPUTE_MODULES.values())
    source = tmp_path / "no_compute.py"
    source.write_text(
        "import fullseye as fs\nimport examplefig as figs\n"
        "fs.op_find('edge')\nfs.op_search('edge')\nfs.write_viewer('x')\n"
        "fs.apply(x, dynamic_name)\nfigs.save_grid([], 'x.png')\n",
        encoding="utf-8",
    )
    assert F.count_calls(source) == ()


def test_fake_exhibit_without_fullseye_is_dropped_by_the_real_generator() -> None:
    broken = copy.deepcopy(G.load())
    fake_id = "fake_without_fullseye"
    fake = copy.deepcopy(broken["exhibits"][0])
    fake.update(id=fake_id, tier="more", source_url="")
    broken["exhibits"].append(fake)
    fake_all = copy.deepcopy(broken["all"][0])
    fake_all.update(id=fake_id, source_url="")
    broken["all"].append(fake_all)
    assert G.gate_results(broken)[fake_id].count == 0
    assert fake_id not in G.build_more(broken, "ja")


def test_main_and_more_are_an_exact_disjoint_partition() -> None:
    data = G.load()
    public = G.public_data(data)
    main_expected = {item["id"] for item in public["exhibits"]
                     if item["tier"] in ("showcase", "featured")}
    all_allowed = {item["id"] for item in public["all"]}
    more_expected = all_allowed - main_expected
    assert len({item["id"] for item in public["exhibits"] if item["tier"] == "showcase"}) == 14
    assert len({item["id"] for item in public["exhibits"] if item["tier"] == "featured"}) == 6

    for lang in ("ja", "en"):
        main = G.build(data, lang)
        more = G.build_more(data, lang)
        main_ids = set(re.findall(r"thumbs/(poc_[A-Za-z0-9_]+)\.jpg", main))
        more_ids = set(re.findall(r"thumbs/all/([A-Za-z0-9_-]+)\.jpg", more))
        assert main_ids == main_expected
        assert more_ids == more_expected
        assert not (main_ids & more_ids)
        assert main_ids | more_ids == all_allowed


def test_withdrawn_and_gate_failures_are_on_neither_page() -> None:
    data = G.load()
    excluded = F.withdrawn_ids()
    excluded.update(item_id for item_id, result in G.gate_results(data).items() if result.count == 0)
    for lang in ("ja", "en"):
        main_ids = set(re.findall(r"thumbs/(poc_[A-Za-z0-9_]+)\.jpg", G.build(data, lang)))
        more_ids = set(re.findall(r"thumbs/all/([A-Za-z0-9_-]+)\.jpg", G.build_more(data, lang)))
        assert not (excluded & (main_ids | more_ids))


def test_field_viewers_exist_and_do_not_reuse_withdrawn_ids() -> None:
    data = G.load()
    items = data["field_viewers"]["items"]
    assert len(items) == 3
    assert not ({item["id"] for item in items} & F.withdrawn_ids())
    assert all((VIEW / item["path"]).is_file() for item in items)
    for lang in ("ja", "en"):
        page = G.build(data, lang)
        positions = [page.index(item["path"] + "?lang=" + lang) for item in items]
        assert positions == sorted(positions)


def test_field_viewer_garbled_text_stops_generation() -> None:
    broken = copy.deepcopy(G.load())
    broken["field_viewers"]["items"][0]["title"]["ja"] = "???"
    bad = G.validate(broken)
    assert bad, "文字化けした題を入れても validate が 0 件では門になっていない"
    assert any("field_viewers" in message and "文字化け" in message for message in bad)


def _relative_targets(text: str) -> set[str]:
    markdown = re.findall(r"!?\[[^\]\n]*\]\(([^)\s]+)\)", text)
    html = re.findall(r"(?:href|src|data-src)=\"([^\"]+)\"", text)
    return {target for target in markdown + html
            if not target.startswith(("http://", "https://", "data:", "#"))
            and Path(urlsplit(target).path).suffix}


def _assert_links_exist(path: Path, text: str) -> None:
    missing = []
    for target in sorted(_relative_targets(text)):
        clean = unquote(urlsplit(target).path)
        if not clean:
            continue
        resolved = (path.parent / clean).resolve()
        if resolved.is_file():
            continue
        # Jekyll が .md から作る .html を指す既存リンクも、正本の実在で確認する。
        markdown_source = resolved.with_suffix(".md") if resolved.suffix == ".html" else None
        if markdown_source is None or not markdown_source.is_file():
            missing.append(target)
    assert not missing, "%s: missing %s" % (path.relative_to(ROOT), missing)


def test_main_pages_are_much_shorter_and_all_new_relative_links_exist() -> None:
    data = G.load()
    assert len(G.build(data, "ja").splitlines()) < 800  # 変更前は 1,605 行
    for lang in ("ja", "en"):
        _assert_links_exist(G.page_path(lang), G.build(data, lang))
        _assert_links_exist(G.more_page_path(lang), G.build_more(data, lang))
