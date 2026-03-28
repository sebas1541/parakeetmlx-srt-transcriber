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
  <title>Parakeet Transcriber</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet" />
  <script>
    tailwind.config = {
      theme: {
        extend: {
          fontFamily: { sans: ['Inter', 'ui-sans-serif', 'system-ui'] },
          colors: {
            primary:    'hsl(228 88% 66%)',
            'primary-hover': 'hsl(228 88% 58%)',
            'primary-soft':  'hsl(228 88% 96%)',
            'gl-bg':    'hsl(228 25% 97%)',
            'gl-card':  '#ffffff',
            'gl-fg':    'hsl(228 30% 14%)',
            'gl-muted': 'hsl(228 10% 55%)',
            'gl-border':'hsl(228 20% 92%)',
          },
          borderRadius: { xl2: '1rem' },
          boxShadow: {
            card: '0 1px 3px 0 rgba(0,0,0,.06), 0 1px 2px -1px rgba(0,0,0,.04)',
            btn:  '0 1px 2px rgba(91,122,247,.25)',
            'btn-hover': '0 6px 16px rgba(91,122,247,.35)',
          },
        }
      }
    }
  </script>
  <style>
    body { -webkit-font-smoothing: antialiased; }
    #drop-zone.drag-over {
      border-color: hsl(228 88% 66%) !important;
      background: hsl(228 88% 96%) !important;
    }
    .spinner {
      width: 18px; height: 18px;
      border: 2px solid rgba(255,255,255,.35);
      border-top-color: #fff;
      border-radius: 9999px;
      animation: spin .7s linear infinite;
      display: none;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    #transcribe-btn.loading .spinner  { display: block; }
    #transcribe-btn.loading .btn-label { display: none; }
    #transcribe-btn.loading { opacity: .85; cursor: not-allowed; pointer-events: none; }
  </style>
</head>
<body class="bg-gl-bg font-sans min-h-screen flex items-start justify-center pt-16 px-4">

  <div class="w-full max-w-lg">

    <!-- Header -->
    <div class="mb-8">
      <div class="flex items-center justify-between mb-2">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-xl bg-primary flex items-center justify-center shadow-btn">
            <svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round"
                d="M12 18.75a6 6 0 0 0 6-6v-1.5m-6 7.5a6 6 0 0 1-6-6v-1.5m6 7.5v3.75m-3.75 0h7.5M12 15.75a3 3 0 0 1-3-3V4.5a3 3 0 1 1 6 0v8.25a3 3 0 0 1-3 3Z" />
            </svg>
          </div>
          <h1 class="text-xl font-semibold tracking-tight text-gl-fg">Parakeet Transcriber</h1>
        </div>
        <button id="lang-toggle" onclick="toggleLang()"
          class="text-[11px] font-semibold text-gl-muted hover:text-gl-fg border border-gl-border rounded-lg px-2.5 py-1 transition-colors duration-150 hover:border-primary hover:bg-primary-soft">
          EN / ES
        </button>
      </div>
      <p id="desc-text" class="text-sm text-gl-muted leading-relaxed pl-0.5"></p>
    </div>

    <!-- Card -->
    <div class="bg-gl-card rounded-2xl border border-gl-border shadow-card overflow-hidden">

      <!-- Drop zone -->
      <div class="p-5 border-b border-gl-border">
        <div
          id="drop-zone"
          class="relative flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-gl-border bg-gl-bg px-6 py-10 transition-colors duration-150 cursor-pointer hover:border-primary hover:bg-primary-soft"
          onclick="document.getElementById('file-input').click()"
        >
          <input id="file-input" type="file" class="hidden"
            accept=".mp3,.mp4,.wav,.m4a,.mov,.flac,.ogg,.aac,.mkv,.webm" />

          <div id="drop-icon" class="w-10 h-10 rounded-xl bg-white border border-gl-border shadow-card flex items-center justify-center">
            <svg class="w-5 h-5 text-gl-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
              <path stroke-linecap="round" stroke-linejoin="round"
                d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5" />
            </svg>
          </div>

          <div id="drop-text" class="text-center">
            <p id="drop-title" class="text-sm font-medium text-gl-fg"></p>
            <p id="drop-sub" class="text-xs text-gl-muted mt-0.5"></p>
          </div>

          <div id="file-name-display" class="hidden text-center">
            <p class="text-sm font-semibold text-gl-fg" id="file-name-text"></p>
            <p class="text-xs text-gl-muted mt-0.5" id="file-size-text"></p>
          </div>

          <p class="text-[11px] text-gl-muted mt-1">mp3 · mp4 · wav · m4a · mov · flac</p>
        </div>
      </div>

      <!-- Action row -->
      <div class="px-5 py-4 flex flex-col gap-3">
        <button
          id="transcribe-btn"
          disabled
          class="flex items-center justify-center gap-2.5 w-full h-11 rounded-xl bg-primary text-white text-sm font-semibold tracking-tight shadow-btn transition-all duration-150 hover:bg-primary-hover hover:-translate-y-px hover:shadow-btn-hover active:translate-y-0 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none"
          onclick="startTranscription()"
        >
          <div class="spinner"></div>
          <span class="btn-label" id="transcribe-label"></span>
        </button>

        <!-- Status -->
        <div id="status-area" class="hidden">
          <div id="status-row" class="flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl bg-gl-bg border border-gl-border">
            <div id="status-spinner" class="hidden w-4 h-4 border-2 border-gl-border border-t-primary rounded-full animate-spin flex-shrink-0"></div>
            <svg id="status-check" class="hidden w-4 h-4 text-emerald-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
              <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" />
            </svg>
            <svg id="status-error-icon" class="hidden w-4 h-4 text-red-500 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
            <p id="status-text" class="text-sm text-gl-muted"></p>
          </div>
        </div>

        <!-- View / Save -->
        <button
          id="download-btn"
          class="hidden items-center justify-center gap-2 w-full h-11 rounded-xl border border-gl-border bg-white text-sm font-semibold text-gl-fg shadow-card transition-all duration-150 hover:border-primary hover:text-primary hover:bg-primary-soft"
        >
          <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
          </svg>
          <span id="view-save-label"></span>
        </button>
      </div>
    </div>


  </div>

  <script>
    // ── i18n ────────────────────────────────────────────────────────────────
    const T = {
      en: {
        desc:        'Drop an audio or video file to generate a downloadable <span class="font-medium text-gl-fg">.srt</span> subtitle file. Powered by Parakeet TDT 0.6B\u00a0v3.',
        dropTitle:   'Drop your file here',
        dropSub:     'or click to browse',
        transcribe:  'Transcribe',
        viewSave:    'View\u00a0& Save SRT',
        uploading:   'Uploading file\u2026',
        uploadFail:  'Upload failed: ',
        complete:    'Transcription complete!',
        error:       'Something went wrong.',
        statusMap: {
          'Loading model':    'Loading model\u2026',
          'Preparing audio':  'Preparing audio\u2026',
          'Transcribing':     'Transcribing\u2026',
          'Building SRT':     'Building SRT\u2026',
        },
      },
      es: {
        desc:        'Sube un archivo de audio o video para generar un archivo <span class="font-medium text-gl-fg">.srt</span> de subtítulos. Impulsado por Parakeet TDT 0.6B\u00a0v3.',
        dropTitle:   'Suelta tu archivo aquí',
        dropSub:     'o haz clic para explorar',
        transcribe:  'Transcribir',
        viewSave:    'Ver\u00a0y guardar SRT',
        uploading:   'Subiendo archivo\u2026',
        uploadFail:  'Error al subir: ',
        complete:    '\u00a1Transcripción completa!',
        error:       'Algo salió mal.',
        statusMap: {
          'Loading model':    'Cargando modelo\u2026',
          'Preparing audio':  'Preparando audio\u2026',
          'Transcribing':     'Transcribiendo\u2026',
          'Building SRT':     'Construyendo SRT\u2026',
        },
      },
    };

    function detectLang() {
      const saved = localStorage.getItem('pt_lang');
      if (saved) return saved;
      return navigator.language.startsWith('es') ? 'es' : 'en';
    }

    let currentLang = detectLang();

    function applyLang() {
      const t = T[currentLang];
      localStorage.setItem('pt_lang', currentLang);
      document.getElementById('desc-text').innerHTML  = t.desc;
      document.getElementById('drop-title').textContent = t.dropTitle;
      document.getElementById('drop-sub').textContent   = t.dropSub;
      document.getElementById('transcribe-label').textContent = t.transcribe;
      document.getElementById('view-save-label').textContent  = t.viewSave;
      document.getElementById('lang-toggle').textContent =
        currentLang === 'en' ? 'EN / ES' : 'ES / EN';
    }

    function toggleLang() {
      currentLang = currentLang === 'en' ? 'es' : 'en';
      applyLang();
    }

    function xlate(serverMsg) {
      const map = T[currentLang].statusMap;
      for (const [key, val] of Object.entries(map)) {
        if (serverMsg.includes(key)) return val;
      }
      return serverMsg;
    }

    // ── Drop zone wiring ────────────────────────────────────────────────────
    let selectedFile = null;
    let pollInterval = null;

    const dropZone  = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');

    dropZone.addEventListener('dragover', e => {
      e.preventDefault();
      dropZone.classList.add('drag-over');
    });
    ['dragleave', 'dragend'].forEach(ev =>
      dropZone.addEventListener(ev, () => dropZone.classList.remove('drag-over'))
    );
    dropZone.addEventListener('drop', e => {
      e.preventDefault();
      dropZone.classList.remove('drag-over');
      const f = e.dataTransfer.files[0];
      if (f) setFile(f);
    });
    fileInput.addEventListener('change', () => {
      if (fileInput.files[0]) setFile(fileInput.files[0]);
    });

    function setFile(f) {
      selectedFile = f;
      const mb = (f.size / 1024 / 1024).toFixed(1);
      document.getElementById('file-name-text').textContent = f.name;
      document.getElementById('file-size-text').textContent = mb + ' MB';
      document.getElementById('drop-text').classList.add('hidden');
      document.getElementById('file-name-display').classList.remove('hidden');
      document.getElementById('transcribe-btn').disabled = false;
      document.getElementById('download-btn').classList.add('hidden');
      document.getElementById('download-btn').classList.remove('flex');
      setStatus(null);
    }

    // ── Status helpers ──────────────────────────────────────────────────────
    function setStatus(msg, state = 'loading') {
      const area    = document.getElementById('status-area');
      const spinner = document.getElementById('status-spinner');
      const check   = document.getElementById('status-check');
      const errIcon = document.getElementById('status-error-icon');
      const text    = document.getElementById('status-text');

      if (!msg) { area.classList.add('hidden'); return; }
      area.classList.remove('hidden');

      spinner.classList.toggle('hidden', state !== 'loading');
      check.classList.toggle('hidden',   state !== 'done');
      errIcon.classList.toggle('hidden', state !== 'error');
      text.textContent = msg;
      text.className = state === 'error'
        ? 'text-sm text-red-500'
        : state === 'done'
          ? 'text-sm text-emerald-600 font-medium'
          : 'text-sm text-gl-muted';
    }

    // ── Transcription ───────────────────────────────────────────────────────
    async function startTranscription() {
      if (!selectedFile) return;
      const t   = T[currentLang];
      const btn = document.getElementById('transcribe-btn');
      btn.classList.add('loading');
      setStatus(t.uploading);

      const form = new FormData();
      form.append('file', selectedFile);

      let jobId;
      try {
        const res  = await fetch('/transcribe', { method: 'POST', body: form });
        const data = await res.json();
        jobId = data.job_id;
      } catch (err) {
        btn.classList.remove('loading');
        setStatus(t.uploadFail + err.message, 'error');
        return;
      }

      pollInterval = setInterval(async () => {
        try {
          const res  = await fetch('/status/' + jobId);
          const data = await res.json();

          if (data.status === 'done') {
            clearInterval(pollInterval);
            btn.classList.remove('loading');
            setStatus(T[currentLang].complete, 'done');
            const dlBtn = document.getElementById('download-btn');
            dlBtn.onclick = () => { window.location.href = '/view/' + jobId; };
            dlBtn.classList.remove('hidden');
            dlBtn.classList.add('flex');
          } else if (data.status === 'error') {
            clearInterval(pollInterval);
            btn.classList.remove('loading');
            setStatus(data.error || T[currentLang].error, 'error');
          } else {
            setStatus(xlate(data.status));
          }
        } catch (_) {}
      }, 800);
    }

    // ── Init ────────────────────────────────────────────────────────────────
    applyLang();
  </script>
</body>
</html>"""
