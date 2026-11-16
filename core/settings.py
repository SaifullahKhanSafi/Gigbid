"""Configuration is resolved relative to the project, never the caller's cwd."""

from pathlib import Path
import os
import secrets
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
RUNTIME = Path(os.getenv("GIGBID_RUNTIME", str(ROOT / "runtime"))).resolve()
RUNTIME.mkdir(parents=True, exist_ok=True)


def config():
    value = yaml.safe_load((ROOT / "agent/config.yaml").read_text())
    value["models"]["profile"] = os.getenv("GIGBID_MODEL_PROFILE", value["models"]["profile"])
    value["marketplace"]["mode"] = os.getenv("GIGBID_MARKETPLACE", value["marketplace"]["mode"])
    return value


def policy():
    return yaml.safe_load((ROOT / "data/policy_pack/local_policy.yaml").read_text())


def secret():
    supplied = os.getenv("GIGBID_SECRET")
    if supplied:
        if len(supplied) < 32 or supplied.startswith("replace-"):
            raise RuntimeError("GIGBID_SECRET must be random and at least 32 characters")
        return supplied
    if os.getenv("GIGBID_ENV") == "production":
        raise RuntimeError("GIGBID_SECRET is required in production")
    path = RUNTIME / "development.secret"
    if not path.exists():
        try:
            with path.open("x") as f:
                f.write(secrets.token_hex(32))
        except FileExistsError:
            pass
    return path.read_text().strip()
