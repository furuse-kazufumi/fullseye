"""記事の素材を素材 repo(``fullseye-media2026q4`` など)に置き、原稿の raw URL を検める道具(2026-11-11)。

Qiita の記事が読む画像は、これまで本体の ``docs/articles/assets/`` に置いて raw URL で配ってきた。
本体が太る(assets だけで 1.4 GB)ので、**これから書く新しい記事の素材**は四半期ごとの公開 repo に置く。
既存の記事・素材・生成器はそのまま(この道具は足すだけ)。

素材 repo の決まり(素材 repo の README):

- 一度置いたファイルは動かさない・消さない・名前を変えない(公開済みの記事の画像が欠ける)。
  差し替えるときは新しい名前で足し、記事の URL を書き換える。
- 置き方は ``<記事の名前>/<ファイル名>``。記事の名前は英小文字・数字・``-``。
- 大きさの目安は GIF 3 MB・PNG 6 MB(``tools/check_exhibit_assets.py`` の ``MAX_GIF_BYTES`` /
  ``MAX_PNG_BYTES`` をそのまま読む)。GIF 以外は PNG の値を上限にする。

手元の clone は「この道具のある repo の根」の**親**の下(``<親>/fullseye-media2026q4``)が既定。
環境変数 ``FULLSEYE_MEDIA_ROOT``(clone たちの親ディレクトリ)で変えられる。作業木(worktree)は
repo の隣に無いことがあるので、見つからないときはこの環境変数を案内する。

使い方::

    py -3.11 tools/article_media.py put <src> <article> [--name N] [--json]
    py -3.11 tools/article_media.py check <原稿.md> [--http] [--json]
    py -3.11 tools/article_media.py url <article> <filename> [--json]

終了コード: 問題なし 0 / 検査の不合格・put の拒否 1 / 使い方・環境の誤り 2。

``put`` は clone に**写すだけ**で、git の add・commit・push はしない(人が中身を見てから commit する)。
``check`` は既定ではネットワークを叩かない。``--http`` を付けたときだけ HEAD で 200 を確かめる。

stdlib だけで動く(``check_exhibit_assets.py`` は numpy を読むので import せず、定数を ast で読む)。
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
_ROOT = _TOOLS.parent

OWNER = "furuse-kazufumi"
RAW_HOST = "https://raw.githubusercontent.com/"

#: 素材 repo の表。名前 → 枝と raw URL の頭。**次の四半期の repo を足すときは、ここに 1 行足して
#: ``CURRENT`` を変えるだけ。** 古い行は消さない(公開済みの記事がその repo を指し続ける)。
MEDIA_REPOS: dict[str, dict[str, str]] = {
    "fullseye-media2026q4": {
        "branch": "main",
        "raw_base": RAW_HOST + OWNER + "/fullseye-media2026q4/main/",
    },
}

#: いま新しい素材を置く repo。
CURRENT = "fullseye-media2026q4"

#: clone たちの親ディレクトリを指す環境変数。
ENV_ROOT = "FULLSEYE_MEDIA_ROOT"

#: 本体の raw URL(対象外。数だけ報告する)。
FULLSEYE_RAW_PREFIX = RAW_HOST + OWNER + "/fullseye/"

#: 記事の名前(英小文字・数字・``-``)とファイル名(英小文字・数字・``-``・``_``・``.``)。
_ARTICLE_RE = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
#: 末尾は ``.`` でも空白でもない(Windows が末尾の ``.`` と空白を落とし、実物の名前と URL がずれる)。
_FILENAME_RE = re.compile(r"[a-z0-9](?:[a-z0-9._-]*[a-z0-9_-])?\Z")
_MAX_ARTICLE_LEN = 64
_MAX_FILENAME_LEN = 100
#: Windows の予約名(語幹。``con.png`` も ``con.v2.png`` も不可)。
_RESERVED_RE = re.compile(r"(?:con|prn|aux|nul|com[1-9]|lpt[1-9])\Z")

#: 原稿から URL を広く拾う(文末の句読点・全角の括弧は URL に含めない)。素材 repo を指していそうなものは
#: ``_looks_media`` で選ぶ(大文字小文字を無視、``http://``・``raw.github.com``・``/blob/``・jsDelivr も拾う)。
_ANY_URL_RE = re.compile(r"(?i)https?://[^\s)\"'<>\]）」』、。]+")
_TRAIL = ".,;:!"
_FULLSEYE_URL_RE = re.compile(re.escape(FULLSEYE_RAW_PREFIX) + r"[^\s)\"'<>\]]+")


def _looks_media(url: str) -> bool:
    """URL の host の後ろ 3 区間のどれかの頭が ``fullseye-media``(大小無視)なら素材 repo を指していそう。"""
    rest = re.sub(r"(?i)^https?://", "", url).split("#", 1)[0].split("?", 1)[0]
    return any(seg.lower().startswith("fullseye-media") for seg in rest.split("/")[1:4])


class MediaError(Exception):
    """この道具の誤りの基底。"""


class MediaEnvError(MediaError):
    """使い方・環境の誤り(clone が無い・git が無い・src が無いなど)。終了コード 2。"""


class MediaRefused(MediaError):
    """put が拒んだ(名前の形・大きさ・同じ名前で中身が違う)。終了コード 1。"""


# ---------------------------------------------------------------- 大きさの上限

def _const_int(node: ast.AST) -> int:
    """``3 * 1024 * 1024`` のような整数の定数式だけを評価する(それ以外は ValueError)。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Mult, ast.Add)):
        a, b = _const_int(node.left), _const_int(node.right)
        return a * b if isinstance(node.op, ast.Mult) else a + b
    raise ValueError(f"整数の定数式ではない: {ast.dump(node)}")


def size_limits() -> dict[str, int]:
    """``tools/check_exhibit_assets.py`` の ``MAX_GIF_BYTES`` / ``MAX_PNG_BYTES`` を読む。

    numpy を読まないよう import せず、ソースを ast で読む。見つからなければ MediaEnvError
    (値を黙って既定に戻すと、基準が動いたときに食い違うため)。
    """
    src = _TOOLS / "check_exhibit_assets.py"
    want = {"MAX_GIF_BYTES": "gif", "MAX_PNG_BYTES": "png"}
    got: dict[str, int] = {}
    try:
        tree = ast.parse(src.read_text(encoding="utf-8"))
    except (OSError, SyntaxError) as e:
        raise MediaEnvError(f"大きさの基準を読めない({src.name}): {e}") from e
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in want:
                try:
                    got[want[name]] = _const_int(node.value)
                except ValueError as e:
                    raise MediaEnvError(f"{src.name} の {name} を読めない: {e}") from e
    if set(got) != set(want.values()):
        raise MediaEnvError(f"{src.name} に {sorted(want)} が見つからない")
    return got


def limit_for(filename: str, limits: dict[str, int] | None = None) -> int:
    """ファイル名の拡張子から上限(バイト)を返す。GIF は GIF の値、それ以外は PNG の値。"""
    lim = limits or size_limits()
    return lim["gif"] if filename.lower().endswith(".gif") else lim["png"]


# ---------------------------------------------------------------- 名前と URL

def check_article_name(article: str) -> None:
    """記事の名前の形を検める(英小文字・数字・``-``)。合わなければ MediaRefused。"""
    if (not isinstance(article, str) or not _ARTICLE_RE.match(article)
            or len(article) > _MAX_ARTICLE_LEN):
        raise MediaRefused(f"記事の名前 {article!r} の形が違う(英小文字・数字・'-' だけ、先頭は英数字、"
                           f"{_MAX_ARTICLE_LEN} 字まで)")
    if _RESERVED_RE.match(article):
        raise MediaRefused(f"記事の名前 {article!r} は Windows の予約名")


def check_file_name(filename: str) -> None:
    """ファイル名の形を検める(英小文字・数字・``-``・``_``・``.``。区切り・``..`` は拒む)。"""
    if (not isinstance(filename, str) or not _FILENAME_RE.match(filename) or ".." in filename
            or len(filename) > _MAX_FILENAME_LEN):
        raise MediaRefused(f"ファイル名 {filename!r} の形が違う(英小文字・数字・'-'・'_'・'.' だけ、"
                           f"先頭は英数字、末尾は '.' でも空白でもない、'..' と区切りは不可、"
                           f"{_MAX_FILENAME_LEN} 字まで)")
    if _RESERVED_RE.match(filename.split(".", 1)[0]):
        raise MediaRefused(f"ファイル名 {filename!r} は Windows の予約名")


def _repo_info(repo: str) -> dict[str, str]:
    try:
        return MEDIA_REPOS[repo]
    except KeyError:
        raise MediaEnvError(f"素材 repo {repo!r} は表(MEDIA_REPOS)に無い。表: {sorted(MEDIA_REPOS)}") from None


def raw_url(article: str, filename: str, repo: str = CURRENT) -> str:
    """素材の raw URL を組む(名前の形も検める)。"""
    info = _repo_info(repo)
    check_article_name(article)
    check_file_name(filename)
    return info["raw_base"] + article + "/" + filename


def _classify(url: str) -> tuple[tuple[str, str, str] | None, str | None, str]:
    """URL を読み、``(結果, 問題の種類, 説明)`` を返す。結果が None なら種類と説明が入る。"""
    if not _looks_media(url):
        return None, "not_media", "素材 repo の raw URL ではない"
    prefix = RAW_HOST + OWNER + "/"
    if not url.startswith(prefix):
        return None, "noncanonical_url", (
            f"素材 repo を指す URL が正しい形ではない(https://raw.githubusercontent.com/{OWNER}/<repo>/<枝>/... "
            "の小文字の形だけ。http・大文字・blob・jsDelivr などは不可)")
    path = url[len(prefix):].split("#", 1)[0].split("?", 1)[0]
    repo, _, rest = path.partition("/")
    if repo not in MEDIA_REPOS:
        return None, "unknown_repo", f"素材 repo {repo!r} は表に無い(表: {sorted(MEDIA_REPOS)})"
    branch = MEDIA_REPOS[repo]["branch"]
    if not rest.startswith(branch + "/"):
        return None, "wrong_branch", f"枝が {branch!r} ではない"
    parts = rest[len(branch) + 1:].split("/")
    if len(parts) != 2:
        return None, "bad_shape", "形が <記事の名前>/<ファイル名> ではない"
    article, filename = parts
    try:
        check_article_name(article)
        check_file_name(filename)
    except MediaRefused as e:
        return None, "bad_shape", str(e)
    return (repo, article, filename), None, ""


def parse_raw_url(url: str) -> tuple[str, str, str] | None:
    """素材の raw URL を ``(repo, article, filename)`` に読む。

    ``?v=N`` などのクエリと ``#`` 以降は落として読む。表に無い repo・枝の違い・形の違いは None。
    """
    got, _kind, _msg = _classify(url)
    return got


# ---------------------------------------------------------------- clone

def media_parent() -> Path:
    """clone たちの親ディレクトリ。``FULLSEYE_MEDIA_ROOT`` が無ければ「この repo の根の親」。"""
    env = os.environ.get(ENV_ROOT)
    return Path(env) if env else _ROOT.parent


def local_root(repo: str = CURRENT) -> Path:
    """素材 repo の手元の clone の根。無ければ MediaEnvError(環境変数を案内する)。"""
    _repo_info(repo)
    root = media_parent() / repo
    if not (root / ".git").exists():
        where = f"環境変数 {ENV_ROOT}" if os.environ.get(ENV_ROOT) else "この repo の根の親(既定)"
        raise MediaEnvError(
            f"素材 repo {repo!r} の clone が見つからない({where} の下の {repo})。"
            f"clone してから、clone たちの親ディレクトリを環境変数 {ENV_ROOT} に入れる"
            "(作業木は repo の隣に無いことがある)。")
    return root


def _git(root: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=False)
    except FileNotFoundError as e:
        raise MediaEnvError("git が見つからない") from e


def committed_blob(root: Path, rel: str, ref: str = "HEAD") -> str | None:
    """``ref``(既定 ``HEAD``)の木にある ``rel`` の blob の sha。無ければ None(ref が無くても None)。"""
    p = _git(root, "ls-tree", ref, "--", rel)
    if p.returncode != 0:
        return None
    line = p.stdout.decode("utf-8", "replace").strip()
    if not line:
        return None
    meta = line.split("\t", 1)[0].split()
    return meta[2] if len(meta) >= 3 and meta[1] == "blob" else None


def worktree_blob(root: Path, rel: str) -> str | None:
    """手元のファイルを git に入れたときの blob の sha(``git hash-object``)。"""
    p = _git(root, "hash-object", "--", rel)
    return p.stdout.decode().strip() if p.returncode == 0 else None


def repo_state(root: Path, repo: str) -> dict:
    """``check`` が頼る手元の git の状態を読む(ネットワークは叩かない・fetch しない)。

    ``{"branch": 今の枝(detached なら None), "remote_ref": "origin/<枝>" か None, "ahead": 先行 commit 数か None}``。
    """
    want = MEDIA_REPOS[repo]["branch"]
    p = _git(root, "symbolic-ref", "--short", "-q", "HEAD")
    branch = p.stdout.decode("utf-8", "replace").strip() if p.returncode == 0 else None
    remote_ref = f"origin/{want}"
    if _git(root, "rev-parse", "--verify", "-q", f"refs/remotes/{remote_ref}").returncode != 0:
        return {"branch": branch, "remote_ref": None, "ahead": None}
    q = _git(root, "rev-list", "--count", f"{remote_ref}..HEAD")
    ahead = int(q.stdout.decode().strip()) if q.returncode == 0 and q.stdout.strip().isdigit() else None
    return {"branch": branch, "remote_ref": remote_ref, "ahead": ahead}


def is_lfs_pointer(root: Path, blob: str) -> bool:
    """blob が Git LFS の pointer なら真(raw URL は画像ではなく pointer の文字を返す)。"""
    p = _git(root, "cat-file", "blob", blob)
    return p.returncode == 0 and p.stdout[:40].startswith(b"version https://git-lfs")


# ---------------------------------------------------------------- put

def put(src: str | os.PathLike, article: str, repo: str = CURRENT, name: str | None = None) -> str:
    """``src`` を clone の ``<article>/<name>`` に写し、raw URL を返す。git の操作はしない。

    - 同じ名前があって中身が同じなら何もしない(冪等)。中身が違えば拒む(上書きしない)。
    - 名前の形・大きさの上限・空のファイルを検める。
    """
    src_p = Path(src)
    filename = src_p.name if name is None else name
    check_article_name(article)
    check_file_name(filename)
    if not src_p.is_file():
        raise MediaEnvError(f"src {src_p} はファイルではない(無いか、ディレクトリ)")
    data = src_p.read_bytes()
    if not data:
        raise MediaRefused(f"src {src_p.name} は空(0 バイト)")
    lim = limit_for(filename)
    if len(data) > lim:
        raise MediaRefused(f"{filename} は {len(data):,} バイトで、上限 {lim:,} バイト"
                           f"(GIF 3 MB・その他 6 MB、tools/check_exhibit_assets.py の基準)を超える")
    root = local_root(repo)
    dest = root / article / filename
    # 名前は検め済みだが、clone の中に収まることを解決後のパスでも確かめる(fail-closed)。
    if root.resolve() not in dest.resolve().parents:
        raise MediaRefused(f"{article}/{filename} が clone の外を指す")
    url = raw_url(article, filename, repo)
    if dest.parent.is_dir():
        clash = [n for n in os.listdir(dest.parent) if n.lower() == filename.lower() and n != filename]
        if clash:
            raise MediaRefused(f"{repo} の {article}/ に大文字小文字だけ違う {clash[0]!r} が既にある"
                               "(Windows では同じファイル。新しい名前で足す)")
    if dest.exists():
        if dest.is_file() and dest.read_bytes() == data:
            return url
        raise MediaRefused(
            f"{repo} に {article}/{filename} が既にあり、中身が違う。置いたファイルは上書きしない"
            "(動かさない・消さない・名前を変えない)。新しい名前で足して(--name)、記事の URL を書き換える。")
    made = not dest.parent.exists()
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "xb") as f:  # 排他的に作る(間に誰かが置いても上書きしない)
            f.write(data)
    except OSError as e:
        if made:
            try:
                dest.parent.rmdir()  # 失敗したときに空の記事ディレクトリを残さない
            except OSError:
                pass
        raise MediaEnvError(f"{article}/{filename} を書けない: {e}") from e
    return url


# ---------------------------------------------------------------- check

def _http_status(url: str, timeout: float = 15.0) -> int | str:
    """HEAD で状態コードを返す(通らなければ説明の文字列)。``--http`` のときだけ呼ぶ。"""
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 (https の raw URL だけ)
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except (urllib.error.URLError, OSError) as e:
        return f"接続できない: {e}"


def scan_text(text: str) -> dict:
    """原稿から URL を拾うだけ(検めない)。``{"media": [...], "fullseye": n}``。重複は 1 本にまとめる。

    素材 repo を指していそうな URL(形が違うものも)を全部拾う。本体の raw URL は数だけ。
    """
    media: list[str] = []
    for m in _ANY_URL_RE.finditer(text):
        u = m.group(0).rstrip(_TRAIL)
        if _looks_media(u) and u not in media:
            media.append(u)
    return {"media": media, "fullseye": len(_FULLSEYE_URL_RE.findall(text))}


_STALE = "手元の origin/<枝> は fetch していないので古いかもしれない"


def _repo_problems(repo: str, branch: str, st: dict) -> list[dict]:
    """素材 repo ごとに 1 回だけ出す問題(今いる枝・未 push の commit)。"""
    tag = f"(repo {repo})"
    out: list[dict] = []
    if st["branch"] != branch:
        now = repr(st["branch"]) if st["branch"] else "detached HEAD"
        out.append({"url": tag, "kind": "wrong_local_branch",
                    "message": f"{repo} の今いる枝は {now} で、{branch!r} ではない(出す枝は {branch!r})"})
    if st["remote_ref"] is not None and st["ahead"]:
        out.append({"url": tag, "kind": "unpushed",
                    "message": f"{repo} は origin/{branch} より {st['ahead']} commit 先行している"
                               f"(push していない)。{_STALE}"})
    return out


def check_text(text: str, http: bool = False) -> list[dict]:
    """原稿の中の素材 repo の raw URL を全部拾って検め、問題の一覧を返す(空なら問題なし)。

    (a) 表にある repo か・枝が合うか (b) 形が ``<article>/<filename>`` か
    (c) 手元の clone にそのファイルがあるか (d) clone の今いる枝が表の枝で、``origin/<枝>``(fetch しない)に push 済みで、手元の中身と同じか
    (``--http`` のとき)HEAD リクエストが 200 か。問題は ``{"url", "kind", "message"}``。
    clone が無いなど環境の誤りは MediaEnvError。本体の raw URL は対象外(``scan_text`` が数える)。
    """
    problems: list[dict] = []
    states: dict[str, dict] = {}
    for url in scan_text(text)["media"]:
        got, kind, msg = _classify(url)
        if got is None:
            problems.append({"url": url, "kind": kind, "message": msg})
            continue
        repo, article, filename = got
        root = local_root(repo)
        rel = f"{article}/{filename}"
        if repo not in states:
            states[repo] = repo_state(root, repo)
            problems.extend(_repo_problems(repo, MEDIA_REPOS[repo]["branch"], states[repo]))
        st = states[repo]
        if st["remote_ref"] is None:
            problems.append({"url": url, "kind": "no_remote_ref",
                             "message": f"{repo} に origin/{MEDIA_REPOS[repo]['branch']} が無く、"
                                        "push 済みか確かめられない"})
            continue
        if not (root / article / filename).is_file():
            problems.append({"url": url, "kind": "missing", "message": f"手元の clone {repo} に {rel} が無い"})
            continue
        blob = committed_blob(root, rel, st["remote_ref"])
        if blob is None:
            kind = "unpushed" if committed_blob(root, rel) else "uncommitted"
            why = ("commit 済みだが origin に無い(push されていない)" if kind == "unpushed"
                   else f"{st['remote_ref']} に無い(commit・push されていない)")
            problems.append({"url": url, "kind": kind,
                             "message": f"{rel} は {repo} で{why}。このまま出すと 404"
                                        f"(origin は手元の追跡枝で、最後の fetch・push の時点のもの。{_STALE})"})
            continue
        if is_lfs_pointer(root, blob):
            problems.append({"url": url, "kind": "lfs_pointer",
                             "message": f"{rel} は Git LFS の pointer(raw URL は画像を返さない)"})
            continue
        if worktree_blob(root, rel) != blob:
            problems.append({"url": url, "kind": "modified",
                             "message": f"{rel} の手元の中身が HEAD と違う(置いたファイルは変えない)"})
            continue
        if http:
            st = _http_status(url)
            if st != 200:
                problems.append({"url": url, "kind": "http", "message": f"HEAD が 200 でない: {st}"})
    return problems


# ---------------------------------------------------------------- CLI

def _emit(as_json: bool, payload: dict, lines: list[str]) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        for ln in lines:
            print(ln)


def _cmd_put(a) -> int:
    url = put(a.src, a.article, name=a.name)
    _emit(a.json, {"ok": True, "url": url, "repo": CURRENT},
          [url, f"(写しただけ。{CURRENT} の clone で中身を見てから add・commit・push する)"])
    return 0


def _cmd_url(a) -> int:
    url = raw_url(a.article, a.filename)
    _emit(a.json, {"ok": True, "url": url}, [url])
    return 0


def _cmd_check(a) -> int:
    try:
        text = Path(a.manuscript).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        raise MediaEnvError(f"原稿を読めない: {e}") from e
    found = scan_text(text)
    problems = check_text(text, http=a.http)
    n = len(found["media"])
    lines = [f"素材 repo の raw URL: {n} 本 / 問題 {len(problems)} 件"
             f" / 本体(fullseye)の raw URL: {found['fullseye']} 本(対象外)"
             + ("" if a.http else " / HTTP は確かめていない(--http で確かめる)")
             + (f" / {_STALE}" if n else "")]
    if n == 0:
        lines.append("素材 repo の URL を 1 本も拾わなかった(検めた素材は 0 本。合格ではなく、対象が無い)。")
    for p in problems:
        lines.append(f"  [{p['kind']}] {p['url']}\n      {p['message']}")
    status = "problems" if problems else ("empty" if n == 0 else "ok")
    _emit(a.json, {"ok": not problems, "status": status, "media_urls": n, "fullseye_urls": found["fullseye"],
                   "http_checked": bool(a.http), "urls": found["media"], "problems": problems}, lines)
    return 1 if problems else 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="記事の素材を素材 repo に置き、原稿の raw URL を検める。")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("put", help="素材を clone に写して raw URL を出す(git の操作はしない)")
    p.add_argument("src")
    p.add_argument("article")
    p.add_argument("--name", default=None, help="置く名前(既定は src のファイル名)")
    p.set_defaults(fn=_cmd_put)
    c = sub.add_parser("check", help="原稿の素材 repo の raw URL を検める")
    c.add_argument("manuscript")
    c.add_argument("--http", action="store_true", help="HEAD リクエストで 200 を確かめる(既定は叩かない)")
    c.set_defaults(fn=_cmd_check)
    u = sub.add_parser("url", help="raw URL を組む")
    u.add_argument("article")
    u.add_argument("filename")
    u.set_defaults(fn=_cmd_url)
    for sp in (p, c, u):
        sp.add_argument("--json", action="store_true", help="機械可読の報告")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return int(e.code or 0)
    try:
        return a.fn(a)
    except MediaRefused as e:
        _emit(a.json, {"ok": False, "error": "refused", "message": str(e)}, [f"拒否: {e}"])
        return 1
    except MediaEnvError as e:
        _emit(a.json, {"ok": False, "error": "environment", "message": str(e)}, [f"環境の誤り: {e}"])
        return 2
    except (OSError, ValueError) as e:  # 想定外でもトレースバックにせず、環境の誤りとして 1 行で出す
        msg = f"{type(e).__name__}: {e}"
        _emit(a.json, {"ok": False, "error": "environment", "message": msg}, [f"環境の誤り: {msg}"])
        return 2


if __name__ == "__main__":
    sys.exit(main())
