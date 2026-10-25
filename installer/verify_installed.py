"""Run representative existing conversion checks against the installed binaries."""
import importlib.util
import json
from pathlib import Path
import sys
import traceback

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("packaged_qa", root / "tests/test_packaged.py")
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)
qa.EXE = Path(sys.argv[1]) / "Meloo.exe"
output = Path(sys.argv[2])
output.mkdir(parents=True, exist_ok=True)
results = []
checks = [
    ("smoke", qa.test_packaged_smoke_has_real_zero_exit),
    ("image_jpg", lambda p: qa.test_packaged_image_codecs(p, "jpg")),
    ("image_heic", lambda p: qa.test_packaged_image_codecs(p, "heic")),
    ("office_pdf", qa.test_packaged_docx_to_pdf_uses_private_office),
    ("audio_mp3", qa.test_packaged_audio_uses_private_ffmpeg),
]

def zip_check(folder):
    import zipfile
    source = folder / "document.txt"
    source.write_text("Mes données à conserver", encoding="utf8")
    result = qa.convert(folder, source, "create_zip")[0]
    with zipfile.ZipFile(result) as archive:
        assert archive.read(source.name) == source.read_bytes()

checks.append(("create_zip", zip_check))
for name, check in checks:
    folder = output / name
    folder.mkdir()
    try:
        check(folder)
        results.append({"name": name, "passed": True})
    except Exception:
        results.append({"name": name, "passed": False, "error": traceback.format_exc()})
(output / "report.json").write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf8")
sys.exit(0 if all(r["passed"] for r in results) else 1)
