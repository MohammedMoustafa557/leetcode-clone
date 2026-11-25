"""Download the long-form learning books into data/docs/ at setup time.

    python -m scripts.fetch_docs            # all collections
    python -m scripts.fetch_docs --only karan

Nothing here is committed to git. Every book is stored *unmodified* (original
markdown) plus its images, so the site can show it fully in-app with a credit
line. Splitting into chapters and pointing image/anchor URLs at our server
happens only when a page is rendered (app/services/docs.py).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data" / "docs"
RAW = "https://raw.githubusercontent.com/"

COLLECTIONS: dict[str, dict] = {
    "system-design-primer": {
        "title": "The System Design Primer",
        "author": "Donne Martin",
        "repo": "https://github.com/donnemartin/system-design-primer",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "base": RAW + "donnemartin/system-design-primer/master/",
        "files": ["README.md"],
        "split": 2,
    },
    "karan-system-design": {
        "title": "System Design (course)",
        "author": "Karan Pratap Singh",
        "repo": "https://github.com/karanpratapsingh/system-design",
        "license": "CC BY-NC-ND 4.0",
        "license_url": "https://creativecommons.org/licenses/by-nc-nd/4.0/",
        "base": RAW + "karanpratapsingh/system-design/main/",
        "files": ["README.md"],
        "split": 1,
        "notice": "Shown verbatim and unmodified, for non-commercial use, under CC BY-NC-ND 4.0.",
    },
    "behavioral-handbook": {
        "title": "Behavioral Interviews (Tech Interview Handbook)",
        "author": "Yangshun Tay and contributors",
        "repo": "https://github.com/yangshun/tech-interview-handbook",
        "license": "MIT",
        "license_url": "https://github.com/yangshun/tech-interview-handbook/blob/main/LICENSE",
        "base": RAW + "yangshun/tech-interview-handbook/main/apps/website/contents/",
        "image_base": RAW + "yangshun/tech-interview-handbook/main/apps/website/static/",
        "files": [
            "behavioral-interview.md", "behavioral-interview-questions.md",
            "behavioral-interview-rubrics.md", "behavioral-interview-senior-candidates.md",
        ],
        "split": 0,  # one chapter per file
    },
}

IMG_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)[^)]*\)|<img[^>]+src=[\"']([^\"']+)[\"']", re.I)


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "codearena-docs/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def resolve(src: str, meta: dict) -> str:
    if src.startswith(("http://", "https://")):
        return src
    if src.startswith("/"):
        return meta.get("image_base", meta["base"]) + src.lstrip("/")
    return meta["base"] + src


def asset_name(url: str) -> str:
    ext = Path(url.split("?")[0]).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"):
        ext = ".png"
    return hashlib.sha1(url.encode()).hexdigest()[:16] + ext


def fetch_collection(key: str) -> None:
    meta = COLLECTIONS[key]
    out = DATA / key
    (out / "assets").mkdir(parents=True, exist_ok=True)
    images: dict[str, str] = {}
    for name in meta["files"]:
        text = fetch(meta["base"] + name).decode("utf-8")
        (out / name).write_text(text, encoding="utf-8")
        for m in IMG_RE.finditer(text):
            src = m.group(1) or m.group(2)
            url = resolve(src, meta)
            target = out / "assets" / asset_name(url)
            images[src] = target.name
            if target.exists():
                continue
            try:
                target.write_bytes(fetch(url))
            except Exception as exc:  # keep going; the page shows the alt text
                print(f"  ! image {url}: {exc}")
                images.pop(src, None)
    manifest = {k: v for k, v in meta.items() if k not in ("base", "image_base")}
    manifest["images"] = images
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print(f"{key}: {len(meta['files'])} file(s), {len(images)} images")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=list(COLLECTIONS))
    ap.add_argument("--if-missing", action="store_true", help="skip collections that are already downloaded")
    args = ap.parse_args()
    for key in [args.only] if args.only else COLLECTIONS:
        if args.if_missing and (DATA / key / "manifest.json").exists():
            continue
        fetch_collection(key)


if __name__ == "__main__":
    main()
