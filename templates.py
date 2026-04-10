"""HTML templates for the main page and the SRT viewer."""


def viewer_page(id_json: str, srt_json: str, srt_subtitle_json: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>transcript.srt</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <script>
    tailwind.config = {{
      theme: {{
        extend: {{
          fontFamily: {{ sans: ['Inter', 'ui-sans-serif', 'system-ui'] }},
          colors: {{
            primary:        'hsl(228 88% 66%)',
            'primary-hover':'hsl(228 88% 58%)',
            'primary-soft': 'hsl(228 88% 96%)',
            'gl-bg':        'hsl(228 25% 97%)',
            'gl-card':      '#ffffff',
            'gl-fg':        'hsl(228 30% 14%)',
            'gl-muted':     'hsl(228 10% 55%)',
            'gl-border':    'hsl(228 20% 92%)',
          }},
        }}
      }}
    }}
  </script>
  <style>
    body {{ -webkit-font-smoothing: antialiased; }}
  </style>
</head>
<body class="bg-gl-bg font-sans flex flex-col h-screen overflow-hidden">

  <!-- Header bar -->
  <div class="flex-shrink-0 flex items-center justify-between px-4 h-14 bg-gl-card border-b border-gl-border">
    <button
      onclick="window.location.href='/'"
      class="flex items-center gap-1.5 text-sm font-medium text-gl-muted hover:text-gl-fg transition-colors duration-150"
    >
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
      </svg>
      <span id="back-label"></span>
    </button>

    <!-- Mode toggle -->
    <div class="flex items-center gap-1 bg-gl-bg rounded-lg p-0.5 border border-gl-border">
      <button id="btn-full" onclick="setMode('full')"
        class="px-2.5 py-1 rounded-md text-xs font-semibold transition-all duration-150 bg-white shadow-sm text-gl-fg border border-gl-border">
        <span id="label-full"></span>
      </button>
      <button id="btn-subtitle" onclick="setMode('subtitle')"
        class="px-2.5 py-1 rounded-md text-xs font-semibold transition-all duration-150 text-gl-muted">
        <span id="label-subtitle"></span>
      </button>
      <button id="btn-txt" onclick="setMode('txt')"
        class="px-2.5 py-1 rounded-md text-xs font-semibold transition-all duration-150 text-gl-muted">
        <span id="label-txt"></span>
      </button>
    </div>

    <button
      id="save-btn"
      onclick="saveFile()"
      class="flex items-center gap-1.5 h-8 px-3 rounded-lg bg-primary text-white text-xs font-semibold shadow transition-all duration-150 hover:bg-primary-hover hover:-translate-y-px active:translate-y-0"
    >
      <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round"
          d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
      </svg>
      <span id="save-label"></span>
    </button>
  </div>

  <!-- SRT blocks -->
  <div class="flex-1 overflow-y-auto px-4 py-4 space-y-2">
    <div id="blocks"></div>
  </div>

  <script>
    const JOB_ID       = {id_json};
    const SRT_FULL     = {srt_json};
    const SRT_SUBTITLE = {srt_subtitle_json};
    // Plain text: strip index + timestamp lines, join paragraphs
    const TXT_PLAIN    = SRT_FULL.trim().split(/\\n\\n+/).map(block => {{
      const lines = block.split('\\n');
      return lines.slice(2).join(' ');
    }}).filter(Boolean).join('\\n\\n');
    let   activeMode   = 'full';

    // ── i18n ──────────────────────────────────────────────────────────────
    const TV = {{
      en: {{ back: 'Back', full: 'Full sentences', sub: 'Subtitles \u22645s', txt: 'Plain text',
             save: 'Save', saving: 'Saving\u2026', saved: 'Saved' }},
      es: {{ back: 'Atrás', full: 'Oraciones completas', sub: 'Subtítulos \u22645s', txt: 'Texto plano',
             save: 'Guardar', saving: 'Guardando\u2026', saved: 'Guardado' }},
    }};

    function detectLang() {{
      const saved = localStorage.getItem('pt_lang');
      return saved || (navigator.language.startsWith('es') ? 'es' : 'en');
    }}

    let currentLang = detectLang();

    function applyViewerLang() {{
      const t = TV[currentLang];
      document.getElementById('back-label').textContent     = t.back;
      document.getElementById('label-full').textContent     = t.full;
      document.getElementById('label-subtitle').textContent = t.sub;
      document.getElementById('label-txt').textContent      = t.txt;
      document.getElementById('save-label').textContent     = t.save;
    }}

    // ── SRT rendering ──────────────────────────────────────────────────────
    function parseSrt(raw) {{
      return raw.trim().split(/\\n\\n+/).map(block => {{
        const lines = block.split('\\n');
        return {{ index: lines[0], time: lines[1], text: lines.slice(2).join(' ') }};
      }}).filter(b => b.text);
    }}

    function render() {{
      const container = document.getElementById('blocks');
      if (activeMode === 'txt') {{
        container.innerHTML = `
          <div class="px-3 py-2">
            <p class="text-sm text-gl-fg leading-relaxed whitespace-pre-wrap select-text">${{TXT_PLAIN}}</p>
          </div>`;
        return;
      }}
      const srt    = activeMode === 'subtitle' ? SRT_SUBTITLE : SRT_FULL;
      const blocks = parseSrt(srt);
      container.innerHTML = blocks.map(b => `
        <div class="flex gap-3 items-start py-2.5 px-3 rounded-xl hover:bg-white hover:shadow-sm transition-all duration-100 border border-transparent hover:border-[hsl(228_20%_92%)]">
          <span class="flex-shrink-0 text-[11px] font-mono text-gl-muted w-5 text-right pt-0.5 select-none">${{b.index}}</span>
          <div class="flex-1 min-w-0">
            <p class="text-[11px] font-mono text-gl-muted mb-0.5 select-none">${{b.time}}</p>
            <p class="text-sm text-gl-fg leading-snug">${{b.text}}</p>
          </div>
        </div>
      `).join('');
    }}

    function setMode(mode) {{
      activeMode = mode;
      const active   = 'px-2.5 py-1 rounded-md text-xs font-semibold transition-all duration-150 bg-white shadow-sm text-gl-fg border border-gl-border';
      const inactive = 'px-2.5 py-1 rounded-md text-xs font-semibold transition-all duration-150 text-gl-muted';
      document.getElementById('btn-full').className     = mode === 'full'     ? active : inactive;
      document.getElementById('btn-subtitle').className = mode === 'subtitle' ? active : inactive;
      document.getElementById('btn-txt').className      = mode === 'txt'      ? active : inactive;
      render();
    }}

    async function saveFile() {{
      const t   = TV[currentLang];
      const btn = document.getElementById('save-btn');
      document.getElementById('save-label').textContent = t.saving;
      btn.disabled = true;
      try {{
        const result = await window.pywebview.api.save_srt(JOB_ID, activeMode);
        if (result.ok) {{
          document.getElementById('save-label').textContent = t.saved;
          setTimeout(() => {{
            document.getElementById('save-label').textContent = t.save;
            btn.disabled = false;
          }}, 2000);
        }} else {{
          document.getElementById('save-label').textContent = t.save;
          btn.disabled = false;
          if (result.error && result.error !== 'Cancelled') alert(result.error);
        }}
      }} catch(e) {{
        document.getElementById('save-label').textContent = t.save;
        btn.disabled = false;
      }}
    }}

    // ── Init ──────────────────────────────────────────────────────────────
    applyViewerLang();
    render();
  </script>
</body>
</html>"""


MAIN_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Super Transcribe</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700&display=swap" rel="stylesheet" />
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui'] },
          colors: {
            primary:         'hsl(228 88% 62%)',
            'primary-hover': 'hsl(228 88% 55%)',
            'primary-soft':  'hsl(228 88% 97%)',
            'gl-bg':         'hsl(228 20% 97%)',
            'gl-card':       '#ffffff',
            'gl-fg':         'hsl(228 30% 12%)',
            'gl-muted':      'hsl(228 10% 52%)',
            'gl-border':     'hsl(228 18% 90%)',
            'gl-hover':      'hsl(228 20% 94%)',
          },
          boxShadow: {
            card:       '0 1px 3px rgba(0,0,0,.07), 0 1px 2px rgba(0,0,0,.04)',
            btn:        '0 1px 2px rgba(80,110,240,.20)',
            'btn-hover':'0 4px 14px rgba(80,110,240,.32)',
          },
        }
      }
    }
  </script>
  <style>
    html, body { height: 100%; overflow: hidden; -webkit-font-smoothing: antialiased; }

    #drop-zone.drag-over {
      border-color: hsl(228 88% 62%) !important;
      background:   hsl(228 88% 97%) !important;
    }

    @keyframes wave {
      0%, 100% { transform: scaleY(0.2); }
      50%       { transform: scaleY(1);  }
    }
    .wave-bar {
      width: 4px; border-radius: 9999px;
      background: hsl(228 88% 62%);
      animation: wave 1.1s ease-in-out infinite;
      transform-origin: bottom center;
    }
    .wave-bar:nth-child(1){animation-delay:0ms;   height:38px;}
    .wave-bar:nth-child(2){animation-delay:110ms; height:54px;}
    .wave-bar:nth-child(3){animation-delay:220ms; height:70px;}
    .wave-bar:nth-child(4){animation-delay:330ms; height:82px;}
    .wave-bar:nth-child(5){animation-delay:220ms; height:70px;}
    .wave-bar:nth-child(6){animation-delay:110ms; height:54px;}
    .wave-bar:nth-child(7){animation-delay:0ms;   height:38px;}

    .view {
      transition: opacity 270ms ease, transform 270ms ease;
      position: absolute; inset: 0;
    }
    .view.hidden-view {
      opacity: 0; transform: translateY(8px); pointer-events: none;
    }

    #transcript-content {
      font-family: ui-monospace, 'SF Mono', Menlo, monospace;
      font-size: .77rem; line-height: 1.75;
      white-space: pre-wrap; word-break: break-word;
      -webkit-user-select: text; user-select: text; cursor: text;
    }

    ::-webkit-scrollbar       { width: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: hsl(228 15% 84%); border-radius: 9999px; }

    .sidebar-item.active      { background: hsl(228 30% 20%) !important; }
    .sidebar-item.active .item-bar { opacity: 1; }
    .item-bar {
      width: 3px; border-radius: 9999px;
      background: hsl(228 88% 68%); opacity: 0;
      transition: opacity 150ms; flex-shrink: 0; align-self: stretch;
    }

    .tab-btn { transition: all 150ms ease; }
    .tab-btn.active { background: hsl(228 88% 97%); color: hsl(228 88% 55%); }
    .tab-btn:not(.active) { color: hsl(228 10% 52%); }
    .tab-btn:not(.active):hover { color: hsl(228 30% 12%); }

    input[type=range] { accent-color: hsl(228 88% 62%); }

    .cap-row { display:flex; align-items:center; gap:10px; margin-bottom:6px; }
    .cap-row label { font-size:.72rem; color:hsl(228 10% 52%); width:96px; flex-shrink:0; }
    .cap-row input[type=range] { flex:1; }
    .cap-row .val { font-size:.72rem; font-weight:600; color:hsl(228 30% 12%); min-width:2rem; text-align:right; }
  </style>
</head>
<body class="font-sans h-screen flex overflow-hidden" style="background:hsl(228 20% 97%);">

  <!-- SIDEBAR -->
  <aside class="w-52 flex-shrink-0 flex flex-col" style="background:hsl(228 25% 11%);">
    <div class="px-4 pt-5 pb-3" style="border-bottom:1px solid hsl(228 22% 18%);">
      <div class="flex items-center gap-2">
        <div class="w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0" style="background:hsl(228 88% 62%);">
          <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
          </svg>
        </div>
        <span class="text-sm font-semibold text-white tracking-tight">Super Transcribe</span>
      </div>
    </div>

    <div class="px-4 pt-4 pb-1">
      <span id="lbl-recents" class="text-xs font-semibold uppercase tracking-widest" style="color:hsl(228 10% 38%);"></span>
    </div>

    <div id="sidebar-list" class="flex-1 overflow-y-auto px-2 pb-3 space-y-px">
      <div id="sidebar-empty" class="px-3 py-4 text-xs" style="color:hsl(228 10% 40%);"></div>
    </div>

    <div class="px-3 pb-4 pt-2" style="border-top:1px solid hsl(228 22% 18%);">
      <button onclick="toggleLang()" id="lang-toggle"
        class="w-full text-xs font-medium py-1.5 rounded-lg transition-colors"
        style="color:hsl(228 15% 58%); background:hsl(228 22% 16%);"></button>
    </div>
  </aside>

  <!-- MAIN -->
  <div class="flex-1 flex flex-col overflow-hidden">

    <!-- Header -->
    <header class="flex-shrink-0 h-12 flex items-center justify-between px-6 bg-white" style="border-bottom:1px solid hsl(228 18% 90%);">
      <span id="header-title" class="text-sm font-semibold tracking-tight" style="color:hsl(228 30% 12%);"></span>
      <button onclick="newTranscription()"
        class="flex items-center gap-1.5 h-8 px-3.5 rounded-lg text-xs font-semibold text-white shadow-btn transition-all hover:-translate-y-px hover:shadow-btn-hover"
        style="background:hsl(228 88% 62%);">
        <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        <span id="lbl-new-btn"></span>
      </button>
    </header>

    <!-- Content viewport -->
    <div class="flex-1 relative overflow-hidden">

      <!-- VIEW: UPLOAD -->
      <div id="view-upload" class="view flex items-center justify-center" style="padding:2rem;">
        <div class="w-full max-w-lg flex flex-col gap-5">
          <h1 id="upload-title" class="text-2xl font-bold tracking-tight" style="color:hsl(228 30% 12%);"></h1>

          <!-- Model -->
          <div class="flex items-center gap-3">
            <span id="lbl-model" class="text-xs font-semibold uppercase tracking-wider" style="color:hsl(228 10% 52%);"></span>
            <div class="flex items-center gap-1 rounded-lg p-0.5" style="background:hsl(228 20% 94%); border:1px solid hsl(228 18% 90%);">
              <button id="btn-model-whisper" onclick="setModel('whisper')"
                class="px-3 py-1 rounded-md text-xs font-semibold transition-all bg-white shadow-sm border" style="color:hsl(228 30% 12%); border-color:hsl(228 18% 88%);">Whisper</button>
              <button id="btn-model-parakeet" onclick="setModel('parakeet')"
                class="px-3 py-1 rounded-md text-xs font-semibold transition-all" style="color:hsl(228 10% 52%);">Parakeet</button>
            </div>
            <span id="lbl-model-hint" class="text-xs" style="color:hsl(228 10% 52%);"></span>
          </div>

          <!-- Drop zone -->
          <div id="drop-zone" onclick="document.getElementById('file-input').click()"
            class="flex flex-col items-center justify-center gap-3 py-10 rounded-2xl border-2 border-dashed cursor-pointer transition-all"
            style="border-color:hsl(228 18% 88%); background:#fff;">
            <input id="file-input" type="file" class="hidden"
              accept=".wav,.mp4,.mov,.mp3,.m4a,.flac,.ogg,.aac,.avi,.mkv,.webm" />
            <div class="w-11 h-11 rounded-xl flex items-center justify-center" style="background:hsl(228 88% 97%);">
              <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="hsl(228 88% 62%)" stroke-width="1.8">
                <path stroke-linecap="round" stroke-linejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <div id="drop-text" class="text-center">
              <p id="drop-title" class="text-sm font-semibold" style="color:hsl(228 30% 12%);"></p>
              <p id="drop-sub" class="text-xs mt-0.5" style="color:hsl(228 10% 52%);"></p>
            </div>
            <div id="file-name-display" class="hidden flex-col items-center gap-0.5 text-center">
              <p id="file-name-text" class="text-sm font-semibold" style="color:hsl(228 30% 12%);"></p>
              <p id="file-size-text" class="text-xs" style="color:hsl(228 10% 52%);"></p>
            </div>
          </div>

          <button id="transcribe-btn" disabled onclick="startTranscription()"
            class="flex items-center justify-center w-full h-11 rounded-xl text-sm font-semibold text-white shadow-btn transition-all hover:-translate-y-px hover:shadow-btn-hover disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none"
            style="background:hsl(228 88% 62%);">
            <span id="transcribe-label"></span>
          </button>
        </div>
      </div>

      <!-- VIEW: PROCESSING -->
      <div id="view-processing" class="view hidden-view flex flex-col items-center justify-center gap-8">
        <div class="relative" style="padding:2rem;">
          <div class="absolute inset-0 rounded-full blur-3xl opacity-15" style="background:hsl(228 88% 62%);"></div>
          <div class="flex items-end gap-2 relative" style="height:90px;">
            <div class="wave-bar"></div>
            <div class="wave-bar"></div>
            <div class="wave-bar"></div>
            <div class="wave-bar"></div>
            <div class="wave-bar"></div>
            <div class="wave-bar"></div>
            <div class="wave-bar"></div>
          </div>
        </div>
        <div class="text-center">
          <p id="proc-filename" class="text-base font-semibold mb-1" style="color:hsl(228 30% 12%);"></p>
          <p id="proc-status" class="text-sm" style="color:hsl(228 10% 52%);"></p>
        </div>
        <div id="proc-bar-wrap" class="hidden w-44 h-1 rounded-full overflow-hidden" style="background:hsl(228 18% 90%);">
          <div id="proc-bar" class="h-full rounded-full transition-all duration-300" style="background:hsl(228 88% 62%); width:0%;"></div>
        </div>
        <p id="proc-download-note" class="hidden text-xs text-center" style="color:hsl(228 10% 55%); max-width:270px; line-height:1.5;"></p>
      </div>

      <!-- VIEW: RESULTS -->
      <div id="view-results" class="view hidden-view flex overflow-hidden" style="height:100%;">

        <!-- Left: transcript -->
        <div class="flex flex-col overflow-hidden" style="width:52%; border-right:1px solid hsl(228 18% 90%);">
          <div class="flex-shrink-0 flex items-center gap-1 px-5 py-2.5 bg-white" style="border-bottom:1px solid hsl(228 18% 90%);">
            <button id="tab-full"     onclick="setTranscriptMode('full')"     class="tab-btn active px-3 py-1 rounded-md text-xs font-semibold"></button>
            <button id="tab-subtitle" onclick="setTranscriptMode('subtitle')" class="tab-btn px-3 py-1 rounded-md text-xs font-semibold"></button>
            <button id="tab-txt"      onclick="setTranscriptMode('txt')"      class="tab-btn px-3 py-1 rounded-md text-xs font-semibold"></button>
          </div>
          <div class="flex-1 overflow-y-auto px-5 py-4">
            <pre id="transcript-content" style="color:hsl(228 30% 12%);"></pre>
          </div>
          <!-- Save SRT: subtle footer under transcript -->
          <div class="flex-shrink-0 flex items-center justify-between px-5 py-2.5" style="border-top:1px solid hsl(228 18% 92%);">
            <div id="autosave-badge" class="hidden items-center gap-1.5">
              <svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="#16a34a" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
              </svg>
              <span id="lbl-autosaved" class="text-xs font-medium" style="color:#16a34a;"></span>
            </div>
            <div id="autosave-badge-placeholder" class="flex-1"></div>
            <button onclick="saveSrt()"
              class="flex items-center gap-1.5 px-3 h-7 rounded-lg text-xs font-semibold text-white transition-colors"
              style="background:hsl(228 88% 62%);">
              <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round"
                  d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
              <span id="lbl-save-srt"></span>
            </button>
          </div>
        </div>

        <!-- Right: Final Cut Pro export -->
        <div class="flex flex-col overflow-y-auto px-5 py-5 gap-4 bg-white" style="width:48%;">

          <!-- Section header -->
          <div>
            <p id="cap-settings-lbl" class="text-xs font-semibold uppercase tracking-wider mb-0.5" style="color:hsl(228 10% 52%);"></p>
            <p id="autosave-path" class="text-xs break-all" style="color:hsl(228 10% 68%); display:none;"></p>
          </div>

          <!-- Caption export (was inside a nested div with border-top) -->
          <div>
            <div class="cap-row"><label id="lbl-maxchars"></label><input type="range" id="sl-maxchars" min="8" max="50" value="42" step="1" oninput="document.getElementById('val-maxchars').textContent=this.value" /><span class="val" id="val-maxchars">42</span></div>
            <div class="cap-row"><label id="lbl-mindur"></label><input type="range" id="sl-mindur" min="0.5" max="10" value="1.2" step="0.1" oninput="document.getElementById('val-mindur').textContent=parseFloat(this.value).toFixed(1)" /><span class="val" id="val-mindur">1.2</span></div>
            <div class="cap-row"><label id="lbl-gap"></label><input type="range" id="sl-gap" min="0" max="60" value="0" step="1" oninput="document.getElementById('val-gap').textContent=this.value" /><span class="val" id="val-gap">0</span></div>

            <div class="flex items-center gap-4 my-3 flex-wrap">
              <div class="flex items-center gap-2">
                <span id="lbl-lines" class="text-xs" style="color:hsl(228 10% 52%);"></span>
                <label class="flex items-center gap-1 text-xs cursor-pointer" style="color:hsl(228 30% 12%);">
                  <input type="radio" name="cap-lines" value="1" checked /> <span id="lbl-single"></span>
                </label>
                <label class="flex items-center gap-1 text-xs cursor-pointer" style="color:hsl(228 30% 12%);">
                  <input type="radio" name="cap-lines" value="2" /> <span id="lbl-double"></span>
                </label>
              </div>
              <div class="flex items-center gap-2 ml-auto">
                <span id="lbl-fps" class="text-xs" style="color:hsl(228 10% 52%);"></span>
                <select id="sel-fps" class="text-xs rounded-lg px-2 py-1 focus:outline-none" style="border:1px solid hsl(228 18% 90%); color:hsl(228 30% 12%); background:#fff;">
                  <option value="23.98">23.98</option>
                  <option value="24">24</option>
                  <option value="25">25</option>
                  <option value="29.97">29.97</option>
                  <option value="30" selected>30</option>
                  <option value="60">60</option>
                </select>
              </div>
            </div>

            <div class="flex flex-col gap-2">
              <button id="fcpxml-btn" onclick="generateFcpxml()"
                class="flex items-center justify-center gap-2 w-full h-9 rounded-xl text-xs font-semibold text-white shadow-btn transition-all hover:-translate-y-px hover:shadow-btn-hover disabled:opacity-40 disabled:cursor-not-allowed"
                style="background:hsl(228 88% 62%);">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
                </svg>
                <span id="fcpxml-label"></span>
              </button>
              <button id="openfcp-btn" onclick="openInFcpx()"
                class="flex items-center justify-center gap-2 w-full h-9 rounded-xl text-xs font-semibold transition-all hover:-translate-y-px hover:bg-gl-hover disabled:opacity-40 disabled:cursor-not-allowed"
                style="border:1px solid hsl(228 18% 90%); color:hsl(228 30% 12%); background:#fff;">
                <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
                </svg>
                <span id="openfcp-label"></span>
              </button>
            </div>
          </div>
        </div>

      </div><!-- /view-results -->
    </div><!-- /viewport -->
  </div><!-- /main -->

  <script>
    // i18n
    const T = {
      en: {
        uploadTitle: 'New Transcription',
        desc:        'Drop an audio or video file to generate a <span class="font-medium" style="color:hsl(228 30% 12%);">.srt</span> subtitle file. Powered by Whisper large-v3-turbo &amp; Parakeet TDT 0.6B.',
        dropTitle:   'Drop your file here',
        dropSub:     'or click to browse',
        transcribe:  'Transcribe',
        uploading:   'Uploading\u2026',
        uploadFail:  'Upload failed: ',
        complete:    'Transcription complete!',
        error:       'Something went wrong.',
        statusMap: {
          'Downloading model\u2026': 'Downloading model\u2026',
          'Loading model\u2026':   'Loading model\u2026',
          'Preparing audio\u2026': 'Preparing audio\u2026',
          'Transcribing\u2026':    'Transcribing\u2026',
          'Building SRT\u2026':    'Building SRT\u2026',
        },
        capSettings: 'Final Cut Pro Export',
        maxChars:    'Max chars / line',
        minDur:      'Min duration (s)',
        gapFr:       'Gap (frames)',
        linesLbl:    'Lines',
        single:      'Single',
        double:      'Double',
        fpsLbl:      'FPS',
        genFcpxml:   'Generate FCPXML\u2026',
        generating:  'Generating\u2026',
        openFcp:     'Open in Final Cut Pro',
        opening:     'Opening\u2026',
        modelLbl:    'Model',
        engOnly:     'English only',
        autoDetect:  'Auto-detect language',
        recents:     'Recents',
        noTrans:     'No transcriptions yet',
        newBtn:      'New Transcription',
        headerNew:   'New Transcription',
        saveSrt:     'Save SRT\u2026',
        saveTxt:     'Save TXT\u2026',
        autosaved:   'Auto-saved to Documents',
        downloadNote: 'First-time setup \u2014 downloading the AI model (~2\u00a0GB). This only happens once.',
        tabFull:     'Full SRT',
        tabSub:      'Subtitle',
        tabTxt:      'Plain Text',
      },
      es: {
        uploadTitle: 'Nueva transcripci\u00f3n',
        desc:        'Sube un archivo de audio o video para generar un <span class="font-medium" style="color:hsl(228 30% 12%);">.srt</span> de subt\u00edtulos. Impulsado por Whisper large-v3-turbo &amp; Parakeet TDT 0.6B.',
        dropTitle:   'Suelta tu archivo aqu\u00ed',
        dropSub:     'o haz clic para explorar',
        transcribe:  'Transcribir',
        uploading:   'Subiendo\u2026',
        uploadFail:  'Error al subir: ',
        complete:    '\u00a1Transcripci\u00f3n completa!',
        error:       'Algo sali\u00f3 mal.',
        statusMap: {
          'Downloading model\u2026': 'Descargando modelo\u2026',
          'Loading model\u2026':   'Cargando modelo\u2026',
          'Preparing audio\u2026': 'Preparando audio\u2026',
          'Transcribing\u2026':    'Transcribiendo\u2026',
          'Building SRT\u2026':    'Construyendo SRT\u2026',
        },
        capSettings: 'Exportar a Final Cut Pro',
        maxChars:    'M\u00e1x. car. / l\u00ednea',
        minDur:      'Dur. m\u00ednima (s)',
        gapFr:       'Espacio (frames)',
        linesLbl:    'L\u00edneas',
        single:      'Una',
        double:      'Dos',
        fpsLbl:      'FPS',
        genFcpxml:   'Generar FCPXML\u2026',
        generating:  'Generando\u2026',
        openFcp:     'Abrir en Final Cut Pro',
        opening:     'Abriendo\u2026',
        modelLbl:    'Modelo',
        engOnly:     'Solo ingl\u00e9s',
        autoDetect:  'Detecci\u00f3n autom\u00e1tica',
        recents:     'Recientes',
        noTrans:     'Sin transcripciones',
        newBtn:      'Nueva transcripci\u00f3n',
        headerNew:   'Nueva transcripci\u00f3n',
        saveSrt:     'Guardar SRT\u2026',
        saveTxt:     'Guardar TXT\u2026',
        autosaved:   'Guardado en Documentos',
        downloadNote: 'Configuraci\u00f3n inicial \u2014 descargando el modelo de IA (~2\u00a0GB). Solo ocurre una vez.',
        tabFull:     'SRT completo',
        tabSub:      'Subt\u00edtulo',
        tabTxt:      'Texto plano',
      },
    };

    let currentLang    = localStorage.getItem('st_lang') || (navigator.language.startsWith('es') ? 'es' : 'en');
    let selectedModel  = 'whisper';
    let selectedFile   = null;
    let pollInterval   = null;
    let currentJobId   = null;
    let currentSrt     = { full: '', subtitle: '', txt: '' };
    let transcriptMode = 'full';

    const VIEWS = ['view-upload', 'view-processing', 'view-results'];
    function showView(id) {
      VIEWS.forEach(v => {
        document.getElementById(v).classList.toggle('hidden-view', v !== id);
      });
    }

    function applyLang() {
      const t = T[currentLang];
      localStorage.setItem('st_lang', currentLang);
      document.getElementById('upload-title').textContent     = t.uploadTitle;
      document.getElementById('drop-title').textContent       = t.dropTitle;
      document.getElementById('drop-sub').textContent         = t.dropSub;
      document.getElementById('transcribe-label').textContent = t.transcribe;
      document.getElementById('lbl-model').textContent        = t.modelLbl;
      document.getElementById('lbl-model-hint').textContent   = selectedModel === 'whisper' ? t.autoDetect : t.engOnly;
      document.getElementById('lang-toggle').textContent      = currentLang === 'en' ? 'EN / ES' : 'ES / EN';
      document.getElementById('lbl-recents').textContent      = t.recents;
      document.getElementById('sidebar-empty').textContent    = t.noTrans;
      document.getElementById('lbl-new-btn').textContent      = t.newBtn;
      document.getElementById('cap-settings-lbl').textContent = t.capSettings;
      document.getElementById('lbl-maxchars').textContent     = t.maxChars;
      document.getElementById('lbl-mindur').textContent       = t.minDur;
      document.getElementById('lbl-gap').textContent          = t.gapFr;
      document.getElementById('lbl-lines').textContent        = t.linesLbl;
      document.getElementById('lbl-single').textContent       = t.single;
      document.getElementById('lbl-double').textContent       = t.double;
      document.getElementById('lbl-fps').textContent          = t.fpsLbl;
      document.getElementById('fcpxml-label').textContent     = t.genFcpxml;
      document.getElementById('openfcp-label').textContent    = t.openFcp;
      document.getElementById('lbl-autosaved').textContent    = t.autosaved;
      document.getElementById('proc-download-note').textContent = t.downloadNote;
      document.getElementById('lbl-save-srt').textContent     = t.saveSrt;
      document.getElementById('tab-full').textContent         = t.tabFull;
      document.getElementById('tab-subtitle').textContent     = t.tabSub;
      document.getElementById('tab-txt').textContent          = t.tabTxt;
    }

    function toggleLang() {
      currentLang = currentLang === 'en' ? 'es' : 'en';
      applyLang();
    }

    function setModel(model) {
      selectedModel = model;
      const aCls = 'px-3 py-1 rounded-md text-xs font-semibold transition-all bg-white shadow-sm border';
      const iCls = 'px-3 py-1 rounded-md text-xs font-semibold transition-all';
      const aStyle = 'color:hsl(228 30% 12%); border-color:hsl(228 18% 88%);';
      const iStyle = 'color:hsl(228 10% 52%);';
      const wb = document.getElementById('btn-model-whisper');
      const pb = document.getElementById('btn-model-parakeet');
      wb.className = model === 'whisper'  ? aCls : iCls; wb.style.cssText = model === 'whisper'  ? aStyle : iStyle;
      pb.className = model === 'parakeet' ? aCls : iCls; pb.style.cssText = model === 'parakeet' ? aStyle : iStyle;
      document.getElementById('lbl-model-hint').textContent = model === 'whisper' ? T[currentLang].autoDetect : T[currentLang].engOnly;
    }

    function onFileSelected(file) {
      if (!file) return;
      selectedFile = file;
      const mb = (file.size / 1048576).toFixed(1);
      document.getElementById('drop-text').classList.add('hidden');
      document.getElementById('file-name-display').classList.remove('hidden');
      document.getElementById('file-name-display').style.display = 'flex';
      document.getElementById('file-name-text').textContent = file.name;
      document.getElementById('file-size-text').textContent = mb + ' MB';
      document.getElementById('transcribe-btn').disabled = false;
    }

    const dz = document.getElementById('drop-zone');
    dz.addEventListener('dragover',  e => { e.preventDefault(); dz.classList.add('drag-over'); });
    dz.addEventListener('dragleave', ()  => dz.classList.remove('drag-over'));
    dz.addEventListener('drop', e => {
      e.preventDefault(); dz.classList.remove('drag-over');
      const f = e.dataTransfer.files[0];
      if (f) onFileSelected(f);
    });
    document.getElementById('file-input').addEventListener('change', e => {
      if (e.target.files[0]) onFileSelected(e.target.files[0]);
    });

    function newTranscription() {
      if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }
      selectedFile = null; currentJobId = null;
      document.getElementById('file-input').value = '';
      document.getElementById('drop-text').classList.remove('hidden');
      document.getElementById('file-name-display').classList.add('hidden');
      document.getElementById('transcribe-btn').disabled = true;
      document.getElementById('header-title').textContent = T[currentLang].headerNew;
      setActiveSidebarItem(null);
      showView('view-upload');
    }

    function xlate(raw) { return (T[currentLang].statusMap[raw] || raw); }

    async function startTranscription() {
      if (!selectedFile) return;
      const t = T[currentLang];
      document.getElementById('proc-filename').textContent = selectedFile.name;
      document.getElementById('proc-status').textContent   = t.uploading;
      document.getElementById('proc-bar-wrap').classList.add('hidden');
      document.getElementById('proc-download-note').classList.add('hidden');
      showView('view-processing');

      const form = new FormData();
      form.append('file', selectedFile);
      form.append('model', selectedModel);

      let jobId;
      try {
        const res  = await fetch('/transcribe', { method: 'POST', body: form });
        const data = await res.json();
        jobId = data.job_id;
      } catch (err) {
        showView('view-upload');
        alert(t.uploadFail + err.message);
        return;
      }

      pollInterval = setInterval(async () => {
        try {
          const res  = await fetch('/status/' + jobId);
          const data = await res.json();
          if (data.status === 'done') {
            clearInterval(pollInterval); pollInterval = null;
            currentJobId = jobId;
            const sr  = await fetch('/srt/' + jobId);
            const sd  = await sr.json();
            loadResultsData(sd, data.auto_save_path, jobId, data.original_filename);
            loadHistory();
          } else if (data.status === 'error') {
            clearInterval(pollInterval); pollInterval = null;
            showView('view-upload');
            alert(data.error || t.error);
          } else {
            document.getElementById('proc-status').textContent = xlate(data.status);
            const isDownloading = data.status === 'Downloading model\u2026';
            document.getElementById('proc-download-note').classList.toggle('hidden', !isDownloading);
            if (data.progress) {
              const pct = Math.round((data.progress.current / data.progress.total) * 100);
              document.getElementById('proc-bar-wrap').classList.remove('hidden');
              document.getElementById('proc-bar').style.width = pct + '%';
            }
          }
        } catch (_) {}
      }, 800);
    }

    function loadResultsData(srtData, autoSavePath, jobId, filename) {
      const txt = (srtData.srt || '').trim().split(/\\n\\n+/).map(b => {
        const ls = b.split('\\n'); return ls.slice(2).join(' ');
      }).filter(Boolean).join('\\n\\n');
      currentSrt = { full: srtData.srt || '', subtitle: srtData.srt_subtitle || srtData.srt || '', txt };
      setTranscriptMode('full');
      const badge = document.getElementById('autosave-badge');
      const placeholder = document.getElementById('autosave-badge-placeholder');
      if (autoSavePath) {
        badge.classList.remove('hidden'); badge.style.display = 'flex';
        placeholder.style.display = 'none';
      } else {
        badge.classList.add('hidden');
        placeholder.style.display = '';
      }
      const title = filename || srtData.filename || 'Transcription';
      document.getElementById('header-title').textContent = title;
      showView('view-results');
    }

    function setTranscriptMode(mode) {
      transcriptMode = mode;
      document.getElementById('transcript-content').textContent = currentSrt[mode] || '';
      ['full','subtitle','txt'].forEach(m => {
        const id  = m === 'subtitle' ? 'tab-subtitle' : m === 'txt' ? 'tab-txt' : 'tab-full';
        const btn = document.getElementById(id);
        btn.classList.toggle('active', m === mode);
      });
      const t = T[currentLang];
      document.getElementById('lbl-save-srt').textContent = mode === 'txt' ? t.saveTxt : t.saveSrt;
    }

    async function saveSrt() {
      if (!currentJobId) return;
      const mode = transcriptMode === 'full' ? 'full' : transcriptMode === 'subtitle' ? 'subtitle' : 'txt';
      try {
        const r = await window.pywebview.api.save_srt(currentJobId, mode);
        if (!r.ok && r.error && r.error !== 'Cancelled') alert(r.error);
      } catch (e) { alert(e.message); }
    }

    function captionParams() {
      return [
        currentJobId,
        parseInt(document.getElementById('sl-maxchars').value, 10),
        parseFloat(document.getElementById('sl-mindur').value),
        parseInt(document.getElementById('sl-gap').value, 10),
        parseInt(document.querySelector('input[name="cap-lines"]:checked').value, 10),
        document.getElementById('sel-fps').value,
      ];
    }

    async function generateFcpxml() {
      const t = T[currentLang]; const btn = document.getElementById('fcpxml-btn'); const lbl = document.getElementById('fcpxml-label');
      btn.disabled = true; lbl.textContent = t.generating;
      try {
        const r = await window.pywebview.api.save_fcpxml(...captionParams());
        if (!r.ok && r.error && r.error !== 'Cancelled') alert(r.error);
      } catch (e) { alert(e.message); }
      finally { btn.disabled = false; lbl.textContent = t.genFcpxml; }
    }

    async function openInFcpx() {
      const t = T[currentLang]; const btn = document.getElementById('openfcp-btn'); const lbl = document.getElementById('openfcp-label');
      btn.disabled = true; lbl.textContent = t.opening;
      try {
        const r = await window.pywebview.api.open_in_fcpx(...captionParams());
        if (!r.ok) alert(r.error);
      } catch (e) { alert(e.message); }
      finally { btn.disabled = false; lbl.textContent = t.openFcp; }
    }

    // Sidebar
    let sidebarHistory = [];

    function relativeDate(iso) {
      const d = new Date(iso); const now = new Date(); const diff = (now - d) / 1000;
      if (diff < 60)    return 'Just now';
      if (diff < 3600)  return Math.floor(diff/60) + 'm ago';
      if (diff < 86400) return Math.floor(diff/3600) + 'h ago';
      return d.toLocaleDateString(currentLang === 'es' ? 'es-ES' : 'en-US', { month: 'short', day: 'numeric' });
    }

    function renderSidebar(history) {
      sidebarHistory = history;
      const list  = document.getElementById('sidebar-list');
      const empty = document.getElementById('sidebar-empty');
      Array.from(list.querySelectorAll('.sidebar-item')).forEach(el => el.remove());
      empty.style.display = history.length ? 'none' : '';
      history.forEach(rec => {
        const item = document.createElement('div');
        item.className = 'sidebar-item flex items-center gap-0 rounded-lg cursor-pointer';
        item.setAttribute('data-id', rec.id);
        item.innerHTML = `
          <div class="item-bar mr-2" style="height:36px;min-height:36px;"></div>
          <div class="py-2 pr-2 min-w-0 flex-1">
            <p class="text-xs font-medium truncate" style="color:hsl(228 15% 76%);" title="${rec.filename}">${rec.filename}</p>
            <p class="text-xs mt-0.5" style="color:hsl(228 10% 42%);">${relativeDate(rec.created_at)}&nbsp;&middot;&nbsp;${rec.model === 'whisper' ? 'W' : 'P'}</p>
          </div>`;
        item.addEventListener('mouseenter', () => { if (!item.classList.contains('active')) item.style.background = 'hsl(228 22% 15%)'; });
        item.addEventListener('mouseleave', () => { if (!item.classList.contains('active')) item.style.background = ''; });
        item.addEventListener('click', () => loadHistoryItem(rec));
        list.insertBefore(item, empty);
      });
    }

    function setActiveSidebarItem(id) {
      document.querySelectorAll('.sidebar-item').forEach(el => {
        const isActive = el.getAttribute('data-id') === id;
        el.classList.toggle('active', isActive);
        el.style.background = isActive ? 'hsl(228 30% 20%)' : '';
      });
    }

    async function loadHistoryItem(rec) {
      setActiveSidebarItem(rec.id);
      currentJobId = rec.id;
      try {
        const res = await fetch('/srt/' + rec.id);
        if (!res.ok) return;
        const data = await res.json();
        loadResultsData(data, data.auto_save_path, rec.id, rec.filename);
      } catch (_) {}
    }

    async function loadHistory() {
      try {
        const res  = await fetch('/history');
        const data = await res.json();
        renderSidebar(data);
        if (currentJobId) setActiveSidebarItem(currentJobId);
      } catch (_) {}
    }

    // Init
    applyLang();
    loadHistory();
    showView('view-upload');
  </script>
</body>
</html>"""
