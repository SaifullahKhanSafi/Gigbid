import json
from core.settings import ROOT
from apps.api.main import app

(ROOT / "openapi.json").write_text(json.dumps(app.openapi(), indent=2) + "\n")
