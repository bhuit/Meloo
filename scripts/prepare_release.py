"""Attach complete Meloo sources and sanitized test evidence to a fresh portable."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    payload = ROOT / "dist/Zeste"
    manifest = json.loads((payload / ".zeste-generated.json").read_text(encoding="utf-8"))
    if manifest.get("product") != "zeste-windows-portable":
        raise RuntimeError("Unrecognized portable")
    for relative, expected in manifest["source_sha256"].items():
        if sha256(ROOT / relative) != expected:
            raise RuntimeError(f"Rebuild after source change: {relative}")
    validation = {}
    for name in ("source", "packaged"):
        report = ET.parse(ROOT / f"build/validation/{name}.xml").getroot()
        cases = report.findall(".//testcase")
        if not cases or any(case.find(tag) is not None for case in cases for tag in ("failure", "error", "skipped")):
            raise RuntimeError(f"All {name} checks must pass before delivery")
        validation[name] = {"passed": len(cases), "tests": [case.get("name") for case in cases]}
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, capture_output=True, check=True)
    files = sorted(set(result.stdout.decode("utf-8").split("\0")) - {""})
    source = payload / "source"
    if source.exists():
        raise RuntimeError("Preserving existing source directory; build a fresh portable")
    for relative in files:
        src = ROOT / relative
        if src.is_symlink() or src.is_junction() or not src.is_file():
            raise RuntimeError(f"Unexpected source entry: {relative}")
        if src.suffix.lower() in (".exe", ".dll", ".pyd", ".msi", ".zip"):
            raise RuntimeError(f"Binary does not belong in source archive: {relative}")
        target = source / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    for name in ("README.md", "README.txt", "LISEZMOI.md", "NOTICE.txt", "LICENSE.txt"):
        shutil.copy2(ROOT / name, payload / name)
    for directory in ("licenses", "docs", "exemples"):
        shutil.copytree(ROOT / directory, payload / directory, dirs_exist_ok=True)
    validation.update(version=manifest["version"], executable_sha256=sha256(payload / "Meloo.exe"))
    (payload / "validation").mkdir(exist_ok=True)
    (payload / "validation/delivery.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    output = ROOT / f"dist/Sources-Meloo-{manifest['version']}.zip"
    with zipfile.ZipFile(output, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in files:
            archive.write(source / relative, "Meloo/" + relative)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            raise RuntimeError("Invalid source archive")
    output.with_suffix(".zip.sha256").write_text(f"{sha256(output)}  {output.name}\n", encoding="ascii")
    print(json.dumps({"version": manifest["version"], "source_files": len(files), "source_bytes": output.stat().st_size, "tests": {k: validation[k]["passed"] for k in ("source", "packaged")}}))


if __name__ == "__main__":
    main()
