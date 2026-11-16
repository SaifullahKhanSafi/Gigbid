"""Package only Git-indexed submission files; never runtime secrets or model weights."""

import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    names = (
        subprocess.check_output(["git", "-c", f"safe.directory={ROOT.as_posix()}", "ls-files", "-z"], cwd=ROOT)
        .decode()
        .split("\0")
    )
    target = ROOT / "output/GigBid_Submission.zip"
    target.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in filter(None, names):
            path = ROOT / name
            if name == ".env" or any(
                part in {"runtime", "node_modules", ".git", "models"} for part in Path(name).parts
            ):
                raise ValueError(f"Private or heavyweight content in index: {name}")
            if name.startswith(("data/raw/", "data/processed/")):
                raise ValueError(f"Unlicensed raw snapshot in index: {name}")
            if path.is_file():
                archive.write(path, "GigBid/" + name)
    print(
        json.dumps(
            {
                "created_at": datetime.now(timezone.utc).isoformat(),
                "archive": str(target),
                "bytes": target.stat().st_size,
                "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
