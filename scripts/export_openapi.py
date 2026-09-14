import json
from pathlib import Path
from backend.app import app
Path("backend/openapi.json").write_text(json.dumps(app.openapi(),indent=2)+"\n")
