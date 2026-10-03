"""Package only tracked, reviewed project files; never include private metadata."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

root = Path(__file__).resolve().parents[1]
files = subprocess.check_output(["git", "ls-files", "-z"], cwd=root).decode().split("\0")
files = [p for p in files if p and (root / p).is_file()]
for name in files:
    if any(part in {"private", ".aws", ".cache"} or part.startswith(".venv") for part in Path(name).parts):
        raise RuntimeError("Private path is tracked; refuse to package")
    if Path(name).name in {"runtime_settings.json", "infrastructure-state.json"}:
        raise RuntimeError("Deployment metadata is tracked; refuse to package")
manifest = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in files}
with zipfile.ZipFile(root / "submission.zip", "w", zipfile.ZIP_DEFLATED) as bundle:
    for name in files:
        bundle.write(root / name, name)
    bundle.writestr("submission-manifest.json", json.dumps(manifest, indent=2))
print("submission.zip created from tracked files; review rubric status before submitting.")
