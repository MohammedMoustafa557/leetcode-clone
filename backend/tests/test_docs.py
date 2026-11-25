import json

import pytest

from app.services import docs

BOOK = """Intro text with ![logo](images/logo.png)

# Caching

See [load balancers](#load-balancing). Image: <img src="images/lb.png">

```python
# not a heading
```

## Cache hit

# Load Balancing

Text.
"""


@pytest.fixture
def library(tmp_path, monkeypatch):
    root = tmp_path / "book"
    (root / "assets").mkdir(parents=True)
    (root / "README.md").write_text(BOOK)
    (root / "assets" / "0123456789abcdef.png").write_bytes(b"\x89PNG")
    (root / "manifest.json").write_text(json.dumps({
        "title": "Test Book", "author": "A", "repo": "https://example.com/r", "license": "CC BY-NC-ND 4.0",
        "license_url": "https://creativecommons.org/licenses/by-nc-nd/4.0/", "notice": "verbatim",
        "files": ["README.md"], "split": 1,
        "images": {"images/logo.png": "0123456789abcdef.png", "images/lb.png": "0123456789abcdef.png"},
    }))
    monkeypatch.setattr(docs, "DOCS_DIR", tmp_path)
    docs.load_collection.cache_clear()
    yield
    docs.load_collection.cache_clear()


def test_book_is_split_and_rendered_in_app(client, library):
    books = client.get("/api/docs").json()
    assert books[0]["id"] == "book" and books[0]["chapters"] == 3
    toc = client.get("/api/docs/book").json()
    assert [c["title"] for c in toc["chapters"]] == ["Introduction", "Caching", "Load Balancing"]
    ch = client.get(f"/api/docs/book/{toc['chapters'][1]['id']}").json()
    md = ch["markdown"]
    assert "# not a heading" in md and "## Cache hit" in md  # code fences don't split chapters
    assert f"](/learn/docs/book/{toc['chapters'][2]['id']}#load-balancing)" in md
    assert 'src="/api/docs/book/assets/0123456789abcdef.png"' in md
    assert ch["credit"]["license"] == "CC BY-NC-ND 4.0" and ch["next"]["title"] == "Load Balancing"
    # text other than links/images is untouched
    assert "Text." in client.get(f"/api/docs/book/{toc['chapters'][2]['id']}").json()["markdown"]


def test_assets_are_served_and_paths_validated(client, library):
    assert client.get("/api/docs/book/assets/0123456789abcdef.png").content == b"\x89PNG"
    assert client.get("/api/docs/book/assets/..%2Fmanifest.json").status_code == 404
    assert client.get("/api/docs/book/assets/aaaaaaaaaaaaaaaa.png").status_code == 404
    assert client.get("/api/docs/nope").status_code == 404
    assert client.get("/api/docs/book/999-x").status_code == 404


def test_handbook_front_matter_and_mdx_lines(tmp_path, monkeypatch):
    root = tmp_path / "hb"
    root.mkdir()
    (root / "a.md").write_text("---\ntitle: 'Hello'\n---\n\nimport X from './x';\n\n<InDocAd />\n\nBody\n")
    (root / "manifest.json").write_text(json.dumps({"files": ["a.md"], "split": 0, "images": {}}))
    monkeypatch.setattr(docs, "DOCS_DIR", tmp_path)
    docs.load_collection.cache_clear()
    meta = docs.load_collection("hb")
    docs.load_collection.cache_clear()
    assert meta["chapters"][0]["title"] == "Hello"
    assert "import" not in meta["chapters"][0]["body"] and "InDocAd" not in meta["chapters"][0]["body"]
    assert "Body" in meta["chapters"][0]["body"]
