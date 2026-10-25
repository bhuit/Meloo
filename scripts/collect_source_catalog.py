"""Resolve exact PyPI source releases; optionally download and verify their hashes.

Only official PyPI/Qt/GitHub/TDF source endpoints are used. This records evidence,
not a legal certification or a claim that wrapper sources cover bundled engines.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"pymupdf4llm", "pymupdf_layout", "onnxruntime", "PySide6_Pdf", "PySide6_WebEngine"}


def read_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Meloo-source-catalog/0.4.2"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def resolve(package):
    name, version = package["name"], package["version"]
    item = {"name": name, "version": version, "license": package.get("license"), "pypi": f"https://pypi.org/project/{name}/{version}/"}
    try:
        metadata = read_json(f"https://pypi.org/pypi/{name}/{version}/json")
        item["sources"] = [{"filename": f["filename"], "url": f["url"], "sha256": f["digests"]["sha256"], "bytes": f["size"]} for f in metadata["urls"] if f["packagetype"] == "sdist"]
        item["project_urls"] = metadata["info"].get("project_urls")
        item["status"] = "sdist_available" if item["sources"] else "upstream_source_required"
    except Exception as error:
        item["status"] = "lookup_failed"
        item["error"] = type(error).__name__
    return item


def download(source, directory):
    path = directory / source["filename"]
    if Path(source["filename"]).name != source["filename"]:
        raise ValueError("Invalid source filename")
    if not path.exists():
        request = urllib.request.Request(source["url"], headers={"User-Agent": "Meloo-source-catalog/0.4.2"})
        with urllib.request.urlopen(request, timeout=120) as stream, path.with_suffix(path.suffix + ".partial").open("xb") as target:
            while block := stream.read(1024 * 1024):
                target.write(block)
        path.with_suffix(path.suffix + ".partial").rename(path)
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != source["sha256"]:
        raise RuntimeError(f"Source checksum mismatch: {path.name}")
    return path.name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    inventory = json.loads((ROOT / "licenses/python-environment/inventory.json").read_text(encoding="utf-8"))
    packages = [p for p in inventory["packages"] if p["name"] not in EXCLUDED]
    with ThreadPoolExecutor(max_workers=6) as pool:
        items = list(pool.map(resolve, packages))
    catalog = {"scope": "Build environment source references; see build_portable.py exclusions and docs/THIRD_PARTY.md for native engines.", "packages": items}
    (ROOT / "licenses/source-catalog.json").write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.download:
        directory = ROOT / "build/third-party-sources/python"
        directory.mkdir(parents=True, exist_ok=True)
        for item in items:
            for source in item.get("sources", []):
                print(download(source, directory), flush=True)
    print(json.dumps({"packages": len(items), "missing_source_distributions": [{"name": i["name"], "version": i["version"], "status": i["status"]} for i in items if i["status"] != "sdist_available"]}))


if __name__ == "__main__":
    main()
