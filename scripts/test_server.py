"""Dedicated browser-test server and separate test-double worker; never changes live data."""

import os
import subprocess
import sys
import tempfile

os.environ["GIGBID_MODEL_MODE"] = "test"
os.environ["GIGBID_CLIENT_MODE"] = "fixture"
os.environ["GIGBID_RUNTIME"] = tempfile.mkdtemp(prefix="gigbid-browser-tests-")
os.environ["GIGBID_SECRET"] = "browser-test-secret-only-longer-than-32-chars"
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ.pop("DATABASE_URL", None)
os.environ.pop("REDIS_URL", None)
if __name__ == "__main__":
    import time

    servers = []
    os.environ["GIGBID_MCP_TRANSPORT"] = "http"
    for i, name in enumerate(["portfolio", "marketplace", "workspace"]):
        port = 8111 + i
        os.environ[name.upper() + "_MCP_URL"] = f"http://127.0.0.1:{port}/mcp"
        env = dict(os.environ, MCP_HTTP="1", MCP_PORT=str(port))
        servers.append(subprocess.Popen([sys.executable, "-m", f"mcp_servers.{name}.server"], env=env))
    time.sleep(2)
    worker = subprocess.Popen([sys.executable, "-m", "worker.runner"], env=os.environ.copy())
    try:
        import uvicorn

        uvicorn.run("apps.api.main:app", host="127.0.0.1", port=8001, log_level="warning")
    finally:
        worker.terminate()
        worker.wait(timeout=10)
        for server in servers:
            server.terminate()
            server.wait(timeout=10)
