import os
import sys
import threading

# Ensure Homebrew binaries (ffmpeg, etc.) are on PATH inside the .app bundle
os.environ["PATH"] = "/opt/homebrew/bin:/usr/local/bin:" + os.environ.get("PATH", "")

import state
from server import run_server, wait_for_port, PORT


if __name__ == "__main__":
    import webview
    from jsapi import JsApi

    threading.Thread(target=run_server, daemon=True).start()

    if not wait_for_port(PORT):
        sys.exit("Server did not start in time.")

    jsapi      = JsApi()
    win        = webview.create_window(
        title="Super Transcribe",
        url=f"http://127.0.0.1:{PORT}",
        width=1100,
        height=680,
        min_size=(900, 560),
        js_api=jsapi,
    )
    state.window = win

    def _apply_macos26_corners(*args):
        """Apply macOS 26 Tahoe-style window corner radius via AppKit."""
        try:
            w = args[0] if args else win
            content = w.native.contentView()
            if content is not None:
                content.setWantsLayer_(True)
                content.layer().setCornerRadius_(20.0)
                content.layer().setMasksToBounds_(True)
        except Exception:
            pass

    win.events.shown += _apply_macos26_corners
    webview.start()
    sys.exit(0)
