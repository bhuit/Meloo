"""Scan publishable files for local identities/secrets without printing matches.

Private values come from the environment or command line; none are stored in
the repository. Third-party author attributions are intentionally preserved.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import types
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SECRET = re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----\r?\n(?:[A-Za-z0-9+/]{40,}={0,2}\r?\n){2,})")


def needles():
    values = json.loads(os.environ.get("MELOO_PRIVATE_STRINGS", "[]"))
    username = os.environ.get("USERNAME", "")
    if username:
        values.extend([username, username.split("-")[0]])
    return [value.lower().encode(encoding) for value in values if len(value) >= 4 for encoding in ("utf-8", "utf-16-le")]


def flags(data, private):
    result = []
    lowered = data.lower()
    if any(value in lowered for value in private):
        result.append("private_identity")
    if SECRET.search(data):
        result.append("credential_pattern")
    return result


def scan_file(path, label, private):
    hits = []
    previous = b""
    with path.open("rb") as source:
        while block := source.read(2 * 1024 * 1024):
            for category in flags(previous + block, private):
                entry = {"file": label, "category": category}
                if entry not in hits:
                    hits.append(entry)
            previous = block[-1024:]
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            for item in archive.infolist():
                if item.is_dir():
                    continue
                for category in flags(archive.read(item), private):
                    hits.append({"file": label + "!" + item.filename, "category": category})
    return hits


def code_bytes(code):
    yield code.co_filename.encode("utf-8")
    for item in code.co_consts:
        if isinstance(item, types.CodeType):
            yield from code_bytes(item)
        elif isinstance(item, str):
            yield item.encode("utf-8", errors="surrogatepass")
        elif isinstance(item, bytes):
            yield item


def scan_pyinstaller(executable, private):
    from PyInstaller.archive.readers import CArchiveReader
    archive = CArchiveReader(str(executable))
    hits = []
    for name, entry in archive.toc.items():
        if entry[-1] != "z":
            continue
        pyz = archive.open_embedded_archive(name)
        for module in pyz.toc:
            code = pyz.extract(module)
            if isinstance(code, types.CodeType):
                for data in code_bytes(code):
                    if flags(data, private):
                        hits.append({"file": executable.name + "!" + module, "category": "embedded_private_data"})
                        break
    return hits


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--payload", type=Path)
    parser.add_argument("--archive", type=Path, action="append", default=[])
    args = parser.parse_args()
    private = needles()
    result = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT, capture_output=True, check=True)
    names = sorted(set(result.stdout.decode("utf-8").split("\0")) - {""})
    hits = []
    for name in names:
        path = ROOT / name
        if path.is_file():
            hits.extend(scan_file(path, name, private))
    payload_count = 0
    if args.payload:
        for path in args.payload.rglob("*"):
            if path.is_file():
                payload_count += 1
                hits.extend(scan_file(path, "payload/" + path.relative_to(args.payload).as_posix(), private))
        hits.extend(scan_pyinstaller(args.payload / "Meloo.exe", private))
    for archive in args.archive:
        hits.extend(scan_file(archive, archive.name, private))
    report = {"source_files_scanned": len(names), "payload_files_scanned": payload_count, "findings": hits,
              "scope": "Known local identities, credential patterns and embedded Python code; not a guarantee against every possible secret."}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return bool(hits)


if __name__ == "__main__":
    raise SystemExit(main())
