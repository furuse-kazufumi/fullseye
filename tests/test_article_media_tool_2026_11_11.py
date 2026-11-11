"""tools/article_media.py(記事の素材を素材 repo に置き、原稿の raw URL を検める道具)のテスト(2026-11-11)。

tmp_path に偽の clone(``git init`` した repo)を作り、``FULLSEYE_MEDIA_ROOT`` をそこへ向けて試す。
実物の clone にもネットワークにも触らない(``--http`` は ``_http_status`` を差し替えて試す)。
"""
import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "article_media.py")
_spec = importlib.util.spec_from_file_location("article_media", TOOL)
am = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(am)

REPO = am.CURRENT
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"}


def _git(root, *args):
    env = dict(os.environ, **GIT_ENV)
    subprocess.run(["git", "-C", str(root), "-c", "core.autocrlf=false", "-c", "commit.gpgsign=false",
                    "-c", "core.hooksPath=", *args], check=True, capture_output=True, env=env)


@pytest.fixture(autouse=True)
def _never_touch_real_clone(tmp_path_factory, monkeypatch):
    """FULLSEYE_MEDIA_ROOT を立て忘れたテストが、実物の clone(repo の隣)に触らないようにする。"""
    monkeypatch.setenv(am.ENV_ROOT, str(tmp_path_factory.mktemp("no-clone-here") / "absent"))


@pytest.fixture
def media(tmp_path, monkeypatch):
    """偽の clone(``<tmp>/media/<CURRENT>``)を作り、環境変数を向ける。clone の根を返す。"""
    parent = tmp_path / "media"
    root = parent / REPO
    root.mkdir(parents=True)
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True, capture_output=True)
    _git(root, "init", "-q", "-b", "main")
    (root / "README.md").write_text("x\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "-q", "-m", "init")
    _git(root, "remote", "add", "origin", str(origin))
    _git(root, "push", "-q", "-u", "origin", "main")
    monkeypatch.setenv(am.ENV_ROOT, str(parent))
    return root


def _src(tmp_path, name="fig.png", data=b"\x89PNG-fake-1"):
    p = tmp_path / "src" / name
    p.parent.mkdir(exist_ok=True)
    p.write_bytes(data)
    return p


def _commit(root, rel, push=True):
    """add・commit し、既定では origin/main へ push する(push=False なら commit まで)。"""
    _git(root, "add", rel)
    _git(root, "commit", "-q", "-m", "add " + rel)
    if push:
        _git(root, "push", "-q", "origin", "main")


# ---------------------------------------------------------------- put

def test_put_new_copies_and_returns_url(media, tmp_path):
    url = am.put(_src(tmp_path), "my-article")
    assert url == am.MEDIA_REPOS[REPO]["raw_base"] + "my-article/fig.png"
    assert (media / "my-article" / "fig.png").read_bytes() == b"\x89PNG-fake-1"
    # git の操作はしない: 写しただけで、HEAD には無い
    assert am.committed_blob(media, "my-article/fig.png") is None


def test_put_is_idempotent_for_same_content(media, tmp_path):
    src = _src(tmp_path)
    u1 = am.put(src, "my-article")
    mtime = (media / "my-article" / "fig.png").stat().st_mtime_ns
    u2 = am.put(src, "my-article")
    assert u1 == u2
    assert (media / "my-article" / "fig.png").stat().st_mtime_ns == mtime


def test_put_refuses_different_content_and_keeps_old(media, tmp_path):
    am.put(_src(tmp_path, data=b"old"), "my-article")
    with pytest.raises(am.MediaRefused, match="新しい名前"):
        am.put(_src(tmp_path, data=b"new"), "my-article")
    assert (media / "my-article" / "fig.png").read_bytes() == b"old"
    # 新しい名前なら足せる
    url = am.put(_src(tmp_path, data=b"new"), "my-article", name="fig-v2.png")
    assert url.endswith("/my-article/fig-v2.png")


@pytest.mark.parametrize("article", ["..", "a/b", "a\\b", "My-Article", "", "-lead", "a_b", "a.b",
                                     "a.", "a ", "a\n", "con", "nul", "aux", "prn", "com1", "lpt9", "x" * 65])
def test_put_refuses_bad_article_names(media, tmp_path, article):
    with pytest.raises(am.MediaRefused):
        am.put(_src(tmp_path), article)
    assert sorted(p.name for p in media.iterdir()) == [".git", "README.md"]


@pytest.mark.parametrize("name", ["..", "../x.png", "a/b.png", "a\\b.png", "Fig.png", "", "a..png", ".hidden",
                                  "fig.png.", "fig.png ", "fig.png\n", "fig.", "con.png", "nul", "aux.v2.png",
                                  "com1.gif", "lpt3.png", "a" * 101])
def test_put_refuses_bad_file_names(media, tmp_path, name):
    with pytest.raises(am.MediaRefused):
        am.put(_src(tmp_path), "my-article", name=name)
    assert not (media / "my-article").exists()


def test_put_refuses_uppercase_src_name_unless_renamed(media, tmp_path):
    src = _src(tmp_path, name="Fig.PNG")
    with pytest.raises(am.MediaRefused):
        am.put(src, "my-article")
    assert am.put(src, "my-article", name="fig.png").endswith("/fig.png")


def test_put_size_limits(media, tmp_path):
    lim = am.size_limits()
    ok = _src(tmp_path, name="ok.gif", data=b"G" * lim["gif"])
    assert am.put(ok, "my-article")
    big = _src(tmp_path, name="big.gif", data=b"G" * (lim["gif"] + 1))
    with pytest.raises(am.MediaRefused, match="上限"):
        am.put(big, "my-article")
    # 同じ大きさでも PNG の上限の内なら通る(GIF だけ 3 MB)
    assert am.put(big, "my-article", name="big.png")
    bigpng = _src(tmp_path, name="huge.png", data=b"P" * (lim["png"] + 1))
    with pytest.raises(am.MediaRefused, match="上限"):
        am.put(bigpng, "my-article")
    assert not (media / "my-article" / "big.gif").exists()
    assert not (media / "my-article" / "huge.png").exists()


def test_put_refuses_empty_and_missing_src(media, tmp_path):
    with pytest.raises(am.MediaRefused):
        am.put(_src(tmp_path, data=b""), "my-article")
    with pytest.raises(am.MediaEnvError):
        am.put(tmp_path / "nope.png", "my-article")


def test_size_limits_match_check_exhibit_assets():
    """ast で読んだ値が、check_exhibit_assets を import した値と同じ(基準を二重に持たない)。"""
    spec = importlib.util.spec_from_file_location("cea", os.path.join(ROOT, "tools", "check_exhibit_assets.py"))
    cea = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cea)
    assert am.size_limits() == {"gif": cea.MAX_GIF_BYTES, "png": cea.MAX_PNG_BYTES}
    assert am.size_limits() == {"gif": 3 * 1024 * 1024, "png": 6 * 1024 * 1024}


def test_local_root_missing_clone_names_env(tmp_path, monkeypatch):
    monkeypatch.setenv(am.ENV_ROOT, str(tmp_path / "nowhere"))
    with pytest.raises(am.MediaEnvError, match=am.ENV_ROOT):
        am.local_root()


# ---------------------------------------------------------------- parse / raw_url

def test_raw_url_parse_roundtrip():
    url = am.raw_url("my-article", "fig_1.v2.png")
    assert am.parse_raw_url(url) == (REPO, "my-article", "fig_1.v2.png")


def test_parse_drops_query_and_fragment():
    url = am.raw_url("my-article", "fig.png")
    assert am.parse_raw_url(url + "?v=3") == (REPO, "my-article", "fig.png")
    assert am.parse_raw_url(url + "?v=3#top") == (REPO, "my-article", "fig.png")


def test_parse_rejects_unknown_repo_and_fullseye_and_bad_shape():
    base = am.RAW_HOST + am.OWNER + "/"
    assert am.parse_raw_url(base + "fullseye-media2099q1/main/a/b.png") is None
    assert am.parse_raw_url(base + "fullseye/master/docs/articles/assets/x.png") is None
    assert am.parse_raw_url(base + REPO + "/master/a/b.png") is None  # 枝が違う
    assert am.parse_raw_url(base + REPO + "/main/b.png") is None  # 記事の名前が無い
    assert am.parse_raw_url(base + REPO + "/main/a/sub/b.png") is None  # 深すぎる
    assert am.parse_raw_url(base + REPO + "/main/A/b.png") is None
    assert am.parse_raw_url("https://example.com/x.png") is None
    with pytest.raises(am.MediaEnvError):
        am.raw_url("a", "b.png", repo="fullseye-media2099q1")


# ---------------------------------------------------------------- check

def _md(*urls):
    return "\n".join(f"![x]({u})" for u in urls) + "\n"


def test_check_committed_passes(media, tmp_path):
    url = am.put(_src(tmp_path), "my-article")
    _commit(media, "my-article/fig.png")
    assert am.check_text(_md(url + "?v=2")) == []


def test_check_uncommitted_fails(media, tmp_path):
    url = am.put(_src(tmp_path), "my-article")
    probs = am.check_text(_md(url))
    assert [p["kind"] for p in probs] == ["uncommitted"]


def test_check_missing_fails(media):
    url = am.raw_url("my-article", "ghost.png")
    assert [p["kind"] for p in am.check_text(_md(url))] == ["missing"]


def test_check_modified_after_commit_fails(media, tmp_path):
    url = am.put(_src(tmp_path), "my-article")
    _commit(media, "my-article/fig.png")
    (media / "my-article" / "fig.png").write_bytes(b"changed")
    assert [p["kind"] for p in am.check_text(_md(url))] == ["modified"]


def test_check_shape_and_repo_errors(media):
    base = am.RAW_HOST + am.OWNER + "/"
    text = _md(base + REPO + "/main/fig.png",
               base + REPO + "/main/a/b/c.png",
               base + REPO + "/master/a/b.png",
               base + "fullseye-media2099q1/main/a/b.png")
    kinds = [p["kind"] for p in am.check_text(text)]
    assert kinds == ["bad_shape", "bad_shape", "wrong_branch", "unknown_repo"]


def test_check_zero_urls_reports_count(media, tmp_path, capsys):
    md = tmp_path / "a.md"
    md.write_text("![x](https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/docs/articles/assets/x.png)\n",
                  encoding="utf-8")
    assert am.check_text(md.read_text(encoding="utf-8")) == []
    assert am.main(["check", str(md)]) == 0
    out = capsys.readouterr().out
    assert "素材 repo の raw URL: 0 本" in out and "合格ではなく" in out
    assert "本体(fullseye)の raw URL: 1 本(対象外)" in out
    assert am.main(["check", str(md), "--json"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["media_urls"] == 0 and rep["fullseye_urls"] == 1 and rep["http_checked"] is False


def test_check_cli_exit_codes_and_json(media, tmp_path, capsys):
    good = am.put(_src(tmp_path), "my-article")
    _commit(media, "my-article/fig.png")
    bad = am.raw_url("my-article", "ghost.png")
    md = tmp_path / "a.md"
    md.write_text(_md(good, good, bad), encoding="utf-8")
    assert am.main(["check", str(md), "--json"]) == 1
    rep = json.loads(capsys.readouterr().out)
    assert rep["media_urls"] == 2 and [p["kind"] for p in rep["problems"]] == ["missing"]
    assert am.main(["check", str(tmp_path / "none.md")]) == 2
    capsys.readouterr()


def test_check_env_error_when_clone_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv(am.ENV_ROOT, str(tmp_path / "nowhere"))
    md = tmp_path / "a.md"
    md.write_text(_md(am.raw_url("my-article", "fig.png")), encoding="utf-8")
    assert am.main(["check", str(md)]) == 2
    assert am.ENV_ROOT in capsys.readouterr().out


def test_check_http_only_when_asked(media, tmp_path, monkeypatch):
    url = am.put(_src(tmp_path), "my-article")
    _commit(media, "my-article/fig.png")
    calls = []

    def fake(u, timeout=15.0):
        calls.append(u)
        return 404

    monkeypatch.setattr(am, "_http_status", fake)
    assert am.check_text(_md(url)) == [] and calls == []
    assert [p["kind"] for p in am.check_text(_md(url), http=True)] == ["http"]
    assert calls == [url]


def test_cli_put_and_url(media, tmp_path, capsys):
    src = _src(tmp_path)
    assert am.main(["put", str(src), "my-article", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["url"].endswith("/my-article/fig.png")
    assert am.main(["put", str(_src(tmp_path, data=b"other")), "my-article"]) == 1
    assert "拒否" in capsys.readouterr().out
    assert am.main(["url", "my-article", "fig.png"]) == 0
    assert capsys.readouterr().out.strip() == am.raw_url("my-article", "fig.png")
    assert am.main(["nope"]) == 2
    capsys.readouterr()


def test_cli_runs_as_script(tmp_path):
    """``py tools/article_media.py url ...`` で動く(stdlib だけ・ネットに触らない)。"""
    p = subprocess.run([sys.executable, TOOL, "url", "my-article", "fig.png"],
                       capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == am.raw_url("my-article", "fig.png")


# ---------------------------------------------------------------- 表の健全さ・stdlib・ローカルパス

def test_table_is_sound():
    assert am.CURRENT in am.MEDIA_REPOS
    for name, info in am.MEDIA_REPOS.items():
        assert re.fullmatch(r"fullseye-media20\d\dq[1-4]", name), name
        assert info["raw_base"] == f"https://raw.githubusercontent.com/{am.OWNER}/{name}/{info['branch']}/"


def test_tool_imports_only_stdlib():
    tree = ast.parse(open(TOOL, encoding="utf-8").read())
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0:
            mods.add(n.module.split(".")[0])
    std = set(sys.stdlib_module_names)
    assert mods <= std, mods - std


def test_no_local_paths_in_tool_and_test():
    drive = re.compile(r"(?<![A-Za-z])[A-Za-z]" + ":" + r"[\\/]")
    bad = ["/" + "c/", "App" + "Data", "/" + "Users/", "pur" + "uy"]
    for path in (TOOL, os.path.abspath(__file__)):
        text = open(path, encoding="utf-8").read()
        assert not drive.search(text), path
        for b in bad:
            assert b not in text, (path, b)


# ---------------------------------------------------------------- 2026-11-11 レビュー後の追加

def _kinds(probs):
    return [p["kind"] for p in probs]


def test_check_staged_but_uncommitted_fails(media, tmp_path):
    """F4: put の次の手は git add。stage しただけ(commit 前)は合格にしない。"""
    url = am.put(_src(tmp_path), "my-article")
    _git(media, "add", "my-article/fig.png")
    assert _kinds(am.check_text(_md(url))) == ["uncommitted"]


def test_check_committed_but_unpushed_fails(media, tmp_path):
    """F1: commit しただけで push していない。"""
    url = am.put(_src(tmp_path), "my-article")
    _commit(media, "my-article/fig.png", push=False)
    probs = am.check_text(_md(url))
    assert "unpushed" in _kinds(probs)
    # ファイルの URL そのものに対しても、HEAD でなく origin/main の木で照合した問題が付く
    assert [p["kind"] for p in probs if p["url"] == url] == ["unpushed"]
    assert all("fetch" in p["message"] for p in probs)  # 追跡枝が古いかもしれない、と書く


def test_check_wrong_local_branch_fails(media, tmp_path):
    """F1: 別の枝で commit(push は feature へ)。"""
    url = am.put(_src(tmp_path), "my-article")
    _git(media, "checkout", "-q", "-b", "feature")
    _commit(media, "my-article/fig.png", push=False)
    probs = am.check_text(_md(url))
    assert "wrong_local_branch" in _kinds(probs)
    assert "unpushed" in _kinds(probs) or "uncommitted" in _kinds(probs)


def test_check_detached_head_fails(media, tmp_path):
    url = am.put(_src(tmp_path), "my-article")
    _commit(media, "my-article/fig.png")
    _git(media, "checkout", "-q", "--detach")
    probs = am.check_text(_md(url))
    assert "wrong_local_branch" in _kinds(probs)
    assert "detached" in probs[0]["message"]


def test_check_no_remote_ref_fails(media, tmp_path):
    url = am.put(_src(tmp_path), "my-article")
    _commit(media, "my-article/fig.png", push=False)
    _git(media, "remote", "remove", "origin")
    assert _kinds(am.check_text(_md(url))) == ["no_remote_ref"]


def test_check_ahead_by_other_commit_fails(media, tmp_path):
    """F1: push 済みのファイルがあっても、手元が先行していれば問題として報告する。"""
    url = am.put(_src(tmp_path), "my-article")
    _commit(media, "my-article/fig.png")
    (media / "other.txt").write_text("o\n", encoding="utf-8")
    _commit(media, "other.txt", push=False)
    assert _kinds(am.check_text(_md(url))) == ["unpushed"]


@pytest.mark.parametrize("variant", [
    "http://raw.githubusercontent.com/furuse-kazufumi/{r}/main/a/b.png",
    "https://raw.githubusercontent.com/Furuse-Kazufumi/{r}/main/a/b.png",
    "https://raw.githubusercontent.com/furuse-kazufumi/Fullseye-Media2026q4/main/a/b.png",
    "https://RAW.githubusercontent.com/furuse-kazufumi/{r}/main/a/b.png",
    "https://raw.github.com/furuse-kazufumi/{r}/main/a/b.png",
    "https://github.com/furuse-kazufumi/{r}/raw/main/a/b.png",
    "https://github.com/furuse-kazufumi/{r}/blob/main/a/b.png",
    "https://cdn.jsdelivr.net/gh/furuse-kazufumi/{r}@main/a/b.png",
    "https://raw.githubusercontent.com/other-owner/{r}/main/a/b.png",
])
def test_check_noncanonical_urls_are_picked_and_fail(media, variant):
    """F2: 表に無い形の URL も数えて、問題にする(黙って通さない)。"""
    url = variant.format(r=REPO)
    assert am.scan_text(_md(url))["media"] == [url]
    probs = am.check_text(_md(url))
    assert len(probs) == 1 and probs[0]["kind"] in {"noncanonical_url", "unknown_repo"}, probs


def test_scan_strips_trailing_punctuation_and_fullwidth_close():
    url = am.raw_url("my-article", "fig.png")
    assert am.scan_text(f"see {url}.")["media"] == [url]
    assert am.scan_text(f"（{url}）、{url}。")["media"] == [url]


def test_scan_does_not_pick_unrelated_urls():
    text = "https://example.com/x.png https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/a.png"
    assert am.scan_text(text) == {"media": [], "fullseye": 1}


def test_put_refuses_case_only_clash(media, tmp_path):
    (media / "my-article").mkdir()
    (media / "my-article" / "Fig.png").write_bytes(b"\x89PNG-fake-1")
    _commit(media, "my-article/Fig.png")
    with pytest.raises(am.MediaRefused, match="大文字小文字"):
        am.put(_src(tmp_path), "my-article")


def test_check_lfs_pointer_fails(media, tmp_path):
    (media / "my-article").mkdir()
    (media / "my-article" / "fig.png").write_bytes(b"version https://git-lfs.github.com/spec/v1\noid sha256:0\nsize 1\n")
    _commit(media, "my-article/fig.png")
    assert _kinds(am.check_text(_md(am.raw_url("my-article", "fig.png")))) == ["lfs_pointer"]


def test_put_oserror_is_env_error_and_leaves_no_empty_dir(media, tmp_path, monkeypatch):
    real_open = open

    def boom(path, mode="r", *a, **k):
        if "xb" in mode:
            raise OSError(22, "boom")
        return real_open(path, mode, *a, **k)

    monkeypatch.setattr("builtins.open", boom)
    with pytest.raises(am.MediaEnvError):
        am.put(_src(tmp_path), "fresh-article")
    monkeypatch.undo()
    assert not (media / "fresh-article").exists()


def test_cli_unexpected_oserror_is_exit_2_one_line(media, tmp_path, monkeypatch, capsys):
    def boom(*a, **k):
        raise OSError(5, "disk")

    monkeypatch.setattr(am, "put", boom)
    assert am.main(["put", str(_src(tmp_path)), "my-article"]) == 2
    out = capsys.readouterr().out
    assert out.count("\n") == 1 and "環境の誤り" in out


def test_size_limits_non_constant_expression_is_env_error(tmp_path, monkeypatch):
    fake = tmp_path / "tools"
    fake.mkdir()
    (fake / "check_exhibit_assets.py").write_text("MAX_GIF_BYTES = 3 << 20\nMAX_PNG_BYTES = 6 << 20\n", encoding="utf-8")
    monkeypatch.setattr(am, "_TOOLS", fake)
    with pytest.raises(am.MediaEnvError):
        am.size_limits()


def test_check_json_empty_has_status(media, tmp_path, capsys):
    md = tmp_path / "a.md"
    md.write_text("no urls here\n", encoding="utf-8")
    assert am.main(["check", str(md), "--json"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["status"] == "empty" and rep["media_urls"] == 0


def test_check_json_status_ok_and_problems(media, tmp_path, capsys):
    good = am.put(_src(tmp_path), "my-article")
    _commit(media, "my-article/fig.png")
    md = tmp_path / "a.md"
    md.write_text(_md(good), encoding="utf-8")
    assert am.main(["check", str(md), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
    md.write_text(_md(am.raw_url("my-article", "ghost.png")), encoding="utf-8")
    assert am.main(["check", str(md), "--json"]) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "problems"


def test_put_refuses_symlinked_article_dir_pointing_outside(media, tmp_path):
    """M1: clone の外を指す記事ディレクトリ(symlink)には書かない。"""
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, media / "linked", target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlink を作れない環境")
    with pytest.raises(am.MediaRefused, match="外"):
        am.put(_src(tmp_path), "linked")
    assert list(outside.iterdir()) == []


def test_local_root_requires_dot_git(tmp_path, monkeypatch):
    """M5: git でないディレクトリは clone とみなさない。"""
    parent = tmp_path / "p"
    (parent / REPO).mkdir(parents=True)
    monkeypatch.setenv(am.ENV_ROOT, str(parent))
    with pytest.raises(am.MediaEnvError):
        am.local_root()


def test_default_parent_is_parent_of_tool_root(monkeypatch):
    """M6: 環境変数が無ければ、この道具のある repo の根の「親」。"""
    monkeypatch.delenv(am.ENV_ROOT, raising=False)
    assert am.media_parent() == Path(ROOT).resolve().parent


def test_parse_drops_fragment_without_query():
    """M7: ``?`` が無く ``#`` だけの URL。"""
    url = am.raw_url("my-article", "fig.png")
    assert am.parse_raw_url(url + "#top") == (REPO, "my-article", "fig.png")


class _H(BaseHTTPRequestHandler):
    seen: list = []

    def do_HEAD(self):  # noqa: N802
        _H.seen.append((self.command, self.path))
        self.send_response(200 if self.path.startswith("/ok") else 404)
        self.end_headers()

    def log_message(self, *a):
        pass


def test_http_status_real_head_against_loopback_server():
    """M8/M9/M14: ``_http_status`` を 127.0.0.1 の小さな server に向けて本当に走らせる(外へは出ない)。"""
    srv = HTTPServer(("127.0.0.1", 0), _H)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        base = f"http://127.0.0.1:{srv.server_port}"
        _H.seen.clear()
        assert am._http_status(base + "/ok.png?v=3") == 200
        assert am._http_status(base + "/missing.png") == 404
        assert _H.seen[0] == ("HEAD", "/ok.png?v=3")  # HEAD で、クエリも付けたまま叩く
    finally:
        srv.shutdown()
        srv.server_close()
    assert isinstance(am._http_status(base + "/ok.png", timeout=2.0), str)  # 閉じた後は接続できない
