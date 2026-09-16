# Copyright (c) 2026 Kazufumi Furuse. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""sample_data fail-closed regressions (offline: the opener is monkeypatched).

* the decompressed size of an archive member is capped (``MAX_EXTRACT_BYTES``);
* an archive entry without ``sha256_out`` is rejected by the manifest check,
  never counts as verified, and its download is refused.
"""
import hashlib
import io
import os
import tarfile

import pytest

import sample_data as SD


def _tar_gz_bytes(member: str, data: bytes) -> bytes:
    bio = io.BytesIO()
    with tarfile.open(fileobj=bio, mode="w:gz") as tf:
        ti = tarfile.TarInfo(member)
        ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))
    return bio.getvalue()


class _Resp:
    def __init__(self, payload: bytes):
        self._b = io.BytesIO(payload)

    def read(self, n):
        return self._b.read(n)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener_for(payload: bytes):
    def opener(req):
        return _Resp(payload)
    return opener


def _install(monkeypatch, tmp_path, entry: dict):
    monkeypatch.setenv("FULLSEYE_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(SD, "MANIFEST", SD.MANIFEST + [entry])
    monkeypatch.setattr(SD, "_BY_ID", {**SD._BY_ID, entry["id"]: entry})


def _entry(payload: bytes, data: bytes, **override) -> dict:
    e = dict(
        id="t-archive", name="test archive", category="mesh", fmt="ply",
        url="https://example.invalid/t.tar.gz", archive="tar.gz",
        member="t/inner.ply", dest="t_inner.ply",
        sha256=hashlib.sha256(payload).hexdigest(),
        sha256_out=hashlib.sha256(data).hexdigest(),
        bytes=len(payload), license="test", commercial="yes", access="direct",
        source_page="https://example.invalid/", attribution="", doc="",
    )
    e.update(override)
    return e


def test_tar_member_extracts_and_verifies(monkeypatch, tmp_path):
    data = b"ply\n" + b"x" * 5000
    payload = _tar_gz_bytes("t/inner.ply", data)
    _install(monkeypatch, tmp_path, _entry(payload, data))
    p = SD.download("t-archive", yes=True, quiet=True, _opener=_opener_for(payload))
    assert os.path.exists(p) and open(p, "rb").read() == data
    assert SD.verify("t-archive") is True


def test_decompressed_size_is_capped(monkeypatch, tmp_path):
    """A tiny .tar.gz that inflates past MAX_EXTRACT_BYTES is refused and
    leaves nothing behind (no .part, no target)."""
    data = b"\0" * 200_000                                    # compresses to ~ nothing
    payload = _tar_gz_bytes("t/inner.ply", data)
    assert len(payload) < 2000
    _install(monkeypatch, tmp_path, _entry(payload, data))
    monkeypatch.setattr(SD, "MAX_EXTRACT_BYTES", 50_000)
    with pytest.raises(ValueError, match="MAX_EXTRACT_BYTES"):
        SD.download("t-archive", yes=True, quiet=True, _opener=_opener_for(payload))
    target = os.path.join(SD.data_dir(), "t_inner.ply")
    assert not os.path.exists(target) and not os.path.exists(target + ".part")
    assert SD.verify("t-archive") is False


def test_extract_cap_is_multiple_of_transfer_cap():
    assert SD.MAX_EXTRACT_BYTES >= SD._MAX_BYTES


def test_archive_entry_without_sha256_out_is_fail_closed(monkeypatch, tmp_path):
    data = b"ply\n" + b"y" * 100
    payload = _tar_gz_bytes("t/inner.ply", data)
    e = _entry(payload, data, sha256_out=None)
    _install(monkeypatch, tmp_path, e)
    # 1. the shipped-manifest validator refuses such an entry
    with pytest.raises(ValueError, match="sha256_out"):
        SD._validate_manifest()
    # 2. a file that merely exists is NOT "verified"
    target = os.path.join(SD.data_dir(), "t_inner.ply")
    os.makedirs(SD.data_dir(), exist_ok=True)
    with open(target, "wb") as w:
        w.write(data)
    assert SD.verify("t-archive") is False
    os.remove(target)
    # 3. downloading it is refused and the extracted file is removed
    with pytest.raises(ValueError, match="sha256_out"):
        SD.download("t-archive", yes=True, quiet=True, _opener=_opener_for(payload))
    assert not os.path.exists(target)


def test_shipped_manifest_pins_sha256_out_on_every_archive_entry():
    for e in SD.MANIFEST:
        if e["archive"] is not None:
            assert e.get("sha256_out"), e["id"]


# --------------------------------------------------------------------------- #
# 利用条件の台帳(ライセンス / 商用 / アクセス)
#
# ★台帳は前からあったのに、**人が読む `docs/ops/SAMPLES.md` には出ていなかった**
#   (2026-09-16)。表の列は id / 種別 / アクセス / URL だけで、ライセンスと商用可否は
#   ソースを読まないと分からなかった —— 看板(「DL URL / ライセンス」)と中身がずれて
#   いた。出す側を直したので、ここでは**台帳が空欄を作らないこと**を固定する。
# --------------------------------------------------------------------------- #

_REQUIRED_TERMS = ("license", "commercial", "access", "source_page", "attribution")
_COMMERCIAL = {"yes", "no", "check"}
_ACCESS = {"direct", "info", "gated"}


def test_every_manifest_entry_carries_its_terms():
    """全行に利用条件が入っていること。

    空欄は「制限なし」ではなく「**調べていない**」。消費側(SAMPLES.md の表)は
    二つを区別できないので、**空欄を作らせない側**で守る。``check`` という
    「未確認」を表す明示的な値を持たせてあるのはそのため。
    """
    bad = []
    for e in SD.catalog():
        for key in _REQUIRED_TERMS:
            if not str(e.get(key) or "").strip():
                bad.append("%s: %s が空" % (e.get("id"), key))
        if e.get("commercial") not in _COMMERCIAL:
            bad.append("%s: commercial=%r(%s のいずれか)"
                       % (e.get("id"), e.get("commercial"), sorted(_COMMERCIAL)))
        if e.get("access") not in _ACCESS:
            bad.append("%s: access=%r(%s のいずれか)"
                       % (e.get("id"), e.get("access"), sorted(_ACCESS)))
    assert not bad, "sample_data の台帳に穴がある: " + "; ".join(bad)


def test_non_commercial_sources_are_never_auto_downloaded():
    """商用不可と分かっている源は ``access='direct'`` にしない。

    ``direct`` は「``download()`` が黙って取ってくる」という意味。条件が厳しいと
    **分かっている**源をその経路に置くと、利用者が規約を読む機会が一度も無いまま
    手元に落ちる。``check``(未確認)+ ``direct`` は許す —— 手元で使う分には
    問題が出にくく、危ないのは成果を外に出すほうなので、そちらは次の門で見る。
    """
    bad = [e["id"] for e in SD.catalog()
           if e.get("commercial") == "no" and e.get("access") == "direct"]
    assert not bad, ("商用不可の源が自動 DL 経路に居る: %s —— access を "
                     "'info' か 'gated' にすること" % bad)


# --------------------------------------------------------------------------- #
# 成果物の門(事故の起きる場所に立てる)
# --------------------------------------------------------------------------- #

#: 図を repo に書き出す呼び出し。
_WRITES_FIGURE = __import__("re").compile(r"\b(savefig|imsave|imwrite)\s*\(")

_SCANNED_DIRS = ("examples", "examples_3d", "examples_oned", "tools")


def _restricted_ids():
    return {e["id"] for e in SD.catalog() if e.get("commercial") != "yes"}


def _figure_from_restricted_source(text, ids):
    """``text`` が制限つきの源を参照し、かつ図を書き出しているなら、その id を返す。"""
    used = sorted(i for i in ids if '"%s"' % i in text or "'%s'" % i in text)
    return used if used and _WRITES_FIGURE.search(text) else []


def test_no_committed_figure_is_made_from_a_restricted_source():
    """商用可と確認できていない源から作った図を repo に置かないこと。

    ★いまは違反ゼロだが、**それは偶然ではなく設計**: 該当する 3 本
    (``examples_3d/dl_mesh_*``, ``mesh_lod_download``)は ``local_path()`` が
    ``None`` なら黙って飛ぶので、CI では図が出ない。だが ``savefig`` を 1 行
    足した瞬間に成立しなくなる —— **門は事故の起きる場所に立てる**ので、
    「いま通っているから要らない」ではなくここに置く。
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ids = _restricted_ids()
    assert ids, "制限つきの源がゼロ —— 台帳の読み取りが壊れている"
    bad = []
    for sub in _SCANNED_DIRS:
        d = os.path.join(root, sub)
        if not os.path.isdir(d):
            continue
        for dirpath, dirnames, filenames in os.walk(d):
            dirnames[:] = sorted(x for x in dirnames if x != "__pycache__")
            for fn in sorted(filenames):
                if not fn.endswith(".py"):
                    continue
                p = os.path.join(dirpath, fn)
                with open(p, encoding="utf-8") as fh:
                    used = _figure_from_restricted_source(fh.read(), ids)
                if used:
                    bad.append("%s(%s)" % (os.path.relpath(p, root), ", ".join(used)))
    assert not bad, ("商用可と確認できていない源から図を書き出している: %s —— "
                     "成果を repo に残さない(out/ へ出す)か、条件を確認して "
                     "commercial='yes' にすること" % "; ".join(bad))


def test_the_restricted_source_gate_would_catch_a_violation():
    """上の門を壊して、ちゃんと捕まることを確かめる。

    検出器を書いたが一度も鳴らしたことがない、という門を増やさないため。
    """
    ids = _restricted_ids()
    victim = sorted(ids)[0]
    decoy = ('p = sample_data.local_path("%s")\n'
             'plt.savefig("docs/x.png")\n' % victim)
    assert _figure_from_restricted_source(decoy, ids) == [victim]
    # 逆に、図を書かなければ捕まらない(いまの 3 本がこちら)
    assert _figure_from_restricted_source(
        'p = sample_data.local_path("%s")\n' % victim, ids) == []
