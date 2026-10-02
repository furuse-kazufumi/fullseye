"""``fullseye.mcp.catalog.scan_notes`` の並びが OS の区切り文字に依らないこと(2026-10-02 の回帰)。

素の ``sorted()`` で全パスを並べていたため、Windows(``\`` = 0x5C)と Linux(``/`` = 0x2F)で
``segmentation/watershed/`` と ``segmentation/watershed3d/`` の前後が入れ替わり、生成物
``fullseye/data/OP_NOTES.json`` の鍵の順が OS ごとに違った(手元の regen は緑、CI の ``regen_all --check`` が赤)。
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fullseye.mcp import catalog  # noqa: E402


def _write(root: Path, rel: str, op: str):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("---\nop: %s\ndim: segmentation\n---\n本文\n" % op, encoding="utf-8")


def test_note_order_follows_the_posix_path(tmp_path):
    ops = tmp_path / "docs" / "ops"
    _write(ops, "segmentation/watershed3d/b_op.md", "b_op")
    _write(ops, "segmentation/watershed/a_op.md", "a_op")
    _write(ops, "segmentation/watershed_x/c_op.md", "c_op")
    got = list(catalog.scan_notes(str(ops)))
    # POSIX の並び: "watershed/" < "watershed3d/" < "watershed_x/"("/" 0x2F < "3" 0x33 < "_" 0x5F)
    assert got == ["a_op", "b_op", "c_op"]


def test_the_shipped_notes_are_in_posix_path_order():
    notes = catalog.scan_notes()
    paths = [m["path"] for metas in notes.values() for m in metas]
    assert len(paths) > 2000
    first_seen = []
    for metas in notes.values():
        first_seen.append(metas[0]["path"])
    assert first_seen == sorted(first_seen)
