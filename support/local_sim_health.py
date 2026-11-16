"""Visible marker service for Compose's local-simulator substitution."""

from fastapi import FastAPI
import uvicorn

app = FastAPI()


@app.get("/health")
def health():
    return {
        "mode": "local_synthetic_fixture",
        "official_gigsim": False,
        "implementation": "Marketplace MCP local_sim adapter; transactions share Postgres",
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8200, access_log=False)
