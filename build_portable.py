"""Build the Windows x64 portable app using only installed/local dependencies.

Run with .venv/Scripts/python.exe build_portable.py. No downloads or installations.
An existing generated portable is archived; an unknown destination is refused.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
VERSION = "0.4.2"
MARKER = ".zeste-generated.json"
PRODUCT = "zeste-windows-portable"


def source_hashes():
    files = [ROOT / "main.py", *sorted((ROOT / "zeste").glob("*.py"))]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def require_local(path: Path, parent: Path):
    resolved = path.resolve()
    if not resolved.is_relative_to(parent.resolve()) or resolved == parent.resolve():
        raise RuntimeError(f"Unsafe generated path: {path}")
    if path.is_symlink() or path.is_junction():
        raise RuntimeError(f"Generated path must not be a link: {path}")
    return resolved


def prepare_generated_directory(path: Path, parent: Path):
    path = require_local(path, parent)
    if path.exists():
        marker = path / MARKER
        if not marker.is_file() or json.loads(marker.read_text(encoding="utf8")).get("product") != PRODUCT:
            raise RuntimeError(f"Preserving unrecognised directory: {path}. Choose an empty build location.")
    else:
        path.mkdir(parents=True)
        (path / MARKER).write_text(json.dumps({"product": PRODUCT, "kind": "build"}), encoding="utf8")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-tools", action="store_true", help="Developer-only build without bundled LibreOffice/share")
    args = parser.parse_args()
    if os.name != "nt" or sys.maxsize < 2**32:
        raise RuntimeError("Build requires 64-bit Windows and 64-bit Python.")
    importlib.metadata.version("pyinstaller")
    for source in [ROOT / "tools/LibreOffice/program/soffice.exe", ROOT / "tools/share/Zeste.Share.exe"]:
        if not args.skip_tools and not source.is_file(): raise RuntimeError(f"Missing local engine: {source}")

    work = prepare_generated_directory(ROOT / "build", ROOT)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)
    require_local(dist, ROOT)
    output = require_local(dist / "Zeste", dist)
    if output.exists():
        marker = output / MARKER
        if not marker.is_file() or json.loads(marker.read_text(encoding="utf8")).get("product") != PRODUCT:
            raise RuntimeError(f"Preserving unrecognised existing portable: {output}")
        archive = require_local(dist / ("Zeste.previous-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f")), dist)
        output.rename(archive)
        print(f"Previous generated portable preserved at {archive}", flush=True)

    assets = ROOT / "assets"
    assets.mkdir(exist_ok=True)
    icon = assets / "zeste.ico"
    env = dict(os.environ)
    for directory in [work / "tmp", work / "cache", work / "icon-profile"]: directory.mkdir(exist_ok=True)
    # Binary dependency resolution must not collect DLLs from unrelated apps
    # present in a developer's PATH (notably Poppler's incompatible ICU DLL).
    clean_path = [Path(sys.executable).parent, Path(sys.base_prefix), Path(os.environ.get("WINDIR", "C:/Windows")) / "System32", Path(os.environ.get("WINDIR", "C:/Windows"))]
    env.update(TEMP=str(work / "tmp"), TMP=str(work / "tmp"), PYINSTALLER_CONFIG_DIR=str(work / "cache"), PATH=os.pathsep.join(map(str, clean_path)))
    if not icon.exists():
        icon_env = {**env, "QT_QPA_PLATFORM": "offscreen", "ZESTE_CONFIG_DIR": str(work / "icon-profile")}
        code = "from PySide6.QtWidgets import QApplication; from zeste.ui import logo; from PIL import Image; import sys; app=QApplication([]); logo(256).pixmap(256,256).save(sys.argv[1]); Image.open(sys.argv[1]).save(sys.argv[2], sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])"
        subprocess.run([sys.executable, "-c", code, str(assets / "zeste.png"), str(icon)], cwd=ROOT, env=icon_env, check=True)

    runtime_hook = work / "runtime_windowed.py"
    runtime_hook.write_text('import os, sys\nfor name in ("stdout", "stderr"):\n    if getattr(sys, name) is None:\n        setattr(sys, name, open(os.devnull, "w", encoding="utf8"))\n', encoding="utf8")
    version_file = work / "version_info.txt"
    version_file.write_text('''VSVersionInfo(ffi=FixedFileInfo(filevers=(0,4,2,0),prodvers=(0,4,2,0),mask=0x3f,flags=0x0,OS=0x40004,fileType=0x1,subtype=0x0,date=(0,0)), kids=[StringFileInfo([StringTable('040c04b0', [StringStruct('FileDescription','Meloo - convertisseur local Windows'), StringStruct('FileVersion','0.4.2'), StringStruct('InternalName','Meloo'), StringStruct('OriginalFilename','Meloo.exe'), StringStruct('ProductName','Meloo'), StringStruct('ProductVersion','0.4.2')])]), VarFileInfo([VarStruct('Translation',[1036,1200])])])''', encoding="utf8")
    spec = work / "Zeste.spec"
    spec_source = r'''
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata
root = Path(@ROOT@)
data = [(str(root / 'assets'), 'assets')]
binaries = []
hidden = ['PySide6.QtCore','PySide6.QtGui','PySide6.QtWidgets','PySide6.QtSvg','PySide6.QtNetwork','imageio_ffmpeg.binaries','_pillow_heif','pillow_heif.HeifImagePlugin','pymupdf._extra','pymupdf._features','pymupdf._mupdf','pymupdf._tgif','pymupdf.table','fitz','cv2','numpy','rarfile']
for package in ['pillow_heif','pdf2docx','py7zr','ebooklib','docx','pptx','openpyxl']:
    hidden += collect_submodules(package, filter=lambda name: '.tests' not in name and not name.endswith('.test'))
for package in ['imageio_ffmpeg','pypandoc','pillow_heif','pymupdf','docx','pptx','ebooklib']:
    data += collect_data_files(package, excludes=['**/tests/**','**/__pycache__/**'])
    binaries += collect_dynamic_libs(package)
for package in ['Pillow','pillow-heif','PyMuPDF','imageio-ffmpeg','python-docx','python-pptx','openpyxl','EbookLib','pdf2docx','py7zr','pypandoc-binary']:
    data += copy_metadata(package)
excluded = ['PySide6.QtWebEngineCore','PySide6.QtWebEngineWidgets','PySide6.QtWebEngineQuick','PySide6.QtQml','PySide6.QtQuick','PySide6.QtQuickWidgets','PySide6.QtQuickControls2','PySide6.Qt3DCore','PySide6.Qt3DRender','PySide6.Qt3DExtras','PySide6.Qt3DInput','PySide6.Qt3DLogic','PySide6.Qt3DAnimation','PySide6.QtCharts','PySide6.QtPdf','PySide6.QtPdfWidgets','PySide6.QtMultimedia','PySide6.QtMultimediaWidgets','PySide6.QtDesigner','PySide6.QtTest','PySide6.QtOpenGLWidgets','onnxruntime','pymupdf4llm','pymupdf_layout','winrt','pytest','tests','tkinter','IPython','matplotlib','scipy','pandas','PyQt5','PyQt6','PySide2','setuptools','pip']
a = Analysis([str(root / 'main.py')], pathex=[str(root)], binaries=binaries, datas=data, hiddenimports=hidden, hookspath=[], hooksconfig={}, runtime_hooks=[str(root/'build/runtime_windowed.py')], excludes=excluded, noarchive=False, optimize=0)
# QtGui automatically collects its virtual-keyboard plugin, which drags in
# QML/Quick even though this application exclusively uses Qt Widgets.
def unused_qt(entry):
    name = Path(entry[0]).name.lower()
    return name.startswith(('qt6qml','qt6quick','qt6virtualkeyboard')) or name == 'qtvirtualkeyboardplugin.dll'
a.binaries = [entry for entry in a.binaries if not unused_qt(entry)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Meloo', debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False, disable_windowed_traceback=False, icon=str(root/'assets/zeste.ico'), version=str(root/'build/version_info.txt'), uac_admin=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Zeste')
'''.replace("@ROOT@", repr(str(ROOT)))
    spec.write_text(spec_source, encoding="utf8")
    before = source_hashes()
    log_path = work / "build.log"
    cmd = [sys.executable, "-m", "PyInstaller", "--clean", "--noconfirm", "--distpath", str(dist), "--workpath", str(work / "pyinstaller"), str(spec)]
    print(f"Building Meloo {VERSION}. Log: {log_path}", flush=True)
    with log_path.open("w", encoding="utf8") as log:
        result = subprocess.run(cmd, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError(f"PyInstaller failed ({result.returncode}); inspect {log_path}")
    if before != source_hashes():
        raise RuntimeError("Sources changed during build: rebuild before delivery.")
    if not (output / "Meloo.exe").is_file(): raise RuntimeError("No executable generated.")
    # Compatibility entry keeps existing shortcuts working with the same IPC/profile.
    shutil.copy2(output / "Meloo.exe", output / "Zeste.exe")
    (output / MARKER).write_text(json.dumps({"product": PRODUCT, "version": VERSION, "kind": "portable", "created_utc": datetime.now(timezone.utc).isoformat(), "source_sha256": before}, indent=2), encoding="utf8")
    if not args.skip_tools:
        print("Copying private LibreOffice and Windows share helper (no installer MSI).", flush=True)
        shutil.copytree(ROOT / "tools/LibreOffice", output / "tools/LibreOffice", ignore=lambda directory, names: [name for name in names if name == "__pycache__" or name.startswith(".~lock.") or name.lower().endswith((".msi", ".pdb", ".dmp", ".pyc", ".log"))])
        (output / "tools/share").mkdir(parents=True)
        shutil.copy2(ROOT / "tools/share/Zeste.Share.exe", output / "tools/share/Zeste.Share.exe")
    shutil.copy2(ROOT / "Installer-Zeste.ps1", output / "Installer-Zeste.ps1")
    shutil.copy2(ROOT / "Installer-Meloo.ps1", output / "Installer-Meloo.ps1")
    print(f"Portable ready: {output / 'Meloo.exe'}", flush=True)
    print("README, source and licensing notices must be added before redistribution.", flush=True)
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as error:
        print(f"Build stopped: {error}", file=sys.stderr)
        raise SystemExit(1)
