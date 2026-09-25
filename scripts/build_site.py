#!/usr/bin/env python3
"""Build the public website from an explicit allowlist of pages and existing figures.

This assembles selected static assets without generating scientific figures.
Only the explicitly approved demo export is public; keep other weights,
manuscripts, raw data, and private notes out of the build.
"""
from pathlib import Path
import base64
import hashlib
import io
import json
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
    "assets/demo/manifest.json", "assets/demo/NOTICE.txt",
    "assets/demo/model.vtp-model.json", "assets/demo/sample.vtp-input.json",
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


def validate_demo_assets():
    """Only publish the two approved, checksummed inference assets."""
    directory = ROOT / "website/assets/demo"
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("format") != "vtp-browser-demo-v1":
        raise ValueError("Invalid public demo manifest")
    for key, name in (("model", "model.vtp-model.json"), ("input", "sample.vtp-input.json")):
        entry = manifest["assets"][key]
        payload = (directory / name).read_bytes()
        if entry["file"] != name or len(payload) != entry["bytes"] or hashlib.sha256(payload).hexdigest() != entry["sha256"]:
            raise ValueError(f"Public demo asset failed integrity verification: {name}")


def main():
    validate_demo_assets()
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
