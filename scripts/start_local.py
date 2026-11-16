"""One command starts the local API, MCP services and durable worker. Ctrl+C stops them."""

import argparse
import json
import os
import subprocess
import sys
import time
from core.settings import ROOT, RUNTIME


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8000)
    p.add_argument("--test-models", action="store_true")
    a = p.parse_args()
    if a.test_models:
        os.environ["GIGBID_MODEL_MODE"] = "test"
        os.environ["GIGBID_CLIENT_MODE"] = "fixture"
    from scripts.bootstrap_local import main as bootstrap

    bootstrap()
    processes = []
    logs = []
    os.environ["GIGBID_MCP_TRANSPORT"] = "http"
    folder = RUNTIME / "logs"
    folder.mkdir(exist_ok=True)

    def launch(name, args, extra=None):
        log = (folder / (name + ".log")).open("a", encoding="utf-8")
        logs.append(log)
        processes.append(
            subprocess.Popen(
                [sys.executable, "-u", *args], cwd=ROOT, env=dict(os.environ, **(extra or {})), stdout=log, stderr=log
            )
        )

    for i, name in enumerate(["portfolio", "marketplace", "workspace"]):
        port = 8101 + i
        os.environ[name.upper() + "_MCP_URL"] = f"http://127.0.0.1:{port}/mcp"
        launch(name, ["-m", f"mcp_servers.{name}.server"], {"MCP_HTTP": "1", "MCP_PORT": str(port)})
    time.sleep(2)
    launch("worker", ["-m", "worker.runner"])
    launch(
        "api", ["-m", "uvicorn", "apps.api.main:app", "--host", "127.0.0.1", "--port", str(a.port), "--no-access-log"]
    )
    (RUNTIME / "processes.json").write_text(
        json.dumps([{"pid": x.pid, "command": x.args} for x in processes], indent=2)
    )
    print(
        f"GigBid: http://127.0.0.1:{a.port}\nPrivate reviewer login: {RUNTIME / 'reviewer-login.txt'}\nCtrl+C stops all GigBid services.",
        flush=True,
    )
    try:
        while all(x.poll() is None for x in processes):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
        for log in logs:
            log.close()


if __name__ == "__main__":
    main()
