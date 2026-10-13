"""Check the reviewable repository file set and local Markdown links."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from maxvell.validation import privacy_categories

SKIP={".git","__pycache__",".venv","build","dist","work","_internal"}
SUFFIXES={".py",".md",".txt",".json",".sql",".toml",".sqlite",".svg"}
NAMES={".gitattributes",".gitignore","LICENSE"}
EXAMPLE_SUFFIXES={".v",".tcl"}

def check():
    failures=[];files=[];bytes_total=0
    for path in sorted(ROOT.rglob("*")):
        relative=path.relative_to(ROOT)
        if any(p in SKIP or p.endswith(".egg-info") for p in relative.parts) or not path.is_file():continue
        name=relative.as_posix();raw=path.read_bytes();bytes_total+=len(raw)
        files.append({"path":name,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()})
        example_source=relative.parts[:2]==("examples","quartus_control") and path.suffix in EXAMPLE_SUFFIXES
        if path.suffix not in SUFFIXES and path.name not in NAMES and not example_source:failures.append("unexpected file: "+name)
        if privacy_categories(name):failures.append("filename privacy: "+name)
        if path.suffix==".sqlite":
            # Raw identifying-marker check complements decoded table/model scans.
            for marker in (b"C:"+b"\\Users\\",b"/home/",b"/Users/",b"conversation_id",b"thread_id",b"session_id"):
                if marker.lower() in raw.lower():failures.append("raw database identifying marker")
            continue
        text=raw.decode("utf-8")
        if privacy_categories(text):failures.append("text privacy: "+name)
        if path.suffix==".md":
            for link in re.findall(r"\[[^\]]*\]\(([^)]+)\)",text):
                if link.startswith(("https://","http://","#")):continue
                target=link.split("#",1)[0]
                resolved=(path.parent/target).resolve()
                if not resolved.is_relative_to(ROOT) or not resolved.is_file():failures.append("broken/local escaping link: "+name)
    git=subprocess.run(["git","-C",str(ROOT),"ls-files","-z"],capture_output=True,check=True).stdout
    tracked=set(git.decode().rstrip("\0").split("\0")) if git else set()
    if tracked and tracked!={f["path"] for f in files}:failures.append("tracked/file inventory differs")
    return {"format":"maxvell.publication_check.v1","status":"passed" if not failures else "failed","failures":sorted(set(failures)),"files":len(files),"bytes":bytes_total,"tracked_files":len(tracked),"inventory":files,"privacy_scope":"heuristic file/text/raw identifying markers; model/database scan is maxvell validate"}

if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--out",type=Path);args=parser.parse_args()
    result=check()
    if args.out:
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(result,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="inventory"},sort_keys=True))
    raise SystemExit(0 if result["status"]=="passed" else 1)
