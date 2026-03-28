<p align="center">
  <img src="assets/icon.png" width="128" alt="Parakeet Transcriber icon" />
</p>

# Parakeet Transcriber

A macOS desktop app that transcribes audio and video files into downloadable **SRT subtitle files**. Powered by [Parakeet TDT 0.6B v3](https://github.com/senstella/parakeet-mlx) — a state-of-the-art ASR model optimised for Apple Silicon via MLX.

Built as a **webview app**: native macOS window chrome (title bar, traffic lights, save dialogs) with the UI rendered inside WKWebView — the same engine Safari uses. Close the window and everything stops — server, model, all of it.

---

## Requirements

- Apple Silicon Mac (M1 / M2 / M3 / M4)
- macOS 13 Ventura or later
- ~2.3 GB free disk space (model cache, downloaded once on first launch)
- Internet access on first launch

---

## One-time setup

### 1. Install Homebrew

If you don't have Homebrew:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Python and ffmpeg

```bash
brew install python@3.11 ffmpeg
```

> If Python 3.11 isn't available, Python 3.10 works fine — `build.sh` detects it automatically.

### 3. Build the app

```bash
cd /path/to/parakeet
chmod +x build.sh
./build.sh
```

The script creates a virtual environment, installs all Python dependencies, and runs PyInstaller. It takes roughly 3–5 minutes. When it finishes, `dist/Parakeet Transcriber.app` opens in Finder automatically.

---

## Install

Drag **`Parakeet Transcriber.app`** from `dist/` to your `/Applications` folder.

---

## Running the app

Double-click **Parakeet Transcriber** in Applications (or from `dist/` directly).

- A native Mac window opens immediately
- **First launch only:** the Parakeet TDT v3 model (~2.3 GB) downloads automatically to `~/.cache/huggingface/hub/` — this takes a few minutes depending on your connection
- Every launch after that is instant

**To use:**
1. Drop an audio or video file onto the upload area (or click to browse)
2. Click **Transcribe**
3. When done, click **View & Save SRT** to open the subtitle viewer
4. In the viewer, toggle between **Full sentences** and **Subtitles ≤5s** mode
5. Click **Save** to write the `.srt` file anywhere on your Mac via a native save dialog

**To quit:** close the window (red traffic light button or Cmd+Q) — the server and model unload immediately.

---

## Supported formats

| Format | Notes |
|--------|-------|
| `.wav` | Used directly |
| `.mp3` | Converted to 16 kHz WAV via ffmpeg |
| `.mp4` | Audio extracted via ffmpeg |
| `.m4a` | Converted via ffmpeg |
| `.mov` | Audio extracted via ffmpeg |
| `.flac` | Converted via ffmpeg |

---

## SRT modes

**Full sentences** — one subtitle block per sentence. Good for reading transcripts.

**Subtitles ≤5s** — breaks long sentences into short clips (max ~5 seconds each) using word-level timestamps. Use this for importing into video editors like Final Cut Pro, DaVinci Resolve, or Premiere.

---

## Troubleshooting

**"ffmpeg not found" error**
```bash
brew install ffmpeg
```
Then restart the app.

**App blocked by Gatekeeper ("app is damaged" / "cannot be opened")**

Run once in Terminal:
```bash
xattr -cr "/Applications/Parakeet Transcriber.app"
```

**Model download is slow**
The model (~2.3 GB) downloads from Hugging Face on first launch only. Subsequent launches skip this entirely — the model is cached at `~/.cache/huggingface/hub/`.

**Browser opens instead of a native window**
This shouldn't happen with a correctly built `.app`. If it does, rebuild:
```bash
rm -rf build dist
./build.sh
```

**Rebuild after modifying the code**
```bash
rm -rf build dist
./build.sh
```

---

## Project structure

```
parakeet/
├── main.py           # Entry point — pywebview window + server startup
├── server.py         # FastAPI routes
├── transcribe.py     # Model loading, audio processing, SRT building
├── jsapi.py          # Python methods exposed to the web page
├── templates.py      # HTML for the main page and SRT viewer
├── state.py          # Shared state (jobs, window reference)
├── requirements.txt  # Python dependencies
├── parakeet.spec     # PyInstaller spec (controls bundling)
├── build.sh          # One-command build script
└── README.md
```

---

## Model

`mlx-community/parakeet-tdt-0.6b-v3` — NVIDIA's Parakeet TDT 0.6B v3, an English-only automatic speech recognition model ported to Apple MLX. English transcription only.
