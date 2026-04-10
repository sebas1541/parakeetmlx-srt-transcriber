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
from captions import build_captions, build_fcpxml, FRAMERATES

PORT = 7860


def build_server():
    from fastapi import FastAPI, UploadFile, File, Request, Form
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
    async def transcribe(file: UploadFile = File(...), model: str = Form("whisper")):
        suffix = Path(file.filename).suffix or ".tmp"
        tmp    = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(await file.read())
        tmp.close()

        job_id           = str(uuid.uuid4())
        state.jobs[job_id] = {
            "status": "queued", "srt": None, "error": None, "progress": None,
            "original_filename": file.filename or "audio",
        }

        threading.Thread(
            target=transcribe_worker,
            args=(job_id, tmp.name, model),
            daemon=True,
        ).start()

        return JSONResponse({"job_id": job_id})

    @api.get("/status/{job_id}")
    async def status(job_id: str):
        job = state.jobs.get(job_id)
        if not job:
            return JSONResponse({"status": "not_found"}, status_code=404)
        return JSONResponse({
            "status":          job["status"],
            "error":           job.get("error"),
            "progress":        job.get("progress"),
            "auto_save_path":  job.get("auto_save_path"),
            "original_filename": job.get("original_filename"),
        })

    @api.get("/history")
    async def history():
        hist_file = state.DOCS_DIR / "history.json"
        if not hist_file.exists():
            return JSONResponse([])
        try:
            data = json.loads(hist_file.read_text(encoding="utf-8"))
            return JSONResponse(data)
        except Exception:
            return JSONResponse([])

    @api.get("/srt/{job_id}")
    async def get_srt(job_id: str):
        """Return SRT + subtitle SRT for a job. Falls back to disk if not in memory."""
        job = state.jobs.get(job_id)
        if job and job.get("srt"):
            return JSONResponse({
                "srt":          job["srt"],
                "srt_subtitle": job.get("srt_subtitle", ""),
                "filename":     job.get("original_filename", ""),
                "auto_save_path": job.get("auto_save_path", ""),
            })
        # Try to load from history on disk
        hist_file = state.DOCS_DIR / "history.json"
        if hist_file.exists():
            try:
                history = json.loads(hist_file.read_text(encoding="utf-8"))
                for rec in history:
                    if rec.get("id") == job_id:
                        srt_path = Path(rec["srt_path"])
                        if srt_path.exists():
                            srt_text = srt_path.read_text(encoding="utf-8")
                            # Inject into state.jobs so jsapi methods can work
                            state.jobs[job_id] = {
                                "status":            "done",
                                "srt":               srt_text,
                                "srt_subtitle":      "",
                                "sentences":         [],
                                "original_filename": rec.get("filename", ""),
                                "auto_save_path":    rec.get("srt_path", ""),
                                "error":             None,
                                "progress":          None,
                            }
                            return JSONResponse({
                                "srt":            srt_text,
                                "srt_subtitle":   "",
                                "filename":       rec.get("filename", ""),
                                "auto_save_path": rec.get("srt_path", ""),
                            })
            except Exception:
                pass
        return JSONResponse({"error": "Not found"}, status_code=404)

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

    @api.post("/captions/{job_id}")
    async def captions(job_id: str, request: Request):
        from fastapi.responses import Response as R
        job = state.jobs.get(job_id)
        if not job or job.get("status") != "done":
            return JSONResponse({"error": "Job not found or not complete"}, status_code=404)
        body = await request.json()
        max_chars    = max(1, int(body.get("max_chars",    42)))
        min_duration = max(0.0, float(body.get("min_duration", 1.2)))
        gap_frames   = max(0, int(body.get("gap_frames",   0)))
        lines        = max(1, min(2, int(body.get("lines",  1))))
        fps_label    = str(body.get("fps", "30"))
        if fps_label not in FRAMERATES:
            fps_label = "30"
        sentences = job.get("sentences", [])
        caps = build_captions(sentences, max_chars, min_duration, gap_frames, lines, fps_label)
        xml  = build_fcpxml(caps, fps_label)
        return R(
            content=xml.encode("utf-8"),
            media_type="application/xml",
            headers={"Content-Disposition": 'attachment; filename="captions.fcpxml"'},
        )

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
