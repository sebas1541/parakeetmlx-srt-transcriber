import os
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import state

_model         = None
_WHISPER_REPO  = "mlx-community/whisper-large-v3-turbo"
_PARAKEET_REPO = "mlx-community/parakeet-tdt-0.6b-v3"

_CONVERT_EXTS = {".mp4", ".mov", ".mp3", ".m4a", ".flac", ".ogg", ".aac",
                 ".avi", ".mkv", ".webm"}


# ── Model download helpers ────────────────────────────────────────────────────

def _is_model_cached(repo_id: str) -> bool:
    """Return True if the HuggingFace model repo is already in the local cache."""
    try:
        import huggingface_hub
        cache     = Path(huggingface_hub.constants.HF_HUB_CACHE)
        folder    = "models--" + repo_id.replace("/", "--")
        snapshots = cache / folder / "snapshots"
        return snapshots.exists() and any(snapshots.iterdir())
    except Exception:
        return False


def _ensure_model_downloaded(repo_id: str, job: dict) -> None:
    """Pre-download a HuggingFace model with per-file progress if not already cached."""
    if _is_model_cached(repo_id):
        return
    try:
        import huggingface_hub
        files = sorted(huggingface_hub.list_repo_files(repo_id))
        total = len(files)
        job["status"] = "Downloading model\u2026"
        for i, filename in enumerate(files, 1):
            job["progress"] = {"current": i, "total": total}
            huggingface_hub.hf_hub_download(repo_id=repo_id, filename=filename)
        job["progress"] = None
    except Exception:
        pass  # fall back to the library's own download on any failure


# ── SRT helpers ───────────────────────────────────────────────────────────────

def _fmt_srt_time(seconds: float) -> str:
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    ms = int(round((seconds % 1) * 1000))
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(sentences) -> str:
    """Full-sentence SRT — one block per sentence."""
    blocks = []
    for i, sent in enumerate(sentences, 1):
        blocks.append(
            f"{i}\n{_fmt_srt_time(sent.start)} --> {_fmt_srt_time(sent.end)}\n{sent.text.strip()}"
        )
    return "\n\n".join(blocks) + "\n"


def build_srt_subtitle(sentences, max_sec: float = 5.0) -> str:
    """Subtitle SRT — uses sentence text for content, token timestamps for timing.

    Avoids BPE token artefacts by never reconstructing text from subword tokens.
    Instead it proportionally maps the token-time boundary back to whole words
    from the already-clean sentence.text string.
    """
    blocks: list[dict] = []

    for sent in sentences:
        text  = sent.text.strip()
        toks  = [t for t in sent.tokens if t.text.strip()]
        if not text or not toks:
            continue

        dur = sent.end - sent.start
        if dur <= max_sec:
            blocks.append({"start": sent.start, "end": sent.end, "text": text})
            continue

        words   = text.split()
        n_toks  = len(toks)
        n_wds   = len(words)
        chunk_start = toks[0].start
        chunk_i     = 0

        for i, tok in enumerate(toks):
            at_end = (i == n_toks - 1)
            if at_end or (tok.end - chunk_start) >= max_sec:
                w0 = round(chunk_i / n_toks * n_wds)
                w1 = round((i + 1) / n_toks * n_wds)
                chunk_text = " ".join(words[w0:w1]).strip()
                if chunk_text:
                    blocks.append({
                        "start": chunk_start,
                        "end":   toks[i].end,
                        "text":  chunk_text,
                    })
                if not at_end:
                    chunk_start = toks[i + 1].start
                    chunk_i     = i + 1

    return "\n\n".join(
        f"{i}\n{_fmt_srt_time(b['start'])} --> {_fmt_srt_time(b['end'])}\n{b['text']}"
        for i, b in enumerate(blocks, 1)
    ) + "\n"


# ── Audio helpers ─────────────────────────────────────────────────────────────

def _find_ffmpeg() -> str | None:
    import sys
    # 1. Bundled ffmpeg inside the .app (PyInstaller puts binaries next to the exe)
    bundled = os.path.join(os.path.dirname(sys.executable), "ffmpeg")
    if os.path.isfile(bundled):
        return bundled
    # 2. Common Homebrew / system paths
    for path in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if os.path.isfile(path):
            return path
    # 3. Anything on PATH
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True, timeout=5)
        return "ffmpeg"
    except Exception:
        return None


def _to_wav(src: str, dst: str) -> None:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError(
            "ffmpeg not found. Install it with: brew install ffmpeg, then restart the app."
        )
    subprocess.run(
        [ffmpeg, "-y", "-i", src, "-ac", "1", "-ar", "16000", dst],
        check=True, capture_output=True, timeout=600,
    )


# ── Chunked transcription (avoids Metal buffer size limit on long files) ──────

_CHUNK_SEC = 5 * 60  # 5-minute chunks


class _Sentence:
    """Lightweight sentence wrapper that supports timestamp offsetting."""
    __slots__ = ("start", "end", "text", "tokens")

    def __init__(self, start, end, text, tokens):
        self.start  = start
        self.end    = end
        self.text   = text
        self.tokens = tokens


class _Token:
    __slots__ = ("start", "end", "text")

    def __init__(self, start, end, text):
        self.start = start
        self.end   = end
        self.text  = text


def _wav_duration(wav_path: str) -> float:
    import wave as _wave
    with _wave.open(wav_path, "rb") as wf:
        return wf.getnframes() / wf.getframerate()


def _transcribe_chunked(model, audio_path: str, job: dict) -> list:
    """Transcribe in 5-minute chunks to stay within Metal's buffer limit."""
    duration = _wav_duration(audio_path)

    if duration <= _CHUNK_SEC:
        job["status"]   = "Transcribing\u2026"
        job["progress"] = None
        return list(model.transcribe(audio_path).sentences)

    ffmpeg    = _find_ffmpeg()
    n_chunks  = int(duration / _CHUNK_SEC) + 1
    sentences = []

    for i in range(n_chunks):
        offset = i * _CHUNK_SEC
        if offset >= duration:
            break

        job["status"]   = "Transcribing\u2026"
        job["progress"] = {"current": i + 1, "total": n_chunks}

        chunk_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        chunk_tmp.close()
        try:
            subprocess.run(
                [ffmpeg, "-y", "-i", audio_path,
                 "-ss", str(offset), "-t", str(_CHUNK_SEC),
                 "-ac", "1", "-ar", "16000", chunk_tmp.name],
                check=True, capture_output=True, timeout=120,
            )
            result = model.transcribe(chunk_tmp.name)
            for sent in result.sentences:
                tokens = [_Token(t.start + offset, t.end + offset, t.text)
                          for t in sent.tokens]
                sentences.append(_Sentence(
                    sent.start + offset,
                    sent.end   + offset,
                    sent.text,
                    tokens,
                ))
        finally:
            os.unlink(chunk_tmp.name)

    return sentences


# ── Whisper helpers ───────────────────────────────────────────────────────────

def _sentences_from_whisper(result) -> list:
    """Convert mlx_whisper output to _Sentence/_Token format."""
    sentences = []
    for seg in result.get("segments", []):
        text = seg.get("text", "").strip()
        if not text:
            continue
        words_data = seg.get("words", [])
        if words_data:
            tokens = [
                _Token(w["start"], w["end"], w["word"].strip())
                for w in words_data
                if w["word"].strip()
            ]
        else:
            tokens = [_Token(seg["start"], seg["end"], text)]
        sentences.append(_Sentence(seg["start"], seg["end"], text, tokens))
    return sentences


def _transcribe_whisper(audio_path: str, job: dict, language: str | None = None) -> list:
    """Transcribe with mlx-whisper. Pass language=None for auto-detection."""
    import mlx_whisper
    job["status"]   = "Transcribing\u2026"
    job["progress"] = None
    kwargs: dict = dict(
        path_or_hf_repo=_WHISPER_REPO,
        word_timestamps=True,
        verbose=False,
    )
    if language:
        kwargs["language"] = language
    result = mlx_whisper.transcribe(audio_path, **kwargs)
    return _sentences_from_whisper(result)


# ── Transcription worker ──────────────────────────────────────────────────────

def transcribe_worker(job_id: str, src_path: str, model: str = "whisper") -> None:
    """model: 'whisper' (auto-detect language) or 'parakeet' (English only)."""
    global _model
    job     = state.jobs[job_id]
    tmp_wav = None
    try:
        job["status"] = "Preparing audio\u2026"
        ext = Path(src_path).suffix.lower()
        if ext in _CONVERT_EXTS:
            tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_wav.close()
            _to_wav(src_path, tmp_wav.name)
            audio_path = tmp_wav.name
        else:
            audio_path = src_path

        if model == "parakeet":
            _ensure_model_downloaded(_PARAKEET_REPO, job)
            job["status"] = "Loading model\u2026"
            if _model is None:
                from parakeet_mlx import from_pretrained
                _model = from_pretrained(_PARAKEET_REPO)
            sentences = _transcribe_chunked(_model, audio_path, job)
        else:
            _ensure_model_downloaded(_WHISPER_REPO, job)
            sentences = _transcribe_whisper(audio_path, job)

        if not sentences:
            job["error"]  = "No speech detected in the file."
            job["status"] = "error"
            return

        job["status"]       = "Building SRT\u2026"
        job["srt"]          = build_srt(sentences)
        job["srt_subtitle"] = build_srt_subtitle(sentences)
        job["sentences"]    = sentences

        # ── Auto-save to ~/Documents/SuperTranscribe/ ──────────────────────
        try:
            orig_name = job.get("original_filename", "transcript")
            stem      = Path(orig_name).stem[:60]
            srt_name  = f"{stem}_{job_id[:8]}.srt"
            srt_path  = state.DOCS_DIR / srt_name
            srt_path.write_text(job["srt"], encoding="utf-8")
            job["auto_save_path"] = str(srt_path)

            hist_file = state.DOCS_DIR / "history.json"
            history: list = []
            if hist_file.exists():
                try:
                    history = json.loads(hist_file.read_text(encoding="utf-8"))
                except Exception:
                    history = []
            history.insert(0, {
                "id":           job_id,
                "filename":     orig_name,
                "created_at":   datetime.now(timezone.utc).isoformat(),
                "srt_path":     str(srt_path),
                "model":        model,
            })
            history = history[:100]  # keep last 100
            hist_file.write_text(json.dumps(history, ensure_ascii=False, indent=2),
                                 encoding="utf-8")
        except Exception:
            pass  # auto-save failure is non-fatal

        job["status"] = "done"

    except Exception as exc:
        job["error"]  = str(exc)
        job["status"] = "error"
    finally:
        if tmp_wav and os.path.exists(tmp_wav.name):
            os.unlink(tmp_wav.name)
        if os.path.exists(src_path):
            os.unlink(src_path)
