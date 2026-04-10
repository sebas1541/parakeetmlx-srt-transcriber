<p align="left">
  <img src="assets/icon.png" width="128" alt="Super Transcribe icon" />
</p>

# Super Transcribe

A macOS desktop app that transcribes audio and video files into SRT subtitle files and FCPXML caption tracks for Final Cut Pro. Powered by [Whisper large-v3-turbo](https://github.com/ml-explore/mlx-examples) (multilingual, auto-detects language) and [Parakeet TDT 0.6B v3](https://github.com/senstella/parakeet-mlx) (English-only, faster) — both running locally on Apple Silicon via MLX.

Built as a webview app: native macOS window with the UI rendered in WKWebView. Close the window and everything stops.

---

## Requirements

- Apple Silicon Mac (M1 / M2 / M3 / M4)
- macOS 13 Ventura or later
- ~3 GB free disk space (model cache, downloaded once on first launch)
- Internet access on first launch (model download + Tailwind CDN)

---

## One-time setup

### 1. Install Homebrew

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. Install Python and ffmpeg

```bash
brew install python@3.11 ffmpeg
```

### 3. Build the app

```bash
cd /path/to/super-transcribe
chmod +x build.sh
./build.sh
```

The script creates a virtual environment, installs all Python dependencies, and runs PyInstaller. When it finishes, `dist/Super Transcribe.app` opens in Finder automatically.

---

## Install

Drag **`Super Transcribe.app`** from `dist/` to your `/Applications` folder.

---

## Using the app

Double-click **Super Transcribe** in Applications (or from `dist/` directly).

**Layout:** The window opens in a landscape dashboard. The left sidebar shows your transcription history. The main area has three views.

### Upload view

- Select a model: **Whisper** (default, multilingual, auto-detects language) or **Parakeet** (English-only, slightly faster)
- Drop an audio or video file onto the drop zone, or click to browse
- Click **Transcribe**

**First launch only:** the selected model downloads automatically (~1.5–2.3 GB to `~/.cache/huggingface/hub/`). Every launch after that is instant.

### Processing view

A waveform animation plays while the model transcribes. Status and progress are shown live.

### Results view

The transcript appears on the left in three tab modes:

| Tab | Content |
|-----|---------|
| Full SRT | Complete SRT with index numbers and timestamps |
| Subtitle | Subtitle-optimized SRT with shorter clips |
| Plain Text | Plain readable text, no timestamps |

You can select and copy text directly from the viewer (Cmd+C).

The footer shows a purple **Save SRT** or **Save TXT** button (label updates based on the active tab) and a green auto-saved badge with the path to the file that was automatically written to `~/Documents/SuperTranscribe/`.

The right panel is **Final Cut Pro Export**:
- Adjust max characters per line, minimum caption duration, frame gap, single/double lines, and frame rate
- **Generate FCPXML** — opens a native save dialog
- **Open in Final Cut Pro** — writes a temp FCPXML and opens it directly in FCP

### Sidebar history

Every completed transcription is saved to `~/Documents/SuperTranscribe/` as an SRT file and recorded in `history.json`. The sidebar lists them newest-first with the filename, relative time, and model badge (W / P). Clicking any item loads it back into the results view — all export functions work on history items too.

**New Transcription** button (top-right of header) resets the view.

**To quit:** close the window (Cmd+Q or red traffic light) — the server and model unload immediately.

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
| `.ogg` | Converted via ffmpeg |
| `.aac` | Converted via ffmpeg |
| `.mkv` | Audio extracted via ffmpeg |
| `.webm` | Audio extracted via ffmpeg |
| `.avi` | Audio extracted via ffmpeg |

---

## Auto-save location

Every transcription is automatically saved to:

```
~/Documents/SuperTranscribe/<filename>_<id>.srt
~/Documents/SuperTranscribe/history.json
```

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
xattr -cr "/Applications/Super Transcribe.app"
```

**Model download is slow**

The model downloads from Hugging Face on first launch only. Subsequent launches skip this entirely — the model is cached at `~/.cache/huggingface/hub/`.

**Rebuild after modifying the code**
```bash
rm -rf build dist
./build.sh
```

---

## Project structure

```
super-transcribe/
├── main.py           # Entry point — pywebview window + server startup
├── server.py         # FastAPI routes (/transcribe, /status, /history, /srt)
├── transcribe.py     # Model loading, audio processing, SRT building, auto-save
├── jsapi.py          # Python methods exposed to the web page (save dialogs, FCP)
├── captions.py       # Caption splitting and FCPXML generation
├── templates.py      # HTML/CSS/JS for the dashboard UI
├── state.py          # Shared state (jobs dict, window reference, DOCS_DIR)
├── requirements.txt  # Python dependencies
├── parakeet.spec     # PyInstaller spec
├── build.sh          # One-command build script
└── README.md
```

---

## Models

**Whisper large-v3-turbo** (`mlx-community/whisper-large-v3-turbo`) — OpenAI's Whisper, multilingual, auto-detects language. Default model.

**Parakeet TDT 0.6B v3** (`mlx-community/parakeet-tdt-0.6b-v3`) — NVIDIA's Parakeet, English-only ASR model ported to Apple MLX. Faster for English content.


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
