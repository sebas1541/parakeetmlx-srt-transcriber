import os
import subprocess
import tempfile
from pathlib import Path

import state

_model = None

_CONVERT_EXTS = {".mp4", ".mov", ".mp3", ".m4a", ".flac", ".ogg", ".aac",
                 ".avi", ".mkv", ".webm"}


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
    for path in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if os.path.isfile(path):
            return path
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


# ── Transcription worker ──────────────────────────────────────────────────────

def transcribe_worker(job_id: str, src_path: str) -> None:
    global _model
    job = state.jobs[job_id]
    tmp_wav = None
    try:
        job["status"] = "Loading model\u2026"
        if _model is None:
            from parakeet_mlx import from_pretrained
            _model = from_pretrained("mlx-community/parakeet-tdt-0.6b-v3")

        job["status"] = "Preparing audio\u2026"
        ext = Path(src_path).suffix.lower()
        if ext in _CONVERT_EXTS:
            tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tmp_wav.close()
            _to_wav(src_path, tmp_wav.name)
            audio_path = tmp_wav.name
        else:
            audio_path = src_path

        sentences = _transcribe_chunked(_model, audio_path, job)

        if not sentences:
            job["error"]  = "No speech detected in the file."
            job["status"] = "error"
            return

        job["status"]       = "Building SRT\u2026"
        job["srt"]          = build_srt(sentences)
        job["srt_subtitle"] = build_srt_subtitle(sentences)
        job["status"]       = "done"

    except Exception as exc:
        job["error"]  = str(exc)
        job["status"] = "error"
    finally:
        if tmp_wav and os.path.exists(tmp_wav.name):
            os.unlink(tmp_wav.name)
        if os.path.exists(src_path):
            os.unlink(src_path)
