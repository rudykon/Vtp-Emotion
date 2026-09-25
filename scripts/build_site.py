#!/usr/bin/env python3
"""Build the public website from an explicit allowlist of pages and existing figures.

This assembles a static website; it neither reads research data nor generates
scientific figures. Keep manuscripts, weights, and private notes out of the build.
"""
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "build" / "site_docs"
PAGES = (
    "index.md", "index.zh.md",
    "guide/method.md", "guide/method.zh.md",
    "research/evidence.md", "research/evidence.zh.md",
    "reference/reproduction.md", "reference/reproduction.zh.md",
    "stylesheets/extra.css", "assets/brand/icon.svg",
)
FIGURES = (
    "icassp2027/method_overview.png", "icassp2027/method_overview.pdf",
    "icassp2027/external_source_decomposition.png",
    "icassp2027/external_source_decomposition.pdf",
    "icassp2027/external_diagnostics.png", "icassp2027/external_diagnostics.pdf",
    "external_data_landscape.png",
)


def main():
    sources = [(ROOT / "website" / name, Path(name)) for name in PAGES]
    sources += [(ROOT / "docs" / "figures" / name, Path("assets/figures") / name) for name in FIGURES]
    sources += [(ROOT / "docs/brand-mark.svg", Path("assets/brand/wordmark.svg")),
                (ROOT / "LICENSE", Path("assets/LICENSE.txt"))]
    for source, _ in sources:
        if not source.is_file() or source.is_symlink():
            raise ValueError(f"Missing or symlinked website input: {source}")
    if STAGING.is_symlink():
        raise ValueError("Website staging directory must not be a symlink")
    if STAGING.exists():
        shutil.rmtree(STAGING)
    for source, destination in sources:
        target = STAGING / destination
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    subprocess.run([sys.executable, "-m", "mkdocs", "build", "--strict"], cwd=ROOT, check=True)
    # Material resolves its language-switch sitemap relative to each hreflang
    # page URL. Provide aliases so translated subpages work without 404 requests.
    site = ROOT / "site"
    sitemap = site / "sitemap.xml"
    for page in site.rglob("index.html"):
        if page.parent != site:
            shutil.copyfile(sitemap, page.parent / "sitemap.xml")
    print(f"Built website from {len(sources)} explicitly selected inputs: {ROOT / 'site'}")


if __name__ == "__main__":
    main()
