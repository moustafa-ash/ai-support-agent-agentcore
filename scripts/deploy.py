"""Pass private resource settings to the Python Starter Toolkit deployment."""
import json
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parents[1] / "starter"
settings = json.loads((root / "runtime_settings.json").read_text())
command = ["agentcore", "deploy"]
for key in ("REGION", "GATEWAY_URL", "KB_ID", "MEMORY_ID"):
    if not settings.get(key):
        sys.exit(f"Missing {key} in private runtime_settings.json")
    command += ["--env", f"{key}={settings[key]}"]
command += ["--env", "PROJECT_EVIDENCE=true"]
sys.exit(subprocess.run(command, cwd=root).returncode)
