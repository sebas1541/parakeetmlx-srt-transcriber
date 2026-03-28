import re
from pathlib import Path

import state


class JsApi:
    """Exposes Python methods to the web page via window.pywebview.api.*"""

    def save_srt(self, job_id: str, mode: str = "full") -> dict:
        """Open a native macOS Save dialog and write the file."""
        import webview as wv

        job = state.jobs.get(job_id)
        if not job:
            return {"ok": False, "error": "Job not found"}

        if mode == "subtitle":
            content = job.get("srt_subtitle")
        elif mode == "txt":
            srt = job.get("srt", "")
            content = "\n\n".join(
                " ".join(l for l in block.splitlines()[2:])
                for block in re.split(r"\n\n+", srt.strip())
                if block.strip()
            )
        else:
            content = job.get("srt")

        if not content:
            return {"ok": False, "error": "No content"}

        try:
            is_txt = (mode == "txt")
            result = state.window.create_file_dialog(
                wv.SAVE_DIALOG,
                save_filename="transcript.txt" if is_txt else "transcript.srt",
                file_types=(("Text Files (*.txt)", "All files (*.*)")
                            if is_txt else
                            ("SRT Files (*.srt)", "All files (*.*)"))
            )
            if not result:
                return {"ok": False, "error": "Cancelled"}

            save_path = result[0] if isinstance(result, (list, tuple)) else str(result)
            ext = ".txt" if mode == "txt" else ".srt"
            if not save_path.lower().endswith(ext):
                save_path += ext

            Path(save_path).write_text(content, encoding="utf-8")
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
