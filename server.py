import json
import socket
import tempfile
import threading
import time
import uuid
from pathlib import Path

import state
from transcribe import transcribe_worker, _CONVERT_EXTS
from templates import MAIN_PAGE, viewer_page

PORT = 7860


def build_server():
    from fastapi import FastAPI, UploadFile, File
    from fastapi.responses import HTMLResponse, JSONResponse, Response
    from fastapi.middleware.cors import CORSMiddleware

    api = FastAPI()
    api.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )

    @api.get("/", response_class=HTMLResponse)
    async def index():
        return MAIN_PAGE

    @api.post("/transcribe")
    async def transcribe(file: UploadFile = File(...)):
        suffix = Path(file.filename).suffix or ".tmp"
        tmp    = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(await file.read())
        tmp.close()

        job_id           = str(uuid.uuid4())
        state.jobs[job_id] = {"status": "queued", "srt": None, "error": None}

        threading.Thread(
            target=transcribe_worker,
            args=(job_id, tmp.name),
            daemon=True,
        ).start()

        return JSONResponse({"job_id": job_id})

    @api.get("/status/{job_id}")
    async def status(job_id: str):
        job = state.jobs.get(job_id)
        if not job:
            return JSONResponse({"status": "not_found"}, status_code=404)
        return JSONResponse({"status": job["status"], "error": job.get("error")})

    @api.get("/view/{job_id}", response_class=HTMLResponse)
    async def view(job_id: str):
        job = state.jobs.get(job_id)
        if not job or job["status"] != "done":
            return HTMLResponse("<p>Not found</p>", status_code=404)
        return HTMLResponse(viewer_page(
            json.dumps(job_id),
            json.dumps(job["srt"]),
            json.dumps(job["srt_subtitle"]),
        ))

    @api.get("/raw/{job_id}")
    async def raw(job_id: str):
        job = state.jobs.get(job_id)
        if not job or job["status"] != "done":
            from fastapi.responses import Response as R
            return R(status_code=404)
        from fastapi.responses import Response as R
        return R(content=job["srt"].encode("utf-8"), media_type="text/plain; charset=utf-8")

    return api


def wait_for_port(port: int, timeout: float = 60.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def run_server() -> None:
    import uvicorn
    uvicorn.run(build_server(), host="127.0.0.1", port=PORT, log_level="error")
