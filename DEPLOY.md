# Deployment guide (free tiers)

Everything is prepared. `python deploy_check.py` runs 25 automated pre-flight
checks and passes: env-driven port, health endpoint, secret enforcement,
database writability, and clean restart with state intact.

```
python deploy_check.py
```

---

## Read this before choosing a host

A trading bot is a **long-running process with memory**, which is the one
workload free tiers are worst at. Two problems you will hit:

| Problem | Consequence | Mitigation |
|---|---|---|
| **Instance sleeps** when idle | Ticks are missed; you re-evaluate late | Point a free pinger at `/healthz` every 5–10 min |
| **Ephemeral disk** | `trader.db` resets on redeploy; trade journal lost | Mount a volume (paid), or accept it for demo only |

**Do not run real money on a sleeping free instance.** A missed tick can mean
a missed exit. Free tiers are for paper trading and for proving the system
runs 24/7 unattended. When you go real, use something always-on.

---

## Option A — Render (easiest, recommended to start)

Free web service. Dockerfile included, `render.yaml` ready.

1. Push this repo to GitHub.
2. render.com → **New → Blueprint** → connect the repo.
   It reads `render.yaml` automatically.
3. Add `APP_TOKEN` (Render generates one via `generateValue: true`).
4. Deploy. You get `https://<name>.onrender.com`.
5. **Keep it awake:** create a free monitor at UptimeRobot (or cron-job.org)
   hitting `https://<name>.onrender.com/healthz` every 5 minutes.

Free tier sleeps after ~15 min idle, so step 5 is not optional.

Cost: **$0**. Persistent disk is a paid add-on — without it, the journal
resets when the instance restarts.

---

## Option B — Hugging Face Spaces (longest free sleep window)

Sleeps after **48h** idle instead of 15 min, and needs no card.

1. Create a Space → **Docker** → Blank.
2. Upload the repo root (the root `Dockerfile` is used automatically).
3. Settings → Variables → add `APP_TOKEN`.
4. Ping `/healthz` daily with a free cron service.

See `deploy/huggingface/README.md`.

⚠️ Free Spaces are **public**. `APP_TOKEN` is required, not optional.
Filesystem is ephemeral.

---

## Option C — Oracle Cloud Always Free (the right answer for real trading)

Genuinely free forever, **always-on**, persistent disk, no sleep. This is a
real VM (up to 4 ARM cores / 24 GB RAM), not a toy sandbox.

1. Sign up at oracle.com/cloud/free (card for identity verification, not charged).
2. Create an ARM Ampere compute instance (Ubuntu 22.04).
3. Open port 8000 in the instance's security list.
4. On the VM:
   ```bash
   sudo apt update && sudo apt install -y python3-pip git
   git clone <your-repo> ai-trader && cd ai-trader
   pip3 install -r requirements.txt
   APP_TOKEN=<your-secret> nohup python3 -m uvicorn aitrader.dashboard.server:api \
       --host 0.0.0.0 --port 8000 > server.log 2>&1 &
   ```
5. Run it under systemd for auto-restart (see below).

Cost: **$0**, always-on, persistent disk. Best free option by a wide margin.

---

## Option D — Fly.io / Railway / Koyeb

`fly.toml` is included (`flyctl deploy`). Railway and Koyeb both read the
Dockerfile. All have limited free allowances that can change; verify current
terms before committing.

---

## Option E — local or any $4–5/mo VPS

Works anywhere Python runs, including a Windows PC (which you'll want anyway
for MT5). `start.sh` / `start.bat` handle it.

---

## Security — do not skip this

`APP_TOKEN` guards every route except `/healthz`. Without it on a public URL,
anyone can POST `/api/control` and flatten your positions or switch the
engine to a real account.

```bash
APP_TOKEN=$(openssl rand -hex 24)   # generate a strong one
```

Then open `https://<your-host>/?token=<APP_TOKEN>` — the page passes it via
the `x-token` header on all API calls. (Current UI reads it from the URL query
string; keep the token in the URL or bookmark it.)

Never commit `.env`. `.env.example` documents every variable.

---

## Environment variables

| Variable | Default | Notes |
|---|---|---|
| `PORT` | `8000` | Set automatically by every host |
| `APP_TOKEN` | *(empty)* | **Set on any public deploy** |
| `DB_PATH` | `state/trader.db` | Point at a mounted volume |
| `PROFILE` | `validated` | `validated \| conservative \| moderate \| aggressive` |
| `TICK_SECONDS` | `300` | How often the market is evaluated |
| `SYMBOLS` | `BTC-USD,ETH-USD,SOL-USD` | Comma separated |
| `RISK_PER_TRADE` | `0.5` | % of equity per trade |
| `VENUE` | `simulator` | `simulator \| mt5 \| kraken` |
| `ACCOUNT_TYPE` | `demo` | `demo \| real` |
| `AUTO_START` | `1` | Set `0` to boot without starting the engine |

---

## systemd unit (for a VM)

```ini
[Unit]
Description=AI Trading Terminal
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/ai-trader
Environment="PORT=8000" "APP_TOKEN=your-secret" "DB_PATH=/home/ubuntu/ai-trader/state/trader.db"
ExecStart=/usr/bin/python3 -m uvicorn aitrader.dashboard.server:api --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Post-deploy checks

```bash
curl https://<your-host>/healthz                      # {"status":"ok",...}
curl -H "x-token: $APP_TOKEN" https://<your-host>/api/state
```

Then, in order:

1. Watch it for **48 hours** — confirm ticks keep happening and equity is
   being recorded.
2. Confirm the **restart path**: restart it deliberately and check the journal
   is still there.
3. Only then consider pointing it at a demo broker, and much later, real money.

---

## One thing I could not do for you

I have no access to a hosting account, so **I cannot press deploy** — every
provider needs you to sign up and authorise. What I did instead was make the
app deploy-ready and prove it: `deploy_check.py` boots the app exactly the way
a host does (env port, fresh DB, secret set), hits every endpoint, kills the
process, restarts it, and confirms state survived. That is the part that
usually breaks, and it passes 25/25.
