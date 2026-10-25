"""Mirror official engine source archives and record checksums for a release."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    ("Qt", "6.12.0", "https://download.qt.io/archive/qt/6.12/6.12.0/single/qt-everywhere-src-6.12.0.tar.xz"),
    ("PySide/Shiboken", "6.12.0", "https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.12.0-src/pyside-setup-everywhere-src-6.12.0.tar.xz"),
    *[("LibreOffice " + kind, "26.8.1.1", f"https://download.documentfoundation.org/libreoffice/src/26.8.1/libreoffice{suffix}-26.8.1.1.tar.xz") for kind, suffix in [("core", ""), ("dictionaries", "-dictionaries"), ("help", "-help"), ("translations", "-translations")]],
    ("FFmpeg", "b08d7969c5 (Gyan 7.1)", "https://github.com/FFmpeg/FFmpeg/archive/b08d7969c5.tar.gz"),
    ("Pandoc", "3.9", "https://github.com/jgm/pandoc/archive/refs/tags/3.9.tar.gz"),
    ("pypandoc", "1.17", "https://github.com/JessicaTegner/pypandoc/archive/refs/tags/v1.17.tar.gz"),
    ("CPython", "3.12.10", "https://www.python.org/ftp/python/3.12.10/Python-3.12.10.tar.xz"),
    ("MuPDF", "1.28.5 (PyMuPDF 2.0 build recipe)", "https://mupdf.com/downloads/archive/mupdf-1.28.5-source.tar.gz"),
    ("libheif", "1.23.6", "https://github.com/strukturag/libheif/releases/download/v1.23.6/libheif-1.23.6.tar.gz"),
    ("libde265", "1.1.3", "https://github.com/strukturag/libde265/releases/download/v1.1.3/libde265-1.1.3.tar.gz"),
    ("x265 for pillow-heif", "4.3", "https://github.com/Multicorewareinc/x265/releases/download/4.3/x265_4.3.tar.gz"),
]


def fetch(item):
    name, version, url = item
    directory = ROOT / "build/third-party-sources/native"
    directory.mkdir(parents=True, exist_ok=True)
    filename = url.rsplit("/", 1)[1]
    if filename in ("3.9.tar.gz", "v1.17.tar.gz", "b08d7969c5.tar.gz"):
        filename = name.lower() + "-" + filename
    output = directory / filename
    record = {"component": name, "version": version, "url": url, "filename": filename}
    try:
        if not output.exists():
            request = urllib.request.Request(url, headers={"User-Agent": "Meloo-source-release/0.4.2"})
            with urllib.request.urlopen(request, timeout=120) as response, output.with_suffix(output.suffix + ".partial").open("wb") as target:
                while block := response.read(1024 * 1024):
                    target.write(block)
            output.with_suffix(output.suffix + ".partial").rename(output)
        with output.open("rb") as stream:
            record.update(sha256=hashlib.file_digest(stream, "sha256").hexdigest(), bytes=output.stat().st_size, status="downloaded")
    except Exception as error:
        record.update(status="failed", error=type(error).__name__)
    print(name + ": " + record["status"], flush=True)
    return record


def main():
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(fetch, SOURCES))
    (ROOT / "licenses/native-source-catalog.json").write_text(json.dumps({"archives": records}, indent=2), encoding="utf-8")
    if any(item["status"] != "downloaded" for item in records):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
