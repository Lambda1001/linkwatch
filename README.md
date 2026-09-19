# linkwatch

A lightweight, terminal-based network latency and packet-loss monitor. `linkwatch` pings three tiers of targets — your ISP gateway, a regional (Nairobi) host, and an intercontinental (Europe) host — on a schedule, stores every result in SQLite, and gives you a CLI to inspect current status, historical summaries, and outages.

The goal: build an honest, long-running record of your actual connection quality, broken down by where in the network path a problem originates.

## Why three tiers?

Pinging a single target only tells you "is the internet up." Pinging three carefully chosen targets tells you **where** a problem is:

- **ISP** — your router/gateway. If this is unhealthy, the problem is local (your Wi-Fi, your cabling, your router).
- **Nairobi / regional** — a host inside Kenya. If ISP is healthy but this isn't, the problem is local ISP routing or peering.
- **Europe** — a fixed, single-location, non-anycast host abroad. If the first two are healthy but this isn't, the problem is international transit.

## Project structure

```
linkwatch/
├── app/
│   ├── __init__.py
│   ├── schema.py       # creates the SQLite schema
│   ├── runner.py       # runs fping against configured targets
│   ├── parser.py       # parses fping output into row dicts
│   ├── db.py            # connection + insert helpers
│   └── queries.py       # read queries used by the CLI
├── cli.py               # linkwatch command-line interface (argparse + rich)
├── main.py              # single collection run: ping targets, parse, insert
├── config.yaml           # targets, intervals, db path
├── pyproject.toml         # packaging config (pip install -e .)
├── data/
│   └── pings.db            # SQLite database (gitignored)
└── tests/
    └── test_parser.py       # parser unit tests
```

## Requirements

- Linux (native, or WSL2 on Windows)
- Python 3.10+
- [`fping`](https://fping.org/) (`sudo apt install fping`)
- `systemd` (for scheduled, unattended collection)

## Setup

```bash
git clone <your-repo-url>
cd linkwatch

python3 -m venv venv
source venv/bin/activate
pip install -e .
```

Edit `config.yaml` with your actual targets:

```yaml
db_path: "data/pings.db"
interval_seconds: 60
targets:
  isp: "192.168.100.1"        # your router/gateway IP
  nairobi: "196.223.21.16"    # a stable local/regional host
  europe: "78.46.170.2"       # a fixed, single-location EU host (e.g. Hetzner: fsn.icmp.hetzner.com)
fping:
  count: 4
  timeout_ms: 2000
```

Initialize the database schema:

```bash
python3 app/schema.py
```

Run one collection cycle manually to confirm everything works:

```bash
python3 main.py
```

Check that rows were inserted:

```bash
sqlite3 data/pings.db "SELECT * FROM pings ORDER BY id DESC LIMIT 10;"
```

## Running continuously (systemd)

`linkwatch` is meant to run unattended, indefinitely, so long-term trends actually mean something. Set it up as a systemd service + timer:

**`/etc/systemd/system/linkwatch.service`**
```ini
[Unit]
Description=Linkwatch ping monitor run
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
User=kevo
WorkingDirectory=/home/kevo/linkwatch
ExecStart=/home/kevo/linkwatch/venv/bin/python3 /home/kevo/linkwatch/main.py
```

**`/etc/systemd/system/linkwatch.timer`**
```ini
[Unit]
Description=Run Linkwatch every minute

[Timer]
OnBootSec=30
OnUnitActiveSec=60
Persistent=true

[Install]
WantedBy=timers.target
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now linkwatch.timer
```

Check it's actually scheduled (should show a real future time under `NEXT`, not a dash):

```bash
systemctl list-timers linkwatch.timer
```

Watch it run live:

```bash
journalctl -u linkwatch.service -f
```

## Using the CLI

Once installed (`pip install -e .`), and optionally symlinked to `~/.local/bin` for global use:

```bash
ln -s ~/linkwatch/venv/bin/linkwatch ~/.local/bin/linkwatch
```

```bash
linkwatch status                          # latest ping results, one row per target
linkwatch summary --hours 24              # avg/min/max RTT and loss over a window
linkwatch outages --hours 48 --threshold 25   # list high-loss events
linkwatch watch --interval 5              # live-refreshing dashboard (Ctrl+C to exit)
```

## Troubleshooting notes

- **`sqlite3.OperationalError: unable to open database file`** — usually a relative-path issue; run scripts from the project root, or use `Path(__file__).resolve().parent` patterns to anchor paths.
- **`IndentationError: unindent does not match any outer indentation level`** — almost always mixed tabs/spaces from editing in nano. Fix with `sed -i 's/\t/    /g' file.py`, and add `set tabstospaces` to `~/.nanorc` to prevent recurrence.
- **`externally-managed-environment` on `pip install`** — Debian/Ubuntu blocking system-wide installs (PEP 668). Use a venv (`python3 -m venv venv && source venv/bin/activate`) rather than `--break-system-packages`.
- **Timer shows `Trigger: n/a` / no scheduled runs** — check for typos in the `.timer` file's directive names (e.g. `OnUnitActiveSec`, not `OnUnitActivateSec`); systemd silently ignores unrecognized keys rather than erroring.
- **A target shows constant 100% loss** — the IP may be dead, blocking ICMP, or was never a reliable single-location host to begin with. See "Choosing targets" below.

## Choosing targets

- **Avoid global anycast IPs** (like 1.1.1.1 or 8.8.8.8) for the Europe target — anycast routes to whichever point-of-presence is nearest you, which may not even be in Europe.
- **Good Europe targets**: Hetzner's dedicated ICMP test hosts are stable, single-location, and made for exactly this purpose:
  ```bash
  fping -c 4 fsn.icmp.hetzner.com   # Falkenstein, Germany
  fping -c 4 nbg.icmp.hetzner.com   # Nuremberg, Germany
  fping -c 4 hel.icmp.hetzner.com   # Helsinki, Finland
  ```
  Resolve to an IP once (`dig +short fsn.icmp.hetzner.com`) and hardcode it in `config.yaml` to avoid a DNS lookup on every run.
- **Good Nairobi targets**: a local ISP's Nairobi-based infrastructure IP, or better, a cheap local VPS (Sasahost, HostPinnacle) you control directly.
- Verify any candidate target with `traceroute`/`mtr` before trusting it — geolocation databases are sometimes wrong about where an IP actually sits.

## Roadmap / upcoming steps

- [ ] Swap remaining placeholder/unverified targets for confirmed, controlled hosts (e.g. a self-provisioned VPS for both Nairobi and Europe legs)
- [ ] Add `test_queries.py` and `test_db.py` for coverage beyond the parser
- [ ] Add a `linkwatch chart <target> --hours N` subcommand using `plotext` or `asciichartpy` for terminal-native RTT trend graphs
- [ ] Add outage-duration detection (group consecutive high-loss rows into incidents, not just individual data points)
- [ ] Add a data retention/rollup job — downsample raw per-minute rows into hourly aggregates after 30 days to keep the database lean over a multi-year run
- [ ] Migrate deployment from the current dev machine to an always-on host (Raspberry Pi or cheap VPS) so collection isn't interrupted by sleep/reboot
- [ ] Add jitter (`rtt_mdev`) tracking — fping's default output doesn't include it; consider `fping -e` or ICMP timestamp deltas for a true jitter figure
- [ ] Add basic alerting (e.g. a Slack/email ping, or just a loud terminal notification) when packet loss on any target exceeds a threshold for N consecutive runs

