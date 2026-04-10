import re
from pathlib import Path

import state
from captions import build_captions, build_fcpxml, FRAMERATES


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

    def save_fcpxml(self, job_id: str, max_chars: int, min_duration: float,
                    gap_frames: int, lines: int, fps: str) -> dict:
        """Build FCPXML and save via native macOS Save dialog."""
        import webview as wv

        job = state.jobs.get(job_id)
        if not job or job.get("status") != "done":
            return {"ok": False, "error": "Job not found"}

        sentences = job.get("sentences", [])
        fps_label = fps if fps in FRAMERATES else "30"
        caps = build_captions(sentences, max(1, int(max_chars)),
                              max(0.0, float(min_duration)),
                              max(0, int(gap_frames)),
                              max(1, min(2, int(lines))),
                              fps_label)
        xml = build_fcpxml(caps, fps_label)
        if not xml:
            return {"ok": False, "error": "No captions generated"}

        try:
            result = state.window.create_file_dialog(
                wv.SAVE_DIALOG,
                save_filename="captions.fcpxml",
                file_types=("FCPXML Files (*.fcpxml)", "All files (*.*)")
            )
            if not result:
                return {"ok": False, "error": "Cancelled"}

            save_path = result[0] if isinstance(result, (list, tuple)) else str(result)
            if not save_path.lower().endswith(".fcpxml"):
                save_path += ".fcpxml"

            Path(save_path).write_text(xml, encoding="utf-8")
            return {"ok": True, "path": save_path}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def open_in_fcpx(self, job_id: str, max_chars: int, min_duration: float,
                     gap_frames: int, lines: int, fps: str) -> dict:
        """Save FCPXML to a temp file and open it directly in Final Cut Pro."""
        import subprocess
        import tempfile

        job = state.jobs.get(job_id)
        if not job or job.get("status") != "done":
            return {"ok": False, "error": "Job not found"}

        sentences = job.get("sentences", [])
        fps_label = fps if fps in FRAMERATES else "30"
        caps = build_captions(sentences, max(1, int(max_chars)),
                              max(0.0, float(min_duration)),
                              max(0, int(gap_frames)),
                              max(1, min(2, int(lines))),
                              fps_label)
        xml = build_fcpxml(caps, fps_label)
        if not xml:
            return {"ok": False, "error": "No captions generated"}

        try:
            with tempfile.NamedTemporaryFile(suffix=".fcpxml", delete=False,
                                            mode="w", encoding="utf-8") as f:
                f.write(xml)
                tmp_path = f.name

            script = (
                'tell application "Final Cut Pro"\n'
                '  launch\n'
                '  activate\n'
                f'  open POSIX file "{tmp_path}"\n'
                'end tell'
            )
            subprocess.run(["osascript", "-e", script], check=True)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
