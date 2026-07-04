import importlib.util
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "build-pages.py"
SPEC = importlib.util.spec_from_file_location("build_pages", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
build_pages = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(build_pages)


def test_render_markdown_renders_cover_markdown_inside_center(tmp_path, monkeypatch):
    docs_dir = tmp_path / "docs"
    site_dir = tmp_path / "site"
    source = docs_dir / "cover.md"
    destination = site_dir / "cover.html"
    docs_dir.mkdir()
    site_dir.mkdir()
    source.write_text(
        """<center>

![Logo UPT](./media/logo-upt.png)

**UNIVERSIDAD PRIVADA DE TACNA**

</center>
""",
        encoding="utf-8",
    )
    monkeypatch.setattr(build_pages, "SITE_DIR", site_dir)

    build_pages.render_markdown(source, destination)

    html = destination.read_text(encoding="utf-8")
    assert '<div class="cover">' in html
    assert '<img alt="Logo UPT" src="./media/logo-upt.png">' in html
    assert "<strong>UNIVERSIDAD PRIVADA DE TACNA</strong>" in html
    assert "![Logo UPT]" not in html
