# Shared mutable state — imported by server, transcribe, and jsapi modules
jobs: dict = {}  # job_id -> {"status": str, "srt": str | None, ...}
window = None    # pywebview Window object (set in main.py after window creation)
