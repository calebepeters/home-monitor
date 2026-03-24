# Home Network Monitor

A lightweight home network monitoring tool that polls hosts and services on a 60-second interval, stores results in SQLite, serves a web dashboard, and sends push alerts via [ntfy.sh](https://ntfy.sh) when something goes down.

Built to run as a systemd service on Ubuntu 24.04 (Proxmox). No Docker.

## Features

- **Ping, HTTP, and TCP checks** — mix and match per host
- **Push alerts** via ntfy.sh — notifies on 2nd consecutive failure and on recovery
- **SQLite storage** — no external database required
- **Web dashboard** — dark-themed, auto-refreshes every 30 seconds, shows uptime and latency per host
- **Expandable history** — click any host card to see recent check results

## Dashboard

![Dashboard screenshot placeholder](https://placehold.co/800x400/1a1a2e/00c853?text=Home+Network+Monitor)

## Quick Start

### Local development

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Copy the example config and fill in your hosts and ntfy topic
cp config.example.yaml config.yaml
python main.py
# Dashboard at http://localhost:8080
```

### Production (Ubuntu 24.04)

```bash
# Copy repo to /opt/network-monitor, then:
sudo bash setup.sh
```

The setup script installs dependencies, creates a venv, sets the `cap_net_raw` capability for unprivileged ICMP ping, and enables the systemd service.

## Configuration

Copy `config.example.yaml` to `config.yaml` and edit it (`config.yaml` is gitignored so your real IPs and ntfy topic stay local):

```yaml
ntfy:
  url: "https://ntfy.sh"
  topic: "your-unique-topic"   # subscribe to this in the ntfy app

polling:
  interval_seconds: 60
  alert_after_failures: 2      # alert on 2nd consecutive failure
  check_timeout_seconds: 10

hosts:
  - name: "My Router"
    checks:
      - type: ping
        host: "192.168.1.1"

  - name: "My Server"
    checks:
      - type: http
        url: "http://192.168.1.10:8080"
        expected_status: 200
      - type: tcp
        host: "192.168.1.10"
        port: 22
```

A host is considered **DOWN** if any of its checks fail.

## Check Types

| Type | Required fields | Notes |
|------|----------------|-------|
| `ping` | `host` | Uses ICMP; requires `cap_net_raw` in production |
| `http` | `url`, `expected_status` | SSL verification disabled (supports self-signed certs) |
| `tcp` | `host`, `port` | Checks that a TCP connection can be established |

## Project Structure

```
src/monitor/
├── checks.py      # ping, HTTP, TCP check functions
├── database.py    # SQLite schema + queries
├── poller.py      # async polling loop + state tracking
├── alerting.py    # ntfy.sh integration
└── api.py         # FastAPI app + routes
static/
└── index.html         # single-file frontend
main.py                # entry point
config.example.yaml    # example config — copy to config.yaml and edit
setup.sh           # Ubuntu 24.04 install script
monitor.service    # systemd unit file
```

## Running Tests

```bash
pip install -r requirements.txt
pytest
```

## Alerts

Subscribe to your ntfy topic in the [ntfy app](https://ntfy.sh) (iOS/Android/web) using the topic name you set in `config.yaml`. You'll receive:

- 🔴 **DOWN** alert on the 2nd consecutive failure (urgent priority)
- 🟢 **UP** alert when a host recovers
