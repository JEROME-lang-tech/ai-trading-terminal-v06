#!/usr/bin/env python3
"""
Entry point for the packaged executable and for any WSGI/ASGI host.

Running the built binary starts the trading terminal on http://localhost:8000
with no Python installation required.
"""

from __future__ import annotations

import os
import sys
import webbrowser
import threading


def main():
    port = int(os.environ.get("PORT", "8000"))
    host = os.environ.get("HOST", "0.0.0.0")

    import uvicorn
    from aitrader.dashboard.server import api

    url = f"http://localhost:{port}"
    if os.environ.get("APP_TOKEN"):
        url += f"/?token={os.environ['APP_TOKEN']}"

    # Open the browser shortly after startup, unless told not to
    # (servers, CI, and headless hosts must set NO_BROWSER=1).
    if not os.environ.get("NO_BROWSER") and sys.stdout.isatty():
        threading.Timer(2.5, lambda: webbrowser.open(url)).start()

    print("=" * 62)
    print("  AI Trading Terminal")
    print("=" * 62)
    print(f"  Dashboard : {url}")
    print(f"  Venue     : {os.environ.get('VENUE', 'simulator')}"
          f"  ({os.environ.get('ACCOUNT_TYPE', 'demo')} account)")
    print(f"  Health    : http://localhost:{port}/healthz")
    print()
    print("  Press Ctrl+C to stop.")
    print("=" * 62)

    uvicorn.run(api, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
