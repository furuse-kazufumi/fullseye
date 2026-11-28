"""公開サイトの404応急ページと、GALLERY画像参照の回帰検査。

Regression checks for the public-site 404 fallback and GALLERY image references.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RAW_GALLERY = "https://raw.githubusercontent.com/furuse-kazufumi/fullseye/master/examples_3d/_gallery/"


def test_404_redirect_is_fixed_to_repository_paths_only():
    """クエリや断片を転送せず、固定ホストの既知フォルダだけを扱う。"""
    text = (DOCS / "404.html").read_text(encoding="utf-8")
    for prefix in ("/examples/", "/examples_3d/", "/tools/", "/tests/", "/fullseye/", "/rust/"):
        assert '"%s"' % prefix in text
    assert "window.location.pathname" in text
    assert "window.location.search" not in text and "window.location.hash" not in text
    assert 'window.location.replace("https://github.com/furuse-kazufumi/fullseye/"' in text
    assert 'href="/"' in text
    assert 'href="https://github.com/furuse-kazufumi/fullseye"' in text


def test_gallery_thumbnails_work_on_pages_and_github():
    """サイト外の相対画像を残さず、14枚×2言語をraw URLで表示する。"""
    for name in ("GALLERY.md", "GALLERY.en.md"):
        text = (DOCS / name).read_text(encoding="utf-8")
        assert text.count(RAW_GALLERY) == 14, name
        assert '../examples_3d/_gallery/' not in text, name
