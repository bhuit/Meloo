import subprocess
from pathlib import Path
from .engine import ROOT, APP_DIR, CREATE_NO_WINDOW, ConversionError


def share(hwnd, paths):
    helper = APP_DIR / "tools/share/Zeste.Share.exe"
    if not helper.is_file(): helper = ROOT / "tools/share/Zeste.Share.exe"
    if not helper.is_file():
        raise ConversionError("Le module de partage Windows est absent. Reconstruis le module native/Share avant de l’utiliser.")
    subprocess.Popen([str(helper), *[str(Path(p).resolve()) for p in paths]], creationflags=CREATE_NO_WINDOW)
