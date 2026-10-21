from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import gen_doc_counts as G  # noqa: E402
import i18n_docs as I  # noqa: E402


def test_numeric_only_comparison_ignores_stamps_and_localized_numbers():
    before = "<!-- i18n-source-sha: 0123456789ab -->\nnotes **3.496** / 939\n"
    after = "<!-- i18n-source-sha: fedcba987654 -->\nnotes **3,535** / 940\n"
    assert I._without_stamp_and_numbers(before) == I._without_stamp_and_numbers(after)
    assert I._without_stamp_and_numbers(before) != I._without_stamp_and_numbers(after + "word")


def test_replacement_is_narrow_and_requires_exactly_one_match(tmp_path):
    path = tmp_path / "guide.md"
    path.write_text("x **3,496 notes** y 2026\n", encoding="utf-8")
    G._replace_one(path, r"\*\*\d{1,3}(?:[,.]\d{3})+\s*(?=notes)", "**3,535 ")
    assert path.read_text(encoding="utf-8") == "x **3,535 notes** y 2026\n"
    with pytest.raises(RuntimeError):
        G._replace_one(path, r"never", "x")


def test_generate_repairs_stale_counts_and_is_idempotent(tmp_path, monkeypatch):
    (tmp_path / "README.md").write_text(
        "intro **939** registry\n---\ngenerated **939** stays owned elsewhere\n", encoding="utf-8")
    (tmp_path / "AI_RAG_GUIDE.md").write_text("ノート **3,496 枚**\n", encoding="utf-8")
    (tmp_path / "AI_RAG_GUIDE.en.md").write_text("**3,496 notes**\n", encoding="utf-8")
    (tmp_path / "AI_RAG_GUIDE.de.md").write_text("**3.496 Notizen**\n", encoding="utf-8")
    stamped = []
    monkeypatch.setattr(G, "DOCS", tmp_path)
    monkeypatch.setattr(G, "counts", lambda: (940, 3535))
    monkeypatch.setattr(G.i18n_docs, "stamp_if_numeric_only", stamped.append)

    G.generate()
    once = {p.name: p.read_text(encoding="utf-8") for p in tmp_path.glob("*.md")}
    G.generate()
    twice = {p.name: p.read_text(encoding="utf-8") for p in tmp_path.glob("*.md")}

    assert once == twice
    assert once["README.md"] == "intro **940** registry\n---\ngenerated **939** stays owned elsewhere\n"
    assert "3,535 枚" in once["AI_RAG_GUIDE.md"]
    assert "3,535 notes" in once["AI_RAG_GUIDE.en.md"]
    assert "3.535 Notizen" in once["AI_RAG_GUIDE.de.md"]
    assert len(stamped) == 4


def test_regen_all_owns_the_count_outputs():
    import regen_all

    assert any(cmd[0] == "tools/gen_doc_counts.py" for cmd, _ in regen_all.CHAIN)
    assert regen_all.OUTPUTS["tools/gen_doc_counts.py"] == [
        "docs/README.md", "docs/README.*.md",
        "docs/AI_RAG_GUIDE.md", "docs/AI_RAG_GUIDE.*.md",
    ]
