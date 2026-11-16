import json
import os
from pathlib import Path
import subprocess
from core.settings import ROOT, RUNTIME
from core.security import token

if __name__ == "__main__":
    config = RUNTIME / "inspector-config.json"
    config.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "GigBid Portfolio": {
                        "type": "streamable-http",
                        "url": "http://127.0.0.1:8101/mcp",
                        "headers": {"Authorization": "Bearer " + token("inspector-owner", "mcp", ttl=3600)},
                        "protocolEra": "legacy",
                    }
                }
            }
        )
    )
    package = next(
        Path(os.getenv("LOCALAPPDATA"))
        .joinpath("npm-cache/_npx")
        .glob("*/node_modules/@modelcontextprotocol/inspector/clients/launcher/build/index.js")
    )
    log = (RUNTIME / "logs/inspector.log").open("w")
    proc = subprocess.Popen(
        ["node", str(package), "--web", "--config", str(config), "--server", "GigBid Portfolio"],
        cwd=ROOT,
        env=dict(os.environ, MCP_AUTO_OPEN_ENABLED="false"),
        stdout=log,
        stderr=log,
    )
    (RUNTIME / "inspector.pid").write_text(str(proc.pid))
    print("Official Inspector started; connection details are private in runtime/logs/inspector.log.")
