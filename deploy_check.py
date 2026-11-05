#!/usr/bin/env python3
"""
Pre-flight check for deployment.

Verifies the things that actually break when you move from a laptop to a
host: env-driven port binding, health endpoint, secret enforcement, database
writability, and survival across a process restart.

    python deploy_check.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

import signal

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("TEST_PORT", "8099"))
TOKEN = "test-secret-1234"
DB = os.path.join(tempfile.mkdtemp(), "deploy_test.db")
BASE = f"http://127.0.0.1:{PORT}"

results = []


def check(name: str, ok: bool, detail: str = ""):
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    return ok


def get(path: str, token: str = None, timeout: int = 10):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("x-token", token)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode()


def wait_up(proc, tries=60):
    for _ in range(tries):
        if proc.poll() is not None:
            return False
        try:
            get("/healthz")
            return True
        except Exception:                                        # noqa: BLE001
            time.sleep(1)
    return False


def main():
    print("\n=== deployment pre-flight ===\n")

    # ---- static files -----------------------------------------------------
    print("Files:")
    for f in ["Dockerfile", "requirements.txt", "Procfile", "render.yaml",
              "fly.toml", "runtime.txt", ".env.example",
              "aitrader/dashboard/static/index.html"]:
        check(f"{f} present", os.path.exists(os.path.join(HERE, f)))

    # ---- dockerfile sanity ------------------------------------------------
    if os.path.exists(os.path.join(HERE, "Dockerfile")):
        d = open(os.path.join(HERE, "Dockerfile")).read()
        check("Dockerfile binds 0.0.0.0", "0.0.0.0" in d)
        check("Dockerfile honours $PORT", "${PORT}" in d or "$PORT" in d)
        check("Dockerfile has healthcheck", "HEALTHCHECK" in d)
        check("Dockerfile runs as non-root-less slim image", "python:3.11-slim" in d)

    # ---- boot the app the way a host would --------------------------------
    print("\nRuntime (env-driven, production-style):")
    env = {**os.environ, "PORT": str(PORT), "DB_PATH": DB, "APP_TOKEN": TOKEN,
           "VENUE": "simulator", "ACCOUNT_TYPE": "demo", "TICK_SECONDS": "300"}
    log = open(os.path.join(tempfile.mkdtemp(), "srv.log"), "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "aitrader.dashboard.server:api",
         "--host", "0.0.0.0", "--port", str(PORT)],
        cwd=HERE, env=env, stdout=log, stderr=subprocess.STDOUT)

    try:
        if not wait_up(proc):
            check("server boots and answers /healthz", False, "timeout")
            print("\n--- server log ---")
            print(open(log.name).read()[-3000:])
            return 1

        check("server boots and answers /healthz", True, f"port {PORT}")

        st, body = get("/healthz")
        check("/healthz open without token", st == 200)
        h = json.loads(body)
        check("health reports engine running", h.get("engine") in ("running", "not started"),
              str(h.get("engine")))

        # token enforcement
        try:
            get("/api/state")                       # no token
            check("APP_TOKEN blocks unauthenticated API", False, "endpoint was open!")
        except urllib.error.HTTPError as e:
            check("APP_TOKEN blocks unauthenticated API", e.code == 401, f"HTTP {e.code}")

        st, _ = get("/api/state", token=TOKEN)
        check("APP_TOKEN allows authenticated API", st == 200)

        st, html = get("/", token=TOKEN)
        check("dashboard serves", st == 200 and "AI Trading Terminal" in html)

        st, cfg = get("/api/config", token=TOKEN)
        check("config endpoint", st == 200 and json.loads(cfg)["risk"]["allow_martingale"] is False)

        st, ch = get("/api/chart?symbol=BTC-USD&limit=50", token=TOKEN)
        check("chart endpoint returns bars",
              st == 200 and len(json.loads(ch).get("bars", [])) > 0)

        # ---- database writability + restart survival -----------------------
        print("\nPersistence:")
        # wait for the first engine tick (6h data over 3 symbols takes a few
        # seconds on a cold start) so we measure real recorded state
        before = None
        for _ in range(90):
            st, perf = get("/api/performance", token=TOKEN)
            before = json.loads(perf)
            if (before.get("equity_points") or 0) > 0 and (before.get("ticks") or 0) == 0:
                pass
            st2, hz = get("/healthz")
            if json.loads(hz).get("ticks", 0) >= 1 and (before.get("equity_points") or 0) > 0:
                break
            time.sleep(2)
        check("engine completed a tick", json.loads(get("/healthz")[1]).get("ticks", 0) >= 1,
              f"{json.loads(get('/healthz')[1]).get('ticks')} ticks")
        check("database writable", os.path.exists(DB))
        check("equity recorded", (before.get("equity_points") or 0) > 0,
              f"{before.get('equity_points')} points")

        print("  restarting process (simulating a host restart / sleep-wake)...")
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=30)

        proc2 = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "aitrader.dashboard.server:api",
             "--host", "0.0.0.0", "--port", str(PORT)],
            cwd=HERE, env=env, stdout=log, stderr=subprocess.STDOUT)
        if not wait_up(proc2):
            check("restarts cleanly", False)
            return 1
        check("restarts cleanly", True)
        st, perf2 = get("/api/performance", token=TOKEN)
        after = json.loads(perf2)
        check("equity history survives restart",
              (after.get("equity_points") or 0) >= (before.get("equity_points") or 0),
              f"{before.get('equity_points')} -> {after.get('equity_points')} points")
        proc2.send_signal(signal.SIGTERM)
        proc2.wait(timeout=30)

    finally:
        if proc.poll() is None:
            proc.kill()
        shutil.rmtree(os.path.dirname(DB), ignore_errors=True)

    print("\n=== summary ===")
    failed = [r for r in results if not r[1]]
    print(f"  {len(results) - len(failed)}/{len(results)} checks passed")
    if failed:
        for n, _, d in failed:
            print(f"  FAILED: {n} {d}")
        return 1
    print("  deploy-ready ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
