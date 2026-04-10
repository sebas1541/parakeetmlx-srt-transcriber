# Shared mutable state — imported by server, transcribe, and jsapi modules
from pathlib import Path

jobs: dict = {}  # job_id -> {"status": str, "srt": str | None, ...}
window = None    # pywebview Window object (set in main.py after window creation)

DOCS_DIR = Path.home() / "Documents" / "SuperTranscribe"
DOCS_DIR.mkdir(parents=True, exist_ok=True)
