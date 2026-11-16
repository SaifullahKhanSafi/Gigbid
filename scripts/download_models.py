"""Download official Ollama manifests/blobs with hash verification, and the open reranker."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import requests
from core.settings import ROOT


def ollama_model(tag, root):
    name, version = tag.split(":")
    base = f"https://registry.ollama.ai/v2/library/{name}"
    r = requests.get(base + "/manifests/" + version, timeout=60)
    r.raise_for_status()
    manifest = r.json()
    for blob in [manifest["config"]] + manifest["layers"]:
        sha = blob["digest"].split(":")[1]
        path = root / "blobs" / ("sha256-" + sha)
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.stat().st_size == blob["size"]:
            print("Cached", tag, sha[:10], flush=True)
            continue
        temporary = path.with_suffix(".partial")
        print("Downloading", tag, blob["size"], "bytes", flush=True)
        with requests.get(base + "/blobs/" + blob["digest"], stream=True, timeout=120) as response:
            response.raise_for_status()
            hash_value = hashlib.sha256()
            with temporary.open("wb") as out:
                for chunk in response.iter_content(1024 * 1024):
                    out.write(chunk)
                    hash_value.update(chunk)
        if hash_value.hexdigest() != sha:
            raise ValueError("Model blob checksum mismatch")
        temporary.replace(path)
    dest = root / "manifests/registry.ollama.ai/library" / name / version
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(manifest))
    print("Installed", tag, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--ollama-root", type=Path, default=ROOT.parent / "runtime/ollama")
    p.add_argument("--reranker-only", action="store_true")
    args = p.parse_args()
    if not args.reranker_only:
        for tag in ["qwen2.5:0.5b", "qwen2.5:1.5b"]:
            ollama_model(tag, args.ollama_root)
    from huggingface_hub import snapshot_download

    snapshot_download(
        "cross-encoder/ms-marco-MiniLM-L6-v2",
        local_dir=os.getenv("GIGBID_RERANKER_PATH", str(ROOT / "models/reranker")),
        allow_patterns=["*.json", "*.safetensors", "vocab.txt", "README.md"],
    )
    print("Reranker installed", flush=True)
