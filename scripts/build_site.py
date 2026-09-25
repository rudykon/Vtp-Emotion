#!/usr/bin/env python3
"""Build the public website from an explicit allowlist of pages and existing figures.

This assembles a static website; it neither reads research data nor generates
scientific figures. Keep manuscripts, weights, and private notes out of the build.
"""
from pathlib import Path
import base64
import hashlib
import io
import tarfile
from urllib.request import urlopen
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
    "demo/index.md", "demo/index.zh.md", "stylesheets/demo.css",
    "javascripts/demo/core.js", "javascripts/demo/worker.js", "javascripts/demo/app.js",
    "licenses/onnxruntime.txt", "licenses/onnxruntime-third-party.txt",
)
FIGURES = (
    "icassp2027/method_overview.png", "icassp2027/method_overview.pdf",
    "icassp2027/external_source_decomposition.png",
    "icassp2027/external_source_decomposition.pdf",
    "icassp2027/external_diagnostics.png", "icassp2027/external_diagnostics.pdf",
    "external_data_landscape.png",
)


ORT_VERSION = "1.22.0"
ORT_INTEGRITY = "Ud/+EBo6mhuaQWt/OjaOk0iNWjXqJoeeMFr6xQEERZdIZH2OWpGzuujz7lfuOBjUa6TEE/sc4nb7Da5dNL34fg=="
ORT_FILES = ("ort.wasm.min.js", "ort-wasm-simd-threaded.mjs", "ort-wasm-simd-threaded.wasm")


def stage_browser_runtime():
    """Stage pinned inference code only, never a model or private input file."""
    cache = ROOT / "build" / "vendor" / f"onnxruntime-web-{ORT_VERSION}.tgz"
    if cache.is_symlink():
        raise ValueError("Runtime cache must not be a symlink")
    if cache.exists():
        payload = cache.read_bytes()
    else:
        url = f"https://registry.npmjs.org/onnxruntime-web/-/onnxruntime-web-{ORT_VERSION}.tgz"
        with urlopen(url, timeout=60) as response:
            payload = response.read(64 * 1024 * 1024 + 1)
    digest = base64.b64encode(hashlib.sha512(payload).digest()).decode("ascii")
    if digest != ORT_INTEGRITY:
        raise ValueError("ONNX Runtime package failed integrity verification")
    cache.parent.mkdir(parents=True, exist_ok=True)
    if not cache.exists():
        cache.write_bytes(payload)
    destination = STAGING / "javascripts" / "vendor" / "onnxruntime"
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as archive:
        for name in ORT_FILES:
            member = archive.getmember(f"package/dist/{name}")
            if not member.isfile() or member.size > 12 * 1024 * 1024:
                raise ValueError(f"Unexpected runtime member: {name}")
            with archive.extractfile(member) as source:
                (destination / name).write_bytes(source.read())


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
    stage_browser_runtime()
    subprocess.run([sys.executable, "-m", "mkdocs", "build", "--strict"], cwd=ROOT, check=True)
    # Material resolves its language-switch sitemap relative to each hreflang
    # page URL. Provide aliases so translated subpages work without 404 requests.
    site = ROOT / "site"
    sitemap = site / "sitemap.xml"
    for page in site.rglob("index.html"):
        if page.parent != site:
            shutil.copyfile(sitemap, page.parent / "sitemap.xml")
    print(f"Built website from {len(sources)} explicitly selected inputs and {len(ORT_FILES)} verified runtime files: {ROOT / 'site'}")


if __name__ == "__main__":
    main()
