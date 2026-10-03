"""Assemble Next standalone files and third-party notices for PyInstaller."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser()
parser.add_argument("--node", required=True, type=Path)
args = parser.parse_args()
stage = root / "build" / "windows" / "stage"
assert stage.resolve().is_relative_to(root / "build" / "windows")
if stage.exists():
    shutil.rmtree(stage)
stage.mkdir(parents=True)
frontend = root / "frontend"
if not (frontend / ".next" / "standalone" / "server.js").is_file():
    raise RuntimeError("Build the desktop frontend first (DISPROT_DESKTOP_BUILD=1).")
shutil.copytree(frontend / ".next" / "standalone", stage / "frontend")
shutil.copytree(frontend / ".next" / "static", stage / "frontend" / ".next" / "static", dirs_exist_ok=True)
if (frontend / "public").exists():
    shutil.copytree(frontend / "public", stage / "frontend" / "public", dirs_exist_ok=True)
shutil.copy2(args.node, stage / "node.exe")
licenses = stage / "licenses"
licenses.mkdir()
node_version = subprocess.check_output([str(args.node), "--version"], text=True).strip()
urllib.request.urlretrieve(f"https://raw.githubusercontent.com/nodejs/node/{node_version}/LICENSE", licenses / "Node-LICENSE.txt")
python_license = Path(sys.base_prefix) / "LICENSE.txt"
if python_license.exists():
    shutil.copy2(python_license, licenses / "Python-LICENSE.txt")
for distribution in importlib.metadata.distributions():
    for file in distribution.files or []:
        if any(word in file.name.lower() for word in ("license", "copying", "notice")):
            source = Path(distribution.locate_file(file))
            if source.is_file():
                target = licenses / "python" / distribution.metadata["Name"] / str(file)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, target)
for package_file in (stage / "frontend" / "node_modules").rglob("package.json"):
    try:
        info = json.loads(package_file.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        continue
    name = info.get("name")
    if not name:
        continue
    original = frontend / "node_modules" / name
    for source in original.glob("*"):
        if source.is_file() and any(word in source.name.lower() for word in ("license", "copying", "notice")):
            target = licenses / "node" / name / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
for source in Path(sys.base_prefix).rglob("license.terms"):
    target = licenses / "tcl-tk" / source.parent.name / source.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
manifest = {
    "version": "0.1.0", "python": sys.version, "node": node_version,
    "git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
    "working_tree_modified": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root, text=True).strip()),
    "packages": {dist.metadata["Name"]: dist.version for dist in importlib.metadata.distributions()},
}
(licenses / "build-info.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"Runtime staged at {stage}")
