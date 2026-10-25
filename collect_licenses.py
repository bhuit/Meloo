"""Collect installed distribution notices and an auditable build inventory."""
import importlib.metadata as metadata
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

root=Path(__file__).resolve().parent
out=root/"licenses/python-environment"
out.mkdir(parents=True,exist_ok=True)
inventory=[]
for dist in sorted(metadata.distributions(),key=lambda d:d.metadata.get("Name","").lower()):
    name=dist.metadata.get("Name","")
    if not name: continue
    item={"name":name,"version":dist.version,"license":dist.metadata.get("License-Expression") or dist.metadata.get("License"),"project_urls":dist.metadata.get_all("Project-URL",[]),"homepage":dist.metadata.get("Home-page"),"notice_files":[]}
    for entry in dist.files or []:
        if not any(word in Path(entry).name.lower() for word in ["license","licence","copying","notice"]): continue
        src=Path(dist.locate_file(entry))
        if not src.is_file() or src.stat().st_size>5_000_000: continue
        if src.suffix.lower() in {".pyc",".pyd",".dll",".so",".png"}: continue
        target=out/(name+"-"+dist.version)/Path(entry).name
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists() and target.read_bytes()!=src.read_bytes():
            import hashlib
            target=target.with_name(hashlib.sha256(str(entry).encode()).hexdigest()[:8]+"-"+target.name)
        shutil.copy2(src,target)
        item["notice_files"].append(str(target.relative_to(root)).replace("\\","/"))
    inventory.append(item)
(out/"inventory.json").write_text(json.dumps({"scope":"Build environment; excludes in build_portable.py determine the smaller runtime set.","packages":inventory},ensure_ascii=False,indent=2),encoding="utf-8")
python_license=Path(sys.base_prefix)/"LICENSE.txt"
if python_license.is_file(): shutil.copy2(python_license,root/"licenses/Python-LICENSE.txt")
dotnet_license=Path(os.environ.get("ProgramFiles",r"C:\Program Files"))/"dotnet/LICENSE.txt"
if dotnet_license.is_file(): shutil.copy2(dotnet_license,root/"licenses/Dotnet-LICENSE.txt")
import imageio_ffmpeg
r=subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),"-L"],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=30,creationflags=0x08000000 if os.name=="nt" else 0)
(root/"licenses/FFmpeg-build-license.txt").write_text(r.stdout+"\n"+r.stderr,encoding="utf-8")
print(json.dumps({"packages":len(inventory),"notice_files":sum(len(x['notice_files']) for x in inventory),"ffmpeg_exit":r.returncode}))
