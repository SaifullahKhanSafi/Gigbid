"""Stop only recorded launcher children whose working directory is this project."""

import json
from core.settings import ROOT, RUNTIME
import psutil

if __name__ == "__main__":
    path = RUNTIME / "processes.json"
    if not path.exists():
        raise SystemExit("No recorded GigBid processes")
    for entry in reversed(json.loads(path.read_text())):
        try:
            process = psutil.Process(entry["pid"])
            if str(ROOT).casefold() != str(process.cwd()).casefold():
                continue
            if not any(
                x in " ".join(process.cmdline()) for x in ["mcp_servers.", "worker.runner", "apps.api.main:app"]
            ):
                continue
            for child in reversed(process.children(recursive=True)):
                child.terminate()
            process.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    print("Stopped recorded GigBid service processes.")
