"""Repository invariants; findings are concrete, not a promise of perfect secret detection."""

from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def run():
    errors = []
    tracked = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    files = (
        [ROOT / p for p in tracked.stdout.splitlines()]
        if tracked.returncode == 0 and tracked.stdout
        else [
            p
            for p in ROOT.rglob("*")
            if p.is_file()
            and p.name != ".env"
            and not any(
                x in p.parts
                for x in [
                    ".git",
                    "node_modules",
                    "runtime",
                    "models",
                    "dist",
                    "test-results",
                    "playwright-report",
                    "__pycache__",
                ]
            )
        ]
    )
    for path in files:
        if path.name == ".env":
            errors.append("Private .env file would be committed")
        if path.suffix not in (".py", ".md", ".yaml", ".yml", ".toml", ".json", ".ts", ".tsx", ".txt"):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if re.search(
            r"(?:ghp_[A-Za-z0-9]{30,}|sk-proj-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----)", text
        ):
            errors.append(f"Possible secret in {path.relative_to(ROOT)}")
    official = ROOT / "gigsim"
    if list(official.glob("*.py")):
        errors.append("Official gigsim directory must not contain our local mock")
    if errors:
        raise SystemExit("\n".join(errors))
    print("Repository invariants passed (best-effort secret scan, reserved GigSim directory).")


if __name__ == "__main__":
    run()
