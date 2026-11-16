import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["GIGBID_MODEL_MODE"] = "test"
os.environ["GIGBID_CLIENT_MODE"] = "fixture"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["GIGBID_RUNTIME"] = tempfile.mkdtemp(prefix="gigbid-tests-")
os.environ["GIGBID_SECRET"] = "test-only-secret-key-with-more-than-32-characters"
os.environ.pop("DATABASE_URL", None)
os.environ.pop("REDIS_URL", None)
