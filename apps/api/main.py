import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from apps.api.routers.routes import router
from core.settings import ROOT

app = FastAPI(
    title="GigBid API",
    version="0.1.0",
    description="Evidence-grounded freelancer copilot. Local synthetic simulator is explicitly labelled.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8000,http://127.0.0.1:8000"
    ).split(","),
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(router)

dist = ROOT / "apps/web/dist"
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        resolved = (dist / path).resolve()
        if resolved.is_relative_to(dist.resolve()) and resolved.is_file():
            return FileResponse(resolved)
        return FileResponse(dist / "index.html")
