"""Caption splitting and FCPXML generation for Parakeet Transcriber."""

from __future__ import annotations

import uuid
from math import gcd
from xml.sax.saxutils import escape

# ── Frame-rate table ──────────────────────────────────────────────────────────
# label -> (fps_numerator, fps_denominator)
FRAMERATES: dict[str, tuple[int, int]] = {
    "23.98": (24000, 1001),
    "24":    (24,    1),
    "25":    (25,    1),
    "29.97": (30000, 1001),
    "30":    (30,    1),
    "60":    (60,    1),
}


def _secs_to_fcptime(t: float, fps_num: int, fps_den: int) -> str:
    """Convert a duration in seconds to a FCPXML rational time string."""
    frames = round(t * fps_num / fps_den)
    if frames == 0:
        return "0s"
    num = frames * fps_den
    den = fps_num
    g = gcd(abs(num), abs(den))
    num //= g
    den //= g
    if den == 1:
        return f"{num}s"
    return f"{num}/{den}s"


# ── SRT → captions fallback (for history items without sentence data) ─────────

def _srt_to_captions(srt: str) -> list[dict]:
    """Parse a plain SRT string into the same [{start, end, text}] format that
    build_captions() produces.  Used when sentence-level data is unavailable."""
    import re
    ts_re = re.compile(
        r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})'
    )
    captions: list[dict] = []
    for block in re.split(r'\n\n+', srt.strip()):
        lines = block.strip().splitlines()
        for i, line in enumerate(lines):
            m = ts_re.match(line.strip())
            if m:
                h1, m1, s1, ms1, h2, m2, s2, ms2 = m.groups()
                start = int(h1)*3600 + int(m1)*60 + int(s1) + int(ms1)/1000
                end   = int(h2)*3600 + int(m2)*60 + int(s2) + int(ms2)/1000
                text  = '\n'.join(lines[i+1:]).strip()
                if text:
                    captions.append({'start': start, 'end': end, 'text': text})
                break
    return captions


# ── Word-level timestamp extraction ──────────────────────────────────────────

def _extract_words(sentences) -> list[tuple[str, float, float]]:
    """Return list of (word, start_sec, end_sec) derived from sentence token timing.

    Uses proportional mapping of token boundaries to word boundaries, avoiding
    BPE subword artefacts the same way build_srt_subtitle does.
    """
    words: list[tuple[str, float, float]] = []
    for sent in sentences:
        text = sent.text.strip()
        toks = [t for t in sent.tokens if t.text.strip()]
        if not text or not toks:
            continue
        word_list = text.split()
        n_toks = len(toks)
        n_wds  = len(word_list)
        for wi, word in enumerate(word_list):
            ti_start = int(wi       / n_wds * n_toks)
            ti_end   = int((wi + 1) / n_wds * n_toks) - 1
            ti_start = max(0, min(ti_start, n_toks - 1))
            ti_end   = max(ti_start, min(ti_end, n_toks - 1))
            words.append((word, toks[ti_start].start, toks[ti_end].end))
    return words


# ── Caption splitting ─────────────────────────────────────────────────────────

def build_captions(
    sentences,
    max_chars: int,
    min_duration: float,
    gap_frames: int,
    lines: int,
    fps_label: str,
) -> list[dict]:
    """Split transcript sentences into timed caption blocks.

    Returns a list of dicts with keys: start (float), end (float), text (str).
    Text may contain a single newline separating two lines when lines == 2.
    """
    fps_num, fps_den = FRAMERATES[fps_label]
    fps      = fps_num / fps_den
    gap_sec  = gap_frames / fps

    words = _extract_words(sentences)
    if not words:
        return []

    captions: list[dict] = []
    i = 0

    while i < len(words):
        cap_lines: list[str] = []
        current_words: list[str] = []
        current_len   = 0
        cap_start     = words[i][1]
        last_end      = words[i][2]

        while i < len(words):
            word, _wstart, wend = words[i]
            added_len = len(word) + (1 if current_words else 0)  # +1 for space

            if current_len + added_len <= max_chars:
                current_words.append(word)
                current_len += added_len
                last_end = wend
                i += 1
            else:
                if not current_words:
                    # Single word exceeds max_chars — accept it to avoid infinite loop
                    current_words.append(word)
                    last_end = wend
                    i += 1

                cap_lines.append(" ".join(current_words))
                current_words = []
                current_len   = 0

                if len(cap_lines) >= lines:
                    break  # caption is full

        if current_words:
            cap_lines.append(" ".join(current_words))

        text         = "\n".join(cap_lines)
        extended_end = max(last_end, cap_start + min_duration)
        captions.append({"start": cap_start, "end": extended_end, "text": text})

    # Enforce gap between consecutive captions
    for j in range(len(captions) - 1):
        next_start      = captions[j + 1]["start"]
        max_allowed_end = next_start - gap_sec
        # Never let a cap end before it starts (minimum 1-frame visual)
        min_end = captions[j]["start"] + (1 / fps)
        captions[j]["end"] = max(min(captions[j]["end"], max_allowed_end), min_end)

    return captions


# ── FCPXML export ─────────────────────────────────────────────────────────────

def build_fcpxml(captions: list[dict], fps_label: str) -> str:
    """Return a complete FCPXML 1.9 string with individual Basic Title clips per caption.

    Each caption becomes a separate <title> clip on lane 1 inside a gap clip,
    identical to how apps like Whisper Auto Captions generate FCPXML for FCP.
    """
    if not captions:
        return ""

    fps_num, fps_den = FRAMERATES[fps_label]
    tc_format = "DF" if fps_label in ("23.98", "29.97") else "NDF"

    # Frame-duration string (inverse of fps)
    fd_num = fps_den
    fd_den = fps_num
    g = gcd(fd_num, fd_den)
    fd_num //= g
    fd_den //= g
    frame_dur_str = f"{fd_num}/{fd_den}s" if fd_den != 1 else f"{fd_num}s"

    # Timeline total duration
    total_end     = captions[-1]["end"] + 1.0
    total_dur_str = _secs_to_fcptime(total_end, fps_num, fps_den)

    project_uid = str(uuid.uuid4()).upper()

    # Build one <title> element per caption
    title_elements: list[str] = []
    for idx, cap in enumerate(captions):
        offset_str = _secs_to_fcptime(cap["start"], fps_num, fps_den)
        frame_sec  = fps_den / fps_num          # one frame in seconds
        dur_sec    = max(cap["end"] - cap["start"], frame_sec)
        dur_str    = _secs_to_fcptime(dur_sec, fps_num, fps_den)

        ts_id    = f"ts{idx + 1}"
        lines    = [l for l in cap["text"].split("\n") if l.strip()]
        content  = escape("\n".join(lines))
        cap_name = escape(lines[0][:40]) if lines else f"Caption {idx + 1}"

        title_elements.append(
            f'\t\t\t\t\t\t\t<title ref="r2" lane="1" offset="{offset_str}" duration="{dur_str}" start="0s" name="{cap_name} - Basic Title">\n'
            f'\t\t\t\t\t\t\t\t<param name="Position" key="9999/999166631/999166633/1/100/101" value="0 -465"/>\n'
            f'\t\t\t\t\t\t\t\t<param name="Flatten" key="999/999166631/999166633/2/351" value="1"/>\n'
            f'\t\t\t\t\t\t\t\t<param name="Alignment" key="9999/999166631/999166633/2/354/999169573/401" value="1 (Center)"/>\n'
            f'\t\t\t\t\t\t\t\t<text>\n'
            f'\t\t\t\t\t\t\t\t\t<text-style ref="{ts_id}">{content}</text-style>\n'
            f'\t\t\t\t\t\t\t\t</text>\n'
            f'\t\t\t\t\t\t\t\t<text-style-def id="{ts_id}">\n'
            f'\t\t\t\t\t\t\t\t\t<text-style font="Helvetica" fontSize="45" fontFace="Regular"'
            f' fontColor="1 1 1 1" shadowColor="0 0 0 0.75" shadowOffset="4 315" alignment="center"/>\n'
            f'\t\t\t\t\t\t\t\t</text-style-def>\n'
            f'\t\t\t\t\t\t\t</title>'
        )

    titles_xml = "\n".join(title_elements)

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE fcpxml>\n'
        '<fcpxml version="1.9">\n'
        '\t<resources>\n'
        f'\t\t<format id="r1" frameDuration="{frame_dur_str}" width="1920" height="1080"'
        ' colorSpace="1-1-1 (Rec. 709)"/>\n'
        '\t\t<effect id="r2" name="Basic Title"'
        ' uid=".../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti"/>\n'
        '\t</resources>\n'
        '\t<library location="">\n'
        '\t\t<event name="Captions">\n'
        f'\t\t\t<project name="Captions" uid="{project_uid}">\n'
        f'\t\t\t\t<sequence duration="{total_dur_str}" format="r1" tcStart="0s"'
        f' tcFormat="{tc_format}" audioLayout="stereo" audioRate="48k">\n'
        '\t\t\t\t\t<spine>\n'
        f'\t\t\t\t\t\t<gap name="Gap" offset="0s" duration="{total_dur_str}" start="0s">\n'
        f'{titles_xml}\n'
        '\t\t\t\t\t\t</gap>\n'
        '\t\t\t\t\t</spine>\n'
        '\t\t\t\t</sequence>\n'
        '\t\t\t</project>\n'
        '\t\t</event>\n'
        '\t</library>\n'
        '</fcpxml>\n'
    )
